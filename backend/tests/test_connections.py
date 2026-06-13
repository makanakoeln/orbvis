"""Connection tests."""

import asyncio

import pytest

from app.connections.livestatus import (
    LivestatusConnection,
    _apply_extra,
    _default_site_id,
    _match_graphs,
    _walk_wato_folders,
)
from app.connections.test import TestConnection
from app.schemas.state import ObjectState


def test_default_site_id_prefers_row_tag(monkeypatch):
    """A per-row site tag wins over the configured default."""
    monkeypatch.setattr("app.core.config.settings.checkmk_site", "CENTRAL")
    assert _default_site_id("REMOTE_A") == "REMOTE_A"


def test_default_site_id_falls_back_to_configured_site(monkeypatch):
    """No row tag (single-site connection) → configured checkmk_site."""
    monkeypatch.setattr("app.core.config.settings.checkmk_site", "CENTRAL")
    assert _default_site_id(None) == "CENTRAL"
    # Empty tag is treated like a missing one (federated fetch can yield "").
    assert _default_site_id("") == "CENTRAL"


def test_default_site_id_standalone_local(monkeypatch):
    """Standalone (no checkmk_site) → 'local'."""
    monkeypatch.setattr("app.core.config.settings.checkmk_site", "")
    assert _default_site_id(None) == "local"
    assert _default_site_id() == "local"


@pytest.mark.asyncio
async def test_test_backend_host_state():
    connection = TestConnection()
    state = await connection.get_host_state("localhost")
    assert state.type == "host"
    assert state.state in ("UP", "DOWN", "UNREACHABLE")


@pytest.mark.asyncio
async def test_test_connection_service_state():
    connection = TestConnection()
    state = await connection.get_service_state("localhost", "HTTP")
    assert state.type == "service"
    assert state.state in ("OK", "WARNING", "CRITICAL", "UNKNOWN")


@pytest.mark.asyncio
async def test_test_backend_get_objects():
    connection = TestConnection()
    hosts = await connection.get_objects("host")
    assert len(hosts) > 0
    assert "localhost" in hosts


@pytest.mark.asyncio
async def test_test_backend_get_objects_search_filters():
    # Server-side autocompleter substring (CMK-style): only matching names come back.
    connection = TestConnection()
    all_hosts = await connection.get_objects("host")
    hit = next(h for h in all_hosts if "host" in h.lower())
    filtered = await connection.get_objects("host", None, "HOST")
    assert filtered == [h for h in all_hosts if "host" in h.lower()]
    assert hit in filtered
    assert await connection.get_objects("host", None, "zzz-no-match") == []


@pytest.mark.asyncio
async def test_test_backend_search_services_by_description():
    # A service term matches every host that runs a matching service, carrying
    # the host + site so the frontend can place the hit in the folder tree.
    connection = TestConnection()
    rows = await connection.search_services(
        host_terms=[], service_terms=["disk"], any_terms=[], limit=100
    )
    assert {r["host_name"] for r in rows} == {
        "localhost",
        "router01",
        "switch01",
        "fileserver",
        "mailserver",
    }
    assert all(r["name"] == "Disk /" for r in rows)
    assert all("site_id" in r for r in rows)


@pytest.mark.asyncio
async def test_test_backend_search_services_and_combines_host_and_service():
    # host + service terms AND together: only the named host's matching service.
    connection = TestConnection()
    rows = await connection.search_services(
        host_terms=["mail"], service_terms=["disk"], any_terms=[], limit=100
    )
    assert [(r["host_name"], r["name"]) for r in rows] == [("mailserver", "Disk /")]


@pytest.mark.asyncio
async def test_test_backend_search_services_bare_matches_host_or_service():
    connection = TestConnection()
    # Bare term hits the host name…
    by_host = await connection.search_services(
        host_terms=[], service_terms=[], any_terms=["switch01"], limit=100
    )
    assert {r["host_name"] for r in by_host} == {"switch01"}
    # …and the service description.
    by_svc = await connection.search_services(
        host_terms=[], service_terms=[], any_terms=["memory"], limit=100
    )
    assert by_svc and all(r["name"] == "Memory" for r in by_svc)


@pytest.mark.asyncio
async def test_test_backend_search_services_respects_limit():
    # limit + 1 is returned so the caller can detect truncation.
    connection = TestConnection()
    rows = await connection.search_services(
        host_terms=[], service_terms=["disk"], any_terms=[], limit=2
    )
    assert len(rows) == 3


@pytest.mark.asyncio
async def test_test_backend_search_services_empty_without_terms():
    # No terms at all → nothing (the endpoint additionally never calls this for a
    # host-only query, which is answered from the already-loaded tree).
    connection = TestConnection()
    assert (
        await connection.search_services(host_terms=[], service_terms=[], any_terms=[], limit=100)
        == []
    )


@pytest.mark.asyncio
async def test_test_backend_is_available():
    connection = TestConnection()
    assert await connection.is_available() is True


@pytest.mark.asyncio
async def test_test_backend_services_summary():
    connection = TestConnection()
    summary = await connection.get_services_summary(["localhost"])
    assert "localhost" in summary
    counts = summary["localhost"]
    # Total must equal the number of demo services for the host.
    assert counts.ok + counts.warning + counts.critical + counts.unknown + counts.pending == 10


@pytest.mark.asyncio
async def test_test_backend_host_state_carries_alias_and_timing():
    connection = TestConnection()
    state = await connection.get_host_state("localhost")
    assert state.alias == "alias-localhost"
    assert state.last_check is not None
    assert state.next_check is not None
    assert state.next_check > state.last_check
    assert state.state_type == "HARD"
    assert state.max_attempts == 3


def test_match_graphs_carries_mirrored_metrics(monkeypatch):
    """A Bidirectional graph's lower metrics survive into GraphGroup.mirrored."""
    from app.integrations.cmk_plugins import CMKGraphingData

    data = CMKGraphingData(
        graphs={
            "bandwidth": (
                "Bandwidth",
                ["if_in_bps", "if_out_bps"],
                frozenset(),
                frozenset({"if_out_bps"}),
            )
        }
    )
    monkeypatch.setattr("app.connections.livestatus.load_cmk_graphing_data", lambda: data)

    groups = _match_graphs({"if_in_bps", "if_out_bps"})
    assert len(groups) == 1
    assert groups[0].metrics == ["if_in_bps", "if_out_bps"]
    assert groups[0].mirrored == ["if_out_bps"]


def test_match_graphs_mirrored_drops_unavailable_metrics(monkeypatch):
    """Mirrored is intersected with the available series, like metrics is."""
    from app.integrations.cmk_plugins import CMKGraphingData

    data = CMKGraphingData(
        graphs={
            "bandwidth": (
                "Bandwidth",
                ["if_in_bps", "if_out_bps"],
                frozenset(),
                frozenset({"if_out_bps"}),
            )
        }
    )
    monkeypatch.setattr("app.connections.livestatus.load_cmk_graphing_data", lambda: data)

    groups = _match_graphs({"if_in_bps"})
    assert groups[0].metrics == ["if_in_bps"]
    assert groups[0].mirrored == []


def test_match_graphs_translates_raw_perfvars_to_canonical(monkeypatch):
    """Raw perfvars (interface in/out) match a canonical template via the name map,
    and the result stays in raw names so it lines up with the series keys."""
    from app.integrations.cmk_plugins import CMKGraphingData

    data = CMKGraphingData(
        graphs={
            "bandwidth": (
                "Bandwidth",
                ["if_in_bps", "if_out_bps"],
                frozenset(),
                frozenset({"if_out_bps"}),
            )
        }
    )
    monkeypatch.setattr("app.connections.livestatus.load_cmk_graphing_data", lambda: data)

    # Without translation the raw perfvars don't match the canonical template.
    assert _match_graphs({"in", "out"}) == []

    name_map = {"in": "if_in_bps", "out": "if_out_bps"}
    groups = _match_graphs({"in", "out"}, name_map)
    assert len(groups) == 1
    assert sorted(groups[0].metrics) == ["in", "out"]
    assert groups[0].mirrored == ["out"]


def test_apply_extra_host_columns_map_correctly():
    """Verify _apply_extra reads the correct column offsets after schema changes.

    Layout (host, after standard 5-col prefix at offset=5):
      [5]=address [6]=alias [7]=last_check [8]=next_check [9]=state_type
      [10]=current_attempt [11]=max_check_attempts [12]=last_state_change
      [13]=notifications_enabled [14]=active_checks_enabled
    """
    state = ObjectState(object_id="", type="host", state="UP")
    row = [
        0,
        "out",
        "",
        0,
        0,
        "192.0.2.1",  # address
        "ALIAS",  # alias
        1700.0,  # last_check
        1760.0,  # next_check
        1,  # state_type=HARD
        2,  # current_attempt
        3,  # max_attempts
        1500.0,  # last_state_change
        1,  # notifications_enabled
        0,  # active_checks_enabled
    ]
    _apply_extra(state, row, offset=5, include_address=True)
    assert state.address == "192.0.2.1"
    assert state.alias == "ALIAS"
    assert state.last_check == 1700.0
    assert state.next_check == 1760.0
    assert state.state_type == "HARD"
    assert state.current_attempt == 2
    assert state.max_attempts == 3
    assert state.last_state_change == 1500.0
    assert state.notifications_enabled is True
    assert state.active_checks_enabled is False


def test_apply_extra_service_columns_map_correctly():
    """Service rows have no alias slot — only next_check is added."""
    state = ObjectState(object_id="", type="service", state="OK")
    row = [
        "h",
        "s",
        0,
        "out",
        "",
        0,
        0,
        1700.0,  # last_check
        1760.0,  # next_check
        0,  # state_type=SOFT
        2,  # current_attempt
        3,  # max_attempts
        1500.0,  # last_state_change
        1,  # notifications_enabled
        1,  # active_checks_enabled
    ]
    _apply_extra(state, row, offset=7)
    assert state.last_check == 1700.0
    assert state.next_check == 1760.0
    assert state.state_type == "SOFT"
    assert state.current_attempt == 2
    assert state.max_attempts == 3
    assert state.last_state_change == 1500.0


def _make_livestatus_connection() -> LivestatusConnection:
    """LivestatusConnection without opening a real socket. Tests stub `_query`."""
    return LivestatusConnection(socket_path="/dev/null")


@pytest.mark.asyncio
async def test_bulk_services_chunks_and_runs_in_parallel(monkeypatch):
    """25-host batch with chunk_size=5 must fan out to 5 concurrent queries.

    Uses an ``asyncio.Barrier`` to prove parallelism deterministically: every
    chunk query must reach the barrier before any returns, so the test fails
    fast on serial execution rather than relying on timing.
    """
    monkeypatch.setattr("app.core.config.settings.flow_board_bulk_service_chunk_size", 5)
    connection = _make_livestatus_connection()

    chunk_args: list[list[str]] = []
    barrier = asyncio.Barrier(5)

    async def _fake_query(query: str) -> list[list[object]]:
        hosts = [
            line.split("=", 1)[1].strip()
            for line in query.splitlines()
            if line.startswith("Filter: host_name =")
        ]
        chunk_args.append(hosts)
        await barrier.wait()
        return [[h, f"{h}/svc", 0, "ok"] for h in hosts]

    monkeypatch.setattr(connection, "_query", _fake_query)

    hostnames = [f"h{i:02d}" for i in range(25)]
    result = await connection.get_hosts_services_batch(hostnames)

    assert len(chunk_args) == 5
    assert sorted(c for chunk in chunk_args for c in chunk) == sorted(hostnames)
    assert sorted(result.keys()) == sorted(hostnames)
    for h, svcs in result.items():
        assert [s["name"] for s in svcs] == [f"{h}/svc"]


@pytest.mark.asyncio
async def test_bulk_services_empty_input_skips_query(monkeypatch):
    connection = _make_livestatus_connection()
    called = False

    async def _fake_query(_query: str) -> list[list[object]]:
        nonlocal called
        called = True
        return []

    monkeypatch.setattr(connection, "_query", _fake_query)
    assert await connection.get_hosts_services_batch([]) == {}
    assert called is False


@pytest.mark.asyncio
async def test_bulk_services_smaller_than_chunk_size_runs_one_query(monkeypatch):
    """Three hosts with chunk_size=5 must collapse into a single query."""
    monkeypatch.setattr("app.core.config.settings.flow_board_bulk_service_chunk_size", 5)
    connection = _make_livestatus_connection()
    calls = 0

    async def _fake_query(_query: str) -> list[list[object]]:
        nonlocal calls
        calls += 1
        return [["h1", "svc-a", 0, ""]]

    monkeypatch.setattr(connection, "_query", _fake_query)
    result = await connection.get_hosts_services_batch(["h1", "h2", "h3"])
    assert calls == 1
    assert result["h1"][0]["name"] == "svc-a"
    assert result["h2"] == [] and result["h3"] == []


# ---------------------------------------------------------------------------
# Hostgroup / Servicegroup aggregation summaries
#
# The drawer + tooltip count chips are driven by ``services_summary`` on the
# group's aggregate ObjectState. These tests pin the Livestatus state-byte →
# summary-slot mapping (UP=ok, DOWN=critical, UNREACHABLE=unknown for hosts;
# OK/WARN/CRIT/UNKN straight-through for services) and the worst-state pick.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hostgroup_aggregation_fills_services_summary(monkeypatch):
    connection = _make_livestatus_connection()

    async def _fake_query(query: str):
        if query.startswith("GET hostgroups"):
            # exists check
            return [["web"]]
        # GET hosts ... Columns: state
        return [[0], [0], [1], [2], [0]]  # 3xUP, 1xDOWN, 1xUNREACHABLE

    monkeypatch.setattr(connection, "_query", _fake_query)
    state = await connection.get_hostgroup_states("web")
    assert state.state == "DOWN"
    assert state.services_summary is not None
    assert state.services_summary.ok == 3
    assert state.services_summary.critical == 1
    assert state.services_summary.unknown == 1
    assert state.services_summary.warning == 0


@pytest.mark.asyncio
async def test_hostgroup_aggregation_unknown_when_no_hosts(monkeypatch):
    connection = _make_livestatus_connection()

    async def _fake_query(query: str):
        if query.startswith("GET hostgroups"):
            return [["empty"]]
        return []

    monkeypatch.setattr(connection, "_query", _fake_query)
    state = await connection.get_hostgroup_states("empty")
    assert state.state == "PENDING"
    # No hosts → no summary populated.
    assert state.services_summary is None


@pytest.mark.asyncio
async def test_hostgroup_aggregation_not_found_when_group_missing(monkeypatch):
    connection = _make_livestatus_connection()

    async def _fake_query(query: str):
        return []  # exists check returns nothing

    monkeypatch.setattr(connection, "_query", _fake_query)
    state = await connection.get_hostgroup_states("ghost")
    assert state.state == "NOT_FOUND"


@pytest.mark.asyncio
async def test_servicegroup_aggregation_fills_services_summary(monkeypatch):
    connection = _make_livestatus_connection()

    async def _fake_query(query: str):
        if query.startswith("GET servicegroups"):
            return [["disks"]]
        # GET services ... Columns: state
        return [[0], [0], [1], [2], [3]]  # 2xOK, 1xWARN, 1xCRIT, 1xUNKN

    monkeypatch.setattr(connection, "_query", _fake_query)
    state = await connection.get_servicegroup_states("disks")
    assert state.state == "CRITICAL"
    assert state.services_summary is not None
    assert state.services_summary.ok == 2
    assert state.services_summary.warning == 1
    assert state.services_summary.critical == 1
    assert state.services_summary.unknown == 1


@pytest.mark.asyncio
async def test_group_member_states_hostgroup_includes_modifiers(monkeypatch):
    """``get_group_member_states`` returns one row per host with the
    Plugin-Output (first line only), ack/downtime/notification flags and
    last-state-change — exactly what the Members tab renders."""
    connection = _make_livestatus_connection()

    async def _fake_query(query: str):
        # name, state, output, ack, dt_depth, notif_enabled, last_state_change
        return [
            ["srv1", 0, "PING OK\nlatency 1ms", 0, 0, 1, 1700.0],
            ["srv2", 1, "ping fail", 1, 1, 0, 1750.0],
        ]

    monkeypatch.setattr(connection, "_query", _fake_query)
    rows = await connection.get_group_member_states("hostgroup", "web")
    assert [r["host"] for r in rows] == ["srv1", "srv2"]
    assert rows[0]["state"] == "UP"
    assert rows[0]["output"] == "PING OK"  # multi-line collapsed to first
    assert rows[1]["state"] == "DOWN"
    assert rows[1]["acknowledged"] is True
    assert rows[1]["in_downtime"] is True
    assert rows[1]["notifications_enabled"] is False
    assert rows[1]["last_state_change"] == 1750.0


@pytest.mark.asyncio
async def test_group_member_states_unknown_type_returns_empty(monkeypatch):
    connection = _make_livestatus_connection()
    rows = await connection.get_group_member_states("contactgroup", "x")
    assert rows == []


def test_walk_wato_folders_real_titles_and_empty(tmp_path):
    """Phase-3 .wato walk: real titles, stable __id, and empty folders.

    Mirrors the CMK on-disk layout — each folder dir carries a .wato dict
    literal; a folder dir with a .wato but no hosts is a (visible) empty folder.
    """
    wato = tmp_path / "wato"
    (wato).mkdir()
    (wato / ".wato").write_text("{'title': 'Main directory'}")  # root → skipped

    dc = wato / "orbvis_dc"
    dc.mkdir()
    (dc / ".wato").write_text("{'title': 'Datacenters', '__id': 'id-dc'}")
    muc = dc / "munich"
    muc.mkdir()
    (muc / ".wato").write_text("{'title': u'München', '__id': 'id-muc'}")
    empty = dc / "emptyrack"
    empty.mkdir()
    (empty / ".wato").write_text("{'title': 'Empty Rack', '__id': 'id-er'}")

    folders = _walk_wato_folders(wato)
    by_path = {f["path"]: f for f in folders}

    assert by_path[""]["title"] == "Main directory"  # real root title carried through
    assert by_path["orbvis_dc"]["title"] == "Datacenters"  # real title, not slug
    assert by_path["orbvis_dc"]["folder_id"] == "id-dc"
    assert by_path["orbvis_dc/munich"]["title"] == "München"  # unicode preserved
    assert "orbvis_dc/emptyrack" in by_path  # empty folder still listed


def test_walk_wato_folders_tolerates_bad_file(tmp_path):
    wato = tmp_path / "wato"
    (wato / "broken").mkdir(parents=True)
    (wato / "broken" / ".wato").write_text("{not valid python")
    folders = _walk_wato_folders(wato)
    # Unparseable .wato → folder still listed, title falls back to the slug.
    assert {f["path"]: f["title"] for f in folders} == {"broken": "broken"}


@pytest.mark.asyncio
async def test_get_objects_escapes_regex_metachars(monkeypatch):
    """The autocomplete needle goes into a `~~` regex filter — metacharacters
    typed by the user must arrive escaped, not break the query."""
    connection = _make_livestatus_connection()
    captured: list[str] = []

    async def _fake_query(query: str) -> list[list[object]]:
        captured.append(query)
        return [["web01"]]

    monkeypatch.setattr(connection, "_query", _fake_query)
    result = await connection.get_objects("host", search="srv(1[+")

    assert result == ["web01"]
    assert "Filter: name ~~ srv\\(1\\[\\+" in captured[0]


def test_ls_escape_strips_query_terminators():
    """LQL filter values are newline-terminated — an embedded \\n/\\r would
    inject extra filter/command lines into the query."""
    from app.connections.livestatus import _ls_escape

    assert _ls_escape("plain-host") == "plain-host"
    assert _ls_escape("evil\nFilter: name = other") == "evilFilter: name = other"
    assert _ls_escape("evil\r\nGET hosts") == "evilGET hosts"
    assert _ls_escape("") == ""
