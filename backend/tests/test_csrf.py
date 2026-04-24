"""Tests for CSRFOriginMiddleware.

Bearer-token and body-authed calls must pass freely; cookie-authed mutations
from unexpected origins must be rejected.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_bearer_authed_mutation_passes_without_origin(client, admin_token):
    """POST with Bearer token and no Origin header must succeed."""
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
