# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""3-stage validate pipeline — parse / nested / custom.

Mirrors ``cmk.gui.form_specs.visitors._base.FormSpecVisitor.validate``:
when a raw value (typically loaded from disk) is structurally wrong, the
visitor returns ``InvalidValue(reason, fallback)`` so the caller can
render the form against the fallback instead of crashing. Tests pin the
contract for each visitor that owns a parse step.
"""

from __future__ import annotations

import app.form_specs._visitors  # noqa: F401 — side-effect: registers visitors
from app.form_specs import validate_form_data
from app.form_specs._registry import InvalidValue, get_visitor

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Integer,
    String,
)


def _string_spec() -> String:
    return String(title=Title("Name"))


def _int_spec() -> Integer:
    return Integer(title=Title("Count"))


def _dict_spec() -> Dictionary:
    return Dictionary(
        title=Title("Settings"),
        elements={
            "name": DictElement(parameter_form=String(), required=True),
            "count": DictElement(parameter_form=Integer(), required=False),
        },
    )


def test_string_parse_accepts_valid_string() -> None:
    spec = _string_spec()
    visitor = get_visitor(spec)
    assert visitor.parse(spec, "hello") == "hello"


def test_string_parse_rejects_int_with_fallback() -> None:
    spec = _string_spec()
    visitor = get_visitor(spec)
    parsed = visitor.parse(spec, 42)
    assert isinstance(parsed, InvalidValue)
    assert "string" in parsed.reason.lower()
    # Fallback must be of the right shape (a string) so callers can
    # render the form without a TypeError.
    assert isinstance(parsed.fallback, str)


def test_integer_parse_rejects_bool() -> None:
    """Booleans are ints in Python — parse must reject explicitly."""
    spec = _int_spec()
    visitor = get_visitor(spec)
    parsed = visitor.parse(spec, True)
    assert isinstance(parsed, InvalidValue)


def test_dictionary_parse_rejects_non_dict() -> None:
    spec = _dict_spec()
    visitor = get_visitor(spec)
    parsed = visitor.parse(spec, "not a dict")
    assert isinstance(parsed, InvalidValue)
    assert isinstance(parsed.fallback, dict)


def test_validate_returns_single_error_on_invalid_root() -> None:
    """Stage-1 parse failure short-circuits nested + custom validators."""
    errors = validate_form_data(_dict_spec(), "definitely not a dict")
    # Without InvalidValue short-circuit, this would have cascaded into a
    # nested "Required field is missing" error for 'name' as well.
    assert len(errors) == 1
    assert errors[0].location == []


def test_validate_nested_runs_when_root_shape_ok() -> None:
    """Stage-2 nested validation runs when root parses cleanly."""
    errors = validate_form_data(_dict_spec(), {"count": 5})  # missing required 'name'
    assert len(errors) == 1
    assert errors[0].location == ["name"]


def test_to_disk_default_is_identity() -> None:
    """Primitive visitors keep wire = disk for now."""
    spec = _string_spec()
    visitor = get_visitor(spec)
    assert visitor.to_disk(spec, "value") == "value"


def test_invalid_value_carries_helpful_reason() -> None:
    """Reason field is human-readable, not just a type name."""
    spec = _int_spec()
    visitor = get_visitor(spec)
    parsed = visitor.parse(spec, "not a number")
    assert isinstance(parsed, InvalidValue)
    assert "Expected" in parsed.reason
