"""Discovery helpers for the cmk.plugins namespace package.

Both perfometer rendering and graph-template / metric metadata loading need
to walk the same ``cmk.plugins.<vendor>.graphing`` subpackages. Centralising
the walk here avoids two near-identical copies drifting out of sync.

``walk_packages`` does not recurse into namespace packages without
``__init__.py`` (e.g. ``collection``), so plugin directories are enumerated
on disk directly.
"""

from __future__ import annotations

import importlib
import pkgutil
import types
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_plugin_dirs() -> set[Path]:
    """Return all cmk.plugins sub-package directories."""
    try:
        import cmk.plugins as _p
    except ImportError:
        return set()
    dirs: set[Path] = set()
    for p in _p.__path__:
        try:
            dirs.update(d for d in Path(p).iterdir() if d.is_dir())
        except OSError:
            pass
    return dirs


def iter_graphing_modules(plugin_dirs: set[Path]) -> Iterator[types.ModuleType]:
    """Yield imported graphing submodules for all plugin directories."""
    for plugin_dir in plugin_dirs:
        graphing_pkg = f"cmk.plugins.{plugin_dir.name}.graphing"
        try:
            graphing_mod = importlib.import_module(graphing_pkg)
        except Exception:
            continue
        for _finder, submod_name, _ispkg in pkgutil.iter_modules(
            graphing_mod.__path__, f"{graphing_pkg}."
        ):
            try:
                yield importlib.import_module(submod_name)
            except Exception:
                continue
