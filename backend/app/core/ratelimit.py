"""A tiny in-process, per-IP rate limiter for the auth endpoints.

Fixed-window-ish (sliding) counter kept in memory. Fine for a single instance;
swap for a Redis-backed limiter when running multiple workers.
"""

from __future__ import annotations

import time

from fastapi import HTTPException, Request, status

from app.core.config import settings


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max = max_calls
        self.window = window_seconds
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = [t for t in self._hits.get(key, ()) if now - t < self.window]
        if len(hits) >= self.max:
            self._hits[key] = hits
            return False
        hits.append(now)
        self._hits[key] = hits
        return True


def rate_limit(max_calls: int, window_seconds: float, name: str):
    """Dependency factory — limits ``max_calls`` per ``window_seconds`` per client IP."""
    limiter = RateLimiter(max_calls, window_seconds)

    def _dep(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        host = request.client.host if request.client else "unknown"
        if not limiter.allow(f"{name}:{host}"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts — please wait a moment and try again.",
            )

    return _dep
