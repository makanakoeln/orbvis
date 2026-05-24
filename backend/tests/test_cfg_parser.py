"""Tests for the legacy .cfg map parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.cfg_parser import _coord, _line_coords, _parse_blocks, cfg_to_board

# ---------------------------------------------------------------------------
# _parse_blocks
# ---------------------------------------------------------------------------


def test_parse_blocks_strips_hash_comments():
    text = "# top comment\ndefine global {\n    alias = Test\n}\n"
    blocks = _parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "global"
    assert blocks[0][1]["alias"] == "Test"


def test_parse_blocks_strips_semicolon_comments():
    text = "; semicolon comment\ndefine host {\n    host_name = srv\n}\n"
    blocks = _parse_blocks(text)
    assert blocks[0][1]["host_name"] == "srv"


def test_parse_blocks_multiple_blocks():
    text = "define global {\n    alias = Map\n}\ndefine host {\n    host_name = h1\n}\n"
    blocks = _parse_blocks(text)
    assert len(blocks) == 2
    assert blocks[0][0] == "global"
    assert blocks[1][0] == "host"


def test_parse_blocks_unknown_type_included():
    text = "define futuretype {\n    key = value\n}\n"
    blocks = _parse_blocks(text)
    assert len(blocks) == 1
    assert blocks[0][0] == "futuretype"
    assert blocks[0][1]["key"] == "value"


# ---------------------------------------------------------------------------
# _coord
# ---------------------------------------------------------------------------


def test_coord_integer():
    assert _coord("100") == 100
    assert _coord("  42  ") == 42


def test_coord_negative():
    assert _coord("-50") == -50


def test_coord_percent_offset():
    assert _coord("50%100") == 100
    assert _coord("-10%200") == 200
    assert _coord("0%-50") == -50


def test_coord_invalid_returns_zero():
    assert _coord("invalid") == 0
    assert _coord("abc%def") == 0


# ---------------------------------------------------------------------------
# _line_coords
# ---------------------------------------------------------------------------


def test_line_coords_comma_separated():
    p = {"x": "10,20", "y": "30,40"}
    assert _line_coords(p) == (10, 30, 20, 40)


def test_line_coords_separate_keys():
    p = {"x": "10", "y": "30", "x2": "20", "y2": "40"}
    assert _line_coords(p) == (10, 30, 20, 40)


def test_line_coords_defaults_to_zero():
    p: dict = {}
    assert _line_coords(p) == (0, 0, 0, 0)


# ---------------------------------------------------------------------------
# cfg_to_board — global block
# ---------------------------------------------------------------------------


def test_cfg_to_board_defaults():
    board = cfg_to_board("", "mymap")
    assert board["name"] == "mymap"
    assert board["alias"] == "mymap"
    assert board["objects"] == []


def test_cfg_to_board_global_alias():
    content = "define global {\n    alias = My Map\n}\n"
    board = cfg_to_board(content, "mymap")
    assert board["alias"] == "My Map"


def test_cfg_to_board_global_map_image():
    content = "define global {\n    map_image = bg.png\n}\n"
    board = cfg_to_board(content, "x")
    assert board["background_image"] == "bg.png"


def test_cfg_to_board_global_iconset():
    content = "define global {\n    iconset = std_big\n}\n"
    board = cfg_to_board(content, "x")
    assert board["icon_size"] == 30


# ---------------------------------------------------------------------------
# cfg_to_board — host block
# ---------------------------------------------------------------------------


def test_cfg_to_board_host():
    content = (
        "define host {\n"
        "    object_id = 1\n"
        "    host_name = server1\n"
        "    x = 100\n"
        "    y = 200\n"
        "    only_hard_states = 1\n"
        "    recognize_services = 1\n"
        "}\n"
    )
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["id"] == "host_1"
    assert obj["type"] == "host"
    assert obj["host_name"] == "server1"
    assert obj["x"] == 100
    assert obj["y"] == 200
    assert obj["only_hard_states"] is True
    assert obj["recognize_services"] is True


def test_cfg_to_board_host_without_flags():
    content = "define host {\n    object_id = 2\n    host_name = s\n    x = 0\n    y = 0\n}\n"
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert "only_hard_states" not in obj
    assert "recognize_services" not in obj


# ---------------------------------------------------------------------------
# cfg_to_board — service block
# ---------------------------------------------------------------------------


def test_cfg_to_board_service():
    content = (
        "define service {\n"
        "    object_id = 3\n"
        "    host_name = server1\n"
        "    service_description = CPU Load\n"
        "    x = 50\n"
        "    y = 60\n"
        "}\n"
    )
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["id"] == "service_3"
    assert obj["type"] == "service"
    assert obj["host_name"] == "server1"
    assert obj["service_description"] == "CPU Load"


# ---------------------------------------------------------------------------
# cfg_to_board — line block
# ---------------------------------------------------------------------------


def test_cfg_to_board_line_weathermap():
    # The legacy format encodes weathermap-style lines via line_type 13/14/15
    # on a stateful service block (view_type=line). Each variant decomposes
    # into shape (arrow_inward) + perfdata-label mode + weather-color flag.
    content = (
        "define service {\n"
        "    object_id = 4\n"
        "    x = 10,20\n"
        "    y = 30,40\n"
        "    line_type = 15\n"
        "    view_type = line\n"
        "    host_name = router1\n"
        "    service_description = Traffic\n"
        "}\n"
    )
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["id"] == "line_4"
    assert obj["type"] == "line"
    assert obj["line_style"] == "arrow_inward"
    assert obj["line_perfdata_label"] == "bandwidth"
    assert obj["line_weather_color"] is True
    assert obj["host_name"] == "router1"
    assert obj["service_description"] == "Traffic"


def test_cfg_to_board_line_plain_no_host():
    # line_type=12 is the truly plain, no-arrow line.
    content = "define line {\n    x = 0,10\n    y = 0,10\n    line_type = 12\n}\n"
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["line_style"] == "plain"
    assert "host_name" not in obj


def test_cfg_to_board_line_default_type_is_arrow_end():
    # Default line_type is 11 (arrow_end) when omitted in the .cfg.
    content = "define line {\n    x = 0,10\n    y = 0,10\n}\n"
    board = cfg_to_board(content, "test")
    assert board["objects"][0]["line_style"] == "arrow_end"


# ---------------------------------------------------------------------------
# cfg_to_board — shape block
# ---------------------------------------------------------------------------


def test_cfg_to_board_shape():
    content = "define shape {\n    object_id = 5\n    x = 50\n    y = 60\n    icon = img.png\n}\n"
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["id"] == "image_5"
    assert obj["type"] == "image"
    assert obj["image_src"] == "img.png"


# ---------------------------------------------------------------------------
# cfg_to_board — textbox block
# ---------------------------------------------------------------------------


def test_cfg_to_board_textbox_coordinates():
    # x + w//2, y + h//2
    content = (
        "define textbox {\n"
        "    object_id = 6\n"
        "    x = 100\n"
        "    y = 200\n"
        "    w = 200\n"
        "    h = 40\n"
        "    text = Hello\n"
        "}\n"
    )
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["x"] == 200  # 100 + 200//2
    assert obj["y"] == 220  # 200 + 40//2


def test_cfg_to_board_textbox_br_to_newline():
    content = "define textbox {\n    x = 0\n    y = 0\n    text = Hello<br>World\n}\n"
    board = cfg_to_board(content, "test")
    assert board["objects"][0]["label"]["text"] == "Hello\nWorld"


def test_cfg_to_board_textbox_html_stripped():
    content = "define textbox {\n    x = 0\n    y = 0\n    text = <b>Bold</b> text\n}\n"
    board = cfg_to_board(content, "test")
    assert board["objects"][0]["label"]["text"] == "Bold text"


# ---------------------------------------------------------------------------
# cfg_to_board — url_target mapping
# ---------------------------------------------------------------------------


def test_cfg_to_board_url_target_frameset_targets():
    for target in ("main", "frames", "main_window"):
        content = (
            f"define host {{\n"
            f"    host_name = s\n    x = 0\n    y = 0\n"
            f"    url_target = {target}\n"
            f"}}\n"
        )
        board = cfg_to_board(content, "test")
        assert board["objects"][0]["url_target"] == "_blank", f"Expected _blank for {target}"


def test_cfg_to_board_url_target_custom():
    content = "define host {\n    host_name = s\n    x = 0\n    y = 0\n    url_target = _self\n}\n"
    board = cfg_to_board(content, "test")
    assert board["objects"][0]["url_target"] == "_self"


# ---------------------------------------------------------------------------
# cfg_to_board — counter-based IDs
# ---------------------------------------------------------------------------


def test_cfg_to_board_counter_id_without_object_id():
    content = (
        "define host {\n    host_name = s1\n    x = 0\n    y = 0\n}\n"
        "define host {\n    host_name = s2\n    x = 10\n    y = 10\n}\n"
    )
    board = cfg_to_board(content, "test")
    ids = [obj["id"] for obj in board["objects"]]
    assert ids == ["host_1", "host_2"]


# ---------------------------------------------------------------------------
# cfg_to_board — unknown block types skipped
# ---------------------------------------------------------------------------


def test_cfg_to_board_unknown_block_skipped():
    content = (
        "define futuretype {\n    foo = bar\n}\n"
        "define host {\n    object_id = 99\n    host_name = s\n    x = 0\n    y = 0\n}\n"
    )
    board = cfg_to_board(content, "test")
    assert len(board["objects"]) == 1
    assert board["objects"][0]["host_name"] == "s"


# ---------------------------------------------------------------------------
# cfg_to_board — full legacy-format fixture coverage
#
# `fixtures/nagvis_all_objects.cfg` is a hand-crafted .cfg map exercising every
# block type and view_type variant the parser supports. This test pins the
# expected import shape so future parser changes can't silently regress
# (e.g. dropping aggregations or misclassifying a service-as-line as an icon).
# ---------------------------------------------------------------------------

_FIXTURE = Path(__file__).parent / "fixtures" / "nagvis_all_objects.cfg"


@pytest.fixture
def all_objects_board() -> dict[str, object]:
    return cfg_to_board(_FIXTURE.read_text(encoding="utf-8"), "all-objects")


def _by_id(board: dict[str, object], obj_id: str) -> dict[str, object]:
    objs = board["objects"]
    assert isinstance(objs, list)
    matches = [o for o in objs if o["id"] == obj_id]
    assert len(matches) == 1, f"expected exactly one object with id {obj_id!r}, got {len(matches)}"
    return matches[0]


def test_fixture_global_settings(all_objects_board):
    assert all_objects_board["alias"] == "All Objects"
    assert all_objects_board["connection_id"] == "ZWEIFUENF"
    assert all_objects_board["icon_size"] == 30  # iconset=std_big
    assert all_objects_board["view"] == {"type": "static"}


def test_fixture_object_count(all_objects_board):
    # 1 host + 4 services (icon/gadget/line-via-view_type/url) + 1 hg + 1 sg + 4 lines
    # (3 stateless: arrow_inward/arrow_end/plain + 1 service-bound weathermap) +
    # 1 textbox + 1 image (shape) + 1 map link + 1 aggregation = 15 objects.
    assert len(all_objects_board["objects"]) == 15


def test_fixture_host(all_objects_board):
    o = _by_id(all_objects_board, "host_h00001")
    assert o["type"] == "host"
    assert o["host_name"] == "localhost"
    assert (o["x"], o["y"]) == (200, 120)
    assert o["only_hard_states"] is True
    assert o["recognize_services"] is True


def test_fixture_service_icon(all_objects_board):
    o = _by_id(all_objects_board, "service_s00001")
    assert o["type"] == "service"
    assert o["service_description"] == "Memory"
    assert o["display"] == {"mode": "icon"}
    assert o["only_hard_states"] is True


def test_fixture_service_gadget(all_objects_board):
    o = _by_id(all_objects_board, "service_s00002")
    # gadget_url=std_speedometer.php must map to OrbVis gadget_type=gauge
    # (otherwise the gauge renders empty because no metric is selected).
    assert o["display"] == {"mode": "gadget", "gadget_type": "gauge", "gadget_metric": None}


def test_fixture_service_with_view_type_line_becomes_line(all_objects_board):
    """The legacy format encodes lines as service blocks with view_type=line — must import as line."""
    o = _by_id(all_objects_board, "line_s00003")
    assert o["type"] == "line"
    assert (o["x"], o["y"], o["x2"], o["y2"]) == (200, 320, 800, 320)
    assert o["host_name"] == "localhost"
    assert o["service_description"] == "Interface 2"
    # No explicit line_type → default (11 → arrow_end)
    assert o["line_style"] == "arrow_end"


def test_fixture_hostgroup(all_objects_board):
    o = _by_id(all_objects_board, "hostgroup_hg0001")
    assert o["type"] == "hostgroup"
    assert o["group_name"] == "linux-servers"


def test_fixture_servicegroup(all_objects_board):
    o = _by_id(all_objects_board, "servicegroup_sg0001")
    assert o["type"] == "servicegroup"
    assert o["group_name"] == "disk-services"


@pytest.mark.parametrize(
    # Legacy line_type → OrbVis line_style mapping for stateless `define line`
    # blocks. See app.services.cfg_parser.LINE_TYPE_MAP for the rationale.
    "obj_id, expected_style",
    [
        ("line_l00001", "arrow_inward"),  # line_type=10 — bidirectional, midpoint
        ("line_l00002", "arrow_end"),  # line_type=11
        ("line_l00003", "plain"),  # line_type=12
    ],
)
def test_fixture_line_styles(all_objects_board, obj_id, expected_style):
    o = _by_id(all_objects_board, obj_id)
    assert o["type"] == "line"
    assert o["line_style"] == expected_style


def test_fixture_service_bound_weathermap_line_carries_metrics(all_objects_board):
    """A bandwidth-labelled weathermap line decomposes into arrow_inward shape +
    perfdata_label='bandwidth' + weather_color=True with both metrics resolved."""
    o = _by_id(all_objects_board, "line_l00004")
    assert o["type"] == "line"
    assert o["line_style"] == "arrow_inward"
    assert o["line_perfdata_label"] == "bandwidth"
    assert o["line_weather_color"] is True
    assert o["host_name"] == "localhost"
    assert o["service_description"] == "Interface 2"
    assert o["weathermap_metric"] == "in"
    assert o["weathermap_metric_out"] == "out"
    # Per-line stroke width is a configurable attribute (default 3 upstream),
    # so an explicit value must round-trip into the imported board.
    assert o["line_width"] == 5


def test_legacy_weathermap_style_migrates_to_arrow_inward():
    """A stored board with line_style='weathermap' must keep loading by
    rewriting transparently to the orthogonal model on validation."""
    from app.schemas.board import BoardObject

    obj = BoardObject.model_validate(
        {
            "id": "line_legacy",
            "type": "line",
            "line_style": "weathermap",
            "host_name": "h",
            "service_description": "s",
        }
    )
    assert obj.line_style == "arrow_inward"
    assert obj.line_perfdata_label == "bandwidth"
    assert obj.line_weather_color is True


def test_view_type_gadget_without_url_defaults_to_gauge():
    # The legacy format defaults a gadget service without explicit gadget_url
    # to the speedometer; OrbVis follows suit so the icon doesn't silently
    # fall back to a plain icon.
    content = (
        "define service {\n"
        "    object_id = 9\n"
        "    host_name = h\n"
        "    service_description = CPU\n"
        "    x = 0\n"
        "    y = 0\n"
        "    view_type = gadget\n"
        "}\n"
    )
    board = cfg_to_board(content, "x")
    assert board["objects"][0]["display"] == {
        "mode": "gadget",
        "gadget_type": "gauge",
        "gadget_metric": None,
    }


def test_fixture_textbox_html_stripped(all_objects_board):
    o = _by_id(all_objects_board, "textbox_tb0001")
    assert o["type"] == "textbox"
    label = o["label"]
    assert isinstance(label, dict)
    # <b>…</b> and other tags stripped, <br> → \n, &nbsp; → real space
    assert label["text"] == "Hello World\nsecond line"
    # legacy textbox x/y is top-left; OrbVis centers, so x/y shifts by w/2,h/2
    assert (o["x"], o["y"]) == (200 + 150, 820 + 30)


def test_fixture_shape_imports_as_image(all_objects_board):
    o = _by_id(all_objects_board, "image_sh0001")
    assert o["type"] == "image"
    assert o["image_src"] == "std_nagvis.png"


def test_fixture_map_link(all_objects_board):
    o = _by_id(all_objects_board, "map_m00001")
    assert o["type"] == "map"
    assert o["map_name"] == "other-map"


def test_fixture_aggregation(all_objects_board):
    """`define aggr { name=… }` must import as type=aggregation, not be silently dropped."""
    o = _by_id(all_objects_board, "aggregation_ag0001")
    assert o["type"] == "aggregation"
    assert o["aggregation_id"] == "Host localhost"


def test_fixture_url_target_frameset_rewritten_to_blank(all_objects_board):
    o = _by_id(all_objects_board, "service_s00004")
    assert o["url"] == "https://example.com/dashboard"
    # url_target=main is a legacy frameset target → rewritten to _blank
    assert o["url_target"] == "_blank"
