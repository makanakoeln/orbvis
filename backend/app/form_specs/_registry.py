# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
# ruff: noqa: ARG002 — polymorphic visitor methods keep all args for subclass overrides
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
from dataclasses import dataclass

from app.form_specs._helpers import loc_required, type_name
from app.form_specs._wire_types import AnyWireFormSpec
from app.form_specs.serialize import FormSpecValidationMessage

from cmk.rulesets.v1.form_specs import FormSpec
from cmk.rulesets.v1.form_specs.validators import ValidationError


@dataclass(frozen=True)
class InvalidValue:
    """Stage-1 parse failure.

    Mirror of ``cmk.gui.form_specs.visitors._type_defs.InvalidValue``: when
    the raw value (typically loaded from disk) has the wrong shape, the
    visitor returns this sentinel carrying a human-readable ``reason`` and
    a safe ``fallback`` of the right shape. Callers can render the
    fallback so the form opens cleanly instead of crashing on
    ``KeyError`` / ``TypeError`` deep inside Vue.
    """

    reason: str
    fallback: object


class FormSpecVisitor[T: FormSpec[object]](ABC):
    """Owns serialise + validate + default + parse + to_disk for one FormSpec.

    Public API surfaces (``serialize``, ``default_value``, ``parse``,
    ``validate``, ``to_disk``) line up with the trio in
    ``cmk.gui.form_specs.visitors._base.FormSpecVisitor`` so that the
    eventual built-in merge is a rename, not a redesign. The 3-stage
    ``validate`` pipeline (parse → nested → custom) matches CMK's
    behaviour: a structurally invalid value gets a single helpful error
    instead of cascading shape mismatches through every nested visitor.
    """

    spec_type: type[FormSpec[object]]

    @abstractmethod
    def serialize(self, spec: T) -> AnyWireFormSpec: ...

    @abstractmethod
    def default_value(self, spec: T) -> object: ...

    def parse(self, spec: T, raw: object) -> object | InvalidValue:
        """Stage-1 shape check; returns the value or an InvalidValue with fallback.

        Default impl runs :meth:`_validate_shape` once and wraps a
        non-empty error list into ``InvalidValue(reason, fallback=default_value)``.
        Subclasses with cheap parse paths can override directly.
        """
        errors = self._validate_shape(spec, raw, [])
        if errors:
            return InvalidValue(reason=errors[0].message, fallback=self.default_value(spec))
        return raw

    def to_disk(self, spec: T, raw: object) -> object:
        """Stage-3 wire→disk serialisation.

        Default identity; override for visitors whose disk shape differs
        from the wire shape (today nothing OrbVis-side, but kept abstract
        so the built-in merge inherits the right contract).
        """
        return raw

    def validate(
        self, spec: T, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        parsed = self.parse(spec, data)
        if isinstance(parsed, InvalidValue):
            return [
                FormSpecValidationMessage(
                    location=list(location),
                    message=parsed.reason,
                    invalid_value=data,
                )
            ]
        nested = self._validate_nested(spec, data, location)
        if nested:
            return nested
        return run_custom_validators(spec, data, location)

    @abstractmethod
    def _validate_shape(
        self, spec: T, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]: ...

    def _validate_nested(
        self, spec: T, data: object, location: list[str]
    ) -> list[FormSpecValidationMessage]:
        """Stage-2 recursion into nested visitors; default is no-op.

        Composite visitors (Dictionary / CascadingSingleChoice / List)
        override to descend; primitives don't.
        """
        return []


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
                    message=loc_required(exc.message),
                    invalid_value=data,
                )
            )
    return out
