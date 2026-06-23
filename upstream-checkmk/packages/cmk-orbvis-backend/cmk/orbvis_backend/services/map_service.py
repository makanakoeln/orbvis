#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Map CRUD and persistence."""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import threading
from pathlib import Path

from cmk.orbvis_backend.core.config import settings
from cmk.orbvis_backend.schemas._validators import coerce_user_url
from cmk.orbvis_backend.schemas.map import (
    MapConfig,
    MapCreate,
    MapObject,
    MapObjectUpdate,
    MapRead,
    MapUpdate,
    _coerce_color,
    view_element_count,
)

logger = logging.getLogger(__name__)

# Only alphanumeric, underscore, and hyphen – enforced both in the Pydantic schema
# (MapCreate.name pattern) and here to prevent path traversal on read/delete.
_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

# Per-map lock around read-modify-write sequences. Handlers run in FastAPI's
# threadpool, so without this, two concurrent edits to the same map race:
# both read the same snapshot, append/modify, and the later write clobbers the
# earlier one's changes. The atomic-rename in _save_map_file only guards
# against half-written files, not against lost updates.
_MAP_LOCKS: dict[str, threading.Lock] = {}
_MAP_LOCKS_GUARD = threading.Lock()


def _map_lock(name: str) -> threading.Lock:
    with _MAP_LOCKS_GUARD:
        lock = _MAP_LOCKS.get(name)
        if lock is None:
            lock = threading.Lock()
            _MAP_LOCKS[name] = lock
        return lock


# In-memory map cache + debounced disk flush. Reads from cache avoid the
# JSON parse on every request, and bursts of writes (drag-end + property edit
# + reorder, or a 504-object bulk import) collapse into a single disk write.
# Cache and bookkeeping are guarded by _CACHE_GUARD.
_CACHE: dict[str, MapConfig] = {}
_DIRTY: set[str] = set()
_FLUSH_TIMERS: dict[str, threading.Timer] = {}
_CACHE_GUARD = threading.Lock()
# Coalesce writes within this window into a single disk flush.
_FLUSH_DEBOUNCE_S = 0.2


def _maps_dir() -> Path:
    p = Path(settings.maps_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def migrate_legacy_keys() -> None:
    """Rewrite ``backend_id`` to ``connection_id`` in map JSON files once.

    The schema's AliasChoices already loads files with the legacy key, so this
    pass is purely about converging the on-disk format. Idempotent: skips files
    that no longer reference the legacy key.
    """
    for path in _maps_dir().glob("*.json"):
        try:
            text = path.read_text(encoding="utf-8")
            if "backend_id" not in text:
                continue
            data = json.loads(text)
            if not _replace_key_recursive(data, "backend_id", "connection_id"):
                continue
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(tmp, path)
            logger.info("Migrated %s: backend_id → connection_id", path.name)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not migrate %s: %s", path, exc)


def _replace_key_recursive(obj: object, old: str, new: str) -> bool:
    changed = False
    if isinstance(obj, dict):
        if old in obj and new not in obj:
            obj[new] = obj.pop(old)
            changed = True
        for v in obj.values():
            if _replace_key_recursive(v, old, new):
                changed = True
    elif isinstance(obj, list):
        for v in obj:
            if _replace_key_recursive(v, old, new):
                changed = True
    return changed


def _map_path(name: str) -> Path:
    """Return the absolute path for a map file, rejecting unsafe names."""
    if not _NAME_RE.match(name):
        raise ValueError(f"Invalid map name: {name!r}")
    return _maps_dir() / f"{name}.json"


def list_maps() -> list[MapRead]:
    # Cache may hold maps whose debounced flush hasn't hit disk yet, plus
    # newer in-memory edits to maps that *are* on disk. Prefer cache for
    # known names so we never list a stale snapshot.
    with _CACHE_GUARD:
        cached = {name: cfg.model_copy(deep=True) for name, cfg in _CACHE.items()}
    seen: set[str] = set()
    maps: list[MapRead] = []
    for name, cfg in cached.items():
        maps.append(_to_read(cfg))
        seen.add(name)
    for path in _maps_dir().glob("*.json"):
        if path.stem in seen:
            continue
        try:
            cfg = _load_map_file(path)
            maps.append(_to_read(cfg))
        except Exception as exc:
            logger.warning("Skipping invalid map file %s: %s", path, exc)
    return sorted(maps, key=lambda m: (m.sort_order, not m.readonly, (m.alias or m.name).lower()))


def get_map(name: str) -> MapConfig | None:
    with _CACHE_GUARD:
        cached = _CACHE.get(name)
    if cached is not None:
        return cached.model_copy(deep=True)
    try:
        path = _map_path(name)
    except ValueError:
        return None
    if not path.exists():
        return None
    cfg = _load_map_file(path)
    with _CACHE_GUARD:
        # Lost a load race with another thread — keep their copy
        existing = _CACHE.get(name)
        if existing is not None:
            return existing.model_copy(deep=True)
        _CACHE[name] = cfg
    return cfg.model_copy(deep=True)


def create_map(data: MapCreate) -> MapConfig:
    with _map_lock(data.name):
        # Existence check covers both disk *and* cache (a debounced create
        # may not have flushed yet). Validates the path along the way.
        path = _map_path(data.name)
        if path.exists() or get_map(data.name) is not None:
            raise ValueError(f"Map '{data.name}' already exists")
        # Names are file-backed, so "Folder" and "folder" collide on
        # case-insensitive filesystems and read as duplicates to the operator
        # everywhere else — reject a name that differs only in case from an
        # existing map.
        lowered = data.name.lower()
        if any(existing.name.lower() == lowered for existing in list_maps()):
            raise ValueError(f"Map '{data.name}' already exists")
        cfg = MapConfig(
            name=data.name,
            alias=data.alias,
            background_image=data.background_image,
            background_color=data.background_color,
            icon_size=data.icon_size,
            connection_id=data.connection_id,
            view=data.view,
            render_mode=data.render_mode,
        )
        _save_map(cfg)
        return cfg


class StaleMapError(Exception):
    """Raised when the client's ``expected_version`` doesn't match disk state.

    The current version is exposed so the API layer can return it in the 409
    response body — the client can then reload, re-display, and let the
    operator decide whether to retry their change.
    """

    def __init__(self, current_version: int) -> None:
        super().__init__(f"Map version mismatch (current: {current_version})")
        self.current_version = current_version


def update_map(
    name: str, data: MapUpdate, expected_version: int | None = None
) -> MapConfig | None:
    with _map_lock(name):
        cfg = get_map(name)
        if cfg is None:
            return None
        if expected_version is not None and cfg.version != expected_version:
            raise StaleMapError(cfg.version)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return cfg
        merged = cfg.model_dump() | update_data
        merged["version"] = cfg.version + 1
        cfg = MapConfig.model_validate(merged)
        _save_map(cfg)
        return cfg


def delete_map(name: str) -> bool:
    try:
        path = _map_path(name)
    except ValueError:
        return False
    with _map_lock(name):
        existed = name in _CACHE or path.exists()
        # Drop cache + cancel pending flush so a stale debounced write can't
        # recreate the file after we unlink it.
        _invalidate_cache(name)
        if path.exists():
            path.unlink()
        return existed


def add_object(name: str, obj: MapObject) -> MapConfig | None:
    with _map_lock(name):
        cfg = get_map(name)
        if cfg is None:
            return None
        existing_ids = {o.id for o in cfg.objects}
        if obj.id in existing_ids:
            raise ValueError(f"Object ID '{obj.id}' already exists in map '{name}'")
        cfg.objects.append(obj)
        cfg.version += 1
        _save_map(cfg)
        return cfg


def update_object(map_name: str, obj_id: str, updates: MapObjectUpdate) -> MapObject | None:
    with _map_lock(map_name):
        cfg = get_map(map_name)
        if cfg is None:
            return None
        for i, obj in enumerate(cfg.objects):
            if obj.id == obj_id:
                new_obj = MapObject.model_validate(
                    obj.model_dump() | updates.model_dump(exclude_unset=True)
                )
                cfg.objects[i] = new_obj
                cfg.version += 1
                _save_map(cfg)
                return new_obj
        return None


def delete_object(map_name: str, obj_id: str) -> bool:
    with _map_lock(map_name):
        cfg = get_map(map_name)
        if cfg is None:
            return False
        original_len = len(cfg.objects)
        cfg.objects = [o for o in cfg.objects if o.id != obj_id]
        if len(cfg.objects) == original_len:
            return False
        # Drop dangling sticky-connector bindings so no line points at a gone object.
        for o in cfg.objects:
            if o.start_ref == obj_id:
                o.start_ref = None
            if o.end_ref == obj_id:
                o.end_ref = None
        cfg.version += 1
        _save_map(cfg)
        return True


def _load_map_file(path: Path) -> MapConfig:
    data = json.loads(path.read_text())
    _sanitize_legacy_data(data)
    return MapConfig.model_validate(data)


def _sanitize_legacy_data(data: object) -> None:
    """In-place pre-cleanup so newly-strict validators don't reject legacy JSON.

    Strict input validators on the API schema would otherwise prevent any
    map from loading if a single object carries a value that pre-dates a
    rule (e.g. an unsupported ``line_color`` written before the regex check
    existed). Coerce these to ``None`` here so the load succeeds; future
    saves through the API still reject bad input.
    """
    if not isinstance(data, dict):
        return
    for obj in data.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        for key in ("line_color", "line_color_border"):
            if key in obj:
                obj[key] = _coerce_color(obj[key])
        for key in ("url", "hover_url", "graph_url"):
            if key in obj:
                obj[key] = coerce_user_url(obj[key])
    view = data.get("view")
    if isinstance(view, dict):
        for key in ("background_image", "tile_url"):
            if key in view:
                view[key] = coerce_user_url(view[key])
        for el in view.get("elements") or []:
            if isinstance(el, dict) and "src" in el:
                el["src"] = coerce_user_url(el["src"])


def _save_map_file(cfg: MapConfig) -> None:
    """Write atomically: write to a uniquely-named temp file, then rename (POSIX-atomic).

    Using a process-unique suffix prevents two concurrent saves from clobbering the
    same .tmp file (last write wins and silently drops the other's changes).
    """
    path = _map_path(cfg.name)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg.model_dump(), f, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _save_map(cfg: MapConfig) -> None:
    """Update the in-memory cache and schedule a debounced disk flush.

    Caller transfers ownership of ``cfg`` — must not keep mutating it after
    this returns, since the same instance is now stored in the cache. This
    skips a deep copy that would otherwise dominate per-op cost on maps
    with many objects.

    Callers must already hold ``_map_lock(cfg.name)`` so the cache update is
    consistent with the read-modify-write they just performed.
    """
    name = cfg.name
    with _CACHE_GUARD:
        _CACHE[name] = cfg
        _DIRTY.add(name)
        old = _FLUSH_TIMERS.pop(name, None)
        if old is not None:
            old.cancel()
        timer = threading.Timer(_FLUSH_DEBOUNCE_S, _flush, args=(name,))
        timer.daemon = True
        _FLUSH_TIMERS[name] = timer
        timer.start()


def _flush(name: str) -> None:
    """Persist a dirty map to disk. Holds the per-map lock to serialize
    against concurrent writers, then writes whatever the cache currently holds.
    """
    with _map_lock(name):
        with _CACHE_GUARD:
            if name not in _DIRTY:
                return
            cfg = _CACHE.get(name)
            _DIRTY.discard(name)
            _FLUSH_TIMERS.pop(name, None)
        if cfg is None:
            return
        try:
            _save_map_file(cfg)
        except Exception:
            # Re-mark dirty so a later write or shutdown flush retries
            with _CACHE_GUARD:
                _DIRTY.add(name)
            logger.exception("Failed to flush map '%s'", name)


def flush_all() -> None:
    """Synchronously flush every dirty map. Call from app shutdown so
    pending in-memory writes don't get lost when the process exits.
    """
    with _CACHE_GUARD:
        # Cancel pending timers so they don't race with us
        for timer in _FLUSH_TIMERS.values():
            timer.cancel()
        _FLUSH_TIMERS.clear()
        names = list(_DIRTY)
    for name in names:
        _flush(name)


def _invalidate_cache(name: str) -> None:
    """Drop a map from the cache and discard any pending flush — used when
    the map is deleted so a stale debounced timer doesn't recreate the file.
    """
    with _CACHE_GUARD:
        _CACHE.pop(name, None)
        _DIRTY.discard(name)
        timer = _FLUSH_TIMERS.pop(name, None)
        if timer is not None:
            timer.cancel()


def clone_map(name: str, new_name: str, alias: str | None = None) -> MapConfig:
    with _map_lock(new_name):
        src = get_map(name)
        if src is None:
            raise ValueError(f"Map '{name}' not found")
        dest_path = _map_path(new_name)
        if dest_path.exists() or get_map(new_name) is not None:
            raise ValueError(f"Map '{new_name}' already exists")
        lowered = new_name.lower()
        if any(existing.name.lower() == lowered for existing in list_maps()):
            raise ValueError(f"Map '{new_name}' already exists")
        cfg = copy.deepcopy(src)
        cfg.name = new_name
        cfg.readonly = False  # clones are always editable
        if alias is not None:
            cfg.alias = alias
        _save_map(cfg)
        return cfg


def import_map(data: dict[str, object], *, overwrite: bool = False) -> MapConfig:
    # Imports carry exported/legacy JSON — apply the same read-side coercion
    # as the load path so one stale value doesn't fail the whole import.
    _sanitize_legacy_data(data)
    cfg = MapConfig.model_validate(data)
    # MapConfig.name carries no pattern (the load path must accept whatever
    # is on disk), so guard the write path here: an unsafe name would pass the
    # cache but make every debounced flush fail in _map_path — the map
    # would silently vanish on restart and be undeletable meanwhile.
    if not _NAME_RE.match(cfg.name):
        raise ValueError(
            f"Map name {cfg.name!r} is invalid — only letters, digits, '_' and '-' are allowed"
        )
    with _map_lock(cfg.name):
        existing = get_map(cfg.name)
        if existing is not None:
            if not overwrite:
                raise ValueError(f"Map '{cfg.name}' already exists")
            if existing.readonly:
                raise ValueError(f"Map '{cfg.name}' is read-only and cannot be overwritten")
        else:
            # Same case-insensitive collision guard as create_map/clone_map
            # (file-backed names collide on case-insensitive filesystems).
            lowered = cfg.name.lower()
            if any(b.name.lower() == lowered for b in list_maps()):
                raise ValueError(f"Map '{cfg.name}' already exists")
        _save_map(cfg)
        return cfg


def reorder_maps(order: list[tuple[str, int]]) -> None:
    """Update sort_order for each named map. Unknown names are silently skipped."""
    for name, sort_order in order:
        with _map_lock(name):
            cfg = get_map(name)
            if cfg is None or cfg.sort_order == sort_order:
                continue
            cfg.sort_order = sort_order
            # Every mutation bumps the version so optimistic locking
            # (If-Match) sees reorders like any other write.
            cfg.version += 1
            _save_map(cfg)


def _to_read(cfg: MapConfig) -> MapRead:
    return MapRead(
        name=cfg.name,
        alias=cfg.alias,
        background_image=cfg.background_image,
        background_color=cfg.background_color,
        version=cfg.version,
        icon_size=cfg.icon_size,
        connection_id=cfg.connection_id,
        view_type=cfg.view.type,
        view=cfg.view,
        object_count=len(cfg.objects) + view_element_count(cfg.view),
        rotation_interval=cfg.rotation_interval,
        sort_order=cfg.sort_order,
        click_action=cfg.click_action,
        readonly=cfg.readonly,
        hover_template=cfg.hover_template,
        context_template=cfg.context_template,
        show_in_lists=cfg.show_in_lists,
        render_mode=cfg.render_mode,
        default_z=cfg.default_z,
    )
