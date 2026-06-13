"""CMK perfometer computation using cmk.graphing.v1 plugin definitions."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache

from app.integrations.cmk_plugins import (
    get_plugin_dirs,
    iter_graphing_modules,
    load_cmk_graphing_data,
)

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


@dataclass(frozen=True)
class RegisteredUnit:
    """Display unit of a metric as declared in its Metric() plugin definition."""

    notation: str  # cmk.graphing.v1 notation class name, e.g. "SINotation"
    symbol: str
    precision_type: str  # "auto" | "strict"
    precision_digits: int


@dataclass
class _PluginData:
    # Perfometer / Bidirectional / Stacked instances from cmk.graphing.v1 (untyped from mypy's view)
    perfometers: list[object] = field(default_factory=list)
    # check_plugin_name → {raw_metric_name → canonical_name}
    renames: dict[str, dict[str, str]] = field(default_factory=dict)
    # check_plugin_name → {raw_metric_name → scale_factor}
    scales: dict[str, dict[str, float]] = field(default_factory=dict)
    # check_plugin_name → [(compiled "~"-pattern, canonical_name|None, scale)]
    # in declaration order — CMK matches exact entries first, then the first
    # regex whose anchored .match() hits (find_matching_translation).
    regex_translations: dict[str, list[tuple[re.Pattern[str], str | None, float]]] = field(
        default_factory=dict
    )
    # metric_name → registered display unit for formatting
    units: dict[str, RegisteredUnit] = field(default_factory=dict)
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


@lru_cache(maxsize=1)
def _load_plugins() -> _PluginData:
    try:
        from cmk.graphing.v1 import perfometers as pf_api
    except ImportError:
        logger.debug("cmk.graphing.v1 not available — perfometer feature disabled")
        return _PluginData()

    data = _PluginData()
    plugin_dirs = get_plugin_dirs()
    if not plugin_dirs:
        logger.debug("No cmk.plugins directories found")
        return data

    for mod in iter_graphing_modules(plugin_dirs):
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
                precision = getattr(obj.unit, "precision", None)
                data.units[obj.name] = RegisteredUnit(
                    notation=type(notation).__name__,
                    # TimeNotation carries no symbol — time is always seconds.
                    symbol=getattr(notation, "symbol", "")
                    or ("s" if type(notation).__name__ == "TimeNotation" else ""),
                    precision_type=(
                        "strict" if type(precision).__name__ == "StrictPrecision" else "auto"
                    ),
                    precision_digits=int(getattr(precision, "digits", 2)),
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
                    rx = data.regex_translations.setdefault(name, [])
                    for src, rule in obj.translations.items():
                        target = getattr(rule, "metric_name", None)
                        factor = float(getattr(rule, "factor", 1.0))
                        if src.startswith("~"):
                            try:
                                rx.append((re.compile(src[1:]), target, factor))
                            except re.error:
                                logger.debug("Invalid translation pattern %r in %s", src, name)
                            continue
                        if target is not None and target != src:
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


def _find_translation(
    label: str,
    plugin_name: str,
    plugins: _PluginData,
) -> tuple[str, float]:
    """Canonical metric name + scale for a raw perfdata label.

    Mirrors cmk.gui.graphing find_matching_translation: an exact entry wins,
    otherwise the first "~"-regex entry whose anchored match hits; no entry
    means the label is already canonical with scale 1.0.
    """
    renamed = plugins.renames.get(plugin_name, {}).get(label)
    scaled = plugins.scales.get(plugin_name, {}).get(label)
    if renamed is not None or scaled is not None:
        return (renamed or label, scaled if scaled is not None else 1.0)
    for pattern, target, factor in plugins.regex_translations.get(plugin_name, []):
        if pattern.match(label):
            return (target or label, factor)
    return (label, 1.0)


def _apply_translations(
    raw: dict[str, _RawMetric],
    check_command: str,
    plugins: _PluginData,
) -> dict[str, _RawMetric]:
    plugin_name = _check_plugin_name(check_command)
    if not plugin_name:
        return raw
    result: dict[str, _RawMetric] = {}
    for src_name, metric in raw.items():
        target_name, factor = _find_translation(src_name, plugin_name, plugins)
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


def _fmt_value(name: str, m: _RawMetric, units: dict[str, RegisteredUnit]) -> str:
    unit_info = units.get(name)
    if unit_info:
        if unit_info.notation == "SINotation":
            return _format_si(m.value, unit_info.symbol)
        if unit_info.notation == "IECNotation":
            return _format_iec(m.value, unit_info.symbol)
        if unit_info.notation == "TimeNotation":
            return _format_si(m.value, "s")
        return _trim(f"{m.value:.2f}") + (f" {unit_info.symbol}" if unit_info.symbol else "")

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
    units: dict[str, RegisteredUnit],
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


def _metric_title(name: str) -> str:
    # Shared single-pass loader — a second cmk.plugins graphing walk here
    # would double the startup cost cmk_plugins.py exists to avoid.
    return load_cmk_graphing_data().titles.get(name, "")


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


# Notation class name → wire enum of cmk-shared-typing's UnitFormat schema —
# the same shape cmk-frontend-vue's unit-format library consumes.
_NOTATION_WIRE: dict[str, str] = {
    "DecimalNotation": "decimal",
    "SINotation": "si",
    "IECNotation": "iec",
    "StandardScientificNotation": "standard_scientific",
    "EngineeringScientificNotation": "engineering_scientific",
    "TimeNotation": "time",
}


@dataclass(frozen=True)
class MetricUnitFormat:
    """Wire-ready display unit for one raw perfdata metric.

    ``scale`` converts the raw perfdata value into the registry's canonical
    unit (translation factor, e.g. ms → s) before formatting.
    """

    notation: str  # UnitFormat wire enum: decimal|si|iec|…|time
    symbol: str
    precision_type: str  # "auto" | "strict"
    precision_digits: int
    scale: float


def metric_unit_formats(perf_data_str: str, check_command: str) -> dict[str, MetricUnitFormat]:
    """Resolve each raw perfdata label to its CMK metric-registry display unit.

    Keys are the RAW perfdata labels (what clients parse from perf_data);
    translation renames and scale factors of the check plugin are applied so a
    client can format ``raw_value * scale`` with the returned unit and get the
    exact rendering Checkmk's GUI shows. Metrics without a registry entry are
    omitted — the client falls back to its own heuristic for those.
    """
    if not perf_data_str.strip() or not _ensure_cmk_graphing_registered():
        return {}
    plugins = _load_plugins()
    if not plugins.units:
        return {}
    raw = _parse_perf_data(perf_data_str)
    if not raw:
        return {}

    out: dict[str, MetricUnitFormat] = {}
    for label in raw:
        canonical, scale = _canonical_name_and_scale(label, check_command)
        unit = plugins.units.get(canonical)
        if unit is None:
            continue
        wire = _NOTATION_WIRE.get(unit.notation)
        if wire is None:
            continue
        out[label] = MetricUnitFormat(
            notation=wire,
            symbol=unit.symbol,
            precision_type=unit.precision_type,
            precision_digits=unit.precision_digits,
            scale=scale,
        )
    return out


_graphing_registered = False


def _ensure_cmk_graphing_registered() -> bool:
    """Populate Checkmk's graphing registries (metric specs + check translations)
    once, exactly as the GUI does at startup. Lets ``metric_titles`` resolve names
    through Checkmk's own logic rather than a reimplementation. CMK mode only — a
    transient failure is retried on the next call (not pinned like an lru_cache)."""
    global _graphing_registered
    if _graphing_registered:
        return True
    try:
        from cmk.gui.graphing_main import register as register_graphing
    except ImportError:
        return False
    try:
        register_graphing()
    except Exception:
        logger.debug("cmk graphing registration unavailable", exc_info=True)
        return False
    _graphing_registered = True
    return True


@lru_cache(maxsize=256)
def _cmk_check_translations(check_command: str) -> object:
    from cmk.gui.graphing._legacy import check_metrics
    from cmk.gui.graphing._translated_metrics import (
        lookup_metric_translations_for_check_command,
    )

    return lookup_metric_translations_for_check_command(check_metrics, check_command)


def _canonical_name_and_scale(label: str, check_command: str) -> tuple[str, float]:
    """Canonical metric name + scale for a raw perfdata label, via Checkmk's own
    find_matching_translation (exact + regex translations). The seam every CMK
    name/unit lookup goes through, so a perfvar that differs from the registry
    name (interface ``in`` / ``out`` → ``if_in_bps`` / ``if_out_bps`` ×8) resolves
    exactly as Checkmk's GUI does."""
    from cmk.gui.graphing._translated_metrics import find_matching_translation
    from cmk.utils.metrics import MetricName

    spec = find_matching_translation(
        MetricName(label.replace(".", "_")), _cmk_check_translations(check_command)
    )
    return (spec.name, spec.scale)


def translate_metric_names(perf_data_str: str, check_command: str) -> dict[str, str]:
    """Map each raw perfdata label to its canonical Checkmk metric name (CMK mode
    only) so a service whose perfvars differ from the registry name matches
    Checkmk graph templates. Labels Checkmk can't translate are omitted."""
    if not perf_data_str.strip() or not _ensure_cmk_graphing_registered():
        return {}
    out: dict[str, str] = {}
    for label in _parse_perf_data(perf_data_str):
        try:
            out[label] = _canonical_name_and_scale(label, check_command)[0]
        except Exception:
            continue
    return out


def metric_titles(perf_data_str: str, check_command: str) -> dict[str, str]:
    """Map each raw perfdata label to its Checkmk metric title using Checkmk's own
    translation + metric registry (CMK mode only). Keys are the RAW labels (what
    clients store and match against perf_data); labels Checkmk doesn't know are
    omitted so the caller falls back to the raw label."""
    if not perf_data_str.strip() or not _ensure_cmk_graphing_registered():
        return {}
    try:
        from cmk.gui.graphing._from_api import metrics_from_api
        from cmk.gui.graphing._legacy import check_metrics
        from cmk.gui.graphing._metrics import get_metric_spec
        from cmk.gui.graphing._translated_metrics import (
            find_matching_translation,
            lookup_metric_translations_for_check_command,
        )
        from cmk.utils.metrics import MetricName
    except ImportError:
        return {}
    translations = lookup_metric_translations_for_check_command(check_metrics, check_command)
    out: dict[str, str] = {}
    for label in _parse_perf_data(perf_data_str):
        try:
            # Checkmk normalises dots to underscores before its registry lookup.
            name = find_matching_translation(MetricName(label.replace(".", "_")), translations).name
            out[label] = get_metric_spec(name, metrics_from_api).title
        except Exception:
            continue
    return out


def metric_title(name: str) -> str | None:
    """Checkmk's display title for a (canonical) metric name via its own registry,
    or ``None`` outside CMK. No check-command translation — callers that have one
    should use ``metric_titles`` instead."""
    if not name or not _ensure_cmk_graphing_registered():
        return None
    try:
        from cmk.gui.graphing._from_api import metrics_from_api
        from cmk.gui.graphing._metrics import get_metric_spec
    except ImportError:
        return None
    try:
        title: str = get_metric_spec(name, metrics_from_api).title
        return title
    except Exception:
        return None
