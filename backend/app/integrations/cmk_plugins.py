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
import logging
import pkgutil
import re
import types
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.integrations import checkmk

logger = logging.getLogger(__name__)


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


_EXPRESSION_PLACEHOLDER_RE = re.compile(r"\s*_EXPRESSION:\{[^}]*\}\s*")


def _identity(x: str) -> str:
    # CMK's Title.localize for graphs that embed metric expressions emits raw
    # `_EXPRESSION:{"metric":"…"}` placeholders when no real translator is
    # supplied. Stripping them keeps the legend readable.
    cleaned = _EXPRESSION_PLACEHOLDER_RE.sub(" ", x)
    return " ".join(cleaned.split())


def _extract_quantity_metrics(qty: object) -> Iterator[str]:
    """Recursively yield metric names from a CMK graphing Quantity expression."""
    if isinstance(qty, str):
        yield qty
        return
    # WarningOf, CriticalOf, MinimumOf, MaximumOf — all have .metric_name: str
    metric_name = getattr(qty, "metric_name", None)
    if isinstance(metric_name, str):
        yield metric_name
        return
    # Sum (.summands), Product (.factors)
    for seq_attr in ("summands", "factors"):
        items = getattr(qty, seq_attr, None)
        if items is not None:
            for item in items:
                yield from _extract_quantity_metrics(item)
            return
    # Difference (.minuend + .subtrahend), Fraction (.dividend + .divisor)
    for a_attr, b_attr in (("minuend", "subtrahend"), ("dividend", "divisor")):
        a = getattr(qty, a_attr, None)
        b = getattr(qty, b_attr, None)
        if a is not None and b is not None:
            yield from _extract_quantity_metrics(a)
            yield from _extract_quantity_metrics(b)
            return
    # Constant or unknown — no metric


@dataclass
class CMKGraphingData:
    titles: dict[str, str] = field(default_factory=dict)
    graphs: dict[str, tuple[str, list[str], frozenset[str]]] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    # scale factor per source metric name (0.0 = conflict sentinel → don't scale)
    scales: dict[str, float] = field(default_factory=dict)


@lru_cache(maxsize=1)
def load_cmk_graphing_data() -> CMKGraphingData:
    """Single-pass loader for CMK metric titles, graph templates, unit symbols, and scale factors."""
    if not checkmk.available:
        return CMKGraphingData()
    try:
        from cmk.graphing.v1 import graphs as _gg
        from cmk.graphing.v1 import metrics as _gm
        from cmk.graphing.v1 import translations as _gt
    except ImportError:
        return CMKGraphingData()
    data = CMKGraphingData()
    for mod in iter_graphing_modules(get_plugin_dirs()):
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if attr.startswith("metric_") and isinstance(obj, _gm.Metric):
                try:
                    data.titles[obj.name] = obj.title.localize(_identity)
                    data.units[obj.name] = getattr(obj.unit.notation, "symbol", "")
                except Exception:
                    pass
            elif attr.startswith("graph_") and isinstance(obj, _gg.Graph):
                names = _extract_graph_metric_names(obj)
                if names:
                    try:
                        conflicting: frozenset[str] = frozenset(getattr(obj, "conflicting", ()))
                        data.graphs[obj.name] = (obj.title.localize(_identity), names, conflicting)
                    except Exception:
                        pass
            elif attr.startswith("translation_") and hasattr(obj, "translations"):
                try:
                    for src_metric, trans in obj.translations.items():
                        if src_metric.startswith("~"):
                            continue
                        if isinstance(trans, (_gt.ScaleBy, _gt.RenameToAndScaleBy)):
                            factor = float(trans.factor)
                            if src_metric in data.scales and data.scales[src_metric] != factor:
                                data.scales[src_metric] = 0.0  # conflict: two different factors
                            elif src_metric not in data.scales:
                                data.scales[src_metric] = factor
                except Exception:
                    pass
    logger.debug(
        "Loaded %d CMK metric titles, %d graph templates, %d scale factors",
        len(data.titles),
        len(data.graphs),
        len(data.scales),
    )
    return data


def _extract_graph_metric_names(graph: object) -> list[str]:
    """Extract metric names from compound_lines only (the actual data series).

    Recursively handles complex Quantity expressions (Sum, WarningOf, …).
    simple_lines are excluded — they contain threshold/overlay lines derived
    from compound metrics and would cause false-positive matches.
    """
    seen: set[str] = set()
    names: list[str] = []
    for item in getattr(graph, "compound_lines", ()):
        for name in _extract_quantity_metrics(item):
            if name not in seen:
                seen.add(name)
                names.append(name)
    return names
