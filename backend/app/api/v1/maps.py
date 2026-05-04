"""Map-related endpoints — currently just a disk-cached tile proxy.

OrbVis worldmap boards default to OpenStreetMap tiles, which can be slow to
fetch from a server with limited internet bandwidth (8+ seconds per tile in
the worst case observed). We proxy and cache them on disk: tiles change
rarely, so after warm-up the map renders nearly instantly. The cache lives
under ``<boards_dir>/../tiles`` and can be wiped without consequence.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, Header, HTTPException, Response, status
from fastapi import Path as PathParam

from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# {s} round-robins across a/b/c subdomains; pick deterministically per (x,y)
# so retries hit the same edge cache.
_UPSTREAM_TEMPLATE = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
_UPSTREAM_SUBDOMAINS = ("a", "b", "c")
_FETCH_TIMEOUT = 30.0
# Per-tile lock so two concurrent requests for the same tile don't both fetch.
_inflight: dict[tuple[int, int, int], asyncio.Lock] = {}
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """Lazy module-level httpx client to reuse the connection pool across tiles."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=_FETCH_TIMEOUT,
            headers={"User-Agent": "OrbVis/1.0 tile-proxy"},
        )
    return _client


def _tiles_dir() -> Path:
    d = Path(settings.boards_dir).parent / "tiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tile_path(z: int, x: int, y: int) -> Path:
    return _tiles_dir() / str(z) / str(x) / f"{y}.png"


async def _fetch_upstream(z: int, x: int, y: int) -> bytes:
    sub = _UPSTREAM_SUBDOMAINS[(x + y) % len(_UPSTREAM_SUBDOMAINS)]
    url = _UPSTREAM_TEMPLATE.format(s=sub, z=z, x=x, y=y)
    resp = await _get_client().get(url)
    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream returned {resp.status_code} for tile {z}/{x}/{y}",
        )
    return resp.content


@router.get("/tiles/{z}/{x}/{y}.png")
async def get_tile(
    z: int = PathParam(..., ge=0, le=20),
    x: int = PathParam(..., ge=0),
    y: int = PathParam(..., ge=0),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
) -> Response:
    if x >= 1 << z or y >= 1 << z:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tile coordinates out of range for zoom",
        )

    cache_path = _tile_path(z, x, y)
    cached = _read_cached(cache_path)
    if cached is not None:
        return _png_response(cached, if_none_match)

    key = (z, x, y)
    lock = _inflight.setdefault(key, asyncio.Lock())
    try:
        async with lock:
            # Re-check after acquiring the lock — another coroutine may have
            # already populated the cache while we were waiting.
            cached = _read_cached(cache_path)
            if cached is not None:
                return _png_response(cached, if_none_match)

            data: bytes
            try:
                data = await _fetch_upstream(z, x, y)
            except httpx.HTTPError as e:
                logger.warning("Tile fetch failed for %s/%s/%s: %s", z, x, y, e)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Upstream tile fetch failed",
                ) from e

            cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache_path.with_suffix(".png.tmp")
            try:
                tmp.write_bytes(data)
                tmp.replace(cache_path)
            except OSError as e:
                logger.warning("Tile cache write failed for %s/%s/%s: %s", z, x, y, e)
                tmp.unlink(missing_ok=True)

            return _png_response(data, if_none_match)
    finally:
        _inflight.pop(key, None)


def _read_cached(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return data or None


def _png_response(data: bytes, if_none_match: str | None = None) -> Response:
    etag = f'"{hashlib.md5(data, usedforsecurity=False).hexdigest()}"'
    headers = {
        "Cache-Control": "public, max-age=86400",
        "ETag": etag,
    }
    if if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(content=data, media_type="image/png", headers=headers)
