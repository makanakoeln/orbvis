"""Tests for the connection_service warmup loop.

The loop keeps livestatus pools primed so the first user-facing /topology call
after a long idle doesn't pay the full cold-start latency.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.connections.base import ConnectionBase
from app.schemas.state import ServicesSummary
from app.services import connection_service, state_service


def _summary(*, crit: int = 0, warn: int = 0, unk: int = 0, pend: int = 0) -> ServicesSummary:
    return ServicesSummary(ok=0, warning=warn, critical=crit, unknown=unk, pending=pend)


def _mock_connection(topology_rows: list[dict] | None = None) -> MagicMock:
    """Build a minimal mock connection that records warmup-relevant calls."""
    connection = MagicMock(spec=ConnectionBase)
    connection.get_topology = AsyncMock(return_value=topology_rows or [])
    connection.get_hosts_services_batch = AsyncMock(return_value={})
    return connection


@pytest.fixture(autouse=True)
def _isolate_registry(monkeypatch):
    """Per-test connection registry so warmup ticks don't pick up siblings."""
    monkeypatch.setattr(state_service, "_connections", {})
    yield


@pytest.mark.asyncio
async def test_warmup_loop_disabled_when_interval_is_zero(monkeypatch):
    """Setting connection_warmup_interval=0 must short-circuit the loop."""
    monkeypatch.setattr("app.core.config.settings.connection_warmup_interval", 0)
    connection = _mock_connection([{"name": "h1"}])
    state_service.register_connection("c1", connection)
    await connection_service.warmup_loop()
    connection.get_topology.assert_not_awaited()


@pytest.mark.asyncio
async def test_warmup_tick_pre_fetches_topology_and_service_sample(monkeypatch):
    """One tick must hit get_topology + the top-K bulk-services query per connection."""
    monkeypatch.setattr("app.core.config.settings.flow_board_top_affected_hosts", 3)
    # Rows in arbitrary order; ranking must surface the highest CRIT count first.
    rows = [
        {"name": "calm-1", "services_summary": _summary(crit=0)},
        {"name": "warn-mild", "services_summary": _summary(warn=1)},
        {"name": "crit-hot", "services_summary": _summary(crit=10)},
        {"name": "crit-warm", "services_summary": _summary(crit=2)},
        {"name": "calm-2", "services_summary": _summary()},
    ]
    connection = _mock_connection(rows)
    state_service.register_connection("c1", connection)
    await connection_service._warmup_tick()
    connection.get_topology.assert_awaited_once()
    connection.get_hosts_services_batch.assert_awaited_once()
    sample = connection.get_hosts_services_batch.await_args.args[0]
    assert sample == ["crit-hot", "crit-warm", "warn-mild"]


@pytest.mark.asyncio
async def test_warmup_tick_swallows_per_connection_failures():
    """A failing connection must not abort the rest of the tick."""
    healthy = _mock_connection([{"name": "h1"}])
    broken = _mock_connection()
    broken.get_topology = AsyncMock(side_effect=RuntimeError("livestatus dead"))
    state_service.register_connection("broken", broken)
    state_service.register_connection("healthy", healthy)
    await connection_service._warmup_tick()
    healthy.get_topology.assert_awaited_once()


@pytest.mark.asyncio
async def test_warmup_loop_runs_periodic_ticks_and_cancels_cleanly(monkeypatch):
    """Loop primes once at start and continues at configured interval; cancel propagates."""
    monkeypatch.setattr("app.core.config.settings.connection_warmup_interval", 1)
    real_sleep = asyncio.sleep
    fast_sleeps: list[float] = []

    async def _sleep(seconds: float) -> None:
        fast_sleeps.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr("app.services.connection_service.asyncio.sleep", _sleep)

    third_tick = asyncio.Event()
    call_count = 0

    async def _topology() -> list[dict]:
        nonlocal call_count
        call_count += 1
        if call_count >= 3:
            third_tick.set()
        return [{"name": "h1"}]

    connection = MagicMock(spec=ConnectionBase)
    connection.get_topology = AsyncMock(side_effect=_topology)
    connection.get_hosts_services_batch = AsyncMock(return_value={})
    state_service.register_connection("c1", connection)

    task = asyncio.create_task(connection_service.warmup_loop())
    await asyncio.wait_for(third_tick.wait(), timeout=2.0)

    assert connection.get_topology.await_count >= 3
    assert all(s == 1 for s in fast_sleeps)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
