from collections import defaultdict

from flask import Blueprint, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from auth import require_admin
from database import db
from models import Agent, Follow, PersonalitySnapshot, OCEAN_KEYS, ocean_dict

agents_bp = Blueprint("agents", __name__)


@agents_bp.route("/", methods=["GET"])
def list_agents():
    from models import PersonalitySnapshot
    run_id = request.args.get("run_id", type=int)
    q = Agent.query.filter_by(is_active=True)
    if run_id:
        q = q.filter_by(run_id=run_id)
    agents = q.all()

    # Batch snapshot counts — one query instead of N lazy loads
    agent_ids = [a.id for a in agents]
    snap_counts = {}
    if agent_ids:
        rows = db.session.query(PersonalitySnapshot.agent_id, func.count(PersonalitySnapshot.id))\
            .filter(PersonalitySnapshot.agent_id.in_(agent_ids))\
            .group_by(PersonalitySnapshot.agent_id).all()
        snap_counts = {agent_id: cnt for agent_id, cnt in rows}

    return jsonify([a.to_dict(snapshot_count=snap_counts.get(a.id, 0)) for a in agents])


@agents_bp.route("/", methods=["POST"])
@require_admin
def create_agent():
    data = request.get_json()
    agent = Agent(
        name=data["name"],
        handle=data["handle"],
        bio=data.get("bio", ""),
    )
    db.session.add(agent)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Handle already taken"}), 409
    return jsonify(agent.to_dict()), 201


@agents_bp.route("/<int:agent_id>", methods=["GET"])
def get_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    return jsonify(agent.to_dict())


@agents_bp.route("/<int:agent_id>", methods=["DELETE"])
@require_admin
def deactivate_agent(agent_id):
    agent = Agent.query.get_or_404(agent_id)
    agent.is_active = False
    db.session.commit()
    return jsonify({"ok": True})


@agents_bp.route("/<int:agent_id>/personality", methods=["GET"])
def get_personality_history(agent_id):
    Agent.query.get_or_404(agent_id)
    snapshots = (
        PersonalitySnapshot.query
        .filter_by(agent_id=agent_id)
        .order_by(PersonalitySnapshot.tick_number)
        .all()
    )
    return jsonify([s.to_dict() for s in snapshots])


@agents_bp.route("/population", methods=["GET"])
def population_drift():
    """Average + SD of OCEAN scores across all agents per tick."""
    run_id = request.args.get("run_id", type=int)
    cols = list(OCEAN_KEYS)

    is_postgres = db.engine.dialect.name == "postgresql"

    if is_postgres:
        aggs = [PersonalitySnapshot.tick_number, func.count(PersonalitySnapshot.id).label("n")]
        for t in cols:
            col = getattr(PersonalitySnapshot, t)
            aggs.append(func.avg(col).label(t))
            aggs.append(func.stddev_pop(col).label(f"{t}_sd"))
        q = db.session.query(*aggs)
        if run_id:
            q = q.filter(PersonalitySnapshot.run_id == run_id)
        rows = q.group_by(PersonalitySnapshot.tick_number).order_by(PersonalitySnapshot.tick_number).all()
        result = []
        for row in rows:
            d = {"tick_number": row.tick_number, "agent_count": row.n}
            for t in cols:
                d[t] = round(getattr(row, t) or 0, 4)
                d[f"{t}_sd"] = round(getattr(row, f"{t}_sd") or 0, 4)
            result.append(d)
    else:
        # SQLite: fetch raw rows and compute stddev in Python
        import math
        from collections import defaultdict
        q = db.session.query(PersonalitySnapshot)
        if run_id:
            q = q.filter(PersonalitySnapshot.run_id == run_id)
        by_tick = defaultdict(list)
        for s in q.order_by(PersonalitySnapshot.tick_number).all():
            by_tick[s.tick_number].append(s)
        result = []
        for tick, snaps in sorted(by_tick.items()):
            d = {"tick_number": tick, "agent_count": len(snaps)}
            for t in cols:
                vals = [getattr(s, t) for s in snaps if getattr(s, t) is not None]
                if vals:
                    mean = sum(vals) / len(vals)
                    sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
                else:
                    mean, sd = 0, 0
                d[t] = round(mean, 4)
                d[f"{t}_sd"] = round(sd, 4)
            result.append(d)

    return jsonify(result)


@agents_bp.route("/graph", methods=["GET"])
def graph():
    """Nodes + directed edges for the social graph."""
    from models import Follow
    run_id = request.args.get("run_id", type=int)
    q = Agent.query.filter_by(is_active=True)
    if run_id:
        q = q.filter_by(run_id=run_id)
    agents = q.all()
    agent_ids = {a.id for a in agents}
    follows = Follow.query.filter(
        Follow.follower_id.in_(agent_ids),
        Follow.followee_id.in_(agent_ids),
    ).all()

    # Post and follower counts — SQL aggregation, no full table load
    from models import Post
    post_q = db.session.query(Post.agent_id, func.count(Post.id).label("n")).filter(Post.is_public == True)
    if run_id:
        post_q = post_q.filter(Post.run_id == run_id)
    post_counts = {row.agent_id: row.n for row in post_q.group_by(Post.agent_id).all()}
    follower_counts = {}
    for f in follows:
        follower_counts[f.followee_id] = follower_counts.get(f.followee_id, 0) + 1

    nodes = [
        {
            "id":                a.id,
            "name":              a.name,
            "handle":            a.handle,
            "avatar":            a.avatar,
            **ocean_dict(a),
            "post_count":        post_counts.get(a.id, 0),
            "follower_count":    follower_counts.get(a.id, 0),
        }
        for a in agents
    ]
    links = [{"source": f.follower_id, "target": f.followee_id} for f in follows]
    return jsonify({"nodes": nodes, "links": links})


@agents_bp.route("/trajectories", methods=["GET"])
def trajectories():
    """Full personality history for all agents — one call for population spaghetti charts."""
    run_id = request.args.get("run_id", type=int)
    q = Agent.query.filter_by(is_active=True)
    if run_id:
        q = q.filter_by(run_id=run_id)
    agents = q.all()
    if not agents:
        return jsonify([])

    agent_map = {a.id: a for a in agents}
    agent_ids = list(agent_map)

    # One query for all snapshots — avoids N+1
    snap_q = PersonalitySnapshot.query.filter(PersonalitySnapshot.agent_id.in_(agent_ids))
    if run_id:
        snap_q = snap_q.filter_by(run_id=run_id)
    snaps = snap_q.order_by(PersonalitySnapshot.agent_id, PersonalitySnapshot.tick_number).all()

    by_agent = defaultdict(list)
    for s in snaps:
        by_agent[s.agent_id].append(s.to_dict())

    return jsonify([
        {
            "id":        a.id,
            "name":      a.name,
            "handle":    a.handle,
            "snapshots": by_agent.get(a.id, []),
        }
        for a in agents
    ])


@agents_bp.route("/<int:follower_id>/follow/<int:followee_id>", methods=["POST"])
@require_admin
def follow(follower_id, followee_id):
    if follower_id == followee_id:
        return jsonify({"error": "Cannot follow yourself"}), 400
    Agent.query.get_or_404(follower_id)
    Agent.query.get_or_404(followee_id)
    db.session.add(Follow(follower_id=follower_id, followee_id=followee_id))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Already following"}), 409
    return jsonify({"ok": True}), 201


@agents_bp.route("/<int:follower_id>/follow/<int:followee_id>", methods=["DELETE"])
@require_admin
def unfollow(follower_id, followee_id):
    follow = Follow.query.filter_by(
        follower_id=follower_id, followee_id=followee_id
    ).first_or_404()
    db.session.delete(follow)
    db.session.commit()
    return jsonify({"ok": True})
