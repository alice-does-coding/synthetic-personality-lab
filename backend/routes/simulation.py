from flask import Blueprint, jsonify

from models import Agent

simulation_bp = Blueprint("simulation", __name__)


def _get_public_run_id():
    from models import Run
    run = Run.query.filter_by(is_public=True).first()
    return run.id if run else None


@simulation_bp.route("/run", methods=["GET"])
def get_run():
    from models import Run
    run = Run.query.filter_by(is_public=True).first()
    if not run:
        return jsonify(None), 200
    return jsonify(run.to_dict())


@simulation_bp.route("/agents", methods=["GET"])
def list_agents():
    run_id = _get_public_run_id()
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
