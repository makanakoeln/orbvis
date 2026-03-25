"""Tests for state aggregation logic in state_service."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.schemas.board import BoardConfig, BoardObject, StaticView
from app.schemas.state import ObjectState
from app.services import state_service
from app.services.state_service import (
    _aggregate_host_with_services_from_data,
    get_backend,
    get_backend_objects,
    get_board_states,
    register_backend,
)


def _host_state(object_id: str, state: str) -> ObjectState:
    return ObjectState(object_id=object_id, type="host", state=state)


def _svc_state(object_id: str, state: str) -> ObjectState:
    return ObjectState(object_id=object_id, type="service", state=state)


def _board(objects: list[BoardObject], backend_id: str = "mock") -> BoardConfig:
    return BoardConfig(
        name="test", alias="Test", backend_id=backend_id, view=StaticView(), objects=objects
    )


def _obj(id: str, type: str = "host", **kwargs) -> BoardObject:
    return BoardObject(id=id, type=type, **kwargs)


# ---------------------------------------------------------------------------
# register_backend / get_backend
# ---------------------------------------------------------------------------


def test_register_and_get_backend(mock_backend, monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {})
    register_backend("mybackend", mock_backend)
    assert get_backend("mybackend") is mock_backend


def test_get_backend_not_found(monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {})
    assert get_backend("nonexistent") is None


# ---------------------------------------------------------------------------
# get_backend_objects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_backend_objects_no_backend(monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {})
    result = await get_backend_objects("missing", "host")
    assert result == []


@pytest.mark.asyncio
async def test_get_backend_objects_returns_list(mock_backend, monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {"mock": mock_backend})
    mock_backend.get_objects = AsyncMock(return_value=["host1", "host2"])
    result = await get_backend_objects("mock", "host")
    assert result == ["host1", "host2"]


@pytest.mark.asyncio
async def test_get_backend_objects_service_filter(mock_backend, monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {"mock": mock_backend})
    mock_backend.get_objects = AsyncMock(return_value=["srv1;CPU", "srv1;RAM", "srv2;CPU"])
    result = await get_backend_objects("mock", "service", host="srv1")
    assert result == ["CPU", "RAM"]


# ---------------------------------------------------------------------------
# _aggregate_host_with_services_from_data — pure logic
# ---------------------------------------------------------------------------


def test_aggregate_no_services_returns_host_state():
    host = _host_state("h1", "UP")
    result = _aggregate_host_with_services_from_data(host, [])
    assert result.state == "UP"
    assert result is host  # same object returned


def test_aggregate_service_warning_wins_over_up():
    host = _host_state("h1", "UP")
    services = [{"state": "WARNING"}, {"state": "OK"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "WARNING"


def test_aggregate_host_down_wins_over_warning():
    host = _host_state("h1", "DOWN")
    services = [{"state": "WARNING"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "DOWN"


def test_aggregate_critical_wins_over_down():
    host = _host_state("h1", "DOWN")
    services = [{"state": "CRITICAL"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "CRITICAL"


def test_aggregate_all_ok_returns_host_state():
    host = _host_state("h1", "UP")
    services = [{"state": "OK"}, {"state": "OK"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "UP"


def test_aggregate_preserves_metadata():
    host = ObjectState(
        object_id="h1",
        type="host",
        state="UP",
        output="PING OK",
        acknowledged=True,
        in_downtime=True,
    )
    services = [{"state": "WARNING"}]
    result = _aggregate_host_with_services_from_data(host, services)
    assert result.state == "WARNING"
    assert result.output == "PING OK"
    assert result.acknowledged is True
    assert result.in_downtime is True


# ---------------------------------------------------------------------------
# get_board_states — no backend registered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_board_states_no_backend(monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {})
    board = _board(
        [
            _obj("h1", "host", host_name="srv1"),
            _obj("s1", "service", host_name="srv1", service_description="CPU"),
        ],
        backend_id="missing",
    )
    result = await get_board_states(board)
    assert result.backend_ok is False
    assert all(s.state == "PENDING" for s in result.states)
    assert len(result.states) == 2


# ---------------------------------------------------------------------------
# get_board_states — with mock backend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_board_states_with_backend(mock_backend, monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {"mock": mock_backend})

    host_state = ObjectState(object_id="h1", type="host", state="UP")
    mock_backend.get_hosts_states = AsyncMock(return_value={"srv1": host_state})

    board = _board([_obj("h1", "host", host_name="srv1")], backend_id="mock")
    result = await get_board_states(board)

    assert result.backend_ok is True
    assert result.states[0].state == "UP"
    assert result.states[0].object_id == "h1"


@pytest.mark.asyncio
async def test_get_board_states_batch_exception_yields_pending(mock_backend, monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {"mock": mock_backend})

    mock_backend.get_hosts_states = AsyncMock(side_effect=Exception("socket error"))

    board = _board([_obj("h1", "host", host_name="srv1")], backend_id="mock")
    result = await get_board_states(board)

    # All monitoring states stale → backend_ok=False
    assert result.backend_ok is False
    assert result.states[0].state == "PENDING"
    assert result.states[0].stale is True


@pytest.mark.asyncio
async def test_get_board_states_non_monitoring_objects(mock_backend, monkeypatch):
    monkeypatch.setattr(state_service, "_backends", {"mock": mock_backend})
    mock_backend.is_available = AsyncMock(return_value=True)

    # textbox and image are non-monitoring types → backend_ok determined by is_available
    board = _board(
        [_obj("t1", "textbox"), _obj("i1", "image")],
        backend_id="mock",
    )
    result = await get_board_states(board)
    assert result.backend_ok is True
    # Both non-monitoring objects get PENDING state
    assert all(s.state == "PENDING" for s in result.states)
