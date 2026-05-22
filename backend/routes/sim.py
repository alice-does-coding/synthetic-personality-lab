from flask import Blueprint, jsonify

from auth import require_admin

sim_bp = Blueprint("sim", __name__)


@sim_bp.route("/admin-check", methods=["GET"])
@require_admin
def admin_check():
    """Lightweight endpoint used by the frontend to verify an admin key
    before unlocking. Returns 200 if the X-Admin-Key header matches, else 401."""
    return jsonify({"ok": True})
