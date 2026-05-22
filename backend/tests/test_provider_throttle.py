import threading
import time

import pytest

from providers._throttle import ProviderGate


def test_acquire_serialises_calls_at_rate_limit():
    # 10 req/sec → calls spaced ~100ms apart
    gate = ProviderGate(rate_limit=10.0, name="test")

    start = time.monotonic()
    for _ in range(4):
        gate.acquire()
    elapsed = time.monotonic() - start

    # First call is free; the next three each wait ~0.1s. Allow scheduling slack.
    assert elapsed >= 0.25
    assert elapsed < 0.6


def test_acquire_is_thread_safe_serialised():
    gate = ProviderGate(rate_limit=20.0, name="test")
    timestamps = []
    lock = threading.Lock()

    def worker():
        gate.acquire()
        with lock:
            timestamps.append(time.monotonic())

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    timestamps.sort()
    deltas = [b - a for a, b in zip(timestamps, timestamps[1:])]
    # Each spacing should be at least ~1/20s = 50ms minus scheduling jitter
    assert all(d >= 0.04 for d in deltas), deltas


def test_auth_latch_lifecycle():
    gate = ProviderGate(rate_limit=100.0, name="test")
    assert not gate.is_auth_failed()

    assert gate.mark_auth_failed() is True   # first caller flips it
    assert gate.is_auth_failed()
    assert gate.mark_auth_failed() is False  # idempotent

    gate.reset_auth()
    assert not gate.is_auth_failed()
    assert gate.mark_auth_failed() is True


def test_auth_latch_is_per_instance():
    a = ProviderGate(rate_limit=100.0, name="a")
    b = ProviderGate(rate_limit=100.0, name="b")
    a.mark_auth_failed()
    assert a.is_auth_failed()
    assert not b.is_auth_failed()
