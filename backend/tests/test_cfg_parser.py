"""Tests for the legacy .cfg map parser."""

from __future__ import annotations

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
    content = (
        "define line {\n"
        "    object_id = 4\n"
        "    x = 10,20\n"
        "    y = 30,40\n"
        "    line_type = 20\n"
        "    host_name = router1\n"
        "    service_description = Traffic\n"
        "}\n"
    )
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["id"] == "line_4"
    assert obj["type"] == "line"
    assert obj["line_style"] == "weathermap"
    assert obj["host_name"] == "router1"
    assert obj["service_description"] == "Traffic"


def test_cfg_to_board_line_plain_no_host():
    content = "define line {\n    x = 0,10\n    y = 0,10\n    line_type = 10\n}\n"
    board = cfg_to_board(content, "test")
    obj = board["objects"][0]
    assert obj["line_style"] == "plain"
    assert "host_name" not in obj


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
