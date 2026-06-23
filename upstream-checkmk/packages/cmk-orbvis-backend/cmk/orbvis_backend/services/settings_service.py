#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Global settings persistence.

Two domains share a single ``settings.json`` on disk:

- ``GlobalSettings`` (map/object defaults) — admin surface „Settings"
- ``SystemSettings`` (logging + Checkmk integration) — admin surface „System"

Each model parses only its own fields (``extra='ignore'``), so reading and
writing one domain never clobbers the other.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from cmk.orbvis_backend.core.config import settings
from cmk.orbvis_backend.schemas.settings import GlobalSettings, SystemSettings

logger = logging.getLogger(__name__)

# Both save paths do read-modify-write on the shared settings.json, and
# handlers run in FastAPI's threadpool — without a lock a concurrent Global
# and System save loses one of the two updates (atomic rename only prevents
# torn files, not lost updates).
_settings_lock = threading.Lock()


def _settings_path() -> Path:
    return Path(settings.maps_dir).parent / "settings.json"


def _read_raw() -> dict[str, object]:
    path = _settings_path()
    if not path.is_file():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read settings.json: %s", exc)
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _write_raw(raw: dict[str, object]) -> None:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.{os.urandom(4).hex()}.tmp")
    try:
        tmp.write_text(
            json.dumps(raw, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


# ── Global (map/object defaults) ────────────────────────────────────────


def get_global_settings() -> GlobalSettings:
    try:
        data = GlobalSettings.model_validate(_read_raw())
    except Exception as exc:
        # A previously-saved file may violate a now-stricter validator
        # (e.g. label_color regex tightened). Fall back to defaults so the
        # admin UI still loads and the operator can re-enter a valid value.
        logger.warning("settings.json failed validation, using defaults: %s", exc)
        data = GlobalSettings()
    # Empty string for an Optional field is the legacy form of "unset"; turn it
    # back into None so the FormSpec UI shows the toggle as off (the placeholder
    # hint takes over visually instead of an active checkbox + empty input).
    for opt_field in ("hover_template", "context_template"):
        if getattr(data, opt_field) == "":
            setattr(data, opt_field, None)
    return data


def save_global_settings(data: GlobalSettings) -> GlobalSettings:
    with _settings_lock:
        raw = _read_raw()
        raw.update(data.model_dump())
        _write_raw(raw)
    return data


# ── System (runtime / integration) ────────────────────────────────────────


def get_system_settings() -> SystemSettings:
    """Return the raw stored ``SystemSettings`` — ``None`` means *unset*.

    Don't apply env-fallbacks here; callers that need the effective value
    use ``get_effective_*`` helpers below. Saving back through the API
    would otherwise persist whatever the env defaulted to and silently
    pin the operator to today's env value.
    """
    data = SystemSettings.model_validate(_read_raw())
    if data.checkmk_url == "":
        data.checkmk_url = None
    return data


def get_effective_log_level() -> str:
    data = get_system_settings()
    return data.log_level or settings.log_level or ("DEBUG" if settings.debug else "INFO")


def get_effective_state_refresh_interval() -> int:
    data = get_system_settings()
    return data.state_refresh_interval or settings.state_refresh_interval


def get_effective_access_token_expire_minutes() -> int:
    data = get_system_settings()
    return data.access_token_expire_minutes or settings.access_token_expire_minutes


def save_system_settings(data: SystemSettings) -> SystemSettings:
    with _settings_lock:
        raw = _read_raw()
        raw.update(data.model_dump())
        _write_raw(raw)
    # Use the effective level (storage overrides env) so toggling the
    # UI back to "Use environment default" takes effect immediately
    # instead of waiting for the next restart.
    apply_log_level(get_effective_log_level())
    return data


def apply_log_level(level: str | None) -> None:
    """Apply *level* to the root logger. Falls back to env-derived default when None."""
    effective = level or settings.log_level or ("DEBUG" if settings.debug else "INFO")
    numeric = getattr(logging, effective, logging.INFO)
    logging.getLogger().setLevel(numeric)
    logger.info("Log level set to %s", effective)
