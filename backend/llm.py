"""Provider-agnostic LLM router.

All simulation code calls these functions instead of touching provider
SDKs directly. The provider and model are stored on the Run record.

One run = one model. On auth failure the call raises LLMAuthError and
the calling layer (engine, simulation_run) stops the run cleanly — no
silent fallback to another provider, which would contaminate the data.
"""
from providers.base import LLMAuthError, LLMRateLimitError  # re-export for callers

__all__ = ["chat", "chat_ipip", "extract_text", "generate_avatar", "reset_auth_latches", "LLMAuthError", "LLMRateLimitError"]


def reset_auth_latches(tick=None, retry_interval=12):
    """Reset per-tick stats. Auth latch is only cleared every retry_interval ticks
    so a bad provider key doesn't waste a call on every single tick."""
    from providers.mistral import reset_stats
    from providers.hf import reset_auth as reset_hf_auth
    from providers.anthropic import reset_auth as reset_anthropic_auth
    clear_latch = (tick is None) or (tick % retry_interval == 0)
    reset_stats(clear_auth_latch=clear_latch)
    reset_hf_auth()
    reset_anthropic_auth()


def chat(provider, model, messages, max_tokens, temperature):
    """Route a chat call to the correct provider. No fallback.

    Returns:
        str for HF and Anthropic (plain string content).
        Mistral response object for mistral (caller must use extract_text).

    Raises LLMAuthError on 401 — caller is expected to stop the run.
    """
    if provider == "hf":
        from providers.hf import chat as hf_chat
        return hf_chat(messages, max_tokens, temperature, model=model)
    elif provider == "anthropic":
        from providers.anthropic import chat as anthropic_chat
        return anthropic_chat(messages, max_tokens, temperature, model=model)
    else:  # default: mistral
        from providers.mistral import make_client, chat as mistral_chat
        client = make_client()
        return mistral_chat(client, messages, max_tokens, temperature, model=model)


def chat_ipip(provider, model, messages, max_tokens, temperature):
    """IPIP variant — longer timeout for Mistral, same for HF/Anthropic. No fallback."""
    if provider == "hf":
        from providers.hf import chat as hf_chat
        return hf_chat(messages, max_tokens, temperature, model=model)
    elif provider == "anthropic":
        from providers.anthropic import chat as anthropic_chat
        return anthropic_chat(messages, max_tokens, temperature, model=model)
    else:
        from providers.mistral import make_ipip_client, chat as mistral_chat
        client = make_ipip_client()
        return mistral_chat(client, messages, max_tokens, temperature, model=model)


def generate_avatar(provider, bio, name=None):
    """Generate a profile image from a bio. Currently HF-only (FLUX).
    Returns a base64 data URL or None."""
    from providers.hf import generate_avatar as hf_avatar
    return hf_avatar(bio, name=name)


def extract_text(provider, content):
    """Extract a plain string from provider response content.

    HF and Anthropic return plain strings already. Mistral returns str | list[TextChunk].
    """
    if provider in ("hf", "anthropic"):
        return content if isinstance(content, str) else ""
    else:
        from providers.mistral import extract_text as mistral_extract
        return mistral_extract(content)
