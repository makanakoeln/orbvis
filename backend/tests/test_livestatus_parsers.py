"""Unit tests for the pure parsing/aggregation helpers in the Livestatus backend.

These cover LQL value escaping, the typed row accessors, the WATO folder-path
and contact-group parsing, BI state coercion, the state/detail row builders and
the perf_data parser — all without opening a Livestatus socket. The socket
routing through ``cmk.livestatus_client`` lives in ``test_livestatus_cmk_client.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.connections.livestatus import (
    _aggregations_to_object_states,
    _apply_extra,
    _build_details,
    _default_site_id,
    _folder_cgconf,
    _folder_path_from_filename,
    _hierarchy_to_node,
    _host_member_rows,
    _ls_escape,
    _parent_folder_path,
    _parse_bi_state,
    _parse_host_state_row,
    _parse_metrics_from_perf,
    _parse_service_state_row,
    _read_wato_info,
    _row_bool,
    _row_dict,
    _row_float,
    _row_float_or_none,
    _row_int,
    _row_list,
    _row_str,
    _row_strs,
    _rrd_metric_id,
    _service_member_rows,
    _services_summary_from_row,
    _title_case,
    _walk_wato_folders,
)
from app.schemas.state import ObjectState


class TestLsEscape:
    def test_strips_newlines(self) -> None:
        assert _ls_escape("foo\nbar") == "foobar"

    def test_strips_carriage_returns(self) -> None:
        assert _ls_escape("foo\r\nbar") == "foobar"

    def test_passthrough_plain(self) -> None:
        assert _ls_escape("host01") == "host01"


class TestRowStr:
    def test_returns_string(self) -> None:
        assert _row_str(["a", "b"], 1) == "b"

    def test_out_of_range_returns_default(self) -> None:
        assert _row_str(["a"], 5, "x") == "x"

    def test_non_string_returns_default(self) -> None:
        assert _row_str([5], 0) == ""


class TestRowInt:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(5, 5), (5.9, 5), (True, 1), (False, 0), ("7", 7)],
    )
    def test_coercions(self, value: object, expected: int) -> None:
        assert _row_int([value], 0) == expected

    def test_unparseable_string_returns_default(self) -> None:
        assert _row_int(["nope"], 0, default=3) == 3

    def test_out_of_range_returns_default(self) -> None:
        assert _row_int([], 0, default=9) == 9


class TestRowFloat:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [(5, 5.0), (5.5, 5.5), (True, 1.0), ("2.5", 2.5)],
    )
    def test_coercions(self, value: object, expected: float) -> None:
        assert _row_float([value], 0) == expected

    def test_unparseable_string_returns_default(self) -> None:
        assert _row_float(["nope"], 0, default=1.5) == 1.5


class TestRowBool:
    def test_truthy_int(self) -> None:
        assert _row_bool([1], 0) is True

    def test_zero_is_false(self) -> None:
        assert _row_bool([0], 0) is False

    def test_out_of_range_uses_default(self) -> None:
        assert _row_bool([], 0, default=True) is True
        assert _row_bool([], 0, default=False) is False


class TestRowFloatOrNone:
    def test_positive_value(self) -> None:
        assert _row_float_or_none([3.5], 0) == 3.5

    def test_zero_sentinel_is_none(self) -> None:
        assert _row_float_or_none([0], 0) is None

    def test_out_of_range_is_none(self) -> None:
        assert _row_float_or_none([], 0) is None


class TestRowListAndDict:
    def test_list_value(self) -> None:
        assert _row_list([["a", "b"]], 0) == ["a", "b"]

    def test_list_non_list_is_empty(self) -> None:
        assert _row_list(["x"], 0) == []

    def test_strs_filters_falsy_and_stringifies(self) -> None:
        assert _row_strs([[1, "", "b", 0]], 0) == ["1", "b"]

    def test_dict_value(self) -> None:
        assert _row_dict([{"k": "v"}], 0) == {"k": "v"}

    def test_dict_non_dict_is_empty(self) -> None:
        assert _row_dict(["x"], 0) == {}


class TestServicesSummaryFromRow:
    def test_maps_five_consecutive_columns(self) -> None:
        summary = _services_summary_from_row([99, 1, 2, 3, 4, 5], base=1)
        assert summary.ok == 1
        assert summary.warning == 2
        assert summary.critical == 3
        assert summary.unknown == 4
        assert summary.pending == 5


class TestFolderPathFromFilename:
    @pytest.mark.parametrize(
        ("filename", "expected"),
        [
            ("/wato/datacenters/muc/hosts.mk", "datacenters/muc"),
            ("/wato/hosts.mk", ""),
            ("wato/hosts.mk", ""),
            ("", ""),
            ("/wato/top/hosts.mk", "top"),
        ],
    )
    def test_normalises(self, filename: str, expected: str) -> None:
        assert _folder_path_from_filename(filename) == expected


class TestParentFolderPath:
    def test_root_has_no_parent(self) -> None:
        assert _parent_folder_path("") is None

    def test_top_level_parent_is_root(self) -> None:
        assert _parent_folder_path("datacenters") == ""

    def test_nested_parent(self) -> None:
        assert _parent_folder_path("datacenters/muc") == "datacenters"


class TestFolderCgconf:
    def test_none_info_yields_empty(self) -> None:
        assert _folder_cgconf(None) == ([], False)

    def test_modern_dict_form(self) -> None:
        info: dict[str, object] = {
            "attributes": {"contactgroups": {"groups": ["admins"], "recurse_perms": True}}
        }
        assert _folder_cgconf(info) == (["admins"], True)

    def test_legacy_tuple_form(self) -> None:
        info: dict[str, object] = {"attributes": {"contactgroups": (True, ["ops"])}}
        assert _folder_cgconf(info) == (["ops"], False)

    def test_missing_contactgroups(self) -> None:
        assert _folder_cgconf({"attributes": {}}) == ([], False)

    def test_non_dict_attributes(self) -> None:
        assert _folder_cgconf({"attributes": "nope"}) == ([], False)


class TestParseBiState:
    @pytest.mark.parametrize(("value", "expected"), [(0, 0), (2, 2), (2.0, 2), ("1", 1)])
    def test_numeric_and_string(self, value: object, expected: int) -> None:
        assert _parse_bi_state(value) == expected

    def test_unparseable_string_is_minus_one(self) -> None:
        assert _parse_bi_state("nope") == -1

    def test_non_numeric_is_minus_one(self) -> None:
        assert _parse_bi_state(None) == -1


class TestAggregationsToObjectStates:
    def test_maps_present_entries(self) -> None:
        raw = {"agg1": {"state": 2, "output": "crit", "acknowledged": True, "in_downtime": False}}
        out = _aggregations_to_object_states(raw, ["agg1"])
        assert out["agg1"].state == "CRITICAL"
        assert out["agg1"].output == "crit"
        assert out["agg1"].acknowledged is True

    def test_state_zero_is_ok_not_pending(self) -> None:
        # state 0 is falsy; guards against the classic `state or -1` bug.
        out = _aggregations_to_object_states({"a": {"state": 0}}, ["a"])
        assert out["a"].state == "OK"

    def test_missing_entry_gets_stale_pending(self) -> None:
        out = _aggregations_to_object_states({}, ["ghost"])
        assert out["ghost"].state == "PENDING"
        assert out["ghost"].stale is True

    def test_non_mapping_raw_yields_all_pending(self) -> None:
        out = _aggregations_to_object_states("garbage", ["a", "b"])
        assert {k: v.state for k, v in out.items()} == {"a": "PENDING", "b": "PENDING"}


class TestHierarchyToNode:
    def test_leaf_with_core_state(self) -> None:
        node = {
            "name": "ping",
            "node_type": "bi_leaf",
            "type_specific": {"core": {"hostname": "web01", "service": "PING", "state": 2}},
            "children": [],
        }
        result = _hierarchy_to_node(node, depth=0, max_depth=5)
        assert result.node_type == "bi_leaf"
        assert result.host_name == "web01"
        assert result.service_description == "PING"
        assert result.state == 2

    def test_aggregator_recurses_into_children(self) -> None:
        node = {
            "name": "root",
            "node_type": "bi_aggregator",
            "children": [{"name": "child", "node_type": "bi_leaf", "children": []}],
        }
        result = _hierarchy_to_node(node, depth=0, max_depth=5)
        assert result.node_type == "bi_aggregator"
        assert len(result.children) == 1
        assert result.children[0].name == "child"

    def test_max_depth_stops_recursion(self) -> None:
        node = {
            "name": "root",
            "node_type": "bi_aggregator",
            "children": [{"name": "child", "node_type": "bi_aggregator", "children": []}],
        }
        result = _hierarchy_to_node(node, depth=0, max_depth=0)
        assert result.children == []


class TestApplyExtra:
    def test_fills_timing_and_attempt_fields(self) -> None:
        state = ObjectState(object_id="", type="host", state="UP")
        # offset 5: last_check, next_check, state_type, attempt, max, last_state_change, notif, checks
        row = ["", "", "", "", "", 100.0, 200.0, 1, 2, 3, 50.0, 1, 1]
        result = _apply_extra(state, row, offset=5)
        assert result.last_check == 100.0
        assert result.next_check == 200.0
        assert result.state_type == "HARD"
        assert result.current_attempt == 2
        assert result.max_attempts == 3
        assert result.last_state_change == 50.0

    def test_zero_timing_becomes_none(self) -> None:
        state = ObjectState(object_id="", type="host", state="UP")
        row = ["", "", "", "", "", 0, 0, 0, 1, 1, 0, 1, 1]
        result = _apply_extra(state, row, offset=5)
        assert result.last_check is None
        assert result.next_check is None
        assert result.state_type == "SOFT"


class TestParseHostStateRow:
    def test_parses_name_and_state(self) -> None:
        row = ["web01", 1, "DOWN output", "", 0, 0, "10.0.0.1", "Web 01", 0, 0, 1, 1, 1, 0, 1, 1]
        name, state = _parse_host_state_row(row, site_id="muc")
        assert name == "web01"
        assert state.state == "DOWN"
        assert state.output == "DOWN output"
        assert state.address == "10.0.0.1"
        assert state.alias == "Web 01"
        assert state.site_id == "muc"


class TestParseServiceStateRow:
    def test_parses_host_service_key_and_state(self) -> None:
        row = ["web01", "PING", 2, "CRIT", "rta=5ms", 0, 0, 0, 0, 1, 1, 1, 0, 1, 1]
        key, state = _parse_service_state_row(row)
        assert key == ("web01", "PING")
        assert state.state == "CRITICAL"
        assert state.output == "CRIT"
        assert state.perf_data == "rta=5ms"


class TestBuildDetails:
    def test_host_details_with_groups_and_comments(self) -> None:
        # _HOST_DETAIL_COLS: long_output, check_command, latency, execution_time,
        # is_flapping, in_notif_period, notif_period, check_interval (8 common),
        # then parents, childs, groups, contact_groups, labels
        row = [
            "line1\\nline2",
            "check-mk-host",
            0.5,
            0.1,
            0,
            1,
            "24x7",
            60.0,
            ["parent01"],
            ["child01"],
            ["grp"],
            ["cg"],
            {"env": "prod"},
        ]
        comment_rows = [[1, "admin", "hi", 100.0, 0]]
        details = _build_details("host", "web01", None, row, comment_rows, [])
        assert details.host_name == "web01"
        assert details.long_output == "line1\nline2"
        assert details.check_command == "check-mk-host"
        assert details.parents == ["parent01"]
        assert details.labels == {"env": "prod"}
        assert len(details.comments) == 1
        assert details.comments[0].author == "admin"

    def test_service_details_use_service_columns(self) -> None:
        row = [
            "",
            "check_ping",
            0.0,
            0.0,
            0,
            1,
            "24x7",
            60.0,
            ["hg"],
            ["sg"],
            ["cg"],
            {},
            123.0,
        ]
        details = _build_details("service", "web01", "PING", row, [], [])
        assert details.service_description == "PING"
        assert details.service_groups == ["sg"]
        assert details.last_time_ok == 123.0


class TestParseMetricsFromPerf:
    def test_parses_label_and_unit(self) -> None:
        metrics = _parse_metrics_from_perf("rta=5ms;100;200 pl=0%;5;10")
        assert metrics == [{"label": "rta", "unit": "ms"}, {"label": "pl", "unit": "%"}]

    def test_quoted_label_with_spaces(self) -> None:
        metrics = _parse_metrics_from_perf("'disk usage'=50GB")
        assert metrics == [{"label": "disk usage", "unit": "GB"}]

    def test_empty_perf_data(self) -> None:
        assert _parse_metrics_from_perf("") == []


class TestRrdMetricId:
    def test_replaces_spaces_and_colons(self) -> None:
        assert _rrd_metric_id("disk read:rate") == "disk_read_rate"

    def test_plain_label_unchanged(self) -> None:
        assert _rrd_metric_id("rta") == "rta"


class TestTitleCase:
    def test_underscores_become_words(self) -> None:
        assert _title_case("if_in_octets") == "If In Octets"

    def test_single_word(self) -> None:
        assert _title_case("rta") == "Rta"


class TestDefaultSiteId:
    def test_explicit_sid_passthrough(self) -> None:
        assert _default_site_id("muc") == "muc"

    def test_falls_back_to_configured_site(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.connections.livestatus.settings.checkmk_site", "central")
        assert _default_site_id(None) == "central"

    def test_falls_back_to_local(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.connections.livestatus.settings.checkmk_site", "")
        assert _default_site_id(None) == "local"


class TestMemberRows:
    def test_host_member_rows(self) -> None:
        rows = [["web01", 1, "down\nsecond line", 1, 2, 0, 50.0]]
        members = _host_member_rows(rows)
        assert len(members) == 1
        assert members[0]["host"] == "web01"
        assert members[0]["state"] == "DOWN"
        assert members[0]["output"] == "down"  # first line only
        assert members[0]["acknowledged"] is True
        assert members[0]["in_downtime"] is True

    def test_host_member_rows_skip_nameless(self) -> None:
        assert _host_member_rows([["", 0, "", 0, 0, 1, 0]]) == []

    def test_service_member_rows(self) -> None:
        rows = [["web01", "PING", 2, "crit", 0, 0, 1, 0.0]]
        members = _service_member_rows(rows)
        assert members[0]["host"] == "web01"
        assert members[0]["service"] == "PING"
        assert members[0]["state"] == "CRITICAL"

    def test_service_member_rows_skip_incomplete(self) -> None:
        assert _service_member_rows([["web01", "", 0, "", 0, 0, 1, 0.0]]) == []


class TestReadWatoInfo:
    def test_parses_python_dict_literal(self, tmp_path: Path) -> None:
        wato = tmp_path / ".wato"
        wato.write_text("{'title': 'Datacenters', '__id': 'abc123'}", encoding="utf-8")
        info = _read_wato_info(wato)
        assert info == {"title": "Datacenters", "__id": "abc123"}

    def test_malformed_file_returns_none(self, tmp_path: Path) -> None:
        wato = tmp_path / ".wato"
        wato.write_text("this is not a dict literal", encoding="utf-8")
        assert _read_wato_info(wato) is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert _read_wato_info(tmp_path / "absent" / ".wato") is None

    def test_non_dict_literal_returns_none(self, tmp_path: Path) -> None:
        wato = tmp_path / ".wato"
        wato.write_text("[1, 2, 3]", encoding="utf-8")
        assert _read_wato_info(wato) is None


class TestWalkWatoFolders:
    def _write(self, root: Path, rel: str, content: str) -> None:
        folder = root if rel == "" else root / rel
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".wato").write_text(content, encoding="utf-8")

    def test_includes_root_with_main_fallback_title(self, tmp_path: Path) -> None:
        self._write(tmp_path, "", "{}")
        folders = _walk_wato_folders(tmp_path)
        root = next(f for f in folders if f["path"] == "")
        assert root["title"] == "Main"

    def test_uses_explicit_title_and_folder_id(self, tmp_path: Path) -> None:
        self._write(tmp_path, "dc", "{'title': 'Datacenters', '__id': 'fid-1'}")
        folders = _walk_wato_folders(tmp_path)
        dc = next(f for f in folders if f["path"] == "dc")
        assert dc["title"] == "Datacenters"
        assert dc["folder_id"] == "fid-1"

    def test_falls_back_to_path_segment_title(self, tmp_path: Path) -> None:
        self._write(tmp_path, "dc/muc", "{}")
        folders = _walk_wato_folders(tmp_path)
        muc = next(f for f in folders if f["path"] == "dc/muc")
        assert muc["title"] == "muc"

    def test_recurse_perms_inherit_to_children(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "dc",
            "{'attributes': {'contactgroups': {'groups': ['ops'], 'recurse_perms': True}}}",
        )
        self._write(tmp_path, "dc/muc", "{}")
        folders = _walk_wato_folders(tmp_path)
        muc = next(f for f in folders if f["path"] == "dc/muc")
        assert "ops" in muc["permitted_groups"]

    def test_non_recursive_groups_do_not_inherit(self, tmp_path: Path) -> None:
        self._write(
            tmp_path,
            "dc",
            "{'attributes': {'contactgroups': {'groups': ['ops'], 'recurse_perms': False}}}",
        )
        self._write(tmp_path, "dc/muc", "{}")
        folders = _walk_wato_folders(tmp_path)
        muc = next(f for f in folders if f["path"] == "dc/muc")
        assert muc["permitted_groups"] == []
