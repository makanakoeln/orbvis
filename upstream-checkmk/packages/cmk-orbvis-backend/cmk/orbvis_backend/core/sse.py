#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""SSE subscription manager — replaces the WebSocket connection manager.

Each subscriber owns an ``asyncio.Queue`` of pre-formatted SSE messages. The
broadcast loop computes one delta per (map, auth_user) and ``put_nowait``s
into the matching subscriber queues — same fanout pattern as the previous
WebSocket manager, no extra fetch cost per subscriber.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cmk.orbvis_backend.integrations.checkmk import FolderScope

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Subscriber:
    # ``auth_user`` is the Livestatus monitoring scope (None = see all hosts).
    # ``folder_scope`` is the independent SETUP-folder read scope. ``group_key``
    # collapses both into one identity so subscribers that would render the SAME
    # map share a single computation+delta — for foldertree maps admin and a
    # see-all guest have the same auth_user (None) but different folder_scope, so
    # the key keeps them apart; for other maps it is just the auth_user.
    auth_user: str | None
    folder_scope: FolderScope | None = None
    group_key: str | None = None
    queue: asyncio.Queue[str] = field(default_factory=lambda: asyncio.Queue(maxsize=64))


class SubscriptionManager:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[Subscriber]] = {}

    def subscribe(
        self,
        map: str,
        auth_user: str | None,
        folder_scope: FolderScope | None = None,
        group_key: str | None = None,
    ) -> Subscriber:
        sub = Subscriber(
            auth_user=auth_user,
            folder_scope=folder_scope,
            group_key=group_key if group_key is not None else auth_user,
        )
        self._subscribers.setdefault(map, set()).add(sub)
        logger.debug(
            "SSE subscribe map=%s user=%s key=%s total=%d",
            map,
            auth_user,
            sub.group_key,
            len(self._subscribers[map]),
        )
        return sub

    def unsubscribe(self, map: str, sub: Subscriber) -> None:
        subs = self._subscribers.get(map, set())
        subs.discard(sub)
        if not subs:
            self._subscribers.pop(map, None)
        logger.debug("SSE unsubscribe map=%s remaining=%d", map, len(subs))

    def get_subscriber_count(self, map: str) -> int:
        return len(self._subscribers.get(map, ()))

    def get_subscribers_grouped(self, map: str) -> dict[str | None, list[Subscriber]]:
        # Grouped by ``group_key`` (auth_user + folder scope), not auth_user alone,
        # so users with different rendered output (e.g. admin vs see-all guest on a
        # foldertree map) get their own computation + delta stream.
        groups: dict[str | None, list[Subscriber]] = {}
        for sub in self._subscribers.get(map, ()):
            groups.setdefault(sub.group_key, []).append(sub)
        return groups

    def push(self, map: str, targets: list[Subscriber], message: str) -> None:
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
                    logger.warning("SSE queue still full after drop for map=%s", map)


manager = SubscriptionManager()
