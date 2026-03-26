"""Simple in-memory rate limiter (no external dependencies)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Sliding-window rate limiter keyed by arbitrary string (e.g. client IP).

    Thread-safe; suitable for single-process deployments.
    """

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_blocked(self, key: str) -> bool:
        """Return True if the key has exceeded the limit (check only, does not record)."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            q = self._calls[key]
            while q and q[0] < cutoff:
                q.popleft()
            return len(q) >= self._max

    def record(self, key: str) -> None:
        """Record one event for key (call after a failed attempt)."""
        now = time.monotonic()
        cutoff = now - self._window
        with self._lock:
            q = self._calls[key]
            while q and q[0] < cutoff:
                q.popleft()
            q.append(now)

    def retry_after(self, key: str) -> float:
        """Seconds until the oldest call in the window expires."""
        now = time.monotonic()
        with self._lock:
            q = self._calls.get(key)
            if not q:
                return 0.0
            return max(0.0, q[0] + self._window - now)


# 5 failed login attempts per 15 minutes per IP
login_limiter = RateLimiter(max_calls=5, window_seconds=15 * 60)
