from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from auth import require_admin
from database import db
from models import Run

runs_bp = Blueprint("runs", __name__)


@runs_bp.route("/", methods=["GET"])
def list_runs():
    from models import PersonalitySnapshot
    from simulation import get_running_run_ids

    runs = Run.query.order_by(Run.id).all()
    running_ids = get_running_run_ids()

    # Snapshot-based tick floor per run (in case last_tick was reset or not saved)
    tick_floors = {
        row[0]: row[1]
        for row in db.session.query(
            PersonalitySnapshot.run_id,
            db.func.max(PersonalitySnapshot.tick_number)
        ).group_by(PersonalitySnapshot.run_id).all()
    }

    result = []
    for r in runs:
        d = r.to_dict()
        d["tick_count"] = max(tick_floors.get(r.id, 0), r.last_tick or 0)
        result.append(d)

    return jsonify({
        "runs": result,
        "running_run_ids": running_ids,
    })


@runs_bp.route("/personas", methods=["GET"])
def list_personas():
    from personas import PERSONAS
    return jsonify([
        {"key": k, "label": v["label"], "description": v["description"]}
        for k, v in PERSONAS.items()
    ])


@runs_bp.route("/", methods=["POST"])
@require_admin
def create_run():
    data = request.get_json() or {}
    if not data.get("name", "").strip():
        return jsonify({"error": "name is required"}), 400
    run = Run(
        name=data["name"],
        description=data.get("description"),
        model=data.get("model", "mistral-large-latest"),
        model_version=data.get("model_version"),
        news_enabled=data.get("news_enabled", True),
        news_categories=data.get("news_categories"),
        post_framing=data.get("post_framing", "an entity on a social network"),
        ipip_framing=data.get("ipip_framing", "your recent inner and outer life"),
        seed_distribution=data.get("seed_distribution", "random"),
        persona=data.get("persona"),
        agent_count=data.get("agent_count"),
        tick_limit=data.get("tick_limit"),
        tick_duration_s=data.get("tick_duration_s"),
        batch_mode=data.get("batch_mode", False),
        ipip_grounded=data.get("ipip_grounded", True),
        random_seed=data.get("random_seed"),
        name_pool=data.get("name_pool") or None,
        notes=data.get("notes"),
        status="seeding",
    )
    db.session.add(run)
    db.session.commit()

    app = current_app._get_current_object()

    if not app.config.get("TESTING"):
        import threading
        run_id = run.id
        num = run.agent_count or 30

        def do_seed():
            with app.app_context():
                from seed import seed_for_run
                # pokemon persona overrides num_agents to 151 inside seed_for_run
                seed_for_run(run_id, num_agents=num)

        threading.Thread(target=do_seed, daemon=True).start()

    return jsonify(run.to_dict()), 201


@runs_bp.route("/<int:run_id>/start", methods=["POST"])
@require_admin
def start_run(run_id):
    """Start or resume a run."""
    run = Run.query.get_or_404(run_id)
    if run.status in ("seeding", "pending"):
        return jsonify({"error": "run is not ready to start"}), 409
    run.status = "running"
    run.ended_at = None
    if not run.started_at:
        run.started_at = datetime.utcnow()
    db.session.commit()

    from simulation import start_run_thread
    start_run_thread(current_app._get_current_object(), run_id)
    return jsonify({"ok": True, "run_id": run_id})


@runs_bp.route("/<int:run_id>/stop", methods=["POST"])
@require_admin
def stop_run(run_id):
    """Stop a run. The tick thread will exit on its next iteration."""
    run = Run.query.get_or_404(run_id)
    run.status = "stopped"
    run.ended_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})


@runs_bp.route("/<int:run_id>", methods=["DELETE"])
@require_admin
def delete_run(run_id):
    """Delete a run and all associated data."""
    run = Run.query.get_or_404(run_id)
    if run.status == "running":
        return jsonify({"error": "stop the run before deleting"}), 409
    db.session.delete(run)
    db.session.commit()
    return jsonify({"ok": True})
