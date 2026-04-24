"""Board CRUD endpoints."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import (
    can_edit_board,
    can_view_board,
    get_current_user,
    require_admin,
)
from app.api.v1.types import BoardName
from app.core.config import settings
from app.core.database import get_db
from app.core.image_security import is_valid_image
from app.models.role import Role
from app.models.user import User
from app.schemas.board import (
    BoardClone,
    BoardConfig,
    BoardCreate,
    BoardObject,
    BoardObjectUpdate,
    BoardPermissionsRead,
    BoardRead,
    BoardUpdate,
)
from app.services import board_service
from app.services.cfg_parser import cfg_to_board

router = APIRouter()

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/svg+xml", "image/webp"}
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
_MAX_BACKGROUND_BYTES = 10 * 1024 * 1024  # 10 MB


def _require_board_view(name: str, user: User) -> None:
    if not can_view_board(user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No view permission for this board"
        )


def _require_board_edit(name: str, user: User) -> None:
    if not can_edit_board(user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No edit permission for this board"
        )


def _require_not_readonly(name: str) -> None:
    cfg = board_service.get_board(name)
    if cfg and cfg.readonly:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This board is read-only")


@router.get("", response_model=list[BoardRead])
async def list_boards(current_user: User = Depends(get_current_user)) -> list[BoardRead]:
    all_boards = board_service.list_boards()
    if current_user.is_admin:
        return all_boards
    return [m for m in all_boards if can_view_board(current_user, m.name)]


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_boards(
    order: list[dict[str, int | str]], _: User = Depends(require_admin)
) -> None:
    """Update sort_order for multiple boards at once. Body: [{"name": "...", "sort_order": 0}, ...]"""
    board_service.reorder_boards(
        [
            (str(item["name"]), int(item["sort_order"]))
            for item in order
            if "name" in item and "sort_order" in item
        ]
    )


@router.post("", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def create_board(data: BoardCreate, _: User = Depends(require_admin)) -> BoardConfig:
    try:
        return board_service.create_board(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.get("/{name}", response_model=BoardConfig)
async def get_board(name: BoardName, current_user: User = Depends(get_current_user)) -> BoardConfig:
    _require_board_view(name, current_user)
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    return cfg


@router.put("/{name}", response_model=BoardConfig)
async def update_board(
    name: BoardName, data: BoardUpdate, current_user: User = Depends(get_current_user)
) -> BoardConfig:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    cfg = board_service.update_board(name, data)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    return cfg


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(name: BoardName, _: User = Depends(require_admin)) -> None:
    if not board_service.delete_board(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )


@router.post("/{name}/clone", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def clone_board(
    name: BoardName, data: BoardClone, _: User = Depends(require_admin)
) -> BoardConfig:
    try:
        return board_service.clone_board(name, data.new_name, data.alias)
    except ValueError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc) else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc)) from None


@router.post("/import", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def import_board(
    data: dict[str, object], overwrite: bool = False, _: User = Depends(require_admin)
) -> BoardConfig:
    try:
        return board_service.import_board(data, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/import/cfg", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def import_cfg(
    file: UploadFile = File(...),
    overwrite: bool = False,
    _: User = Depends(require_admin),
) -> BoardConfig:
    """Import a legacy .cfg map file and convert it to an OrbVis board."""
    if not file.filename or not file.filename.lower().endswith(".cfg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only .cfg files are accepted"
        )
    content = (await file.read()).decode("utf-8", errors="replace")
    map_name = Path(file.filename).stem
    data = cfg_to_board(content, map_name)
    try:
        return board_service.import_board(data, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


# ----- Board permissions (read) -----


@router.get("/{name}/permissions", response_model=BoardPermissionsRead)
async def get_board_permissions(
    name: BoardName,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> BoardPermissionsRead:
    """Return which roles have direct (non-wildcard) view/edit permissions on this board."""
    result = await db.execute(select(Role))
    roles = result.scalars().all()

    view_roles: list[str] = []
    edit_roles: list[str] = []
    for role in roles:
        for perm in role.permissions:
            if perm.mod == "map" and perm.obj == name:
                if perm.act == "view" and role.name not in view_roles:
                    view_roles.append(role.name)
                elif perm.act == "edit" and role.name not in edit_roles:
                    edit_roles.append(role.name)

    return BoardPermissionsRead(view=view_roles, edit=edit_roles)


# ----- Background image -----


@router.post("/{name}/background")
async def upload_background(
    name: BoardName,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    if board_service.get_board(name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type"
        )

    contents = await file.read(_MAX_BACKGROUND_BYTES + 1)
    if len(contents) > _MAX_BACKGROUND_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Background image must not exceed {_MAX_BACKGROUND_BYTES // 1024 // 1024} MB",
        )
    if not is_valid_image(contents):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match a supported image format",
        )

    raw_suffix = Path(file.filename or "").suffix.lower()
    suffix = raw_suffix if raw_suffix in _ALLOWED_SUFFIXES else ".png"

    bg_dir = Path(settings.boards_dir) / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{name}{suffix}"
    dest = bg_dir / filename

    fd, tmp_path = tempfile.mkstemp(dir=bg_dir, prefix=f"{name}.", suffix=suffix)
    try:
        try:
            os.write(fd, contents)
        finally:
            os.close(fd)
        Path(tmp_path).replace(dest)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    board_service.update_board(name, BoardUpdate(background_image=filename))
    return JSONResponse({"filename": filename})


@router.delete("/{name}/background", status_code=status.HTTP_204_NO_CONTENT)
async def delete_background(
    name: BoardName, current_user: User = Depends(get_current_user)
) -> None:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    if board_service.get_board(name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    bg_dir = Path(settings.boards_dir) / "backgrounds"
    for f in bg_dir.glob(f"{name}.*"):
        f.unlink(missing_ok=True)
    board_service.update_board(name, BoardUpdate(background_image=None))


# ----- Object sub-resources -----


@router.post("/{name}/objects", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def add_object(
    name: BoardName, obj: BoardObject, current_user: User = Depends(get_current_user)
) -> BoardConfig:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    try:
        cfg = board_service.add_object(name, obj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    return cfg


@router.put("/{name}/objects/{obj_id}", response_model=BoardObject)
async def update_object(
    name: BoardName,
    obj_id: str,
    updates: BoardObjectUpdate,
    current_user: User = Depends(get_current_user),
) -> BoardObject:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    obj = board_service.update_object(name, obj_id, updates)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    return obj


@router.delete("/{name}/objects/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    name: BoardName, obj_id: str, current_user: User = Depends(get_current_user)
) -> None:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    if not board_service.delete_object(name, obj_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
