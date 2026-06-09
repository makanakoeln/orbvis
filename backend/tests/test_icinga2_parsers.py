"""Unit tests for the pure parsing/aggregation helpers in the Icinga2 backend.

These cover filter-literal escaping, worst-state aggregation, the type-safe
attribute accessors and the timing-field mapping — all without touching the
Icinga2 REST API.
"""

from __future__ import annotations

from app.connections.icinga2 import (
    _apply_icinga_extra,
    _icinga_dict,
    _icinga_float,
    _icinga_int,
    _icinga_str,
    _iq,
    _worst_host,
    _worst_svc,
)
from app.schemas.state import ObjectState


class TestIq:
    def test_escapes_double_quotes(self) -> None:
        assert _iq('say "hi"') == 'say \\"hi\\"'

    def test_escapes_backslash(self) -> None:
        assert _iq("a\\b") == "a\\\\b"

    def test_backslash_escaped_before_quote(self) -> None:
        # A leading backslash must be doubled first, then the quote escaped —
        # otherwise the escape char itself could break out of the literal.
        assert _iq('\\"') == '\\\\\\"'

    def test_passthrough_plain(self) -> None:
        assert _iq("localhost") == "localhost"


class TestWorstHost:
    def test_down_beats_unreachable(self) -> None:
        assert _worst_host("UP", "UNREACHABLE", "DOWN") == "DOWN"

    def test_unreachable_beats_up(self) -> None:
        assert _worst_host("UP", "UNREACHABLE") == "UNREACHABLE"

    def test_all_up(self) -> None:
        assert _worst_host("UP", "UP") == "UP"

    def test_unknown_state_treated_as_ok(self) -> None:
        assert _worst_host("UP", "BOGUS") == "UP"


class TestWorstSvc:
    def test_critical_is_worst(self) -> None:
        assert _worst_svc("OK", "WARNING", "CRITICAL") == "CRITICAL"

    def test_warning_beats_unknown(self) -> None:
        assert _worst_svc("WARNING", "UNKNOWN") == "WARNING"

    def test_unknown_beats_ok(self) -> None:
        assert _worst_svc("OK", "UNKNOWN") == "UNKNOWN"


class TestIcingaDict:
    def test_returns_nested_dict(self) -> None:
        assert _icinga_dict({"attrs": {"a": 1}}, "attrs") == {"a": 1}

    def test_non_dict_value_yields_empty(self) -> None:
        assert _icinga_dict({"attrs": "nope"}, "attrs") == {}

    def test_missing_key_yields_empty(self) -> None:
        assert _icinga_dict({}, "attrs") == {}


class TestIcingaStr:
    def test_returns_string(self) -> None:
        assert _icinga_str({"name": "web01"}, "name") == "web01"

    def test_non_string_returns_default(self) -> None:
        assert _icinga_str({"name": 5}, "name", default="x") == "x"

    def test_missing_returns_default(self) -> None:
        assert _icinga_str({}, "name") == ""


class TestIcingaInt:
    def test_int_value(self) -> None:
        assert _icinga_int({"state": 2}, "state") == 2

    def test_float_is_truncated(self) -> None:
        assert _icinga_int({"state": 2.9}, "state") == 2

    def test_bool_is_int(self) -> None:
        assert _icinga_int({"flag": True}, "flag") == 1

    def test_string_returns_default(self) -> None:
        assert _icinga_int({"state": "2"}, "state", default=7) == 7

    def test_missing_returns_default(self) -> None:
        assert _icinga_int({}, "state", default=3) == 3


class TestIcingaFloat:
    def test_positive_value(self) -> None:
        assert _icinga_float({"ts": 5.5}, "ts") == 5.5

    def test_zero_is_none(self) -> None:
        assert _icinga_float({"ts": 0}, "ts") is None

    def test_negative_is_none(self) -> None:
        assert _icinga_float({"ts": -3}, "ts") is None

    def test_bool_is_none(self) -> None:
        assert _icinga_float({"ts": True}, "ts") is None

    def test_missing_is_none(self) -> None:
        assert _icinga_float({}, "ts") is None


class TestApplyIcingaExtra:
    def _state(self) -> ObjectState:
        return ObjectState(object_id="o1", type="host", state="UP")

    def test_maps_timing_and_attempts(self) -> None:
        attrs: dict[str, object] = {
            "last_check": 100.0,
            "last_state_change": 50.0,
            "state_type": 0,
            "check_attempt": 2,
            "max_check_attempts": 3,
        }
        s = _apply_icinga_extra(self._state(), attrs)
        assert s.last_check == 100.0
        assert s.last_state_change == 50.0
        assert s.state_type == "SOFT"
        assert s.current_attempt == 2
        assert s.max_attempts == 3

    def test_hard_state_type(self) -> None:
        assert _apply_icinga_extra(self._state(), {"state_type": 1}).state_type == "HARD"

    def test_missing_state_type_defaults_hard(self) -> None:
        assert _apply_icinga_extra(self._state(), {}).state_type == "HARD"
