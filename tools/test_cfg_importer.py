"""Unit tests for the cfg_importer tool."""

import json
import textwrap
from pathlib import Path

from cfg_importer import blocks_to_board_json, convert_file, parse_cfg_file

SAMPLE_CFG = textwrap.dedent("""
    define global {
        alias=Demo Overview
        map_image=demo-overview.png
        connection_id=live_1
    }

    define host {
        host_name=localhost
        x=100
        y=200
        label_show=1
        object_id=1
    }

    define service {
        host_name=localhost
        service_description=HTTP
        x=300
        y=200
        label_show=1
        object_id=2
    }

    define hostgroup {
        hostgroup_name=web-servers
        x=500
        y=100
        object_id=3
    }

    define line {
        x=100
        y=200
        x2=300
        y2=200
        line_type=12
        object_id=4
    }
""")


def test_parse_cfg_file(tmp_path: Path):
    cfg = tmp_path / "test.cfg"
    cfg.write_text(SAMPLE_CFG)
    blocks = parse_cfg_file(cfg)
    assert len(blocks) == 5
    types = [b.block_type for b in blocks]
    assert "global" in types
    assert "host" in types
    assert "service" in types
    assert "hostgroup" in types
    assert "line" in types


def test_blocks_to_board_json(tmp_path: Path):
    cfg = tmp_path / "test_map.cfg"
    cfg.write_text(SAMPLE_CFG)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "test_map")

    assert result["name"] == "test_map"
    assert result["alias"] == "Demo Overview"
    assert result["background_image"] == "demo-overview.png"
    assert result["connection_id"] == "live_1"
    assert len(result["objects"]) == 4  # host, service, hostgroup, line

    host_obj = next(o for o in result["objects"] if o["type"] == "host")
    assert host_obj["host_name"] == "localhost"
    assert host_obj["x"] == 100
    assert host_obj["y"] == 200

    service_obj = next(o for o in result["objects"] if o["type"] == "service")
    assert service_obj["service_description"] == "HTTP"

    line_obj = next(o for o in result["objects"] if o["type"] == "line")
    assert line_obj["x2"] == 300
    assert line_obj["y2"] == 200
    assert line_obj["line_style"] == "plain"


def test_convert_file(tmp_path: Path):
    cfg = tmp_path / "demo.cfg"
    cfg.write_text(SAMPLE_CFG)
    output_dir = tmp_path / "maps"
    out = convert_file(cfg, output_dir)
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["name"] == "demo"
    assert len(data["objects"]) == 4


def test_label_styling_and_url(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define host {
            host_name=srv1
            x=10
            y=20
            label_x=-5
            label_y=12
            label_size=14
            label_color=#ff0000
            label_background=#000000
            url=http://example.com/host
            url_target=_self
            object_id=1
        }
    """)
    cfg = tmp_path / "styling.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "styling")
    obj = result["objects"][0]
    assert obj["label"]["x"] == -5
    assert obj["label"]["y"] == 12
    assert obj["label"]["size"] == 14
    assert obj["label"]["color"] == "#ff0000"
    assert obj["label"]["background"] == "#000000"
    assert obj["url"] == "http://example.com/host"
    assert obj["url_target"] == "_self"


def test_textbox_text(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define textbox {
            x=50
            y=50
            text=Hello OrbVis World
            object_id=1
        }
    """)
    cfg = tmp_path / "textbox.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "textbox")
    obj = result["objects"][0]
    assert obj["type"] == "textbox"
    assert obj["label"]["text"] == "Hello OrbVis World"


def test_relative_coords_resolve_to_referenced_object(tmp_path: Path):
    # NagVis encodes "linked" lines as ``<object_id>%<offset>`` so the line
    # endpoints follow the referenced host. The importer indexes objects by
    # their NagVis object_id and resolves each relative coord to
    # ``<target_coord> + <offset>`` in a second pass.
    cfg_text = textwrap.dedent("""
        define host {
            host_name=anchor
            x=400
            y=200
            object_id=anchor1
        }
        define line {
            object_id=l1
            x=anchor1%5,500
            y=anchor1%-10,200
            line_type=12
        }
    """)
    cfg = tmp_path / "relcoords.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "relcoords")
    line_obj = next(o for o in result["objects"] if o["type"] == "line")
    assert line_obj["x"] == 405  # 400 + 5
    assert line_obj["y"] == 190  # 200 - 10
    assert line_obj["x2"] == 500
    assert line_obj["y2"] == 200
    # internal scaffolding must not leak into the output
    assert "_pending_refs" not in line_obj


def test_relative_coords_unresolvable_falls_back_to_offset(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define host {
            host_name=srv1
            x=missing%10
            y=ghost%-20
            object_id=1
        }
    """)
    cfg = tmp_path / "rel-broken.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "rel-broken")
    obj = result["objects"][0]
    assert obj["x"] == 10
    assert obj["y"] == -20
    assert "_pending_refs" not in obj


def test_z_index_defaults_match_nagvis(tmp_path: Path):
    # NagVis defaults: stateful objects 10, textbox 5, shape 1, line 0.
    cfg_text = textwrap.dedent("""
        define host {
            host_name=h1
            x=10
            y=10
            object_id=h
        }
        define textbox {
            text=hi
            x=20
            y=20
            object_id=t
        }
        define shape {
            icon=foo.png
            x=30
            y=30
            object_id=s
        }
        define line {
            x=40,50
            y=40,50
            line_type=12
            object_id=l
        }
    """)
    cfg = tmp_path / "z.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "z")
    by_type = {o["type"]: o for o in result["objects"]}
    assert by_type["host"]["z"] == 10
    assert by_type["textbox"]["z"] == 5
    assert by_type["image"]["z"] == 1
    assert by_type["line"]["z"] == 0


def test_textbox_auto_size_does_not_shift_position(tmp_path: Path):
    # ``w=auto`` (the NagVis default) means the renderer sizes the box, so we
    # must leave textbox_width unset and skip the half-width center offset.
    cfg_text = textwrap.dedent("""
        define textbox {
            text=hello
            x=100
            y=200
            w=auto
            h=auto
            object_id=t
        }
    """)
    cfg = tmp_path / "tb-auto.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    obj = blocks_to_board_json(blocks, "tb-auto")["objects"][0]
    assert obj["x"] == 100
    assert obj["y"] == 200
    assert "textbox_width" not in obj
    assert "textbox_height" not in obj


def test_textbox_numeric_size_shifts_to_center_and_persists(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define textbox {
            text=hello
            x=100
            y=200
            w=300
            h=40
            background_color=#222222
            border_color=transparent
            object_id=t
        }
    """)
    cfg = tmp_path / "tb-num.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    obj = blocks_to_board_json(blocks, "tb-num")["objects"][0]
    assert obj["textbox_width"] == 300
    assert obj["textbox_height"] == 40
    assert obj["x"] == 250  # 100 + 300/2
    assert obj["y"] == 220  # 200 + 40/2
    assert obj["textbox_background"] == "#222222"
    assert obj["textbox_border"] == "transparent"


def test_label_style_css_is_parsed(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define service {
            host_name=h1
            service_description=cpu
            x=10
            y=20
            label_show=1
            label_text=[service_description]
            label_style=color:#abcdef;font-size:18px;font-weight:bold
            object_id=1
        }
    """)
    cfg = tmp_path / "label-style.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    obj = blocks_to_board_json(blocks, "label-style")["objects"][0]
    assert obj["label"]["color"] == "#abcdef"
    assert obj["label"]["size"] == 18


def test_label_color_explicit_wins_over_style(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define service {
            host_name=h1
            service_description=cpu
            x=10
            y=20
            label_show=1
            label_color=#ff0000
            label_style=color:#0000ff
            object_id=1
        }
    """)
    cfg = tmp_path / "label-explicit.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    obj = blocks_to_board_json(blocks, "label-explicit")["objects"][0]
    assert obj["label"]["color"] == "#ff0000"


def test_line_label_imported(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define line {
            x=10,20
            y=30,40
            line_type=12
            label_show=1
            label_text=Trunk A
            object_id=l1
        }
    """)
    cfg = tmp_path / "line-label.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    obj = blocks_to_board_json(blocks, "line-label")["objects"][0]
    assert obj["label"]["show"] is True
    assert obj["label"]["text"] == "Trunk A"


def test_line_without_label_stays_hidden(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define line {
            x=10,20
            y=30,40
            line_type=12
            object_id=l1
        }
    """)
    cfg = tmp_path / "line-nolabel.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    obj = blocks_to_board_json(blocks, "line-nolabel")["objects"][0]
    assert obj["label"]["show"] is False


def test_per_object_backend_imported_when_differs(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define global {
            backend_id=primary
        }
        define host {
            host_name=local
            x=10
            y=20
            object_id=h1
        }
        define host {
            host_name=remote
            backend_id=secondary
            x=40
            y=20
            object_id=h2
        }
    """)
    cfg = tmp_path / "multi-backend.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "multi-backend")
    assert result["connection_id"] == "primary"
    by_host = {o["host_name"]: o for o in result["objects"] if o["type"] == "host"}
    assert "connection_id" not in by_host["local"]  # inherits board default
    assert by_host["remote"]["connection_id"] == "secondary"


def test_background_color_imported(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define global {
            alias=Demo
            background_color=#e8e8e8
        }
    """)
    cfg = tmp_path / "bg.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "bg")
    assert result["background_color"] == "#e8e8e8"


def test_gadget_speedometer(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define service {
            host_name=srv1
            service_description=CPU load
            x=100
            y=100
            view_type=gadget
            gadget_url=std_speedometer.php
            object_id=1
        }
    """)
    cfg = tmp_path / "gadget.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "gadget")
    obj = result["objects"][0]
    assert obj["display"]["mode"] == "gadget"
    assert obj["display"]["gadget_type"] == "gauge"
    assert obj["display"]["gadget_metric"] is None


def test_gadget_bar_variants(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define service {
            host_name=srv1
            service_description=Bandwidth
            x=10
            y=10
            view_type=gadget
            gadget_url=std_bar.php
            object_id=1
        }
        define service {
            host_name=srv1
            service_description=Bandwidth
            x=20
            y=20
            view_type=gadget
            gadget_url=std_html_bar.php
            object_id=2
        }
    """)
    cfg = tmp_path / "bars.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "bars")
    for obj in result["objects"]:
        assert obj["display"]["mode"] == "gadget"
        assert obj["display"]["gadget_type"] == "bar"


def test_gadget_unknown_falls_back_with_warning(tmp_path: Path, capsys):
    cfg_text = textwrap.dedent("""
        define service {
            host_name=srv1
            service_description=Custom
            x=10
            y=10
            view_type=gadget
            gadget_url=my_custom_gadget.php
            object_id=42
        }
    """)
    cfg = tmp_path / "custom.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "custom")
    obj = result["objects"][0]
    # Unknown gadget_url falls back to icon, OrbVis renders a normal service icon
    assert obj["display"]["mode"] == "icon"
    assert "gadget_type" not in obj["display"]
    # Warning is emitted on stderr with object identifier and the offending url
    captured = capsys.readouterr()
    assert "service 42" in captured.err
    assert "my_custom_gadget.php" in captured.err


def test_aggr_object(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define aggr {
            aggr_name=Servers
            aggr_url=http://cmk/site/check_mk/view.py?view_name=aggr_single&aggr_name=Servers
            x=100
            y=120
            object_id=42
        }
    """)
    cfg = tmp_path / "aggr.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_board_json(blocks, "aggr")
    obj = result["objects"][0]
    assert obj["type"] == "aggregation"
    assert obj["aggregation_id"] == "Servers"
    assert obj["url"].endswith("aggr_name=Servers")


def test_comment_handling(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        # This is a comment
        define global {
            alias=Test
        }
        define host {
            host_name=server1
            x=10
            y=20
            object_id=1
        }
    """)
    cfg = tmp_path / "commented.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    assert len(blocks) == 2
    global_block = next(b for b in blocks if b.block_type == "global")
    assert global_block.properties["alias"] == "Test"
