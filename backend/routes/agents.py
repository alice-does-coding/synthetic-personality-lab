from collections import defaultdict

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from database import db
from models import Agent, Follow, PersonalitySnapshot

agents_bp = Blueprint("agents", __name__)


@agents_bp.route("/", methods=["GET"])
def list_agents():
    agents = Agent.query.filter_by(is_active=True).all()
    return jsonify([a.to_dict() for a in agents])


@agents_bp.route("/", methods=["POST"])
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
    """Average OCEAN scores across all agents per tick, for population-level drift chart."""
    snapshots = PersonalitySnapshot.query.order_by(PersonalitySnapshot.tick_number).all()

    by_tick = defaultdict(list)
    for s in snapshots:
        by_tick[s.tick_number].append(s)

    result = []
    for tick, snaps in sorted(by_tick.items()):
        n = len(snaps)
        result.append({
            "tick_number":       tick,
            "openness":          sum(s.openness          for s in snaps) / n,
            "conscientiousness": sum(s.conscientiousness for s in snaps) / n,
            "extraversion":      sum(s.extraversion      for s in snaps) / n,
            "agreeableness":     sum(s.agreeableness     for s in snaps) / n,
            "neuroticism":       sum(s.neuroticism       for s in snaps) / n,
            "agent_count":       n,
        })

    return jsonify(result)


@agents_bp.route("/<int:follower_id>/follow/<int:followee_id>", methods=["POST"])
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
def unfollow(follower_id, followee_id):
    follow = Follow.query.filter_by(
        follower_id=follower_id, followee_id=followee_id
    ).first_or_404()
    db.session.delete(follow)
    db.session.commit()
    return jsonify({"ok": True})
