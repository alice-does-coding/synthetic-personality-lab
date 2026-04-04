from flask import Blueprint, jsonify, current_app

from auth import require_admin
from database import db
from models import SimState

sim_bp = Blueprint("sim", __name__)


@sim_bp.route("/status", methods=["GET"])
def status():
    from config import Config
    state = SimState.get()
    return jsonify({
        "current_tick": state.current_tick,
        "is_running": state.is_running,
        "active_run_id": state.run_id,
        "agents_per_tick": Config.AGENTS_PER_TICK,
        "rate_limit": Config.MISTRAL_RATE_LIMIT,
    })


@sim_bp.route("/start", methods=["POST"])
@require_admin
def start():
    state = SimState.get()
    state.is_running = True
    db.session.commit()
    return jsonify({"ok": True, "current_tick": state.current_tick})


@sim_bp.route("/stop", methods=["POST"])
@require_admin
def stop():
    state = SimState.get()
    state.is_running = False
    db.session.commit()
    return jsonify({"ok": True, "current_tick": state.current_tick})


@sim_bp.route("/tick", methods=["POST"])
@require_admin
def manual_tick():
    """Fire a single tick immediately — useful for development."""
    from simulation import run_tick
    run_tick(current_app._get_current_object(), force=True)
    state = SimState.get()
    return jsonify({"ok": True, "current_tick": state.current_tick})


@sim_bp.route("/assess", methods=["POST"])
@require_admin
def manual_assess():
    """Kick off a full IPIP assessment in the background and return immediately."""
    import threading
    from simulation import run_tick
    app = current_app._get_current_object()
    threading.Thread(target=run_tick, kwargs={"app": app, "force": True, "force_ipip": True}, daemon=True).start()
    return jsonify({"ok": True, "message": "assessment started"})
