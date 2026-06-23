# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for a single monitoring connection.

The list-level CRUD (add/remove/clone) stays in the existing
ConnectionsView; FormSpec drives the edit form for one entry. Type is a
CascadingSingleChoice so the field set switches between livestatus,
icinga2 and test in lock-step with the backend ``ConnectionConfig``
discriminator.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from cmk.orbvis_backend.form_specs import OrbDictGroup
from cmk.orbvis_backend.schemas.connection import REDACTED_SECRET, ConnectionConfig

logger = logging.getLogger(__name__)

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Integer,
    Password,
    String,
)

# Nagios cores need an automation account to fetch metric history via REST.
# CMC sites get rrddata over Livestatus so the credentials never apply — when
# the deployment is detected as CMC we drop the whole group from the spec.
_REST_CREDENTIALS = OrbDictGroup(
    title=Title("Checkmk REST API credentials"),
    help_text=Help(
        "Only used to fetch metric history from Nagios cores; CMC sites "
        "stream metrics over Livestatus. Leave both fields empty when in "
        "doubt — connection testing still works."
    ),
    key="rest_credentials",
)

# Livestatus branch fields outside the ``target`` cascading choice. The
# converter splits target (socket vs TCP) explicitly below.
_LIVESTATUS_FIELDS = (
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


def _omd_socket_prefill() -> InputHint | DefaultValue:
    """Auto-fill the OMD livestatus socket when OrbVis runs inside an OMD site.

    Saves the operator from retyping /omd/sites/<site>/tmp/run/live on every
    new connection. Falls back to a placeholder hint when not in OMD.
    """
    omd_root = os.environ.get("OMD_ROOT")
    if omd_root:
        # /tmp/run/live is the OMD Livestatus Unix-domain socket, not a
        # temp-file path — bandit B108 is a false positive here.
        return DefaultValue(f"{omd_root}/tmp/run/live")  # nosec B108
    return InputHint("/omd/sites/<site>/tmp/run/live")


def _livestatus_target() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Connection target"),
        help_text=Help(
            "Pick Unix socket when OrbVis runs inside the same OMD site as the "
            "monitoring core (path is at tmp/run/live). Pick TCP for remote "
            "Livestatus / xinetd setups."
        ),
        elements=[
            CascadingSingleChoiceElement(
                name="socket",
                title=Title("Unix socket"),
                parameter_form=Dictionary(
                    title=Title("Unix socket"),
                    elements={
                        "socket_path": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Socket path"),
                                prefill=_omd_socket_prefill(),
                                field_size=FieldSize.LARGE,
                            ),
                        ),
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="tcp",
                title=Title("TCP (host + port)"),
                parameter_form=Dictionary(
                    title=Title("TCP endpoint"),
                    elements={
                        "host": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Host"),
                                prefill=InputHint("livestatus.example.com"),
                                field_size=FieldSize.LARGE,
                            ),
                        ),
                        "port": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Port"),
                                prefill=DefaultValue(6557),
                            ),
                        ),
                        "tls": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("TLS"),
                                label=Label("Use TLS (matches OMD LIVESTATUS_TLS=on)"),
                                help_text=Help(
                                    "OMD wraps the 6557 listener in stunnel by default. "
                                    "Disable only when the remote endpoint is plain TCP."
                                ),
                                prefill=DefaultValue(True),
                            ),
                        ),
                        "tls_verify": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("Verify TLS certificate"),
                                label=Label("Reject self-signed or invalid certificates"),
                                help_text=Help(
                                    "OMD ships a self-signed per-site CA — leave this off "
                                    "unless your endpoint presents a publicly trusted cert."
                                ),
                                prefill=DefaultValue(False),
                            ),
                        ),
                    },
                ),
            ),
        ],
        prefill=DefaultValue("socket"),
    )


def _livestatus_branch(include_automation: bool = True) -> Dictionary:
    elements: dict[str, DictElement[object]] = {
        "target": DictElement(
            required=True,
            parameter_form=_livestatus_target(),
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
                field_size=FieldSize.LARGE,
            ),
        ),
    }
    if include_automation:
        elements["automation_user"] = DictElement(
            group=_REST_CREDENTIALS,
            parameter_form=String(
                title=Title("User"),
                prefill=InputHint("automation"),
            ),
        )
        elements["automation_secret"] = DictElement(
            group=_REST_CREDENTIALS,
            parameter_form=Password(
                title=Title("Secret"),
            ),
        )
    return Dictionary(title=Title("Livestatus connection"), elements=elements)


def _icinga2_branch() -> Dictionary:
    return Dictionary(
        title=Title("Icinga2 REST API"),
        elements={
            "icinga2_url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Icinga2 URL"),
                    prefill=InputHint("https://icinga.example.com:5665"),
                    field_size=FieldSize.LARGE,
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


MonitoringCore = Literal["cmc", "nagios"]


def connection_spec(monitoring_core: MonitoringCore | None = None) -> Dictionary:
    """Build the FormSpec; drop automation_user/secret when CMC is detected.

    monitoring_core is ``"cmc"`` / ``"nagios"`` / None. ``None`` includes all
    fields so remote / unknown setups stay editable.
    """
    include_automation = monitoring_core != "cmc"
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
                    help_text=Help("Shown in map pickers and the connection list."),
                    field_size=FieldSize.LARGE,
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
                            parameter_form=_livestatus_branch(
                                include_automation=include_automation
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="icinga2",
                            title=Title("Icinga2 REST API"),
                            parameter_form=_icinga2_branch(),
                        ),
                        # Demo backend lives last so an operator can't pick it
                        # by accident as the first option in the dropdown.
                        CascadingSingleChoiceElement(
                            name="test",
                            title=Title("Test backend (demo data)"),
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
    branch_data: dict[str, object] = {}
    if cfg.type == "livestatus":
        for field in _LIVESTATUS_FIELDS:
            value = payload.get(field)
            if value is not None:
                branch_data[field] = value
        # Target is a CascadingSingleChoice on the wire: ['socket', {socket_path}]
        # or ['tcp', {host, port}]. TCP wins when host is set, socket otherwise.
        if cfg.host:
            branch_data["target"] = [
                "tcp",
                {
                    "host": cfg.host,
                    "port": cfg.port if cfg.port is not None else 6557,
                    "tls": cfg.tls,
                    "tls_verify": cfg.tls_verify,
                },
            ]
        else:
            branch_data["target"] = ["socket", {"socket_path": cfg.socket_path or ""}]
    elif cfg.type == "icinga2":
        for field in _ICINGA2_FIELDS:
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
        if type_name == "livestatus":
            raw.update({k: v for k, v in branch.items() if k != "target"})
            target = branch.get("target")
            if isinstance(target, list | tuple) and len(target) == 2:
                target_name, target_value = target
                if target_name == "tcp" and isinstance(target_value, dict):
                    raw["host"] = target_value.get("host")
                    raw["port"] = target_value.get("port")
                    if "tls" in target_value:
                        raw["tls"] = target_value.get("tls")
                    if "tls_verify" in target_value:
                        raw["tls_verify"] = target_value.get("tls_verify")
                elif target_name == "socket" and isinstance(target_value, dict):
                    raw["socket_path"] = target_value.get("socket_path")
        else:
            raw.update(branch)
    # Password fields come from the FormSpec as a 4-tuple
    # ``[type, store_id, explicit_value, store_used]``. ConnectionConfig
    # expects a plain string — unwrap to the explicit value.
    for pwd_field in ("automation_secret", "icinga2_password"):
        raw[pwd_field] = _unwrap_password(raw.get(pwd_field))
    if existing is not None:
        if raw.get("automation_secret") == REDACTED_SECRET:
            raw["automation_secret"] = existing.automation_secret
        if raw.get("icinga2_password") == REDACTED_SECRET:
            raw["icinga2_password"] = existing.icinga2_password
    return ConnectionConfig.model_validate(raw)


def _unwrap_password(value: object) -> object:
    """FormSpec Password emits ``[type, store_id, explicit, used]``.

    OrbVis only supports explicit passwords (no password store), so we keep
    the explicit slot and discard the rest. Pattern-matches the wire shape
    instead of indexing ``value[2]`` so a CMK-side tuple change shows up as
    a fallthrough (logged) rather than an IndexError at runtime.
    Already-flat strings (e.g. from legacy callers or the REDACTED sentinel)
    pass through unchanged.
    """
    match value:
        case ["explicit_password", _, str(explicit), bool()]:
            return explicit or None
        case ("explicit_password", _, str(explicit), bool()):
            return explicit or None
        case str() | None:
            return value
        case _:
            logger.warning(
                "Unknown FormSpec password shape, passing through unchanged",
                extra={"value_type": type(value).__name__},
            )
            return value
