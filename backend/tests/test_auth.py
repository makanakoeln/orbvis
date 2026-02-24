"""Auth endpoint tests."""

import pytest


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
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token(client, admin_user):
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "secret"}
    )
    refresh_token = login.json()["refresh_token"]
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()
