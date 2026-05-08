"""CMK perfometer computation using cmk.graphing.v1 plugin definitions."""

from __future__ import annotations

import importlib
import logging
import pkgutil
import re
import types
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public result types
# ---------------------------------------------------------------------------


@dataclass
class PerfometerSegment:
    pct: float  # 0–100
    color: str  # hex, e.g. "#19d379"


@dataclass
class PerfometerResult:
    label: str
    rows: list[list[PerfometerSegment]]  # 1 row for simple, 2 for stacked/bidirectional
    pcts: list[
        float
    ]  # raw side percentages: [pct] simple, [left, right] bi, [lower, upper] stacked


# ---------------------------------------------------------------------------
# Raw perf_data parser (Nagios format)
# ---------------------------------------------------------------------------

_PERF_RE = re.compile(r"(?:'[^']+'|[^\s]+)=[^\s]*")


@dataclass
class _RawMetric:
    value: float
    unit: str
    warn: float | None
    crit: float | None
    min: float | None
    max: float | None


def _parse_perf_data(raw: str) -> dict[str, _RawMetric]:
    result: dict[str, _RawMetric] = {}
    for part in _PERF_RE.findall(raw):
        eq = part.index("=")
        label = part[:eq].strip("'")
        rest = part[eq + 1 :]
        val_str, *rest_parts = rest.split(";")
        m = re.match(r"^(-?[\d.]+)([a-zA-Z%]*)", val_str)
        if not m:
            continue

        def _n(s: str | None) -> float | None:
            return float(s) if s is not None and s != "" else None

        result[label] = _RawMetric(
            value=float(m.group(1)),
            unit=m.group(2),
            warn=_n(rest_parts[0] if len(rest_parts) > 0 else None),
            crit=_n(rest_parts[1] if len(rest_parts) > 1 else None),
            min=_n(rest_parts[2] if len(rest_parts) > 2 else None),
            max=_n(rest_parts[3] if len(rest_parts) > 3 else None),
        )
    return result


# ---------------------------------------------------------------------------
# Plugin loading
# ---------------------------------------------------------------------------


@dataclass
class _PluginData:
    # canonical_metric_name → (value, unit, warn, crit) after translation
    # perfometers: list of (Perfometer | Bidirectional | Stacked)
    # Perfometer / Bidirectional / Stacked instances from cmk.graphing.v1 (untyped from mypy's view)
    perfometers: list[object] = field(default_factory=list)
    # check_plugin_name → {raw_metric_name → canonical_name}
    renames: dict[str, dict[str, str]] = field(default_factory=dict)
    # check_plugin_name → {raw_metric_name → scale_factor}
    scales: dict[str, dict[str, float]] = field(default_factory=dict)
    # metric_name → (notation_type_name, symbol) for formatting
    units: dict[str, tuple[str, str]] = field(default_factory=dict)
    # metric_name → Color enum member name (e.g. "GREEN", "BLUE")
    colors: dict[str, str] = field(default_factory=dict)


# Mapping from cmk.graphing.v1.metrics.Color enum names → hex strings.
# Mirrors cmk.gui.color.Color so OrbVis renders metrics in the same colors CMK does.
_COLOR_HEX: dict[str, str] = {
    "LIGHT_RED": "#f37c7c",
    "RED": "#ed3b3b",
    "DARK_RED": "#a82a2a",
    "LIGHT_ORANGE": "#ffad54",
    "ORANGE": "#ff8400",
    "DARK_ORANGE": "#b55e00",
    "LIGHT_YELLOW": "#ffe456",
    "YELLOW": "#ffd703",
    "DARK_YELLOW": "#ac7c02",
    "LIGHT_GREEN": "#62e0bf",
    "GREEN": "#15d1a0",
    "DARK_GREEN": "#0f9472",
    "LIGHT_BLUE": "#6fc1f7",
    "BLUE": "#28a2f3",
    "DARK_BLUE": "#1c73ad",
    "LIGHT_CYAN": "#68eeee",
    "CYAN": "#1ee6e6",
    "DARK_CYAN": "#17b5b5",
    "LIGHT_PURPLE": "#acaaff",
    "PURPLE": "#8380ff",
    "DARK_PURPLE": "#5d5bb5",
    "LIGHT_PINK": "#f9a8e2",
    "PINK": "#ec48b6",
    "DARK_PINK": "#be187a",
    "LIGHT_BROWN": "#d4ad84",
    "BROWN": "#bf8548",
    "DARK_BROWN": "#885e33",
    "LIGHT_GRAY": "#acacac",
    "GRAY": "#8c8c8c",
    "DARK_GRAY": "#5d5d5d",
    "BLACK": "#1e262e",
    "WHITE": "#ffffff",
}


def _get_plugin_dirs() -> set[Path]:
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


def _iter_graphing_modules(plugin_dirs: set[Path]) -> Iterator[types.ModuleType]:
    for plugin_dir in plugin_dirs:
        pkg = f"cmk.plugins.{plugin_dir.name}.graphing"
        try:
            mod = importlib.import_module(pkg)
        except Exception:
            continue
        for _finder, submod_name, _ispkg in pkgutil.iter_modules(mod.__path__, f"{pkg}."):
            try:
                yield importlib.import_module(submod_name)
            except Exception:
                continue


@lru_cache(maxsize=1)
def _load_plugins() -> _PluginData:
    try:
        from cmk.graphing.v1 import perfometers as pf_api
    except ImportError:
        logger.debug("cmk.graphing.v1 not available — perfometer feature disabled")
        return _PluginData()

    data = _PluginData()
    plugin_dirs = _get_plugin_dirs()
    if not plugin_dirs:
        logger.debug("No cmk.plugins directories found")
        return data

    for mod in _iter_graphing_modules(plugin_dirs):
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if attr.startswith("perfometer_") and isinstance(
                obj, (pf_api.Perfometer, pf_api.Bidirectional, pf_api.Stacked)
            ):
                data.perfometers.append(obj)
            elif (
                attr.startswith("metric_")
                and hasattr(obj, "name")
                and hasattr(obj, "unit")
                and hasattr(obj.unit, "notation")
            ):
                notation = obj.unit.notation
                data.units[obj.name] = (
                    type(notation).__name__,
                    getattr(notation, "symbol", ""),
                )
                color = getattr(obj, "color", None)
                if color is not None and hasattr(color, "name"):
                    data.colors[obj.name] = color.name
            elif (
                attr.startswith("translation_")
                and hasattr(obj, "translations")
                and hasattr(obj, "check_commands")
            ):
                for cmd in obj.check_commands:
                    name = getattr(cmd, "name", None)
                    if not name:
                        continue
                    rn = data.renames.setdefault(name, {})
                    sc = data.scales.setdefault(name, {})
                    for src, rule in obj.translations.items():
                        if src.startswith("~"):
                            continue
                        target = getattr(rule, "metric_name", src)
                        factor = float(getattr(rule, "factor", 1.0))
                        if target != src:
                            rn[src] = target
                        if factor != 1.0:
                            sc[src] = factor

    logger.debug(
        "Loaded %d perfometer definitions, %d translation sets",
        len(data.perfometers),
        len(data.renames),
    )
    return data


# ---------------------------------------------------------------------------
# Translation + metric resolution
# ---------------------------------------------------------------------------


def _check_plugin_name(check_command: str) -> str:
    """Extract plugin name from a Livestatus check_command string.

    'check_mk-cpu_loads' → 'cpu_loads'
    'check_mk_active-http' → 'http'
    'check-host-alive' → ''
    """
    if check_command.startswith("check_mk-"):
        return check_command[len("check_mk-") :]
    if check_command.startswith("check_mk_active-"):
        return check_command[len("check_mk_active-") :]
    return ""


def _apply_translations(
    raw: dict[str, _RawMetric],
    check_command: str,
    plugins: _PluginData,
) -> dict[str, _RawMetric]:
    plugin_name = _check_plugin_name(check_command)
    if not plugin_name:
        return raw
    renames = plugins.renames.get(plugin_name, {})
    scales = plugins.scales.get(plugin_name, {})
    if not renames and not scales:
        return raw
    result: dict[str, _RawMetric] = {}
    for src_name, metric in raw.items():
        target_name = renames.get(src_name, src_name)
        factor = scales.get(src_name, 1.0)
        if factor != 1.0:
            metric = _RawMetric(
                value=metric.value * factor,
                unit=metric.unit,
                warn=metric.warn * factor if metric.warn is not None else None,
                crit=metric.crit * factor if metric.crit is not None else None,
                min=metric.min * factor if metric.min is not None else None,
                max=metric.max * factor if metric.max is not None else None,
            )
        result[target_name] = metric
    return result


# ---------------------------------------------------------------------------
# Perfometer matching and stack computation
# ---------------------------------------------------------------------------


def _get_segment_names(segments: object) -> list[str]:
    """Extract canonical metric names from a perfometer's segments list."""
    names: list[str] = []
    if not isinstance(segments, Iterable) or isinstance(segments, str | bytes):
        return names
    for seg in segments:
        if isinstance(seg, str):
            names.append(seg)
        else:
            # Complex expression — walk known attributes
            for attr in ("metric_name", "summands", "factors"):
                val = getattr(seg, attr, None)
                if val is None:
                    continue
                if isinstance(val, str):
                    names.append(val)
                elif isinstance(val, Iterable):
                    names.extend(_get_segment_names(val))
    return names


def _perfometer_matches(perf: object, metrics: dict[str, _RawMetric]) -> bool:
    """Return True if all required segment metrics are present."""
    try:
        from cmk.graphing.v1 import perfometers as pf_api
    except ImportError:
        return False
    if isinstance(perf, pf_api.Perfometer):
        return all(n in metrics for n in _get_segment_names(perf.segments))
    if isinstance(perf, pf_api.Bidirectional):
        return _perfometer_matches(perf.left, metrics) or _perfometer_matches(perf.right, metrics)
    if isinstance(perf, pf_api.Stacked):
        return _perfometer_matches(perf.lower, metrics) or _perfometer_matches(perf.upper, metrics)
    return False


def _resolve_quantity(q: object, metrics: dict[str, _RawMetric]) -> float:
    """Resolve a cmk.graphing.v1 Quantity (literal, metric-ref, or expression) to a float."""
    if isinstance(q, (int, float)):
        return float(q)
    if isinstance(q, str):
        m = metrics.get(q)
        return m.value if m else 0.0
    try:
        from cmk.graphing.v1 import metrics as m_api
    except ImportError:
        return 0.0
    if isinstance(q, m_api.MaximumOf):
        m = metrics.get(q.metric_name)
        return m.max if m and m.max is not None else 0.0
    if isinstance(q, m_api.MinimumOf):
        m = metrics.get(q.metric_name)
        return m.min if m and m.min is not None else 0.0
    if isinstance(q, m_api.WarningOf):
        m = metrics.get(q.metric_name)
        return m.warn if m and m.warn is not None else 0.0
    if isinstance(q, m_api.CriticalOf):
        m = metrics.get(q.metric_name)
        return m.crit if m and m.crit is not None else 0.0
    if isinstance(q, m_api.Constant):
        return float(q.value)
    if hasattr(q, "summands"):
        return sum(_resolve_quantity(s, metrics) for s in q.summands)
    if hasattr(q, "factors"):
        result = 1.0
        for f in q.factors:
            result *= _resolve_quantity(f, metrics)
        return result
    return 0.0


def _resolve_bound(bound: object, metrics: dict[str, _RawMetric]) -> float:
    value = getattr(bound, "value", None)
    return _resolve_quantity(value, metrics) if value is not None else 0.0


_WARN_HEX = "#ffd000"
_CRIT_HEX = "#ff3232"


def _metric_color(
    metric_name: str,
    m: _RawMetric,
    colors: dict[str, str],
) -> str:
    """Resolve the fill color for a metric.

    Uses the metric's declared color from its Metric() plugin definition.
    Falls back to warn/crit colors when the current value breaches thresholds.
    """
    if m.crit is not None and m.value >= m.crit > 0:
        return _CRIT_HEX
    if m.warn is not None and m.value >= m.warn > 0:
        return _WARN_HEX
    declared = colors.get(metric_name)
    if declared and declared in _COLOR_HEX:
        return _COLOR_HEX[declared]
    return _COLOR_HEX["GREEN"]


_REMAINDER_COLOR = "#52525b"  # zinc-600 — visible on dark glass cards


def _compute_simple_side(
    perf: object,
    metrics: dict[str, _RawMetric],
    colors: dict[str, str],
) -> tuple[float, float, str] | None:
    """Return (raw_pct, segment_pct, color) for a single Perfometer.

    raw_pct is the true [0,100] utilization for label display.
    segment_pct adds a 1% visual floor so non-zero fills don't vanish.
    """
    names = _get_segment_names(getattr(perf, "segments", ()))
    present = [n for n in names if n in metrics]
    if not present:
        return None
    total = sum(metrics[n].value for n in present)
    focus_range = getattr(perf, "focus_range", None)
    if focus_range is None:
        return None
    lower = _resolve_bound(getattr(focus_range, "lower", None), metrics)
    upper = _resolve_bound(getattr(focus_range, "upper", None), metrics)
    if upper <= lower:
        return None
    raw_pct = min(100.0, max(0.0, (total - lower) / (upper - lower) * 100))
    segment_pct = 1.0 if total > 0 and raw_pct < 1.0 else raw_pct
    color = _metric_color(present[0], metrics[present[0]], colors)
    return (round(raw_pct, 2), round(segment_pct, 1), color)


def _compute_simple_row(
    perf: object,
    metrics: dict[str, _RawMetric],
    colors: dict[str, str],
) -> tuple[list[PerfometerSegment], float] | None:
    side = _compute_simple_side(perf, metrics, colors)
    if side is None:
        return None
    raw_pct, segment_pct, color = side
    row = [
        PerfometerSegment(pct=segment_pct, color=color),
        PerfometerSegment(pct=round(100 - segment_pct, 1), color=_REMAINDER_COLOR),
    ]
    return (row, raw_pct)


def _compute_bidirectional_row(
    perf: object,
    metrics: dict[str, _RawMetric],
    colors: dict[str, str],
) -> tuple[list[PerfometerSegment], float, float] | None:
    """Single-row layout: [empty_left, left_fill, right_fill, empty_right], each half = 50%."""
    left = _compute_simple_side(getattr(perf, "left", None), metrics, colors)
    right = _compute_simple_side(getattr(perf, "right", None), metrics, colors)
    if left is None or right is None:
        return None
    left_raw, left_seg, left_color = left
    right_raw, right_seg, right_color = right
    row = [
        PerfometerSegment(pct=round(50 - 50 * left_seg / 100, 1), color=_REMAINDER_COLOR),
        PerfometerSegment(pct=round(50 * left_seg / 100, 1), color=left_color),
        PerfometerSegment(pct=round(50 * right_seg / 100, 1), color=right_color),
        PerfometerSegment(pct=round(50 - 50 * right_seg / 100, 1), color=_REMAINDER_COLOR),
    ]
    return (row, left_raw, right_raw)


def _format_si(value: float, symbol: str) -> str:
    av = abs(value)
    for prefix, factor in (
        ("P", 1e15),
        ("T", 1e12),
        ("G", 1e9),
        ("M", 1e6),
        ("k", 1e3),
    ):
        if av >= factor:
            return _trim(f"{value / factor:.2f}") + f" {prefix}{symbol}"
    if av >= 1 or av == 0:
        return _trim(f"{value:.2f}") + f" {symbol}"
    for prefix, factor in (("m", 1e-3), ("µ", 1e-6), ("n", 1e-9)):
        if av >= factor:
            return _trim(f"{value / factor:.2f}") + f" {prefix}{symbol}"
    return f"{value:.2e} {symbol}"


def _format_iec(value: float, symbol: str) -> str:
    av = abs(value)
    for prefix, factor in (
        ("Pi", 2**50),
        ("Ti", 2**40),
        ("Gi", 2**30),
        ("Mi", 2**20),
        ("Ki", 2**10),
    ):
        if av >= factor:
            return _trim(f"{value / factor:.2f}") + f" {prefix}{symbol}"
    return _trim(f"{value:.2f}") + f" {symbol}"


def _trim(s: str) -> str:
    """Trim trailing zeros after the decimal point: '5.00' → '5', '5.10' → '5.1'."""
    return s.rstrip("0").rstrip(".") if "." in s else s


def _fmt_value(name: str, m: _RawMetric, units: dict[str, tuple[str, str]]) -> str:
    unit_info = units.get(name)
    if unit_info:
        notation_type, symbol = unit_info
        if notation_type == "SINotation":
            return _format_si(m.value, symbol)
        if notation_type == "IECNotation":
            return _format_iec(m.value, symbol)
        if notation_type == "TimeNotation":
            return _format_si(m.value, "s")
        return _trim(f"{m.value:.2f}") + (f" {symbol}" if symbol else "")

    v = m.value
    unit = m.unit
    if unit in ("B", "bytes"):
        for suffix, divisor in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
            if v >= divisor:
                return f"{v / divisor:.1f} {suffix}"
        return f"{v:.0f} B"
    if abs(v) >= 1000:
        return f"{v:,.0f}{unit}"
    if v == int(v):
        return f"{int(v)}{unit}"
    return _trim(f"{v:.2f}") + unit


def _label_from_segments(
    perf: object,
    metrics: dict[str, _RawMetric],
    units: dict[str, tuple[str, str]],
) -> str:
    names = _get_segment_names(getattr(perf, "segments", ()))
    present = [n for n in names if n in metrics]
    if not present:
        return ""
    value = _fmt_value(present[0], metrics[present[0]], units)
    # Prepend the CMK metric title ("RAM usage 53.88 %") so consumers don't
    # have to reach back into the metric registry to label the value. Falls
    # back to just the value when the title isn't registered.
    title = _metric_title(present[0])
    return f"{title} {value}".strip() if title else value


@lru_cache(maxsize=1)
def _metric_title_map() -> dict[str, str]:
    """Map metric name → display title from cmk.plugins.<x>.graphing modules."""
    titles: dict[str, str] = {}
    try:
        from cmk.graphing.v1 import metrics as _gm
    except ImportError:
        return titles
    for mod in _iter_graphing_modules(_get_plugin_dirs()):
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, _gm.Metric):
                try:
                    titles[obj.name] = obj.title.localize(lambda s: s)
                except Exception:
                    pass
    return titles


def _metric_title(name: str) -> str:
    return _metric_title_map().get(name, "")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _superseder_map() -> dict[str, str]:
    """superseded_perfometer_name → superseder_perfometer_name.

    Mirrors cmk.gui.graphing._perfometer_superseding so OrbVis honours the same
    "use the percent perfometer when both bytes and percent metrics are
    present" tie-breaks Checkmk applies (e.g. Memory: mem_used vs mem_used_percent).
    """
    try:
        from cmk.gui.graphing._perfometer_superseding import (
            PERFOMETER_SUPERSEDED_TO_SUPERSEDER,
        )
    except ImportError:
        return {}
    return dict(PERFOMETER_SUPERSEDED_TO_SUPERSEDER)


def compute_perfometer(perf_data_str: str, check_command: str) -> PerfometerResult | None:
    """Compute a CMK-style perfometer stack from raw Nagios perf_data.

    Returns None if no matching perfometer definition is found.
    """
    if not perf_data_str.strip():
        return None

    plugins = _load_plugins()
    if not plugins.perfometers:
        return None

    raw = _parse_perf_data(perf_data_str)
    if not raw:
        return None

    metrics = _apply_translations(raw, check_command, plugins)

    try:
        from cmk.graphing.v1 import perfometers as pf_api
    except ImportError:
        return None

    superseders = _superseder_map()
    matching_names = {
        getattr(p, "name", "") for p in plugins.perfometers if _perfometer_matches(p, metrics)
    }

    for perf_def in plugins.perfometers:
        if not _perfometer_matches(perf_def, metrics):
            continue
        # Skip superseded perfometers when their superseder is also a candidate
        # (e.g. mem_used loses to mem_used_percent on the Linux Memory check).
        superseder = superseders.get(getattr(perf_def, "name", ""))
        if superseder and superseder in matching_names:
            continue

        if isinstance(perf_def, pf_api.Perfometer):
            simple = _compute_simple_row(perf_def, metrics, plugins.colors)
            if simple is None:
                continue
            row, pct = simple
            return PerfometerResult(
                label=_label_from_segments(perf_def, metrics, plugins.units),
                rows=[row],
                pcts=[pct],
            )

        if isinstance(perf_def, pf_api.Bidirectional):
            bi = _compute_bidirectional_row(perf_def, metrics, plugins.colors)
            if bi is None:
                continue
            row, left_pct, right_pct = bi
            left_label = _label_from_segments(perf_def.left, metrics, plugins.units)
            right_label = _label_from_segments(perf_def.right, metrics, plugins.units)
            return PerfometerResult(
                label=" / ".join(filter(None, [left_label, right_label])),
                rows=[row],
                pcts=[left_pct, right_pct],
            )

        if isinstance(perf_def, pf_api.Stacked):
            rows = []
            pcts = []
            for part in (perf_def.lower, perf_def.upper):
                if _perfometer_matches(part, metrics):
                    simple = _compute_simple_row(part, metrics, plugins.colors)
                    if simple:
                        rows.append(simple[0])
                        pcts.append(simple[1])
            if rows:
                labels = []
                for part in (perf_def.lower, perf_def.upper):
                    if _perfometer_matches(part, metrics):
                        labels.append(_label_from_segments(part, metrics, plugins.units))
                return PerfometerResult(
                    label=" / ".join(filter(None, labels)),
                    rows=rows,
                    pcts=pcts,
                )

    return None
