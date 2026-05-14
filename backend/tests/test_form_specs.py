# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec stack — serialisation and validation tests.

Uses real ``cmk.rulesets.v1.form_specs`` classes (installed via
cmk-plugin-apis).
"""

from __future__ import annotations

from app.form_specs import serialize_form_spec, validate_form_data

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    String,
)


def _global_settings_spec() -> Dictionary:
    return Dictionary(
        title=Title("Global Settings"),
        elements={
            "icon_size": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Icon size"),
                    unit_symbol="px",
                    prefill=DefaultValue(30),
                ),
            ),
            "label_show": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Show label"),
                    label=Label("Display labels under each object"),
                    prefill=DefaultValue(True),
                ),
            ),
            "log_level": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Log level"),
                    elements=[
                        SingleChoiceElement(name="DEBUG", title=Title("Debug")),
                        SingleChoiceElement(name="INFO", title=Title("Info")),
                        SingleChoiceElement(name="WARNING", title=Title("Warning")),
                    ],
                ),
            ),
            "hover_template": DictElement(
                parameter_form=String(
                    title=Title("Hover template"),
                ),
            ),
        },
    )


def test_serialize_emits_dictionary_with_typed_children() -> None:
    spec = _global_settings_spec()
    json_spec = serialize_form_spec(spec)

    assert json_spec["type"] == "dictionary"
    assert json_spec["title"] == "Global Settings"
    elements = {el["name"]: el for el in json_spec["elements"]}  # type: ignore[union-attr]
    assert elements["icon_size"]["required"] is True
    assert elements["icon_size"]["parameter_form"]["type"] == "integer"
    assert elements["icon_size"]["parameter_form"]["unit"] == "px"
    assert elements["log_level"]["parameter_form"]["type"] == "single_choice"
    assert elements["hover_template"]["required"] is False


def test_validate_accepts_valid_payload() -> None:
    spec = _global_settings_spec()
    errors = validate_form_data(
        spec,
        {
            "icon_size": 30,
            "label_show": True,
            "log_level": "INFO",
            "hover_template": "{{name}}",
        },
    )
    assert errors == []


def test_validate_reports_missing_required_field() -> None:
    spec = _global_settings_spec()
    errors = validate_form_data(spec, {"icon_size": 30, "label_show": True})
    locations = {tuple(e.location) for e in errors}
    assert ("log_level",) in locations


def test_validate_rejects_invalid_choice() -> None:
    spec = _global_settings_spec()
    errors = validate_form_data(
        spec,
        {"icon_size": 30, "label_show": True, "log_level": "TRACE"},
    )
    assert any(e.location == ["log_level"] for e in errors)


def test_validate_rejects_wrong_type() -> None:
    spec = _global_settings_spec()
    errors = validate_form_data(
        spec,
        {"icon_size": "thirty", "label_show": True, "log_level": "INFO"},
    )
    assert any(e.location == ["icon_size"] and "Expected integer" in e.message for e in errors)


def test_validate_walks_nested_dictionary() -> None:
    inner = Dictionary(
        title=Title("Templates"),
        elements={
            "hover": DictElement(
                required=True,
                parameter_form=String(title=Title("Hover")),
            ),
        },
    )
    outer = Dictionary(
        title=Title("Outer"),
        elements={
            "templates": DictElement(required=True, parameter_form=inner),
        },
    )
    errors = validate_form_data(outer, {"templates": {}})
    assert any(e.location == ["templates", "hover"] for e in errors)


def test_unknown_field_is_silently_ignored() -> None:
    spec = _global_settings_spec()
    errors = validate_form_data(
        spec,
        {
            "icon_size": 30,
            "label_show": True,
            "log_level": "INFO",
            "removed_legacy_key": "old value",
        },
    )
    assert errors == []


def test_validation_message_to_dict_is_json_friendly() -> None:
    spec = _global_settings_spec()
    errors = validate_form_data(spec, {"icon_size": "bad"})
    assert errors
    for err in errors:
        d = err.to_dict()
        assert "location" in d and isinstance(d["location"], list)
        assert "message" in d and isinstance(d["message"], str)
        assert "invalid_value" in d


# ── Connection-Roundtrip (Phase B) ─────────────────────────────────────


def test_connection_config_to_form_data_livestatus_branch() -> None:
    from app.form_specs.connections import config_to_form_data
    from app.schemas.connection import ConnectionConfig

    cfg = ConnectionConfig(
        id="live_1",
        type="livestatus",
        label="Primary",
        socket_path="/omd/sites/SITE/tmp/run/live",
        timeout=10.0,
        automation_user="automation",
        automation_secret="topsecret",
    )
    form = config_to_form_data(cfg)
    assert form["id"] == "live_1"
    assert form["label"] == "Primary"
    type_field = form["type"]
    assert isinstance(type_field, list)
    assert type_field[0] == "livestatus"
    branch = type_field[1]
    assert isinstance(branch, dict)
    assert branch["socket_path"] == "/omd/sites/SITE/tmp/run/live"
    assert branch["automation_secret"] == "topsecret"
    # Icinga2 fields must not leak into a livestatus branch
    assert "icinga2_url" not in branch


def test_connection_form_data_to_config_preserves_redacted_secret() -> None:
    from app.form_specs.connections import config_to_form_data, form_data_to_config
    from app.schemas.connection import REDACTED_SECRET, ConnectionConfig

    stored = ConnectionConfig(
        id="live_1",
        type="livestatus",
        timeout=10.0,
        automation_user="automation",
        automation_secret="REAL-SECRET",
    )
    # API would redact for the response:
    redacted_form = config_to_form_data(
        stored.model_copy(update={"automation_secret": REDACTED_SECRET})
    )
    # Frontend echoes the redaction back unchanged on save:
    rebuilt = form_data_to_config(redacted_form, existing=stored)
    # Real secret survives:
    assert rebuilt.automation_secret == "REAL-SECRET"


def test_connection_form_data_to_config_rejects_unknown_type() -> None:
    from app.form_specs.connections import form_data_to_config

    bad = {"id": "x", "label": "", "type": ["nagiosql", {}]}
    try:
        form_data_to_config(bad)
    except ValueError as exc:
        assert "Unknown backend type" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
