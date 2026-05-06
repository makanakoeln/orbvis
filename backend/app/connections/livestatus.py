"""MK Livestatus connection via asyncio Unix/TCP socket."""

from __future__ import annotations

import asyncio
import importlib
import json as _json
import logging
import pkgutil
import re as _re
import threading
import time
import types
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from cmk.livestatus_client import MultiSiteConnection

import httpx

from app.connections.base import (
    ConnectionBase,
    GraphGroup,
    MetricHistoryResult,
    ServiceRow,
    TopologyRow,
)
from app.core.config import settings
from app.integrations import checkmk as _cmk_integration
from app.integrations import checkmk_sites as _cmk_sites
from app.schemas.board import AggregationInfo, AggregationNode
from app.schemas.state import ObjectState, ServicesSummary

logger = logging.getLogger(__name__)

# When set, every Livestatus query in the current asyncio task includes
# ``AuthUser: <username>`` so Livestatus only returns objects the user
# is a contact for (contact-group filtering).
_auth_user_ctx: ContextVar[str | None] = ContextVar("_auth_user_ctx", default=None)


def _identity(x: str) -> str:
    return x


@lru_cache(maxsize=1)
def _get_plugin_dirs() -> set[Path]:
    """Return all cmk.plugins sub-package directories.

    walk_packages does not recurse into namespace packages without __init__.py
    (e.g. ``collection``), so we enumerate subdirectories on disk directly.
    """
    try:
        import cmk.plugins as _p
    except ImportError:
        return set()
    dirs: set[Path] = set()
    for p in _p.__path__:
        try:
            dirs.update(d for d in Path(p).iterdir() if d.is_dir())
        except OSError:
            pass
    return dirs


def _iter_graphing_modules(plugin_dirs: set[Path]) -> Iterator[types.ModuleType]:
    """Yield imported graphing submodules for all plugin directories."""
    for plugin_dir in plugin_dirs:
        graphing_pkg = f"cmk.plugins.{plugin_dir.name}.graphing"
        try:
            graphing_mod = importlib.import_module(graphing_pkg)
        except Exception:
            continue
        for _finder, submod_name, _ispkg in pkgutil.iter_modules(
            graphing_mod.__path__, f"{graphing_pkg}."
        ):
            try:
                yield importlib.import_module(submod_name)
            except Exception:
                continue


def _extract_quantity_metrics(qty: object) -> Iterator[str]:
    """Recursively yield metric names from a CMK graphing Quantity expression."""
    if isinstance(qty, str):
        yield qty
        return
    # WarningOf, CriticalOf, MinimumOf, MaximumOf — all have .metric_name: str
    metric_name = getattr(qty, "metric_name", None)
    if isinstance(metric_name, str):
        yield metric_name
        return
    # Sum (.summands), Product (.factors)
    for seq_attr in ("summands", "factors"):
        items = getattr(qty, seq_attr, None)
        if items is not None:
            for item in items:
                yield from _extract_quantity_metrics(item)
            return
    # Difference (.minuend + .subtrahend), Fraction (.dividend + .divisor)
    for a_attr, b_attr in (("minuend", "subtrahend"), ("dividend", "divisor")):
        a = getattr(qty, a_attr, None)
        b = getattr(qty, b_attr, None)
        if a is not None and b is not None:
            yield from _extract_quantity_metrics(a)
            yield from _extract_quantity_metrics(b)
            return
    # Constant or unknown — no metric


@dataclass
class _CMKGraphingData:
    titles: dict[str, str] = field(default_factory=dict)
    graphs: dict[str, tuple[str, list[str], frozenset[str]]] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    # scale factor per source metric name (0.0 = conflict sentinel → don't scale)
    scales: dict[str, float] = field(default_factory=dict)


@lru_cache(maxsize=1)
def _load_cmk_graphing_data() -> _CMKGraphingData:
    """Single-pass loader for CMK metric titles, graph templates, unit symbols, and scale factors."""
    if not _cmk_integration.available:
        return _CMKGraphingData()
    try:
        from cmk.graphing.v1 import graphs as _gg
        from cmk.graphing.v1 import metrics as _gm
        from cmk.graphing.v1 import translations as _gt
    except ImportError:
        return _CMKGraphingData()
    data = _CMKGraphingData()
    for mod in _iter_graphing_modules(_get_plugin_dirs()):
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if attr.startswith("metric_") and isinstance(obj, _gm.Metric):
                try:
                    data.titles[obj.name] = obj.title.localize(_identity)
                    data.units[obj.name] = getattr(obj.unit.notation, "symbol", "")
                except Exception:
                    pass
            elif attr.startswith("graph_") and isinstance(obj, _gg.Graph):
                names = _extract_graph_metric_names(obj)
                if names:
                    try:
                        conflicting: frozenset[str] = frozenset(getattr(obj, "conflicting", ()))
                        data.graphs[obj.name] = (obj.title.localize(_identity), names, conflicting)
                    except Exception:
                        pass
            elif attr.startswith("translation_") and hasattr(obj, "translations"):
                try:
                    for src_metric, trans in obj.translations.items():
                        if src_metric.startswith("~"):
                            continue
                        if isinstance(trans, (_gt.ScaleBy, _gt.RenameToAndScaleBy)):
                            factor = float(trans.factor)
                            if src_metric in data.scales and data.scales[src_metric] != factor:
                                data.scales[src_metric] = 0.0  # conflict: two different factors
                            elif src_metric not in data.scales:
                                data.scales[src_metric] = factor
                except Exception:
                    pass
    logger.debug(
        "Loaded %d CMK metric titles, %d graph templates, %d scale factors",
        len(data.titles),
        len(data.graphs),
        len(data.scales),
    )
    return data


def _extract_graph_metric_names(graph: object) -> list[str]:
    """Extract metric names from compound_lines only (the actual data series).

    Recursively handles complex Quantity expressions (Sum, WarningOf, …).
    simple_lines are excluded — they contain threshold/overlay lines derived
    from compound metrics and would cause false-positive matches.
    """
    seen: set[str] = set()
    names: list[str] = []
    for item in getattr(graph, "compound_lines", ()):
        for name in _extract_quantity_metrics(item):
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names


def _load_cmk_metric_titles() -> dict[str, str]:
    return _load_cmk_graphing_data().titles


def _load_cmk_graphs() -> dict[str, tuple[str, list[str], frozenset[str]]]:
    return _load_cmk_graphing_data().graphs


def _load_cmk_metric_units() -> dict[str, str]:
    return _load_cmk_graphing_data().units


def _load_cmk_metric_scales() -> dict[str, float]:
    return _load_cmk_graphing_data().scales


def _match_graphs(available: set[str]) -> list[GraphGroup]:
    """Return CMK graph groups whose compound metrics overlap with ``available``.

    Graphs with conflicting metrics present in ``available`` are excluded.
    When multiple graphs share the same title, only the best-matching one
    (most metrics covered) is kept.
    """
    candidates: list[GraphGroup] = []
    for graph_id, (title, metrics, conflicting) in _load_cmk_graphs().items():
        if conflicting & available:
            continue
        matching = [m for m in metrics if m in available]
        if matching:
            candidates.append(GraphGroup(id=graph_id, title=title, metrics=matching))

    # Deduplicate by title: keep the group with the most matching metrics
    best: dict[str, GraphGroup] = {}
    for g in candidates:
        existing = best.get(g.title)
        if existing is None or len(g.metrics) > len(existing.metrics):
            best[g.title] = g
    return list(best.values())


def _cmk_metric_title(label: str) -> str:
    return _load_cmk_metric_titles().get(label) or " ".join(
        w.capitalize() for w in label.split("_")
    )


def _ls_escape(value: str) -> str:
    """Strip newline/carriage-return characters to prevent Livestatus query injection.

    LQL filter values are terminated by a newline; embedding one would allow injecting
    additional filter lines or commands into the query.
    """
    return value.replace("\r", "").replace("\n", "")


# ---------------------------------------------------------------------------
# Typed Livestatus row helpers
# ---------------------------------------------------------------------------

# A Livestatus row is a heterogeneous JSON array: each column can hold a scalar,
# a list, or an object. We treat it as list[object] and use the _row_* helpers
# below for typed extraction with sensible defaults.
LivestatusRow = list[object]


def _row_str(row: LivestatusRow, idx: int, default: str = "") -> str:
    if idx >= len(row):
        return default
    v = row[idx]
    return v if isinstance(v, str) else default


def _row_int(row: LivestatusRow, idx: int, default: int = 0) -> int:
    if idx >= len(row):
        return default
    v = row[idx]
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int | float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return default
    return default


def _row_float(row: LivestatusRow, idx: int, default: float = 0.0) -> float:
    if idx >= len(row):
        return default
    v = row[idx]
    if isinstance(v, bool):
        return float(v)
    if isinstance(v, int | float):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except ValueError:
            return default
    return default


def _row_bool(row: LivestatusRow, idx: int, *, default: bool = True) -> bool:
    if idx >= len(row):
        return default
    return bool(_row_int(row, idx, default=1 if default else 0))


def _row_list(row: LivestatusRow, idx: int) -> list[object]:
    if idx >= len(row):
        return []
    v = row[idx]
    return v if isinstance(v, list) else []


def _row_dict(row: LivestatusRow, idx: int) -> dict[str, object]:
    if idx >= len(row):
        return {}
    v = row[idx]
    return v if isinstance(v, dict) else {}


def _services_summary_from_row(row: LivestatusRow, base: int) -> ServicesSummary:
    """Build ``ServicesSummary`` from 5 consecutive ``num_services_*`` columns
    starting at ``base`` (order: ok, warn, crit, unknown, pending)."""
    return ServicesSummary(
        ok=_row_int(row, base),
        warning=_row_int(row, base + 1),
        critical=_row_int(row, base + 2),
        unknown=_row_int(row, base + 3),
        pending=_row_int(row, base + 4),
    )


class _ExtraFields(TypedDict, total=False):
    """Tail columns of a Livestatus host/service row — mapped onto ObjectState."""

    address: str
    alias: str
    last_check: float | None
    next_check: float | None
    state_type: str
    current_attempt: int
    max_attempts: int
    last_state_change: float | None
    notifications_enabled: bool
    active_checks_enabled: bool


class _MetricInfo(TypedDict):
    """Parsed perf_data entry (label + unit) used for rrddata queries."""

    label: str
    unit: str


def _rrd_metric_id(label: str) -> str:
    """Sanitize a perf_data metric label for use in a Livestatus rrddata column spec.

    CMC stores metrics with underscores in place of spaces and colons. The column
    name must not contain spaces or colons because those are delimiters in the LQL
    Columns header.
    """
    return label.replace(" ", "_").replace(":", "_")


# Livestatus state code → string mapping
_HOST_STATE_MAP = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
_SERVICE_STATE_MAP = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}
# Checkmk BI aggregation states (cmk.bi.bi_aggregation.BIStates).
# -2 = ERROR / 4 = UNREACHABLE — both rare; collapsed onto UNKNOWN for OrbVis.
_BI_STATE_MAP = {
    -2: "UNKNOWN",
    -1: "PENDING",
    0: "OK",
    1: "WARNING",
    2: "CRITICAL",
    3: "UNKNOWN",
    4: "UNKNOWN",
}


def _aggregations_to_object_states(
    raw: Mapping[str, object] | object, requested_ids: list[str]
) -> dict[str, ObjectState]:
    """Map a Checkmk BI result dict to OrbVis ObjectState entries.

    *raw* is a mapping ``{aggregation_id: {state, output, acknowledged, in_downtime}}``,
    produced either by the in-process cmk.bi path or by the REST API. Missing
    entries get a stale PENDING placeholder so the caller never sees gaps.
    """
    aggrs: Mapping[str, object] = raw if isinstance(raw, Mapping) else {}
    out: dict[str, ObjectState] = {}
    for aid in requested_ids:
        entry = aggrs.get(aid)
        if not isinstance(entry, dict):
            out[aid] = ObjectState(object_id="", type="aggregation", state="PENDING", stale=True)
            continue
        out[aid] = ObjectState(
            object_id="",
            type="aggregation",
            state=_BI_STATE_MAP.get(int(entry.get("state", -1) or -1), "UNKNOWN"),
            output=str(entry.get("output", "") or ""),
            acknowledged=bool(entry.get("acknowledged", False)),
            in_downtime=bool(entry.get("in_downtime", False)),
        )
    return out


def _hierarchy_to_node(node: Mapping[str, object], depth: int, max_depth: int) -> AggregationNode:
    """Convert one node from Checkmks ajax_fetch_aggregation_data hierarchy.

    Standalone-mode shape (per ``cmk.gui.nodevis.aggregation``): ``node_type``,
    ``name``, ``children`` plus state info under ``type_specific.core`` and
    leaf host/service identifiers in the same dict.
    """
    type_specific = node.get("type_specific")
    core: Mapping[str, object] = {}
    if isinstance(type_specific, Mapping):
        c = type_specific.get("core")
        if isinstance(c, Mapping):
            core = c

    node_type: Literal["bi_aggregator", "bi_leaf"] = (
        "bi_aggregator" if str(node.get("node_type") or "") == "bi_aggregator" else "bi_leaf"
    )
    host_name = str(core.get("hostname") or "") or None
    service = str(core.get("service") or "") or None

    children_raw = node.get("children") if depth < max_depth else None
    children: list[AggregationNode] = []
    if isinstance(children_raw, list):
        for child in children_raw:
            if isinstance(child, Mapping):
                children.append(_hierarchy_to_node(child, depth + 1, max_depth))

    state_raw = core.get("state", -1)
    state_val = int(state_raw) if isinstance(state_raw, int | float | str) else -1
    return AggregationNode(
        name=str(node.get("name") or ""),
        node_type=node_type,
        state=state_val,
        in_downtime=bool(core.get("in_downtime", False)),
        acknowledged=bool(core.get("acknowledged", False)),
        host_name=host_name,
        service_description=service,
        children=children,
    )


# Aggregate: worst state wins (higher = worse)
_HOST_SEVERITY = {"UP": 0, "UNREACHABLE": 1, "DOWN": 2, "PENDING": -1}
_SERVICE_SEVERITY = {"OK": 0, "UNKNOWN": 1, "WARNING": 2, "CRITICAL": 3, "PENDING": -1}
_STATE_TYPE_MAP = {0: "SOFT", 1: "HARD"}

_HOST_EXTRA_COLS = (
    "address alias last_check next_check state_type current_attempt max_check_attempts"
    " last_state_change notifications_enabled active_checks_enabled"
)
_SVC_EXTRA_COLS = (
    "last_check next_check state_type current_attempt max_check_attempts last_state_change"
    " notifications_enabled active_checks_enabled"
)


def _apply_extra(
    state: ObjectState, row: LivestatusRow, offset: int = 5, *, include_address: bool = False
) -> ObjectState:
    """Fill the tail ObjectState fields (address, timings, attempt counters) from the row."""
    col = offset
    if include_address:
        state.address = _row_str(row, col)
        state.alias = _row_str(row, col + 1)
        col += 2
    lc = _row_float(row, col)
    nc = _row_float(row, col + 1)
    lsc = _row_float(row, col + 5)
    state.last_check = lc if lc > 0 else None
    state.next_check = nc if nc > 0 else None
    state.state_type = _STATE_TYPE_MAP.get(_row_int(row, col + 2, default=1), "HARD")
    state.current_attempt = _row_int(row, col + 3)
    state.max_attempts = _row_int(row, col + 4)
    state.last_state_change = lsc if lsc > 0 else None
    state.notifications_enabled = _row_bool(row, col + 6, default=True)
    state.active_checks_enabled = _row_bool(row, col + 7, default=True)
    return state


def _is_central_local_socket(host: str | None, socket_path: str) -> bool:
    if not settings.checkmk_omd_root or host is not None:
        return False
    return socket_path == str(Path(settings.checkmk_omd_root) / "tmp" / "run" / "live")


def _build_state_from_row(
    row: LivestatusRow,
    state_map: dict[int, str],
    type_: str,
    *,
    include_address: bool = False,
) -> ObjectState:
    """Construct an ObjectState from a livestatus row with the standard 5-column prefix."""
    state = ObjectState(
        object_id="",
        type=type_,
        state=state_map.get(_row_int(row, 0), "UNKNOWN"),
        output=_row_str(row, 1),
        perf_data=_row_str(row, 2),
        acknowledged=_row_bool(row, 3, default=False),
        in_downtime=_row_int(row, 4) > 0,
    )
    return _apply_extra(state, row, include_address=include_address)


def _parse_host_state_row(row: LivestatusRow) -> tuple[str, ObjectState]:
    """Parse host row [name, state, output, perf_data, ack, downtime, ...extra]."""
    state = ObjectState(
        object_id="",
        type="host",
        state=_HOST_STATE_MAP.get(_row_int(row, 1), "UNKNOWN"),
        output=_row_str(row, 2),
        perf_data=_row_str(row, 3),
        acknowledged=_row_bool(row, 4, default=False),
        in_downtime=_row_int(row, 5) > 0,
    )
    return _row_str(row, 0), _apply_extra(state, row, offset=6, include_address=True)


def _parse_service_state_row(row: LivestatusRow) -> tuple[tuple[str, str], ObjectState]:
    """Parse service row [host_name, description, state, output, perf_data, ack, downtime, ...extra]."""
    state = ObjectState(
        object_id="",
        type="service",
        state=_SERVICE_STATE_MAP.get(_row_int(row, 2), "UNKNOWN"),
        output=_row_str(row, 3),
        perf_data=_row_str(row, 4),
        acknowledged=_row_bool(row, 5, default=False),
        in_downtime=_row_int(row, 6) > 0,
    )
    return (_row_str(row, 0), _row_str(row, 1)), _apply_extra(state, row, offset=7)


def _parse_metrics_from_perf(perf_data: str) -> list[_MetricInfo]:
    """Parse perf_data string into [{label, unit}] for rrddata queries."""
    results: list[_MetricInfo] = []
    for part in _re.findall(r"(?:'[^']+'|[^\s]+)=\S*", perf_data):
        eq = part.index("=")
        label = part[:eq].strip("'")
        rest = part[eq + 1 :]
        # Extract unit from the value part (digits/dots/minus, then unit letters)
        m = _re.match(r"[-\d.]+([a-zA-Z%]*)", rest.split(";")[0])
        unit = m.group(1) if m else ""
        results.append({"label": label, "unit": unit})
    return results


class LivestatusConnection(ConnectionBase):
    """Connects to a Livestatus socket (Unix or TCP) and queries host/service states."""

    connection_id: str = "live_1"

    def __init__(
        self,
        socket_path: str = "/var/run/nagios/rw/live",
        host: str | None = None,
        port: int = 6557,
        timeout: float = 10.0,
        checkmk_url: str | None = None,
        automation_user: str | None = None,
        automation_secret: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self._socket_path = socket_path
        self._host = host
        self._port = port
        self._timeout = timeout
        self._checkmk_url = checkmk_url
        self._automation_user = automation_user
        self._automation_secret = automation_secret
        self._verify_ssl = verify_ssl
        self._semaphore = asyncio.Semaphore(settings.connection_pool_size)
        self._aggregations_cache: tuple[float, list[AggregationInfo]] | None = None
        # Per-host-set cache for get_services_summary (TTL=_SERVICES_SUMMARY_CACHE_TTL)
        self._services_summary_cache: dict[
            frozenset[str], tuple[float, dict[str, ServicesSummary]]
        ] = {}

        # Auto-federate when this connection points at the central site's local
        # Livestatus socket — the socket only sees local data, so MultiSiteConnection
        # is required to also reach remote-site hosts/services.
        self._sites: dict[str, dict[str, object]] | None = (
            _cmk_sites.load_sites() if _is_central_local_socket(host, socket_path) else None
        )
        self._mc: MultiSiteConnection | None = None  # lazy
        self._mc_mtime: float = 0.0
        self._mc_lock = threading.Lock()
        self._mc_dead: set[str] = set()
        if self._sites:
            logger.info(
                "Livestatus federation enabled: %d sites (%s)",
                len(self._sites),
                ", ".join(sorted(self._sites)),
            )

    @asynccontextmanager
    async def with_auth_user(self, username: str) -> AsyncIterator[None]:
        """Context manager: scope Livestatus queries to *username*'s contact groups.

        While active, every ``_query_raw`` call in this asyncio task appends
        ``AuthUser: <username>`` to the LQL request so Livestatus only returns
        hosts/services the user is a contact for.
        """
        token = _auth_user_ctx.set(username)
        try:
            yield
        finally:
            _auth_user_ctx.reset(token)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_host_state(self, hostname: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: state plugin_output perf_data acknowledged scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"Filter: name = {_ls_escape(hostname)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="host", state="PENDING")
        return _build_state_from_row(rows[0], _HOST_STATE_MAP, "host", include_address=True)

    async def get_service_state(self, host: str, service: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: state plugin_output perf_data acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"Filter: host_name = {_ls_escape(host)}\n"
            f"Filter: description = {_ls_escape(service)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="service", state="PENDING")
        return _build_state_from_row(rows[0], _SERVICE_STATE_MAP, "service")

    async def get_service_perf_and_cmd(self, host: str, service: str) -> tuple[str, str]:
        """Return (perf_data, check_command) for a single service."""
        query = (
            f"GET services\n"
            f"Columns: perf_data check_command\n"
            f"Filter: host_name = {_ls_escape(host)}\n"
            f"Filter: description = {_ls_escape(service)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return "", ""
        r = rows[0]
        return _row_str(r, 0), _row_str(r, 1)

    async def get_host_hard_state(self, hostname: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: last_hard_state plugin_output perf_data acknowledged scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"Filter: name = {_ls_escape(hostname)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="host", state="PENDING")
        return _build_state_from_row(rows[0], _HOST_STATE_MAP, "host", include_address=True)

    async def get_service_hard_state(self, host: str, service: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: last_hard_state plugin_output perf_data acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"Filter: host_name = {_ls_escape(host)}\n"
            f"Filter: description = {_ls_escape(service)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="service", state="PENDING")
        return _build_state_from_row(rows[0], _SERVICE_STATE_MAP, "service")

    async def get_hostgroup_states(self, group: str) -> ObjectState:
        # Distinguish "group does not exist" (NOT_FOUND) from "group exists but
        # is empty / hosts not yet checked" (PENDING) so the UI can render them
        # differently. Two queries are intentional — `GET hosts ... Filter:
        # groups >=` returns 0 rows for both cases, which is what the user
        # complained about.
        exists_q = f"GET hostgroups\nColumns: name\nFilter: name = {_ls_escape(group)}\n"
        exists_rows = await self._query(exists_q)
        if not exists_rows:
            return ObjectState(object_id="", type="hostgroup", state="NOT_FOUND")
        query = f"GET hosts\nColumns: state\nFilter: groups >= {_ls_escape(group)}\n"
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="hostgroup", state="PENDING")
        worst = max(
            (_HOST_STATE_MAP.get(_row_int(r, 0), "UNKNOWN") for r in rows),
            key=lambda s: _HOST_SEVERITY.get(s, 0),
        )
        return ObjectState(object_id="", type="hostgroup", state=worst)

    async def get_servicegroup_states(self, group: str) -> ObjectState:
        exists_q = f"GET servicegroups\nColumns: name\nFilter: name = {_ls_escape(group)}\n"
        exists_rows = await self._query(exists_q)
        if not exists_rows:
            return ObjectState(object_id="", type="servicegroup", state="NOT_FOUND")
        query = f"GET services\nColumns: state\nFilter: groups >= {_ls_escape(group)}\n"
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="servicegroup", state="PENDING")
        worst = max(
            (_SERVICE_STATE_MAP.get(_row_int(r, 0), "UNKNOWN") for r in rows),
            key=lambda s: _SERVICE_SEVERITY.get(s, 0),
        )
        return ObjectState(object_id="", type="servicegroup", state=worst)

    async def get_objects(self, obj_type: str) -> list[str]:
        if obj_type == "host":
            rows = await self._query("GET hosts\nColumns: name\n")
            return [_row_str(r, 0) for r in rows]
        if obj_type == "service":
            rows = await self._query("GET services\nColumns: host_name description\n")
            return [f"{_row_str(r, 0)};{_row_str(r, 1)}" for r in rows]
        if obj_type == "hostgroup":
            rows = await self._query("GET hostgroups\nColumns: name\n")
            return [_row_str(r, 0) for r in rows]
        if obj_type == "servicegroup":
            rows = await self._query("GET servicegroups\nColumns: name\n")
            return [_row_str(r, 0) for r in rows]
        return []

    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        if group_type == "all_hosts":
            rows = await self._query("GET hosts\nColumns: name\n")
            return [_row_str(r, 0) for r in rows]
        if group_type == "all_services":
            rows = await self._query("GET services\nColumns: host_name description\n")
            return [f"{_row_str(r, 0)};{_row_str(r, 1)}" for r in rows]
        if group_type == "hostgroup":
            query = f"GET hosts\nColumns: name\nFilter: groups >= {_ls_escape(group_name)}\n"
            rows = await self._query(query)
            return [_row_str(r, 0) for r in rows]
        if group_type == "servicegroup":
            query = f"GET services\nColumns: host_name description\nFilter: groups >= {_ls_escape(group_name)}\n"
            rows = await self._query(query)
            return [f"{_row_str(r, 0)};{_row_str(r, 1)}" for r in rows]
        return []

    async def get_topology(self) -> list[TopologyRow]:
        # Fetch hosts + status-detail columns + per-host service-state counters.
        # The num_services_* columns are O(1) on the hosts table (Livestatus
        # core maintains them) so the donut summary comes for free in this
        # single query — no separate Stats round-trip, multisite-safe because
        # each row is self-contained per host.
        tagged = await self._query_with_site(
            "GET hosts\n"
            "Columns: name parents state plugin_output "
            "alias address acknowledged scheduled_downtime_depth last_check next_check "
            "state_type current_attempt max_check_attempts last_state_change "
            "notifications_enabled active_checks_enabled "
            "num_services_ok num_services_warn num_services_crit "
            "num_services_unknown num_services_pending\n"
        )
        result: list[TopologyRow] = []
        for site_id, r in tagged:
            name = _row_str(r, 0)
            if not name:
                continue
            raw_parents = r[1] if len(r) > 1 else ""
            if isinstance(raw_parents, list):
                parents = [p for p in raw_parents if isinstance(p, str) and p]
            elif isinstance(raw_parents, str):
                parents = [p.strip() for p in raw_parents.split(",") if p.strip()]
            else:
                parents = []
            lc = _row_float(r, 8)
            nc = _row_float(r, 9)
            lsc = _row_float(r, 13)
            row: TopologyRow = {
                "name": name,
                "parents": parents,
                "state": _HOST_STATE_MAP.get(_row_int(r, 2), "UNKNOWN"),
                "output": _row_str(r, 3),
                "alias": _row_str(r, 4),
                "address": _row_str(r, 5),
                "acknowledged": _row_bool(r, 6, default=False),
                "in_downtime": _row_int(r, 7) > 0,
                "last_check": lc if lc > 0 else None,
                "next_check": nc if nc > 0 else None,
                "state_type": _STATE_TYPE_MAP.get(_row_int(r, 10, default=1), "HARD"),
                "current_attempt": _row_int(r, 11),
                "max_attempts": _row_int(r, 12),
                "last_state_change": lsc if lsc > 0 else None,
                "notifications_enabled": _row_bool(r, 14, default=True),
                "active_checks_enabled": _row_bool(r, 15, default=True),
                "services_summary": _services_summary_from_row(r, 16),
            }
            if site_id is not None:
                row["site_id"] = site_id
            result.append(row)
        return result

    async def get_host_services(self, hostname: str) -> list[ServiceRow]:
        rows = await self._query(
            "GET services\n"
            f"Filter: host_name = {_ls_escape(hostname)}\n"
            "Columns: description state plugin_output\n"
        )
        return [
            ServiceRow(
                name=_row_str(r, 0),
                state=_SERVICE_STATE_MAP.get(_row_int(r, 1), "UNKNOWN"),
                output=_row_str(r, 2),
            )
            for r in rows
        ]

    async def get_host_geo(self, hostname: str) -> tuple[float, float] | None:
        query = (
            f"GET hosts\n"
            f"Columns: labels custom_variable_names custom_variable_values\n"
            f"Filter: name = {_ls_escape(hostname)}\n"
        )
        rows = await self._query(query)
        if not rows or not rows[0]:
            return None
        r = rows[0]

        # 1. OrbVis labels: orbvis_lat / orbvis_lng
        labels = _row_dict(r, 0)
        lat_raw = labels.get("orbvis_lat")
        lng_raw = labels.get("orbvis_lng")
        if lat_raw is not None and lng_raw is not None:
            try:
                return float(str(lat_raw)), float(str(lng_raw))
            except (TypeError, ValueError):
                pass

        # 2. Legacy custom variables: LAT / LONG
        names = _row_list(r, 1)
        values = _row_list(r, 2)
        cv: dict[str, object] = {
            str(n): v for n, v in zip(names, values, strict=False) if isinstance(n, str)
        }
        lat_raw = cv.get("LAT")
        lng_raw = cv.get("LONG")
        if lat_raw is not None and lng_raw is not None:
            try:
                return float(str(lat_raw)), float(str(lng_raw))
            except (TypeError, ValueError):
                return None
        return None

    async def get_graph_templates(self, host: str, service: str | None) -> list[GraphGroup]:
        try:
            if service:
                state = await self.get_service_state(host, service)
            else:
                state = await self.get_host_state(host)
            metrics = {
                part[: part.index("=")].strip("'")
                for part in _re.findall(r"(?:'[^']+'|[^\s]+)=[^\s]*", state.perf_data)
            }
            return _match_graphs(metrics)
        except Exception:
            return []

    async def get_metric_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Fetch metric history.

        Uses Checkmk Web API (webapi.py) when automation credentials are configured
        (Checkmk Raw / Nagios core). Falls back to Livestatus rrddata column otherwise
        (Checkmk Enterprise / CMC only).
        """
        if self._checkmk_url and self._automation_user and self._automation_secret:
            return await self._fetch_cmk_graph_history(host, service, start, end)
        return await self._fetch_rrddata_history(host, service, start, end)

    async def _fetch_cmk_graph_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Fetch metric history via Checkmk 2.x REST API (works with Nagios/Raw core)."""
        from datetime import datetime

        assert self._checkmk_url is not None
        cmk_url = self._checkmk_url.rstrip("/")
        if cmk_url.startswith("/"):
            cmk_url = "http://127.0.0.1" + cmk_url
        base_url = cmk_url
        parts = base_url.rstrip("/").split("/")
        site = parts[-2] if len(parts) >= 2 and parts[-1] == "check_mk" else parts[-1]
        api_url = base_url + "/api/1.0/domain-types/metric/actions/get/invoke"
        auth_header = f"Bearer {self._automation_user} {self._automation_secret}"

        metric_names = await self._get_perf_metric_names(host, service)
        if not metric_names:
            metric_names = await self._get_cmk_metric_names(host, service, base_url, auth_header)
        if not metric_names:
            return MetricHistoryResult()

        start_dt = datetime.fromtimestamp(start, tz=UTC).isoformat()
        end_dt = datetime.fromtimestamp(end, tz=UTC).isoformat()

        series: dict[str, list[tuple[float, float, str]]] = {}
        titles: dict[str, str] = {}
        try:
            async with httpx.AsyncClient(verify=self._verify_ssl, timeout=self._timeout) as client:
                for metric_id in metric_names[:5]:
                    body = {
                        "time_range": {"start": start_dt, "end": end_dt},
                        "site": site,
                        "host_name": host,
                        "service_description": service or "",
                        "type": "single_metric",
                        "metric_id": metric_id,
                    }
                    try:
                        resp = await client.post(
                            api_url,
                            json=body,
                            headers={"Authorization": auth_header, "Accept": "application/json"},
                        )
                        if resp.status_code != 200:
                            logger.debug("CMK REST API %s: HTTP %s", metric_id, resp.status_code)
                            continue
                        data = resp.json()
                    except Exception as exc:
                        logger.debug("CMK REST API request failed for %s: %s", metric_id, exc)
                        continue

                    step = float(data.get("step", 60))
                    try:
                        ts_start = datetime.fromisoformat(
                            data.get("time_range", {}).get("start", "")
                        ).timestamp()
                    except Exception:
                        ts_start = float(start)

                    for metric in data.get("metrics", []):
                        unit_obj = metric.get("unit", {}) or {}
                        unit = unit_obj.get("symbol", "") or ""
                        points: list[tuple[float, float, str]] = [
                            (ts_start + i * step, float(v), unit)
                            for i, v in enumerate(metric.get("data_points", []))
                            if v is not None
                        ]
                        if points:
                            series[metric_id] = points
                            title = metric.get("title", "") or ""
                            if title:
                                titles[metric_id] = title
                            break
        except Exception as exc:
            logger.warning("CMK REST API metric history failed: %s", exc)
        return MetricHistoryResult(series=series, titles=titles)

    async def _get_perf_metric_names(self, host: str, service: str | None) -> list[str]:
        """Get metric names from Livestatus perf_data for a host/service."""
        if service:
            query = (
                f"GET services\n"
                f"Columns: perf_data\n"
                f"Filter: host_name = {_ls_escape(host)}\n"
                f"Filter: description = {_ls_escape(service)}\n"
            )
        else:
            query = f"GET hosts\nColumns: perf_data\nFilter: name = {_ls_escape(host)}\n"
        try:
            rows = await self._query(query)
            if not rows or not rows[0]:
                return []
            perf_data = str(rows[0][0])
            return [m.split("=")[0].strip() for m in perf_data.split() if "=" in m]
        except Exception as exc:
            logger.debug("Failed to get perf_data from Livestatus: %s", exc)
            return []

    async def _get_cmk_metric_names(
        self,
        host: str,
        service: str | None,
        base_url: str,
        auth_header: str,
    ) -> list[str]:
        """Fallback: get metric names via Checkmk REST API service endpoint."""
        if not service:
            return []
        url = (
            base_url
            + "/api/1.0/domain-types/service/collections/all"
            + f"?host_name={host}&columns=metrics&columns=description"
        )
        try:
            async with httpx.AsyncClient(verify=self._verify_ssl, timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": auth_header, "Accept": "application/json"},
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
                for item in data.get("value", []):
                    ext = item.get("extensions", {})
                    if ext.get("description") == service:
                        metrics = ext.get("metrics", [])
                        return list(metrics) if metrics else []
                return []
        except Exception as exc:
            logger.warning("CMK REST API metric names fallback failed: %s", exc)
            return []

    async def _fetch_rrddata_history(
        self,
        host: str,
        service: str | None,
        start: int,
        end: int,
    ) -> MetricHistoryResult:
        """Fetch metric history via Livestatus rrddata column (Checkmk Enterprise/CMC only)."""
        logger.debug("rrddata fetch: host=%r service=%r start=%d end=%d", host, service, start, end)

        try:
            if service:
                state = await self.get_service_state(host, service)
            else:
                state = await self.get_host_state(host)
        except Exception as exc:
            logger.warning("rrddata: failed to get state for %r/%r: %s", host, service, exc)
            return MetricHistoryResult()

        metrics = _parse_metrics_from_perf(state.perf_data or "")
        if not metrics:
            logger.debug("rrddata: no metrics in perf_data for %r/%r", host, service)
            return MetricHistoryResult()

        # CMC/CEE rrddata column format:
        #   rrddata:m1:{metric}.average:{start}:{end}:{step}:{max_entries}
        # step=1 lets CMC pick the finest available RRD archive automatically.
        # max_entries caps the number of returned data points.
        window = end - start
        max_entries = min(max(window // 60, 60), 500)

        rrd_cols = " ".join(
            f"rrddata:m1:{_rrd_metric_id(m['label'])}.average:{start}:{end}:1:{max_entries}"
            for m in metrics
        )
        if service:
            query = (
                f"GET services\n"
                f"Columns: {rrd_cols}\n"
                f"Filter: host_name = {_ls_escape(host)}\n"
                f"Filter: description = {_ls_escape(service)}\n"
            )
        else:
            query = f"GET hosts\nColumns: {rrd_cols}\nFilter: name = {_ls_escape(host)}\n"

        try:
            rows = await self._query(query)
        except Exception as exc:
            logger.warning(
                "rrddata query failed for %r/%r (CMC/Enterprise required): %s",
                host,
                service,
                exc,
            )
            logger.debug("rrddata failed query was:\n%s", query)
            return MetricHistoryResult()

        if not rows or not rows[0]:
            logger.debug(
                "rrddata: empty result for %r/%r (no rrddata support or no data in range)",
                host,
                service,
            )
            return MetricHistoryResult()

        # CMC returns each rrddata column as a flat list:
        #   [actual_start, actual_end, actual_step, v0, v1, ..., vN]
        # A value of None means no RRD file / metric exists for this column.
        metric_scales = _load_cmk_metric_scales()
        metric_units = _load_cmk_metric_units()
        series: dict[str, list[tuple[float, float, str]]] = {}
        titles: dict[str, str] = {}
        row = rows[0]
        for i, m in enumerate(metrics):
            if i >= len(row):
                continue
            rrd = row[i]
            if not rrd or not isinstance(rrd, list) or len(rrd) < 4:
                continue
            try:
                actual_start = float(rrd[0])
                actual_step = float(rrd[2])
                values = rrd[3:]
                label = m["label"]
                perf_unit = m["unit"]
                # CMK translations (e.g. ScaleBy(1048576) for fs_used) convert check-plugin
                # units (MiB) to the canonical graphing unit (bytes) at display time; apply
                # the same factor here. Guard: values ≥1e9 are already in bytes (Linux mem
                # checks), so skip scaling even when a Windows translation matches the name.
                scale = metric_scales.get(label, 0.0) if perf_unit == "" else 0.0
                if scale > 0:
                    first = next((float(v) for v in values if v is not None), None)
                    if first is not None and abs(first) >= 1e9:
                        scale = 0.0
                unit = metric_units.get(label, perf_unit) if perf_unit == "" else perf_unit
                points: list[tuple[float, float, str]] = []
                for j, v in enumerate(values):
                    if v is not None:
                        ts = actual_start + j * actual_step
                        val = float(v) * scale if scale > 0 else float(v)
                        points.append((ts, val, unit))
                if points:
                    series[label] = points
                    titles[label] = _cmk_metric_title(label)
            except (IndexError, TypeError, ValueError) as exc:
                logger.debug("rrddata: failed to parse metric %r: %s, raw=%r", m["label"], exc, rrd)
                continue

        logger.debug("rrddata: returning %d metrics for %r/%r", len(series), host, service)
        return MetricHistoryResult(
            series=series,
            titles=titles,
            graphs=_match_graphs(set(series.keys())),
        )

    async def is_available(self) -> bool:
        try:
            await self._query("GET hosts\nColumns: name\nLimit: 1\n")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Checkmk BI (Business Intelligence) — REST API
    # ------------------------------------------------------------------

    def _cmk_rest_base(self) -> str | None:
        """Return the Checkmk REST API base, or None if not configured for REST calls."""
        if not (self._checkmk_url and self._automation_user and self._automation_secret):
            return None
        cmk_url = self._checkmk_url.rstrip("/")
        if cmk_url.startswith("/"):
            cmk_url = "http://127.0.0.1" + cmk_url
        return cmk_url + "/api/1.0"

    async def _cmk_rest(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
    ) -> dict[str, object] | None:
        """Call a Checkmk REST endpoint and return parsed JSON; None on any failure."""
        base = self._cmk_rest_base()
        if base is None:
            return None
        url = base + path
        auth = f"Bearer {self._automation_user} {self._automation_secret}"
        try:
            async with httpx.AsyncClient(verify=self._verify_ssl, timeout=self._timeout) as client:
                resp = await client.request(
                    method,
                    url,
                    json=json,
                    headers={"Authorization": auth, "Accept": "application/json"},
                )
                if resp.status_code != 200:
                    logger.debug("CMK REST %s %s: HTTP %s", method, path, resp.status_code)
                    return None
                data = resp.json()
                return data if isinstance(data, dict) else None
        except Exception as exc:
            logger.debug("CMK REST %s %s failed: %s", method, path, exc)
            return None

    async def get_aggregation_state(self, aggregation_id: str) -> ObjectState:
        states = await self.get_aggregations_states([aggregation_id])
        return states.get(
            aggregation_id, ObjectState(object_id="", type="aggregation", state="PENDING")
        )

    def _bi_query_sync(
        self,
        query: object,
        only_sites: object = None,
        fetch_full_data: bool = False,
    ) -> object:
        """Sync Livestatus query for cmk.bi's SitesCallback.

        Runs inside an ``asyncio.to_thread`` worker; spins up a fresh event loop
        to drive our async ``_query_raw``. ``AuthUser:`` is injected automatically
        via the ``_auth_user_ctx`` ContextVar set by ``with_auth_user(...)``.

        Two pieces of compatibility shimming:
        - cmk.bi hardcodes ``Cache: reload`` in compiler.py + data_fetcher.py.
          Some Livestatus connections reject the header with HTTP 400 ("undefined
          request header") — strip it; it's only a perf hint, not correctness.
        - cmk.gui.bi.bi_manager wraps every query in ``sites.prepend_site()``,
          which prepends the site_id column to each row. cmk.bi consumers
          (compiler:309, data_fetcher:363/424) read ``row[0]`` as site_id and
          ``row[1]+`` as actual data — we replicate that here.
        """
        from cmk.livestatus_client._connection import LivestatusResponse

        del fetch_full_data  # bi_fetch_full_data isn't needed

        lql = "\n".join(line for line in str(query).splitlines() if not line.startswith("Cache:"))

        if self._sites:
            sites_filter: list[str] | None = None
            if isinstance(only_sites, list):
                sites_filter = [str(s) for s in only_sites if s]
            return LivestatusResponse(self._run_multisite_sync(lql, only_sites=sites_filter))

        del only_sites
        loop = asyncio.new_event_loop()
        try:
            rows = loop.run_until_complete(self._query_raw(lql))
        finally:
            loop.close()
        site_id = settings.checkmk_site or "local"
        return LivestatusResponse([[site_id, *row] for row in rows])

    async def get_aggregations_states(self, aggregation_ids: list[str]) -> dict[str, ObjectState]:
        if not aggregation_ids:
            return {}

        # Site-mode: in-process cmk.bi (preferred — per-user permissions, no auth)
        if _cmk_integration.cmk_bi_available():
            site_id = settings.checkmk_site or "local"
            site_data = await asyncio.to_thread(
                _cmk_integration.cmk_bi_get_aggregations_states,
                self._bi_query_sync,
                site_id,
                aggregation_ids,
            )
            if site_data:
                return _aggregations_to_object_states(site_data, aggregation_ids)

        # Standalone-mode fallback: REST API with whatever auth the connection
        # connection has (typically Bearer with automation_user/secret).
        rest_data = await self._cmk_rest(
            "POST",
            "/domain-types/bi_aggregation/actions/aggregation_state/invoke",
            json={"filter_names": aggregation_ids},
        )
        if rest_data is None:
            return {
                aid: ObjectState(object_id="", type="aggregation", state="PENDING", stale=True)
                for aid in aggregation_ids
            }
        return _aggregations_to_object_states(rest_data.get("aggregations") or {}, aggregation_ids)

    async def list_aggregations(self) -> list[AggregationInfo]:
        import time as _time

        now = _time.time()
        if self._aggregations_cache is not None and now - self._aggregations_cache[0] < 60.0:
            return self._aggregations_cache[1]

        # Site-mode: in-process cmk.bi
        if _cmk_integration.cmk_bi_available():
            site_id = settings.checkmk_site or "local"
            entries = await asyncio.to_thread(
                _cmk_integration.cmk_bi_list_aggregations,
                self._bi_query_sync,
                site_id,
            )
            if entries:
                result = [
                    AggregationInfo(id=e["id"], title=e["title"], pack_id=e["pack_id"])
                    for e in entries
                ]
                self._aggregations_cache = (now, result)
                return result

        # Standalone-mode fallback: REST API
        data = await self._cmk_rest("GET", "/domain-types/bi_pack/collections/all")
        if data is None:
            return self._aggregations_cache[1] if self._aggregations_cache else []

        result_rest: list[AggregationInfo] = []
        packs = data.get("value")
        for pack in packs if isinstance(packs, list) else []:
            if not isinstance(pack, dict):
                continue
            pack_id = str(pack.get("id", "") or "")
            members_raw = pack.get("members")
            members = members_raw.get("aggregations") if isinstance(members_raw, dict) else None
            aggrs = members.get("value") if isinstance(members, dict) else None
            for aggr in aggrs if isinstance(aggrs, list) else []:
                if not isinstance(aggr, dict):
                    continue
                aid = str(aggr.get("id", "") or "")
                if not aid:
                    continue
                title = str(aggr.get("title", "") or aid)
                result_rest.append(AggregationInfo(id=aid, title=title, pack_id=pack_id))

        self._aggregations_cache = (now, result_rest)
        return result_rest

    async def get_aggregation_tree(
        self, aggregation_id: str, max_depth: int
    ) -> AggregationNode | None:
        if not aggregation_id:
            return None
        max_depth = max(0, min(max_depth, 10))

        if _cmk_integration.cmk_bi_available():
            site_id = settings.checkmk_site or "local"
            tree = await asyncio.to_thread(
                _cmk_integration.cmk_bi_get_aggregation_tree,
                self._bi_query_sync,
                site_id,
                aggregation_id,
                max_depth,
            )
            if tree is not None:
                return AggregationNode.model_validate(tree)

        # Standalone-mode fallback: ajax_fetch_aggregation_data GUI page.
        # Bearer-auth-capable since CMK 2.4; older versions silently return None.
        ajax = await self._cmk_gui_get(
            "/ajax_fetch_aggregation_data.py",
            params={"aggregations": _json.dumps([aggregation_id])},
        )
        if not isinstance(ajax, dict):
            return None
        node_config = ajax.get("node_config")
        hierarchy = node_config.get("hierarchy") if isinstance(node_config, dict) else None
        if not isinstance(hierarchy, dict):
            return None
        return _hierarchy_to_node(hierarchy, depth=0, max_depth=max_depth)

    async def _cmk_gui_get(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> object | None:
        """GET a Checkmk GUI ajax page with the configured Bearer auth.

        ``self._checkmk_url`` is the GUI base (e.g. ``/<site>/check_mk``) so the
        page lives at ``{cmk_url}{path}``. Returns parsed JSON or None.
        """
        if not (self._checkmk_url and self._automation_user and self._automation_secret):
            return None
        cmk_url = self._checkmk_url.rstrip("/")
        if cmk_url.startswith("/"):
            cmk_url = "http://127.0.0.1" + cmk_url
        url = cmk_url + path
        auth = f"Bearer {self._automation_user} {self._automation_secret}"
        try:
            async with httpx.AsyncClient(verify=self._verify_ssl, timeout=self._timeout) as client:
                resp = await client.get(
                    url,
                    params=params,
                    headers={"Authorization": auth, "Accept": "application/json"},
                )
                if resp.status_code != 200:
                    logger.debug("CMK GUI GET %s: HTTP %s", path, resp.status_code)
                    return None
                data: object = resp.json()
                return data
        except Exception as exc:
            logger.debug("CMK GUI GET %s failed: %s", path, exc)
            return None

    # ------------------------------------------------------------------
    # Batch query methods
    # ------------------------------------------------------------------

    async def get_hosts_states(
        self, hostnames: list[str], only_hard: bool = False
    ) -> dict[str, ObjectState]:
        if not hostnames:
            return {}
        state_col = "last_hard_state" if only_hard else "state"
        filters = "".join(f"Filter: name = {_ls_escape(h)}\n" for h in hostnames)
        if len(hostnames) > 1:
            filters += f"Or: {len(hostnames)}\n"
        rows = await self._query(
            f"GET hosts\n"
            f"Columns: name {state_col} plugin_output perf_data acknowledged "
            f"scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"{filters}"
        )
        return dict(_parse_host_state_row(r) for r in rows)

    async def get_all_hosts_states(self, only_hard: bool = False) -> dict[str, ObjectState]:
        state_col = "last_hard_state" if only_hard else "state"
        rows = await self._query(
            f"GET hosts\n"
            f"Columns: name {state_col} plugin_output perf_data acknowledged "
            f"scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
        )
        return dict(_parse_host_state_row(r) for r in rows)

    async def get_all_services_states(
        self, only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        state_col = "last_hard_state" if only_hard else "state"
        rows = await self._query(
            f"GET services\n"
            f"Columns: host_name description {state_col} plugin_output perf_data "
            f"acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
        )
        return dict(_parse_service_state_row(r) for r in rows)

    async def get_services_states(
        self, pairs: list[tuple[str, str]], only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        if not pairs:
            return {}
        state_col = "last_hard_state" if only_hard else "state"
        filter_lines = ""
        for host, svc in pairs:
            filter_lines += (
                f"Filter: host_name = {_ls_escape(host)}\n"
                f"Filter: description = {_ls_escape(svc)}\n"
                f"And: 2\n"
            )
        if len(pairs) > 1:
            filter_lines += f"Or: {len(pairs)}\n"
        rows = await self._query(
            f"GET services\n"
            f"Columns: host_name description {state_col} plugin_output perf_data "
            f"acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"{filter_lines}"
        )
        return dict(_parse_service_state_row(r) for r in rows)

    # Above this host count we drop the per-host filter list and post-filter
    # in Python — mirrors cmk.gui.nodevis.topology._fetch_data: the core
    # spends more on filter evaluation than on returning all rows.
    _SERVICES_SUMMARY_FILTER_THRESHOLD = 500
    # Result cache TTL — slightly under the default refresh interval so a
    # second concurrent refresh of the same board (multi-tab, multi-user) can
    # hit the cache.
    _SERVICES_SUMMARY_CACHE_TTL = 4.0

    async def get_services_summary(self, hostnames: list[str]) -> dict[str, ServicesSummary]:
        """Return service-state counts per host.

        Reads the per-host ``num_services_{ok,warn,crit,unknown,pending}``
        columns straight from the ``hosts`` table — Livestatus core maintains
        them as O(1) counters, so this is a single round-trip regardless of
        host count and multisite-safe (each row is self-contained per host;
        sites merge by simple row concatenation).
        """
        if not hostnames:
            return {}

        cache_key = frozenset(hostnames)
        cached = self._services_summary_cache.get(cache_key)
        now = time.monotonic()
        if cached is not None and now - cached[0] < self._SERVICES_SUMMARY_CACHE_TTL:
            return dict(cached[1])

        query_all = len(hostnames) > self._SERVICES_SUMMARY_FILTER_THRESHOLD
        if query_all:
            filters = ""
        else:
            filters = "".join(f"Filter: name = {_ls_escape(h)}\n" for h in hostnames)
            if len(hostnames) > 1:
                filters += f"Or: {len(hostnames)}\n"
        query = (
            "GET hosts\n"
            "Columns: name num_services_ok num_services_warn num_services_crit "
            "num_services_unknown num_services_pending\n"
            f"{filters}"
        )
        try:
            rows = await self._query(query)
        except Exception:
            logger.warning("services-summary query failed", exc_info=True)
            return {h: ServicesSummary() for h in hostnames}

        wanted = set(hostnames) if query_all else None
        merged: dict[str, ServicesSummary] = {h: ServicesSummary() for h in hostnames}
        for r in rows:
            name = _row_str(r, 0)
            if not name:
                continue
            if wanted is not None and name not in wanted:
                continue
            merged[name] = _services_summary_from_row(r, 1)

        for k in [
            k
            for k, (ts, _) in self._services_summary_cache.items()
            if now - ts >= self._SERVICES_SUMMARY_CACHE_TTL
        ]:
            self._services_summary_cache.pop(k, None)
        self._services_summary_cache[cache_key] = (now, merged)
        if len(self._services_summary_cache) > 32:
            oldest = next(iter(self._services_summary_cache))
            self._services_summary_cache.pop(oldest, None)
        return dict(merged)

    async def get_hosts_services_batch(self, hostnames: list[str]) -> dict[str, list[ServiceRow]]:
        if not hostnames:
            return {}
        filters = "".join(f"Filter: host_name = {_ls_escape(h)}\n" for h in hostnames)
        if len(hostnames) > 1:
            filters += f"Or: {len(hostnames)}\n"
        rows = await self._query(
            f"GET services\nColumns: host_name description state plugin_output\n{filters}"
        )
        results: dict[str, list[ServiceRow]] = {h: [] for h in hostnames}
        for r in rows:
            results[_row_str(r, 0)].append(
                ServiceRow(
                    name=_row_str(r, 1),
                    state=_SERVICE_STATE_MAP.get(_row_int(r, 2), "UNKNOWN"),
                    output=_row_str(r, 3),
                )
            )
        return results

    # ------------------------------------------------------------------
    # Low-level socket communication
    # ------------------------------------------------------------------

    async def _query(self, query: str) -> list[LivestatusRow]:
        """Run a Livestatus query, stripping the federated site_id prefix."""
        return [row for _, row in await self._query_with_site(query)]

    async def _query_with_site(self, query: str) -> list[tuple[str | None, LivestatusRow]]:
        """Run a query and return ``(site_id, row)`` tuples.

        Single-site connections yield ``site_id=None`` so callers can remain
        connection-agnostic.
        """
        if self._sites:
            rows = await asyncio.wait_for(
                asyncio.to_thread(self._run_multisite_sync, query),
                timeout=settings.connection_query_timeout,
            )
            return [
                (str(row[0]) if row and isinstance(row[0], str) else None, row[1:]) for row in rows
            ]
        async with self._semaphore:
            rows = await asyncio.wait_for(
                self._query_raw(query),
                timeout=settings.connection_query_timeout,
            )
        return [(None, r) for r in rows]

    def _run_multisite_sync(
        self, lql: str, only_sites: list[str] | None = None
    ) -> list[list[object]]:
        """Sync federated query via Checkmks ``MultiSiteConnection``.

        Must run in a worker thread (``asyncio.to_thread``); ``MultiSiteConnection``
        is sync. ``AuthUser:`` is sent per-query so the cached connection isn't
        mutated across concurrent users.
        """
        from cmk.livestatus_client import MultiSiteConnection, SiteConfigurations

        if not self._sites:
            return []

        with self._mc_lock:
            current_mtime = _cmk_sites.sites_mk_mtime()
            if self._mc is None or current_mtime != self._mc_mtime:
                if self._mc is not None:
                    logger.info("sites.mk changed — reloading enabled sites")
                self._sites = _cmk_sites.load_sites()
                if not self._sites:
                    self._mc = None
                    self._mc_mtime = current_mtime
                    self._mc_dead = set()
                    return []
                self._mc = MultiSiteConnection(sites=SiteConfigurations(self._sites))
                self._mc.set_prepend_site(True)
                self._mc_mtime = current_mtime
                self._mc_dead = set()
            mc = self._mc

            headers = ""
            auth_user = _auth_user_ctx.get()
            if auth_user:
                headers += f"AuthUser: {auth_user}\n"

            mc.set_only_sites(only_sites)
            try:
                rows = mc.query(lql, add_headers=headers)
            finally:
                mc.set_only_sites(None)

            self._log_dead_site_transitions(mc.dead_sites())
            return list(rows)

    def _log_dead_site_transitions(self, dead: Mapping[str, Mapping[str, object]]) -> None:
        """Log only when a site enters or leaves the dead set, not every query."""
        current = set(dead)
        for sid in current - self._mc_dead:
            logger.warning("Livestatus site %s dead: %s", sid, dead[sid].get("exception"))
        for sid in self._mc_dead - current:
            logger.info("Livestatus site %s recovered", sid)
        self._mc_dead = current

    async def _query_raw(self, query: str) -> list[LivestatusRow]:
        """Send a Livestatus query and return parsed rows."""
        lql = query.rstrip("\n") + "\nOutputFormat: json\nResponseHeader: fixed16\n"
        auth_user = _auth_user_ctx.get()
        if auth_user:
            lql += f"AuthUser: {auth_user}\n"
        lql += "\n"

        if self._host:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout,
            )
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self._socket_path),
                timeout=self._timeout,
            )

        # asyncio.shield() prevents a second CancelledError from aborting
        # wait_closed() when the caller cancels this coroutine mid-cleanup.
        try:
            writer.write(lql.encode())
            await writer.drain()

            # Fixed-16 response header: "200          42\n"
            header = await asyncio.wait_for(reader.read(16), timeout=self._timeout)
            if not header:
                return []
            status = 0
            length = 0
            try:
                status = int(header[:3])
                length = int(header[4:15].strip())
            except ValueError:
                logger.warning("Livestatus returned unexpected response: %r", header)
                return []

            body = b""
            while len(body) < length:
                chunk = await asyncio.wait_for(
                    reader.read(length - len(body)), timeout=self._timeout
                )
                if not chunk:
                    break
                body += chunk

            if status != 200:
                logger.error("Livestatus error %d: %s", status, body.decode())
                return []

            text = body.decode("utf-8").strip()
            if not text:
                return []
            parsed: list[LivestatusRow] = _json.loads(text)
            return parsed
        finally:
            writer.close()
            try:
                await asyncio.shield(writer.wait_closed())
            except Exception:
                pass
