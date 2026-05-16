"""Global settings persistence.

Two domains share a single ``settings.json`` on disk:

- ``GlobalSettings`` (board/object defaults) — admin surface „Settings"
- ``SystemSettings`` (logging + Checkmk integration) — admin surface „System"

Each model parses only its own fields (``extra='ignore'``), so reading and
writing one domain never clobbers the other.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app.core.config import settings
from app.schemas.settings import GlobalSettings, SystemSettings

logger = logging.getLogger(__name__)


def _settings_path() -> Path:
    return Path(settings.boards_dir).parent / "settings.json"


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


# ── Global (board/object defaults) ────────────────────────────────────────


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
    raw = _read_raw()
    raw.update(data.model_dump())
    _write_raw(raw)
    return data


# ── System (runtime / integration) ────────────────────────────────────────


def get_system_settings() -> SystemSettings:
    data = SystemSettings.model_validate(_read_raw())
    if data.log_level is None:
        data.log_level = settings.log_level or ("DEBUG" if settings.debug else "INFO")
    if data.checkmk_url == "":
        data.checkmk_url = None
    return data


def save_system_settings(data: SystemSettings) -> SystemSettings:
    raw = _read_raw()
    raw.update(data.model_dump())
    _write_raw(raw)
    apply_log_level(data.log_level)
    return data


def apply_log_level(level: str | None) -> None:
    """Apply *level* to the root logger. Falls back to env-derived default when None."""
    effective = level or settings.log_level or ("DEBUG" if settings.debug else "INFO")
    numeric = getattr(logging, effective, logging.INFO)
    logging.getLogger().setLevel(numeric)
    logger.info("Log level set to %s", effective)
