"""Unit tests for the cfg_importer tool."""

import json
import textwrap
from pathlib import Path

import pytest

from cfg_importer import blocks_to_map_json, convert_file, parse_cfg_file


SAMPLE_CFG = textwrap.dedent("""
    define global {
        alias=Demo Overview
        map_image=demo-overview.png
        backend_id=live_1
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
        line_type=10
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


def test_blocks_to_map_json():
    from io import StringIO
    import sys

    tmp = Path("/tmp/test_map.cfg")
    tmp.write_text(SAMPLE_CFG)
    blocks = parse_cfg_file(tmp)
    result = blocks_to_map_json(blocks, "test_map")

    assert result["name"] == "test_map"
    assert result["globals"]["alias"] == "Demo Overview"
    assert result["globals"]["background_image"] == "demo-overview.png"
    assert result["globals"]["backend_id"] == "live_1"
    assert len(result["objects"]) == 4  # host, service, hostgroup, line

    host_obj = next(o for o in result["objects"] if o["type"] == "host")
    assert host_obj["host_name"] == "localhost"
    assert host_obj["x"] == 100
    assert host_obj["y"] == 200

    service_obj = next(o for o in result["objects"] if o["type"] == "service")
    assert service_obj["service_description"] == "HTTP"

    line_obj = next(o for o in result["objects"] if o["type"] == "line")
    assert line_obj["extra"]["x2"] == 300
    assert line_obj["extra"]["y2"] == 200


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
    result = blocks_to_map_json(blocks, "styling")
    obj = result["objects"][0]
    assert obj["label_x"] == -5
    assert obj["label_y"] == 12
    assert obj["label_size"] == 14
    assert obj["label_color"] == "#ff0000"
    assert obj["label_background"] == "#000000"
    assert obj["url"] == "http://example.com/host"
    assert obj["url_target"] == "_self"


def test_textbox_text(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define textbox {
            x=50
            y=50
            text=Hello NagVis World
            object_id=1
        }
    """)
    cfg = tmp_path / "textbox.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_map_json(blocks, "textbox")
    obj = result["objects"][0]
    assert obj["type"] == "textbox"
    assert obj["label_text"] == "Hello NagVis World"


def test_relative_coords(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        define host {
            host_name=srv1
            x=123%10
            y=456%-20
            object_id=1
        }
    """)
    cfg = tmp_path / "relcoords.cfg"
    cfg.write_text(cfg_text)
    blocks = parse_cfg_file(cfg)
    result = blocks_to_map_json(blocks, "relcoords")
    obj = result["objects"][0]
    # Offset values are used as best-effort position
    assert obj["x"] == 10
    assert obj["y"] == -20
    # Original strings preserved in extra
    assert obj["extra"]["x_orig"] == "123%10"
    assert obj["extra"]["y_orig"] == "456%-20"


def test_comment_handling(tmp_path: Path):
    cfg_text = textwrap.dedent("""
        # This is a comment
        define global {
            alias=Test ; inline comment
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
