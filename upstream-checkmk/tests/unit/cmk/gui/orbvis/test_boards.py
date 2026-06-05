#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.gui.orbvis._boards import BoardSummary, load_board_summaries


@pytest.fixture(name="boards_dir")
def fixture_boards_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cmk.utils.paths, "omd_root", tmp_path)
    directory = tmp_path / "var" / "orbvis" / "boards"
    directory.mkdir(parents=True)
    return directory


def test_load_board_summaries_without_boards_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cmk.utils.paths, "omd_root", tmp_path)
    assert load_board_summaries() == []


def test_load_board_summaries_sorted_by_file_name(boards_dir: Path) -> None:
    (boards_dir / "zz.json").write_text(json.dumps({"name": "zz", "alias": "Last"}))
    (boards_dir / "aa.json").write_text(json.dumps({"name": "aa", "alias": "First"}))

    assert load_board_summaries() == [
        BoardSummary(name="aa", alias="First"),
        BoardSummary(name="zz", alias="Last"),
    ]


def test_load_board_summaries_skips_demo_boards(boards_dir: Path) -> None:
    (boards_dir / "demo.json").write_text("{}")
    (boards_dir / "demo-flow.json").write_text("{}")
    (boards_dir / "demolition.json").write_text("{}")

    assert load_board_summaries() == [BoardSummary(name="demolition", alias="demolition")]


def test_load_board_summaries_falls_back_to_name_as_alias(boards_dir: Path) -> None:
    (boards_dir / "network.json").write_text(json.dumps({"name": "network"}))

    assert load_board_summaries() == [BoardSummary(name="network", alias="network")]


def test_load_board_summaries_falls_back_to_file_stem(boards_dir: Path) -> None:
    (boards_dir / "broken.json").write_text("not json")
    (boards_dir / "scalar.json").write_text(json.dumps([1, 2, 3]))

    assert load_board_summaries() == [
        BoardSummary(name="broken", alias="broken"),
        BoardSummary(name="scalar", alias="scalar"),
    ]
