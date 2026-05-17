# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Shared helpers for FormSpec visitors.

Pure functions used by both serialise and validate paths — no FormSpec
state, no mutation. Kept separate from :mod:`_registry` so the visitor
modules stay readable.
"""

from __future__ import annotations

from app.vendor.cmk_form_specs_extended import DictGroupExtended, DictionaryGroupLayout

from cmk.rulesets.v1._localize import _Localizable
from cmk.rulesets.v1.form_specs import DictElement, DictGroup, FormSpec, InputHint


def identity(s: str) -> str:
    return s


def loc(text: _Localizable | None) -> str | None:
    return None if text is None else text.localize(identity)


def common(spec: FormSpec[object], type_tag: str) -> dict[str, object]:
    return {
        "type": type_tag,
        "title": loc(spec.title),
        "help": loc(spec.help_text) or "",
        "validators": [],
    }


def input_hint(prefill: object) -> object:
    """Surface ``InputHint(value=...)`` as placeholder text on the wire.

    DefaultValue is for the saved-value path (handled by the visitor's
    ``default_value``); InputHint is purely a UI affordance.
    """
    if isinstance(prefill, InputHint):
        value = prefill.value
        return value if value is not None else ""
    return None


def name(value: object) -> object:
    """SingleChoice element names may be enums — emit underlying value."""
    if hasattr(value, "value"):
        return value.value
    return value


def slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in text).strip("_")


def group_dict(el: DictElement[object]) -> dict[str, object] | None:
    """Serialise a DictElement's ``group`` for the wire format.

    Prefers an explicit ``OrbDictGroup.key`` over the title-slug fallback,
    because CMK's own visitor identifies groups by repr(title+help) — fragile
    when titles repeat or are empty, which OrbVis' ``_LABEL_OFFSETS`` triggers.
    """
    from app.form_specs.serialize import OrbDictGroup

    grp = el.group
    if not isinstance(grp, DictGroup):
        return None
    title = loc(grp.title) or ""
    help_text = loc(grp.help_text) or ""
    layout = (
        grp.layout.value
        if isinstance(grp, DictGroupExtended)
        else DictionaryGroupLayout.vertical.value
    )
    if isinstance(grp, OrbDictGroup) and grp.key:
        key = grp.key
    else:
        key = slugify(title) or "group"
    return {"key": key, "title": title, "help": help_text, "layout": layout}


def type_name(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__
