class LLMError(Exception):
    pass


class LLMAuthError(LLMError):
    """Raised on auth failure (401/unauthorized). Run should be stopped."""


class LLMRateLimitError(LLMError):
    """Raised on rate limit — caller should back off."""
