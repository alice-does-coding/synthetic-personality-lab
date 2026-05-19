import logging
import threading
import time

from anthropic import Anthropic
from anthropic import APIStatusError, APIConnectionError, APITimeoutError, RateLimitError, AuthenticationError

from config import Config
from providers.base import LLMAuthError, LLMRateLimitError

logger = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────

_rl_lock = threading.Lock()
_rl_next = 0.0  # monotonic time when next call is allowed

# Auth-failure latch — set on first 401; bail in-flight workers without retrying.
_auth_failed = threading.Event()

_client_lock = threading.Lock()
_client = None


def reset_auth():
    _auth_failed.clear()


def _get_client():
    global _client
    with _client_lock:
        if _client is None:
            _client = Anthropic(api_key=Config.ANTHROPIC_API_KEY, timeout=120.0)
        return _client


def _split_system(messages):
    """Anthropic takes `system` as a separate kwarg, not a message role.
    Splits any role=system messages out of the list and joins them."""
    system_parts = []
    rest = []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m.get("content", ""))
        else:
            rest.append(m)
    system = "\n\n".join(s for s in system_parts if s) or None
    return system, rest


def chat(messages, max_tokens, temperature, model):
    """Call Anthropic Messages API.

    Returns plain string content (matches HF provider shape so llm.extract_text
    can route by provider).

    Raises LLMAuthError on 401. Raises LLMRateLimitError if retries exhausted on 429.
    """
    global _rl_next
    if _auth_failed.is_set():
        raise LLMAuthError("Anthropic API key invalid (auth failure already seen this tick)")

    system, msgs = _split_system(messages)
    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": msgs,
    }
    if system:
        kwargs["system"] = system

    client = _get_client()
    max_retries = 6
    for attempt in range(max_retries):
        with _rl_lock:
            now = time.monotonic()
            wait = _rl_next - now
            if wait > 0:
                time.sleep(wait)
            _rl_next = time.monotonic() + (1.0 / Config.ANTHROPIC_RATE_LIMIT)

        try:
            resp = client.messages.create(**kwargs)
        except AuthenticationError as exc:
            if not _auth_failed.is_set():
                logger.error("Anthropic 401 — invalid or exhausted API key. Stopping.")
                _auth_failed.set()
            raise LLMAuthError(str(exc)) from exc
        except RateLimitError as exc:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("Anthropic 429 rate limit (attempt %d/%d) — backing off %ds",
                               attempt + 1, max_retries, backoff)
                time.sleep(backoff)
                continue
            raise LLMRateLimitError(str(exc)) from exc
        except (APIConnectionError, APITimeoutError) as exc:
            if attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("Anthropic connection/timeout (attempt %d/%d) — backing off %ds: %s",
                               attempt + 1, max_retries, backoff, exc)
                time.sleep(backoff)
                continue
            raise
        except APIStatusError as exc:
            status = getattr(exc, "status_code", None)
            if status in (500, 502, 503, 504, 529) and attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("Anthropic %s (attempt %d/%d) — backing off %ds",
                               status, attempt + 1, max_retries, backoff)
                time.sleep(backoff)
                continue
            logger.error("Anthropic %s for model %s: %s", status, model, exc)
            raise

        # Concatenate text blocks; Claude responses can contain multiple blocks.
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
