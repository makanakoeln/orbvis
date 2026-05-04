"""WebSocket connection manager for real-time state updates."""

from __future__ import annotations

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per map."""

    def __init__(self) -> None:
        self._connections: dict[str, dict[WebSocket, str | None]] = {}

    async def connect(
        self,
        map_name: str,
        websocket: WebSocket,
        *,
        already_accepted: bool = False,
        auth_user: str | None = None,
    ) -> None:
        if not already_accepted:
            await websocket.accept()
        self._connections.setdefault(map_name, {})[websocket] = auth_user
        logger.debug(
            "WS connected for map '%s' (total: %d)",
            map_name,
            len(self._connections[map_name]),
        )

    def disconnect(self, map_name: str, websocket: WebSocket) -> None:
        connections = self._connections.get(map_name, {})
        connections.pop(websocket, None)
        if not connections:
            self._connections.pop(map_name, None)
        logger.debug("WS disconnected for map '%s'", map_name)

    async def broadcast_map_states(self, map_name: str, states: dict[str, object]) -> None:
        """Push state update to all clients subscribed to a map (no per-user filtering)."""
        connections = self._connections.get(map_name, {})
        if not connections:
            return

        message = json.dumps({"type": "state_update", "map": map_name, "states": states})
        dead: list[WebSocket] = []

        for ws in list(connections):
            try:
                await ws.send_text(message)
            except Exception as exc:
                logger.debug("WS send failed for map %r: %s — dropping client", map_name, exc)
                dead.append(ws)

        for ws in dead:
            self.disconnect(map_name, ws)

    def get_connection_count(self, map_name: str) -> int:
        return len(self._connections.get(map_name, {}))

    def get_connections_grouped(self, map_name: str) -> dict[str | None, list[WebSocket]]:
        """Return connections grouped by auth_user.

        Used by the broadcast loop to issue one Livestatus query per unique
        user when contact-group filtering is active.
        """
        groups: dict[str | None, list[WebSocket]] = {}
        for ws, auth_user in self._connections.get(map_name, {}).items():
            groups.setdefault(auth_user, []).append(ws)
        return groups

    async def send_to_connections(
        self, map_name: str, connections: list[WebSocket], message: str
    ) -> None:
        """Send *message* to a specific subset of connections, pruning dead ones."""
        for ws in list(connections):
            try:
                await ws.send_text(message)
            except Exception as exc:
                logger.debug("WS targeted send failed for map %r: %s", map_name, exc)
                self.disconnect(map_name, ws)


manager = ConnectionManager()
