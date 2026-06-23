#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable
from pathlib import Path

import pytest

import cmk.gui.permissions
import cmk.utils.paths
from cmk.gui.orbvis import _orbvis_auth
from cmk.gui.permissions import PermissionRegistry, PermissionSectionRegistry


def test_register(monkeypatch: pytest.MonkeyPatch) -> None:
    section_registry = PermissionSectionRegistry()
    registry = PermissionRegistry()
    dynamic_declarations: list[Callable[[], None]] = []
    monkeypatch.setattr(_orbvis_auth, "declare_dynamic_permissions", dynamic_declarations.append)

    _orbvis_auth.register(section_registry, registry)

    assert section_registry["orbvis"].title == "Maps"
    assert sorted(registry.keys()) == [
        "orbvis.configure",
        "orbvis.edit_all",
        "orbvis.use",
        "orbvis.view_all",
    ]
    assert list(registry["orbvis.use"].defaults) == ["admin", "user"]
    assert list(registry["orbvis.view_all"].defaults) == ["admin", "user"]
    assert list(registry["orbvis.edit_all"].defaults) == ["admin"]
    assert list(registry["orbvis.configure"].defaults) == ["admin"]
    assert dynamic_declarations == [_orbvis_auth.declare_map_permissions]


@pytest.fixture(name="permission_registry")
def fixture_permission_registry(monkeypatch: pytest.MonkeyPatch) -> PermissionRegistry:
    """Isolate the global registries the dynamic permission declaration writes to"""
    section_registry = PermissionSectionRegistry()
    registry = PermissionRegistry()
    monkeypatch.setattr(cmk.gui.permissions, "permission_section_registry", section_registry)
    monkeypatch.setattr(cmk.gui.permissions, "permission_registry", registry)
    monkeypatch.setattr(_orbvis_auth, "permission_registry", registry)
    monkeypatch.setattr(_orbvis_auth, "_declared_map_permissions", set())
    section_registry.register(_orbvis_auth.PERMISSION_SECTION_ORBVIS)
    return registry


@pytest.fixture(name="maps_dir")
def fixture_maps_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cmk.utils.paths, "omd_root", tmp_path)
    directory = tmp_path / "var" / "orbvis" / "maps"
    directory.mkdir(parents=True)
    return directory


def test_declare_map_permissions(permission_registry: PermissionRegistry, maps_dir: Path) -> None:
    (maps_dir / "network.json").write_text(
        json.dumps({"name": "network", "alias": "Network overview"})
    )
    (maps_dir / "demo-flow.json").write_text("{}")

    _orbvis_auth.declare_map_permissions()

    assert sorted(permission_registry.keys()) == [
        "orbvis.edit_network",
        "orbvis.view_network",
    ]
    view_permission = permission_registry["orbvis.view_network"]
    assert view_permission.title == "View map 'Network overview'"
    assert list(view_permission.defaults) == ["admin", "user"]
    edit_permission = permission_registry["orbvis.edit_network"]
    assert edit_permission.title == "Edit map 'Network overview'"
    assert list(edit_permission.defaults) == ["admin"]


def test_declare_map_permissions_drops_deleted_maps(
    permission_registry: PermissionRegistry, maps_dir: Path
) -> None:
    map_path = maps_dir / "network.json"
    map_path.write_text("{}")
    (maps_dir / "flow.json").write_text("{}")

    _orbvis_auth.declare_map_permissions()
    assert "orbvis.view_network" in permission_registry

    map_path.unlink()
    _orbvis_auth.declare_map_permissions()

    assert sorted(permission_registry.keys()) == [
        "orbvis.edit_flow",
        "orbvis.view_flow",
    ]
