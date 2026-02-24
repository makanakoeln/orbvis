"""Authentication business logic."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenResponse
from app.schemas.user import UserCreate

logger = logging.getLogger(__name__)


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    """Return User if credentials are valid, else None."""
    result = await db.execute(select(User).where(User.name == username))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password):
        return None
    if not user.is_active:
        return None
    return user


def create_tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.user_id),
        refresh_token=create_refresh_token(user.user_id),
    )


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        name=data.name,
        password=hash_password(data.password),
        is_active=data.is_active,
        is_admin=data.is_admin,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
