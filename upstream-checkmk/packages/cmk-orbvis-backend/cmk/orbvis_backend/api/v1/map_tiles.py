#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Map-related endpoints — currently just a disk-cached tile proxy.

OrbVis worldmap maps default to OpenStreetMap tiles, which can be slow to
fetch from a server with limited internet bandwidth (8+ seconds per tile in
the worst case observed). We proxy and cache them on disk: tiles change
rarely, so after warm-up the map renders nearly instantly. The cache lives
under ``<maps_dir>/../tiles`` and can be wiped without consequence.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi import Path as PathParam

from cmk.orbvis_backend.core.config import settings
from cmk.orbvis_backend.core.database import get_db
from cmk.orbvis_backend.core.ratelimit import tile_fetch_limiter
from cmk.orbvis_backend.core.version import APP_VERSION
from cmk.orbvis_backend.services.auth_service import authenticate_url_token

logger = logging.getLogger(__name__)
router = APIRouter()

# OSM's tile policy requires the bare host (the a/b/c sharding subdomains are
# deprecated under HTTP/2) and a clear, identifying User-Agent (not a library
# default). https://operations.osmfoundation.org/policies/tiles/
_UPSTREAM_TEMPLATE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
_USER_AGENT = f"OrbVis/{APP_VERSION}"
_FETCH_TIMEOUT = 30.0
# OSM policy floor: cache at least 7 days when upstream freshness can't be read.
_MIN_FRESH_SECONDS = 7 * 24 * 3600
# Per-tile lock so two concurrent requests for the same tile don't both fetch.
_inflight: dict[tuple[int, int, int], asyncio.Lock] = {}
_client: httpx.AsyncClient | None = None

# Hard ceiling for the on-disk cache: tiles are written on every cache miss,
# and at z=20 there are 2^40 possible coordinates — without a cap an abusive
# client could fill the disk. Beyond the cap tiles are still proxied, just no
# longer cached. Size is tracked incrementally after one lazy scan.
_MAX_CACHE_BYTES = 2 * 1024**3
_cache_bytes: int | None = None
_cache_full_logged = False


def _get_client() -> httpx.AsyncClient:
    """Lazy module-level httpx client to reuse the connection pool across tiles."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=_FETCH_TIMEOUT,
            headers={"User-Agent": _USER_AGENT},
        )
    return _client


def _tiles_dir() -> Path:
    d = Path(settings.maps_dir).parent / "tiles"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _tile_path(z: int, x: int, y: int) -> Path:
    return _tiles_dir() / str(z) / str(x) / f"{y}.png"


@dataclass
class _TileMeta:
    etag: str | None
    last_modified: str | None
    expires_at: float


def _freshness_deadline(headers: httpx.Headers, now: float) -> float:
    cache_control = headers.get("Cache-Control", "")
    match = re.search(r"max-age=(\d+)", cache_control)
    if match:
        return now + int(match.group(1))
    expires = headers.get("Expires")
    if expires:
        try:
            return float(parsedate_to_datetime(expires).timestamp())
        except (TypeError, ValueError):
            pass
    return now + _MIN_FRESH_SECONDS


def _meta_from_headers(headers: httpx.Headers, now: float, prev: _TileMeta | None) -> _TileMeta:
    # A 304 carries no validators of its own — keep the ones we already stored.
    return _TileMeta(
        etag=headers.get("ETag") or (prev.etag if prev else None),
        last_modified=headers.get("Last-Modified") or (prev.last_modified if prev else None),
        expires_at=_freshness_deadline(headers, now),
    )


async def _fetch_upstream(z: int, x: int, y: int, validators: _TileMeta | None) -> httpx.Response:
    url = _UPSTREAM_TEMPLATE.format(z=z, x=x, y=y)
    headers: dict[str, str] = {}
    if validators is not None:
        if validators.etag:
            headers["If-None-Match"] = validators.etag
        if validators.last_modified:
            headers["If-Modified-Since"] = validators.last_modified
    return await _get_client().get(url, headers=headers)


@router.get("/tiles/{z}/{x}/{y}.png")
async def get_tile(
    request: Request,
    z: int = PathParam(..., ge=0, le=20),
    x: int = PathParam(..., ge=0),
    y: int = PathParam(..., ge=0),
    token: str = Query(..., description="Stream ticket or access token (<img> can't set headers)"),
    if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    db: sqlite3.Connection = Depends(get_db),
) -> Response:
    # Same ?token= pattern as the SSE endpoint: tile fetches come from <img>
    # elements, which cannot carry an Authorization header. Rate limiting on
    # top keeps even an authenticated client from filling cache/bandwidth.
    client_ip = request.client.host if request.client else "unknown"
    if tile_fetch_limiter.is_blocked(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limited")
    tile_fetch_limiter.record(client_ip)
    user = await authenticate_url_token(db, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if x >= 1 << z or y >= 1 << z:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tile coordinates out of range for zoom",
        )

    cache_path = _tile_path(z, x, y)
    cached = _read_cached(cache_path)
    meta = _read_meta(cache_path)
    if cached is not None and meta is not None and time.time() < meta.expires_at:
        return _png_response(cached, if_none_match)

    key = (z, x, y)
    # Locks stay in the dict for the process lifetime: popping in a finally
    # would release the key while other coroutines still wait on the same
    # lock, letting a third request create a fresh lock and fetch in
    # parallel. Growth is bounded by the distinct tiles actually viewed.
    lock = _inflight.setdefault(key, asyncio.Lock())
    async with lock:
        # Re-check after acquiring the lock — another coroutine may have
        # already refreshed the cache while we were waiting.
        cached = _read_cached(cache_path)
        meta = _read_meta(cache_path)
        now = time.time()
        if cached is not None and meta is not None and now < meta.expires_at:
            return _png_response(cached, if_none_match)

        validators = meta if cached is not None else None
        try:
            resp = await _fetch_upstream(z, x, y, validators)
            now = time.time()
            if resp.status_code == 304 and cached is not None:
                _write_meta(cache_path, _meta_from_headers(resp.headers, now, meta))
                return _png_response(cached, if_none_match)
            if resp.status_code == 200:
                data = resp.content
                _write_cache(cache_path, data)
                _write_meta(cache_path, _meta_from_headers(resp.headers, now, None))
                return _png_response(data, if_none_match)
            upstream_error: Exception = HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream returned {resp.status_code} for tile {z}/{x}/{y}",
            )
        except httpx.HTTPError as e:
            upstream_error = e

        # Reached only on upstream failure: a stale tile beats a hard error
        # (and spares OSM a retry storm); only propagate when nothing cached.
        if cached is not None:
            logger.warning(
                "Tile fetch/revalidation failed for %s/%s/%s, serving stale: %s",
                z,
                x,
                y,
                upstream_error,
            )
            return _png_response(cached, if_none_match)
        logger.warning("Tile fetch failed for %s/%s/%s: %s", z, x, y, upstream_error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream tile fetch failed",
        ) from upstream_error


def _read_cached(path: Path) -> bytes | None:
    if not path.is_file():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    return data or None


def _cache_has_room(cache_path: Path, incoming: int) -> bool:
    global _cache_bytes, _cache_full_logged
    if _cache_bytes is None:
        _cache_bytes = sum(f.stat().st_size for f in _tiles_dir().rglob("*.png"))
    try:
        previous = cache_path.stat().st_size
    except OSError:
        previous = 0
    if _cache_bytes - previous + incoming > _MAX_CACHE_BYTES:
        if not _cache_full_logged:
            _cache_full_logged = True
            logger.warning(
                "Tile cache reached %d bytes — serving tiles uncached; wipe %s to reset",
                _MAX_CACHE_BYTES,
                _tiles_dir(),
            )
        return False
    _cache_bytes += incoming - previous
    return True


def _write_cache(cache_path: Path, data: bytes) -> None:
    if not _cache_has_room(cache_path, len(data)):
        return
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_name(cache_path.name + ".tmp")
    try:
        tmp.write_bytes(data)
        tmp.replace(cache_path)
    except OSError as e:
        logger.warning("Tile cache write failed for %s: %s", cache_path, e)
        tmp.unlink(missing_ok=True)


def _meta_path(cache_path: Path) -> Path:
    return cache_path.with_name(cache_path.name + ".meta")


def _read_meta(cache_path: Path) -> _TileMeta | None:
    try:
        raw = _meta_path(cache_path).read_text()
    except OSError:
        return None
    try:
        d = json.loads(raw)
        return _TileMeta(
            etag=d.get("etag"),
            last_modified=d.get("last_modified"),
            expires_at=float(d["expires_at"]),
        )
    except (ValueError, KeyError, TypeError):
        return None


def _write_meta(cache_path: Path, meta: _TileMeta) -> None:
    path = _meta_path(cache_path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        tmp.write_text(
            json.dumps(
                {
                    "etag": meta.etag,
                    "last_modified": meta.last_modified,
                    "expires_at": meta.expires_at,
                }
            )
        )
        tmp.replace(path)
    except OSError as e:
        logger.warning("Tile meta write failed for %s: %s", cache_path, e)
        tmp.unlink(missing_ok=True)


def _png_response(data: bytes, if_none_match: str | None = None) -> Response:
    etag = f'"{hashlib.md5(data, usedforsecurity=False).hexdigest()}"'
    headers = {
        "Cache-Control": "public, max-age=86400",
        "ETag": etag,
    }
    if if_none_match == etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(content=data, media_type="image/png", headers=headers)
