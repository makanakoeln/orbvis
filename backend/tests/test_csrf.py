"""Tests for CSRFOriginMiddleware.

Bearer-token and body-authed calls must pass freely; cookie-authed mutations
from unexpected origins must be rejected.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_bearer_authed_mutation_passes_without_origin(
    client, admin_token, tmp_path, monkeypatch
):
    """POST with Bearer token and no Origin header must succeed."""
    monkeypatch.setattr("app.core.config.settings.boards_dir", str(tmp_path))
    monkeypatch.setattr("app.services.board_service.settings.boards_dir", str(tmp_path))
    response = await client.post(
        "/api/v1/boards",
        json={"name": "csrf-bearer", "alias": "x"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_body_authed_refresh_passes_without_origin(client, admin_user):
    """POST /refresh carries credentials in the body, not in a cookie — no CSRF risk."""
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    refresh = login.json()["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cookie_authed_mutation_rejected_without_origin(client):
    """State-changing request with a cookie + no Authorization + no Origin must be rejected."""
    response = await client.post(
        "/api/v1/boards",
        json={"name": "csrf-cookie", "alias": "x"},
        headers={"Cookie": "auth_demo=forged-session-value"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cookie_authed_mutation_rejected_from_foreign_origin(client):
    """Same as above, but with an origin header pointing to an untrusted domain."""
    response = await client.post(
        "/api/v1/boards",
        json={"name": "csrf-foreign", "alias": "x"},
        headers={
            "Cookie": "auth_demo=forged-session-value",
            "Origin": "https://evil.example.com",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_exempt_from_csrf_origin_check(client, admin_user):
    """/login must be reachable without Origin even with a cookie attached (pre-auth)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "secret"},
        headers={"Cookie": "something=irrelevant"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_cookie_authed_mutation_accepted_when_same_origin(client):
    """Same-origin (Origin's host == X-Forwarded-Host) is safe even if the
    Origin string is not literally listed in ALLOWED_ORIGINS — covers OMD
    deployments where the site-FQDN can't be enumerated up-front. The CSRF
    middleware must let the request through; auth then rejects it because
    the cookie is forged. The pre-fix behaviour was a hard 403 from the
    middleware before auth could even look at the request."""
    response = await client.post(
        "/api/v1/boards",
        json={"name": "csrf-same-origin", "alias": "x"},
        headers={
            "Cookie": "auth_demo=forged-session-value",
            "Origin": "https://orbvis.example.com",
            "X-Forwarded-Host": "orbvis.example.com",
        },
    )
    # Same-origin → CSRF middleware lets it through; downstream auth rejects
    # the forged cookie with 401 (not 403, which is the CSRF middleware's code).
    assert response.status_code == 401
