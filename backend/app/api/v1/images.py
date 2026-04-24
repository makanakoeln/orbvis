"""Image library management endpoints."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import TypedDict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_current_user, require_admin
from app.core.config import settings
from app.core.image_security import is_valid_image
from app.models.user import User

router = APIRouter()


class ImageListEntry(TypedDict):
    name: str
    url: str


_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
_MAX_ICON_BYTES = 2 * 1024 * 1024  # 2 MB


def _images_dir() -> Path:
    d = Path(settings.boards_dir).parent / "images"
    d.mkdir(parents=True, exist_ok=True)
    return d


@router.get("", response_model=list[ImageListEntry])
async def list_images(
    _current_user: User = Depends(get_current_user),
) -> list[ImageListEntry]:
    d = _images_dir()
    result: list[ImageListEntry] = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in _ALLOWED_SUFFIXES:
            result.append({"name": f.name, "url": f"images/{f.name}"})
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
) -> JSONResponse:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
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

    if not is_valid_image(contents):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match a supported image format",
        )

    raw_suffix = Path(file.filename or "").suffix.lower()
    suffix = raw_suffix if raw_suffix in _ALLOWED_SUFFIXES else ".png"
    stem = Path(file.filename or "image").stem
    filename = stem + suffix

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

    return JSONResponse(
        {"name": filename, "url": f"images/{filename}"}, status_code=status.HTTP_201_CREATED
    )


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    name: str,
    _: User = Depends(require_admin),
) -> None:
    d = _images_dir().resolve()
    # Reject obvious traversal attempts before hitting the filesystem.
    if "/" in name or "\\" in name or name in ("", ".", ".."):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
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
    path.unlink()
