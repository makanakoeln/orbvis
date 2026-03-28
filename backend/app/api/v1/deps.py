"""Shared FastAPI dependencies."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token, is_token_blocked
from app.integrations import checkmk as cmk_integration
from app.models.user import User
from app.services.auth_service import get_user_by_id

bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode JWT and return the authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: int = int(str(payload["sub"]))
        jti = str(payload.get("jti", ""))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_exception from None

    if jti and is_token_blocked(jti):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def can_view_board(user: User, board_name: str) -> bool:
    """Return True if the user may view the given board.

    When CHECKMK_OMD_ROOT is configured, delegates to the Checkmk permission
    system. Falls back to the OrbVis DB role/permission system otherwise.
    """
    if settings.checkmk_omd_root:
        return user.is_admin or cmk_integration.check_board_permission(
            user.name, board_name, "view"
        )
    return user_has_permission(user, "map", "view", board_name)


def can_view_board_by_name(username: str, board_name: str) -> bool:
    """Check board view permission using only a username string (for background tasks).

    Only applicable when CHECKMK_OMD_ROOT is configured; returns True otherwise
    (non-CMK setups require a User object for OrbVis RBAC checks).
    """
    if settings.checkmk_omd_root:
        return cmk_integration.check_board_permission(username, board_name, "view")
    return True


def can_edit_board(user: User, board_name: str) -> bool:
    """Return True if the user may edit the given board.

    When CHECKMK_OMD_ROOT is configured, delegates to the Checkmk permission
    system. Falls back to the OrbVis DB role/permission system otherwise.
    """
    if settings.checkmk_omd_root:
        return user.is_admin or cmk_integration.check_board_permission(
            user.name, board_name, "edit"
        )
    return user_has_permission(user, "map", "edit", board_name)


def user_has_permission(
    user: User, mod: str, act: str, obj: str, require_explicit: bool = False
) -> bool:
    """Return True if user has the requested permission.

    By default, is_admin grants all permissions. Set require_explicit=True for
    sensitive operations where an explicit role assignment is always required.
    """
    if not require_explicit and user.is_admin:
        return True
    for role in user.roles:
        for perm in role.permissions:
            if perm.mod == mod and perm.act == act and (perm.obj == "*" or perm.obj == obj):
                return True
    return False
