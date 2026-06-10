"""State endpoints + Server-Sent Events for real-time updates."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from collections.abc import AsyncIterator
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse

from app.api.v1.connections import TopologyNode, build_topology_response
from app.api.v1.deps import can_view_board as _can_view_board
from app.api.v1.deps import can_view_board_by_name as _can_view_board_by_name
from app.api.v1.deps import get_current_user, resolve_auth_user
from app.api.v1.types import BoardName
from app.connections.base import ServiceMatchRow, ServiceRow
from app.core.config import settings
from app.core.database import get_db
from app.core.ratelimit import ws_connect_limiter
from app.core.sse import Subscriber, manager
from app.integrations.checkmk import resolve_folder_scope
from app.models.user import User
from app.schemas.board import BoardConfig, FlowView, FolderTreeView, RadarView
from app.schemas.state import (
    FolderHostService,
    FolderServiceMatch,
    FolderServiceSearchResult,
    FolderTreeDelta,
    MapStates,
    ObjectState,
    ObjectTiming,
)
from app.services import board_service, settings_service, state_service
from app.services.auth_service import authenticate_url_token

logger = logging.getLogger(__name__)

router = APIRouter()


# Shared broadcast task per active board — avoids O(n²) fetch × broadcast.
# Without this every connected client would independently fetch the topology
# + states and push to all clients.
_broadcast_tasks: dict[str, asyncio.Task[None]] = {}
# Last dead-sites list pushed per (board, subscriber-group): a federation site
# dying/recovering must reach clients even when no node-level delta exists.
_dead_sites_snapshots: dict[tuple[str, str | None], list[str]] = {}

# Heartbeat cadence for SSE keepalives. Sized below typical Apache ProxyTimeout
# (60 s default in OMD) so the stream doesn't get torn down on idle boards.
_SSE_KEEPALIVE_INTERVAL = 30.0


async def _fetch_topology_for_user(
    cfg: BoardConfig, auth_user: str | None
) -> list[TopologyNode] | None:
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        return None

    services_per_host = settings.flow_board_max_services_per_host
    top_affected_hosts = settings.flow_board_top_affected_hosts
    root: str | None = None
    child_layers: int | None = None
    parent_layers: int | None = None
    if isinstance(cfg.view, FlowView):
        if cfg.view.max_services_per_host is not None:
            services_per_host = cfg.view.max_services_per_host
        if cfg.view.top_affected_hosts is not None:
            top_affected_hosts = cfg.view.top_affected_hosts
        root = cfg.view.root
        child_layers = cfg.view.child_layers
        parent_layers = cfg.view.parent_layers

    async def _build() -> list[TopologyNode]:
        return await build_topology_response(
            connection,
            include_services=True,
            services_per_host=services_per_host,
            top_affected_hosts=top_affected_hosts,
            root=root,
            child_layers=child_layers,
            parent_layers=parent_layers,
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


def _build_states_msg(
    board_name: str,
    states: MapStates,
    to_send: list[ObjectState],
    removed_ids: list[str],
    full: bool,
    timing: list[ObjectTiming],
    ft_delta: FolderTreeDelta | None,
) -> str:
    return json.dumps(
        {
            "type": "state_update",
            "map": board_name,
            "states": {
                "map_name": states.map_name,
                "states": [s.model_dump() for s in to_send],
                "generated_at": states.generated_at,
                "connection_ok": states.connection_ok,
                "dead_sites": states.dead_sites,
                # Foldertree boards diff the tree per tick: ``full`` on the first
                # tick / a structural change, else only changed nodes. At 100k+
                # hosts the full tree is ~45MB raw, so streaming the whole thing
                # every 5s froze the client — the delta cuts that to O(changes).
                "folder_tree_delta": ft_delta.model_dump() if ft_delta is not None else None,
            },
            "removed_ids": removed_ids,
            "full": full,
            "timing": [tm.model_dump() for tm in timing],
        }
    )


async def _push_topology_to(
    cfg: BoardConfig,
    auth_user: str | None,
    targets: list[Subscriber],
    *,
    force_full: bool,
) -> None:
    if not targets:
        return
    nodes = await _fetch_topology_for_user(cfg, auth_user)
    if nodes is None:
        return
    delta = state_service.compute_topology_delta(cfg.name, auth_user, nodes, force_full=force_full)
    if not (force_full or delta.added or delta.changed or delta.removed or delta.timing):
        return
    msg = json.dumps({"type": "topology_update", "map": cfg.name, "delta": delta.model_dump()})
    manager.push(cfg.name, targets, msg)


async def _broadcast_loop(board_name: str) -> None:
    """Fetch states once per interval and push to all subscribers.

    With CHECKMK_OMD_ROOT, subscribers are grouped by auth_user and each group
    receives states filtered to its user's contact groups. Otherwise a single
    shared query is issued.

    Delta-encoded per (board, auth_user): only added/changed states travel the
    wire, plus object_ids that disappeared. The first tick (or after a snapshot
    is dropped) is full so newly-attached subscribers converge.

    Flow Boards additionally receive ``topology_update`` deltas so the FlowBoard
    component renders without its own REST polling.
    """
    logger.debug("Broadcast loop started for board '%s'", board_name)
    try:
        while manager.get_subscriber_count(board_name) > 0:
            cfg = board_service.get_board(board_name)
            tick_start = asyncio.get_event_loop().time()
            user_count = 0
            if cfg is not None:
                if settings.checkmk_omd_root:
                    grouped = manager.get_subscribers_grouped(board_name)
                    user_count = len(grouped)
                    for group_key, subs in grouped.items():
                        # All subs in a group render identically; the first carries
                        # the monitoring (auth_user) + folder (folder_scope) scopes.
                        # Snapshots/deltas are keyed by group_key so admin and a
                        # see-all guest on a foldertree board don't share a tree.
                        rep = subs[0]
                        auth_user = rep.auth_user
                        can_view = (
                            (lambda n, u=auth_user: _can_view_board_by_name(u, n))
                            if auth_user is not None
                            else None
                        )
                        states = await state_service.get_board_states(
                            cfg,
                            auth_user=auth_user,
                            can_view_board=can_view,
                            folder_scope=rep.folder_scope,
                        )
                        to_send, removed_ids, is_full, timing = state_service.compute_states_delta(
                            board_name, group_key, states.states
                        )
                        # Computed unconditionally so the snapshot stays current;
                        # the tree carries its own delta (structure can shift with
                        # no host-state delta — see compute_folder_tree_delta).
                        ft_delta = (
                            state_service.compute_folder_tree_delta(
                                board_name, group_key, states.folder_tree
                            )
                            if cfg.view.type == "foldertree"
                            else None
                        )
                        ft_changed = ft_delta is not None and (
                            ft_delta.full or bool(ft_delta.changed)
                        )
                        ds_key = (board_name, group_key)
                        ds_changed = _dead_sites_snapshots.get(ds_key) != states.dead_sites
                        _dead_sites_snapshots[ds_key] = states.dead_sites
                        if is_full or to_send or removed_ids or timing or ft_changed or ds_changed:
                            msg = _build_states_msg(
                                board_name, states, to_send, removed_ids, is_full, timing, ft_delta
                            )
                            manager.push(board_name, subs, msg)
                        if cfg.view.type == "flow":
                            await _push_topology_to(cfg, auth_user, subs, force_full=False)
                else:
                    user_count = 1
                    states = await state_service.get_board_states(cfg)
                    to_send, removed_ids, is_full, timing = state_service.compute_states_delta(
                        board_name, None, states.states
                    )
                    ft_delta = (
                        state_service.compute_folder_tree_delta(
                            board_name, None, states.folder_tree
                        )
                        if cfg.view.type == "foldertree"
                        else None
                    )
                    ft_changed = ft_delta is not None and (ft_delta.full or bool(ft_delta.changed))
                    subs = list(manager.get_subscribers_grouped(board_name).get(None, []))
                    if is_full or to_send or removed_ids or timing or ft_changed:
                        msg = _build_states_msg(
                            board_name, states, to_send, removed_ids, is_full, timing, ft_delta
                        )
                        manager.push(board_name, subs, msg)
                    if cfg.view.type == "flow":
                        await _push_topology_to(cfg, None, subs, force_full=False)
            elapsed_ms = (asyncio.get_event_loop().time() - tick_start) * 1000
            logger.debug(
                "Broadcast tick board=%s user_groups=%d elapsed=%.0fms",
                board_name,
                user_count,
                elapsed_ms,
            )
            # Read interval fresh each tick so System-Settings changes apply
            # without restarting the backend.
            await asyncio.sleep(settings_service.get_effective_state_refresh_interval())
    except Exception:
        logger.exception("Broadcast loop error for board '%s'", board_name)
    finally:
        _broadcast_tasks.pop(board_name, None)
        state_service.drop_topology_snapshot(board_name)
        state_service.drop_states_snapshot(board_name)
        state_service.drop_board_snapshots(_dead_sites_snapshots, board_name)
        logger.debug("Broadcast loop stopped for board '%s'", board_name)


_RADAR_FILTERS: set[str] = {"hostgroup", "servicegroup", "all_hosts", "all_services"}


# Returns a pre-dumped Response (passed through untouched) instead of a model:
# skips FastAPI's second full re-validation, which dominated initial load on
# 100k+-host boards. response_model stays for the OpenAPI schema (api.ts codegen).
@router.get("/boards/{name}/states", response_model=MapStates)
async def get_board_states(
    name: BoardName,
    current_user: User = Depends(get_current_user),
    radar_filter: str | None = None,
    radar_filter_value: str | None = None,
    ft_override: bool = False,
    ft_root_folder: str = "",
    ft_show_empty_folders: bool = True,
    ft_only_hard_states: bool = False,
    ft_sites: list[str] = Query(default_factory=list),
) -> Response:
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    # Settings-preview override for radar boards. Both query params arrive
    # together so we never mix disk-state filter with a half-edited override.
    if (
        cfg.view.type == "radar"
        and radar_filter is not None
        and radar_filter_value is not None
        and radar_filter in _RADAR_FILTERS
    ):
        cfg = cfg.model_copy(
            update={
                "view": RadarView(
                    filter=cast(
                        Literal["hostgroup", "servicegroup", "all_hosts", "all_services"],
                        radar_filter,
                    ),
                    filter_value=radar_filter_value,
                )
            }
        )
    # Settings-preview override for foldertree boards: only the server-side view
    # fields (the others are mirrored client-side and need no requery). Gated on
    # an explicit flag so an empty root_folder reads as "(all)" not "unset".
    # problems_only is forced off so the server never prunes healthy nodes — the
    # client filters it reactively, so toggling it in the preview works both ways
    # without a per-toggle tree rebuild.
    if ft_override and isinstance(cfg.view, FolderTreeView):
        cfg = cfg.model_copy(
            update={
                "view": cfg.view.model_copy(
                    update={
                        "root_folder": ft_root_folder,
                        "show_empty_folders": ft_show_empty_folders,
                        "only_hard_states": ft_only_hard_states,
                        "sites": ft_sites,
                        "problems_only": False,
                    }
                )
            }
        )
    auth_user = resolve_auth_user(current_user.name, current_user.is_admin)
    # Only foldertree boards consume folder_scope; skip the permission/contact-group
    # lookups for every other board type.
    folder_scope = (
        resolve_folder_scope(current_user.name, current_user.is_admin)
        if cfg.view.type == "foldertree"
        else None
    )
    states = await state_service.get_board_states(
        cfg,
        auth_user=auth_user,
        can_view_board=lambda n: _can_view_board(current_user, n),
        folder_scope=folder_scope,
    )
    return Response(content=states.model_dump_json(), media_type="application/json")


@router.get("/boards/{name}/folder-host-services", response_model=list[FolderHostService])
async def get_folder_host_services(
    name: BoardName,
    host: str = Query(..., description="Host name to fetch services for"),
    current_user: User = Depends(get_current_user),
) -> list[FolderHostService]:
    """Lazily fetch a single host's services for a foldertree board.

    Only invoked when an operator expands a host in the tree/map — a single
    host-scoped Livestatus query — so the board scales to environments with
    millions of hosts (services are never pushed eagerly over SSE).
    """
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    if not _can_view_board(current_user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No board view permission"
        )
    if not isinstance(cfg.view, FolderTreeView):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not a foldertree board"
        )
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    auth_user = resolve_auth_user(current_user.name, current_user.is_admin)
    only_hard = cfg.view.only_hard_states

    async def _fetch() -> list[ServiceRow]:
        return await connection.get_host_services(host, only_hard=only_hard)

    try:
        if (
            auth_user is not None
            and settings.checkmk_omd_root
            and hasattr(connection, "with_auth_user")
        ):
            async with connection.with_auth_user(auth_user):
                rows = await _fetch()
        else:
            rows = await _fetch()
    except Exception:
        logger.warning("folder host-services fetch failed for '%s'/%s", name, host, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Service fetch failed"
        ) from None

    services = [
        FolderHostService(
            name=r["name"],
            state=r["state"],
            output=r.get("output", ""),
            acknowledged=r.get("acknowledged", False),
            in_downtime=r.get("in_downtime", False),
            is_flapping=r.get("is_flapping", False),
            last_state_change=r.get("last_state_change"),
        )
        for r in rows
    ]
    # Worst-state first (CRITICAL on top), then alphabetical — matches the
    # host/folder ordering elsewhere in the tree.
    state_service.sort_folder_services(services)
    return services


@router.get("/boards/{name}/folder-search", response_model=FolderServiceSearchResult)
async def folder_service_search(
    name: BoardName,
    s: list[str] = Query(default_factory=list, description="Service-name substrings (AND)"),
    h: list[str] = Query(default_factory=list, description="Host-name substrings (AND)"),
    q: list[str] = Query(default_factory=list, description="Bare substrings (host OR service)"),
    current_user: User = Depends(get_current_user),
) -> FolderServiceSearchResult:
    """Server-side service search for a foldertree board.

    Services are never pushed over SSE (would not scale to millions), so a
    ``s:``/bare search that should reach un-expanded hosts queries Livestatus
    directly with a hard ``Limit``. The frontend places each hit into the host
    it already has in the tree. Pure host/folder searches stay client-side and
    never call this. Terms shorter than 2 chars are dropped (too broad).
    """
    limit = settings.object_autocomplete_limit

    # Trim and drop sub-2-char terms (too broad); forward the trimmed value so a
    # stray space never leaks into the match.
    def _terms(raw: list[str]) -> list[str]:
        return [s for s in (t.strip() for t in raw) if len(s) >= 2]

    service_terms = _terms(s)
    host_terms = _terms(h)
    any_terms = _terms(q)
    # Only a service-bearing query reaches the backend; a pure host search is
    # answered from the already-loaded tree on the client.
    if not service_terms and not any_terms:
        return FolderServiceSearchResult(matches=[], truncated=False, limit=limit)

    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    if not _can_view_board(current_user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No board view permission"
        )
    if not isinstance(cfg.view, FolderTreeView):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Not a foldertree board"
        )
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    auth_user = resolve_auth_user(current_user.name, current_user.is_admin)
    only_hard = cfg.view.only_hard_states

    async def _fetch() -> list[ServiceMatchRow]:
        return await connection.search_services(
            host_terms=host_terms,
            service_terms=service_terms,
            any_terms=any_terms,
            limit=limit,
            only_hard=only_hard,
        )

    try:
        if (
            auth_user is not None
            and settings.checkmk_omd_root
            and hasattr(connection, "with_auth_user")
        ):
            async with connection.with_auth_user(auth_user):
                rows = await _fetch()
        else:
            rows = await _fetch()
    except Exception:
        logger.warning("folder service search failed for '%s'", name, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Service search failed"
        ) from None

    truncated = len(rows) > limit
    rows = rows[:limit]

    # Group hits by (host, site), preserving first-seen order; sort each host's
    # services worst-state first, matching the lazy folder-host-services order.
    grouped: dict[tuple[str, str | None], list[FolderHostService]] = {}
    for r in rows:
        key = (r["host_name"], r.get("site_id"))
        grouped.setdefault(key, []).append(
            FolderHostService(
                name=r["name"],
                state=r["state"],
                output=r.get("output", ""),
                acknowledged=r.get("acknowledged", False),
                in_downtime=r.get("in_downtime", False),
                is_flapping=r.get("is_flapping", False),
                last_state_change=r.get("last_state_change"),
            )
        )
    matches: list[FolderServiceMatch] = []
    for (host, site), svcs in grouped.items():
        state_service.sort_folder_services(svcs)
        matches.append(FolderServiceMatch(host=host, site_id=site, services=svcs))
    return FolderServiceSearchResult(matches=matches, truncated=truncated, limit=limit)


@router.get("/sse/boards/{name}")
async def sse_board_states(
    name: BoardName,
    request: Request,
    token: str = Query(
        ..., description="Stream ticket or access token (EventSource can't set headers)"
    ),
    db: sqlite3.Connection = Depends(get_db),
) -> StreamingResponse:
    """SSE endpoint streaming state + topology updates for a board.

    Authentication: ``?token=`` query parameter (EventSource cannot set custom
    headers). Proxies log query strings, so the frontend sends a short-lived
    stream ticket (``POST /auth/stream-ticket``); plain access tokens stay
    accepted for older external callers.
    """
    client_ip = request.client.host if request.client else "unknown"
    if ws_connect_limiter.is_blocked(client_ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limited")
    ws_connect_limiter.record(client_ip)

    user = await authenticate_url_token(db, token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not _can_view_board(user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No board view permission"
        )

    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )

    auth_user = resolve_auth_user(user.name, user.is_admin)
    # Foldertree boards render a SETUP folder skeleton scoped by folder-read
    # permission, which differs from the monitoring scope (a see-all guest shares
    # auth_user=None with an admin but sees fewer folders). Fold that into the
    # subscriber group key so they get separate computations; other board types
    # group by auth_user alone.
    folder_scope = None
    group_key: str | None = auth_user
    if cfg.view.type == "foldertree":
        folder_scope = resolve_folder_scope(user.name, user.is_admin)
        group_key = f"{auth_user}#{folder_scope.key}"
    sub = manager.subscribe(name, auth_user, folder_scope=folder_scope, group_key=group_key)

    # A new subscriber joins against a snapshot primed by the group's earlier
    # members, so the next tick would send only a delta — leaving this client's
    # REST-loaded states/tree to diverge on anything that changed before it
    # joined. Drop the group's snapshot so the next tick is a full resend and the
    # group reconverges (mirrors the Flow Board's force_full-on-join).
    state_service.drop_states_snapshot(name, group_key)

    if name not in _broadcast_tasks or _broadcast_tasks[name].done():
        _broadcast_tasks[name] = asyncio.create_task(_broadcast_loop(name))

    # First-paint topology for Flow Boards so the client doesn't wait a full
    # broadcast tick before the initial render.
    if cfg.view.type == "flow":
        await _push_topology_to(cfg, auth_user, [sub], force_full=True)

    async def event_stream() -> AsyncIterator[bytes]:
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(sub.queue.get(), timeout=_SSE_KEEPALIVE_INTERVAL)
                    yield f"data: {msg}\n\n".encode()
                except TimeoutError:
                    yield b": keepalive\n\n"
        finally:
            manager.unsubscribe(name, sub)

    headers = {
        # Apache buffers proxied responses by default; opt out so events flow
        # through immediately.
        "X-Accel-Buffering": "no",
        "Cache-Control": "no-cache, no-store",
    }
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
