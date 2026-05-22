"""Shared FastAPI dependencies."""

from __future__ import annotations

import sqlite3

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.database import get_db
from app.integrations import checkmk as cmk_integration
from app.models.user import User
from app.services.auth_service import authenticate_bearer_token

bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: sqlite3.Connection = Depends(get_db),
) -> User:
    user = await authenticate_bearer_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


def _check_board_permission(user: User, board_name: str, action: str) -> bool:
    if settings.checkmk_omd_root:
        return user.is_admin or cmk_integration.check_board_permission(
            user.name, board_name, action
        )
    return user_has_permission(user, "map", action, board_name)


def can_view_board(user: User, board_name: str) -> bool:
    return _check_board_permission(user, board_name, "view")


def resolve_auth_user(username: str, is_admin: bool) -> str | None:
    """Username to pass as Livestatus AuthUser, or None for unrestricted access.

    Admins and users with CMK ``general.see_all`` bypass contact-group filtering.
    Outside Checkmk integrations there is no AuthUser concept, so this returns
    None unconditionally.
    """
    if not settings.checkmk_omd_root:
        return None
    if is_admin:
        return None
    if cmk_integration.check_checkmk_permission(username, "general.see_all"):
        return None
    return username


def can_view_board_by_name(username: str, board_name: str) -> bool:
    """Permission check using only a username string (for background tasks).

    Applicable only when CHECKMK_OMD_ROOT is configured; non-CMK setups need a
    User object for OrbVis RBAC and return True here.
    """
    if settings.checkmk_omd_root:
        return cmk_integration.check_board_permission(username, board_name, "view")
    return True


def can_edit_board(user: User, board_name: str) -> bool:
    return _check_board_permission(user, board_name, "edit")


def user_has_permission(
    user: User, mod: str, act: str, obj: str, require_explicit: bool = False
) -> bool:
    """Return True if user has the requested permission.

    is_admin grants all permissions by default. Set require_explicit=True for
    sensitive operations (e.g. changing another user's password) where an
    explicit role assignment is required regardless of admin status.
    """
    if not require_explicit and user.is_admin:
        return True
    for role in user.roles:
        for perm in role.permissions:
            if perm.mod == mod and perm.act == act and perm.obj in ("*", obj):
                return True
    return False
