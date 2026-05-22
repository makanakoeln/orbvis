"""User management endpoints."""

from __future__ import annotations

import asyncio
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.deps import get_current_user, require_admin, user_has_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.auth_service import (
    _fetch_user,
    _load_roles_for_user,
    create_user,
    get_user_by_id,
)

router = APIRouter()


@router.get("", response_model=list[UserRead])
async def list_users(
    db: sqlite3.Connection = Depends(get_db), _: User = Depends(require_admin)
) -> list[UserRead]:
    def _list() -> list[User]:
        rows = db.execute(
            "SELECT user_id, name, password, is_active, is_admin, "
            "must_change_password, theme, language FROM users ORDER BY user_id"
        ).fetchall()
        result = []
        for row in rows:
            user = User(
                user_id=row["user_id"],
                name=row["name"],
                password=row["password"],
                is_active=bool(row["is_active"]),
                is_admin=bool(row["is_admin"]),
                must_change_password=bool(row["must_change_password"]),
                theme=row["theme"],
                language=row["language"],
            )
            user.roles = _load_roles_for_user(db, user.user_id)
            result.append(user)
        return result

    users = await asyncio.to_thread(_list)
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    data: UserCreate,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserRead:
    existing = await asyncio.to_thread(
        lambda: db.execute("SELECT 1 FROM users WHERE name = ?", (data.name,)).fetchone()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = await create_user(db, data)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if not current_user.is_admin and current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if not current_user.is_admin and current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = data.model_dump(exclude_none=True)

    # Changing another user's password requires explicit user/edit/* — is_admin alone is not enough.
    if "password" in update_data and current_user.user_id != user_id:
        if not user_has_permission(current_user, "user", "edit", "*", require_explicit=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="user/edit/* permission required to change another user's password",
            )

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if "password" in update_data:
        update_data["password"] = hash_password(update_data.pop("password"))
        update_data["must_change_password"] = False
    if not current_user.is_admin:
        update_data.pop("is_admin", None)

    if update_data:
        # Boolean fields are stored as 0/1 in SQLite.
        for k in ("is_active", "is_admin", "must_change_password"):
            if k in update_data:
                update_data[k] = 1 if update_data[k] else 0

        cols = ", ".join(f"{k} = ?" for k in update_data)
        params = (*update_data.values(), user_id)

        def _update() -> None:
            # `cols` is built from a fixed allowlist (form keys); bandit flags
            # the f-string but the actual values are bound via "?" placeholders.
            db.execute(f"UPDATE users SET {cols} WHERE user_id = ?", params)  # nosec B608

        await asyncio.to_thread(_update)

    user = await get_user_by_id(db, user_id)
    assert user is not None
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: sqlite3.Connection = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    if current_user.user_id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself"
        )
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await asyncio.to_thread(lambda: db.execute("DELETE FROM users WHERE user_id = ?", (user_id,)))


@router.post("/{user_id}/roles/{role_id}", response_model=UserRead)
async def assign_role(
    user_id: int,
    role_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserRead:
    def _assign() -> tuple[User | None, sqlite3.Row | None]:
        u_row = db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)).fetchone()
        r_row = db.execute("SELECT 1 FROM roles WHERE role_id = ?", (role_id,)).fetchone()
        if u_row is None or r_row is None:
            return None, None
        db.execute(
            "INSERT OR IGNORE INTO users2roles (user_id, role_id) VALUES (?, ?)",
            (user_id, role_id),
        )
        user = _fetch_user(db, "user_id = ?", (user_id,))
        return user, r_row

    user, role_row = await asyncio.to_thread(_assign)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found" if role_row is None else "Role not found",
        )
    return UserRead.model_validate(user)


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(
    user_id: int,
    role_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await asyncio.to_thread(
        lambda: db.execute(
            "DELETE FROM users2roles WHERE user_id = ? AND role_id = ?",
            (user_id, role_id),
        )
    )
