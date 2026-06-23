# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""OrbVis FormSpec stack — re-exports the relevant subset of
:mod:`cmk.rulesets.v1` plus the OrbVis-side serialiser and validator
used by API endpoints. The vendored frontend dispatcher under
``frontend/src/vendor/cmk/form/`` consumes the JSON emitted by these.

The Standalone (Docker) distribution ships without ``cmk.rulesets.v1``;
in that case ``FORM_SPECS_AVAILABLE`` is False and the names below are
not defined. API consumers gate FormSpec route registration on the
flag and fall back to the flat pydantic CRUD endpoints.
"""

try:
    from cmk.orbvis_backend.form_specs.serialize import (
        FormSpecValidationMessage,
        OrbColorString,
        OrbDictGroup,
        OrbHostString,
        serialize_form_spec,
    )
    from cmk.orbvis_backend.form_specs.validate import validate_form_data

    from cmk.rulesets.v1 import Help, Label, Message, Title
    from cmk.rulesets.v1.form_specs import (
        BooleanChoice,
        CascadingSingleChoice,
        CascadingSingleChoiceElement,
        DefaultValue,
        DictElement,
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

    FORM_SPECS_AVAILABLE = True
except ImportError:
    FORM_SPECS_AVAILABLE = False

__all__ = [
    "FORM_SPECS_AVAILABLE",
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
    "OrbColorString",
    "OrbDictGroup",
    "OrbHostString",
    "Password",
    "SingleChoice",
    "SingleChoiceElement",
    "String",
    "Title",
    "serialize_form_spec",
    "validate_form_data",
]
