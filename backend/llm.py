"""Provider-agnostic LLM router.

All simulation code calls these functions instead of touching provider
SDKs directly. The provider and model are stored on the Run record.
"""
from providers.base import LLMAuthError, LLMRateLimitError  # re-export for callers

__all__ = ["chat", "chat_ipip", "extract_text", "generate_avatar", "reset_auth_latches", "LLMAuthError", "LLMRateLimitError"]


def reset_auth_latches(tick=None, retry_interval=12):
    """Reset per-tick stats. Auth latch is only cleared every retry_interval ticks
    so a bad Mistral key doesn't waste a call on every single tick."""
    from providers.mistral import reset_stats
    from providers.hf import reset_auth
    clear_latch = (tick is None) or (tick % retry_interval == 0)
    reset_stats(clear_auth_latch=clear_latch)
    reset_auth()


def _hf_fallback(messages, max_tokens, temperature):
    """Fall back to HF when the primary provider is unavailable."""
    import logging
    from config import Config
    from providers.hf import chat as hf_chat
    logging.getLogger(__name__).warning("primary provider unavailable — falling back to HF (%s)", Config.HF_CHAT_MODEL)
    return hf_chat(messages, max_tokens, temperature, model=Config.HF_CHAT_MODEL)


def chat(provider, model, messages, max_tokens, temperature):
    """Route a chat call to the correct provider.

    Falls back to HF automatically on auth failure so the simulation keeps running
    even when the primary provider (Mistral) has a billing/key issue.

    Returns:
        str for HF (plain string content).
        Mistral response object for mistral (caller must use extract_text).

    Raises LLMAuthError only if both primary and fallback fail.
    """
    if provider == "hf":
        from providers.hf import chat as hf_chat
        return hf_chat(messages, max_tokens, temperature, model=model)
    else:  # default: mistral
        try:
            from providers.mistral import make_client, chat as mistral_chat
            client = make_client()
            return mistral_chat(client, messages, max_tokens, temperature, model=model)
        except LLMAuthError:
            return _hf_fallback(messages, max_tokens, temperature)


def chat_ipip(provider, model, messages, max_tokens, temperature):
    """IPIP variant — longer timeout for Mistral, same for HF."""
    if provider == "hf":
        from providers.hf import chat as hf_chat
        return hf_chat(messages, max_tokens, temperature, model=model)
    else:
        try:
            from providers.mistral import make_ipip_client, chat as mistral_chat
            client = make_ipip_client()
            return mistral_chat(client, messages, max_tokens, temperature, model=model)
        except LLMAuthError:
            return _hf_fallback(messages, max_tokens, temperature)


def generate_avatar(provider, bio, name=None):
    """Generate a profile image from a bio. Currently HF-only (FLUX).
    Returns a base64 data URL or None."""
    from providers.hf import generate_avatar as hf_avatar
    return hf_avatar(bio, name=name)


def extract_text(provider, content):
    """Extract a plain string from provider response content.

    HF returns plain strings already. Mistral returns str | list[TextChunk].
    """
    if provider == "hf":
        return content if isinstance(content, str) else ""
    else:
        from providers.mistral import extract_text as mistral_extract
        return mistral_extract(content)
