"""User management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_admin, user_has_permission
from app.core.database import get_db
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.auth_service import create_user, get_user_by_id

router = APIRouter()


@router.get("", response_model=list[UserRead])
async def list_users(
    db: AsyncSession = Depends(get_db), _: User = Depends(require_admin)
) -> list[UserRead]:
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [UserRead.model_validate(u) for u in users]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserRead:
    # Check uniqueness
    existing = await db.execute(select(User).where(User.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = await create_user(db, data)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    # Users can read their own profile; admins can read any
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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if not current_user.is_admin and current_user.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    update_data = data.model_dump(exclude_none=True)

    # Changing another user's password requires an explicit user/edit role — is_admin alone is not enough
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
    # Non-admins cannot change admin flag
    if not current_user.is_admin:
        update_data.pop("is_admin", None)

    for key, value in update_data.items():
        setattr(user, key, value)

    await db.flush()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    if current_user.user_id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)


@router.post("/{user_id}/roles/{role_id}", response_model=UserRead)
async def assign_role(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> UserRead:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    role_result = await db.execute(select(Role).where(Role.role_id == role_id))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    if role not in user.roles:
        user.roles.append(role)
    await db.flush()
    await db.refresh(user)
    return UserRead.model_validate(user)


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.roles = [r for r in user.roles if r.role_id != role_id]
