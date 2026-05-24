"""Board CRUD and persistence."""

from __future__ import annotations

import copy
import json
import logging
import os
import re
import threading
from pathlib import Path

from app.core.config import settings
from app.schemas.board import (
    BoardConfig,
    BoardCreate,
    BoardObject,
    BoardObjectUpdate,
    BoardRead,
    BoardUpdate,
)

logger = logging.getLogger(__name__)

# Only alphanumeric, underscore, and hyphen – enforced both in the Pydantic schema
# (BoardCreate.name pattern) and here to prevent path traversal on read/delete.
_NAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")

# Per-board lock around read-modify-write sequences. Handlers run in FastAPI's
# threadpool, so without this, two concurrent edits to the same board race:
# both read the same snapshot, append/modify, and the later write clobbers the
# earlier one's changes. The atomic-rename in _save_board_file only guards
# against half-written files, not against lost updates.
_BOARD_LOCKS: dict[str, threading.Lock] = {}
_BOARD_LOCKS_GUARD = threading.Lock()


def _board_lock(name: str) -> threading.Lock:
    with _BOARD_LOCKS_GUARD:
        lock = _BOARD_LOCKS.get(name)
        if lock is None:
            lock = threading.Lock()
            _BOARD_LOCKS[name] = lock
        return lock


# In-memory board cache + debounced disk flush. Reads from cache avoid the
# JSON parse on every request, and bursts of writes (drag-end + property edit
# + reorder, or a 504-object bulk import) collapse into a single disk write.
# Cache and bookkeeping are guarded by _CACHE_GUARD.
_CACHE: dict[str, BoardConfig] = {}
_DIRTY: set[str] = set()
_FLUSH_TIMERS: dict[str, threading.Timer] = {}
_CACHE_GUARD = threading.Lock()
# Coalesce writes within this window into a single disk flush.
_FLUSH_DEBOUNCE_S = 0.2


def _boards_dir() -> Path:
    p = Path(settings.boards_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def migrate_legacy_keys() -> None:
    """Rewrite ``backend_id`` to ``connection_id`` in board JSON files once.

    The schema's AliasChoices already loads files with the legacy key, so this
    pass is purely about converging the on-disk format. Idempotent: skips files
    that no longer reference the legacy key.
    """
    for path in _boards_dir().glob("*.json"):
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


def _board_path(name: str) -> Path:
    """Return the absolute path for a board file, rejecting unsafe names."""
    if not _NAME_RE.match(name):
        raise ValueError(f"Invalid board name: {name!r}")
    return _boards_dir() / f"{name}.json"


def list_boards() -> list[BoardRead]:
    # Cache may hold boards whose debounced flush hasn't hit disk yet, plus
    # newer in-memory edits to boards that *are* on disk. Prefer cache for
    # known names so we never list a stale snapshot.
    with _CACHE_GUARD:
        cached = {name: cfg.model_copy(deep=True) for name, cfg in _CACHE.items()}
    seen: set[str] = set()
    boards: list[BoardRead] = []
    for name, cfg in cached.items():
        boards.append(_to_read(cfg))
        seen.add(name)
    for path in _boards_dir().glob("*.json"):
        if path.stem in seen:
            continue
        try:
            cfg = _load_board_file(path)
            boards.append(_to_read(cfg))
        except Exception as exc:
            logger.warning("Skipping invalid board file %s: %s", path, exc)
    return sorted(boards, key=lambda m: (m.sort_order, not m.readonly, (m.alias or m.name).lower()))


def get_board(name: str) -> BoardConfig | None:
    with _CACHE_GUARD:
        cached = _CACHE.get(name)
    if cached is not None:
        return cached.model_copy(deep=True)
    try:
        path = _board_path(name)
    except ValueError:
        return None
    if not path.exists():
        return None
    cfg = _load_board_file(path)
    with _CACHE_GUARD:
        # Lost a load race with another thread — keep their copy
        existing = _CACHE.get(name)
        if existing is not None:
            return existing.model_copy(deep=True)
        _CACHE[name] = cfg
    return cfg.model_copy(deep=True)


def create_board(data: BoardCreate) -> BoardConfig:
    with _board_lock(data.name):
        # Existence check covers both disk *and* cache (a debounced create
        # may not have flushed yet). Validates the path along the way.
        path = _board_path(data.name)
        if path.exists() or get_board(data.name) is not None:
            raise ValueError(f"Board '{data.name}' already exists")
        cfg = BoardConfig(
            name=data.name,
            alias=data.alias,
            background_image=data.background_image,
            background_color=data.background_color,
            icon_size=data.icon_size,
            connection_id=data.connection_id,
            view=data.view,
        )
        _save_board(cfg)
        return cfg


class StaleBoardError(Exception):
    """Raised when the client's ``expected_version`` doesn't match disk state.

    The current version is exposed so the API layer can return it in the 409
    response body — the client can then reload, re-display, and let the
    operator decide whether to retry their change.
    """

    def __init__(self, current_version: int) -> None:
        super().__init__(f"Board version mismatch (current: {current_version})")
        self.current_version = current_version


def update_board(
    name: str, data: BoardUpdate, expected_version: int | None = None
) -> BoardConfig | None:
    with _board_lock(name):
        cfg = get_board(name)
        if cfg is None:
            return None
        if expected_version is not None and cfg.version != expected_version:
            raise StaleBoardError(cfg.version)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return cfg
        merged = cfg.model_dump() | update_data
        merged["version"] = cfg.version + 1
        cfg = BoardConfig.model_validate(merged)
        _save_board(cfg)
        return cfg


def delete_board(name: str) -> bool:
    try:
        path = _board_path(name)
    except ValueError:
        return False
    with _board_lock(name):
        existed = name in _CACHE or path.exists()
        # Drop cache + cancel pending flush so a stale debounced write can't
        # recreate the file after we unlink it.
        _invalidate_cache(name)
        if path.exists():
            path.unlink()
        return existed


def add_object(name: str, obj: BoardObject) -> BoardConfig | None:
    with _board_lock(name):
        cfg = get_board(name)
        if cfg is None:
            return None
        existing_ids = {o.id for o in cfg.objects}
        if obj.id in existing_ids:
            raise ValueError(f"Object ID '{obj.id}' already exists in board '{name}'")
        cfg.objects.append(obj)
        cfg.version += 1
        _save_board(cfg)
        return cfg


def update_object(board_name: str, obj_id: str, updates: BoardObjectUpdate) -> BoardObject | None:
    with _board_lock(board_name):
        cfg = get_board(board_name)
        if cfg is None:
            return None
        for i, obj in enumerate(cfg.objects):
            if obj.id == obj_id:
                new_obj = BoardObject.model_validate(
                    obj.model_dump() | updates.model_dump(exclude_unset=True)
                )
                cfg.objects[i] = new_obj
                cfg.version += 1
                _save_board(cfg)
                return new_obj
        return None


def delete_object(board_name: str, obj_id: str) -> bool:
    with _board_lock(board_name):
        cfg = get_board(board_name)
        if cfg is None:
            return False
        original_len = len(cfg.objects)
        cfg.objects = [o for o in cfg.objects if o.id != obj_id]
        if len(cfg.objects) == original_len:
            return False
        cfg.version += 1
        _save_board(cfg)
        return True


def _load_board_file(path: Path) -> BoardConfig:
    data = json.loads(path.read_text())
    _sanitize_legacy_data(data)
    return BoardConfig.model_validate(data)


def _sanitize_legacy_data(data: object) -> None:
    """In-place pre-cleanup so newly-strict validators don't reject legacy JSON.

    Strict input validators on the API schema would otherwise prevent any
    board from loading if a single object carries a value that pre-dates a
    rule (e.g. an unsupported ``line_color`` written before the regex check
    existed). Coerce these to ``None`` here so the load succeeds; future
    saves through the API still reject bad input.
    """
    if not isinstance(data, dict):
        return
    from app.schemas.board import _coerce_color

    for obj in data.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        for key in ("line_color", "line_color_border"):
            if key in obj:
                obj[key] = _coerce_color(obj[key])


def _save_board_file(cfg: BoardConfig) -> None:
    """Write atomically: write to a uniquely-named temp file, then rename (POSIX-atomic).

    Using a process-unique suffix prevents two concurrent saves from clobbering the
    same .tmp file (last write wins and silently drops the other's changes).
    """
    path = _board_path(cfg.name)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{os.urandom(4).hex()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg.model_dump(), f, indent=2, ensure_ascii=False)
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _save_board(cfg: BoardConfig) -> None:
    """Update the in-memory cache and schedule a debounced disk flush.

    Caller transfers ownership of ``cfg`` — must not keep mutating it after
    this returns, since the same instance is now stored in the cache. This
    skips a deep copy that would otherwise dominate per-op cost on boards
    with many objects.

    Callers must already hold ``_board_lock(cfg.name)`` so the cache update is
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
    """Persist a dirty board to disk. Holds the per-board lock to serialize
    against concurrent writers, then writes whatever the cache currently holds.
    """
    with _board_lock(name):
        with _CACHE_GUARD:
            if name not in _DIRTY:
                return
            cfg = _CACHE.get(name)
            _DIRTY.discard(name)
            _FLUSH_TIMERS.pop(name, None)
        if cfg is None:
            return
        try:
            _save_board_file(cfg)
        except Exception:
            # Re-mark dirty so a later write or shutdown flush retries
            with _CACHE_GUARD:
                _DIRTY.add(name)
            logger.exception("Failed to flush board '%s'", name)


def flush_all() -> None:
    """Synchronously flush every dirty board. Call from app shutdown so
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
    """Drop a board from the cache and discard any pending flush — used when
    the board is deleted so a stale debounced timer doesn't recreate the file.
    """
    with _CACHE_GUARD:
        _CACHE.pop(name, None)
        _DIRTY.discard(name)
        timer = _FLUSH_TIMERS.pop(name, None)
        if timer is not None:
            timer.cancel()


def clone_board(name: str, new_name: str, alias: str | None = None) -> BoardConfig:
    with _board_lock(new_name):
        src = get_board(name)
        if src is None:
            raise ValueError(f"Board '{name}' not found")
        dest_path = _board_path(new_name)
        if dest_path.exists() or get_board(new_name) is not None:
            raise ValueError(f"Board '{new_name}' already exists")
        cfg = copy.deepcopy(src)
        cfg.name = new_name
        cfg.readonly = False  # clones are always editable
        if alias is not None:
            cfg.alias = alias
        _save_board(cfg)
        return cfg


def import_board(data: dict[str, object], *, overwrite: bool = False) -> BoardConfig:
    cfg = BoardConfig.model_validate(data)
    with _board_lock(cfg.name):
        existing = get_board(cfg.name)
        if existing is not None:
            if not overwrite:
                raise ValueError(f"Board '{cfg.name}' already exists")
            if existing.readonly:
                raise ValueError(f"Board '{cfg.name}' is read-only and cannot be overwritten")
        _save_board(cfg)
        return cfg


def reorder_boards(order: list[tuple[str, int]]) -> None:
    """Update sort_order for each named board. Unknown names are silently skipped."""
    for name, sort_order in order:
        with _board_lock(name):
            cfg = get_board(name)
            if cfg is None:
                continue
            cfg.sort_order = sort_order
            _save_board(cfg)


def _to_read(cfg: BoardConfig) -> BoardRead:
    return BoardRead(
        name=cfg.name,
        alias=cfg.alias,
        background_image=cfg.background_image,
        background_color=cfg.background_color,
        version=cfg.version,
        icon_size=cfg.icon_size,
        connection_id=cfg.connection_id,
        view_type=cfg.view.type,
        view=cfg.view,
        object_count=len(cfg.objects),
        rotation_interval=cfg.rotation_interval,
        sort_order=cfg.sort_order,
        click_action=cfg.click_action,
        readonly=cfg.readonly,
        hover_template=cfg.hover_template,
        context_template=cfg.context_template,
        show_in_lists=cfg.show_in_lists,
    )
