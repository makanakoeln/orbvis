#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest

from cmk.gui.orbvis import _monitor_menu
from cmk.gui.orbvis._maps import MapSummary
from cmk.gui.utils.roles import UserPermissions

# orbvis_monitor_topics reads identity from the module-global ``user`` and
# ignores its UserPermissions argument, so a placeholder is enough.
_PERMS = cast(UserPermissions, None)


class _FakeUser:
    def __init__(self, allowed: set[str]) -> None:
        self._allowed = allowed

    def may(self, permission: str) -> bool:
        return permission in self._allowed


def _patch(monkeypatch: pytest.MonkeyPatch, allowed: set[str], summaries: list[MapSummary]) -> None:
    monkeypatch.setattr(_monitor_menu, "user", _FakeUser(allowed))
    monkeypatch.setattr(_monitor_menu, "load_map_summaries", lambda: summaries)
    monkeypatch.setattr(_monitor_menu, "declare_map_permissions", lambda: None)


def test_no_topic_without_use_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, set(), [MapSummary(name="net", alias="Network")])
    assert _monitor_menu.orbvis_monitor_topics(_PERMS) == []


def test_no_topic_when_no_map_is_viewable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, {"orbvis.use"}, [MapSummary(name="net", alias="Network")])
    assert _monitor_menu.orbvis_monitor_topics(_PERMS) == []


def test_view_all_lists_every_map_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    summaries = [MapSummary(name="net", alias="Network"), MapSummary(name="dc", alias="Datacenter")]
    _patch(monkeypatch, {"orbvis.use", "orbvis.view_all"}, summaries)

    topics = _monitor_menu.orbvis_monitor_topics(_PERMS)

    assert len(topics) == 1
    assert topics[0].title == "Maps"
    assert [e.url for e in topics[0].entries] == [
        "orbvis.py#/maps/net",
        "orbvis.py#/maps/dc",
    ]


def test_per_map_permission_filters_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    summaries = [MapSummary(name="net", alias="Network"), MapSummary(name="dc", alias="Datacenter")]
    _patch(monkeypatch, {"orbvis.use", "orbvis.view_net"}, summaries)

    topics = _monitor_menu.orbvis_monitor_topics(_PERMS)

    assert len(topics) == 1
    assert [e.id for e in topics[0].entries] == ["orbvis_map_net"]
