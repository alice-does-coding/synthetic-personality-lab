import logging
import threading
import time

from mistralai.client import Mistral
from mistralai.client.models import TextChunk

from config import Config
from providers._throttle import ProviderGate
from providers.base import LLMAuthError, LLMRateLimitError

logger = logging.getLogger(__name__)

_gate = ProviderGate(rate_limit=Config.MISTRAL_RATE_LIMIT, name="mistral")

# Per-tick call stats (reset at tick start, accumulated across workers)
_stats_lock     = threading.Lock()
_stats_calls    = 0
_stats_throttle = 0.0   # total seconds spent waiting in the rate-limit gate
_stats_api      = 0.0   # total seconds spent waiting for Mistral to respond


def reset_stats(clear_auth_latch=False):
    """Reset per-tick call stats. Auth latch is NOT cleared by default — it persists
    across ticks so we don't waste a call retrying a known-bad key every tick.
    Pass clear_auth_latch=True to allow Mistral to be retried (e.g. hourly)."""
    global _stats_calls, _stats_throttle, _stats_api
    with _stats_lock:
        _stats_calls = _stats_throttle = _stats_api = 0
    if clear_auth_latch:
        _gate.reset_auth()


def read_stats():
    with _stats_lock:
        return _stats_calls, _stats_throttle, _stats_api


# ── Text extraction ───────────────────────────────────────────────────────────

def extract_text(content):
    """Extract plain text from a Mistral response content field (str | list | None)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "".join(c.text for c in content if isinstance(c, TextChunk))


# ── Client factories ──────────────────────────────────────────────────────────

def make_client(timeout_s=60):
    return Mistral(api_key=Config.MISTRAL_API_KEY, timeout_ms=timeout_s * 1000)


def make_ipip_client():
    """Longer timeout for IPIP — 120-item prompts + recent posts take longer to generate."""
    return make_client(timeout_s=120)


# ── Chat with retry + throttle ────────────────────────────────────────────────

def chat(client, messages, max_tokens, temperature, model=None):
    """Call Mistral with proactive throttling + exponential-backoff retry on 429/5xx.

    Raises LLMAuthError on 401. Raises LLMRateLimitError if all retries exhausted on 429.
    Returns the raw response object (resp.choices[0].message.content is str | list[TextChunk]).
    """
    global _stats_calls, _stats_throttle, _stats_api
    model = model or Config.MISTRAL_MODEL
    # If a previous worker already hit a 401 this tick, bail immediately.
    if _gate.is_auth_failed():
        raise LLMAuthError("Mistral API key invalid (auth failure already seen this tick)")
    max_retries = 6
    for attempt in range(max_retries):
        throttle_s = _gate.acquire()

        api_start = time.monotonic()
        try:
            resp = client.chat.complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            api_s = time.monotonic() - api_start
            with _stats_lock:
                _stats_calls    += 1
                _stats_throttle += throttle_s
                _stats_api      += api_s
            return resp
        except Exception as exc:
            err_str = repr(exc)
            is_auth_err   = "401" in err_str or "unauthorized" in err_str.lower() or "authentication" in err_str.lower()
            is_rate_limit = "429" in err_str or "rate" in str(exc).lower()
            is_server_err = any(c in err_str for c in ("500", "502", "503", "504", "unavailable"))
            is_timeout    = any(c in err_str for c in ("ReadTimeout", "ConnectTimeout", "TimeoutError", "timed out", "timeout"))
            if is_auth_err:
                if _gate.mark_auth_failed():
                    logger.error("Mistral 401 — invalid or exhausted API key. Stopping.")
                raise LLMAuthError(str(exc)) from exc
            if is_rate_limit and attempt == max_retries - 1:
                raise LLMRateLimitError(str(exc)) from exc
            if (is_rate_limit or is_server_err or is_timeout) and attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("Mistral error (attempt %d/%d) — backing off %ds: %s",
                               attempt + 1, max_retries, backoff, exc)
                time.sleep(backoff)
            else:
                raise
