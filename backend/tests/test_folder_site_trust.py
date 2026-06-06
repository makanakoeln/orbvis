"""Per-site trust: dead federation sites replay their last known foldertree
host rows (marked stale) instead of silently vanishing from the tree."""

from __future__ import annotations

import pytest

from app.connections import livestatus as ls_mod
from app.connections.livestatus import LivestatusConnection


def _row(name: str) -> list:
    # name filename state plugin_output ack downtime ok warn crit unk pend flap last_change
    return [name, "/wato/dc/hosts.mk", 0, "OK", 0, 0, 5, 0, 0, 0, 0, 0, 1000.0]


@pytest.mark.asyncio
async def test_dead_site_hosts_replay_as_stale(monkeypatch):
    conn = LivestatusConnection(socket_path="/dev/null")
    conn._sites = {"central": {}, "remote": {}}

    async def _no_folders():
        return []

    monkeypatch.setattr(ls_mod, "_load_wato_folders", _no_folders)

    ticks = [
        [("central", _row("c1")), ("remote", _row("r1"))],
        [("central", _row("c1"))],
    ]

    async def _fake_query(_lql: str):
        return ticks.pop(0)

    monkeypatch.setattr(conn, "_query_with_site", _fake_query)

    # Tick 1: both sites answer — nothing stale, nothing dead.
    data = await conn.get_folder_tree()
    assert data.dead_sites == []
    assert {h["host_name"] for h in data.hosts} == {"c1", "r1"}
    assert not any(h.get("stale") for h in data.hosts)

    # Tick 2: remote died — its host rows replay from the cache, marked stale.
    conn._mc_dead = {"remote"}
    data = await conn.get_folder_tree()
    assert data.dead_sites == ["remote"]
    by_name = {h["host_name"]: h for h in data.hosts}
    assert set(by_name) == {"c1", "r1"}
    assert by_name["r1"].get("stale") is True
    assert by_name["r1"]["site_id"] == "remote"
    assert not by_name["c1"].get("stale")


@pytest.mark.asyncio
async def test_single_site_never_reports_dead_sites(monkeypatch):
    conn = LivestatusConnection(socket_path="/dev/null")

    async def _no_folders():
        return []

    monkeypatch.setattr(ls_mod, "_load_wato_folders", _no_folders)

    async def _fake_query(_lql: str):
        return [(None, _row("h1"))]

    monkeypatch.setattr(conn, "_query_with_site", _fake_query)
    conn._mc_dead = {"ghost"}  # leftover state must be ignored without federation
    data = await conn.get_folder_tree()
    assert data.dead_sites == []
    assert not any(h.get("stale") for h in data.hosts)


@pytest.mark.asyncio
async def test_replay_cache_is_auth_scoped(monkeypatch):
    """A contact-scoped user must never receive another scope's cached rows —
    the replay cache is keyed by the livestatus auth context."""
    from app.connections.livestatus import _auth_user_ctx

    conn = LivestatusConnection(socket_path="/dev/null")
    conn._sites = {"central": {}, "remote": {}}

    async def _no_folders():
        return []

    monkeypatch.setattr(ls_mod, "_load_wato_folders", _no_folders)

    ticks = [
        [("central", _row("c1")), ("remote", _row("r1"))],  # admin, both alive
        [("central", _row("c1"))],  # scoped user, remote already dead
    ]

    async def _fake_query(_lql: str):
        return ticks.pop(0)

    monkeypatch.setattr(conn, "_query_with_site", _fake_query)

    # Unscoped (admin) fetch fills the unscoped cache slot.
    await conn.get_folder_tree()
    conn._mc_dead = {"remote"}

    # Scoped user has no cached rows for the dead site → nothing replayed,
    # but the dead site is still reported for the banner.
    token = _auth_user_ctx.set("scoped_user")
    try:
        data = await conn.get_folder_tree()
    finally:
        _auth_user_ctx.reset(token)
    assert data.dead_sites == ["remote"]
    assert {h["host_name"] for h in data.hosts} == {"c1"}
    assert not any(h.get("stale") for h in data.hosts)
