"""State endpoints + WebSocket for real-time updates."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.core.websocket import manager
from app.models.user import User
from app.schemas.state import MapStates
from app.services import map_service, state_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/maps/{name}/states", response_model=MapStates)
async def get_map_states(
    name: str, _: User = Depends(get_current_user)
) -> MapStates:
    cfg = map_service.get_map(name)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return await state_service.get_map_states(cfg)


@router.websocket("/ws/maps/{name}")
async def websocket_map_states(name: str, websocket: WebSocket) -> None:
    """WebSocket endpoint: pushes state updates for a map at regular intervals."""
    cfg = map_service.get_map(name)
    if cfg is None:
        await websocket.close(code=4004)
        return

    await manager.connect(name, websocket)
    try:
        while True:
            # Push current states to this specific client
            states = await state_service.get_map_states(cfg)
            await manager.broadcast_map_states(name, states.model_dump())
            await asyncio.sleep(settings.state_refresh_interval)
    except WebSocketDisconnect:
        manager.disconnect(name, websocket)
    except Exception:
        logger.exception("WebSocket error for map '%s'", name)
        manager.disconnect(name, websocket)
