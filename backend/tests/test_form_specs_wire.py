# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Drift check: every emitted wire dict must construct a canonical dataclass.

The canonical FormSpec wire-format dataclasses live in
``cmk.shared_typing.vue_formspec_components`` (built-in) or the vendored
mirror under ``app.vendor.cmk_shared_typing`` (MKP / standalone).
OrbVis visitors emit dicts shaped after a documented subset of those
dataclasses. If upstream adds a required field, this test fails before
the frontend silently breaks.

For OrbVis-only tags (``orb_color``) the test validates structurally
against ``String`` because OrbColorString is a String at runtime — only
the dispatcher tag differs.
"""

from __future__ import annotations

from dataclasses import fields, is_dataclass

from app.form_specs import OrbColorString, serialize_form_spec
from app.form_specs._canonical import WIRE_TYPE_TO_CLASS
from app.form_specs._canonical import String as CanonicalString

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Float,
    Integer,
    List,
    MultilineText,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)

# Tags that are OrbVis-internal and validated against a substitute dataclass.
_ORBVIS_TAG_ALIAS: dict[str, type] = {
    "orb_color": CanonicalString,
}


def _comprehensive_spec() -> Dictionary:
    """Single Dictionary that uses every OrbVis-supported FormSpec type once."""
    return Dictionary(
        title=Title("All FormSpec types"),
        help_text=Help("Comprehensive spec for drift testing"),
        elements={
            "s": DictElement(parameter_form=String(title=Title("A string")), required=True),
            "color": DictElement(parameter_form=OrbColorString(title=Title("Color"))),
            "txt": DictElement(parameter_form=MultilineText(title=Title("Text"))),
            "i": DictElement(parameter_form=Integer(title=Title("Int"))),
            "f": DictElement(parameter_form=Float(title=Title("Float"))),
            "b": DictElement(parameter_form=BooleanChoice(title=Title("Yes/No"))),
            "p": DictElement(parameter_form=Password(title=Title("Password"))),
            "fv": DictElement(parameter_form=FixedValue(value=42, title=Title("Fixed"))),
            "sc": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Pick one"),
                    elements=[
                        SingleChoiceElement(name="a", title=Title("A")),
                        SingleChoiceElement(name="b", title=Title("B")),
                    ],
                    prefill=DefaultValue("a"),
                )
            ),
            "csc": DictElement(
                parameter_form=CascadingSingleChoice(
                    title=Title("Cascade"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="x",
                            title=Title("X"),
                            parameter_form=String(title=Title("X-detail")),
                        ),
                    ],
                )
            ),
            "lst": DictElement(parameter_form=List(element_template=String(), title=Title("Many"))),
        },
    )


def _validate_against_canonical(payload: dict[str, object], path: str) -> list[str]:
    """Return list of human-readable drift complaints for one wire dict.

    Empty list = no drift.
    """
    tag = payload.get("type")
    if not isinstance(tag, str):
        return [f"{path}: missing string 'type' tag, got {tag!r}"]

    canonical = WIRE_TYPE_TO_CLASS.get(tag) or _ORBVIS_TAG_ALIAS.get(tag)
    if canonical is None:
        return [f"{path}: unknown wire type tag {tag!r}"]
    if not is_dataclass(canonical):
        return []  # nothing structural to check

    errors: list[str] = []
    # Drop OrbVis-only / additive keys before constructing — these aren't part
    # of the canonical dataclass and would cause "unexpected keyword" failures.
    canonical_field_names = {f.name for f in fields(canonical)}
    extra = set(payload) - canonical_field_names
    if extra:
        # Extra keys aren't fatal (frontend ignores them) but worth surfacing.
        errors.append(f"{path}: extra keys not in canonical {canonical.__name__}: {sorted(extra)}")
    filtered = {k: v for k, v in payload.items() if k in canonical_field_names}

    try:
        canonical(**filtered)
    except TypeError as exc:
        errors.append(f"{path}: cannot construct {canonical.__name__}: {exc}")

    return errors


def _walk(payload: object, path: str) -> list[str]:
    """Recursively validate every wire-shaped dict embedded in ``payload``."""
    out: list[str] = []
    if isinstance(payload, dict):
        if "type" in payload and isinstance(payload["type"], str):
            out.extend(_validate_against_canonical(payload, path))
        for key, value in payload.items():
            out.extend(_walk(value, f"{path}.{key}"))
    elif isinstance(payload, (list, tuple)):
        for idx, item in enumerate(payload):
            out.extend(_walk(item, f"{path}[{idx}]"))
    return out


def test_emitted_wire_matches_canonical_dataclasses() -> None:
    """Every wire dict OrbVis emits must construct its canonical dataclass.

    Fails loudly when upstream cmk.shared_typing adds a required field —
    expected to be wired into the visitor BEFORE the frontend breaks.
    """
    wire = serialize_form_spec(_comprehensive_spec())
    complaints = _walk(wire, "$")

    # Extra-keys warnings are informational; only treat outright construction
    # failures or missing tags as test failures.
    fatal = [c for c in complaints if "extra keys" not in c]
    assert not fatal, "Wire-format drift against cmk.shared_typing:\n  " + "\n  ".join(fatal)


def test_orbcolor_validates_as_string() -> None:
    """OrbColorString emits ``orb_color`` but is structurally a String."""
    wire = serialize_form_spec(OrbColorString(title=Title("Tint")))
    assert wire["type"] == "orb_color"
    # Construct against canonical String to lock down the field shape.
    canonical_fields = {f.name for f in fields(CanonicalString)}
    filtered = {k: v for k, v in wire.items() if k in canonical_fields}
    # Required upstream fields not produced by OrbVis must be patched in
    # before construction (autocompleter is Optional on the canonical type
    # but typed strictly so we explicitly pass None).
    filtered.setdefault("autocompleter", None)
    CanonicalString(**filtered)


def test_canonical_module_loads() -> None:
    """The vendored / upstream module must import without surprise."""
    from app.form_specs import _canonical

    # All registered wire tags must point to dataclass types.
    for tag, cls in _canonical.WIRE_TYPE_TO_CLASS.items():
        assert is_dataclass(cls), f"{tag} → {cls!r} is not a dataclass"
    # Sanity-check the canonical String type isn't a stub.
    assert len(fields(_canonical.String)) > 3
