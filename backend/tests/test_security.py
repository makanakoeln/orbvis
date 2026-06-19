"""Unit tests for the stream-ticket factory and the in-memory token blocklist.

Covers only the deployment-agnostic pieces of ``app.core.security``: the
short-lived stream ticket (used for SSE/tile URLs that cannot send an
Authorization header) and the per-process logout blocklist. The bcrypt
password helpers belong to the native-auth path and are intentionally left
out here.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest

from app.core import security


@pytest.fixture(autouse=True)
def _clear_blocklist() -> Iterator[None]:
    """The blocklist is module-global; isolate every test from its neighbours."""
    with security._blocklist_lock:
        security._blocklist.clear()
    yield
    with security._blocklist_lock:
        security._blocklist.clear()


# ---------------------------------------------------------------------------
# create_stream_ticket
# ---------------------------------------------------------------------------


class TestStreamTicket:
    def test_payload_marks_subject_and_stream_type(self) -> None:
        token = security.create_stream_ticket("42")
        decoded = security.decode_token(token)
        assert decoded["sub"] == "42"
        assert decoded["type"] == "stream"
        assert decoded["jti"]

    def test_integer_subject_is_stringified(self) -> None:
        decoded = security.decode_token(security.create_stream_ticket(7))
        assert decoded["sub"] == "7"

    def test_expiry_matches_five_minute_ttl(self) -> None:
        before = datetime.now(UTC)
        decoded = security.decode_token(security.create_stream_ticket("1"))
        exp_raw = decoded["exp"]
        assert isinstance(exp_raw, int)
        exp = datetime.fromtimestamp(exp_raw, UTC)
        delta = exp - before
        # TTL is 5 minutes; allow a second of slack for the clock between calls.
        assert security.STREAM_TICKET_TTL - timedelta(seconds=2) <= delta
        assert delta <= security.STREAM_TICKET_TTL + timedelta(seconds=2)

    def test_each_ticket_has_a_unique_jti(self) -> None:
        a = security.decode_token(security.create_stream_ticket("1"))
        b = security.decode_token(security.create_stream_ticket("1"))
        assert a["jti"] != b["jti"]

    def test_ticket_type_differs_from_access_and_refresh(self) -> None:
        stream = security.decode_token(security.create_stream_ticket("1"))["type"]
        access = security.decode_token(security.create_access_token("1"))["type"]
        refresh = security.decode_token(security.create_refresh_token("1"))["type"]
        assert stream == "stream"
        assert access == "access"
        assert refresh == "refresh"


# ---------------------------------------------------------------------------
# Token blocklist
# ---------------------------------------------------------------------------


class TestBlocklist:
    def test_blocked_token_is_reported_blocked(self) -> None:
        future = datetime.now(UTC) + timedelta(minutes=10)
        security.blocklist_token("jti-active", future)
        assert security.is_token_blocked("jti-active") is True

    def test_unknown_token_is_not_blocked(self) -> None:
        assert security.is_token_blocked("never-seen") is False

    def test_expired_entry_is_pruned_on_read(self) -> None:
        past = datetime.now(UTC) - timedelta(seconds=1)
        security.blocklist_token("jti-expired", past)
        # Pruning happens on read too, so an expired token reports unblocked
        # and is dropped from the store.
        assert security.is_token_blocked("jti-expired") is False
        with security._blocklist_lock:
            assert "jti-expired" not in security._blocklist

    def test_expired_entry_is_pruned_when_adding_another(self) -> None:
        security.blocklist_token("old", datetime.now(UTC) - timedelta(seconds=1))
        security.blocklist_token("new", datetime.now(UTC) + timedelta(minutes=5))
        with security._blocklist_lock:
            assert "old" not in security._blocklist
            assert "new" in security._blocklist

    def test_active_entries_survive_pruning(self) -> None:
        future = datetime.now(UTC) + timedelta(minutes=5)
        security.blocklist_token("keep-1", future)
        security.blocklist_token("keep-2", future)
        security._prune_blocklist()
        assert security.is_token_blocked("keep-1") is True
        assert security.is_token_blocked("keep-2") is True

    def test_reblocking_updates_expiry(self) -> None:
        security.blocklist_token("jti", datetime.now(UTC) + timedelta(seconds=30))
        new_exp = datetime.now(UTC) + timedelta(hours=1)
        security.blocklist_token("jti", new_exp)
        with security._blocklist_lock:
            assert security._blocklist["jti"] == new_exp
