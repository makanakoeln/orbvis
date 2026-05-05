"""Board CRUD and persistence."""

from __future__ import annotations

import copy
import json
import logging
import os
import re
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
    boards = []
    for path in _boards_dir().glob("*.json"):
        try:
            cfg = _load_board_file(path)
            boards.append(_to_read(cfg))
        except Exception as exc:
            logger.warning("Skipping invalid board file %s: %s", path, exc)
    return sorted(boards, key=lambda m: (m.sort_order, not m.readonly, (m.alias or m.name).lower()))


def get_board(name: str) -> BoardConfig | None:
    try:
        path = _board_path(name)
    except ValueError:
        return None
    if not path.exists():
        return None
    return _load_board_file(path)


def create_board(data: BoardCreate) -> BoardConfig:
    path = _board_path(data.name)
    if path.exists():
        raise ValueError(f"Board '{data.name}' already exists")
    cfg = BoardConfig(
        name=data.name,
        alias=data.alias,
        background_image=data.background_image,
        icon_size=data.icon_size,
        connection_id=data.connection_id,
        view=data.view,
    )
    _save_board_file(cfg)
    return cfg


def update_board(name: str, data: BoardUpdate) -> BoardConfig | None:
    cfg = get_board(name)
    if cfg is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        return cfg
    cfg = BoardConfig.model_validate(cfg.model_dump() | update_data)
    _save_board_file(cfg)
    return cfg


def delete_board(name: str) -> bool:
    try:
        path = _board_path(name)
    except ValueError:
        return False
    if not path.exists():
        return False
    path.unlink()
    return True


def add_object(name: str, obj: BoardObject) -> BoardConfig | None:
    cfg = get_board(name)
    if cfg is None:
        return None
    existing_ids = {o.id for o in cfg.objects}
    if obj.id in existing_ids:
        raise ValueError(f"Object ID '{obj.id}' already exists in board '{name}'")
    cfg.objects.append(obj)
    _save_board_file(cfg)
    return cfg


def update_object(board_name: str, obj_id: str, updates: BoardObjectUpdate) -> BoardObject | None:
    cfg = get_board(board_name)
    if cfg is None:
        return None
    for i, obj in enumerate(cfg.objects):
        if obj.id == obj_id:
            new_obj = BoardObject.model_validate(
                obj.model_dump() | updates.model_dump(exclude_unset=True)
            )
            cfg.objects[i] = new_obj
            _save_board_file(cfg)
            return new_obj
    return None


def delete_object(board_name: str, obj_id: str) -> bool:
    cfg = get_board(board_name)
    if cfg is None:
        return False
    original_len = len(cfg.objects)
    cfg.objects = [o for o in cfg.objects if o.id != obj_id]
    if len(cfg.objects) == original_len:
        return False
    _save_board_file(cfg)
    return True


def _load_board_file(path: Path) -> BoardConfig:
    data = json.loads(path.read_text())
    return BoardConfig.model_validate(data)


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


def clone_board(name: str, new_name: str, alias: str | None = None) -> BoardConfig:
    src = get_board(name)
    if src is None:
        raise ValueError(f"Board '{name}' not found")
    dest_path = _board_path(new_name)
    if dest_path.exists():
        raise ValueError(f"Board '{new_name}' already exists")
    cfg = copy.deepcopy(src)
    cfg.name = new_name
    cfg.readonly = False  # clones are always editable
    if alias is not None:
        cfg.alias = alias
    _save_board_file(cfg)
    return cfg


def import_board(data: dict[str, object], *, overwrite: bool = False) -> BoardConfig:
    cfg = BoardConfig.model_validate(data)
    path = _board_path(cfg.name)
    if path.exists():
        if not overwrite:
            raise ValueError(f"Board '{cfg.name}' already exists")
        existing = _load_board_file(path)
        if existing.readonly:
            raise ValueError(f"Board '{cfg.name}' is read-only and cannot be overwritten")
    _save_board_file(cfg)
    return cfg


def reorder_boards(order: list[tuple[str, int]]) -> None:
    """Update sort_order for each named board. Unknown names are silently skipped."""
    for name, sort_order in order:
        cfg = get_board(name)
        if cfg is None:
            continue
        cfg.sort_order = sort_order
        _save_board_file(cfg)


def _to_read(cfg: BoardConfig) -> BoardRead:
    return BoardRead(
        name=cfg.name,
        alias=cfg.alias,
        background_image=cfg.background_image,
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
