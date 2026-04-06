from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from auth import require_admin
from database import db
from models import Run

runs_bp = Blueprint("runs", __name__)


@runs_bp.route("/", methods=["GET"])
def list_runs():
    from models import Agent, PersonalitySnapshot, Post
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

    # Actual max post tick per run — may differ from last_tick when post generation
    # failed (e.g. Mistral 401) while the tick counter kept incrementing
    post_tick_maxes = {
        row[0]: row[1]
        for row in db.session.query(
            Post.run_id,
            db.func.max(Post.tick_number)
        ).group_by(Post.run_id).all()
    }

    # Actual seeded agent count — may differ from agent_count (e.g. pokemon = 151)
    actual_agent_counts = {
        row[0]: row[1]
        for row in db.session.query(Agent.run_id, db.func.count(Agent.id))
        .group_by(Agent.run_id).all()
    }

    # Public post count per run
    post_counts = {
        row[0]: row[1]
        for row in db.session.query(Post.run_id, db.func.count(Post.id))
        .filter(Post.is_public == True)
        .group_by(Post.run_id).all()
    }

    result = []
    for r in runs:
        d = r.to_dict()
        d["tick_count"]          = max(tick_floors.get(r.id, 0), r.last_tick or 0)
        d["max_post_tick"]       = post_tick_maxes.get(r.id, 0)
        d["actual_agent_count"]  = actual_agent_counts.get(r.id, 0)
        d["post_count"]          = post_counts.get(r.id, 0)
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
        provider=data.get("provider", "mistral"),
        model_version=data.get("model_version"),
        news_enabled=data.get("news_enabled", True),
        news_categories=data.get("news_categories"),
        post_framing=data.get("post_framing") or "an entity on a social network",
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
    prev_status = run.status
    run.status = "running"
    run.ended_at = None
    if not run.started_at:
        run.started_at = datetime.utcnow()
    db.session.commit()

    app = current_app._get_current_object()
    from simulation import log_event, start_run_thread
    if prev_status == "failed":
        log_event(app, run_id, "info", f"Retry initiated (previous status: {prev_status})")
    elif prev_status == "stopped":
        log_event(app, run_id, "info", "Run resumed")
    start_run_thread(app, run_id)
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


@runs_bp.route("/<int:run_id>/events", methods=["GET"])
def get_run_events(run_id):
    from models import RunEvent
    events = RunEvent.query.filter_by(run_id=run_id).order_by(RunEvent.id).all()
    return jsonify([e.to_dict() for e in events])


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
