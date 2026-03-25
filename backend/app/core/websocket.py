"""WebSocket connection manager for real-time state updates."""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per map."""

    def __init__(self) -> None:
        # map_name -> set of websockets
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, map_name: str, websocket: WebSocket, *, already_accepted: bool = False) -> None:
        if not already_accepted:
            await websocket.accept()
        self._connections.setdefault(map_name, set()).add(websocket)
        logger.info(
            "WS connected for map '%s' (total: %d)",
            map_name,
            len(self._connections[map_name]),
        )

    def disconnect(self, map_name: str, websocket: WebSocket) -> None:
        connections = self._connections.get(map_name, set())
        connections.discard(websocket)
        if not connections:
            self._connections.pop(map_name, None)
        logger.info("WS disconnected for map '%s'", map_name)

    async def broadcast_map_states(self, map_name: str, states: dict) -> None:
        """Push state update to all clients subscribed to a map."""
        connections = self._connections.get(map_name, set())
        if not connections:
            return

        message = json.dumps({"type": "state_update", "map": map_name, "states": states})
        dead: set[WebSocket] = set()

        # Iterate over a snapshot so that concurrent disconnect() calls on the live
        # set don't cause skipped sends or "Set changed size during iteration" errors.
        for ws in set(connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        for ws in dead:
            self.disconnect(map_name, ws)

    def get_connection_count(self, map_name: str) -> int:
        return len(self._connections.get(map_name, set()))


manager = ConnectionManager()
