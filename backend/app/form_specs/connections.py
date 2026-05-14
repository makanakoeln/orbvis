# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for a single monitoring connection.

The list-level CRUD (add/remove/clone) stays in the existing
ConnectionsView; FormSpec drives the edit form for one entry. Type is a
CascadingSingleChoice so the field set switches between livestatus,
icinga2 and test in lock-step with the backend ``ConnectionConfig``
discriminator.
"""

from __future__ import annotations

from app.schemas.connection import REDACTED_SECRET, ConnectionConfig

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    Password,
    String,
)

# Field sets per type — kept in one place so the converter doesn't drift
# from the FormSpec branch definitions below.
_LIVESTATUS_FIELDS = (
    "socket_path",
    "host",
    "port",
    "timeout",
    "checkmk_url",
    "automation_user",
    "automation_secret",
)
_ICINGA2_FIELDS = (
    "icinga2_url",
    "icinga2_username",
    "icinga2_password",
    "icinga2_verify_ssl",
    "timeout",
)


def _livestatus_branch() -> Dictionary:
    return Dictionary(
        title=Title("Livestatus connection"),
        elements={
            "socket_path": DictElement(
                parameter_form=String(
                    title=Title("Unix socket path"),
                    help_text=Help(
                        "Either the Unix socket path OR host+port, not both. "
                        "When OrbVis runs inside an OMD site, the socket is at "
                        "tmp/run/live."
                    ),
                    prefill=InputHint("/omd/sites/<site>/tmp/run/live"),
                ),
            ),
            "host": DictElement(
                parameter_form=String(
                    title=Title("TCP host"),
                    prefill=InputHint("livestatus.example.com"),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("TCP port"),
                    prefill=DefaultValue(6557),
                ),
            ),
            "timeout": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(10),
                ),
            ),
            "checkmk_url": DictElement(
                parameter_form=String(
                    title=Title("Checkmk URL"),
                    help_text=Help(
                        "Used for deep links into the Checkmk GUI. Leave empty "
                        "to inherit the global setting."
                    ),
                    prefill=InputHint("/<site>/check_mk"),
                ),
            ),
            "automation_user": DictElement(
                parameter_form=String(
                    title=Title("Automation user"),
                    help_text=Help(
                        "Required for actions (acknowledge, downtime) against the Checkmk REST API."
                    ),
                ),
            ),
            "automation_secret": DictElement(
                parameter_form=Password(
                    title=Title("Automation secret"),
                ),
            ),
        },
    )


def _icinga2_branch() -> Dictionary:
    return Dictionary(
        title=Title("Icinga2 REST API"),
        elements={
            "icinga2_url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Icinga2 URL"),
                    prefill=InputHint("https://icinga.example.com:5665"),
                ),
            ),
            "icinga2_username": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("API username"),
                ),
            ),
            "icinga2_password": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("API password"),
                ),
            ),
            "icinga2_verify_ssl": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Verify SSL certificate"),
                    label=Label("Reject self-signed or invalid certificates"),
                    prefill=DefaultValue(True),
                ),
            ),
            "timeout": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Timeout"),
                    unit_symbol="s",
                    prefill=DefaultValue(10),
                ),
            ),
        },
    )


def _test_branch() -> FixedValue:
    return FixedValue(
        title=Title("Test backend"),
        label=Label("Returns deterministic demo data; no external connection."),
        value=None,
    )


def connection_spec() -> Dictionary:
    # ID lives in the URL, not the FormSpec — edit only.
    return Dictionary(
        title=Title("Edit connection"),
        help_text=Help(
            "Pick the backend type and fill in its connection details. "
            "Stored secrets stay intact when you don't retype them."
        ),
        elements={
            "label": DictElement(
                parameter_form=String(
                    title=Title("Display label"),
                    help_text=Help("Shown in board pickers and the connection list."),
                ),
            ),
            "type": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Backend type"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="livestatus",
                            title=Title("Livestatus (Checkmk / Nagios)"),
                            parameter_form=_livestatus_branch(),
                        ),
                        CascadingSingleChoiceElement(
                            name="icinga2",
                            title=Title("Icinga2 REST API"),
                            parameter_form=_icinga2_branch(),
                        ),
                        CascadingSingleChoiceElement(
                            name="test",
                            title=Title("Test backend (demo)"),
                            parameter_form=_test_branch(),
                        ),
                    ],
                    prefill=DefaultValue("livestatus"),
                ),
            ),
        },
    )


def config_to_form_data(cfg: ConnectionConfig) -> dict[str, object]:
    """Flat ConnectionConfig → nested form-shape with cascading ``type``.

    ``id`` is excluded — it's the URL-segment in the edit endpoint.
    """
    payload = cfg.model_dump()
    branch_fields = _ICINGA2_FIELDS if cfg.type == "icinga2" else _LIVESTATUS_FIELDS
    branch_data: dict[str, object] = {}
    if cfg.type != "test":
        for field in branch_fields:
            value = payload.get(field)
            if value is not None:
                branch_data[field] = value
    return {
        "label": payload.get("label", ""),
        "type": [cfg.type, branch_data if cfg.type != "test" else None],
    }


def form_data_to_config(
    form: dict[str, object],
    existing: ConnectionConfig | None = None,
    *,
    connection_id: str | None = None,
) -> ConnectionConfig:
    """Form-shape → ConnectionConfig.

    The connection ID comes from the URL (``connection_id``) or from
    ``existing.id``; the form doesn't carry it. Stored secrets survive
    the REDACTED sentinel round-trip from *existing*.
    """
    type_field = form.get("type")
    if not isinstance(type_field, list | tuple) or len(type_field) != 2:
        raise ValueError("Malformed 'type' — expected [name, value] pair")
    type_name, branch = type_field
    if type_name not in ("livestatus", "icinga2", "test"):
        raise ValueError(f"Unknown backend type {type_name!r}")
    final_id = connection_id or (existing.id if existing is not None else None)
    if not final_id:
        raise ValueError("Connection ID required")
    raw: dict[str, object] = {
        "id": final_id,
        "type": type_name,
        "label": form.get("label", ""),
    }
    if isinstance(branch, dict):
        raw.update(branch)
    if existing is not None:
        if raw.get("automation_secret") == REDACTED_SECRET:
            raw["automation_secret"] = existing.automation_secret
        if raw.get("icinga2_password") == REDACTED_SECRET:
            raw["icinga2_password"] = existing.icinga2_password
    return ConnectionConfig.model_validate(raw)
