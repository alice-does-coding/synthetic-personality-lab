from flask import Blueprint, jsonify, request

from arcade import create_arcade_agent
from models import Agent

arcade_bp = Blueprint("arcade", __name__)

_VALID_SEED_MODES = {"describe", "random", "scratch"}


def _get_arcade_run_id():
    from models import Run
    run = Run.query.filter_by(is_arcade=True).first()
    return run.id if run else None


@arcade_bp.route("/run", methods=["GET"])
def get_run():
    from models import Run
    run = Run.query.filter_by(is_arcade=True).first()
    if not run:
        return jsonify(None), 200
    return jsonify(run.to_dict())


@arcade_bp.route("/agents", methods=["POST"])
def submit_agent():
    data = request.get_json(silent=True) or {}

    creator_token = data.get("creator_token", "")
    if not creator_token:
        return jsonify({"error": "creator_token is required"}), 400

    seed_mode = data.get("seed_mode", "describe")
    if seed_mode not in _VALID_SEED_MODES:
        return jsonify({"error": f"seed_mode must be one of: {', '.join(sorted(_VALID_SEED_MODES))}"}), 400

    try:
        if seed_mode == "random":
            agent = create_arcade_agent(creator_token, seed_mode="random")

        elif seed_mode == "scratch":
            agent = create_arcade_agent(
                creator_token,
                seed_mode="scratch",
                name=data.get("name", ""),
                bio=data.get("bio", ""),
                openness=data.get("openness"),
                conscientiousness=data.get("conscientiousness"),
                extraversion=data.get("extraversion"),
                agreeableness=data.get("agreeableness"),
                neuroticism=data.get("neuroticism"),
            )

        else:  # describe
            agent = create_arcade_agent(
                creator_token,
                seed_mode="describe",
                name=data.get("name", ""),
                description=data.get("description", ""),
            )

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify(agent.to_dict()), 201


@arcade_bp.route("/agents", methods=["GET"])
def list_agents():
    run_id = _get_arcade_run_id()
    if not run_id:
        return jsonify([])
    agents = (
        Agent.query
        .filter_by(run_id=run_id, is_active=True)
        .filter(Agent.creator_token.isnot(None))
        .order_by(Agent.created_at.desc())
        .all()
    )
    return jsonify([a.to_dict() for a in agents])


@arcade_bp.route("/agents/mine", methods=["GET"])
def my_agent():
    creator_token = request.args.get("creator_token", "")
    if not creator_token:
        return jsonify({"error": "creator_token is required"}), 400
    agent = Agent.query.filter_by(creator_token=creator_token, is_active=True).first()
    if not agent:
        return jsonify(None), 200
    return jsonify(agent.to_dict())
