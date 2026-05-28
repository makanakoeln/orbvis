"""MK Livestatus connection via asyncio Unix/TCP socket."""

from __future__ import annotations

import asyncio
import contextlib
import json as _json
import logging
import random
import re
import re as _re
import ssl
import threading
import time
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
    GeoHost,
    GraphGroup,
    GroupMemberRow,
    MetricHistoryResult,
    ServiceRow,
    TopologyRow,
)
from app.core.config import settings
from app.integrations import checkmk as _cmk_integration
from app.integrations import checkmk_sites as _cmk_sites
from app.integrations.cmk_plugins import get_plugin_dirs, iter_graphing_modules
from app.schemas.board import AggregationInfo, AggregationNode
from app.schemas.state import (
    CommentInfo,
    DowntimeInfo,
    ObjectDetails,
    ObjectState,
    ServicesSummary,
)

logger = logging.getLogger(__name__)


class LivestatusProtocolError(RuntimeError):
    """Raised when the Livestatus wire response is missing or malformed.

    Distinct from connect-level errors (refused / timeout) so callers can
    tell "I couldn't reach the socket" apart from "I reached something but
    it didn't speak Livestatus" — the latter is the classic symptom of a
    plain TCP probe against a TLS-wrapped listener.
    """


# When set, every Livestatus query in the current asyncio task includes
# ``AuthUser: <username>`` so Livestatus only returns objects the user
# is a contact for (contact-group filtering).
_auth_user_ctx: ContextVar[str | None] = ContextVar("_auth_user_ctx", default=None)


_EXPRESSION_PLACEHOLDER_RE = re.compile(r"\s*_EXPRESSION:\{[^}]*\}\s*")


def _identity(x: str) -> str:
    # CMK's Title.localize for graphs that embed metric expressions emits raw
    # `_EXPRESSION:{"metric":"…"}` placeholders when no real translator is
    # supplied. Stripping them keeps the legend readable.
    cleaned = _EXPRESSION_PLACEHOLDER_RE.sub(" ", x)
    return " ".join(cleaned.split())


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
    for mod in iter_graphing_modules(get_plugin_dirs()):
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


def _row_float_or_none(row: LivestatusRow, idx: int) -> float | None:
    """Return float for the cell, or None when livestatus reports the missing
    sentinel 0 (used for never-checked services) or the column is absent."""
    if idx >= len(row):
        return None
    v = _row_float(row, idx, default=0.0)
    return v if v > 0 else None


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

# Column lists for the on-demand object-details endpoint. Order matters —
# _build_details indexes positionally.
_HOST_DETAIL_COLS = (
    "long_plugin_output check_command latency execution_time is_flapping"
    " in_notification_period notification_period check_interval"
    " parents childs groups contact_groups labels"
)
_SVC_DETAIL_COLS = (
    "long_plugin_output check_command latency execution_time is_flapping"
    " in_notification_period notification_period check_interval"
    " host_groups groups contact_groups labels last_time_ok"
)
_COMMENT_COLS = "id author comment entry_time expire_time"
_DOWNTIME_COLS = "id author comment start_time end_time fixed"


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
    site_id: str | None = None,
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
        site_id=site_id,
    )
    return _apply_extra(state, row, include_address=include_address)


def _parse_host_state_row(
    row: LivestatusRow, *, site_id: str | None = None
) -> tuple[str, ObjectState]:
    """Parse host row [name, state, output, perf_data, ack, downtime, ...extra]."""
    state = ObjectState(
        object_id="",
        type="host",
        state=_HOST_STATE_MAP.get(_row_int(row, 1), "UNKNOWN"),
        output=_row_str(row, 2),
        perf_data=_row_str(row, 3),
        acknowledged=_row_bool(row, 4, default=False),
        in_downtime=_row_int(row, 5) > 0,
        site_id=site_id,
    )
    return _row_str(row, 0), _apply_extra(state, row, offset=6, include_address=True)


def _parse_service_state_row(
    row: LivestatusRow, *, site_id: str | None = None
) -> tuple[tuple[str, str], ObjectState]:
    """Parse service row [host_name, description, state, output, perf_data, ack, downtime, ...extra]."""
    state = ObjectState(
        object_id="",
        type="service",
        state=_SERVICE_STATE_MAP.get(_row_int(row, 2), "UNKNOWN"),
        output=_row_str(row, 3),
        perf_data=_row_str(row, 4),
        acknowledged=_row_bool(row, 5, default=False),
        in_downtime=_row_int(row, 6) > 0,
        site_id=site_id,
    )
    return (_row_str(row, 0), _row_str(row, 1)), _apply_extra(state, row, offset=7)


def _row_strs(row: LivestatusRow, idx: int) -> list[str]:
    """Return a string list from a Livestatus list-typed column."""
    return [str(x) for x in _row_list(row, idx) if x]


def _build_details(
    type_: Literal["host", "service"],
    host: str,
    service: str | None,
    row: LivestatusRow,
    comment_rows: list[LivestatusRow],
    downtime_rows: list[LivestatusRow],
) -> ObjectDetails:
    """Map a host/service detail row + comments/downtimes onto ObjectDetails.

    Column order must mirror ``_HOST_DETAIL_COLS`` / ``_SVC_DETAIL_COLS``.
    The leading 9 columns are common; the trailing group list differs (host:
    parents, children, groups · service: host_groups, groups + last_time_ok).
    """
    common_count = 8
    d = ObjectDetails(
        type=type_,
        host_name=host,
        service_description=service,
        # Livestatus encodes line breaks in the agent output as the literal "\n"
        # so they survive the line-based wire protocol; the UI wants real newlines.
        long_output=_row_str(row, 0).replace("\\n", "\n").replace("\\r", ""),
        check_command=_row_str(row, 1),
        latency=_row_float_or_none(row, 2),
        execution_time=_row_float_or_none(row, 3),
        is_flapping=_row_bool(row, 4, default=False),
        in_notification_period=_row_bool(row, 5, default=True),
        notification_period=_row_str(row, 6),
        check_interval=_row_float_or_none(row, 7),
    )

    if type_ == "host":
        d.parents = _row_strs(row, common_count)
        d.children = _row_strs(row, common_count + 1)
        d.host_groups = _row_strs(row, common_count + 2)
        d.contact_groups = _row_strs(row, common_count + 3)
        d.labels = {str(k): str(v) for k, v in _row_dict(row, common_count + 4).items()}
    else:
        d.host_groups = _row_strs(row, common_count)
        d.service_groups = _row_strs(row, common_count + 1)
        d.contact_groups = _row_strs(row, common_count + 2)
        d.labels = {str(k): str(v) for k, v in _row_dict(row, common_count + 3).items()}
        d.last_time_ok = _row_float_or_none(row, common_count + 4)

    d.comments = [
        CommentInfo(
            id=_row_int(r, 0),
            author=_row_str(r, 1),
            comment=_row_str(r, 2),
            entry_time=_row_float(r, 3),
            expire_time=_row_float_or_none(r, 4),
        )
        for r in comment_rows
    ]
    d.downtimes = [
        DowntimeInfo(
            id=_row_int(r, 0),
            author=_row_str(r, 1),
            comment=_row_str(r, 2),
            start_time=_row_float(r, 3),
            end_time=_row_float(r, 4),
            fixed=_row_bool(r, 5, default=True),
        )
        for r in downtime_rows
    ]
    return d


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
        tls: bool = True,
        tls_verify: bool = False,
        timeout: float = 10.0,
        checkmk_url: str | None = None,
        automation_user: str | None = None,
        automation_secret: str | None = None,
        verify_ssl: bool = True,
    ) -> None:
        self._socket_path = socket_path
        self._host = host
        self._port = port
        # TLS only applies to the TCP path. OMD's `LIVESTATUS_TLS=on` wraps
        # the 6557 listener in stunnel; opening a plain TCP socket against
        # it succeeds at the TCP layer but the stunnel side drops the bytes,
        # so every query silently returns garbage. Built once at init so a
        # high-fanout flow-board burst doesn't rebuild the context per
        # connection.
        self._tls = tls
        self._tls_verify = tls_verify
        self._ssl_ctx: ssl.SSLContext | None = self._build_ssl_context() if (tls and host) else None
        self._timeout = timeout
        self._checkmk_url = checkmk_url
        self._automation_user = automation_user
        self._automation_secret = automation_secret
        self._verify_ssl = verify_ssl
        self._semaphore = asyncio.Semaphore(settings.connection_pool_size)
        # Separate, tighter cap on bulk-services fan-out so 500-host top-K
        # fetches don't blast the unix-socket listen backlog (EAGAIN). Held
        # at chunk granularity in get_hosts_services_batch.
        self._bulk_chunk_semaphore = asyncio.Semaphore(
            settings.flow_board_bulk_max_concurrent_chunks
        )
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
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="host", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            _HOST_STATE_MAP,
            "host",
            include_address=True,
            site_id=sid if sid is not None else (settings.checkmk_site or "local"),
        )

    async def get_service_state(self, host: str, service: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: state plugin_output perf_data acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"Filter: host_name = {_ls_escape(host)}\n"
            f"Filter: description = {_ls_escape(service)}\n"
        )
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="service", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            _SERVICE_STATE_MAP,
            "service",
            site_id=sid if sid is not None else (settings.checkmk_site or "local"),
        )

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

    async def get_host_details(self, hostname: str) -> ObjectDetails | None:
        return await self._fetch_details("host", hostname, None)

    async def get_service_details(self, hostname: str, service: str) -> ObjectDetails | None:
        return await self._fetch_details("service", hostname, service)

    async def _get_metric_titles(self, host: str, service: str | None) -> dict[str, str]:
        """Lookup display titles for the host/service's perf_data metric IDs."""
        names = await self._get_perf_metric_names(host, service)
        return {n: _cmk_metric_title(n) for n in names}

    async def _fetch_details(
        self, type_: Literal["host", "service"], host: str, service: str | None
    ) -> ObjectDetails | None:
        is_host = type_ == "host"
        now = int(time.time())
        if is_host:
            row_table, row_filter = "hosts", f"Filter: name = {_ls_escape(host)}\n"
            scope_filter = (
                f"Filter: host_name = {_ls_escape(host)}\nFilter: is_service = 0\nAnd: 2\n"
            )
        else:
            assert service is not None
            row_table = "services"
            row_filter = (
                f"Filter: host_name = {_ls_escape(host)}\n"
                f"Filter: description = {_ls_escape(service)}\n"
            )
            scope_filter = (
                f"Filter: host_name = {_ls_escape(host)}\n"
                f"Filter: service_description = {_ls_escape(service)}\nAnd: 2\n"
            )
        cols = _HOST_DETAIL_COLS if is_host else _SVC_DETAIL_COLS
        # Drop expired comments and ended downtimes — the drawer header reads
        # "Active downtimes", and stale comments add noise without value.
        active_cmt = f"Filter: expire_time = 0\nFilter: expire_time >= {now}\nOr: 2\n"
        active_dt = f"Filter: end_time >= {now}\n"
        rows, cmt_rows, dt_rows, metric_titles = await asyncio.gather(
            self._query(f"GET {row_table}\nColumns: {cols}\n{row_filter}"),
            self._query(f"GET comments\nColumns: {_COMMENT_COLS}\n{scope_filter}{active_cmt}"),
            self._query(f"GET downtimes\nColumns: {_DOWNTIME_COLS}\n{scope_filter}{active_dt}"),
            self._get_metric_titles(host, service),
        )
        if not rows:
            return None
        details = _build_details(type_, host, service, rows[0], cmt_rows, dt_rows)
        details.metric_titles = metric_titles
        return details

    async def get_host_hard_state(self, hostname: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: last_hard_state plugin_output perf_data acknowledged scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"Filter: name = {_ls_escape(hostname)}\n"
        )
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="host", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            _HOST_STATE_MAP,
            "host",
            include_address=True,
            site_id=sid if sid is not None else (settings.checkmk_site or "local"),
        )

    async def get_service_hard_state(self, host: str, service: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: last_hard_state plugin_output perf_data acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"Filter: host_name = {_ls_escape(host)}\n"
            f"Filter: description = {_ls_escape(service)}\n"
        )
        tagged = await self._query_with_site(query)
        if not tagged:
            return ObjectState(object_id="", type="service", state="PENDING")
        sid, row = tagged[0]
        return _build_state_from_row(
            row,
            _SERVICE_STATE_MAP,
            "service",
            site_id=sid if sid is not None else (settings.checkmk_site or "local"),
        )

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
        states = [_HOST_STATE_MAP.get(_row_int(r, 0), "UNKNOWN") for r in rows]
        worst = max(states, key=lambda s: _HOST_SEVERITY.get(s, 0))
        # Map host states onto the services_summary slots so the hover/tooltip
        # can render counts the same way it does for host objects: UP=ok,
        # DOWN=critical, UNREACHABLE=unknown.
        summary = ServicesSummary(
            ok=sum(1 for s in states if s == "UP"),
            critical=sum(1 for s in states if s == "DOWN"),
            unknown=sum(1 for s in states if s == "UNREACHABLE"),
            pending=sum(1 for s in states if s == "PENDING"),
        )
        return ObjectState(object_id="", type="hostgroup", state=worst, services_summary=summary)

    async def get_servicegroup_states(self, group: str) -> ObjectState:
        exists_q = f"GET servicegroups\nColumns: name\nFilter: name = {_ls_escape(group)}\n"
        exists_rows = await self._query(exists_q)
        if not exists_rows:
            return ObjectState(object_id="", type="servicegroup", state="NOT_FOUND")
        query = f"GET services\nColumns: state\nFilter: groups >= {_ls_escape(group)}\n"
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="servicegroup", state="PENDING")
        states = [_SERVICE_STATE_MAP.get(_row_int(r, 0), "UNKNOWN") for r in rows]
        worst = max(states, key=lambda s: _SERVICE_SEVERITY.get(s, 0))
        summary = ServicesSummary(
            ok=sum(1 for s in states if s == "OK"),
            warning=sum(1 for s in states if s == "WARNING"),
            critical=sum(1 for s in states if s == "CRITICAL"),
            unknown=sum(1 for s in states if s == "UNKNOWN"),
            pending=sum(1 for s in states if s == "PENDING"),
        )
        return ObjectState(object_id="", type="servicegroup", state=worst, services_summary=summary)

    async def get_dyngroup_member_states(
        self, object_types: str, object_filter: str
    ) -> list[GroupMemberRow]:
        lql_filter = object_filter.replace("\\n", "\n")
        if not lql_filter.endswith("\n"):
            lql_filter += "\n"
        if object_types == "service":
            query = (
                "GET services\n"
                "Columns: host_name description state plugin_output acknowledged "
                "scheduled_downtime_depth notifications_enabled last_state_change\n"
                f"{lql_filter}"
            )
            rows = await self._query(query)
            svc_out: list[GroupMemberRow] = []
            for r in rows:
                host = _row_str(r, 0)
                svc = _row_str(r, 1)
                if not host or not svc:
                    continue
                svc_out.append(
                    GroupMemberRow(
                        host=host,
                        service=svc,
                        state=_SERVICE_STATE_MAP.get(_row_int(r, 2), "UNKNOWN"),
                        output=_row_str(r, 3).split("\n", 1)[0],
                        acknowledged=bool(_row_int(r, 4)),
                        in_downtime=_row_int(r, 5) > 0,
                        notifications_enabled=bool(_row_int(r, 6)),
                        last_state_change=_row_float(r, 7) or None,
                    )
                )
            return svc_out
        query = (
            "GET hosts\n"
            "Columns: name state plugin_output acknowledged "
            "scheduled_downtime_depth notifications_enabled last_state_change\n"
            f"{lql_filter}"
        )
        rows = await self._query(query)
        host_out: list[GroupMemberRow] = []
        for r in rows:
            name = _row_str(r, 0)
            if not name:
                continue
            host_out.append(
                GroupMemberRow(
                    host=name,
                    service="",
                    state=_HOST_STATE_MAP.get(_row_int(r, 1), "UNKNOWN"),
                    output=_row_str(r, 2).split("\n", 1)[0],
                    acknowledged=bool(_row_int(r, 3)),
                    in_downtime=_row_int(r, 4) > 0,
                    notifications_enabled=bool(_row_int(r, 5)),
                    last_state_change=_row_float(r, 6) or None,
                )
            )
        return host_out

    async def get_dyngroup_state(self, object_types: str, object_filter: str) -> ObjectState:
        # NagVis-style: feed the validated filter into GET hosts/services and
        # aggregate worst-of. normalize_object_filter at the schema layer has
        # already restricted this to safe Filter:/And:/Or: lines.
        lql_filter = object_filter.replace("\\n", "\n")
        if not lql_filter.endswith("\n"):
            lql_filter += "\n"
        if object_types == "service":
            rows = await self._query(f"GET services\nColumns: state\n{lql_filter}")
            if not rows:
                return ObjectState(object_id="", type="dyngroup", state="PENDING")
            states = [_SERVICE_STATE_MAP.get(_row_int(r, 0), "UNKNOWN") for r in rows]
            worst = max(states, key=lambda s: _SERVICE_SEVERITY.get(s, 0))
            summary = ServicesSummary(
                ok=sum(1 for s in states if s == "OK"),
                warning=sum(1 for s in states if s == "WARNING"),
                critical=sum(1 for s in states if s == "CRITICAL"),
                unknown=sum(1 for s in states if s == "UNKNOWN"),
                pending=sum(1 for s in states if s == "PENDING"),
            )
            return ObjectState(object_id="", type="dyngroup", state=worst, services_summary=summary)
        rows = await self._query(f"GET hosts\nColumns: state\n{lql_filter}")
        if not rows:
            return ObjectState(object_id="", type="dyngroup", state="PENDING")
        states = [_HOST_STATE_MAP.get(_row_int(r, 0), "UNKNOWN") for r in rows]
        worst = max(states, key=lambda s: _HOST_SEVERITY.get(s, 0))
        summary = ServicesSummary(
            ok=sum(1 for s in states if s == "UP"),
            critical=sum(1 for s in states if s == "DOWN"),
            unknown=sum(1 for s in states if s == "UNREACHABLE"),
            pending=sum(1 for s in states if s == "PENDING"),
        )
        return ObjectState(object_id="", type="dyngroup", state=worst, services_summary=summary)

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
            # Federated multisite tags rows with site_id; single-site connections
            # don't, but consumers (FlowBoard site umbrella, drawer aggregation)
            # still want a stable identifier to group hosts under.
            row["site_id"] = site_id if site_id is not None else (settings.checkmk_site or "local")
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

    async def get_group_member_states(
        self, group_type: str, group_name: str
    ) -> list[GroupMemberRow]:
        """Fetch per-member state details for a host- or service-group.

        Single Livestatus query per group — the drawer renders the triage
        list straight from the result without a follow-up round-trip. Plugin
        output is the first non-empty line so a one-line preview shows next
        to each member without bloating the response.
        """
        if group_type == "hostgroup":
            query = (
                "GET hosts\n"
                "Columns: name state plugin_output acknowledged "
                "scheduled_downtime_depth notifications_enabled last_state_change\n"
                f"Filter: groups >= {_ls_escape(group_name)}\n"
            )
            rows = await self._query(query)
            out: list[GroupMemberRow] = []
            for r in rows:
                name = _row_str(r, 0)
                if not name:
                    continue
                out.append(
                    GroupMemberRow(
                        host=name,
                        service="",
                        state=_HOST_STATE_MAP.get(_row_int(r, 1), "UNKNOWN"),
                        output=_row_str(r, 2).split("\n", 1)[0],
                        acknowledged=bool(_row_int(r, 3)),
                        in_downtime=_row_int(r, 4) > 0,
                        notifications_enabled=bool(_row_int(r, 5)),
                        last_state_change=_row_float(r, 6) or None,
                    )
                )
            return out
        if group_type == "servicegroup":
            query = (
                "GET services\n"
                "Columns: host_name description state plugin_output acknowledged "
                "scheduled_downtime_depth notifications_enabled last_state_change\n"
                f"Filter: groups >= {_ls_escape(group_name)}\n"
            )
            rows = await self._query(query)
            out_s: list[GroupMemberRow] = []
            for r in rows:
                host = _row_str(r, 0)
                svc = _row_str(r, 1)
                if not host or not svc:
                    continue
                out_s.append(
                    GroupMemberRow(
                        host=host,
                        service=svc,
                        state=_SERVICE_STATE_MAP.get(_row_int(r, 2), "UNKNOWN"),
                        output=_row_str(r, 3).split("\n", 1)[0],
                        acknowledged=bool(_row_int(r, 4)),
                        in_downtime=_row_int(r, 5) > 0,
                        notifications_enabled=bool(_row_int(r, 6)),
                        last_state_change=_row_float(r, 7) or None,
                    )
                )
            return out_s
        return []

    async def get_hosts_with_geo(
        self, *, group_type: str | None = None, group_name: str | None = None
    ) -> list[GeoHost]:
        """Return every host whose monitoring data carries geo-coordinates.

        Reads the same label/custom-variable conventions as ``get_host_geo``:
        orbvis_lat / orbvis_lng labels first, legacy LAT / LONG custom vars as
        fallback. Hosts without geo data are filtered out so the worldmap
        automap source receives a clean list.
        """
        filt = ""
        if group_type == "hostgroup" and group_name:
            filt = f"Filter: groups >= {_ls_escape(group_name)}\n"
        elif group_type == "servicegroup" and group_name:
            # servicegroup membership lives on the services table; resolve to
            # the unique host names that own a member service.
            svc_rows = await self._query(
                f"GET services\nColumns: host_name\nFilter: groups >= {_ls_escape(group_name)}\n"
            )
            host_names = {_row_str(r, 0) for r in svc_rows if _row_str(r, 0)}
            if not host_names:
                return []
            host_filters = "".join(f"Filter: name = {_ls_escape(h)}\n" for h in host_names)
            filt = f"{host_filters}Or: {len(host_names)}\n"

        query = (
            "GET hosts\n"
            "Columns: name alias labels custom_variable_names custom_variable_values\n" + filt
        )
        rows = await self._query(query)
        out: list[GeoHost] = []
        for r in rows:
            name = _row_str(r, 0)
            if not name:
                continue
            alias = _row_str(r, 1) or name
            labels = _row_dict(r, 2)
            lat_raw: object | None = labels.get("orbvis_lat")
            lng_raw: object | None = labels.get("orbvis_lng")
            if lat_raw is None or lng_raw is None:
                names = _row_list(r, 3)
                values = _row_list(r, 4)
                cv = {str(n): v for n, v in zip(names, values, strict=False) if isinstance(n, str)}
                lat_raw = cv.get("LAT")
                lng_raw = cv.get("LONG")
            if lat_raw is None or lng_raw is None:
                continue
            try:
                out.append(
                    GeoHost(
                        name=name, alias=alias, lat=float(str(lat_raw)), lng=float(str(lng_raw))
                    )
                )
            except (TypeError, ValueError):
                continue
        return out

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
        # 2.5 removed the GET flavour of /domain-types/service/collections/all
        # (deprecated since 2.4); the POST endpoint takes host_name and
        # columns in the JSON body.
        url = base_url + "/api/1.0/domain-types/service/collections/all"
        try:
            async with httpx.AsyncClient(verify=self._verify_ssl, timeout=self._timeout) as client:
                resp = await client.post(
                    url,
                    headers={
                        "Authorization": auth_header,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json={"host_name": host, "columns": ["metrics", "description"]},
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
        # ``_query_raw`` now raises ``LivestatusProtocolError`` for empty /
        # unparseable wire responses, so a missing exception here genuinely
        # means the connection talked Livestatus end-to-end. The query
        # itself can return zero rows for an empty cluster — that's fine.
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
        from cmk.livestatus_client import LivestatusResponse

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
        tagged = await self._query_with_site(
            f"GET hosts\n"
            f"Columns: name {state_col} plugin_output perf_data acknowledged "
            f"scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"{filters}"
        )
        fallback = settings.checkmk_site or "local"
        return dict(_parse_host_state_row(r, site_id=sid or fallback) for sid, r in tagged)

    async def get_all_hosts_states(self, only_hard: bool = False) -> dict[str, ObjectState]:
        state_col = "last_hard_state" if only_hard else "state"
        tagged = await self._query_with_site(
            f"GET hosts\n"
            f"Columns: name {state_col} plugin_output perf_data acknowledged "
            f"scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
        )
        fallback = settings.checkmk_site or "local"
        return dict(_parse_host_state_row(r, site_id=sid or fallback) for sid, r in tagged)

    async def get_all_services_states(
        self, only_hard: bool = False
    ) -> dict[tuple[str, str], ObjectState]:
        state_col = "last_hard_state" if only_hard else "state"
        tagged = await self._query_with_site(
            f"GET services\n"
            f"Columns: host_name description {state_col} plugin_output perf_data "
            f"acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
        )
        fallback = settings.checkmk_site or "local"
        return dict(_parse_service_state_row(r, site_id=sid or fallback) for sid, r in tagged)

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
        tagged = await self._query_with_site(
            f"GET services\n"
            f"Columns: host_name description {state_col} plugin_output perf_data "
            f"acknowledged scheduled_downtime_depth {_SVC_EXTRA_COLS}\n"
            f"{filter_lines}"
        )
        fallback = settings.checkmk_site or "local"
        return dict(_parse_service_state_row(r, site_id=sid or fallback) for sid, r in tagged)

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
        chunk_size = settings.flow_board_bulk_service_chunk_size

        async def _query_chunk(hosts: list[str]) -> list[LivestatusRow]:
            filters = "".join(f"Filter: host_name = {_ls_escape(h)}\n" for h in hosts)
            if len(hosts) > 1:
                filters += f"Or: {len(hosts)}\n"
            return await self._query(
                "GET services\n"
                "Columns: host_name description state plugin_output "
                "acknowledged scheduled_downtime_depth notifications_enabled "
                "last_state_change last_check next_check\n" + filters
            )

        async def _bounded_query_chunk(hosts: list[str]) -> list[LivestatusRow]:
            async with self._bulk_chunk_semaphore:
                return await _query_chunk(hosts)

        # Split top-K into smaller parallel queries: one slow host stalls only
        # its own chunk. The semaphore caps in-flight chunks so high host counts
        # (e.g. 500-host top-K → 100 chunks) don't exhaust the livestatus
        # listen backlog. ``return_exceptions=True`` lets a single failed chunk
        # degrade gracefully (those hosts get an empty service list) instead of
        # killing the whole topology broadcast.
        chunks = [hostnames[i : i + chunk_size] for i in range(0, len(hostnames), chunk_size)]
        chunk_results = await asyncio.gather(
            *(_bounded_query_chunk(c) for c in chunks),
            return_exceptions=True,
        )

        results: dict[str, list[ServiceRow]] = {h: [] for h in hostnames}
        for rows in chunk_results:
            if isinstance(rows, BaseException):
                logger.warning("services chunk failed", exc_info=rows)
                continue
            for r in rows:
                results[_row_str(r, 0)].append(
                    ServiceRow(
                        name=_row_str(r, 1),
                        state=_SERVICE_STATE_MAP.get(_row_int(r, 2), "UNKNOWN"),
                        output=_row_str(r, 3),
                        acknowledged=bool(_row_int(r, 4)),
                        in_downtime=_row_int(r, 5) > 0,
                        notifications_enabled=bool(_row_int(r, 6)),
                        last_state_change=_row_float_or_none(r, 7),
                        last_check=_row_float_or_none(r, 8),
                        next_check=_row_float_or_none(r, 9),
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

    async def send_command(self, command: str, site_id: str | None = None) -> None:
        """Send a Livestatus external command to the configured site.

        ``command`` is the bare command body — e.g.
        ``"SCHEDULE_FORCED_SVC_CHECK;hostname;service;1700000000"`` — *without*
        the ``COMMAND [<timestamp>]`` framing. SingleSiteConnection.command
        and the federated MultiSiteConnection both add the ``COMMAND``
        prefix and timestamp themselves, so the bare body is the right
        contract.

        The Checkmk REST API does not expose host/service action verbs like
        ``reschedule-active-checks`` or ``disable-notifications`` (no version
        between 2.3 and 2.6 carries these endpoints), so anything that the
        DetailDrawer would normally call out to CMK REST for has to be
        relayed through livestatus' command pipe instead. Federated sites
        get the request routed via ``MultiSiteConnection.command``;
        single-socket connections write the line straight to the unix
        socket — no response is expected from a COMMAND, livestatus just
        queues it.
        """
        if self._sites:
            await asyncio.to_thread(self._run_multisite_command, command, site_id)
            return
        # Single-socket path: livestatus expects ``COMMAND [<ts>] <body>``.
        ts = int(time.time())
        full = f"COMMAND [{ts}] {command}"
        _reader, writer = await self._open_connection()
        try:
            writer.write((full + "\n").encode())
            await writer.drain()
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    def _run_multisite_command(self, command_body: str, site_id: str | None) -> None:
        """Send a Livestatus external command via MultiSiteConnection.

        Parallel to ``_run_multisite_sync`` but uses ``mc.command()`` —
        which adds the ``COMMAND [<timestamp>]`` framing internally, so
        we pass the bare command body. Sync; must run in a worker thread.
        """
        from cmk.livestatus_client import MultiSiteConnection, SiteConfigurations

        if not self._sites:
            return
        with self._mc_lock:
            current_mtime = _cmk_sites.sites_mk_mtime()
            if self._mc is None or current_mtime != self._mc_mtime:
                self._sites = _cmk_sites.load_sites()
                if not self._sites:
                    self._mc = None
                    self._mc_mtime = current_mtime
                    self._mc_dead = set()
                    return
                self._mc = MultiSiteConnection(sites=SiteConfigurations(self._sites))
                self._mc.set_prepend_site(True)
                self._mc_mtime = current_mtime
                self._mc_dead = set()
            # `MultiSiteConnection.command` requires a real configured
            # sitename — "local" only matches when the literal site is
            # named "local". In OMD the site name comes from $OMD_SITE
            # (RTEST25C etc.).
            target = site_id or settings.checkmk_site or "local"
            self._mc.command(command_body, target)

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

    def _build_ssl_context(self) -> ssl.SSLContext:
        """Build the SSLContext for TLS-wrapped Livestatus TCP connections.

        ``tls_verify`` flips both peer-cert validation and hostname matching:
        OMD's stunnel ships a self-signed per-site CA, so verify-on without
        a manually pre-trusted CA bundle would always fail. The default
        (off) follows the same pragmatic choice as ``icinga2_verify_ssl``.
        """
        ctx = ssl.create_default_context()
        if not self._tls_verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        return ctx

    async def _open_connection(
        self,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        """Open a TCP/Unix connection to livestatus, retrying on transient EAGAIN.

        High-fanout flow-board fetches (top-K with hundreds of hosts) burst many
        concurrent connects which can momentarily exhaust the unix-socket
        listen backlog. The kernel surfaces this as
        ``BlockingIOError: [Errno 11] Resource temporarily unavailable``.
        Short jittered backoff resolves it without hammering further; the cap
        keeps total latency bounded so a genuinely-down livestatus still fails
        the per-query timeout.
        """
        attempts = 4
        for i in range(attempts):
            try:
                if self._host:
                    return await asyncio.wait_for(
                        asyncio.open_connection(
                            self._host,
                            self._port,
                            ssl=self._ssl_ctx,
                            server_hostname=self._host if self._ssl_ctx else None,
                        ),
                        timeout=self._timeout,
                    )
                return await asyncio.wait_for(
                    asyncio.open_unix_connection(self._socket_path),
                    timeout=self._timeout,
                )
            except (BlockingIOError, ConnectionResetError, ConnectionRefusedError):
                if i == attempts - 1:
                    raise
                await asyncio.sleep(0.05 + random.random() * 0.1)
        raise AssertionError("unreachable")  # pragma: no cover

    async def _query_raw(self, query: str) -> list[LivestatusRow]:
        """Send a Livestatus query and return parsed rows."""
        lql = query.rstrip("\n") + "\nOutputFormat: json\nResponseHeader: fixed16\n"
        auth_user = _auth_user_ctx.get()
        if auth_user:
            lql += f"AuthUser: {auth_user}\n"
        lql += "\n"

        reader, writer = await self._open_connection()

        # asyncio.shield() prevents a second CancelledError from aborting
        # wait_closed() when the caller cancels this coroutine mid-cleanup.
        try:
            writer.write(lql.encode())
            await writer.drain()

            # Fixed-16 response header: "200          42\n". An empty read
            # means the peer closed before sending any response — typically
            # a TLS-wrapped listener rejecting our plain LQL. Surface as a
            # protocol error so callers don't mistake it for "0 rows".
            header = await asyncio.wait_for(reader.read(16), timeout=self._timeout)
            if not header:
                raise LivestatusProtocolError(
                    "Livestatus closed connection before sending a response header "
                    "(TLS mismatch or remote shutdown?)"
                )
            status: int
            length: int
            try:
                status = int(header[:3])
                length = int(header[4:15].strip())
            except ValueError as exc:
                # Garbage in the first 16 bytes is the standard symptom of a
                # plain-TCP probe against a TLS-wrapped listener.
                raise LivestatusProtocolError(
                    f"Livestatus returned unparseable response header {header!r}"
                ) from exc

            body = b""
            while len(body) < length:
                chunk = await asyncio.wait_for(
                    reader.read(length - len(body)), timeout=self._timeout
                )
                if not chunk:
                    break
                body += chunk

            if status != 200:
                # Body carries the human-readable error from livestatus
                # (bad filter, unknown column, …). Surface it instead of
                # silently returning [] so the caller sees the cause.
                raise LivestatusProtocolError(
                    f"Livestatus error {status}: {body.decode(errors='replace')}"
                )

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
