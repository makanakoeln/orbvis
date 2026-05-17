# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""Visitor registry for FormSpec serialise/validate/default.

Mirrors the visitor pattern from
``cmk.gui.form_specs.visitors._registry`` so behaviour stays one
indirection away from upstream: each FormSpec type has one visitor that
owns *all three* operations, and ``get_visitor()`` resolves via the
class MRO so subclasses (``OrbColorString``) match before their base
(``String``) without depending on registration order.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.form_specs._helpers import identity, type_name
from app.form_specs._wire_types import AnyWireFormSpec
from app.form_specs.serialize import FormSpecValidationMessage

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs.validators import ValidationError


class FormSpecVisitor[T: FormSpec[object]](ABC):
    """Owns serialise + validate + default for one FormSpec class."""

    spec_type: type[FormSpec[object]]

    @abstractmethod
    def serialize(self, spec: T) -> AnyWireFormSpec: ...

    @abstractmethod
    def default_value(self, spec: T) -> object: ...

    def validate(
        self, spec: T, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        errors = self._validate_shape(spec, data, location)
        if errors:
            return errors
        return run_custom_validators(spec, data, location)

    @abstractmethod
    def _validate_shape(
        self, spec: T, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]: ...


_REGISTRY: dict[type[FormSpec[object]], FormSpecVisitor[FormSpec[object]]] = {}


def register[T: FormSpec[object]](visitor: FormSpecVisitor[T]) -> FormSpecVisitor[T]:
    _REGISTRY[visitor.spec_type] = visitor
    return visitor


def get_visitor(spec: FormSpec[object]) -> FormSpecVisitor[FormSpec[object]]:
    for cls in type(spec).__mro__:
        if cls in _REGISTRY:
            return _REGISTRY[cls]
    raise TypeError(f"No FormSpec visitor registered for {type(spec).__name__}")


def msg(
    location: list[str], message: str, invalid_value: object = None
) -> FormSpecValidationMessage:
    return FormSpecValidationMessage(
        location=location, message=message, invalid_value=invalid_value
    )


def type_mismatch(
    location: list[str], expected: str, got: object
) -> list[FormSpecValidationMessage]:
    return [msg(location, f"Expected {expected}, got {type_name(got)}", got)]


def run_custom_validators(
    spec: FormSpec[object], data: object, location: list[str]
) -> list[FormSpecValidationMessage]:
    """Execute ``spec.custom_validate`` and convert ValidationError to messages.

    Mirrors stage 3 of cmk.gui.form_specs.visitors._base.FormSpecVisitor.validate
    (``compute_validation_errors``): only runs after shape/nested checks pass,
    because re-validating a value that's already wrong type just produces noise.
    """
    custom = getattr(spec, "custom_validate", None)
    if not custom:
        return []
    out: list[FormSpecValidationMessage] = []
    for validator in custom:
        try:
            validator(data)
        except ValidationError as exc:
            out.append(
                FormSpecValidationMessage(
                    location=list(location),
                    message=exc.message.localize(identity),
                    invalid_value=data,
                )
            )
    return out
