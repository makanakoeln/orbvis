"""Backend configuration persistence and runtime registration."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

from app.connections.base import topology_problem_rank
from app.core.config import settings
from app.schemas.connection import ConnectionConfig
from app.services import state_service
from app.services.state_service import register_connection as _register

if TYPE_CHECKING:
    from app.connections.base import ConnectionBase

logger = logging.getLogger(__name__)


def _path() -> Path:
    return Path(settings.connections_file)


def migrate_legacy_filename() -> None:
    """Rename a pre-rename ``backends.json`` to ``connections.json`` once.

    Idempotent: only renames when the legacy file is present and the new file
    does not yet exist, so re-running is a no-op. Any failure is logged but
    does not abort startup — the file simply remains under the old name.
    """
    new_path = _path()
    legacy = new_path.with_name("backends.json")
    if legacy.exists() and not new_path.exists():
        try:
            legacy.replace(new_path)
            logger.info("Migrated %s → %s", legacy, new_path)
        except OSError as exc:
            logger.warning("Could not rename %s → %s: %s", legacy, new_path, exc)


def load_all() -> list[ConnectionConfig]:
    path = _path()
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out: list[ConnectionConfig] = []
    # Skipping invalid entries instead of raising so one stale record doesn't
    # abort lifespan startup.
    for raw in data:
        try:
            out.append(ConnectionConfig.model_validate(raw))
        except Exception as exc:
            entry_id = raw.get("id", "<no-id>") if isinstance(raw, dict) else "<not-a-dict>"
            logger.warning("Skipping invalid connection %r: %s", entry_id, exc)
    return out


def _save_all(connections: list[ConnectionConfig]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        try:
            os.write(fd, json.dumps([b.model_dump() for b in connections], indent=2).encode())
        finally:
            os.close(fd)
        Path(tmp).replace(path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def get(connection_id: str) -> ConnectionConfig | None:
    return next((b for b in load_all() if b.id == connection_id), None)


def create(cfg: ConnectionConfig) -> ConnectionConfig:
    connections = load_all()
    if any(b.id == cfg.id for b in connections):
        raise ValueError(f"Connection '{cfg.id}' already exists")
    connections.append(cfg)
    _save_all(connections)
    _activate(cfg)
    return cfg


def update(connection_id: str, updates: ConnectionConfig) -> ConnectionConfig | None:
    connections = load_all()
    for i, b in enumerate(connections):
        if b.id == connection_id:
            connections[i] = updates
            _save_all(connections)
            _activate(updates)
            return updates
    return None


def delete(connection_id: str) -> bool:
    connections = load_all()
    new = [b for b in connections if b.id != connection_id]
    if len(new) == len(connections):
        return False
    _save_all(new)
    return True


def activate_all() -> None:
    """Load all persisted connection configs and register them at startup."""
    for cfg in load_all():
        try:
            _activate(cfg)
            logger.info("Activated connection '%s' (type=%s)", cfg.id, cfg.type)
        except Exception as exc:
            logger.error("Failed to activate connection '%s': %s", cfg.id, exc)


def build_instance(cfg: ConnectionConfig) -> ConnectionBase:
    """Build a connection instance without registering it (e.g. for connection tests)."""
    if cfg.type == "test":
        from app.connections.test import TestConnection

        return TestConnection()
    if cfg.type == "icinga2":
        from app.connections.icinga2 import Icinga2Connection

        return Icinga2Connection(
            url=cfg.icinga2_url or "https://localhost:5665",
            username=cfg.icinga2_username or "",
            password=cfg.icinga2_password or "",
            timeout=cfg.timeout,
            verify_ssl=cfg.icinga2_verify_ssl,
        )
    from app.connections.livestatus import LivestatusConnection

    return LivestatusConnection(
        socket_path=cfg.socket_path or "/var/run/nagios/rw/live",
        host=cfg.host,
        port=cfg.port if cfg.port is not None else 6557,
        tls=cfg.tls,
        tls_verify=cfg.tls_verify,
        timeout=cfg.timeout,
        checkmk_url=cfg.checkmk_url,
        automation_user=cfg.automation_user,
        automation_secret=cfg.automation_secret,
    )


def _activate(cfg: ConnectionConfig) -> None:
    """Instantiate and register a connection with the state service."""
    _register(cfg.id, build_instance(cfg))


async def _warmup_tick() -> None:
    """One pass: pre-fetch topology + the top-K bulk-services slice per connection.

    Uses the same ranking as the REST endpoint so warmup primes services for
    exactly the hosts a flow-board page will request — otherwise the warm
    pool only helps the cheap query and the user still pays for the bulk
    services round-trip.
    """
    top_k = settings.flow_board_top_affected_hosts
    for connection_id in state_service.list_connection_ids():
        connection = state_service.get_connection(connection_id)
        if connection is None:
            continue
        try:
            t0 = time.monotonic()
            rows = await connection.get_topology()
            if rows and top_k > 0:
                ranked = sorted(rows, key=topology_problem_rank, reverse=True)
                sample = [r["name"] for r in ranked[:top_k]]
                await connection.get_hosts_services_batch(sample)
            logger.debug(
                "warmup tick connection=%s hosts=%d elapsed=%.0fms",
                connection_id,
                len(rows),
                (time.monotonic() - t0) * 1000,
            )
        except Exception:
            # Stale sockets heal on the next tick; never crash the loop.
            logger.warning("warmup tick failed for connection %s", connection_id, exc_info=True)


async def warmup_loop() -> None:
    """Periodically warm livestatus pools so the first user-facing query is fast.

    Idle pools on large sites can take 10-15 s on the first /topology call
    (socket open + cold service-cache fetch). Issuing a small query every
    ``connection_warmup_interval`` seconds keeps the pool primed. Sequential
    `await` per tick rules out overlapping ticks even on slow sites.
    """
    interval = settings.connection_warmup_interval
    if interval <= 0:
        return
    # Prime immediately so the first request after startup is warm.
    await _warmup_tick()
    while True:
        await asyncio.sleep(interval)
        await _warmup_tick()
