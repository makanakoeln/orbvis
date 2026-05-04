"""Backend configuration persistence and runtime registration."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import settings
from app.schemas.backend import BackendConfig
from app.services.state_service import register_backend as _register

if TYPE_CHECKING:
    from app.backends.base import BackendBase

logger = logging.getLogger(__name__)


def _path() -> Path:
    return Path(settings.backends_file)


def load_all() -> list[BackendConfig]:
    path = _path()
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [BackendConfig.model_validate(b) for b in data]


def _save_all(backends: list[BackendConfig]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        try:
            os.write(fd, json.dumps([b.model_dump() for b in backends], indent=2).encode())
        finally:
            os.close(fd)
        Path(tmp).replace(path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def get(backend_id: str) -> BackendConfig | None:
    return next((b for b in load_all() if b.id == backend_id), None)


def create(cfg: BackendConfig) -> BackendConfig:
    backends = load_all()
    if any(b.id == cfg.id for b in backends):
        raise ValueError(f"Backend '{cfg.id}' already exists")
    backends.append(cfg)
    _save_all(backends)
    _activate(cfg)
    return cfg


def update(backend_id: str, updates: BackendConfig) -> BackendConfig | None:
    backends = load_all()
    for i, b in enumerate(backends):
        if b.id == backend_id:
            backends[i] = updates
            _save_all(backends)
            _activate(updates)
            return updates
    return None


def delete(backend_id: str) -> bool:
    backends = load_all()
    new = [b for b in backends if b.id != backend_id]
    if len(new) == len(backends):
        return False
    _save_all(new)
    return True


def activate_all() -> None:
    """Load all persisted backend configs and register them at startup."""
    for cfg in load_all():
        try:
            _activate(cfg)
            logger.info("Activated backend '%s' (type=%s)", cfg.id, cfg.type)
        except Exception as exc:
            logger.error("Failed to activate backend '%s': %s", cfg.id, exc)


def build_instance(cfg: BackendConfig) -> BackendBase:
    """Build a backend instance without registering it (e.g. for connection tests)."""
    if cfg.type == "test":
        from app.backends.test import TestBackend

        return TestBackend()
    if cfg.type == "icinga2":
        from app.backends.icinga2 import Icinga2Backend

        return Icinga2Backend(
            url=cfg.icinga2_url or "https://localhost:5665",
            username=cfg.icinga2_username or "",
            password=cfg.icinga2_password or "",
            timeout=cfg.timeout,
            verify_ssl=cfg.icinga2_verify_ssl,
        )
    from app.backends.livestatus import LivestatusBackend

    return LivestatusBackend(
        socket_path=cfg.socket_path or "/var/run/nagios/rw/live",
        host=cfg.host,
        port=cfg.port,
        timeout=cfg.timeout,
        checkmk_url=cfg.checkmk_url,
        automation_user=cfg.automation_user,
        automation_secret=cfg.automation_secret,
    )


def _activate(cfg: BackendConfig) -> None:
    """Instantiate and register a backend with the state service."""
    _register(cfg.id, build_instance(cfg))
