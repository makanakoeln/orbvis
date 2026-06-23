#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

import cmk.utils.paths
from cmk.gui.orbvis._pages import _collect_stylesheets, _load_manifest


def test_collect_stylesheets_walks_imports_before_own_css() -> None:
    manifest = {
        "src/main.ts": {"file": "main.js", "css": ["main.css"], "imports": ["_dep.js"]},
        "_dep.js": {"file": "dep.js", "css": ["dep.css"]},
    }
    # imported stylesheets first, then the entry's own
    assert _collect_stylesheets(manifest, "src/main.ts") == ["dep.css", "main.css"]


def test_collect_stylesheets_deduplicates_shared_css() -> None:
    manifest = {
        "src/main.ts": {"file": "main.js", "imports": ["_a.js", "_b.js"]},
        "_a.js": {"file": "a.js", "css": ["shared.css"]},
        "_b.js": {"file": "b.js", "css": ["shared.css"]},
    }
    assert _collect_stylesheets(manifest, "src/main.ts") == ["shared.css"]


def test_collect_stylesheets_survives_import_cycle() -> None:
    manifest = {
        "src/main.ts": {"file": "main.js", "css": ["main.css"], "imports": ["_a.js"]},
        "_a.js": {"file": "a.js", "css": ["a.css"], "imports": ["src/main.ts"]},
    }
    # the _seen guard breaks the cycle instead of recursing forever
    assert sorted(_collect_stylesheets(manifest, "src/main.ts")) == ["a.css", "main.css"]


def test_load_manifest_resolves_entry_and_styles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cmk.utils.paths, "web_dir", tmp_path)
    bundle = tmp_path / "htdocs" / "cmk-orbvis-frontend"
    bundle.mkdir(parents=True)
    (bundle / ".manifest.json").write_text(
        json.dumps({"src/main.ts": {"file": "assets/main-abc.js", "css": ["assets/main-abc.css"]}})
    )
    _load_manifest.cache_clear()
    try:
        manifest = _load_manifest()
        assert manifest.main == "cmk-orbvis-frontend/assets/main-abc.js"
        assert manifest.stylesheets == ["assets/main-abc.css"]
    finally:
        _load_manifest.cache_clear()
