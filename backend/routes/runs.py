from datetime import datetime

from flask import Blueprint, jsonify, request

from auth import require_admin
from database import db
from models import Run, SimState

runs_bp = Blueprint("runs", __name__)


@runs_bp.route("/", methods=["GET"])
def list_runs():
    from models import PersonalitySnapshot
    runs = Run.query.order_by(Run.id).all()
    state = SimState.get()

    # Real tick count per run from snapshots
    tick_counts = {
        row[0]: row[1]
        for row in db.session.query(
            PersonalitySnapshot.run_id,
            db.func.max(PersonalitySnapshot.tick_number)
        ).group_by(PersonalitySnapshot.run_id).all()
    }
    # Active run uses live sim tick (more up-to-date than last snapshot)
    if state.run_id:
        tick_counts[state.run_id] = state.current_tick

    result = []
    for r in runs:
        d = r.to_dict()
        # Use the best available tick count: live sim > last saved > max snapshot
        d["tick_count"] = max(tick_counts.get(r.id, 0), r.last_tick)
        result.append(d)

    return jsonify({
        "runs": result,
        "active_run_id": state.run_id,
        "current_tick": state.current_tick,
        "is_running": state.is_running,
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
        post_framing=data.get("post_framing", "a user on a social media platform"),
        ipip_framing=data.get("ipip_framing", "your recent inner and outer life"),
        seed_distribution=data.get("seed_distribution", "random"),
        persona=data.get("persona"),
        agent_count=data.get("agent_count"),
        tick_limit=data.get("tick_limit"),
        tick_duration_s=data.get("tick_duration_s"),
        notes=data.get("notes"),
        status="seeding",
    )
    db.session.add(run)
    db.session.commit()

    from flask import current_app
    app = current_app._get_current_object()

    if not app.config.get("TESTING"):
        import threading
        run_id = run.id
        num = run.agent_count or 30

        def do_seed():
            with app.app_context():
                from seed import seed_for_run
                seed_for_run(run_id, num_agents=num)

        threading.Thread(target=do_seed, daemon=True).start()

    return jsonify(run.to_dict()), 201


@runs_bp.route("/<int:run_id>/activate", methods=["POST"])
@require_admin
def activate_run(run_id):
    """Manually jump the queue — stop current run and activate this one."""
    run = Run.query.get_or_404(run_id)
    state = SimState.get()

    # Save tick position and stop the previously active run
    if state.run_id and state.run_id != run_id:
        _save_tick_for_run(state.run_id, state.current_tick)
        prev = db.session.get(Run, state.run_id)
        if prev and prev.status == "running":
            prev.status = "stopped"
            prev.ended_at = datetime.utcnow()

    state.is_running = False
    state.run_id = run.id
    state.current_tick = _max_tick_for_run(run.id)
    run.status = "running"
    if not run.started_at:
        run.started_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "active_run_id": run.id, "current_tick": state.current_tick})



@runs_bp.route("/<int:run_id>/start", methods=["POST"])
@require_admin
def start_run(run_id):
    """Start (or resume) a run without resetting tick position."""
    run = Run.query.get_or_404(run_id)
    state = SimState.get()
    state.run_id = run.id
    state.is_running = True
    run.status = "running"
    run.ended_at = None
    if not run.started_at:
        run.started_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True, "active_run_id": run.id, "current_tick": state.current_tick})


@runs_bp.route("/<int:run_id>/stop", methods=["POST"])
@require_admin
def stop_run(run_id):
    """Pause the sim."""
    run = Run.query.get_or_404(run_id)
    state = SimState.get()
    _save_tick_for_run(run_id, state.current_tick)
    run.status = "stopped"
    run.ended_at = datetime.utcnow()
    state.is_running = False
    db.session.commit()
    return jsonify({"ok": True})


@runs_bp.route("/<int:run_id>", methods=["DELETE"])
@require_admin
def delete_run(run_id):
    """Delete a run and all associated data."""
    run = Run.query.get_or_404(run_id)
    state = SimState.get()

    if run.status == "running":
        return jsonify({"error": "Cannot delete a running run. Stop it first."}), 409

    # If SimState still points here, clear it
    if state.run_id == run_id:
        state.is_running = False
        state.run_id = None
        state.current_tick = 0

    db.session.delete(run)
    db.session.commit()
    return jsonify({"ok": True})


def _max_tick_for_run(run_id):
    from models import PersonalitySnapshot
    snapshot_max = db.session.query(
        db.func.max(PersonalitySnapshot.tick_number)
    ).filter_by(run_id=run_id).scalar() or 0
    run = db.session.get(Run, run_id)
    last_tick = run.last_tick if run else 0
    return max(snapshot_max, last_tick)


def _save_tick_for_run(run_id, tick):
    """Persist current tick position on the run so it survives switching."""
    run = db.session.get(Run, run_id)
    if run:
        run.last_tick = tick
