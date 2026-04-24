"""MK Livestatus backend via asyncio Unix/TCP socket."""

from __future__ import annotations

import asyncio
import importlib
import json as _json
import logging
import pkgutil
import re as _re
import types
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

import httpx

from app.backends.base import BackendBase, GraphGroup, MetricHistoryResult, ServiceRow, TopologyRow
from app.core.config import settings
from app.integrations import checkmk as _cmk_integration
from app.schemas.state import ObjectState

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


class _ExtraFields(TypedDict, total=False):
    """Tail columns of a Livestatus host/service row — mapped onto ObjectState."""

    address: str
    last_check: float | None
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

# Aggregate: worst state wins (higher = worse)
_HOST_SEVERITY = {"UP": 0, "UNREACHABLE": 1, "DOWN": 2, "PENDING": -1}
_SERVICE_SEVERITY = {"OK": 0, "UNKNOWN": 1, "WARNING": 2, "CRITICAL": 3, "PENDING": -1}
_STATE_TYPE_MAP = {0: "SOFT", 1: "HARD"}

_HOST_EXTRA_COLS = (
    "address last_check state_type current_attempt max_check_attempts last_state_change"
    " notifications_enabled active_checks_enabled"
)
_SVC_EXTRA_COLS = (
    "last_check state_type current_attempt max_check_attempts last_state_change"
    " notifications_enabled active_checks_enabled"
)


def _apply_extra(
    state: ObjectState, row: LivestatusRow, offset: int = 5, *, include_address: bool = False
) -> ObjectState:
    """Fill the tail ObjectState fields (address, timings, attempt counters) from the row."""
    col = offset
    if include_address:
        state.address = _row_str(row, col)
        col += 1
    lc = _row_float(row, col)
    lsc = _row_float(row, col + 4)
    state.last_check = lc if lc > 0 else None
    state.state_type = _STATE_TYPE_MAP.get(_row_int(row, col + 1, default=1), "HARD")
    state.current_attempt = _row_int(row, col + 2)
    state.max_attempts = _row_int(row, col + 3)
    state.last_state_change = lsc if lsc > 0 else None
    state.notifications_enabled = _row_bool(row, col + 5, default=True)
    state.active_checks_enabled = _row_bool(row, col + 6, default=True)
    return state


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


class LivestatusBackend(BackendBase):
    """Connects to a Livestatus socket (Unix or TCP) and queries host/service states."""

    backend_id: str = "live_1"

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
        self._semaphore = asyncio.Semaphore(settings.backend_max_connections)

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
        rows = await self._query("GET hosts\nColumns: name parents state plugin_output\n")
        result: list[TopologyRow] = []
        for r in rows:
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
            result.append(
                TopologyRow(
                    name=name,
                    parents=parents,
                    state=_HOST_STATE_MAP.get(_row_int(r, 2), "UNKNOWN"),
                    output=_row_str(r, 3),
                )
            )
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
            logger.info(
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
        # Columns: [0]=name [1]=state [2]=output [3]=perf_data [4]=ack [5]=downtime [6..]=extra
        results: dict[str, ObjectState] = {}
        for r in rows:
            name = _row_str(r, 0)
            state = ObjectState(
                object_id="",
                type="host",
                state=_HOST_STATE_MAP.get(_row_int(r, 1), "UNKNOWN"),
                output=_row_str(r, 2),
                perf_data=_row_str(r, 3),
                acknowledged=_row_bool(r, 4, default=False),
                in_downtime=_row_int(r, 5) > 0,
            )
            results[name] = _apply_extra(state, r, offset=6, include_address=True)
        return results

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
        # Columns: [0]=host_name [1]=description [2]=state [3]=output [4]=perf_data
        #          [5]=ack [6]=downtime [7..]=extra
        results: dict[tuple[str, str], ObjectState] = {}
        for r in rows:
            key = (_row_str(r, 0), _row_str(r, 1))
            state = ObjectState(
                object_id="",
                type="service",
                state=_SERVICE_STATE_MAP.get(_row_int(r, 2), "UNKNOWN"),
                output=_row_str(r, 3),
                perf_data=_row_str(r, 4),
                acknowledged=_row_bool(r, 5, default=False),
                in_downtime=_row_int(r, 6) > 0,
            )
            results[key] = _apply_extra(state, r, offset=7)
        return results

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
        """Acquire connection slot and run query with an overall timeout."""
        async with self._semaphore:
            return await asyncio.wait_for(
                self._query_raw(query),
                timeout=settings.backend_query_timeout,
            )

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
