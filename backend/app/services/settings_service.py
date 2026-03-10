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
    return Path(settings.maps_dir).parent / "settings.json"


def get_settings() -> GlobalSettings:
    path = _settings_path()
    if not path.is_file():
        return GlobalSettings()
    try:
        return GlobalSettings.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except Exception as exc:
        logger.warning("Could not read settings.json: %s", exc)
        return GlobalSettings()


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
    return data
