"""Tile proxy: caching, OSM-policy revalidation and graceful staleness."""

from __future__ import annotations

import time

import httpx
import pytest

from app.api.v1 import maps
from app.core.version import APP_VERSION


class _FakeClient:
    def __init__(self, responses: list[httpx.Response | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, url: str, headers: dict[str, str] | None = None) -> httpx.Response:
        self.calls.append((url, headers or {}))
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def fake_upstream(tmp_path, monkeypatch):
    monkeypatch.setattr(maps, "_tiles_dir", lambda: tmp_path)
    monkeypatch.setattr(maps, "_cache_bytes", None)
    monkeypatch.setattr(maps, "_cache_full_logged", False)

    def _install(responses: list[httpx.Response | Exception]) -> _FakeClient:
        fake = _FakeClient(responses)
        monkeypatch.setattr(maps, "_get_client", lambda: fake)
        return fake

    return _install


def _png(content: bytes, **headers: str) -> httpx.Response:
    return httpx.Response(200, headers=headers, content=content)


@pytest.mark.asyncio
async def test_bare_host_and_identifying_user_agent():
    assert "{s}" not in maps._UPSTREAM_TEMPLATE
    assert maps._UPSTREAM_TEMPLATE.startswith("https://tile.openstreetmap.org/")
    assert maps._USER_AGENT == f"OrbVis/{APP_VERSION}"
    upstream = maps._get_client()
    try:
        assert upstream.headers["user-agent"] == f"OrbVis/{APP_VERSION}"
    finally:
        await upstream.aclose()
        maps._client = None


@pytest.mark.asyncio
async def test_fresh_cache_skips_upstream(client, admin_token, fake_upstream):
    fake = fake_upstream([_png(b"PNG1", **{"Cache-Control": "max-age=3600"})])

    first = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    assert first.status_code == 200
    assert first.content == b"PNG1"

    second = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    assert second.status_code == 200
    assert second.content == b"PNG1"

    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_stale_tile_revalidates_with_conditional_request(client, admin_token, fake_upstream):
    fake = fake_upstream(
        [
            _png(b"PNG1", **{"Cache-Control": "max-age=0", "ETag": '"abc"'}),
            httpx.Response(304, headers={"Cache-Control": "max-age=3600"}),
        ]
    )

    await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    second = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")

    assert second.status_code == 200
    assert second.content == b"PNG1"
    assert len(fake.calls) == 2
    assert fake.calls[1][1].get("If-None-Match") == '"abc"'

    # The 304 carried a fresh max-age, so the next hit is served from cache.
    third = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    assert third.content == b"PNG1"
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_stale_tile_served_when_upstream_fails(client, admin_token, fake_upstream):
    fake = fake_upstream(
        [
            _png(b"PNG1", **{"Cache-Control": "max-age=0"}),
            httpx.ConnectError("boom"),
        ]
    )

    await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    second = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")

    assert second.status_code == 200
    assert second.content == b"PNG1"
    assert len(fake.calls) == 2


@pytest.mark.asyncio
async def test_error_when_no_cache_and_upstream_fails(client, admin_token, fake_upstream):
    fake_upstream([httpx.ConnectError("boom")])

    resp = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_missing_headers_fall_back_to_seven_day_floor(client, admin_token, fake_upstream):
    fake = fake_upstream([_png(b"PNG1")])

    await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    meta = maps._read_meta(maps._tile_path(2, 1, 1))
    assert meta is not None
    assert abs(meta.expires_at - (time.time() + maps._MIN_FRESH_SECONDS)) < 60
    # Served from cache on the next hit — no second upstream call within the floor.
    await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_tile_requires_valid_token(client, fake_upstream):
    fake_upstream([_png(b"PNG1")])
    missing = await client.get("/api/v1/maps/tiles/2/1/1.png")
    assert missing.status_code == 422
    invalid = await client.get("/api/v1/maps/tiles/2/1/1.png?token=not-a-jwt")
    assert invalid.status_code == 401


@pytest.mark.asyncio
async def test_cache_cap_stops_writes_but_still_serves(
    client, admin_token, fake_upstream, monkeypatch
):
    fake_upstream([_png(b"PNG1"), _png(b"PNG2")])
    monkeypatch.setattr(maps, "_MAX_CACHE_BYTES", 0)
    first = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    assert first.status_code == 200
    assert first.content == b"PNG1"
    assert not maps._tile_path(2, 1, 1).exists()
    # Not cached, so the next request goes upstream again.
    second = await client.get(f"/api/v1/maps/tiles/2/1/1.png?token={admin_token}")
    assert second.content == b"PNG2"
