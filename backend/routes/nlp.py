"""
Thin proxy to the NLP microservice.
Lets the frontend (or other backend routes) call /api/nlp/analyze
without needing to know the NLP service URL.
"""
import json
import time
import urllib.error
import urllib.request

from flask import Blueprint, jsonify, request

from config import Config

nlp_bp = Blueprint("nlp", __name__)


def _forward(path, body, retries=3):
    payload = json.dumps(body).encode()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                Config.NLP_SERVICE_URL + path,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, OSError) as exc:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise


@nlp_bp.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "missing text"}), 400
    try:
        return jsonify(_forward("/analyze", {"text": data["text"]}))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@nlp_bp.route("/analyze/batch", methods=["POST"])
def analyze_batch():
    data = request.get_json()
    if not data or "texts" not in data:
        return jsonify({"error": "missing texts"}), 400
    try:
        return jsonify(_forward("/analyze/batch", {"texts": data["texts"]}))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@nlp_bp.route("/health", methods=["GET"])
def health():
    try:
        req = urllib.request.Request(Config.NLP_SERVICE_URL + "/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return jsonify(json.loads(resp.read()))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502
