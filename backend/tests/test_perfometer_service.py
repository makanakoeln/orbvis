"""Unit tests for the pure helpers in perfometer_service.

These cover the perf_data parsing, unit formatting and quantity/bound
resolution that feed gadget perfometer rendering. They run without OMD —
the cmk.graphing imports inside the module degrade gracefully (ImportError
→ neutral fallback), so only the pure paths are exercised here.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.perfometer_service import (
    RegisteredUnit,
    _compute_simple_row,
    _compute_simple_side,
    _fmt_value,
    _format_iec,
    _format_si,
    _metric_color,
    _parse_perf_data,
    _PluginData,
    _RawMetric,
    _resolve_bound,
    _resolve_quantity,
    _trim,
    metric_titles,
    metric_unit_formats,
)


def _metric(
    value: float,
    *,
    unit: str = "",
    warn: float | None = None,
    crit: float | None = None,
    min: float | None = None,
    max: float | None = None,
) -> _RawMetric:
    return _RawMetric(value=value, unit=unit, warn=warn, crit=crit, min=min, max=max)


class TestParsePerfData:
    def test_single_metric_with_thresholds(self) -> None:
        out = _parse_perf_data("rta=0.5ms;100;200;0;500")
        assert set(out) == {"rta"}
        m = out["rta"]
        assert (m.value, m.unit) == (0.5, "ms")
        assert (m.warn, m.crit, m.min, m.max) == (100.0, 200.0, 0.0, 500.0)

    def test_multiple_metrics(self) -> None:
        out = _parse_perf_data("a=1 b=2.5")
        assert out["a"].value == 1.0
        assert out["b"].value == 2.5

    def test_quoted_label_with_spaces(self) -> None:
        out = _parse_perf_data("'disk usage'=80%;90;95")
        assert "disk usage" in out
        assert out["disk usage"].value == 80.0
        assert out["disk usage"].unit == "%"

    def test_negative_value(self) -> None:
        out = _parse_perf_data("temp=-5")
        assert out["temp"].value == -5.0

    def test_empty_threshold_fields_are_none(self) -> None:
        out = _parse_perf_data("load=0.5;;;0;")
        m = out["load"]
        assert m.warn is None and m.crit is None
        assert m.min == 0.0 and m.max is None

    def test_missing_thresholds_are_none(self) -> None:
        m = _parse_perf_data("load=0.5")["load"]
        assert (m.warn, m.crit, m.min, m.max) == (None, None, None, None)

    def test_empty_input(self) -> None:
        assert _parse_perf_data("") == {}

    def test_non_numeric_value_is_skipped(self) -> None:
        assert _parse_perf_data("status=abc") == {}


class TestTrim:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("5.00", "5"), ("5.10", "5.1"), ("5.0", "5"), ("5", "5"), ("0.25", "0.25")],
    )
    def test_trim(self, raw: str, expected: str) -> None:
        assert _trim(raw) == expected


class TestFormatSi:
    def test_kilo(self) -> None:
        assert _format_si(1500, "B") == "1.5 kB"

    def test_mega(self) -> None:
        assert _format_si(2.5e6, "B") == "2.5 MB"

    def test_zero(self) -> None:
        assert _format_si(0, "B") == "0 B"

    def test_milli_prefix(self) -> None:
        assert _format_si(0.5, "s") == "500 ms"


class TestFormatIec:
    def test_kibi(self) -> None:
        assert _format_iec(1536, "B") == "1.5 KiB"

    def test_below_unit(self) -> None:
        assert _format_iec(512, "B") == "512 B"


class TestFmtValue:
    def test_si_notation(self) -> None:
        assert (
            _fmt_value(
                "x",
                _metric(1500),
                {
                    "x": RegisteredUnit(
                        notation="SINotation", symbol="B", precision_type="auto", precision_digits=2
                    )
                },
            )
            == "1.5 kB"
        )

    def test_iec_notation(self) -> None:
        assert (
            _fmt_value(
                "x",
                _metric(1536),
                {
                    "x": RegisteredUnit(
                        notation="IECNotation",
                        symbol="B",
                        precision_type="auto",
                        precision_digits=2,
                    )
                },
            )
            == "1.5 KiB"
        )

    def test_time_notation_uses_seconds(self) -> None:
        assert (
            _fmt_value(
                "x",
                _metric(90),
                {
                    "x": RegisteredUnit(
                        notation="TimeNotation",
                        symbol="",
                        precision_type="auto",
                        precision_digits=2,
                    )
                },
            )
            == "90 s"
        )

    def test_unknown_notation_falls_back_to_symbol(self) -> None:
        assert (
            _fmt_value(
                "x",
                _metric(53.88),
                {
                    "x": RegisteredUnit(
                        notation="DecimalNotation",
                        symbol="%",
                        precision_type="auto",
                        precision_digits=2,
                    )
                },
            )
            == "53.88 %"
        )

    def test_legacy_bytes_unit(self) -> None:
        assert _fmt_value("x", _metric(2e9, unit="B"), {}) == "2.0 GB"

    def test_legacy_large_number(self) -> None:
        assert _fmt_value("x", _metric(1500), {}) == "1,500"

    def test_legacy_integer(self) -> None:
        assert _fmt_value("x", _metric(5, unit="%"), {}) == "5%"

    def test_legacy_float(self) -> None:
        assert _fmt_value("x", _metric(0.5, unit="x"), {}) == "0.5x"


class TestResolveQuantity:
    def test_literal_int(self) -> None:
        assert _resolve_quantity(5, {}) == 5.0

    def test_literal_float(self) -> None:
        assert _resolve_quantity(2.5, {}) == 2.5

    def test_metric_reference_present(self) -> None:
        assert _resolve_quantity("cpu", {"cpu": _metric(42)}) == 42.0

    def test_metric_reference_absent(self) -> None:
        assert _resolve_quantity("missing", {}) == 0.0


class TestResolveBound:
    def test_literal_value(self) -> None:
        assert _resolve_bound(SimpleNamespace(value=10), {}) == 10.0

    def test_metric_reference_value(self) -> None:
        assert _resolve_bound(SimpleNamespace(value="cpu"), {"cpu": _metric(42)}) == 42.0

    def test_none_bound(self) -> None:
        assert _resolve_bound(None, {}) == 0.0

    def test_bound_without_value(self) -> None:
        assert _resolve_bound(SimpleNamespace(), {}) == 0.0


class TestMetricColor:
    _CRIT = "#ff3232"
    _WARN = "#ffd000"
    _GREEN = "#15d1a0"
    _BLUE = "#28a2f3"

    def test_crit_breach(self) -> None:
        assert _metric_color("x", _metric(95, crit=90), {}) == self._CRIT

    def test_warn_breach(self) -> None:
        assert _metric_color("x", _metric(85, warn=80), {}) == self._WARN

    def test_declared_color(self) -> None:
        assert _metric_color("x", _metric(10), {"x": "BLUE"}) == self._BLUE

    def test_default_green(self) -> None:
        assert _metric_color("x", _metric(10), {}) == self._GREEN


def _simple_perf(segment: str, lower: float, upper: float) -> SimpleNamespace:
    return SimpleNamespace(
        segments=[segment],
        focus_range=SimpleNamespace(
            lower=SimpleNamespace(value=lower),
            upper=SimpleNamespace(value=upper),
        ),
    )


class TestComputeSimpleSide:
    def test_basic_utilization(self) -> None:
        perf = _simple_perf("cpu", 0, 100)
        side = _compute_simple_side(perf, {"cpu": _metric(53.88)}, {})
        assert side is not None
        raw_pct, segment_pct, color = side
        assert raw_pct == 53.88
        assert segment_pct == 53.9
        assert color == "#15d1a0"

    def test_visual_floor_for_tiny_nonzero(self) -> None:
        perf = _simple_perf("cpu", 0, 100)
        side = _compute_simple_side(perf, {"cpu": _metric(0.3)}, {})
        assert side is not None
        raw_pct, segment_pct, _ = side
        assert raw_pct == 0.3
        assert segment_pct == 1.0

    def test_clamps_above_100(self) -> None:
        perf = _simple_perf("cpu", 0, 100)
        side = _compute_simple_side(perf, {"cpu": _metric(250)}, {})
        assert side is not None
        assert side[0] == 100.0

    def test_no_present_metric(self) -> None:
        assert _compute_simple_side(_simple_perf("cpu", 0, 100), {}, {}) is None

    def test_degenerate_range(self) -> None:
        assert _compute_simple_side(_simple_perf("cpu", 100, 100), {"cpu": _metric(50)}, {}) is None


class TestComputeSimpleRow:
    def test_row_fills_to_100(self) -> None:
        row_result = _compute_simple_row(_simple_perf("cpu", 0, 100), {"cpu": _metric(53.88)}, {})
        assert row_result is not None
        row, raw_pct = row_result
        assert raw_pct == 53.88
        assert [round(s.pct, 1) for s in row] == [53.9, 46.1]
        assert row[0].color == "#15d1a0"
        assert row[1].color == "#52525b"


class TestMetricUnitFormats:
    """metric_unit_formats looks up the unit by the Checkmk-translated canonical
    name and applies the translation scale. Translation correctness itself lives
    in Checkmk (``_canonical_name_and_scale``) and is mocked here."""

    @pytest.fixture()
    def plugins(self, monkeypatch: pytest.MonkeyPatch) -> _PluginData:
        data = _PluginData(
            units={
                "mem_used": RegisteredUnit(
                    notation="IECNotation", symbol="B", precision_type="auto", precision_digits=2
                ),
                "rta": RegisteredUnit(
                    notation="TimeNotation", symbol="s", precision_type="auto", precision_digits=3
                ),
                "if_out_bps": RegisteredUnit(
                    notation="SINotation",
                    symbol="bits/s",
                    precision_type="strict",
                    precision_digits=2,
                ),
            },
        )
        # Canonical name + scale as Checkmk's find_matching_translation resolves them.
        trans = {"mem": ("mem_used", 1.0), "rta": ("rta", 0.001), "out": ("if_out_bps", 8.0)}
        monkeypatch.setattr("app.services.perfometer_service._load_plugins", lambda: data)
        monkeypatch.setattr(
            "app.services.perfometer_service._ensure_cmk_graphing_registered", lambda: True
        )
        monkeypatch.setattr(
            "app.services.perfometer_service._canonical_name_and_scale",
            lambda label, cc: trans.get(label, (label, 1.0)),
        )
        return data

    def test_translated_name_and_scale_applied(self, plugins: _PluginData) -> None:
        out = metric_unit_formats("mem=8927830016B;;;0; rta=0.02ms;;;;", "check_mk-my_check")
        assert out["mem"].notation == "iec"
        assert out["mem"].symbol == "B"
        assert out["mem"].scale == 1.0
        assert out["rta"].notation == "time"
        assert out["rta"].scale == 0.001
        assert out["rta"].precision_digits == 3

    def test_interface_octets_to_bits_scale(self, plugins: _PluginData) -> None:
        out = metric_unit_formats("out=131;;;0;", "check_mk-lnx_if")
        assert out["out"].notation == "si"
        assert out["out"].symbol == "bits/s"
        assert out["out"].scale == 8.0

    def test_unregistered_metric_is_omitted(self, plugins: _PluginData) -> None:
        out = metric_unit_formats("unknown=5;;;;", "check_mk-my_check")
        assert out == {}

    def test_empty_perfdata(self, plugins: _PluginData) -> None:
        assert metric_unit_formats("", "check_mk-my_check") == {}


class TestMetricTitles:
    """Without OMD the Checkmk graphing registry is unavailable, so titles fall
    back to {} and the endpoint shows raw labels. The CMK-mode path (real titles
    via Checkmk's own translation + registry) is covered by the live deployment."""

    def test_no_cmk_returns_empty(self) -> None:
        assert metric_titles("load1=1.09;;;0;8 load5=0.56;;;;", "check_mk-cpu_loads") == {}

    def test_empty_perfdata_returns_empty(self) -> None:
        assert metric_titles("", "check_mk-cpu_loads") == {}
