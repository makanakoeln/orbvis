"""Role and permission management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_admin
from app.core.database import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.permission import PermissionCreate, PermissionRead
from app.schemas.role import RoleCreate, RoleRead

router = APIRouter()


# ---- Roles ----


@router.get("", response_model=list[RoleRead])
async def list_roles(
    db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> list[RoleRead]:
    result = await db.execute(select(Role))
    return [RoleRead.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> RoleRead:
    existing = await db.execute(select(Role).where(Role.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Role name already exists")
    role = Role(name=data.name)
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return RoleRead.model_validate(role)


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    role_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> RoleRead:
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return RoleRead.model_validate(role)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int, db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> None:
    result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    await db.delete(role)


# ---- Permissions ----


@router.get("/permissions/", response_model=list[PermissionRead])
async def list_permissions(
    db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> list[PermissionRead]:
    result = await db.execute(select(Permission))
    return [PermissionRead.model_validate(p) for p in result.scalars().all()]


@router.post("/permissions/", response_model=PermissionRead, status_code=status.HTTP_201_CREATED)
async def create_permission(
    data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> PermissionRead:
    perm = Permission(mod=data.mod, act=data.act, obj=data.obj)
    db.add(perm)
    await db.flush()
    await db.refresh(perm)
    return PermissionRead.model_validate(perm)


@router.post("/{role_id}/permissions/{perm_id}", response_model=RoleRead)
async def assign_permission(
    role_id: int,
    perm_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> RoleRead:
    role_result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    perm_result = await db.execute(select(Permission).where(Permission.perm_id == perm_id))
    perm = perm_result.scalar_one_or_none()
    if perm is None:
        raise HTTPException(status_code=404, detail="Permission not found")
    if perm not in role.permissions:
        role.permissions.append(perm)
    await db.flush()
    await db.refresh(role)
    return RoleRead.model_validate(role)


@router.delete("/{role_id}/permissions/{perm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_permission(
    role_id: int,
    perm_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    role_result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    role.permissions = [p for p in role.permissions if p.perm_id != perm_id]
