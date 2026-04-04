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
    tick_counts[state.run_id] = state.current_tick

    result = []
    for r in runs:
        d = r.to_dict()
        d["tick_count"] = tick_counts.get(r.id, 0)
        result.append(d)

    return jsonify({
        "runs": result,
        "active_run_id": state.run_id,
        "current_tick": state.current_tick,
        "is_running": state.is_running,
    })


@runs_bp.route("/", methods=["POST"])
@require_admin
def create_run():
    data = request.get_json()
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
        agent_count=data.get("agent_count"),
        tick_limit=data.get("tick_limit"),
        tick_duration_s=data.get("tick_duration_s"),
        notes=data.get("notes"),
        started_at=datetime.utcnow(),
    )
    db.session.add(run)
    db.session.commit()
    return jsonify(run.to_dict()), 201


@runs_bp.route("/<int:run_id>/activate", methods=["POST"])
@require_admin
def activate_run(run_id):
    """Switch the simulation to a different run."""
    run = Run.query.get_or_404(run_id)
    state = SimState.get()
    was_running = state.is_running
    state.is_running = False  # stop before switching
    state.run_id = run.id
    state.current_tick = _max_tick_for_run(run.id)
    db.session.commit()
    return jsonify({
        "ok": True,
        "active_run_id": run.id,
        "current_tick": state.current_tick,
        "was_running": was_running,
    })


@runs_bp.route("/<int:run_id>/seed", methods=["POST"])
@require_admin
def seed_run(run_id):
    """Seed agents for a run. Runs in background — returns immediately."""
    import threading
    run = Run.query.get_or_404(run_id)
    from flask import current_app
    app = current_app._get_current_object()

    def do_seed():
        with app.app_context():
            from seed import seed_for_run
            num = run.agent_count or 30
            seed_for_run(run_id, num_agents=num)

    threading.Thread(target=do_seed, daemon=True).start()
    return jsonify({"ok": True, "message": f"Seeding {run.agent_count or 30} agents in background"})


@runs_bp.route("/<int:run_id>/start", methods=["POST"])
@require_admin
def start_run(run_id):
    """Activate a run and start the sim."""
    run = Run.query.get_or_404(run_id)
    state = SimState.get()
    state.run_id = run.id
    state.current_tick = _max_tick_for_run(run.id)
    state.is_running = True
    db.session.commit()
    return jsonify({"ok": True, "active_run_id": run.id, "current_tick": state.current_tick})


@runs_bp.route("/<int:run_id>/stop", methods=["POST"])
@require_admin
def stop_run(run_id):
    """Stop the sim (run stays active)."""
    state = SimState.get()
    state.is_running = False
    db.session.commit()
    return jsonify({"ok": True})


def _max_tick_for_run(run_id):
    from models import PersonalitySnapshot
    result = db.session.query(
        db.func.max(PersonalitySnapshot.tick_number)
    ).filter_by(run_id=run_id).scalar()
    return result or 0
