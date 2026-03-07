"""State endpoints + WebSocket for real-time updates."""

from __future__ import annotations

import asyncio
import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    status,
)
from jose import JWTError

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.websocket import manager
from app.models.user import User
from app.schemas.state import MapStates
from app.services import map_service, state_service
from app.services.auth_service import get_user_by_id

logger = logging.getLogger(__name__)

router = APIRouter()

# One shared broadcast task per active map – avoids O(n²) fetch × broadcast behaviour.
# Without this each connected client would independently fetch and broadcast to all clients.
_broadcast_tasks: dict[str, asyncio.Task[None]] = {}


async def _broadcast_loop(map_name: str) -> None:
    """Fetch states once per interval and push to all clients subscribed to this map."""
    logger.info("Broadcast loop started for map '%s'", map_name)
    try:
        while manager.get_connection_count(map_name) > 0:
            cfg = map_service.get_map(map_name)
            if cfg is not None:
                states = await state_service.get_map_states(cfg)
                await manager.broadcast_map_states(map_name, states.model_dump())
            await asyncio.sleep(settings.state_refresh_interval)
    except Exception:
        logger.exception("Broadcast loop error for map '%s'", map_name)
    finally:
        _broadcast_tasks.pop(map_name, None)
        logger.info("Broadcast loop stopped for map '%s'", map_name)


@router.get("/maps/{name}/states", response_model=MapStates)
async def get_map_states(
    name: str, _: User = Depends(get_current_user)
) -> MapStates:
    cfg = map_service.get_map(name)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return await state_service.get_map_states(cfg)


@router.websocket("/ws/maps/{name}")
async def websocket_map_states(
    name: str,
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """WebSocket endpoint: streams state updates for a map.

    Authentication: pass the JWT access token as ?token=<token> query parameter
    (Authorization header is not available after the WebSocket upgrade handshake).

    A short-lived DB session is used only for the auth check and closed immediately
    afterwards; the session is NOT held open for the lifetime of the connection.
    """
    # --- Authenticate ---
    if not token:
        await websocket.close(code=4001)
        return
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("not an access token")
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        await websocket.close(code=4001)
        return

    # Use an explicit short-lived session rather than Depends(get_db).
    # Depends(get_db) would hold the connection open until the endpoint returns,
    # which for WebSockets means until the client disconnects – potentially hours.
    async with AsyncSessionLocal() as db:
        user = await get_user_by_id(db, user_id)
        user_valid = user is not None and user.is_active
    # DB session is closed here; no connection held for the WS lifetime.

    if not user_valid:
        await websocket.close(code=4001)
        return

    # --- Check map exists ---
    cfg = map_service.get_map(name)
    if cfg is None:
        await websocket.close(code=4004)
        return

    await manager.connect(name, websocket)

    # Start the shared broadcast task if it is not already running for this map.
    if name not in _broadcast_tasks or _broadcast_tasks[name].done():
        _broadcast_tasks[name] = asyncio.create_task(_broadcast_loop(name))

    # Hold the connection open until the client disconnects.
    try:
        while True:
            await websocket.receive()  # any message; we only care about disconnect
    except Exception:
        pass  # WebSocketDisconnect, RuntimeError, or other protocol error
    finally:
        manager.disconnect(name, websocket)
