"""Tests for the async ConnectionBase methods of ``Icinga2Connection``.

The pure helpers live in ``test_icinga2_parsers.py``; here we exercise the
state-translation methods by stubbing ``_get_results`` so no Icinga2 REST API
is touched. Both the happy path and the not-found / transport-error fallbacks
are covered.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.connections.icinga2 import Icinga2Connection


def _conn() -> Icinga2Connection:
    return Icinga2Connection(url="https://icinga.test", username="u", password="p")


def _stub_results(conn: Icinga2Connection, results: list[dict[str, Any]]) -> None:
    conn._get_results = AsyncMock(return_value=results)  # type: ignore[method-assign]


def _stub_raises(conn: Icinga2Connection) -> None:
    conn._get_results = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# get_host_state
# ---------------------------------------------------------------------------


class TestGetHostState:
    async def test_maps_state_and_flags(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [
                {
                    "attrs": {
                        "state": 1,
                        "last_check_result": {"output": "host down"},
                        "acknowledgement": 1,
                        "downtime_depth": 2,
                        "address": "10.0.0.1",
                        "state_type": 1,
                    }
                }
            ],
        )
        state = await conn.get_host_state("web01")
        assert state.state == "DOWN"
        assert state.output == "host down"
        assert state.acknowledged is True
        assert state.in_downtime is True
        assert state.address == "10.0.0.1"
        assert state.state_type == "HARD"

    @pytest.mark.parametrize(
        ("state_int", "expected"),
        [(0, "UP"), (1, "DOWN"), (2, "UNREACHABLE"), (99, "UNREACHABLE")],
    )
    async def test_state_integer_translation(self, state_int: int, expected: str) -> None:
        conn = _conn()
        _stub_results(conn, [{"attrs": {"state": state_int}}])
        assert (await conn.get_host_state("h")).state == expected

    async def test_not_found_returns_unreachable_with_message(self) -> None:
        conn = _conn()
        _stub_results(conn, [])
        state = await conn.get_host_state("ghost")
        assert state.state == "UNREACHABLE"
        assert "ghost" in (state.output or "")
        assert state.stale is False

    async def test_transport_error_returns_stale(self) -> None:
        conn = _conn()
        _stub_raises(conn)
        state = await conn.get_host_state("web01")
        assert state.state == "UNREACHABLE"
        assert state.stale is True


# ---------------------------------------------------------------------------
# get_service_state
# ---------------------------------------------------------------------------


class TestGetServiceState:
    async def test_maps_state_output_and_perfdata(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [
                {
                    "attrs": {
                        "state": 2,
                        "last_check_result": {
                            "output": "CRIT",
                            "performance_data": ["rta=5ms", "pl=0%"],
                        },
                        "acknowledgement": 0,
                        "downtime_depth": 0,
                    }
                }
            ],
        )
        state = await conn.get_service_state("web01", "ping")
        assert state.state == "CRITICAL"
        assert state.output == "CRIT"
        assert state.perf_data == "rta=5ms pl=0%"
        assert state.acknowledged is False

    async def test_non_list_perfdata_yields_empty_string(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [{"attrs": {"state": 0, "last_check_result": {"performance_data": None}}}],
        )
        state = await conn.get_service_state("web01", "ping")
        assert state.state == "OK"
        assert state.perf_data == ""

    async def test_not_found_returns_unknown(self) -> None:
        conn = _conn()
        _stub_results(conn, [])
        state = await conn.get_service_state("web01", "ghost")
        assert state.state == "UNKNOWN"
        assert "ghost" in (state.output or "")

    async def test_transport_error_returns_stale(self) -> None:
        conn = _conn()
        _stub_raises(conn)
        state = await conn.get_service_state("web01", "ping")
        assert state.state == "UNKNOWN"
        assert state.stale is True


# ---------------------------------------------------------------------------
# Group aggregation
# ---------------------------------------------------------------------------


class TestGroupStates:
    async def test_hostgroup_reports_worst_member(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [{"attrs": {"state": 0}}, {"attrs": {"state": 2}}, {"attrs": {"state": 0}}],
        )
        state = await conn.get_hostgroup_states("dc1")
        assert state.state == "UNREACHABLE"
        assert "3 hosts" in (state.output or "")

    async def test_empty_hostgroup_is_pending(self) -> None:
        conn = _conn()
        _stub_results(conn, [])
        state = await conn.get_hostgroup_states("dc1")
        assert state.state == "PENDING"

    async def test_servicegroup_reports_worst_member(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [{"attrs": {"state": 1}}, {"attrs": {"state": 2}}],
        )
        state = await conn.get_servicegroup_states("db")
        assert state.state == "CRITICAL"
        assert "2 services" in (state.output or "")

    async def test_servicegroup_error_is_stale_unknown(self) -> None:
        conn = _conn()
        _stub_raises(conn)
        state = await conn.get_servicegroup_states("db")
        assert state.state == "UNKNOWN"
        assert state.stale is True


# ---------------------------------------------------------------------------
# Object listing
# ---------------------------------------------------------------------------


class TestGetObjects:
    async def test_lists_host_names(self) -> None:
        conn = _conn()
        _stub_results(conn, [{"attrs": {"name": "web01"}}, {"attrs": {"name": "web02"}}])
        assert await conn.get_objects("host") == ["web01", "web02"]

    async def test_service_names_are_host_qualified(self) -> None:
        conn = _conn()
        _stub_results(conn, [{"attrs": {"host_name": "web01", "name": "ping"}}])
        assert await conn.get_objects("service") == ["web01;ping"]

    async def test_search_filters_on_service_description(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [
                {"attrs": {"host_name": "web01", "name": "ping"}},
                {"attrs": {"host_name": "web01", "name": "cpu load"}},
            ],
        )
        assert await conn.get_objects("service", search="CPU") == ["web01;cpu load"]

    async def test_unknown_object_type_returns_empty(self) -> None:
        conn = _conn()
        _stub_results(conn, [{"attrs": {"name": "web01"}}])
        assert await conn.get_objects("nonsense") == []

    async def test_error_returns_empty(self) -> None:
        conn = _conn()
        _stub_raises(conn)
        assert await conn.get_objects("host") == []


# ---------------------------------------------------------------------------
# Group members
# ---------------------------------------------------------------------------


class TestGroupMembers:
    async def test_all_hosts(self) -> None:
        conn = _conn()
        _stub_results(conn, [{"attrs": {"name": "web01"}}, {"attrs": {"name": "web02"}}])
        assert await conn.get_group_members("all_hosts", "") == ["web01", "web02"]

    async def test_servicegroup_members_are_host_qualified(self) -> None:
        conn = _conn()
        _stub_results(conn, [{"attrs": {"host_name": "web01", "name": "ping"}}])
        assert await conn.get_group_members("servicegroup", "net") == ["web01;ping"]

    async def test_unknown_group_type_returns_empty(self) -> None:
        conn = _conn()
        _stub_results(conn, [{"attrs": {"name": "web01"}}])
        assert await conn.get_group_members("bogus", "x") == []


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------


class TestTopology:
    async def test_builds_nodes_with_parents(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [
                {
                    "attrs": {
                        "name": "web01",
                        "state": 0,
                        "last_check_result": {"output": "ok"},
                        "vars": {"parents": ["core01", "core02"]},
                    }
                }
            ],
        )
        nodes = await conn.get_topology()
        assert len(nodes) == 1
        assert nodes[0]["name"] == "web01"
        assert nodes[0]["parents"] == ["core01", "core02"]
        assert nodes[0]["state"] == "UP"
        assert nodes[0]["output"] == "ok"

    async def test_scalar_parent_is_wrapped_in_list(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [{"attrs": {"name": "web01", "state": 1, "vars": {"parents": "core01"}}}],
        )
        nodes = await conn.get_topology()
        assert nodes[0]["parents"] == ["core01"]
        assert nodes[0]["state"] == "DOWN"

    async def test_error_returns_empty(self) -> None:
        conn = _conn()
        _stub_raises(conn)
        assert await conn.get_topology() == []


# ---------------------------------------------------------------------------
# Host services
# ---------------------------------------------------------------------------


class TestHostServices:
    async def test_lists_services_with_state(self) -> None:
        conn = _conn()
        _stub_results(
            conn,
            [
                {"attrs": {"name": "ping", "state": 0, "last_check_result": {"output": "ok"}}},
                {"attrs": {"name": "cpu", "state": 2, "last_check_result": {"output": "crit"}}},
            ],
        )
        rows = await conn.get_host_services("web01")
        assert [(r["name"], r["state"]) for r in rows] == [("ping", "OK"), ("cpu", "CRITICAL")]

    async def test_error_returns_empty(self) -> None:
        conn = _conn()
        _stub_raises(conn)
        assert await conn.get_host_services("web01") == []
