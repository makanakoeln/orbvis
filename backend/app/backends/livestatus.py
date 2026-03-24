"""MK Livestatus backend via asyncio Unix/TCP socket."""

from __future__ import annotations

import asyncio
import json as _json
import logging

from app.backends.base import BackendBase
from app.core.config import settings
from app.schemas.state import ObjectState

logger = logging.getLogger(__name__)


def _ls_escape(value: str) -> str:
    """Strip newline/carriage-return characters to prevent Livestatus query injection.

    LQL filter values are terminated by a newline; embedding one would allow injecting
    additional filter lines or commands into the query.
    """
    return value.replace("\r", "").replace("\n", "")


# Livestatus state code → string mapping
_HOST_STATE_MAP = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
_SERVICE_STATE_MAP = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}

# Aggregate: worst state wins (higher = worse)
_HOST_SEVERITY = {"UP": 0, "UNREACHABLE": 1, "DOWN": 2, "PENDING": -1}
_SERVICE_SEVERITY = {"OK": 0, "UNKNOWN": 1, "WARNING": 2, "CRITICAL": 3, "PENDING": -1}
_STATE_TYPE_MAP = {0: "SOFT", 1: "HARD"}

_HOST_EXTRA_COLS = "address last_check state_type current_attempt max_check_attempts last_state_change"
_SVC_EXTRA_COLS  = "last_check state_type current_attempt max_check_attempts last_state_change"


def _parse_extra(row: list, offset: int = 5, *, include_address: bool = False) -> dict:
    try:
        col = offset
        address = str(row[col]) if include_address and len(row) > col else ""
        if include_address:
            col += 1
        lc      = float(row[col])     if len(row) > col     else 0.0
        st      = int(row[col + 1])   if len(row) > col + 1 else 1
        attempt = int(row[col + 2])   if len(row) > col + 2 else 0
        max_att = int(row[col + 3])   if len(row) > col + 3 else 0
        lsc     = float(row[col + 4]) if len(row) > col + 4 else 0.0
    except (ValueError, TypeError):
        return {}
    result = dict(
        last_check=lc if lc > 0 else None,
        state_type=_STATE_TYPE_MAP.get(st, "HARD"),
        current_attempt=attempt,
        max_attempts=max_att,
        last_state_change=lsc if lsc > 0 else None,
    )
    if include_address:
        result["address"] = address
    return result


class LivestatusBackend(BackendBase):
    """Connects to a Livestatus socket (Unix or TCP) and queries host/service states."""

    backend_id: str = "live_1"

    def __init__(
        self,
        socket_path: str = "/var/run/nagios/rw/live",
        host: str | None = None,
        port: int = 6557,
        timeout: float = 10.0,
    ) -> None:
        self._socket_path = socket_path
        self._host = host
        self._port = port
        self._timeout = timeout
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
        query = (
            f"GET hosts\n"
            f"Columns: state\n"
            f"Filter: groups >= {_ls_escape(group)}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="hostgroup", state="PENDING")
        worst = max(
            (_HOST_STATE_MAP.get(int(r[0]), "UNKNOWN") for r in rows),
            key=lambda s: _HOST_SEVERITY.get(s, 0),
        )
        return ObjectState(object_id="", type="hostgroup", state=worst)

    async def get_servicegroup_states(self, group: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: state\n"
            f"Filter: groups >= {_ls_escape(group)}\n"
        )
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
            result.append({
                "name": r[0],
                "parents": parents,
                "state": _HOST_STATE_MAP.get(int(r[2]), "UNKNOWN") if len(r) > 2 else "UNKNOWN",
                "output": r[3] if len(r) > 3 else "",
            })
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
            cv = dict(zip(names, values))
            return float(cv["LAT"]), float(cv["LONG"])
        except (KeyError, TypeError, ValueError):
            return None

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

    async def get_hosts_services_batch(
        self, hostnames: list[str]
    ) -> dict[str, list[dict]]:
        if not hostnames:
            return {}
        filters = "".join(f"Filter: host_name = {_ls_escape(h)}\n" for h in hostnames)
        if len(hostnames) > 1:
            filters += f"Or: {len(hostnames)}\n"
        rows = await self._query(
            f"GET services\n"
            f"Columns: host_name description state plugin_output\n"
            f"{filters}"
        )
        results: dict[str, list[dict]] = {h: [] for h in hostnames}
        for r in rows:
            results[str(r[0])].append({
                "name": r[1],
                "state": _SERVICE_STATE_MAP.get(int(r[2]), "UNKNOWN"),
                "output": r[3],
            })
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
