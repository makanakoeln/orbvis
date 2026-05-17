# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec localizer hook — Built-in build wires this to cmk.gui.i18n._.

Standalone/MKP keeps the identity default; tests verify that swapping the
localizer at runtime is picked up by every code path that flattens a
``_Localizable`` (Title/Help/Label, Password i18n labels, validation
messages).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest

pytest.importorskip(
    "cmk.rulesets.v1", reason="Standalone build ships without cmk.rulesets.v1", exc_type=ImportError
)

from app.form_specs import OrbColorString, serialize_form_spec, validate_form_data
from app.form_specs._helpers import identity, set_localizer
from app.form_specs._wire_types import WireDictElement, WireDictionary, WirePassword

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError


@pytest.fixture(autouse=True)
def _reset_localizer() -> Iterator[None]:
    """Ensure each test starts with identity and never leaks a custom localizer."""
    set_localizer(identity)
    yield
    set_localizer(identity)


def _spec() -> Dictionary:
    return Dictionary(
        title=Title("Settings"),
        help_text=Help("Help text"),
        elements={
            "name": DictElement(parameter_form=String(title=Title("Name")), required=True),
            "color": DictElement(
                parameter_form=OrbColorString(title=Title("Color")), required=False
            ),
            "secret": DictElement(parameter_form=Password(title=Title("Secret")), required=False),
        },
    )


def test_default_localizer_is_identity() -> None:
    wire = serialize_form_spec(_spec())
    assert wire["title"] == "Settings"
    assert wire["help"] == "Help text"


def test_custom_localizer_called_for_titles_and_help() -> None:
    calls: list[str] = []

    def loc(s: str) -> str:
        calls.append(s)
        return f"[{s}]"

    set_localizer(loc)
    wire = serialize_form_spec(_spec())

    assert wire["title"] == "[Settings]"
    assert wire["help"] == "[Help text]"
    assert "Name" in calls
    assert "Color" in calls
    assert "Secret" in calls


def test_password_i18n_labels_use_localizer() -> None:
    set_localizer(lambda s: f"de:{s}")
    wire = serialize_form_spec(_spec())

    dict_wire = cast(WireDictionary, wire)
    elements: list[WireDictElement] = dict_wire["elements"]
    secret_el = next(el for el in elements if el["name"] == "secret")
    secret_form = cast(WirePassword, secret_el["parameter_form"])
    assert secret_form["type"] == "password"
    i18n = secret_form["i18n"]
    assert i18n["explicit_password"] == "de:Explicit password"
    assert i18n["choose_password_type"] == "de:Choose password type"


def test_custom_validate_message_localised() -> None:
    def must_be_red(value: str) -> None:
        if value != "red":
            raise ValidationError(Message("Value must be 'red'"))

    spec = Dictionary(
        elements={
            "color": DictElement(
                parameter_form=String(custom_validate=(must_be_red,)),
                required=True,
            ),
        },
    )

    set_localizer(lambda s: f"DE({s})")
    errors = validate_form_data(spec, {"color": "blue"})

    assert len(errors) == 1
    assert errors[0].message == "DE(Value must be 'red')"
