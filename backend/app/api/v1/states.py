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

from app.api.v1.connections import TopologyNode, build_topology_response
from app.api.v1.deps import can_view_board as _can_view_board
from app.api.v1.deps import can_view_board_by_name as _can_view_board_by_name
from app.api.v1.deps import get_current_user, resolve_auth_user
from app.api.v1.types import BoardName
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.middleware import is_same_origin
from app.core.ratelimit import ws_connect_limiter
from app.core.websocket import manager
from app.models.user import User
from app.schemas.board import BoardConfig, FlowView
from app.schemas.state import MapStates, ObjectState
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


# One shared broadcast task per active board – avoids O(n²) fetch × broadcast behaviour.
# Without this each connected client would independently fetch and broadcast to all clients.
_broadcast_tasks: dict[str, asyncio.Task[None]] = {}


async def _fetch_topology_for_user(
    cfg: BoardConfig, auth_user: str | None
) -> list[TopologyNode] | None:
    """Fetch the live topology + services for a Flow Board under auth_user.

    Returns None when the connection is unregistered or unavailable (so the
    caller can skip broadcasting without leaking errors to clients). Always
    pulls service detail for the top-K affected hosts so subscribed clients
    can render any service layout (off/donut don't need it but the diff
    encoding only sends host rows that actually changed, so the cost is bounded).
    """
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        return None

    services_per_host = settings.flow_board_max_services_per_host
    top_affected_hosts = settings.flow_board_top_affected_hosts
    if isinstance(cfg.view, FlowView):
        if cfg.view.max_services_per_host is not None:
            services_per_host = cfg.view.max_services_per_host
        if cfg.view.top_affected_hosts is not None:
            top_affected_hosts = cfg.view.top_affected_hosts

    async def _build() -> list[TopologyNode]:
        return await build_topology_response(
            connection,
            include_services=True,
            services_per_host=services_per_host,
            top_affected_hosts=top_affected_hosts,
        )

    try:
        if (
            auth_user is not None
            and settings.checkmk_omd_root
            and hasattr(connection, "with_auth_user")
        ):
            async with connection.with_auth_user(auth_user):
                return await _build()
        return await _build()
    except Exception:
        logger.warning("topology fetch failed for board '%s'", cfg.name, exc_info=True)
        return None


async def _send_topology_to(
    cfg: BoardConfig,
    auth_user: str | None,
    targets: list[WebSocket],
    *,
    force_full: bool,
) -> None:
    """Compute the topology delta for (board, auth_user) and push it to *targets*.

    Empty deltas are skipped unless `force_full=True`.
    """
    if not targets:
        return
    nodes = await _fetch_topology_for_user(cfg, auth_user)
    if nodes is None:
        return
    delta = state_service.compute_topology_delta(cfg.name, auth_user, nodes, force_full=force_full)
    if not (force_full or delta.added or delta.changed or delta.removed):
        return
    msg = json.dumps({"type": "topology_update", "map": cfg.name, "delta": delta.model_dump()})
    await manager.send_to_connections(cfg.name, targets, msg)


def _build_states_msg(
    board_name: str,
    states: MapStates,
    to_send: list[ObjectState],
    removed_ids: list[str],
    full: bool,
) -> str:
    """Encode a state-update message. When full=False, ``states.states`` holds
    only added/changed entries and ``removed_ids`` carries entries gone from
    the previous tick — frontend merges instead of replaces.
    """
    return json.dumps(
        {
            "type": "state_update",
            "map": board_name,
            "states": {
                "map_name": states.map_name,
                "states": [s.model_dump() for s in to_send],
                "generated_at": states.generated_at,
                "connection_ok": states.connection_ok,
            },
            "removed_ids": removed_ids,
            "full": full,
        }
    )


async def _broadcast_loop(board_name: str) -> None:
    """Fetch states once per interval and push to all clients subscribed to this board.

    When CHECKMK_OMD_ROOT is configured, connections are grouped by auth_user and
    each group receives states filtered to its user's contact groups.  Otherwise a
    single shared query is issued for efficiency.

    Updates are delta-encoded against the previous tick's snapshot per
    (board, auth_user) — only added/changed states travel the wire, plus
    object_ids that disappeared. The first tick after the loop starts (or when
    a snapshot is dropped) is full so newly-attached clients converge.

    For Flow Boards (`view.type == "flow"`) the loop additionally pushes
    `topology_update` messages with delta encoding so the FlowBoard component
    can render without its own REST polling.
    """
    logger.debug("Broadcast loop started for board '%s'", board_name)
    try:
        while manager.get_connection_count(board_name) > 0:
            cfg = board_service.get_board(board_name)
            tick_start = asyncio.get_event_loop().time()
            user_count = 0
            if cfg is not None:
                if settings.checkmk_omd_root:
                    grouped = manager.get_connections_grouped(board_name)
                    user_count = len(grouped)
                    for auth_user, connections in grouped.items():
                        can_view = (
                            (lambda n, u=auth_user: _can_view_board_by_name(u, n))
                            if auth_user is not None
                            else None
                        )
                        states = await state_service.get_board_states(
                            cfg, auth_user=auth_user, can_view_board=can_view
                        )
                        to_send, removed_ids, is_full = state_service.compute_states_delta(
                            board_name, auth_user, states.states
                        )
                        if is_full or to_send or removed_ids:
                            msg = _build_states_msg(
                                board_name, states, to_send, removed_ids, is_full
                            )
                            await manager.send_to_connections(board_name, connections, msg)
                        if cfg.view.type == "flow":
                            await _send_topology_to(cfg, auth_user, connections, force_full=False)
                else:
                    user_count = 1
                    states = await state_service.get_board_states(cfg)
                    to_send, removed_ids, is_full = state_service.compute_states_delta(
                        board_name, None, states.states
                    )
                    connections = list(manager.get_connections_grouped(board_name).get(None, []))
                    if is_full or to_send or removed_ids:
                        msg = _build_states_msg(board_name, states, to_send, removed_ids, is_full)
                        await manager.send_to_connections(board_name, connections, msg)
                    if cfg.view.type == "flow":
                        await _send_topology_to(cfg, None, connections, force_full=False)
            elapsed_ms = (asyncio.get_event_loop().time() - tick_start) * 1000
            logger.debug(
                "Broadcast tick board=%s user_groups=%d elapsed=%.0fms",
                board_name,
                user_count,
                elapsed_ms,
            )
            await asyncio.sleep(settings.state_refresh_interval)
    except Exception:
        logger.exception("Broadcast loop error for board '%s'", board_name)
    finally:
        _broadcast_tasks.pop(board_name, None)
        state_service.drop_topology_snapshot(board_name)
        state_service.drop_states_snapshot(board_name)
        logger.debug("Broadcast loop stopped for board '%s'", board_name)


@router.get("/boards/{name}/states", response_model=MapStates)
async def get_board_states(
    name: BoardName, current_user: User = Depends(get_current_user)
) -> MapStates:
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    auth_user = resolve_auth_user(current_user.name, current_user.is_admin)
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

    # Origin guard: browsers don't enforce same-origin on WS, so block hostile
    # cross-origin pages. Same-origin or explicit allowlist; missing header =
    # non-browser client.
    origin = websocket.headers.get("origin")
    if (
        origin
        and origin not in settings.allowed_origins
        and not is_same_origin(origin, websocket.scope.get("headers", []))
    ):
        await websocket.close(code=_WS_CLOSE_AUTH_FAILED)
        return

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
        ws_auth_user = resolve_auth_user(user.name, user.is_admin)

    cfg = board_service.get_board(name)
    if cfg is None:
        await websocket.close(code=_WS_CLOSE_NOT_FOUND)
        return

    await manager.connect(name, websocket, already_accepted=True, auth_user=ws_auth_user)

    if name not in _broadcast_tasks or _broadcast_tasks[name].done():
        _broadcast_tasks[name] = asyncio.create_task(_broadcast_loop(name))

    # First-paint push for Flow Boards: don't make the client wait up to one
    # broadcast tick (state_refresh_interval) for the initial topology.
    if cfg.view.type == "flow":
        await _send_topology_to(cfg, ws_auth_user, [websocket], force_full=True)

    try:
        while True:
            await websocket.receive()
    except Exception:
        pass
    finally:
        manager.disconnect(name, websocket)
