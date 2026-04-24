"""CMK perfometer computation using cmk.graphing.v1 plugin definitions."""

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
    perfometers: list = field(default_factory=list)
    # check_plugin_name → {raw_metric_name → canonical_name}
    renames: dict[str, dict[str, str]] = field(default_factory=dict)
    # check_plugin_name → {raw_metric_name → scale_factor}
    scales: dict[str, dict[str, float]] = field(default_factory=dict)
    # metric_name → (notation_type_name, symbol) for formatting
    units: dict[str, tuple[str, str]] = field(default_factory=dict)


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


def _get_segment_names(segments) -> list[str]:
    """Extract canonical metric names from a perfometer's segments list."""
    names: list[str] = []
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
                elif hasattr(val, "__iter__"):
                    names.extend(_get_segment_names(val))
    return names


def _perfometer_matches(perf, metrics: dict[str, _RawMetric]) -> bool:
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


def _resolve_quantity(q, metrics: dict[str, _RawMetric]) -> float:
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


def _resolve_bound(bound, metrics: dict[str, _RawMetric]) -> float:
    return _resolve_quantity(bound.value, metrics)


def _metric_color(m: _RawMetric, pct: float) -> str:
    if m.warn is not None and m.crit is not None and m.crit > m.warn > 0:
        scale = m.crit - m.warn
        if m.value < m.warn:
            return "#19d379"
        if m.value < m.crit:
            t = (m.value - m.warn) / scale
            r = round(245 - (245 - 239) * t)
            g = round(163 - (163 - 68) * t)
            return f"#{r:02x}{g:02x}0b"
        return "#ef4444"
    # fallback: green→amber→red by percentage
    if pct <= 50:
        t = pct / 50
        r = round(25 + (245 - 25) * t)
        g = round(211 - (211 - 163) * t)
        b = round(121 - (121 - 11) * t)
        return f"#{r:02x}{g:02x}{b:02x}"
    t = (pct - 50) / 50
    r = round(245 + (239 - 245) * t)
    g = round(163 - (163 - 68) * t)
    b = round(11 + (68 - 11) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


_REMAINDER_COLOR = "#2a2a2a"


def _compute_simple_side(
    perf,
    metrics: dict[str, _RawMetric],
) -> tuple[float, str] | None:
    """Return (pct, color) for a single Perfometer — not a full row."""
    names = _get_segment_names(perf.segments)
    present = [n for n in names if n in metrics]
    if not present:
        return None
    total = sum(metrics[n].value for n in present)
    lower = _resolve_bound(perf.focus_range.lower, metrics)
    upper = _resolve_bound(perf.focus_range.upper, metrics)
    if upper <= lower:
        return None
    pct = min(100.0, max(0.0, (total - lower) / (upper - lower) * 100))
    color = _metric_color(metrics[present[0]], pct)
    return (round(pct, 1), color)


def _compute_simple_row(
    perf,
    metrics: dict[str, _RawMetric],
) -> list[PerfometerSegment]:
    side = _compute_simple_side(perf, metrics)
    if side is None:
        return []
    pct, color = side
    return [
        PerfometerSegment(pct=pct, color=color),
        PerfometerSegment(pct=round(100 - pct, 1), color=_REMAINDER_COLOR),
    ]


def _compute_bidirectional_row(
    perf,
    metrics: dict[str, _RawMetric],
) -> list[PerfometerSegment] | None:
    """Single-row layout: [empty_left, left_fill, right_fill, empty_right], each half = 50%."""
    left = _compute_simple_side(perf.left, metrics)
    right = _compute_simple_side(perf.right, metrics)
    if left is None or right is None:
        return None
    left_pct, left_color = left
    right_pct, right_color = right
    empty_left = 50 - 50 * left_pct / 100
    fill_left = 50 * left_pct / 100
    fill_right = 50 * right_pct / 100
    empty_right = 50 - 50 * right_pct / 100
    return [
        PerfometerSegment(pct=round(empty_left, 1), color=_REMAINDER_COLOR),
        PerfometerSegment(pct=round(fill_left, 1), color=left_color),
        PerfometerSegment(pct=round(fill_right, 1), color=right_color),
        PerfometerSegment(pct=round(empty_right, 1), color=_REMAINDER_COLOR),
    ]


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
    perf,
    metrics: dict[str, _RawMetric],
    units: dict[str, tuple[str, str]],
) -> str:
    names = _get_segment_names(perf.segments)
    present = [n for n in names if n in metrics]
    if not present:
        return ""
    return _fmt_value(present[0], metrics[present[0]], units)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


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

    for perf_def in plugins.perfometers:
        if not _perfometer_matches(perf_def, metrics):
            continue

        if isinstance(perf_def, pf_api.Perfometer):
            row = _compute_simple_row(perf_def, metrics)
            if not row:
                continue
            return PerfometerResult(
                label=_label_from_segments(perf_def, metrics, plugins.units),
                rows=[row],
            )

        if isinstance(perf_def, pf_api.Bidirectional):
            bi_row = _compute_bidirectional_row(perf_def, metrics)
            if bi_row is None:
                continue
            left_label = _label_from_segments(perf_def.left, metrics, plugins.units)
            right_label = _label_from_segments(perf_def.right, metrics, plugins.units)
            return PerfometerResult(
                label=" / ".join(filter(None, [left_label, right_label])),
                rows=[bi_row],
            )

        if isinstance(perf_def, pf_api.Stacked):
            rows = []
            for part in (perf_def.lower, perf_def.upper):
                if _perfometer_matches(part, metrics):
                    row = _compute_simple_row(part, metrics)
                    if row:
                        rows.append(row)
            if rows:
                labels = []
                for part in (perf_def.lower, perf_def.upper):
                    if _perfometer_matches(part, metrics):
                        labels.append(_label_from_segments(part, metrics, plugins.units))
                return PerfometerResult(
                    label=" / ".join(filter(None, labels)),
                    rows=rows,
                )

    return None
