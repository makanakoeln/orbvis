"""Map CRUD and persistence."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.config import settings
from app.schemas.map import (
    MapConfig,
    MapCreate,
    MapGlobals,
    MapObject,
    MapRead,
    MapUpdate,
)

logger = logging.getLogger(__name__)


def _maps_dir() -> Path:
    p = Path(settings.maps_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _map_path(name: str) -> Path:
    return _maps_dir() / f"{name}.json"


def list_maps() -> list[MapRead]:
    maps = []
    for path in _maps_dir().glob("*.json"):
        try:
            cfg = _load_map_file(path)
            maps.append(_to_read(cfg))
        except Exception as exc:
            logger.warning("Skipping invalid map file %s: %s", path, exc)
    return sorted(maps, key=lambda m: m.name)


def get_map(name: str) -> MapConfig | None:
    path = _map_path(name)
    if not path.exists():
        return None
    return _load_map_file(path)


def create_map(data: MapCreate) -> MapConfig:
    path = _map_path(data.name)
    if path.exists():
        raise ValueError(f"Map '{data.name}' already exists")
    cfg = MapConfig(
        name=data.name,
        globals=MapGlobals(
            alias=data.alias,
            background_image=data.background_image,
            icon_size=data.icon_size,
            backend_id=data.backend_id,
        ),
    )
    _save_map_file(cfg)
    return cfg


def update_map(name: str, data: MapUpdate) -> MapConfig | None:
    cfg = get_map(name)
    if cfg is None:
        return None
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(cfg.globals, key, value)
    _save_map_file(cfg)
    return cfg


def delete_map(name: str) -> bool:
    path = _map_path(name)
    if not path.exists():
        return False
    path.unlink()
    return True


def add_object(name: str, obj: MapObject) -> MapConfig | None:
    cfg = get_map(name)
    if cfg is None:
        return None
    existing_ids = {o.id for o in cfg.objects}
    if obj.id in existing_ids:
        raise ValueError(f"Object ID '{obj.id}' already exists in map '{name}'")
    cfg.objects.append(obj)
    _save_map_file(cfg)
    return cfg


def update_object(map_name: str, obj_id: str, updates: dict) -> MapObject | None:
    cfg = get_map(map_name)
    if cfg is None:
        return None
    for obj in cfg.objects:
        if obj.id == obj_id:
            for key, value in updates.items():
                if hasattr(obj, key) and key != "extra":
                    setattr(obj, key, value)
                else:
                    obj.extra[key] = value
            _save_map_file(cfg)
            return obj
    return None


def delete_object(map_name: str, obj_id: str) -> bool:
    cfg = get_map(map_name)
    if cfg is None:
        return False
    original_len = len(cfg.objects)
    cfg.objects = [o for o in cfg.objects if o.id != obj_id]
    if len(cfg.objects) == original_len:
        return False
    _save_map_file(cfg)
    return True


def _load_map_file(path: Path) -> MapConfig:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return MapConfig.model_validate(data)


def _save_map_file(cfg: MapConfig) -> None:
    path = _map_path(cfg.name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg.model_dump(), f, indent=2, ensure_ascii=False)


def _to_read(cfg: MapConfig) -> MapRead:
    return MapRead(
        name=cfg.name,
        alias=cfg.globals.alias,
        background_image=cfg.globals.background_image,
        icon_size=cfg.globals.icon_size,
        backend_id=cfg.globals.backend_id,
        object_count=len(cfg.objects),
    )
