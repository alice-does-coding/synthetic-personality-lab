"""Shared rate-limiter + auth-failure latch used by every LLM provider.

The throttle gate serialises all in-flight workers through a per-provider lock
so calls leave at most `rate_limit` requests per second. The auth latch flips
on the first observed 401 in a tick so other concurrent workers bail without
making their own redundant HTTP calls; ``reset_auth()`` lets the caller decide
when to retry (typically on tick boundaries via ``llm.reset_auth_latches``).
"""
import threading
import time


class ProviderGate:
    def __init__(self, rate_limit, name):
        self.rate_limit = rate_limit
        self.name = name
        self._rl_lock = threading.Lock()
        self._rl_next = 0.0  # monotonic time when the next call is allowed
        self._auth_failed = threading.Event()

    def acquire(self):
        """Block until the rate limit allows the next call. Returns the seconds slept."""
        with self._rl_lock:
            now = time.monotonic()
            wait = self._rl_next - now
            if wait > 0:
                time.sleep(wait)
                slept = wait
            else:
                slept = 0.0
            self._rl_next = time.monotonic() + (1.0 / self.rate_limit)
        return slept

    def is_auth_failed(self):
        return self._auth_failed.is_set()

    def mark_auth_failed(self):
        """Idempotent. Returns True if this caller flipped the latch (use for one-shot logging)."""
        if self._auth_failed.is_set():
            return False
        self._auth_failed.set()
        return True

    def reset_auth(self):
        self._auth_failed.clear()
