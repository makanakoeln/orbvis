#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared FastAPI dependencies."""

from __future__ import annotations

import sqlite3

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cmk.orbvis_backend.core.config import settings
from cmk.orbvis_backend.core.database import get_db
from cmk.orbvis_backend.integrations import checkmk as cmk_integration
from cmk.orbvis_backend.models.user import User
from cmk.orbvis_backend.services.auth_service import authenticate_bearer_token

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


def can_configure(user: User) -> bool:
    """True if the user may manage connections, images and global settings.

    In Checkmk deployments this honours the ``orbvis.configure`` permission so
    non-admin roles can be granted access. Standalone has no such permission, so
    it stays admin-only.
    """
    if settings.checkmk_omd_root:
        return user.is_admin or cmk_integration.check_configure_permission(user.name)
    return user.is_admin


def can_create_map(user: User) -> bool:
    """True if the user may create or delete maps.

    In Checkmk deployments this honours ``orbvis.edit_all`` (which grants map
    creation per the WATO declaration). Standalone falls back to the native
    ``map/edit`` RBAC permission.
    """
    if settings.checkmk_omd_root:
        return user.is_admin or cmk_integration.check_create_permission(user.name)
    return user_has_permission(user, "map", "edit", "*")


# Keep in sync with the verbs in connections.py and the CmkAction union in
# frontend/src/api/client.ts. "remove_downtime" is gate-only: the frontend
# routes it through the CMK REST downtime-delete endpoint, never host/service
# -action, so it is here purely so mayCommand() can show/hide the button.
COMMAND_ACTION_PERMISSIONS: dict[str, str] = {
    "acknowledge": "action.acknowledge",
    "remove_acknowledgement": "action.acknowledge",
    "force_check": "action.reschedule",
    "schedule_downtime": "action.downtimes",
    "remove_downtime": "action.downtimes",
    "add_comment": "action.addcomment",
    "enable_notifications": "action.notifications",
    "disable_notifications": "action.notifications",
    "enable_checks": "action.enablechecks",
    "disable_checks": "action.enablechecks",
}


def can_run_command(user: User, action: str) -> bool:
    """True if the user may run the given host/service command verb.

    Checkmk deployments honour the granular command permissions so any role with
    the right — not just admins — can issue commands. Standalone has no such
    permissions, so it stays admin-only.
    """
    perm = COMMAND_ACTION_PERMISSIONS.get(action)
    if perm is None:
        return False
    if settings.checkmk_omd_root:
        return user.is_admin or cmk_integration.check_checkmk_permission(user.name, perm)
    return user.is_admin


def allowed_command_actions(user: User) -> list[str]:
    return [verb for verb in COMMAND_ACTION_PERMISSIONS if can_run_command(user, verb)]


async def require_configure(current_user: User = Depends(get_current_user)) -> User:
    if not can_configure(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="OrbVis configuration access required"
        )
    return current_user


async def require_create_map(current_user: User = Depends(get_current_user)) -> User:
    if not can_create_map(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Map creation access required"
        )
    return current_user


async def require_connection_read(current_user: User = Depends(get_current_user)) -> User:
    """Read-only access to the connection list.

    Map creators need it to pick a connection when creating a map, so this
    admits ``can_create_map`` in addition to ``can_configure``. Mutating a
    connection still requires ``require_configure``.
    """
    if not (can_configure(current_user) or can_create_map(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="OrbVis configuration access required"
        )
    return current_user


def _check_map_permission(user: User, map_name: str, action: str) -> bool:
    if settings.checkmk_omd_root:
        return user.is_admin or cmk_integration.check_map_permission(
            user.name, map_name, action
        )
    return user_has_permission(user, "map", action, map_name)


def can_view_map(user: User, map_name: str) -> bool:
    return _check_map_permission(user, map_name, "view")


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


def can_view_map_by_name(username: str, map_name: str) -> bool:
    """Permission check using only a username string (for background tasks).

    Applicable only when CHECKMK_OMD_ROOT is configured; non-CMK setups need a
    User object for OrbVis RBAC and return True here.
    """
    if settings.checkmk_omd_root:
        return cmk_integration.check_map_permission(username, map_name, "view")
    return True


def can_edit_map(user: User, map_name: str) -> bool:
    return _check_map_permission(user, map_name, "edit")


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
