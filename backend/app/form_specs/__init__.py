# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""OrbVis FormSpec stack — re-exports the relevant subset of
:mod:`cmk.rulesets.v1` plus the OrbVis-side serialiser and validator
used by API endpoints. The vendored frontend dispatcher under
``frontend/src/vendor/cmk/form/`` consumes the JSON emitted by these.
"""

from dataclasses import dataclass

from app.form_specs.serialize import (
    FormSpecValidationMessage,
    serialize_form_spec,
)
from app.form_specs.validate import validate_form_data

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    DictGroup,
    Dictionary,
    FieldSize,
    FixedValue,
    Float,
    FormSpec,
    InputHint,
    Integer,
    List,
    MultilineText,
    Password,
    SingleChoice,
    SingleChoiceElement,
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

    layout: str = "vertical"
    key: str | None = None


__all__ = [
    "BooleanChoice",
    "CascadingSingleChoice",
    "CascadingSingleChoiceElement",
    "DefaultValue",
    "DictElement",
    "Dictionary",
    "FieldSize",
    "FixedValue",
    "Float",
    "FormSpec",
    "FormSpecValidationMessage",
    "Help",
    "InputHint",
    "Integer",
    "Label",
    "List",
    "Message",
    "MultilineText",
    "OrbDictGroup",
    "Password",
    "SingleChoice",
    "SingleChoiceElement",
    "String",
    "Title",
    "serialize_form_spec",
    "validate_form_data",
]
