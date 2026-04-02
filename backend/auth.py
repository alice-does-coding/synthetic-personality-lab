from functools import wraps
from flask import request, jsonify, current_app


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = current_app.config.get("ADMIN_KEY")
        if not key:
            return jsonify({"error": "ADMIN_KEY not configured"}), 500
        if request.headers.get("X-Admin-Key") != key:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
