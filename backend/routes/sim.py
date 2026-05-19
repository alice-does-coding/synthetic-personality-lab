from flask import Blueprint, jsonify, current_app, request

from auth import require_admin
from config import Config

sim_bp = Blueprint("sim", __name__)


@sim_bp.route("/status", methods=["GET"])
def status():
    from engine import get_running_run_ids
    return jsonify({
        "running_run_ids":  get_running_run_ids(),
        "agents_per_tick":  Config.AGENTS_PER_TICK,
        "rate_limit":       Config.MISTRAL_RATE_LIMIT,
        "max_workers":      Config.MAX_WORKERS,
    })


@sim_bp.route("/admin-check", methods=["GET"])
@require_admin
def admin_check():
    """Lightweight endpoint used by the frontend to verify an admin key
    before unlocking. Returns 200 if the X-Admin-Key header matches, else 401."""
    return jsonify({"ok": True})


@sim_bp.route("/tick", methods=["POST"])
@require_admin
def manual_tick():
    """Fire a single tick for a specific run."""
    data   = request.get_json() or {}
    run_id = data.get("run_id")
    if not run_id:
        return jsonify({"error": "run_id required"}), 400
    force_ipip = data.get("force_ipip", False)
    skip_ipip  = data.get("skip_ipip",  False)
    import threading
    from engine import run_tick
    app = current_app._get_current_object()
    threading.Thread(
        target=run_tick,
        kwargs={"app": app, "run_id": run_id, "force": True,
                "force_ipip": force_ipip, "skip_ipip": skip_ipip},
        daemon=True,
    ).start()
    return jsonify({"ok": True, "run_id": run_id})


@sim_bp.route("/assess", methods=["POST"])
@require_admin
def manual_assess():
    """Force a full IPIP assessment for a specific run."""
    data   = request.get_json() or {}
    run_id = data.get("run_id")
    if not run_id:
        return jsonify({"error": "run_id required"}), 400
    import threading
    from engine import run_tick
    app = current_app._get_current_object()
    threading.Thread(
        target=run_tick,
        kwargs={"app": app, "run_id": run_id, "force": True, "force_ipip": True},
        daemon=True,
    ).start()
    return jsonify({"ok": True, "run_id": run_id})
