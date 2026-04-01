from flask import Blueprint, jsonify, current_app

from database import db
from models import SimState

sim_bp = Blueprint("sim", __name__)


@sim_bp.route("/status", methods=["GET"])
def status():
    state = SimState.get()
    return jsonify({
        "current_tick": state.current_tick,
        "is_running": state.is_running,
    })


@sim_bp.route("/start", methods=["POST"])
def start():
    state = SimState.get()
    state.is_running = True
    db.session.commit()
    return jsonify({"ok": True, "current_tick": state.current_tick})


@sim_bp.route("/stop", methods=["POST"])
def stop():
    state = SimState.get()
    state.is_running = False
    db.session.commit()
    return jsonify({"ok": True, "current_tick": state.current_tick})


@sim_bp.route("/tick", methods=["POST"])
def manual_tick():
    """Fire a single tick immediately — useful for development."""
    from simulation import run_tick
    run_tick(current_app._get_current_object(), force=True)
    state = SimState.get()
    return jsonify({"ok": True, "current_tick": state.current_tick})
