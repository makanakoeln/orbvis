"""Role and permission management endpoints."""

from __future__ import annotations

import asyncio
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.deps import require_admin
from app.core.database import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.permission import PermissionCreate, PermissionRead
from app.schemas.role import RoleCreate, RoleRead

router = APIRouter()


def _load_role(db: sqlite3.Connection, role_id: int) -> Role | None:
    row = db.execute("SELECT role_id, name FROM roles WHERE role_id = ?", (role_id,)).fetchone()
    if row is None:
        return None
    role = Role(role_id=row["role_id"], name=row["name"])
    role.permissions = [
        Permission(perm_id=p["perm_id"], mod=p["mod"], act=p["act"], obj=p["obj"])
        for p in db.execute(
            """
            SELECT p.perm_id, p.mod, p.act, p.obj
            FROM permissions p
            JOIN roles2perms r2p ON r2p.perm_id = p.perm_id
            WHERE r2p.role_id = ?
            """,
            (role_id,),
        ).fetchall()
    ]
    return role


@router.get("", response_model=list[RoleRead])
async def list_roles(
    db: sqlite3.Connection = Depends(get_db), _: User = Depends(require_admin)
) -> list[RoleRead]:
    def _list() -> list[Role]:
        return [
            r
            for row in db.execute("SELECT role_id, name FROM roles ORDER BY role_id").fetchall()
            for r in [_load_role(db, row["role_id"])]
            if r is not None
        ]

    roles = await asyncio.to_thread(_list)
    return [RoleRead.model_validate(r) for r in roles]


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_admin),
) -> RoleRead:
    def _create() -> int | None:
        existing = db.execute("SELECT 1 FROM roles WHERE name = ?", (data.name,)).fetchone()
        if existing:
            return None
        cursor = db.execute("INSERT INTO roles (name) VALUES (?)", (data.name,))
        return cursor.lastrowid

    role_id = await asyncio.to_thread(_create)
    if role_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    role = await asyncio.to_thread(_load_role, db, role_id)
    assert role is not None
    return RoleRead.model_validate(role)


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: int, db: sqlite3.Connection = Depends(get_db), _: User = Depends(require_admin)
) -> RoleRead:
    role = await asyncio.to_thread(_load_role, db, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return RoleRead.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int, db: sqlite3.Connection = Depends(get_db), _: User = Depends(require_admin)
) -> None:
    def _delete() -> bool:
        row = db.execute("SELECT 1 FROM roles WHERE role_id = ?", (role_id,)).fetchone()
        if row is None:
            return False
        db.execute("DELETE FROM roles WHERE role_id = ?", (role_id,))
        return True

    if not await asyncio.to_thread(_delete):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")


@router.get("/permissions/", response_model=list[PermissionRead])
async def list_permissions(
    db: sqlite3.Connection = Depends(get_db), _: User = Depends(require_admin)
) -> list[PermissionRead]:
    def _list() -> list[Permission]:
        return [
            Permission(perm_id=r["perm_id"], mod=r["mod"], act=r["act"], obj=r["obj"])
            for r in db.execute(
                "SELECT perm_id, mod, act, obj FROM permissions ORDER BY perm_id"
            ).fetchall()
        ]

    perms = await asyncio.to_thread(_list)
    return [PermissionRead.model_validate(p) for p in perms]


@router.post("/permissions/", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_admin),
) -> PermissionRead:
    def _create() -> Permission:
        cursor = db.execute(
            "INSERT INTO permissions (mod, act, obj) VALUES (?, ?, ?)",
            (data.mod, data.act, data.obj),
        )
        perm_id = cursor.lastrowid
        assert perm_id is not None
        return Permission(perm_id=perm_id, mod=data.mod, act=data.act, obj=data.obj)

    perm = await asyncio.to_thread(_create)
    return PermissionRead.model_validate(perm)


@router.post("/{role_id}/permissions/{perm_id}", response_model=RoleRead)
async def assign_permission(
    role_id: int,
    perm_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_admin),
) -> RoleRead:
    def _assign() -> tuple[Role | None, bool]:
        r = db.execute("SELECT 1 FROM roles WHERE role_id = ?", (role_id,)).fetchone()
        if r is None:
            return None, False
        p = db.execute("SELECT 1 FROM permissions WHERE perm_id = ?", (perm_id,)).fetchone()
        if p is None:
            return None, True
        db.execute(
            "INSERT OR IGNORE INTO roles2perms (role_id, perm_id) VALUES (?, ?)",
            (role_id, perm_id),
        )
        return _load_role(db, role_id), True

    role, role_existed = await asyncio.to_thread(_assign)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found" if role_existed else "Role not found",
        )
    return RoleRead.model_validate(role)


@router.delete("/{role_id}/permissions/{perm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permission(
    role_id: int,
    perm_id: int,
    db: sqlite3.Connection = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    def _delete() -> bool:
        row = db.execute("SELECT 1 FROM roles WHERE role_id = ?", (role_id,)).fetchone()
        if row is None:
            return False
        db.execute(
            "DELETE FROM roles2perms WHERE role_id = ? AND perm_id = ?",
            (role_id, perm_id),
        )
        return True

    if not await asyncio.to_thread(_delete):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
