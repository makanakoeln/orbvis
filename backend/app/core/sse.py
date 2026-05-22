"""SSE subscription manager — replaces the WebSocket connection manager.

Each subscriber owns an ``asyncio.Queue`` of pre-formatted SSE messages. The
broadcast loop computes one delta per (board, auth_user) and ``put_nowait``s
into the matching subscriber queues — same fanout pattern as the previous
WebSocket manager, no extra fetch cost per subscriber.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Subscriber:
    auth_user: str | None
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=64))


class SubscriptionManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[Subscriber]] = {}

    def subscribe(self, board: str, auth_user: str | None) -> Subscriber:
        sub = Subscriber(auth_user=auth_user)
        self._subscribers.setdefault(board, set()).add(sub)
        logger.debug(
            "SSE subscribe board=%s user=%s total=%d",
            board,
            auth_user,
            len(self._subscribers[board]),
        )
        return sub

    def unsubscribe(self, board: str, sub: Subscriber) -> None:
        subs = self._subscribers.get(board, set())
        subs.discard(sub)
        if not subs:
            self._subscribers.pop(board, None)
        logger.debug("SSE unsubscribe board=%s remaining=%d", board, len(subs))

    def get_subscriber_count(self, board: str) -> int:
        return len(self._subscribers.get(board, ()))

    def get_subscribers_grouped(self, board: str) -> dict[str | None, list[Subscriber]]:
        groups: dict[str | None, list[Subscriber]] = {}
        for sub in self._subscribers.get(board, ()):
            groups.setdefault(sub.auth_user, []).append(sub)
        return groups

    def push(self, board: str, targets: list[Subscriber], message: str) -> None:
        """Put *message* into each target's queue, dropping the slowest if full.

        A full queue means the client is too slow to consume — better to drop
        the oldest pending payload than block the broadcast loop.
        """
        for sub in targets:
            try:
                sub.queue.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    sub.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    sub.queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("SSE queue still full after drop for board=%s", board)


manager = SubscriptionManager()
