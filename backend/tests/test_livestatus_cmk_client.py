"""Single-site routing through cmk.livestatus_client (CMK mode only)."""

import sys
import types
from typing import ClassVar

import pytest

from app.connections import livestatus as ls_mod
from app.connections.livestatus import (
    LivestatusConnection,
    _cmk_livestatus_client_available,
)


class _FakeQuerySpecification:
    def __init__(self, table: str, columns: list[str], headers: str) -> None:
        self.table = table
        self.columns = columns
        self.headers = headers

    def __str__(self) -> str:
        query = f"GET {self.table}\n"
        if self.columns:
            query += f"Columns: {' '.join(self.columns)}\n"
        return query + self.headers


class _FakeQuery:
    def __init__(self, query: "str | _FakeQuerySpecification") -> None:
        self.wrapped = query

    def __str__(self) -> str:
        return str(self.wrapped)


class _FakeSingleSiteConnection:
    """Records constructor args, queries and commands instead of opening sockets."""

    instances: ClassVar[list["_FakeSingleSiteConnection"]] = []

    def __init__(
        self,
        socketurl: str,
        tls: bool = False,
        verify: bool = True,
        ca_file_path: str | None = None,
    ) -> None:
        self.socketurl = socketurl
        self.tls = tls
        self.verify = verify
        self.ca_file_path = ca_file_path
        self.timeout: int | None = None
        self.queries: list[tuple[str, str]] = []
        self.commands: list[str] = []
        self.rows: list[list[object]] = [["h1", 0], ["h2", 1]]
        self.disconnected = False
        _FakeSingleSiteConnection.instances.append(self)

    def set_timeout(self, timeout: int) -> None:
        self.timeout = timeout

    def query(self, lql: object, add_headers: str = "") -> list[list[object]]:
        self.queries.append((str(lql), add_headers))
        return self.rows

    def command(self, body: str) -> None:
        self.commands.append(body)

    def disconnect(self) -> None:
        self.disconnected = True


@pytest.fixture
def fake_cmk_client(monkeypatch):
    """Inject a fake ``cmk.livestatus_client`` module and reset the import cache."""
    _FakeSingleSiteConnection.instances = []
    cmk_pkg = types.ModuleType("cmk")
    client_mod = types.ModuleType("cmk.livestatus_client")
    client_mod.SingleSiteConnection = _FakeSingleSiteConnection  # type: ignore[attr-defined]
    client_mod.Query = _FakeQuery  # type: ignore[attr-defined]
    client_mod.QuerySpecification = _FakeQuerySpecification  # type: ignore[attr-defined]
    cmk_pkg.livestatus_client = client_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "cmk", cmk_pkg)
    monkeypatch.setitem(sys.modules, "cmk.livestatus_client", client_mod)
    _cmk_livestatus_client_available.cache_clear()
    yield client_mod
    _cmk_livestatus_client_available.cache_clear()


def test_standalone_keeps_native_path():
    conn = LivestatusConnection(socket_path="/dev/null")
    assert conn._use_cmk_client is False
    assert conn._ss_socketurl == "unix:/dev/null"


def test_socketurl_tcp():
    conn = LivestatusConnection(host="10.0.0.1", port=6557)
    assert conn._ss_socketurl == "tcp:10.0.0.1:6557"


def test_flag_set_in_cmk_mode(monkeypatch, fake_cmk_client, tmp_path):
    monkeypatch.setattr(ls_mod._cmk_integration, "available", True)
    monkeypatch.setattr("app.core.config.settings.checkmk_omd_root", str(tmp_path))
    conn = LivestatusConnection(socket_path="/dev/null")
    assert conn._use_cmk_client is True
    assert conn._ss_ca_file == str(tmp_path / "var" / "ssl" / "ca-certificates.crt")


def test_flag_off_without_cmk_integration(fake_cmk_client):
    """Importable client alone is not enough — OMD context is required."""
    conn = LivestatusConnection(socket_path="/dev/null")
    assert conn._use_cmk_client is False


@pytest.mark.asyncio
async def test_query_routes_through_cmk_client(fake_cmk_client):
    conn = LivestatusConnection(socket_path="/dev/null", timeout=7.0)
    conn._use_cmk_client = True
    rows = await conn._query_with_site("GET hosts\nColumns: name state\n")
    assert rows == [(None, ["h1", 0]), (None, ["h2", 1])]
    fake = _FakeSingleSiteConnection.instances[-1]
    assert fake.socketurl == "unix:/dev/null"
    assert fake.tls is False  # TLS only applies to the TCP path
    assert fake.timeout == 7
    assert fake.disconnected is True
    lql, headers = fake.queries[0]
    assert lql == "GET hosts\nColumns: name state\n"
    assert headers == ""


@pytest.mark.asyncio
async def test_sub_second_timeout_never_becomes_nonblocking(fake_cmk_client):
    """timeout=0.5 must not truncate to set_timeout(0) (= non-blocking socket)."""
    conn = LivestatusConnection(socket_path="/dev/null", timeout=0.5)
    conn._use_cmk_client = True
    await conn._query_with_site("GET hosts\n")
    assert _FakeSingleSiteConnection.instances[-1].timeout == 1


@pytest.mark.asyncio
async def test_query_passes_auth_user_header(fake_cmk_client):
    conn = LivestatusConnection(socket_path="/dev/null")
    conn._use_cmk_client = True
    async with conn.with_auth_user("ops"):
        await conn._query_with_site("GET hosts\n")
    _lql, headers = _FakeSingleSiteConnection.instances[-1].queries[0]
    assert headers == "AuthUser: ops\n"


@pytest.mark.asyncio
async def test_tcp_tls_params_forwarded(fake_cmk_client):
    conn = LivestatusConnection(host="10.0.0.1", port=6557, tls=True, tls_verify=True)
    conn._use_cmk_client = True
    await conn._query_with_site("GET hosts\n")
    fake = _FakeSingleSiteConnection.instances[-1]
    assert fake.socketurl == "tcp:10.0.0.1:6557"
    assert fake.tls is True
    assert fake.verify is True


@pytest.mark.asyncio
async def test_send_command_routes_through_cmk_client(fake_cmk_client):
    conn = LivestatusConnection(socket_path="/dev/null")
    conn._use_cmk_client = True
    await conn.send_command("SCHEDULE_FORCED_SVC_CHECK;h1;CPU;1700000000")
    fake = _FakeSingleSiteConnection.instances[-1]
    # Bare body — the client adds the COMMAND [<ts>] framing itself.
    assert fake.commands == ["SCHEDULE_FORCED_SVC_CHECK;h1;CPU;1700000000"]
    assert fake.disconnected is True


def test_lql_to_query_builds_query_specification(fake_cmk_client):
    """Structured queries make the client use OutputFormat json (fast path)."""
    q = ls_mod._lql_to_query(
        "GET services\nColumns: host_name description state\nFilter: state > 0\nLimit: 5\n"
    )
    spec = q.wrapped
    assert isinstance(spec, _FakeQuerySpecification)
    assert spec.table == "services"
    assert spec.columns == ["host_name", "description", "state"]
    assert spec.headers == "Filter: state > 0\nLimit: 5\n"


def test_lql_to_query_roundtrips_lql(fake_cmk_client):
    lql = "GET hosts\nColumns: name state\nFilter: name != \n"
    assert str(ls_mod._lql_to_query(lql)) == lql


def test_lql_to_query_falls_back_to_string(fake_cmk_client):
    """No GET line or repeated Columns → keep the raw string (slow but correct)."""
    assert ls_mod._lql_to_query("COMMAND foo").wrapped == "COMMAND foo"
    doubled = "GET hosts\nColumns: name\nColumns: state\n"
    assert ls_mod._lql_to_query(doubled).wrapped == doubled


@pytest.mark.asyncio
async def test_native_path_used_when_flag_off(monkeypatch):
    conn = LivestatusConnection(socket_path="/dev/null")
    called: list[str] = []

    async def _fake_query_raw(query: str) -> list[list[object]]:
        called.append(query)
        return [["h1", 0]]

    monkeypatch.setattr(conn, "_query_raw", _fake_query_raw)
    rows = await conn._query_with_site("GET hosts\n")
    assert called == ["GET hosts\n"]
    assert rows == [(None, ["h1", 0])]
