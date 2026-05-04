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

    def _prune_key(self, key: str, cutoff: float) -> deque[float] | None:
        """Drop timestamps older than cutoff; evict the key entirely when empty.

        Must be called under self._lock. Returns the still-populated deque, or
        None if the key has been evicted — preventing the _calls dict from
        growing unbounded for bursty one-off sources (NAT-masked clients,
        scanners, etc.).
        """
        q = self._calls.get(key)
        if q is None:
            return None
        while q and q[0] < cutoff:
            q.popleft()
        if not q:
            del self._calls[key]
            return None
        return q

    def is_blocked(self, key: str) -> bool:
        """Return True if the key has exceeded the limit (check only, does not record)."""
        now = time.monotonic()
        with self._lock:
            q = self._prune_key(key, now - self._window)
            return q is not None and len(q) >= self._max

    def record(self, key: str) -> None:
        """Record one failed attempt for key."""
        now = time.monotonic()
        with self._lock:
            self._prune_key(key, now - self._window)
            self._calls[key].append(now)

    def retry_after(self, key: str) -> float:
        """Seconds until the oldest recorded attempt falls outside the window."""
        now = time.monotonic()
        with self._lock:
            q = self._prune_key(key, now - self._window)
            if q is None:
                return 0.0
            return max(0.0, q[0] + self._window - now)


# 5 failed login attempts per 15 minutes per IP
login_limiter = RateLimiter(max_calls=5, window_seconds=15 * 60)

# 30 WebSocket handshakes per minute per IP — covers typical reconnect storms
# (tab restore, laptop wake) but blocks scripted connection floods.
ws_connect_limiter = RateLimiter(max_calls=30, window_seconds=60)
