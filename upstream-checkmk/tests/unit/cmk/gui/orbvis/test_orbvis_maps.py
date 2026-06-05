#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.gui.config import active_config
from cmk.gui.logged_in import user
from cmk.gui.orbvis import _orbvis_maps
from cmk.gui.orbvis._orbvis_maps import OrbVisBoards
from cmk.gui.utils.output_funnel import output_funnel


@pytest.fixture(name="site_root")
def fixture_site_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cmk.utils.paths, "omd_root", tmp_path)
    return tmp_path


@pytest.fixture(name="local_install")
def fixture_local_install(site_root: Path) -> None:
    marker = site_root / "etc" / "apache" / "conf.d" / "orbvis.conf"
    marker.parent.mkdir(parents=True)
    marker.touch()


@pytest.fixture(name="boards_dir")
def fixture_boards_dir(site_root: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(_orbvis_maps, "declare_board_permissions", lambda: None)
    directory = site_root / "var" / "orbvis" / "boards"
    directory.mkdir(parents=True)
    return directory


def _show_snapin() -> str:
    with output_funnel.plugged():
        OrbVisBoards().show(active_config)
        return "".join(output_funnel.drain())


def test_type_name() -> None:
    assert OrbVisBoards.type_name() == "orbvis_boards"


def test_title() -> None:
    assert OrbVisBoards.title() == "OrbVis boards"


def test_description() -> None:
    assert OrbVisBoards.description() == "List of available OrbVis boards"


def test_refresh_regularly() -> None:
    assert OrbVisBoards.refresh_regularly() is False


def test_is_local_install(site_root: Path, local_install: None) -> None:
    assert _orbvis_maps._is_local_install() is True


def test_is_no_local_install(site_root: Path) -> None:
    assert _orbvis_maps._is_local_install() is False


@pytest.mark.usefixtures("request_context")
@pytest.mark.parametrize(
    "permissions,expected",
    [
        (set(), False),
        ({"orbvis.use"}, False),
        ({"orbvis.view_all", "orbvis.view_network"}, False),
        ({"orbvis.use", "orbvis.view_all"}, True),
        ({"orbvis.use", "orbvis.view_network"}, True),
        ({"orbvis.use", "orbvis.view_other"}, False),
    ],
)
def test_user_may_view_board(
    monkeypatch: pytest.MonkeyPatch, permissions: set[str], expected: bool
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda permission_name: permission_name in permissions)
        assert _orbvis_maps._user_may_view_board("network") is expected


@pytest.mark.usefixtures("request_context")
def test_show_without_local_install(site_root: Path) -> None:
    rendered = _show_snapin()
    assert "OrbVis is not set up on this site." in rendered
    assert "footnotelink" not in rendered


@pytest.mark.usefixtures("request_context", "local_install")
def test_show_without_boards(boards_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda permission_name: True)
        rendered = _show_snapin()

    assert "No OrbVis boards found." in rendered
    assert "Open OrbVis" in rendered


@pytest.mark.usefixtures("request_context", "local_install")
def test_show_board_links(boards_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (boards_dir / "network.json").write_text(
        json.dumps({"name": "network", "alias": "Network overview"})
    )

    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda permission_name: True)
        rendered = _show_snapin()

    assert "Network overview" in rendered
    assert "../orbvis/#/boards/network" in rendered
    assert "Open OrbVis" in rendered


@pytest.mark.usefixtures("request_context", "local_install")
def test_show_filters_unpermitted_boards(boards_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (boards_dir / "network.json").write_text(json.dumps({"name": "network"}))
    (boards_dir / "flow.json").write_text(json.dumps({"name": "flow"}))

    with monkeypatch.context() as m:
        m.setattr(
            user,
            "may",
            lambda permission_name: permission_name in {"orbvis.use", "orbvis.view_network"},
        )
        rendered = _show_snapin()

    assert "../orbvis/#/boards/network" in rendered
    assert "../orbvis/#/boards/flow" not in rendered
