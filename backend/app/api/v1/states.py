"""State endpoints + WebSocket for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    status,
)

from app.api.v1.deps import can_view_board as _can_view_board
from app.api.v1.deps import can_view_board_by_name as _can_view_board_by_name
from app.api.v1.deps import get_current_user
from app.api.v1.types import BoardName
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.ratelimit import ws_connect_limiter
from app.core.websocket import manager
from app.integrations import checkmk as _cmk_integration
from app.models.user import User
from app.schemas.state import MapStates
from app.services import board_service, state_service
from app.services.auth_service import authenticate_bearer_token

logger = logging.getLogger(__name__)

# WebSocket close codes (application range 4000–4999, per RFC 6455).
# 4001 is used uniformly for "auth failed" so clients can trigger a re-login
# on any auth-related rejection without needing to distinguish reasons.
_WS_CLOSE_AUTH_FAILED = 4001
_WS_CLOSE_NO_PERMISSION = 4003
_WS_CLOSE_NOT_FOUND = 4004
_WS_CLOSE_RATE_LIMITED = 4008

router = APIRouter()


def _resolve_auth_user(username: str, is_admin: bool) -> str | None:
    """Return the username to pass as AuthUser to Livestatus, or None for unrestricted access.

    Users with admin role or CMK's 'general.see_all' permission bypass contact-group
    filtering so Livestatus returns all objects instead of only those the user is a contact for.
    """
    if not settings.checkmk_omd_root:
        return None
    if is_admin:
        return None
    if _cmk_integration.check_checkmk_permission(username, "general.see_all"):
        return None
    return username


# One shared broadcast task per active board – avoids O(n²) fetch × broadcast behaviour.
# Without this each connected client would independently fetch and broadcast to all clients.
_broadcast_tasks: dict[str, asyncio.Task[None]] = {}


async def _broadcast_loop(board_name: str) -> None:
    """Fetch states once per interval and push to all clients subscribed to this board.

    When CHECKMK_OMD_ROOT is configured, connections are grouped by auth_user and
    each group receives states filtered to its user's contact groups.  Otherwise a
    single shared query is issued for efficiency.
    """
    logger.info("Broadcast loop started for board '%s'", board_name)
    try:
        while manager.get_connection_count(board_name) > 0:
            cfg = board_service.get_board(board_name)
            if cfg is not None:
                if settings.checkmk_omd_root:
                    grouped = manager.get_connections_grouped(board_name)
                    for auth_user, connections in grouped.items():
                        can_view = (
                            (lambda n, u=auth_user: _can_view_board_by_name(u, n))
                            if auth_user is not None
                            else None
                        )
                        states = await state_service.get_board_states(
                            cfg, auth_user=auth_user, can_view_board=can_view
                        )
                        msg = json.dumps(
                            {
                                "type": "state_update",
                                "map": board_name,
                                "states": states.model_dump(),
                            }
                        )
                        await manager.send_to_connections(board_name, connections, msg)
                else:
                    states = await state_service.get_board_states(cfg)
                    await manager.broadcast_map_states(board_name, states.model_dump())
            await asyncio.sleep(settings.state_refresh_interval)
    except Exception:
        logger.exception("Broadcast loop error for board '%s'", board_name)
    finally:
        _broadcast_tasks.pop(board_name, None)
        logger.info("Broadcast loop stopped for board '%s'", board_name)


@router.get("/boards/{name}/states", response_model=MapStates)
async def get_board_states(
    name: BoardName, current_user: User = Depends(get_current_user)
) -> MapStates:
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    auth_user = _resolve_auth_user(current_user.name, current_user.is_admin)
    return await state_service.get_board_states(
        cfg,
        auth_user=auth_user,
        can_view_board=lambda n: _can_view_board(current_user, n),
    )


@router.websocket("/ws/boards/{name}")
async def websocket_board_states(
    name: BoardName,
    websocket: WebSocket,
) -> None:
    """WebSocket endpoint: streams state updates for a board.

    Authentication: the client must send {"type": "auth", "token": "<access_token>"}
    as the very first message after the connection is opened. The token is never
    passed in the URL to avoid leaking it into server logs and browser history.

    Hardening: connects are rate-limited per client IP, and the auth-message
    timeout is short (3 s) so stalled or silent connections don't tie up slots.
    """
    client_ip = websocket.client.host if websocket.client else "unknown"
    if ws_connect_limiter.is_blocked(client_ip):
        # Too many connects from this IP in the recent window — reject without accept.
        await websocket.close(code=_WS_CLOSE_RATE_LIMITED)
        return
    ws_connect_limiter.record(client_ip)

    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=3.0)
        msg = json.loads(raw)
        if msg.get("type") != "auth" or not isinstance(msg.get("token"), str):
            await websocket.close(code=_WS_CLOSE_AUTH_FAILED)
            return
        token: str = msg["token"]
    except Exception:
        await websocket.close(code=_WS_CLOSE_AUTH_FAILED)
        return

    async with AsyncSessionLocal() as db:
        user = await authenticate_bearer_token(db, token)
        if user is None:
            await websocket.close(code=_WS_CLOSE_AUTH_FAILED)
            return
        if not _can_view_board(user, name):
            await websocket.close(code=_WS_CLOSE_NO_PERMISSION)
            return
        ws_auth_user = _resolve_auth_user(user.name, user.is_admin)

    cfg = board_service.get_board(name)
    if cfg is None:
        await websocket.close(code=_WS_CLOSE_NOT_FOUND)
        return

    await manager.connect(name, websocket, already_accepted=True, auth_user=ws_auth_user)

    if name not in _broadcast_tasks or _broadcast_tasks[name].done():
        _broadcast_tasks[name] = asyncio.create_task(_broadcast_loop(name))

    try:
        while True:
            await websocket.receive()
    except Exception:
        pass
    finally:
        manager.disconnect(name, websocket)
