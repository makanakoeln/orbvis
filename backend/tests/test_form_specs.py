# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec stack — serialisation and validation tests.

Uses real ``cmk.rulesets.v1.form_specs`` classes (installed via
cmk-plugin-apis).
"""

from __future__ import annotations

from app.form_specs import OrbColorString, serialize_form_spec, validate_form_data

from cmk.rulesets.v1 import Label, Message, Title
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
from cmk.rulesets.v1.form_specs.validators import MatchRegex, NumberInRange


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
    # id stays out of the form payload — it's the URL segment on save.
    assert "id" not in form
    assert form["label"] == "Primary"
    type_field = form["type"]
    assert isinstance(type_field, list)
    assert type_field[0] == "livestatus"
    branch = type_field[1]
    assert isinstance(branch, dict)
    # ``target`` is a CascadingSingleChoice [name, dict] that splits unix-socket
    # from TCP — schaut nach dem Unix-socket-Pfad in der "socket" branch.
    assert branch["target"] == ["socket", {"socket_path": "/omd/sites/SITE/tmp/run/live"}]
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


def test_connection_roundtrip_livestatus_tcp() -> None:
    from app.form_specs.connections import config_to_form_data, form_data_to_config
    from app.schemas.connection import ConnectionConfig

    cfg = ConnectionConfig(
        id="tcp_live",
        type="livestatus",
        label="Remote",
        host="livestatus.example.com",
        port=6557,
        timeout=10.0,
    )
    form = config_to_form_data(cfg)
    branch = form["type"][1]
    assert branch["target"] == [
        "tcp",
        {"host": "livestatus.example.com", "port": 6557},
    ]
    assert "socket_path" not in branch
    rebuilt = form_data_to_config(form, connection_id="tcp_live")
    assert rebuilt.host == "livestatus.example.com"
    assert rebuilt.port == 6557
    assert rebuilt.socket_path is None


def test_connection_roundtrip_icinga2() -> None:
    from app.form_specs.connections import config_to_form_data, form_data_to_config
    from app.schemas.connection import ConnectionConfig

    cfg = ConnectionConfig(
        id="icinga",
        type="icinga2",
        label="Icinga",
        icinga2_url="https://icinga.example.com:5665",
        icinga2_username="root",
        icinga2_password="secret",
        icinga2_verify_ssl=True,
        timeout=15.0,
    )
    form = config_to_form_data(cfg)
    branch = form["type"][1]
    assert branch["icinga2_url"] == "https://icinga.example.com:5665"
    assert branch["icinga2_verify_ssl"] is True
    rebuilt = form_data_to_config(form, connection_id="icinga")
    assert rebuilt.type == "icinga2"
    assert rebuilt.icinga2_url == "https://icinga.example.com:5665"


def test_connection_roundtrip_test_backend() -> None:
    from app.form_specs.connections import config_to_form_data, form_data_to_config
    from app.schemas.connection import ConnectionConfig

    cfg = ConnectionConfig(id="demo", type="test", label="Demo")
    form = config_to_form_data(cfg)
    assert form["type"] == ["test", None]
    rebuilt = form_data_to_config(form, connection_id="demo")
    assert rebuilt.type == "test"


def test_socket_path_rejects_relative() -> None:
    from app.schemas.connection import ConnectionConfig

    try:
        ConnectionConfig(id="x", type="livestatus", socket_path="relative/path")
    except ValueError as exc:
        assert "absolute" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for relative socket_path")


def test_socket_path_rejects_dotdot() -> None:
    from app.schemas.connection import ConnectionConfig

    try:
        ConnectionConfig(id="x", type="livestatus", socket_path="/omd/sites/../etc/shadow")
    except ValueError as exc:
        assert ".." in str(exc)
    else:
        raise AssertionError("Expected ValueError for '..' in socket_path")


def test_socket_path_rejects_nul_byte() -> None:
    from app.schemas.connection import ConnectionConfig

    try:
        ConnectionConfig(id="x", type="livestatus", socket_path="/tmp/foo\x00bar")
    except ValueError as exc:
        assert "NUL" in str(exc)
    else:
        raise AssertionError("Expected ValueError for NUL in socket_path")


def test_socket_path_accepts_absolute() -> None:
    from app.schemas.connection import ConnectionConfig

    cfg = ConnectionConfig(id="x", type="livestatus", socket_path="/omd/sites/foo/tmp/run/live")
    assert cfg.socket_path == "/omd/sites/foo/tmp/run/live"


def test_connection_form_data_unwraps_password_tuple() -> None:
    """FormSpec emits passwords as [type, store_id, explicit, used] — backend must unwrap."""
    from app.form_specs.connections import form_data_to_config

    form = {
        "label": "icinga",
        "type": [
            "icinga2",
            {
                "icinga2_url": "https://icinga.example.com:5665",
                "icinga2_username": "root",
                "icinga2_password": ["explicit_password", "", "secret123", False],
                "icinga2_verify_ssl": True,
                "timeout": 15,
            },
        ],
    }
    cfg = form_data_to_config(form, connection_id="icinga")
    assert cfg.icinga2_password == "secret123"


# ── custom_validate (Step F) ───────────────────────────────────────────


def test_custom_validate_match_regex_fails_for_invalid_string() -> None:
    """MatchRegex on a String must surface as a FormSpecValidationMessage."""
    spec = Dictionary(
        title=Title("S"),
        elements={
            "color": DictElement(
                required=True,
                parameter_form=OrbColorString(
                    title=Title("Color"),
                    custom_validate=(
                        MatchRegex(
                            r"^(#[0-9a-fA-F]{6}|transparent)$",
                            error_msg=Message("Use a 6-digit hex or 'transparent'."),
                        ),
                    ),
                ),
            ),
        },
    )
    errors = validate_form_data(spec, {"color": "not-a-hex"})
    assert any(e.location == ["color"] and "hex" in e.message for e in errors), (
        f"expected MatchRegex error, got {errors}"
    )


def test_custom_validate_passes_for_valid_string() -> None:
    spec = Dictionary(
        title=Title("S"),
        elements={
            "color": DictElement(
                required=True,
                parameter_form=OrbColorString(
                    title=Title("Color"),
                    custom_validate=(
                        MatchRegex(
                            r"^(#[0-9a-fA-F]{6}|transparent)$",
                            error_msg=Message("Invalid."),
                        ),
                    ),
                ),
            ),
        },
    )
    assert validate_form_data(spec, {"color": "#ffffff"}) == []
    assert validate_form_data(spec, {"color": "transparent"}) == []


def test_custom_validate_skipped_on_shape_mismatch() -> None:
    """If the shape check fails, custom_validate must not run — mirrors CMK's
    3-stage validate where stage 3 only triggers on a clean stage-1/2.
    """
    spec = Dictionary(
        title=Title("S"),
        elements={
            "color": DictElement(
                required=True,
                parameter_form=OrbColorString(
                    title=Title("Color"),
                    custom_validate=(MatchRegex(r"^never$", error_msg=Message("regex")),),
                ),
            ),
        },
    )
    errors = validate_form_data(spec, {"color": 123})
    # Only the type-mismatch error — no regex error, because shape already failed.
    assert len(errors) == 1
    assert "Expected string" in errors[0].message


def test_custom_validate_number_in_range_on_integer() -> None:
    spec = Dictionary(
        title=Title("S"),
        elements={
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Port"),
                    custom_validate=(NumberInRange(min_value=1, max_value=65535),),
                ),
            ),
        },
    )
    assert validate_form_data(spec, {"port": 6557}) == []
    errors = validate_form_data(spec, {"port": 0})
    assert any(e.location == ["port"] for e in errors)
