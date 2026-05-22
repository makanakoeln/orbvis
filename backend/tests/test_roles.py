"""Tests for role and permission management API endpoints."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Roles CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_roles_empty(client, admin_token):
    response = await client.get("/api/v1/roles", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_roles_non_admin_forbidden(client, regular_token, regular_user):
    response = await client.get(
        "/api/v1/roles", headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_role(client, admin_token):
    response = await client.post(
        "/api/v1/roles",
        json={"name": "viewers"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "viewers"


@pytest.mark.asyncio
async def test_create_role_duplicate_name(client, admin_token):
    await client.post(
        "/api/v1/roles",
        json={"name": "dupe"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/v1/roles",
        json={"name": "dupe"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_role(client, admin_token, db_session):
    cursor = db_session.execute("INSERT INTO roles (name) VALUES (?)", ("myrole",))
    role_id = cursor.lastrowid

    response = await client.get(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "myrole"


@pytest.mark.asyncio
async def test_get_role_not_found(client, admin_token):
    response = await client.get(
        "/api/v1/roles/99999", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_role(client, admin_token, db_session):
    cursor = db_session.execute("INSERT INTO roles (name) VALUES (?)", ("todelete",))
    role_id = cursor.lastrowid

    response = await client.delete(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    response = await client.get(
        f"/api/v1/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_role_not_found(client, admin_token):
    response = await client.delete(
        "/api/v1/roles/99999", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Permissions CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_permissions_empty(client, admin_token):
    response = await client.get(
        "/api/v1/roles/permissions/", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_permission(client, admin_token):
    response = await client.post(
        "/api/v1/roles/permissions/",
        json={"mod": "map", "act": "view", "obj": "*"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["mod"] == "map"
    assert data["act"] == "view"
    assert data["obj"] == "*"


# ---------------------------------------------------------------------------
# Role ↔ Permission assignment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_and_remove_permission(client, admin_token, db_session):
    role_id = db_session.execute("INSERT INTO roles (name) VALUES (?)", ("r1",)).lastrowid
    perm_id = db_session.execute(
        "INSERT INTO permissions (mod, act, obj) VALUES (?, ?, ?)",
        ("map", "view", "test-board"),
    ).lastrowid

    response = await client.post(
        f"/api/v1/roles/{role_id}/permissions/{perm_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert any(p["perm_id"] == perm_id for p in response.json()["permissions"])

    response2 = await client.post(
        f"/api/v1/roles/{role_id}/permissions/{perm_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response2.status_code == 200

    response = await client.delete(
        f"/api/v1/roles/{role_id}/permissions/{perm_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_assign_permission_role_not_found(client, admin_token, db_session):
    perm_id = db_session.execute(
        "INSERT INTO permissions (mod, act, obj) VALUES (?, ?, ?)",
        ("map", "view", "*"),
    ).lastrowid

    response = await client.post(
        f"/api/v1/roles/99999/permissions/{perm_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_permission_perm_not_found(client, admin_token, db_session):
    role_id = db_session.execute("INSERT INTO roles (name) VALUES (?)", ("r2",)).lastrowid

    response = await client.post(
        f"/api/v1/roles/{role_id}/permissions/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404
