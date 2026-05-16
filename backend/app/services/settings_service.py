"""Global settings persistence."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from app.core.config import settings
from app.schemas.settings import GlobalSettings

logger = logging.getLogger(__name__)


def _settings_path() -> Path:
    return Path(settings.boards_dir).parent / "settings.json"


def get_settings() -> GlobalSettings:
    path = _settings_path()
    if not path.is_file():
        data = GlobalSettings()
    else:
        try:
            data = GlobalSettings.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            logger.warning("Could not read settings.json: %s", exc)
            data = GlobalSettings()
    if data.log_level is None:
        data.log_level = settings.log_level or ("DEBUG" if settings.debug else "INFO")
    # Empty string for an Optional field is the legacy form of "unset"; turn it
    # back into None so the FormSpec UI shows the toggle as off (the placeholder
    # hint takes over visually instead of an active checkbox + empty input).
    for opt_field in ("hover_template", "context_template", "checkmk_url"):
        if getattr(data, opt_field) == "":
            setattr(data, opt_field, None)
    return data


def save_settings(data: GlobalSettings) -> GlobalSettings:
    path = _settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.{os.urandom(4).hex()}.tmp")
    try:
        tmp.write_text(
            json.dumps(data.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    apply_log_level(data.log_level)
    return data


def apply_log_level(level: str | None) -> None:
    """Apply *level* to the root logger. Falls back to env-derived default when None."""
    effective = level or settings.log_level or ("DEBUG" if settings.debug else "INFO")
    numeric = getattr(logging, effective, logging.INFO)
    logging.getLogger().setLevel(numeric)
    logger.info("Log level set to %s", effective)
