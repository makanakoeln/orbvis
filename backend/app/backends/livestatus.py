"""MK Livestatus backend via asyncio Unix/TCP socket."""

from __future__ import annotations

import asyncio
import importlib
import json as _json
import logging
import pkgutil
import re as _re
from datetime import UTC
from functools import lru_cache
from pathlib import Path

import httpx

from app.backends.base import BackendBase, MetricHistoryResult
from app.core.config import settings
from app.integrations import checkmk as _cmk_integration
from app.schemas.state import ObjectState

logger = logging.getLogger(__name__)


def _identity(x: str) -> str:
    return x


@lru_cache(maxsize=1)
def _load_cmk_metric_titles() -> dict[str, str]:
    """Discover metric titles from all ``cmk.plugins.*.graphing`` submodules.

    Returns an empty dict in non-CMK environments.
    """
    if not _cmk_integration.available:
        return {}

    try:
        import cmk.plugins as _cmk_plugins
        from cmk.graphing.v1 import metrics as _gm
    except ImportError:
        return {}

    titles: dict[str, str] = {}

    # Enumerate plugin directories directly: walk_packages does not recurse into
    # namespace packages without __init__.py (e.g. "collection"), so we iterate
    # subdirectories on disk and import each *.graphing package explicitly.
    plugin_dirs: set[Path] = set()
    for p in _cmk_plugins.__path__:
        try:
            plugin_dirs.update(d for d in Path(p).iterdir() if d.is_dir())
        except OSError:
            pass

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
                mod = importlib.import_module(submod_name)
            except Exception:
                continue
            for attr in dir(mod):
                if not attr.startswith("metric_"):
                    continue
                obj = getattr(mod, attr)
                if not isinstance(obj, _gm.Metric):
                    continue
                try:
                    titles[obj.name] = obj.title.localize(_identity)
                except Exception:
                    pass

    logger.debug("Loaded %d CMK metric titles", len(titles))
    return titles


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


def _rrd_metric_id(label: str) -> str:
    """Sanitize a perf_data metric label for use in a Livestatus rrddata column spec.

    CMC stores metrics with underscores in place of spaces and colons (matching the
    NagVis convention). The column name must not contain spaces or colons because those
    are delimiters in the LQL Columns header.
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
)
_SVC_EXTRA_COLS = "last_check state_type current_attempt max_check_attempts last_state_change"


def _parse_extra(row: list, offset: int = 5, *, include_address: bool = False) -> dict:
    try:
        col = offset
        address = str(row[col]) if include_address and len(row) > col else ""
        if include_address:
            col += 1
        lc = float(row[col]) if len(row) > col else 0.0
        st = int(row[col + 1]) if len(row) > col + 1 else 1
        attempt = int(row[col + 2]) if len(row) > col + 2 else 0
        max_att = int(row[col + 3]) if len(row) > col + 3 else 0
        lsc = float(row[col + 4]) if len(row) > col + 4 else 0.0
    except (ValueError, TypeError):
        return {}
    result = {
        "last_check": lc if lc > 0 else None,
        "state_type": _STATE_TYPE_MAP.get(st, "HARD"),
        "current_attempt": attempt,
        "max_attempts": max_att,
        "last_state_change": lsc if lsc > 0 else None,
    }
    if include_address:
        result["address"] = address
    return result


def _parse_metrics_from_perf(perf_data: str) -> list[dict]:
    """Parse perf_data string into [{label, unit}] for rrddata queries."""
    results = []
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
        r = rows[0]
        return ObjectState(
            object_id="",
            type="host",
            state=_HOST_STATE_MAP.get(int(r[0]), "UNKNOWN"),
            output=r[1],
            perf_data=r[2],
            acknowledged=bool(int(r[3])),
            in_downtime=int(r[4]) > 0,
            **_parse_extra(r, include_address=True),
        )

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
        r = rows[0]
        return ObjectState(
            object_id="",
            type="service",
            state=_SERVICE_STATE_MAP.get(int(r[0]), "UNKNOWN"),
            output=r[1],
            perf_data=r[2],
            acknowledged=bool(int(r[3])),
            in_downtime=int(r[4]) > 0,
            **_parse_extra(r),
        )

    async def get_host_hard_state(self, hostname: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: last_hard_state plugin_output perf_data acknowledged scheduled_downtime_depth {_HOST_EXTRA_COLS}\n"
            f"Filter: name = {_ls_escape(hostname)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="host", state="PENDING")
        r = rows[0]
        return ObjectState(
            object_id="",
            type="host",
            state=_HOST_STATE_MAP.get(int(r[0]), "UNKNOWN"),
            output=r[1],
            perf_data=r[2],
            acknowledged=bool(int(r[3])),
            in_downtime=int(r[4]) > 0,
            **_parse_extra(r, include_address=True),
        )

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
        r = rows[0]
        return ObjectState(
            object_id="",
            type="service",
            state=_SERVICE_STATE_MAP.get(int(r[0]), "UNKNOWN"),
            output=r[1],
            perf_data=r[2],
            acknowledged=bool(int(r[3])),
            in_downtime=int(r[4]) > 0,
            **_parse_extra(r),
        )

    async def get_hostgroup_states(self, group: str) -> ObjectState:
        query = f"GET hosts\nColumns: state\nFilter: groups >= {_ls_escape(group)}\n"
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="hostgroup", state="PENDING")
        worst = max(
            (_HOST_STATE_MAP.get(int(r[0]), "UNKNOWN") for r in rows),
            key=lambda s: _HOST_SEVERITY.get(s, 0),
        )
        return ObjectState(object_id="", type="hostgroup", state=worst)

    async def get_servicegroup_states(self, group: str) -> ObjectState:
        query = f"GET services\nColumns: state\nFilter: groups >= {_ls_escape(group)}\n"
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="servicegroup", state="PENDING")
        worst = max(
            (_SERVICE_STATE_MAP.get(int(r[0]), "UNKNOWN") for r in rows),
            key=lambda s: _SERVICE_SEVERITY.get(s, 0),
        )
        return ObjectState(object_id="", type="servicegroup", state=worst)

    async def get_objects(self, obj_type: str) -> list[str]:
        if obj_type == "host":
            rows = await self._query("GET hosts\nColumns: name\n")
            return [r[0] for r in rows]
        if obj_type == "service":
            rows = await self._query("GET services\nColumns: host_name description\n")
            return [f"{r[0]};{r[1]}" for r in rows]
        if obj_type == "hostgroup":
            rows = await self._query("GET hostgroups\nColumns: name\n")
            return [r[0] for r in rows]
        if obj_type == "servicegroup":
            rows = await self._query("GET servicegroups\nColumns: name\n")
            return [r[0] for r in rows]
        return []

    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        if group_type == "all_hosts":
            rows = await self._query("GET hosts\nColumns: name\n")
            return [r[0] for r in rows]
        if group_type == "all_services":
            rows = await self._query("GET services\nColumns: host_name description\n")
            return [f"{r[0]};{r[1]}" for r in rows]
        if group_type == "hostgroup":
            query = f"GET hosts\nColumns: name\nFilter: groups >= {_ls_escape(group_name)}\n"
            rows = await self._query(query)
            return [r[0] for r in rows]
        if group_type == "servicegroup":
            query = f"GET services\nColumns: host_name description\nFilter: groups >= {_ls_escape(group_name)}\n"
            rows = await self._query(query)
            return [f"{r[0]};{r[1]}" for r in rows]
        return []

    async def get_topology(self) -> list[dict]:
        rows = await self._query("GET hosts\nColumns: name parents state plugin_output\n")
        result = []
        for r in rows:
            if not r or not r[0]:
                continue
            raw_parents = r[1] if len(r) > 1 else []
            if isinstance(raw_parents, list):
                parents = [p for p in raw_parents if p]
            else:
                parents = [p.strip() for p in (raw_parents or "").split(",") if p.strip()]
            result.append(
                {
                    "name": r[0],
                    "parents": parents,
                    "state": _HOST_STATE_MAP.get(int(r[2]), "UNKNOWN") if len(r) > 2 else "UNKNOWN",
                    "output": r[3] if len(r) > 3 else "",
                }
            )
        return result

    async def get_host_services(self, hostname: str) -> list[dict]:
        rows = await self._query(
            "GET services\n"
            f"Filter: host_name = {_ls_escape(hostname)}\n"
            "Columns: description state plugin_output\n"
        )
        return [
            {
                "name": r[0],
                "state": _SERVICE_STATE_MAP.get(int(r[1]), "UNKNOWN"),
                "output": r[2],
            }
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
        labels: dict = r[0] if isinstance(r[0], dict) else {}
        try:
            return float(labels["orbvis_lat"]), float(labels["orbvis_lng"])
        except (KeyError, TypeError, ValueError):
            pass

        # 2. NagVis-compatible custom variables: LAT / LONG
        try:
            names: list = r[1] if isinstance(r[1], list) else []
            values: list = r[2] if isinstance(r[2], list) else []
            cv = dict(zip(names, values, strict=False))
            return float(cv["LAT"]), float(cv["LONG"])
        except (KeyError, TypeError, ValueError):
            return None

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
                        return ext.get("metrics", [])
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
                unit = m["unit"]
                points: list[tuple[float, float, str]] = []
                for j, v in enumerate(values):
                    if v is not None:
                        ts = actual_start + j * actual_step
                        points.append((ts, float(v), unit))
                if points:
                    label = m["label"]
                    series[label] = points
                    titles[label] = _cmk_metric_title(label)
            except (IndexError, TypeError, ValueError) as exc:
                logger.debug("rrddata: failed to parse metric %r: %s, raw=%r", m["label"], exc, rrd)
                continue

        logger.debug("rrddata: returning %d metrics for %r/%r", len(series), host, service)
        return MetricHistoryResult(series=series, titles=titles)

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
            name = str(r[0])
            results[name] = ObjectState(
                object_id="",
                type="host",
                state=_HOST_STATE_MAP.get(int(r[1]), "UNKNOWN"),
                output=r[2],
                perf_data=r[3],
                acknowledged=bool(int(r[4])),
                in_downtime=int(r[5]) > 0,
                **_parse_extra(r, offset=6, include_address=True),
            )
        for h in hostnames:
            if h not in results:
                results[h] = ObjectState(object_id="", type="host", state="PENDING")
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
            key = (str(r[0]), str(r[1]))
            results[key] = ObjectState(
                object_id="",
                type="service",
                state=_SERVICE_STATE_MAP.get(int(r[2]), "UNKNOWN"),
                output=r[3],
                perf_data=r[4],
                acknowledged=bool(int(r[5])),
                in_downtime=int(r[6]) > 0,
                **_parse_extra(r, offset=7),
            )
        for pair in pairs:
            if pair not in results:
                results[pair] = ObjectState(object_id="", type="service", state="PENDING")
        return results

    async def get_hosts_services_batch(self, hostnames: list[str]) -> dict[str, list[dict]]:
        if not hostnames:
            return {}
        filters = "".join(f"Filter: host_name = {_ls_escape(h)}\n" for h in hostnames)
        if len(hostnames) > 1:
            filters += f"Or: {len(hostnames)}\n"
        rows = await self._query(
            f"GET services\nColumns: host_name description state plugin_output\n{filters}"
        )
        results: dict[str, list[dict]] = {h: [] for h in hostnames}
        for r in rows:
            results[str(r[0])].append(
                {
                    "name": r[1],
                    "state": _SERVICE_STATE_MAP.get(int(r[2]), "UNKNOWN"),
                    "output": r[3],
                }
            )
        return results

    # ------------------------------------------------------------------
    # Low-level socket communication
    # ------------------------------------------------------------------

    async def _query(self, query: str) -> list[list]:
        """Acquire connection slot and run query with an overall timeout."""
        async with self._semaphore:
            return await asyncio.wait_for(
                self._query_raw(query),
                timeout=settings.backend_query_timeout,
            )

    async def _query_raw(self, query: str) -> list[list]:
        """Send a Livestatus query and return parsed rows."""
        lql = query.rstrip("\n") + "\nOutputFormat: json\nResponseHeader: fixed16\n\n"

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

        try:
            writer.write(lql.encode())
            await writer.drain()

            # Fixed-16 response header: "200          42\n"
            header = await asyncio.wait_for(reader.read(16), timeout=self._timeout)
            if not header:
                return []
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
            return _json.loads(text)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
