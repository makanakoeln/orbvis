"""Icinga2 REST API monitoring connection."""

from __future__ import annotations

import logging

import httpx

from app.connections.base import ConnectionBase, ServiceRow, TopologyRow
from app.schemas.state import ObjectState

# HTTP-Query-Parameter: Icinga2 akzeptiert str/int/float/bool — httpx serialisiert selbst
IcingaParams = dict[str, str | int | float | bool | None]
# Rohes Icinga2-API-Result-Objekt (heterogene JSON-Struktur, keys dynamisch)
IcingaObject = dict[str, object]

logger = logging.getLogger(__name__)


def _iq(value: str) -> str:
    """Escape a value for use inside an Icinga2 filter string literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


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


def _icinga_dict(obj: IcingaObject, key: str) -> IcingaObject:
    """Type-safe nested dict access for Icinga2 API results."""
    val = obj.get(key, {})
    return val if isinstance(val, dict) else {}


def _icinga_str(obj: IcingaObject, key: str, *, default: str = "") -> str:
    val = obj.get(key, default)
    return val if isinstance(val, str) else default


def _icinga_int(obj: IcingaObject, key: str, *, default: int = 0) -> int:
    val = obj.get(key, default)
    if isinstance(val, bool):  # bool is a subclass of int; keep behavior explicit
        return int(val)
    if isinstance(val, int | float):
        return int(val)
    return default


def _icinga_float(obj: IcingaObject, key: str) -> float | None:
    val = obj.get(key, 0) or 0
    if isinstance(val, bool):
        return None
    if isinstance(val, int | float):
        return float(val) if val > 0 else None
    return None


def _apply_icinga_extra(state: ObjectState, attrs: IcingaObject) -> ObjectState:
    """Fill the check_attempt/state_type/timing fields of an ObjectState from Icinga2 attrs."""
    state.last_check = _icinga_float(attrs, "last_check")
    state.last_state_change = _icinga_float(attrs, "last_state_change")
    state.state_type = "HARD" if attrs.get("state_type", 1) else "SOFT"
    state.current_attempt = _icinga_int(attrs, "check_attempt", default=0)
    state.max_attempts = _icinga_int(attrs, "max_check_attempts", default=0)
    return state


class Icinga2Connection(ConnectionBase):
    """Query monitoring state from an Icinga2 instance via its REST API."""

    connection_id = "icinga2"

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

    async def _get_results(
        self, path: str, params: IcingaParams | None = None
    ) -> list[IcingaObject]:
        async with self._client() as client:
            resp = await client.get(f"{self._base}/{path.lstrip('/')}", params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return list(results) if results else []

    # ------------------------------------------------------------------
    # ConnectionBase implementation
    # ------------------------------------------------------------------

    async def get_host_state(self, hostname: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/hosts",
                params={"filter": f'host.name=="{_iq(hostname)}"'},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_host_state(%s) failed: %s", hostname, exc)
            return ObjectState(object_id="", type="host", state="UNREACHABLE", stale=True)

        if not results:
            return ObjectState(
                object_id="",
                type="host",
                state="UNREACHABLE",
                output=f"Host '{hostname}' not found in Icinga2",
            )

        attrs = _icinga_dict(results[0], "attrs")
        state_int = _icinga_int(attrs, "state", default=1)
        state = ObjectState(
            object_id="",
            type="host",
            state=_HOST_STATE_MAP.get(state_int, "UNREACHABLE"),
            output=_icinga_str(_icinga_dict(attrs, "last_check_result"), "output"),
            acknowledged=bool(_icinga_int(attrs, "acknowledgement", default=0)),
            in_downtime=bool(_icinga_int(attrs, "downtime_depth", default=0)),
            address=_icinga_str(attrs, "address"),
        )
        return _apply_icinga_extra(state, attrs)

    async def get_service_state(self, host: str, service: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/services",
                params={
                    "filter": f'service.host_name=="{_iq(host)}" && service.name=="{_iq(service)}"'
                },
            )
        except Exception as exc:
            logger.warning("Icinga2 get_service_state(%s/%s) failed: %s", host, service, exc)
            return ObjectState(object_id="", type="service", state="UNKNOWN", stale=True)

        if not results:
            return ObjectState(
                object_id="",
                type="service",
                state="UNKNOWN",
                output=f"Service '{service}' on '{host}' not found in Icinga2",
            )

        attrs = _icinga_dict(results[0], "attrs")
        state_int = _icinga_int(attrs, "state", default=3)
        check_result = _icinga_dict(attrs, "last_check_result")
        perf_data_raw = check_result.get("performance_data", [])
        perf_data = (
            " ".join(p for p in perf_data_raw if isinstance(p, str))
            if isinstance(perf_data_raw, list)
            else ""
        )
        state = ObjectState(
            object_id="",
            type="service",
            state=_SVC_STATE_MAP.get(state_int, "UNKNOWN"),
            output=_icinga_str(check_result, "output"),
            perf_data=perf_data,
            acknowledged=bool(_icinga_int(attrs, "acknowledgement", default=0)),
            in_downtime=bool(_icinga_int(attrs, "downtime_depth", default=0)),
        )
        return _apply_icinga_extra(state, attrs)

    async def get_hostgroup_states(self, group: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/hosts",
                params={"filter": f'"{_iq(group)}" in host.groups'},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_hostgroup_states(%s) failed: %s", group, exc)
            return ObjectState(object_id="", type="hostgroup", state="UNREACHABLE", stale=True)

        if not results:
            return ObjectState(
                object_id="",
                type="hostgroup",
                state="PENDING",
                output=f"Hostgroup '{group}' has no members",
            )

        states = [
            _HOST_STATE_MAP.get(_icinga_int(_icinga_dict(r, "attrs"), "state", default=0), "UP")
            for r in results
        ]
        worst = _worst_host(*states)
        return ObjectState(
            object_id="",
            type="hostgroup",
            state=worst,
            output=f"{len(results)} hosts, worst: {worst}",
        )

    async def get_servicegroup_states(self, group: str) -> ObjectState:
        try:
            results = await self._get_results(
                "objects/services",
                params={"filter": f'"{_iq(group)}" in service.groups'},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_servicegroup_states(%s) failed: %s", group, exc)
            return ObjectState(object_id="", type="servicegroup", state="UNKNOWN", stale=True)

        if not results:
            return ObjectState(
                object_id="",
                type="servicegroup",
                state="PENDING",
                output=f"Servicegroup '{group}' has no members",
            )

        states = [
            _SVC_STATE_MAP.get(_icinga_int(_icinga_dict(r, "attrs"), "state", default=0), "OK")
            for r in results
        ]
        worst = _worst_svc(*states)
        return ObjectState(
            object_id="",
            type="servicegroup",
            state=worst,
            output=f"{len(results)} services, worst: {worst}",
        )

    async def get_objects(self, obj_type: str, host: str | None = None) -> list[str]:
        try:
            if obj_type == "host":
                results = await self._get_results("objects/hosts", params={"attrs": "name"})
                return [_icinga_str(_icinga_dict(r, "attrs"), "name") for r in results]
            if obj_type == "service":
                params: IcingaParams = {"attrs": "host_name,name"}
                if host:
                    params["filter"] = f'service.host_name=="{_iq(host)}"'
                results = await self._get_results("objects/services", params=params)
                return [
                    f"{_icinga_str(_icinga_dict(r, 'attrs'), 'host_name')};"
                    f"{_icinga_str(_icinga_dict(r, 'attrs'), 'name')}"
                    for r in results
                ]
        except Exception as exc:
            logger.warning("Icinga2 get_objects(%s) failed: %s", obj_type, exc)
        return []

    async def get_group_members(self, group_type: str, group_name: str) -> list[str]:
        try:
            if group_type == "all_hosts":
                results = await self._get_results("objects/hosts", params={"attrs": "name"})
                return [_icinga_str(_icinga_dict(r, "attrs"), "name") for r in results]
            if group_type == "all_services":
                results = await self._get_results(
                    "objects/services", params={"attrs": "host_name,name"}
                )
                return [
                    f"{_icinga_str(_icinga_dict(r, 'attrs'), 'host_name')};"
                    f"{_icinga_str(_icinga_dict(r, 'attrs'), 'name')}"
                    for r in results
                ]
            if group_type == "hostgroup":
                results = await self._get_results(
                    "objects/hosts",
                    params={"filter": f'"{_iq(group_name)}" in host.groups', "attrs": "name"},
                )
                return [_icinga_str(_icinga_dict(r, "attrs"), "name") for r in results]
            if group_type == "servicegroup":
                results = await self._get_results(
                    "objects/services",
                    params={
                        "filter": f'"{_iq(group_name)}" in service.groups',
                        "attrs": "host_name,name",
                    },
                )
                return [
                    f"{_icinga_str(_icinga_dict(r, 'attrs'), 'host_name')};"
                    f"{_icinga_str(_icinga_dict(r, 'attrs'), 'name')}"
                    for r in results
                ]
        except Exception as exc:
            logger.warning(
                "Icinga2 get_group_members(%s/%s) failed: %s", group_type, group_name, exc
            )
        return []

    async def get_topology(self) -> list[TopologyRow]:
        try:
            results = await self._get_results(
                "objects/hosts",
                params={"attrs": "name,state,last_check_result,vars"},
            )
        except Exception as exc:
            logger.warning("Icinga2 get_topology() failed: %s", exc)
            return []

        nodes: list[TopologyRow] = []
        for r in results:
            attrs = _icinga_dict(r, "attrs")
            state_int = _icinga_int(attrs, "state", default=0)
            output = _icinga_str(_icinga_dict(attrs, "last_check_result"), "output", default="")
            parents_raw = _icinga_dict(attrs, "vars").get("parents", [])
            if isinstance(parents_raw, str):
                parents: list[str] = [parents_raw]
            elif isinstance(parents_raw, list):
                parents = [p for p in parents_raw if isinstance(p, str)]
            else:
                parents = []
            name_raw = attrs.get("name", "")
            nodes.append(
                TopologyRow(
                    name=name_raw if isinstance(name_raw, str) else "",
                    parents=parents,
                    state=_HOST_STATE_MAP.get(state_int, "UP"),
                    output=output,
                )
            )
        return nodes

    async def get_host_services(self, hostname: str, only_hard: bool = False) -> list[ServiceRow]:
        try:
            results = await self._get_results(
                "objects/services",
                params={
                    "filter": f'service.host_name=="{_iq(hostname)}"',
                    "attrs": "name,state,last_check_result",
                },
            )
        except Exception as exc:
            logger.warning("Icinga2 get_host_services(%s) failed: %s", hostname, exc)
            return []
        out: list[ServiceRow] = []
        for r in results:
            attrs = _icinga_dict(r, "attrs")
            state_int = _icinga_int(attrs, "state", default=3)
            output = _icinga_str(_icinga_dict(attrs, "last_check_result"), "output", default="")
            out.append(
                ServiceRow(
                    name=_icinga_str(attrs, "name", default=""),
                    state=_SVC_STATE_MAP.get(state_int, "UNKNOWN"),
                    output=output,
                )
            )
        return out

    async def is_available(self) -> bool:
        try:
            async with self._client() as client:
                resp = await client.get(self._base)
                return resp.status_code < 500
        except Exception:
            return False
