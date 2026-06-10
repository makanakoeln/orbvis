"""Tests for user management API endpoints and RBAC logic."""

from __future__ import annotations

import pytest

from app.api.v1.deps import user_has_permission
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

# ---------------------------------------------------------------------------
# user_has_permission — pure unit tests (no DB, no HTTP)
# ---------------------------------------------------------------------------


def _user(is_admin: bool = False) -> User:
    u = User(name="x", password="x", is_active=True, is_admin=is_admin)
    u.roles = []
    return u


def _role_with_perm(mod: str, act: str, obj: str) -> Role:
    perm = Permission(mod=mod, act=act, obj=obj)
    perm.perm_id = 1
    perm.roles = []
    role = Role(name="r")
    role.role_id = 1
    role.permissions = [perm]
    role.users = []
    return role


def test_permission_admin_bypass():
    user = _user(is_admin=True)
    assert user_has_permission(user, "map", "view", "any-board")


def test_permission_wildcard_matches_any_object():
    role = _role_with_perm("map", "view", "*")
    user = _user()
    user.roles = [role]
    assert user_has_permission(user, "map", "view", "board-x")
    assert user_has_permission(user, "map", "view", "board-y")


def test_permission_exact_object_match():
    role = _role_with_perm("map", "view", "my-board")
    user = _user()
    user.roles = [role]
    assert user_has_permission(user, "map", "view", "my-board")
    assert not user_has_permission(user, "map", "view", "other-board")


def test_permission_wrong_mod_or_act():
    role = _role_with_perm("map", "view", "*")
    user = _user()
    user.roles = [role]
    assert not user_has_permission(user, "map", "edit", "*")
    assert not user_has_permission(user, "user", "view", "*")


def test_permission_require_explicit_bypasses_admin():
    user = _user(is_admin=True)
    # Admin without explicit role cannot change another user's password
    assert not user_has_permission(user, "user", "edit", "*", require_explicit=True)


def test_permission_require_explicit_with_role():
    role = _role_with_perm("user", "edit", "*")
    user = _user(is_admin=True)
    user.roles = [role]
    assert user_has_permission(user, "user", "edit", "*", require_explicit=True)


def test_permission_no_roles():
    user = _user(is_admin=False)
    assert not user_has_permission(user, "map", "view", "board")


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_users_admin(client, admin_token, admin_user):
    response = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    names = [u["name"] for u in response.json()]
    assert "admin" in names


@pytest.mark.asyncio
async def test_list_users_non_admin_forbidden(client, regular_token, regular_user):
    response = await client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {regular_token}"}
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_admin(client, admin_token):
    response = await client.post(
        "/api/v1/users",
        json={"name": "newuser", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "newuser"


@pytest.mark.asyncio
async def test_create_user_duplicate_name(client, admin_token, admin_user):
    response = await client.post(
        "/api/v1/users",
        json={"name": "admin", "password": "password123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_user_non_admin_forbidden(client, regular_token, regular_user):
    response = await client.post(
        "/api/v1/users",
        json={"name": "anotheruser", "password": "password123"},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_own_user_profile(client, regular_token, regular_user):
    response = await client.get(
        f"/api/v1/users/{regular_user.user_id}",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "regular"


@pytest.mark.asyncio
async def test_get_other_user_profile_forbidden(client, regular_token, admin_user, regular_user):
    response = await client.get(
        f"/api/v1/users/{admin_user.user_id}",
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_nonexistent_user(client, admin_token):
    response = await client.get(
        "/api/v1/users/99999", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_own_password(client, regular_token, regular_user):
    response = await client.patch(
        f"/api/v1/users/{regular_user.user_id}",
        json={"password": "newpassword123"},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_must_change_password_cleared(client, db_session):
    """User changing their OWN password clears must_change_password flag."""
    from app.core.security import hash_password

    cursor = db_session.execute(
        "INSERT INTO users (name, password, is_active, is_admin, must_change_password) "
        "VALUES (?, ?, 1, 0, 1)",
        ("pwchange", hash_password("oldpw123")),
    )
    user_id = cursor.lastrowid

    login = await client.post(
        "/api/v1/auth/login", json={"username": "pwchange", "password": "oldpw123"}
    )
    token = login.json()["access_token"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        json={"password": "newpassword123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is False


@pytest.mark.asyncio
async def test_update_other_user_password_requires_explicit_permission(
    client, regular_token, admin_user, regular_user
):
    response = await client.patch(
        f"/api/v1/users/{admin_user.user_id}",
        json={"password": "newpassword123"},
        headers={"Authorization": f"Bearer {regular_token}"},
    )
    # regular user has no user/edit/* permission
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_user_admin(client, admin_token, db_session):
    from app.core.security import hash_password

    cursor = db_session.execute(
        "INSERT INTO users (name, password, is_active, is_admin, must_change_password) "
        "VALUES (?, ?, 1, 0, 0)",
        ("todelete", hash_password("x")),
    )
    user_id = cursor.lastrowid

    response = await client.delete(
        f"/api/v1/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_self_forbidden(client, admin_token, admin_user):
    response = await client.delete(
        f"/api/v1/users/{admin_user.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_nonexistent_user(client, admin_token):
    response = await client.delete(
        "/api/v1/users/99999", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_and_remove_role(client, admin_token, admin_user, db_session):
    cursor = db_session.execute("INSERT INTO roles (name) VALUES (?)", ("testrole",))
    role_id = cursor.lastrowid

    response = await client.post(
        f"/api/v1/users/{admin_user.user_id}/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    role_names = [r["name"] for r in response.json()["roles"]]
    assert "testrole" in role_names

    response = await client.delete(
        f"/api/v1/users/{admin_user.user_id}/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_assign_role_not_found(client, admin_token, admin_user):
    response = await client.post(
        f"/api/v1/users/{admin_user.user_id}/roles/99999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# update_user hardening: rename conflicts + self-service field restriction
# ---------------------------------------------------------------------------


async def _create_user(client, admin_token, name, password="password123"):
    resp = await client.post(
        "/api/v1/users",
        json={"name": name, "password": password},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()


@pytest.mark.asyncio
async def test_rename_to_taken_username_yields_409(client, admin_token):
    a = await _create_user(client, admin_token, "rename-a")
    await _create_user(client, admin_token, "rename-b")
    resp = await client.patch(
        f"/api/v1/users/{a['user_id']}",
        json={"name": "rename-b"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_self_service_cannot_change_administrative_fields(client, admin_token):
    created = await _create_user(client, admin_token, "selfsvc", password="initial-pw")
    login = await client.post(
        "/api/v1/auth/login", json={"username": "selfsvc", "password": "initial-pw"}
    )
    token = login.json()["access_token"]
    resp = await client.patch(
        f"/api/v1/users/{created['user_id']}",
        json={
            "name": "hijacked",
            "is_active": False,
            "must_change_password": True,
            "theme": "dark",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "selfsvc"
    assert body["is_active"] is True
    assert body["must_change_password"] is False
    assert body["theme"] == "dark"
