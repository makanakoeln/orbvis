#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.gui.orbvis._maps import load_map_summaries, MapSummary


@pytest.fixture(name="maps_dir")
def fixture_maps_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cmk.utils.paths, "omd_root", tmp_path)
    directory = tmp_path / "var" / "orbvis" / "maps"
    directory.mkdir(parents=True)
    return directory


def test_load_map_summaries_without_maps_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cmk.utils.paths, "omd_root", tmp_path)
    assert load_map_summaries() == []


def test_load_map_summaries_sorted_by_file_name(maps_dir: Path) -> None:
    (maps_dir / "zz.json").write_text(json.dumps({"name": "zz", "alias": "Last"}))
    (maps_dir / "aa.json").write_text(json.dumps({"name": "aa", "alias": "First"}))

    assert load_map_summaries() == [
        MapSummary(name="aa", alias="First"),
        MapSummary(name="zz", alias="Last"),
    ]


def test_load_map_summaries_skips_demo_maps(maps_dir: Path) -> None:
    (maps_dir / "demo.json").write_text("{}")
    (maps_dir / "demo-flow.json").write_text("{}")
    (maps_dir / "demolition.json").write_text("{}")

    assert load_map_summaries() == [MapSummary(name="demolition", alias="demolition")]


def test_load_map_summaries_falls_back_to_name_as_alias(maps_dir: Path) -> None:
    (maps_dir / "network.json").write_text(json.dumps({"name": "network"}))

    assert load_map_summaries() == [MapSummary(name="network", alias="network")]


def test_load_map_summaries_falls_back_to_file_stem(maps_dir: Path) -> None:
    (maps_dir / "broken.json").write_text("not json")
    (maps_dir / "scalar.json").write_text(json.dumps([1, 2, 3]))

    assert load_map_summaries() == [
        MapSummary(name="broken", alias="broken"),
        MapSummary(name="scalar", alias="scalar"),
    ]
