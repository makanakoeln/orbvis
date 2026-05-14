# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec → JSON for the vendored frontend dispatcher.

Output shape matches :mod:`cmk.gui.form_specs.visitors` so the vendored
frontend components can render it 1:1 with the upstream FormSpec stack.
Only the subset of FormSpec types OrbVis uses is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from cmk.rulesets.v1._localize import _Localizable
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    DefaultValue,
    DictElement,
    DictGroup,
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


@dataclass(frozen=True, kw_only=True)
class OrbDictGroup(DictGroup):  # type: ignore[misc]
    """DictGroup + optional ``layout`` / explicit ``key`` for OrbVis FormSpecs.

    CMK's DictGroup only carries title + help; the vendored FormDictionary
    component reads ``group.layout`` ("vertical" stacks sections, "horizontal"
    arranges siblings inline). Adds an explicit ``key`` so groups with the
    same title don't collide.
    """

    layout: Literal["vertical", "horizontal"] = "vertical"
    key: str | None = None


def _identity(s: str) -> str:
    return s


def _loc(text: _Localizable | None) -> str | None:
    return None if text is None else text.localize(_identity)


@dataclass(frozen=True)
class FormSpecValidationMessage:
    location: list[str]
    message: str
    invalid_value: object | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "location": list(self.location),
            "message": self.message,
            "invalid_value": self.invalid_value,
        }


def serialize_form_spec(spec: FormSpec[object]) -> dict[str, object]:
    if isinstance(spec, Dictionary):
        return _common(spec, "dictionary") | {
            "elements": [
                {
                    "name": name,
                    "required": el.required,
                    "parameter_form": serialize_form_spec(el.parameter_form),
                    "default_value": _default_value(el.parameter_form),
                    "render_only": el.render_only,
                    "group": _group(el),
                }
                for name, el in spec.elements.items()
            ],
        }
    if isinstance(spec, String):
        return _common(spec, "string") | {
            "label": _loc(spec.label),
            "field_size": spec.field_size.name,
        }
    if isinstance(spec, MultilineText):
        return _common(spec, "multiline_text") | {
            "label": _loc(spec.label),
            "monospaced": spec.monospaced,
        }
    if isinstance(spec, Integer):
        return _common(spec, "integer") | {
            "label": _loc(spec.label),
            "unit": spec.unit_symbol,
        }
    if isinstance(spec, Float):
        return _common(spec, "float") | {
            "label": _loc(spec.label),
            "unit": spec.unit_symbol,
        }
    if isinstance(spec, BooleanChoice):
        return _common(spec, "boolean_choice") | {"label": _loc(spec.label)}
    if isinstance(spec, Password):
        # FormPassword expects password_store_choices + i18n strings — OrbVis has
        # no password-store, so we emit an empty list and labels for the dropdown
        # the user never gets to see in store mode.
        return _common(spec, "password") | {
            "password_store_choices": [],
            "i18n": {
                "explicit_password": "Explicit password",
                "password_store": "Stored password",
                "no_password_store_choices": "No password store available",
                "password_choice_invalid": "Invalid password choice",
                "choose_password_from_store": "Choose stored password",
                "choose_password_type": "Choose password type",
            },
        }
    if isinstance(spec, FixedValue):
        return _common(spec, "fixed_value") | {
            "label": _loc(spec.label),
            "value": spec.value,
        }
    if isinstance(spec, SingleChoice):
        return _common(spec, "single_choice") | {
            "label": _loc(spec.label),
            "no_elements_text": _loc(spec.no_elements_text),
            "elements": [{"name": _name(el.name), "title": _loc(el.title)} for el in spec.elements],
        }
    if isinstance(spec, CascadingSingleChoice):
        return _common(spec, "cascading_single_choice") | {
            "label": _loc(spec.label),
            "elements": [
                {
                    "name": el.name,
                    "title": _loc(el.title),
                    "parameter_form": serialize_form_spec(el.parameter_form),
                    # Frontend FormCascadingSingleChoice reads this when the
                    # user switches branches — without it the new branch's
                    # body crashes on `'host' in undefined`.
                    "default_value": _default_value(el.parameter_form),
                }
                for el in spec.elements
            ],
        }
    if isinstance(spec, List):
        return _common(spec, "list") | {
            "element_template": serialize_form_spec(spec.element_template),
            "add_element_label": _loc(spec.add_element_label),
            "remove_element_label": _loc(spec.remove_element_label),
            "no_element_label": _loc(spec.no_element_label),
            "editable_order": spec.editable_order,
        }
    raise TypeError(f"FormSpec type {type(spec).__name__} not serialisable yet")


def _group(el: DictElement[object]) -> dict[str, object] | None:
    group = el.group
    if not isinstance(group, DictGroup):
        return None
    title = _loc(group.title) or ""
    help_text = _loc(group.help_text) or ""
    if isinstance(group, OrbDictGroup):
        layout = group.layout
        key = group.key or _slugify(title) or "group"
    else:
        layout = "vertical"
        key = _slugify(title) or "group"
    return {"key": key, "title": title, "help": help_text, "layout": layout}


def _slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in text).strip("_")


def _common[T](spec: FormSpec[T], type_tag: str) -> dict[str, object]:
    return {
        "type": type_tag,
        "title": _loc(spec.title),
        "help": _loc(spec.help_text) or "",
        "validators": [],
    }


try:
    from cmk.gui.form_specs.visitors import DEFAULT_VALUE as _CMK_DEFAULT
    from cmk.gui.form_specs.visitors import get_visitor as _cmk_get_visitor
    from cmk.gui.form_specs.visitors._base import VisitorOptions as _CmkVisitorOptions

    _CMK_VISITORS_AVAILABLE = True
except ImportError:
    _CMK_VISITORS_AVAILABLE = False


def _default_value(spec: FormSpec[object]) -> object:
    if _CMK_VISITORS_AVAILABLE:
        try:
            visitor = _cmk_get_visitor(spec, _CmkVisitorOptions(data_origin="disk"))
            _, value = visitor.to_vue(_CMK_DEFAULT)
            return value
        except Exception:
            pass
    if isinstance(spec, String | MultilineText):
        return spec.prefill.value if isinstance(spec.prefill, DefaultValue) else ""
    if isinstance(spec, Integer | Float):
        return spec.prefill.value if isinstance(spec.prefill, DefaultValue) else None
    if isinstance(spec, BooleanChoice):
        return spec.prefill.value if isinstance(spec.prefill, DefaultValue) else False
    if isinstance(spec, SingleChoice):
        if isinstance(spec.prefill, DefaultValue):
            return _name(spec.prefill.value)
        return None
    if isinstance(spec, FixedValue):
        return spec.value
    if isinstance(spec, Password):
        return ["explicit_password", "", "", False]
    if isinstance(spec, CascadingSingleChoice):
        first = spec.elements[0] if spec.elements else None
        if isinstance(spec.prefill, DefaultValue):
            chosen = next(
                (e for e in spec.elements if e.name == spec.prefill.value),
                first,
            )
        else:
            chosen = first
        if chosen is None:
            return [None, None]
        return [chosen.name, _default_value(chosen.parameter_form)]
    if isinstance(spec, Dictionary):
        return {
            name: _default_value(el.parameter_form)
            for name, el in spec.elements.items()
            if el.required
        }
    if isinstance(spec, List):
        return []
    return None


def _name(name: object) -> object:
    # SingleChoice element names are usually plain strings, but the
    # CMK type allows enums — emit the underlying value for the wire.
    if hasattr(name, "value"):
        return name.value
    return name
