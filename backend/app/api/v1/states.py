"""State endpoints + WebSocket for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging

import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    status,
)

from app.api.v1.deps import can_view_board, get_current_user
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.websocket import manager
from app.models.user import User
from app.schemas.state import MapStates
from app.services import board_service, state_service
from app.services.auth_service import get_user_by_id

logger = logging.getLogger(__name__)

router = APIRouter()

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
                        states = await state_service.get_board_states(cfg, auth_user=auth_user)
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
async def get_board_states(name: str, current_user: User = Depends(get_current_user)) -> MapStates:
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    auth_user = current_user.name if settings.checkmk_omd_root else None
    return await state_service.get_board_states(cfg, auth_user=auth_user)


@router.websocket("/ws/boards/{name}")
async def websocket_board_states(
    name: str,
    websocket: WebSocket,
) -> None:
    """WebSocket endpoint: streams state updates for a board.

    Authentication: the client must send {"type": "auth", "token": "<access_token>"}
    as the very first message after the connection is opened. The token is never
    passed in the URL to avoid leaking it into server logs and browser history.
    """
    await websocket.accept()
    try:
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        msg = json.loads(raw)
        if msg.get("type") != "auth" or not isinstance(msg.get("token"), str):
            await websocket.close(code=4001)
            return
        token: str = msg["token"]
    except Exception:
        await websocket.close(code=4001)
        return

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("not an access token")
        user_id = int(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(db, user_id)
        if user is None or not user.is_active:
            await websocket.close(code=4001)
            return
        if not can_view_board(user, name):
            await websocket.close(code=4003)
            return
        ws_auth_user = user.name

    cfg = board_service.get_board(name)
    if cfg is None:
        await websocket.close(code=4004)
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
