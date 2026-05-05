"""Backend configuration persistence and runtime registration."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import settings
from app.schemas.connection import ConnectionConfig
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
    return [ConnectionConfig.model_validate(b) for b in data]


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
        port=cfg.port,
        timeout=cfg.timeout,
        checkmk_url=cfg.checkmk_url,
        automation_user=cfg.automation_user,
        automation_secret=cfg.automation_secret,
    )


def _activate(cfg: ConnectionConfig) -> None:
    """Instantiate and register a connection with the state service."""
    _register(cfg.id, build_instance(cfg))
