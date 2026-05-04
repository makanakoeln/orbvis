"""Auth endpoint tests."""

import pytest

from app.core.ratelimit import login_limiter


@pytest.fixture(autouse=True)
def _reset_login_limiter():
    """Login limiter is in-memory and shared across tests; clear it each run
    so a previous test's failed-login spam doesn't leak into the next test."""
    login_limiter._calls.clear()
    yield
    login_limiter._calls.clear()


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    response = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    response = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me(client, admin_token):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "admin"
    assert data["is_admin"] is True


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client, admin_user):
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    refresh_token = login.json()["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_refresh_token_rotation_invalidates_old(client, admin_user):
    """A refresh token must not be reusable after rotation."""
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    old_refresh = login.json()["refresh_token"]
    # First refresh rotates the token.
    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    # Using the old refresh token again must be rejected.
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert second.status_code == 401
    # The newly issued refresh token should still work.
    new_refresh = first.json()["refresh_token"]
    third = await client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert third.status_code == 200


@pytest.mark.asyncio
async def test_login_throttled_after_repeated_failures(client, admin_user):
    """After login_limiter._max failures from the same client IP, the next
    attempt returns 429 with a Retry-After header — even with the correct
    password (the limiter blocks before authentication runs)."""
    for _ in range(login_limiter._max):
        await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    response = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client, admin_user):
    """Submitting an access token (type=access) where a refresh token is
    expected must fail closed — not authenticate the caller."""
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    access_token = login.json()["access_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_garbage(client):
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"})
    assert response.status_code == 401
