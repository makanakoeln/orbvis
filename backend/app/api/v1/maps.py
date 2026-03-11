"""Map CRUD endpoints."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, get_db, require_admin, user_has_permission
from app.core.config import settings
from app.models.role import Role
from app.models.user import User
from app.schemas.map import MapClone, MapConfig, MapCreate, MapObject, MapPermissionsRead, MapRead, MapUpdate
from app.services import map_service

router = APIRouter()

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/svg+xml", "image/webp"}
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
_MAX_BACKGROUND_BYTES = 10 * 1024 * 1024  # 10 MB


def _is_valid_image(content: bytes) -> bool:
    """Validate image content via magic bytes, not just the Content-Type header."""
    h = content[:16]
    if h[:4] == b"\x89PNG":
        return True
    if h[:3] == b"\xff\xd8\xff":  # JPEG
        return True
    if h[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if h[:4] == b"RIFF" and content[8:12] == b"WEBP":  # WebP
        return True
    # SVG: search first 512 bytes for the <svg element.
    # We intentionally do NOT match <?xml alone – that matches any XML file.
    # A valid SVG must contain an <svg element regardless of whether it has an XML prolog.
    snippet = content[:512].lower()
    if b"<svg" in snippet:
        return True
    return False


def _require_map_view(name: str, user: User) -> None:
    if not user_has_permission(user, "map", "view", name):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No view permission for this map")


def _require_map_edit(name: str, user: User) -> None:
    if not user_has_permission(user, "map", "edit", name):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No edit permission for this map")


def _require_not_readonly(name: str) -> None:
    cfg = map_service.get_map(name)
    if cfg and cfg.readonly:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This map is read-only")


@router.get("", response_model=list[MapRead])
async def list_maps(current_user: User = Depends(get_current_user)) -> list[MapRead]:
    all_maps = map_service.list_maps()
    if current_user.is_admin:
        return all_maps
    return [m for m in all_maps if user_has_permission(current_user, "map", "view", m.name)]


@router.post("", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def create_map(
    data: MapCreate, _: User = Depends(require_admin)
) -> MapConfig:
    try:
        return map_service.create_map(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{name}", response_model=MapConfig)
async def get_map(name: str, current_user: User = Depends(get_current_user)) -> MapConfig:
    _require_map_view(name, current_user)
    cfg = map_service.get_map(name)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg


@router.put("/{name}", response_model=MapConfig)
async def update_map(
    name: str, data: MapUpdate, current_user: User = Depends(get_current_user)
) -> MapConfig:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    cfg = map_service.update_map(name, data)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_map(name: str, _: User = Depends(require_admin)) -> None:
    if not map_service.delete_map(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")


@router.post("/{name}/clone", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def clone_map(
    name: str, data: MapClone, _: User = Depends(require_admin)
) -> MapConfig:
    try:
        return map_service.clone_map(name, data.new_name, data.alias)
    except ValueError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc) else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc))


@router.post("/import", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def import_map(
    data: dict, overwrite: bool = False, _: User = Depends(require_admin)
) -> MapConfig:
    try:
        return map_service.import_map(data, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ----- Map permissions (read) -----

@router.get("/{name}/permissions", response_model=MapPermissionsRead)
async def get_map_permissions(
    name: str,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MapPermissionsRead:
    """Return which roles have direct (non-wildcard) view/edit permissions on this map."""
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

    return MapPermissionsRead(view=view_roles, edit=edit_roles)


# ----- Background image -----

@router.post("/{name}/background")
async def upload_background(
    name: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    if map_service.get_map(name) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type")

    contents = await file.read(_MAX_BACKGROUND_BYTES + 1)
    if len(contents) > _MAX_BACKGROUND_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Background image must not exceed {_MAX_BACKGROUND_BYTES // 1024 // 1024} MB",
        )
    if not _is_valid_image(contents):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match a supported image format",
        )

    raw_suffix = Path(file.filename or "").suffix.lower()
    suffix = raw_suffix if raw_suffix in _ALLOWED_SUFFIXES else ".png"

    bg_dir = Path(settings.maps_dir) / "backgrounds"
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

    map_service.update_map(name, MapUpdate(background_image=filename))
    return JSONResponse({"filename": filename})


@router.delete("/{name}/background", status_code=status.HTTP_204_NO_CONTENT)
async def delete_background(name: str, current_user: User = Depends(get_current_user)) -> None:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    if map_service.get_map(name) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    bg_dir = Path(settings.maps_dir) / "backgrounds"
    for f in bg_dir.glob(f"{name}.*"):
        f.unlink(missing_ok=True)
    map_service.update_map(name, MapUpdate(background_image=None))


# ----- Object sub-resources -----

@router.post("/{name}/objects", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def add_object(
    name: str, obj: MapObject, current_user: User = Depends(get_current_user)
) -> MapConfig:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    try:
        cfg = map_service.add_object(name, obj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg


@router.put("/{name}/objects/{obj_id}", response_model=MapObject)
async def update_object(
    name: str, obj_id: str, updates: dict[str, Any], current_user: User = Depends(get_current_user)
) -> MapObject:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    obj = map_service.update_object(name, obj_id, updates)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    return obj


@router.delete("/{name}/objects/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    name: str, obj_id: str, current_user: User = Depends(get_current_user)
) -> None:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    if not map_service.delete_object(name, obj_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
