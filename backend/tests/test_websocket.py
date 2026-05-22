"""SSE auth + rate-limit tests for /api/v1/sse/boards/{name}.

Covered paths:
  - missing token query param → 422
  - invalid / refresh token   → 401
  - blocked access token      → 401
  - connect rate-limit        → 429 before stream starts
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core import _jwt
from app.core.config import settings
from app.core.ratelimit import ws_connect_limiter
from app.core.security import (
    blocklist_token,
    create_access_token,
    create_refresh_token,
)


def _reset_limiter() -> None:
    ws_connect_limiter._calls.clear()


@pytest.fixture(autouse=True)
def _reset_sse_state():
    _reset_limiter()
    yield
    _reset_limiter()


@pytest.mark.asyncio
async def test_sse_requires_token(client, admin_user):
    response = await client.get("/api/v1/sse/boards/demo")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sse_rejects_refresh_token_instead_of_access(client, admin_user):
    refresh = create_refresh_token(admin_user.user_id)
    response = await client.get(f"/api/v1/sse/boards/demo?token={refresh}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sse_rejects_blocked_access_token(client, admin_user):
    token = create_access_token(admin_user.user_id)
    payload = _jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    jti = str(payload["jti"])
    blocklist_token(jti, datetime.now(UTC) + timedelta(minutes=5))

    response = await client.get(f"/api/v1/sse/boards/demo?token={token}")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sse_rate_limiter_rejects_connection_floods(client, admin_user, monkeypatch):
    """When the rate limiter reports the client as blocked, the SSE endpoint
    refuses the request before any board or auth lookup.
    """
    token = create_access_token(admin_user.user_id)
    monkeypatch.setattr(ws_connect_limiter, "is_blocked", lambda _key: True)

    response = await client.get(f"/api/v1/sse/boards/demo?token={token}")
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_sse_rejects_invalid_token(client, admin_user):
    response = await client.get("/api/v1/sse/boards/demo?token=garbage")
    assert response.status_code == 401
