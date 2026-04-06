import logging
import threading
import time

import requests

from config import Config
from providers.base import LLMAuthError, LLMRateLimitError

logger = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────
# HF Pro serverless: ~10 req/sec is safe; default conservative at 8

_rl_lock = threading.Lock()
_rl_next = 0.0  # monotonic time when next call is allowed

# Auth-failure latch — set on first 401 this tick; subsequent in-flight workers
# bail immediately without making HTTP calls or logging duplicate errors.
_auth_failed = threading.Event()

HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/{model}/v1/chat/completions"


def reset_auth():
    """Clear the auth-failure latch. Called at tick start via llm.py."""
    _auth_failed.clear()


def chat(messages, max_tokens, temperature, model):
    """Call HF Inference API (OpenAI-compatible chat endpoint).

    Retries on 5xx/429 with exponential backoff — same pattern as mistral.py.
    Returns the plain string content from choices[0].message.content.

    Raises LLMAuthError on 401.
    Raises LLMRateLimitError if all retries on 429 are exhausted.
    """
    global _rl_next
    if _auth_failed.is_set():
        raise LLMAuthError("HF API key invalid (auth failure already seen this tick)")
    url = HF_INFERENCE_URL.format(model=model)
    headers = {
        "Authorization": f"Bearer {Config.HF_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    max_retries = 6
    for attempt in range(max_retries):
        # Proactive throttle
        with _rl_lock:
            now = time.monotonic()
            wait = _rl_next - now
            if wait > 0:
                time.sleep(wait)
            _rl_next = time.monotonic() + (1.0 / Config.HF_RATE_LIMIT)

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.exceptions.Timeout as exc:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("HF request timeout (attempt %d/%d) — backing off %ds",
                               attempt + 1, max_retries, backoff)
                time.sleep(backoff)
                continue
            raise

        if resp.status_code == 200:
            data = resp.json()
            return data["choices"][0]["message"]["content"]

        if resp.status_code == 401:
            if not _auth_failed.is_set():
                logger.error("HF 401 — invalid or exhausted API key. Stopping.")
                _auth_failed.set()
            raise LLMAuthError(f"HF auth error: {resp.text}")

        if resp.status_code == 429:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("HF 429 rate limit (attempt %d/%d) — backing off %ds",
                               attempt + 1, max_retries, backoff)
                time.sleep(backoff)
                continue
            raise LLMRateLimitError(f"HF rate limit exhausted after {max_retries} attempts")

        if resp.status_code in (500, 502, 503, 504):
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("HF %d server error (attempt %d/%d) — backing off %ds",
                               resp.status_code, attempt + 1, max_retries, backoff)
                time.sleep(backoff)
                continue
            resp.raise_for_status()

        # Any other non-2xx
        resp.raise_for_status()
