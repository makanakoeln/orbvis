"""Icinga2 REST API monitoring backend."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.backends.base import BackendBase
from app.schemas.state import ObjectState

logger = logging.getLogger(__name__)

# Icinga2 host state integers → OrbVis strings
_HOST_STATE_MAP = {0: "UP", 1: "DOWN", 2: "UNREACHABLE"}
# Icinga2 service state integers → OrbVis strings
_SVC_STATE_MAP = {0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN"}

# Worst-state aggregation order (higher index = worse)
_HOST_SEVERITY = {"UP": 0, "PENDING": 0, "UNREACHABLE": 1, "DOWN": 2}
_SVC_SEVERITY = {"OK": 0, "PENDING": 0, "UNKNOWN": 1, "WARNING": 2, "CRITICAL": 3}


def _worst_host(*states: str) -> str:
    return max(states, key=lambda s: _HOST_SEVERITY.get(s, 0))


def _worst_svc(*states: str) -> str:
    return max(states, key=lambda s: _SVC_SEVERITY.get(s, 0))


class Icinga2Backend(BackendBase):
    """Query monitoring state from an Icinga2 instance via its REST API."""

    backend_id = "icinga2"

    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        timeout: float = 10.0,
        verify_ssl: bool = True,
    ) -> None:
        self._base = url.rstrip("/") + "/v1"
        self._auth = (username, password)
        self._timeout = timeout
        self._verify = verify_ssl

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            auth=self._auth,
            verify=self._verify,
            timeout=self._timeout,
            headers={"Accept": "application/json"},
        )

    async def _get_results(self, path: str, params: dict[str, Any] | None = None) -> list[dict]:
        async with self._client() as client:
            resp = await client.get(f"{self._base}/{path.lstrip('/')}", params=params)
            resp.raise_for_status()
            return resp.json().get("results", [])

    # ------------------------------------------------------------------
    # BackendBase implementation
    # ------------------------------------------------------------------

    async def get_host_state(self, hostname: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/hosts",
                params={"filter": f'host.name=="{hostname}"'},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_host_state(%s) failed: %s", hostname, exc)
            return ObjectState(object_id="", type="host", state="UNREACHABLE", stale=True)

        if not results:
            return ObjectState(object_id="", type="host", state="UNREACHABLE",
                               output=f"Host '{hostname}' not found in Icinga2")

        attrs = results[0].get("attrs", {})
        state_int = int(attrs.get("state", 1))
        return ObjectState(
            object_id="",
            type="host",
            state=_HOST_STATE_MAP.get(state_int, "UNREACHABLE"),
            output=attrs.get("last_check_result", {}).get("output", ""),
            acknowledged=bool(attrs.get("acknowledgement", 0)),
            in_downtime=bool(attrs.get("downtime_depth", 0)),
        )

    async def get_service_state(self, host: str, service: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/services",
                params={"filter": f'service.host_name=="{host}" && service.name=="{service}"'},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_service_state(%s/%s) failed: %s", host, service, exc)
            return ObjectState(object_id="", type="service", state="UNKNOWN", stale=True)

        if not results:
            return ObjectState(object_id="", type="service", state="UNKNOWN",
                               output=f"Service '{service}' on '{host}' not found in Icinga2")

        attrs = results[0].get("attrs", {})
        state_int = int(attrs.get("state", 3))
        check_result = attrs.get("last_check_result", {})
        perf_data = " ".join(check_result.get("performance_data", []))
        return ObjectState(
            object_id="",
            type="service",
            state=_SVC_STATE_MAP.get(state_int, "UNKNOWN"),
            output=check_result.get("output", ""),
            perf_data=perf_data,
            acknowledged=bool(attrs.get("acknowledgement", 0)),
            in_downtime=bool(attrs.get("downtime_depth", 0)),
        )

    async def get_hostgroup_states(self, group: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/hosts",
                params={"filter": f'"{group}" in host.groups'},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_hostgroup_states(%s) failed: %s", group, exc)
            return ObjectState(object_id="", type="hostgroup", state="UNREACHABLE", stale=True)

        if not results:
            return ObjectState(object_id="", type="hostgroup", state="PENDING",
                               output=f"Hostgroup '{group}' has no members")

        states = [
            _HOST_STATE_MAP.get(int(r.get("attrs", {}).get("state", 0)), "UP")
            for r in results
        ]
        worst = _worst_host(*states)
        return ObjectState(object_id="", type="hostgroup", state=worst,
                           output=f"{len(results)} hosts, worst: {worst}")

    async def get_servicegroup_states(self, group: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/services",
                params={"filter": f'"{group}" in service.groups'},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_servicegroup_states(%s) failed: %s", group, exc)
            return ObjectState(object_id="", type="servicegroup", state="UNKNOWN", stale=True)

        if not results:
            return ObjectState(object_id="", type="servicegroup", state="PENDING",
                               output=f"Servicegroup '{group}' has no members")

        states = [
            _SVC_STATE_MAP.get(int(r.get("attrs", {}).get("state", 0)), "OK")
            for r in results
        ]
        worst = _worst_svc(*states)
        return ObjectState(object_id="", type="servicegroup", state=worst,
                           output=f"{len(results)} services, worst: {worst}")

    async def get_objects(self, obj_type: str) -> list[str]:
        try:
            if obj_type == "host":
                results = await self._get_results("objects/hosts", params={"attrs": "name"})
                return [r["attrs"]["name"] for r in results]
            if obj_type == "service":
                results = await self._get_results(
                    "objects/services", params={"attrs": "host_name,name"}
                )
                return [f'{r["attrs"]["host_name"]};{r["attrs"]["name"]}' for r in results]
        except Exception as exc:
            logger.warning("Icinga2 get_objects(%s) failed: %s", obj_type, exc)
        return []

    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        try:
            if group_type == "all_hosts":
                results = await self._get_results("objects/hosts", params={"attrs": "name"})
                return [r["attrs"]["name"] for r in results]
            if group_type == "all_services":
                results = await self._get_results(
                    "objects/services", params={"attrs": "host_name,name"}
                )
                return [f'{r["attrs"]["host_name"]};{r["attrs"]["name"]}' for r in results]
            if group_type == "hostgroup":
                results = await self._get_results(
                    "objects/hosts",
                    params={"filter": f'"{group_name}" in host.groups', "attrs": "name"},
                )
                return [r["attrs"]["name"] for r in results]
            if group_type == "servicegroup":
                results = await self._get_results(
                    "objects/services",
                    params={
                        "filter": f'"{group_name}" in service.groups',
                        "attrs": "host_name,name",
                    },
                )
                return [f'{r["attrs"]["host_name"]};{r["attrs"]["name"]}' for r in results]
        except Exception as exc:
            logger.warning("Icinga2 get_group_members(%s/%s) failed: %s", group_type, group_name, exc)
        return []

    async def get_topology(self) -> list[dict]:
        try:
            results = await self._get_results(
                "objects/hosts",
                params={"attrs": "name,state,last_check_result,vars"},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_topology() failed: %s", exc)
            return []

        nodes = []
        for r in results:
            attrs = r.get("attrs", {})
            state_int = int(attrs.get("state", 0))
            output = attrs.get("last_check_result", {}).get("output", "")
            parents = attrs.get("vars", {}).get("parents", [])
            if isinstance(parents, str):
                parents = [parents]
            nodes.append({
                "name": attrs["name"],
                "parents": parents,
                "state": _HOST_STATE_MAP.get(state_int, "UP"),
                "output": output,
            })
        return nodes

    async def get_host_services(self, hostname: str) -> list[dict]:
        try:
            results = await self._get_results(
                "objects/services",
                params={
                    "filter": f'service.host_name=="{hostname}"',
                    "attrs": "name,state,last_check_result",
                },
            )
        except Exception as exc:
            logger.warning("Icinga2 get_host_services(%s) failed: %s", hostname, exc)
            return []
        out = []
        for r in results:
            attrs = r.get("attrs", {})
            state_int = int(attrs.get("state", 3))
            output = attrs.get("last_check_result", {}).get("output", "")
            out.append({
                "name": attrs.get("name", ""),
                "state": _SVC_STATE_MAP.get(state_int, "UNKNOWN"),
                "output": output,
            })
        return out

    async def is_available(self) -> bool:
        try:
            async with self._client() as client:
                resp = await client.get(self._base)
                return resp.status_code < 500
        except Exception:
            return False
