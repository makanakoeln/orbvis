# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Canonical wire-format dataclasses from ``cmk.shared_typing``.

Single source of truth for the FormSpec wire format. Tries the upstream
``cmk.shared_typing`` package first (available built-in on CMK 2.4+);
falls back to the vendored snapshot in
:mod:`app.vendor.cmk_shared_typing` for MKP / standalone builds.

OrbVis-internal :mod:`_wire_types` TypedDicts mirror a subset of these
dataclasses. The drift-check test in
``tests/test_form_specs_wire.py`` walks every emitted wire dict and
instantiates the corresponding canonical dataclass so the next time
upstream adds a required field the suite turns red instead of the
frontend crashing silently at runtime.
"""

from __future__ import annotations

try:
    from cmk.shared_typing import vue_formspec_components as ws
except ImportError:
    from app.vendor.cmk_shared_typing import vue_formspec_components as ws


BooleanChoice = ws.BooleanChoice
CascadingSingleChoice = ws.CascadingSingleChoice
CascadingSingleChoiceElement = ws.CascadingSingleChoiceElement
Dictionary = ws.Dictionary
DictionaryElement = ws.DictionaryElement
DictionaryGroup = ws.DictionaryGroup
DictionaryGroupLayout = ws.DictionaryGroupLayout
FixedValue = ws.FixedValue
Float = ws.Float
FormSpec = ws.FormSpec
I18nPassword = ws.I18nPassword
Integer = ws.Integer
List = ws.List
MultilineText = ws.MultilineText
Password = ws.Password
SingleChoice = ws.SingleChoice
SingleChoiceElement = ws.SingleChoiceElement
String = ws.String
StringFieldSize = ws.StringFieldSize
ValidationMessage = ws.ValidationMessage


# Maps the ``type`` tag emitted by OrbVis visitors to the canonical dataclass.
# OrbVis-only tags (``orb_color``) are absent here — the drift test treats
# them as opaque and skips structural validation.
WIRE_TYPE_TO_CLASS: dict[str, type] = {
    "boolean_choice": BooleanChoice,
    "cascading_single_choice": CascadingSingleChoice,
    "dictionary": Dictionary,
    "fixed_value": FixedValue,
    "float": Float,
    "integer": Integer,
    "list": List,
    "multiline_text": MultilineText,
    "password": Password,
    "single_choice": SingleChoice,
    "string": String,
}


__all__ = [
    "WIRE_TYPE_TO_CLASS",
    "BooleanChoice",
    "CascadingSingleChoice",
    "CascadingSingleChoiceElement",
    "Dictionary",
    "DictionaryElement",
    "DictionaryGroup",
    "DictionaryGroupLayout",
    "FixedValue",
    "Float",
    "FormSpec",
    "I18nPassword",
    "Integer",
    "List",
    "MultilineText",
    "Password",
    "SingleChoice",
    "SingleChoiceElement",
    "String",
    "StringFieldSize",
    "ValidationMessage",
]
