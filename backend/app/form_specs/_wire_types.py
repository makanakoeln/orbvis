# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""TypedDicts describing the FormSpec wire format.

Mirror the structure produced by ``cmk.gui.form_specs.visitors.*.to_vue``
(and validated by the JSON schemas under
``packages/cmk-shared-typing/source/vue_formspec/components.json``) so
that any drift between OrbVis' visitors and the upstream wire format is
caught by mypy rather than by a downstream JS exception.

The TypedDicts cover the subset of FormSpec types OrbVis emits — adding
a new visitor requires adding the corresponding TypedDict + extending
the ``AnyWireFormSpec`` union below.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class WireDictionaryGroup(TypedDict):
    key: str
    title: str
    help: str
    layout: str


class WireDictElement(TypedDict):
    name: str
    required: bool
    parameter_form: AnyWireFormSpec
    default_value: object
    render_only: bool
    group: NotRequired[WireDictionaryGroup | None]


class WireSingleChoiceElement(TypedDict):
    name: object
    title: str | None


class WireCascadingChoiceElement(TypedDict):
    name: str
    title: str | None
    parameter_form: AnyWireFormSpec
    default_value: object


class _Base(TypedDict):
    title: str | None
    help: str
    validators: list[object]


class WireDictionary(_Base):
    type: Literal["dictionary"]
    elements: list[WireDictElement]
    # Required by the canonical cmk.shared_typing.Dictionary dataclass.
    # OrbVis groups are derived per-element via WireDictionaryGroup (see
    # group_dict in _helpers), so the top-level ``groups`` list stays empty.
    groups: list[WireDictionaryGroup]
    no_elements_text: str
    additional_static_elements: object


class WireString(_Base):
    type: Literal["string"]
    label: str | None
    field_size: str
    input_hint: object
    autocompleter: object


class WireOrbColor(_Base):
    type: Literal["orb_color"]
    label: str | None
    field_size: str
    input_hint: object
    autocompleter: object


class WireOrbHostAutocomplete(_Base):
    type: Literal["orb_host_autocomplete"]
    label: str | None
    field_size: str
    input_hint: object
    autocompleter: object


class WireMultilineText(_Base):
    type: Literal["multiline_text"]
    label: str | None
    monospaced: bool
    input_hint: object
    macro_support: bool


class WireInteger(_Base):
    type: Literal["integer"]
    label: str | None
    unit: str | None
    input_hint: object


class WireFloat(_Base):
    type: Literal["float"]
    label: str | None
    unit: str | None
    input_hint: object


class WireBooleanChoice(_Base):
    type: Literal["boolean_choice"]
    label: str | None
    text_on: str
    text_off: str


class WirePasswordI18n(TypedDict):
    explicit_password: str
    password_store: str
    no_password_store_choices: str
    password_choice_invalid: str
    choose_password_from_store: str
    choose_password_type: str


class WirePassword(_Base):
    type: Literal["password"]
    password_store_choices: list[object]
    i18n: WirePasswordI18n


class WireFixedValue(_Base):
    type: Literal["fixed_value"]
    label: str | None
    value: object


class WireSingleChoice(_Base):
    type: Literal["single_choice"]
    label: str | None
    no_elements_text: str | None
    elements: list[WireSingleChoiceElement]
    frozen: bool
    input_hint: object


class WireCascadingSingleChoice(_Base):
    type: Literal["cascading_single_choice"]
    label: str | None
    elements: list[WireCascadingChoiceElement]
    no_elements_text: str
    input_hint: object


class WireList(_Base):
    type: Literal["list"]
    element_template: AnyWireFormSpec
    add_element_label: str | None
    remove_element_label: str | None
    no_element_label: str | None
    editable_order: bool
    element_default_value: object


AnyWireFormSpec = (
    WireDictionary
    | WireString
    | WireOrbColor
    | WireOrbHostAutocomplete
    | WireMultilineText
    | WireInteger
    | WireFloat
    | WireBooleanChoice
    | WirePassword
    | WireFixedValue
    | WireSingleChoice
    | WireCascadingSingleChoice
    | WireList
)
