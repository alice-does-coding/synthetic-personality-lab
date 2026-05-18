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

HF_INFERENCE_URL = "https://router.huggingface.co/v1/chat/completions"


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
    url = HF_INFERENCE_URL
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

        if resp.status_code == 403:
            # Model gated — user must accept terms on huggingface.co/model-page
            msg = f"HF 403 — model access denied for {model}. Accept the model's terms on huggingface.co then retry."
            logger.error(msg)
            raise LLMAuthError(msg)

        if resp.status_code in (400, 422):
            logger.error("HF %d — bad request for model %s: %s", resp.status_code, model, resp.text[:500])
            raise RuntimeError(f"HF {resp.status_code} bad request: {resp.text[:300]}")

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

        # Any other non-2xx — log body before raising so we can diagnose
        logger.error("HF %d error for model %s: %s", resp.status_code, model, resp.text[:500])
        resp.raise_for_status()


# ── Avatar generation (FLUX text-to-image) ───────────────────────────────────

_AVATAR_MODEL = "black-forest-labs/FLUX.1-schnell"
_AVATAR_URL   = f"https://router.huggingface.co/hf-inference/models/{_AVATAR_MODEL}"


def generate_avatar(bio, name=None, model=None):
    """Generate a 256×256 profile portrait from a bio via FLUX.1-schnell.

    Returns a base64 data URL (data:image/...) or None on any failure.
    Failures are logged but never raised — avatar generation is best-effort.
    """
    import base64

    subject = f"{name} — {bio[:120]}" if name else bio[:180]
    prompt = (
        f"Generate an 8-bit pixel art portrait profile picture based on this description: {subject}. "
        "The style should be highly pixelated, with visible grid lines, limited color palette, "
        "and sharp, blocky edges. Emphasize the retro video game aesthetic, using large, distinct pixels. "
        "The image should look like it belongs in an early 8-bit or 16-bit era game, "
        "with minimal detail and exaggerated features."
    )
    url = _AVATAR_URL
    headers = {
        "Authorization": f"Bearer {Config.HF_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {"width": 256, "height": 256, "num_inference_steps": 4},
    }

    for attempt in range(4):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
        except requests.exceptions.Timeout:
            logger.warning("FLUX avatar timeout (attempt %d/4)", attempt + 1)
            continue

        if resp.status_code == 200:
            mime = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
            b64  = base64.b64encode(resp.content).decode("utf-8")
            return f"data:{mime};base64,{b64}"

        if resp.status_code == 503:
            # Model loading — HF returns estimated_time in body
            import time, json as _json
            try:
                wait = _json.loads(resp.text).get("estimated_time", 20)
            except Exception:
                wait = 20
            logger.info("FLUX model loading — waiting %.0fs", wait)
            time.sleep(min(wait, 30))
            continue

        logger.warning("FLUX avatar failed (%d): %s", resp.status_code, resp.text[:200])
        return None

    logger.warning("FLUX avatar: all retries exhausted")
    return None
