"""The in-process per-key rate limiter."""

from __future__ import annotations

from app.core.ratelimit import RateLimiter


def test_allows_up_to_max_then_blocks():
    rl = RateLimiter(max_calls=3, window_seconds=60)
    assert [rl.allow("k") for _ in range(3)] == [True, True, True]
    assert rl.allow("k") is False  # the 4th call in the window is blocked


def test_budget_is_per_key():
    rl = RateLimiter(max_calls=1, window_seconds=60)
    assert rl.allow("a") is True
    assert rl.allow("a") is False
    assert rl.allow("b") is True  # a different key has its own budget
