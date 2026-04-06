"""Provider-agnostic LLM router.

All simulation code calls these functions instead of touching provider
SDKs directly. The provider and model are stored on the Run record.
"""
from providers.base import LLMAuthError, LLMRateLimitError  # re-export for callers

__all__ = ["chat", "chat_ipip", "extract_text", "generate_avatar", "reset_auth_latches", "LLMAuthError", "LLMRateLimitError"]


def reset_auth_latches():
    """Clear per-provider auth-failure latches. Called at the start of each tick."""
    from providers.mistral import reset_stats   # reset_stats also clears the latch
    from providers.hf import reset_auth
    reset_stats()
    reset_auth()


def chat(provider, model, messages, max_tokens, temperature):
    """Route a chat call to the correct provider.

    Returns:
        str for HF (plain string content).
        Mistral response object for mistral (caller must use extract_text).

    Raises LLMAuthError on fatal auth failure.
    """
    if provider == "hf":
        from providers.hf import chat as hf_chat
        return hf_chat(messages, max_tokens, temperature, model=model)
    else:  # default: mistral
        from providers.mistral import make_client, chat as mistral_chat
        client = make_client()
        return mistral_chat(client, messages, max_tokens, temperature, model=model)


def chat_ipip(provider, model, messages, max_tokens, temperature):
    """IPIP variant — longer timeout for Mistral, same for HF."""
    if provider == "hf":
        from providers.hf import chat as hf_chat
        return hf_chat(messages, max_tokens, temperature, model=model)
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

    HF returns plain strings already. Mistral returns str | list[TextChunk].
    """
    if provider == "hf":
        return content if isinstance(content, str) else ""
    else:
        from providers.mistral import extract_text as mistral_extract
        return mistral_extract(content)
