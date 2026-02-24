"""MK Livestatus backend via asyncio Unix/TCP socket."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.backends.base import BackendBase
from app.schemas.state import ObjectState

logger = logging.getLogger(__name__)

# Livestatus state code → string mapping
_HOST_STATE_MAP = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
_SERVICE_STATE_MAP = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}

# Aggregate: worst state wins (higher = worse)
_HOST_SEVERITY = {"UP": 0, "UNREACHABLE": 1, "DOWN": 2, "PENDING": -1}
_SERVICE_SEVERITY = {"OK": 0, "UNKNOWN": 1, "WARNING": 2, "CRITICAL": 3, "PENDING": -1}


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

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_host_state(self, hostname: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: state plugin_output acknowledged scheduled_downtime_depth\n"
            f"Filter: name = {hostname}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="host", state="PENDING", stale=True)
        state_code, output, ack, downtime = rows[0]
        return ObjectState(
            object_id="",
            type="host",
            state=_HOST_STATE_MAP.get(int(state_code), "UNKNOWN"),
            output=output,
            acknowledged=bool(int(ack)),
            in_downtime=int(downtime) > 0,
        )

    async def get_service_state(self, host: str, service: str) -> ObjectState:
        query = (
            f"GET services\n"
            f"Columns: state plugin_output acknowledged scheduled_downtime_depth\n"
            f"Filter: host_name = {host}\n"
            f"Filter: description = {service}\n"
        )
        rows = await self._query(query)
        if not rows:
            return ObjectState(object_id="", type="service", state="PENDING", stale=True)
        state_code, output, ack, downtime = rows[0]
        return ObjectState(
            object_id="",
            type="service",
            state=_SERVICE_STATE_MAP.get(int(state_code), "UNKNOWN"),
            output=output,
            acknowledged=bool(int(ack)),
            in_downtime=int(downtime) > 0,
        )

    async def get_hostgroup_states(self, group: str) -> ObjectState:
        query = (
            f"GET hosts\n"
            f"Columns: state\n"
            f"Filter: groups >= {group}\n"
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
            f"Filter: groups >= {group}\n"
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

    async def is_available(self) -> bool:
        try:
            await self._query("GET hosts\nColumns: name\nLimit: 1\n")
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Low-level socket communication
    # ------------------------------------------------------------------

    async def _query(self, query: str) -> list[list[str]]:
        """Send a Livestatus query and return parsed rows."""
        lql = query.rstrip("\n") + "\nOutputFormat: csv\nResponseHeader: fixed16\n\n"

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
            status = int(header[:3])
            length = int(header[4:15].strip())

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
            return [line.split(";") for line in text.splitlines()]
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
