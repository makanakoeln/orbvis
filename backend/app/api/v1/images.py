"""Image library management endpoints."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import TypedDict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_current_user, require_configure
from app.core.config import settings
from app.core.image_security import ICON_MIME_TYPES, ICON_SUFFIXES, is_valid_image
from app.models.user import User
from app.services import board_service

router = APIRouter()


class ImageListEntry(TypedDict):
    name: str
    url: str
    builtin: bool


class ImageUsageEntry(TypedDict):
    board: str
    alias: str | None
    object_ids: list[str]
    is_background: bool


_MAX_ICON_BYTES = 2 * 1024 * 1024  # 2 MB
_BUILTIN_DIR = Path(__file__).resolve().parents[2] / "builtin_icons"

# Stems are restricted to the same safe charset as board names — uploads with
# e.g. a Windows path in the filename would otherwise persist a file that the
# delete/usage endpoints (which reject '\\') can never address again.
_UNSAFE_STEM_CHARS = re.compile(r"[^a-zA-Z0-9_\-]")


def _require_valid_image_name(name: str) -> None:
    if "/" in name or "\\" in name or name in ("", ".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")


def _images_dir() -> Path:
    d = Path(settings.boards_dir).parent / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _builtin_names() -> set[str]:
    if not _BUILTIN_DIR.is_dir():
        return set()
    return {
        p.name for p in _BUILTIN_DIR.iterdir() if p.is_file() and p.suffix.lower() in ICON_SUFFIXES
    }


def _is_builtin(name: str) -> bool:
    return name in _builtin_names()


def _find_image_usage(name: str) -> list[ImageUsageEntry]:
    """Return all boards that reference *name* as object icon or background."""
    usage: list[ImageUsageEntry] = []
    for board in board_service.list_boards():
        cfg = board_service.get_board(board.name)
        if cfg is None:
            continue
        object_ids: list[str] = []
        for obj in cfg.objects:
            obj_image = obj.image_src
            if obj.display is not None and obj.display.image:
                obj_image = obj.display.image
            if obj_image == name:
                object_ids.append(obj.id)
        is_background = cfg.background_image == name
        if object_ids or is_background:
            usage.append(
                {
                    "board": cfg.name,
                    "alias": cfg.alias,
                    "object_ids": object_ids,
                    "is_background": is_background,
                }
            )
    return usage


@router.get("", response_model=list[ImageListEntry])
async def list_images(
    _current_user: User = Depends(get_current_user),
) -> list[ImageListEntry]:
    d = _images_dir()
    builtins = _builtin_names()
    result: list[ImageListEntry] = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in ICON_SUFFIXES:
            result.append(
                {"name": f.name, "url": f"images/{f.name}", "builtin": f.name in builtins}
            )
    return result


@router.get("/{name}/usage", response_model=list[ImageUsageEntry])
async def image_usage(
    name: str,
    _current_user: User = Depends(get_current_user),
) -> list[ImageUsageEntry]:
    _require_valid_image_name(name)
    return _find_image_usage(name)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(require_configure),
) -> JSONResponse:
    if file.content_type not in ICON_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type",
        )

    contents = await file.read(_MAX_ICON_BYTES + 1)
    if len(contents) > _MAX_ICON_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file too large (max 2 MB)",
        )

    # GIF stays out of icons (ICON_MIME_TYPES has no image/gif) even when the
    # client fakes the Content-Type — the magic-byte check enforces it too.
    if not is_valid_image(contents, allow_gif=False):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match a supported image format",
        )

    raw_suffix = Path(file.filename or "").suffix.lower()
    suffix = raw_suffix if raw_suffix in ICON_SUFFIXES else ".png"
    stem = _UNSAFE_STEM_CHARS.sub("_", Path(file.filename or "image").stem) or "image"
    filename = stem + suffix
    if _is_builtin(filename):
        # DELETE protects builtins; uploads must not overwrite them either —
        # a builtin icon is referenced across boards and silently replacing
        # it would change every board at once.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in images cannot be overwritten",
        )

    d = _images_dir()
    fd, tmp_path = tempfile.mkstemp(dir=d, prefix="upload_", suffix=suffix)
    try:
        try:
            os.write(fd, contents)
        finally:
            os.close(fd)
        Path(tmp_path).replace(d / filename)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    builtin = _is_builtin(filename)
    return JSONResponse(
        {"name": filename, "url": f"images/{filename}", "builtin": builtin},
        status_code=status.HTTP_201_CREATED,
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    name: str,
    force: bool = False,
    _: User = Depends(require_configure),
) -> None:
    d = _images_dir().resolve()
    # Reject obvious traversal attempts before hitting the filesystem.
    _require_valid_image_name(name)
    if _is_builtin(name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Built-in images cannot be deleted",
        )
    # Resolve both paths strictly and compare via is_relative_to so symlinks
    # pointing outside the images dir are caught — str.startswith could be
    # tricked by a symlink whose target lives above the images dir.
    try:
        path = (d / name).resolve(strict=True)
    except (OSError, RuntimeError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Image '{name}' not found"
        ) from None
    if not path.is_relative_to(d):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    if not force:
        usage = _find_image_usage(name)
        if usage:
            # 409 Conflict signals to the client: image still in use, force=true required.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": f"Image '{name}' is in use",
                    "usage": usage,
                },
            )
    path.unlink()
