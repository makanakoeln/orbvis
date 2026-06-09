"""Unit tests for the SSE SubscriptionManager.

Covers subscriber bookkeeping, the group_key collapsing that decides which
subscribers share one delta computation, and the drop-oldest backpressure in
``push`` when a slow client's queue is full.
"""

from __future__ import annotations

import asyncio

from app.core.sse import Subscriber, SubscriptionManager


class TestSubscribeUnsubscribe:
    def test_subscribe_tracks_and_counts(self) -> None:
        mgr = SubscriptionManager()
        sub = mgr.subscribe("board1", "alice")
        assert mgr.get_subscriber_count("board1") == 1
        # group_key defaults to auth_user when not given explicitly.
        assert sub.group_key == "alice"

    def test_explicit_group_key_is_kept(self) -> None:
        mgr = SubscriptionManager()
        sub = mgr.subscribe("board1", None, group_key="admin-folderscope")
        assert sub.group_key == "admin-folderscope"

    def test_unsubscribe_removes_and_drops_empty_board(self) -> None:
        mgr = SubscriptionManager()
        sub = mgr.subscribe("board1", "alice")
        mgr.unsubscribe("board1", sub)
        assert mgr.get_subscriber_count("board1") == 0
        # Board key removed entirely once the last subscriber leaves.
        assert "board1" not in mgr._subscribers

    def test_unsubscribe_unknown_is_noop(self) -> None:
        mgr = SubscriptionManager()
        mgr.unsubscribe("ghost", Subscriber(auth_user="x"))
        assert mgr.get_subscriber_count("ghost") == 0


class TestGroupedSubscribers:
    def test_same_auth_user_different_group_key_split(self) -> None:
        # Foldertree board: admin and a see-all guest share auth_user None but
        # render differently, so distinct group_keys keep them in separate groups.
        mgr = SubscriptionManager()
        mgr.subscribe("board1", None, group_key="admin")
        mgr.subscribe("board1", None, group_key="guest")
        groups = mgr.get_subscribers_grouped("board1")
        assert set(groups) == {"admin", "guest"}
        assert all(len(v) == 1 for v in groups.values())

    def test_same_group_key_shares_one_group(self) -> None:
        mgr = SubscriptionManager()
        mgr.subscribe("board1", "user1")
        mgr.subscribe("board1", "user1")
        groups = mgr.get_subscribers_grouped("board1")
        assert set(groups) == {"user1"}
        assert len(groups["user1"]) == 2

    def test_empty_board_yields_no_groups(self) -> None:
        assert SubscriptionManager().get_subscribers_grouped("none") == {}


class TestPush:
    def test_delivers_message_to_each_target(self) -> None:
        mgr = SubscriptionManager()
        a = mgr.subscribe("board1", "a")
        b = mgr.subscribe("board1", "b")
        mgr.push("board1", [a, b], "data: x\n\n")
        assert a.queue.get_nowait() == "data: x\n\n"
        assert b.queue.get_nowait() == "data: x\n\n"

    def test_full_queue_drops_oldest(self) -> None:
        # A slow client whose queue is full must lose the OLDEST payload, not
        # block the broadcast loop, and still receive the newest one.
        sub = Subscriber(auth_user="slow", queue=asyncio.Queue(maxsize=1))
        sub.queue.put_nowait("old")
        mgr = SubscriptionManager()
        mgr.push("board1", [sub], "new")
        assert sub.queue.get_nowait() == "new"
        assert sub.queue.empty()
