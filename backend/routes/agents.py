from collections import defaultdict

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from auth import require_admin
from database import db
from models import Agent, Follow, PersonalitySnapshot

agents_bp = Blueprint("agents", __name__)


@agents_bp.route("/", methods=["GET"])
def list_agents():
    agents = Agent.query.filter_by(is_active=True).all()
    return jsonify([a.to_dict() for a in agents])


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
    import math
    snapshots = PersonalitySnapshot.query.order_by(PersonalitySnapshot.tick_number).all()

    by_tick = defaultdict(list)
    for s in snapshots:
        by_tick[s.tick_number].append(s)

    def sd(values, mean):
        if len(values) < 2:
            return 0.0
        return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))

    result = []
    for tick, snaps in sorted(by_tick.items()):
        n = len(snaps)
        row = {"tick_number": tick, "agent_count": n}
        for trait in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
            vals = [getattr(s, trait) for s in snaps]
            mean = sum(vals) / n
            row[trait] = mean
            row[f"{trait}_sd"] = sd(vals, mean)
        result.append(row)

    return jsonify(result)


@agents_bp.route("/graph", methods=["GET"])
def graph():
    """Nodes + directed edges for the social graph."""
    from models import Follow
    agents = Agent.query.filter_by(is_active=True).all()
    follows = Follow.query.all()

    # Post and follower counts
    from collections import Counter
    from models import Post
    post_counts     = Counter(p.agent_id for p in Post.query.filter_by(is_public=True).all())
    follower_counts = Counter(f.followee_id for f in follows)

    nodes = [
        {
            "id":                a.id,
            "name":              a.name,
            "handle":            a.handle,
            "openness":          a.openness,
            "conscientiousness": a.conscientiousness,
            "extraversion":      a.extraversion,
            "agreeableness":     a.agreeableness,
            "neuroticism":       a.neuroticism,
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
    agents = Agent.query.filter_by(is_active=True).all()
    result = []
    for agent in agents:
        snaps = (
            PersonalitySnapshot.query
            .filter_by(agent_id=agent.id)
            .order_by(PersonalitySnapshot.tick_number)
            .all()
        )
        result.append({
            "id":     agent.id,
            "name":   agent.name,
            "handle": agent.handle,
            "snapshots": [s.to_dict() for s in snaps],
        })
    return jsonify(result)


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
