"""Icon set management endpoints."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.v1.deps import get_current_user, require_admin
from app.core.config import settings
from app.models.user import User

router = APIRouter()

_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}
_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".webp"}
_MAX_ICON_BYTES = 2 * 1024 * 1024  # 2 MB


def _icons_dir() -> Path:
    d = Path(settings.maps_dir).parent / "icons"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _is_valid_icon(content: bytes) -> bool:
    h = content[:16]
    if h[:4] == b"\x89PNG":
        return True
    if h[:3] == b"\xff\xd8\xff":
        return True
    if h[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return True
    if b"<svg" in content[:512].lower():
        return True
    return False


@router.get("", response_model=list[dict])
async def list_icons(
    _current_user: User = Depends(get_current_user),
) -> list[dict]:
    d = _icons_dir()
    result = []
    for f in sorted(d.iterdir()):
        if f.is_file() and f.suffix.lower() in _ALLOWED_SUFFIXES:
            result.append({"name": f.name, "url": f"/icons/{f.name}"})
    return result


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_icon(
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
            detail="Icon file too large (max 2 MB)",
        )

    if not _is_valid_icon(contents):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match a supported image format",
        )

    raw_suffix = Path(file.filename or "").suffix.lower()
    suffix = raw_suffix if raw_suffix in _ALLOWED_SUFFIXES else ".png"
    stem = Path(file.filename or "icon").stem
    filename = stem + suffix

    d = _icons_dir()
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

    return JSONResponse({"name": filename, "url": f"/icons/{filename}"}, status_code=201)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_icon(
    name: str,
    _: User = Depends(require_admin),
) -> None:
    d = _icons_dir()
    # Prevent path traversal
    path = (d / name).resolve()
    if not str(path).startswith(str(d.resolve())):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Icon '{name}' not found")
    path.unlink()
