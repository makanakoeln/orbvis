# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
# ruff: noqa: ARG002 — polymorphic visitor methods keep ``spec`` even when unused locally
"""Concrete FormSpec visitors.

One class per supported FormSpec type. Registration happens at module
import time via the ``register(...)`` calls at the bottom — importing
this module is what populates the registry consulted by
``serialize_form_spec`` and ``validate_form_data``.

When CMK ships its full visitor stack (cmk.gui.form_specs.visitors),
:func:`_default_via_cmk` short-circuits to it; otherwise the per-visitor
``default_value`` provides the OrbVis fallback. This keeps wire-format
defaults aligned with CMK whenever possible.

Visitor return types are :mod:`_wire_types` TypedDicts so mypy catches
drift against the JSON schema in
``packages/cmk-shared-typing/source/vue_formspec/components.json``.
"""

from __future__ import annotations

from collections.abc import Callable

from app.form_specs._helpers import group_dict, input_hint, loc, name, tr
from app.form_specs._registry import (
    FormSpecVisitor,
    get_visitor,
    msg,
    register,
    type_mismatch,
)
from app.form_specs._wire_types import (
    WireBooleanChoice,
    WireCascadingChoiceElement,
    WireCascadingSingleChoice,
    WireDictElement,
    WireDictionary,
    WireFixedValue,
    WireFloat,
    WireInteger,
    WireList,
    WireMultilineText,
    WireOrbColor,
    WireOrbHostAutocomplete,
    WirePassword,
    WireSingleChoice,
    WireSingleChoiceElement,
    WireString,
)
from app.form_specs.serialize import FormSpecValidationMessage, OrbColorString, OrbHostString

from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    DefaultValue,
    Dictionary,
    FixedValue,
    Float,
    FormSpec,
    Integer,
    List,
    MultilineText,
    Password,
    SingleChoice,
    String,
)

try:
    from cmk.gui.form_specs.visitors import DEFAULT_VALUE as _CMK_DEFAULT
    from cmk.gui.form_specs.visitors import get_visitor as _cmk_get_visitor
    from cmk.gui.form_specs.visitors._base import VisitorOptions as _CmkVisitorOptions

    _CMK_VISITORS_AVAILABLE = True
except ImportError:
    _CMK_VISITORS_AVAILABLE = False


class _Missing:
    """Sentinel — distinguishes 'CMK couldn't compute' from 'CMK returned None'."""


_MISSING = _Missing()


def _default_via_cmk(spec: FormSpec[object]) -> object:
    if not _CMK_VISITORS_AVAILABLE:
        return _MISSING
    try:
        visitor = _cmk_get_visitor(spec, _CmkVisitorOptions(data_origin="disk"))
        _, value = visitor.to_vue(_CMK_DEFAULT)
        return value
    except Exception:
        return _MISSING


def cmk_default_or[S: FormSpec[object]](spec: S, fallback: Callable[[S], object]) -> object:
    """CMK-first default with OrbVis fallback.

    Each leaf visitor's ``default_value`` would otherwise repeat the same
    ``_default_via_cmk`` + ``isinstance(_, _Missing)`` dance — this keeps the
    sentinel logic in one place so visitors only spell out their fallback.
    """
    via_cmk = _default_via_cmk(spec)
    if not isinstance(via_cmk, _Missing):
        return via_cmk
    return fallback(spec)


# ── Dictionary ─────────────────────────────────────────────────────────


class DictionaryVisitor(FormSpecVisitor[Dictionary]):
    spec_type = Dictionary

    def serialize(self, spec: Dictionary) -> WireDictionary:
        elements: list[WireDictElement] = []
        for key, el in spec.elements.items():
            child = get_visitor(el.parameter_form)
            wire_el: WireDictElement = {
                "name": key,
                "required": el.required,
                "parameter_form": child.serialize(el.parameter_form),
                "default_value": child.default_value(el.parameter_form),
                "render_only": el.render_only,
                "group": group_dict(el),
            }
            elements.append(wire_el)
        return {
            "type": "dictionary",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "elements": elements,
            # Per-element groups carry the canonical DictionaryGroup payload
            # via WireDictElement.group; no top-level group dedupe needed.
            "groups": [],
            "no_elements_text": "",
            "additional_static_elements": None,
        }

    def default_value(self, spec: Dictionary) -> object:
        def _fallback(s: Dictionary) -> object:
            return {
                key: get_visitor(el.parameter_form).default_value(el.parameter_form)
                for key, el in s.elements.items()
                if el.required
            }

        return cmk_default_or(spec, _fallback)

    def _validate_shape(
        self, spec: Dictionary, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, dict):
            return type_mismatch(location, "object", data)
        return []

    def _validate_nested(
        self, spec: Dictionary, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, dict):
            return []
        errors: list[FormSpecValidationMessage] = []
        for key, el in spec.elements.items():
            if key in data:
                visitor = get_visitor(el.parameter_form)
                errors.extend(visitor.validate(el.parameter_form, data[key], [*location, key]))
            elif el.required:
                errors.append(
                    FormSpecValidationMessage(
                        location=[*location, key],
                        message="Required field is missing",
                    )
                )
        return errors


# ── String / OrbColorString / MultilineText ────────────────────────────


class StringVisitor(FormSpecVisitor[String]):
    spec_type = String

    def serialize(self, spec: String) -> WireString:
        return {
            "type": "string",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "field_size": spec.field_size.name,
            "input_hint": input_hint(spec.prefill),
            "autocompleter": None,
        }

    def default_value(self, spec: String) -> object:
        return cmk_default_or(
            spec, lambda s: s.prefill.value if isinstance(s.prefill, DefaultValue) else ""
        )

    def _validate_shape(
        self, spec: String, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, str):
            return type_mismatch(location, "string", data)
        return []


class OrbColorStringVisitor(FormSpecVisitor[OrbColorString]):
    spec_type = OrbColorString

    def serialize(self, spec: OrbColorString) -> WireOrbColor:
        return {
            "type": "orb_color",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "field_size": spec.field_size.name,
            "input_hint": input_hint(spec.prefill),
            "autocompleter": None,
        }

    def default_value(self, spec: OrbColorString) -> object:
        return cmk_default_or(
            spec, lambda s: s.prefill.value if isinstance(s.prefill, DefaultValue) else ""
        )

    def _validate_shape(
        self, spec: OrbColorString, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, str):
            return type_mismatch(location, "string", data)
        return []


class OrbHostStringVisitor(FormSpecVisitor[OrbHostString]):
    spec_type = OrbHostString

    def serialize(self, spec: OrbHostString) -> WireOrbHostAutocomplete:
        return {
            "type": "orb_host_autocomplete",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "field_size": spec.field_size.name,
            "input_hint": input_hint(spec.prefill),
            "autocompleter": None,
        }

    def default_value(self, spec: OrbHostString) -> object:
        return cmk_default_or(
            spec, lambda s: s.prefill.value if isinstance(s.prefill, DefaultValue) else ""
        )

    def _validate_shape(
        self, spec: OrbHostString, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, str):
            return type_mismatch(location, "string", data)
        return []


class MultilineTextVisitor(FormSpecVisitor[MultilineText]):
    spec_type = MultilineText

    def serialize(self, spec: MultilineText) -> WireMultilineText:
        return {
            "type": "multiline_text",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "monospaced": spec.monospaced,
            "input_hint": input_hint(spec.prefill),
            "macro_support": False,
        }

    def default_value(self, spec: MultilineText) -> object:
        return cmk_default_or(
            spec, lambda s: s.prefill.value if isinstance(s.prefill, DefaultValue) else ""
        )

    def _validate_shape(
        self, spec: MultilineText, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, str):
            return type_mismatch(location, "string", data)
        return []


# ── Integer / Float ────────────────────────────────────────────────────


class IntegerVisitor(FormSpecVisitor[Integer]):
    spec_type = Integer

    def serialize(self, spec: Integer) -> WireInteger:
        return {
            "type": "integer",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "unit": spec.unit_symbol,
            "input_hint": input_hint(spec.prefill),
        }

    def default_value(self, spec: Integer) -> object:
        return cmk_default_or(
            spec, lambda s: s.prefill.value if isinstance(s.prefill, DefaultValue) else None
        )

    def _validate_shape(
        self, spec: Integer, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, int) or isinstance(data, bool):
            return type_mismatch(location, "integer", data)
        return []


class FloatVisitor(FormSpecVisitor[Float]):
    spec_type = Float

    def serialize(self, spec: Float) -> WireFloat:
        return {
            "type": "float",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "unit": spec.unit_symbol,
            "input_hint": input_hint(spec.prefill),
        }

    def default_value(self, spec: Float) -> object:
        return cmk_default_or(
            spec, lambda s: s.prefill.value if isinstance(s.prefill, DefaultValue) else None
        )

    def _validate_shape(
        self, spec: Float, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, int | float) or isinstance(data, bool):
            return type_mismatch(location, "number", data)
        return []


# ── BooleanChoice ──────────────────────────────────────────────────────


class BooleanChoiceVisitor(FormSpecVisitor[BooleanChoice]):
    spec_type = BooleanChoice

    def serialize(self, spec: BooleanChoice) -> WireBooleanChoice:
        return {
            "type": "boolean_choice",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "text_on": tr("On"),
            "text_off": tr("Off"),
        }

    def default_value(self, spec: BooleanChoice) -> object:
        return cmk_default_or(
            spec, lambda s: s.prefill.value if isinstance(s.prefill, DefaultValue) else False
        )

    def _validate_shape(
        self, spec: BooleanChoice, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, bool):
            return type_mismatch(location, "boolean", data)
        return []


# ── Password ───────────────────────────────────────────────────────────


class PasswordVisitor(FormSpecVisitor[Password]):
    spec_type = Password

    def serialize(self, spec: Password) -> WirePassword:
        # FormPassword expects password_store_choices + i18n strings — OrbVis has
        # no password-store, so we emit an empty list and labels for the dropdown
        # the user never gets to see in store mode.
        return {
            "type": "password",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "password_store_choices": [],
            "i18n": {
                "explicit_password": tr("Explicit password"),
                "password_store": tr("Stored password"),
                "no_password_store_choices": tr("No password store available"),
                "password_choice_invalid": tr("Invalid password choice"),
                "choose_password_from_store": tr("Choose stored password"),
                "choose_password_type": tr("Choose password type"),
            },
        }

    def default_value(self, spec: Password) -> object:
        return cmk_default_or(spec, lambda _s: ["explicit_password", "", "", False])

    def _validate_shape(
        self, spec: Password, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, str):
            return type_mismatch(location, "string", data)
        return []


# ── FixedValue ─────────────────────────────────────────────────────────


class FixedValueVisitor(FormSpecVisitor[FixedValue]):
    spec_type = FixedValue

    def serialize(self, spec: FixedValue) -> WireFixedValue:
        return {
            "type": "fixed_value",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "value": spec.value,
        }

    def default_value(self, spec: FixedValue) -> object:
        return cmk_default_or(spec, lambda s: s.value)

    def _validate_shape(
        self, spec: FixedValue, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if data != spec.value:
            return [msg(location, f"Value must equal {spec.value!r}", data)]
        return []


# ── SingleChoice / CascadingSingleChoice ───────────────────────────────


class SingleChoiceVisitor(FormSpecVisitor[SingleChoice]):
    spec_type = SingleChoice

    def serialize(self, spec: SingleChoice) -> WireSingleChoice:
        elements: list[WireSingleChoiceElement] = [
            {"name": name(el.name), "title": loc(el.title)} for el in spec.elements
        ]
        return {
            "type": "single_choice",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "no_elements_text": loc(spec.no_elements_text),
            "elements": elements,
            "frozen": False,
            "input_hint": None,
        }

    def default_value(self, spec: SingleChoice) -> object:
        def _fallback(s: SingleChoice) -> object:
            if isinstance(s.prefill, DefaultValue):
                return name(s.prefill.value)
            return None

        return cmk_default_or(spec, _fallback)

    def _validate_shape(
        self, spec: SingleChoice, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        valid = {name(el.name) for el in spec.elements}
        if data not in valid:
            return [
                msg(
                    location,
                    f"Value must be one of {sorted(str(v) for v in valid)}",
                    data,
                )
            ]
        return []


class CascadingSingleChoiceVisitor(FormSpecVisitor[CascadingSingleChoice]):
    spec_type = CascadingSingleChoice

    def serialize(self, spec: CascadingSingleChoice) -> WireCascadingSingleChoice:
        elements: list[WireCascadingChoiceElement] = []
        for el in spec.elements:
            child = get_visitor(el.parameter_form)
            elements.append(
                {
                    "name": el.name,
                    "title": loc(el.title),
                    "parameter_form": child.serialize(el.parameter_form),
                    # Frontend FormCascadingSingleChoice reads this when the
                    # user switches branches — without it the new branch's
                    # body crashes on `'host' in undefined`.
                    "default_value": child.default_value(el.parameter_form),
                }
            )
        return {
            "type": "cascading_single_choice",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "label": loc(spec.label),
            "elements": elements,
            "no_elements_text": "",
            "input_hint": None,
        }

    def default_value(self, spec: CascadingSingleChoice) -> object:
        def _fallback(s: CascadingSingleChoice) -> object:
            first = s.elements[0] if s.elements else None
            if isinstance(s.prefill, DefaultValue):
                chosen = next(
                    (e for e in s.elements if e.name == s.prefill.value),
                    first,
                )
            else:
                chosen = first
            if chosen is None:
                return [None, None]
            return [
                chosen.name,
                get_visitor(chosen.parameter_form).default_value(chosen.parameter_form),
            ]

        return cmk_default_or(spec, _fallback)

    def _validate_shape(
        self, spec: CascadingSingleChoice, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, list | tuple) or len(data) != 2:
            return [msg(location, "Expected [choice, value] pair", data)]
        choice, _ = data
        if not any(branch.name == choice for branch in spec.elements):
            return [msg(location, f"Unknown choice {choice!r}", data)]
        return []

    def _validate_nested(
        self, spec: CascadingSingleChoice, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, list | tuple) or len(data) != 2:
            return []
        choice, value = data
        for branch in spec.elements:
            if branch.name == choice:
                return list(
                    get_visitor(branch.parameter_form).validate(
                        branch.parameter_form, value, location
                    )
                )
        return []


# ── List ───────────────────────────────────────────────────────────────


class ListVisitor(FormSpecVisitor[List]):
    spec_type = List

    def serialize(self, spec: List) -> WireList:
        element_visitor = get_visitor(spec.element_template)
        return {
            "type": "list",
            "title": loc(spec.title),
            "help": loc(spec.help_text) or "",
            "validators": [],
            "element_template": element_visitor.serialize(spec.element_template),
            "add_element_label": loc(spec.add_element_label),
            "remove_element_label": loc(spec.remove_element_label),
            "no_element_label": loc(spec.no_element_label),
            "editable_order": spec.editable_order,
            "element_default_value": element_visitor.default_value(spec.element_template),
        }

    def default_value(self, spec: List) -> object:
        return cmk_default_or(spec, lambda _s: [])

    def _validate_shape(
        self, spec: List, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, list):
            return type_mismatch(location, "array", data)
        return []

    def _validate_nested(
        self, spec: List, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        if not isinstance(data, list):
            return []
        out: list[FormSpecValidationMessage] = []
        elem_visitor = get_visitor(spec.element_template)
        for idx, item in enumerate(data):
            out.extend(elem_visitor.validate(spec.element_template, item, [*location, str(idx)]))
        return out


# ── Registration ───────────────────────────────────────────────────────


register(DictionaryVisitor())
register(StringVisitor())
register(OrbColorStringVisitor())
register(OrbHostStringVisitor())
register(MultilineTextVisitor())
register(IntegerVisitor())
register(FloatVisitor())
register(BooleanChoiceVisitor())
register(PasswordVisitor())
register(FixedValueVisitor())
register(SingleChoiceVisitor())
register(CascadingSingleChoiceVisitor())
register(ListVisitor())
