# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Server-side validation for FormSpec submissions."""

from __future__ import annotations

from app.form_specs.serialize import FormSpecValidationMessage

from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
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


def validate_form_data(
    spec: FormSpec[object],
    data: object,
) -> list[FormSpecValidationMessage]:
    return list(_walk(spec, data, location=[]))


def _walk(
    spec: FormSpec[object],
    data: object,
    *,
    location: list[str],
) -> list[FormSpecValidationMessage]:
    if isinstance(spec, Dictionary):
        if not isinstance(data, dict):
            return _type_mismatch(location, "object", data)
        errors: list[FormSpecValidationMessage] = []
        for name, element in spec.elements.items():
            if name in data:
                errors.extend(
                    _walk(
                        element.parameter_form,
                        data[name],
                        location=[*location, name],
                    )
                )
            elif element.required:
                errors.append(
                    FormSpecValidationMessage(
                        location=[*location, name],
                        message="Required field is missing",
                    )
                )
        return errors

    if isinstance(spec, String | MultilineText):
        if not isinstance(data, str):
            return _type_mismatch(location, "string", data)
        return []

    if isinstance(spec, Integer):
        if not isinstance(data, int) or isinstance(data, bool):
            return _type_mismatch(location, "integer", data)
        return []

    if isinstance(spec, Float):
        if not isinstance(data, int | float) or isinstance(data, bool):
            return _type_mismatch(location, "number", data)
        return []

    if isinstance(spec, BooleanChoice):
        if not isinstance(data, bool):
            return _type_mismatch(location, "boolean", data)
        return []

    if isinstance(spec, Password):
        if not isinstance(data, str):
            return _type_mismatch(location, "string", data)
        return []

    if isinstance(spec, FixedValue):
        if data != spec.value:
            return [_msg(location, f"Value must equal {spec.value!r}", data)]
        return []

    if isinstance(spec, SingleChoice):
        valid = {_element_name(el.name) for el in spec.elements}
        if data not in valid:
            return [
                _msg(
                    location,
                    f"Value must be one of {sorted(str(v) for v in valid)}",
                    data,
                )
            ]
        return []

    if isinstance(spec, CascadingSingleChoice):
        if not isinstance(data, list | tuple) or len(data) != 2:
            return [_msg(location, "Expected [choice, value] pair", data)]
        choice, value = data
        for branch in spec.elements:
            if branch.name == choice:
                return _walk(branch.parameter_form, value, location=location)
        return [_msg(location, f"Unknown choice {choice!r}", data)]

    if isinstance(spec, List):
        if not isinstance(data, list):
            return _type_mismatch(location, "array", data)
        out: list[FormSpecValidationMessage] = []
        for idx, item in enumerate(data):
            out.extend(_walk(spec.element_template, item, location=[*location, str(idx)]))
        return out

    raise TypeError(f"FormSpec type {type(spec).__name__} not validatable yet")


def _element_name(name: object) -> object:
    if hasattr(name, "value"):
        return name.value
    return name


def _type_mismatch(
    location: list[str], expected: str, got: object
) -> list[FormSpecValidationMessage]:
    return [_msg(location, f"Expected {expected}, got {_type_name(got)}", got)]


def _msg(
    location: list[str], message: str, invalid_value: object = None
) -> FormSpecValidationMessage:
    return FormSpecValidationMessage(
        location=location, message=message, invalid_value=invalid_value
    )


def _type_name(value: object) -> str:
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
