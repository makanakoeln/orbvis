# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the metadata subset of a board.

Covers the fields the Pilot vendor renders cleanly: alias, connection,
icon-size override, rotation, templates, click action and visibility.

Type-specific view geometry (worldmap lat/lng/zoom, flow root, radar
filter) plus background image stay in the existing custom Vue surface
because they need live previews / pickers FormSpec doesn't ship.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.form_specs import OrbDictGroup, OrbHostString

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
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import NumberInRange

_IDENTIFICATION = OrbDictGroup(
    title=Title("Identification"),
    help_text=Help("Display name and the monitoring connection this board pulls data from."),
    key="identification",
)
_BEHAVIOR = OrbDictGroup(
    title=Title("Behavior"),
    help_text=Help("How the board appears in the rotation and reacts to clicks."),
    key="behavior",
)
_DISPLAY = OrbDictGroup(
    title=Title("Display defaults"),
    help_text=Help("Per-board overrides of the global object defaults."),
    key="display",
)
_TEMPLATES = OrbDictGroup(
    title=Title("Templates"),
    help_text=Help(
        "Per-board overrides for the global hover / context-menu fallback. "
        "Placeholders: {{name}}, {{state}}, {{output}}, {{host}}, {{service}}."
    ),
    key="templates",
)


def _connection_choice_title(cid: str, label: str, backend: str) -> str:
    """Format a SingleChoice title as ``label (id) · backend``."""
    head = f"{label} ({cid})" if label and label != cid else cid
    return f"{head} · {backend}" if backend else head


def _connection_form(
    choices: Sequence[tuple[str, str, str]] | None,
) -> SingleChoice | String:
    # Empty list keeps the form editable on fresh installs that have no
    # connections registered yet — falls back to free-text so the operator
    # can still type the ID they're about to create.
    if not choices:
        return String(
            title=Title("Connection"),
            help_text=Help(
                "Connection ID this board pulls monitoring data from. "
                "Individual objects can override this."
            ),
            prefill=InputHint("live_1"),
            field_size=FieldSize.LARGE,
        )
    return SingleChoice(
        title=Title("Connection"),
        help_text=Help(
            "Monitoring connection this board pulls data from. "
            "Individual objects can override this."
        ),
        elements=[
            SingleChoiceElement(
                name=cid,
                title=Title(_connection_choice_title(cid, label, backend)),
            )
            for cid, label, backend in choices
        ],
    )


def board_metadata_spec(
    connection_choices: Sequence[tuple[str, str, str]] | None = None,
) -> Dictionary:
    return Dictionary(
        title=Title("Board settings"),
        help_text=Help(
            "Metadata that applies to the whole board. Type-specific "
            "view geometry and the background image stay in the custom "
            "editor."
        ),
        elements={
            "alias": DictElement(
                required=True,
                group=_IDENTIFICATION,
                parameter_form=String(
                    title=Title("Display name"),
                    help_text=Help(
                        "Shown on board cards and in the header. Leave blank to "
                        "fall back to the technical name."
                    ),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "connection_id": DictElement(
                required=True,
                group=_IDENTIFICATION,
                parameter_form=_connection_form(connection_choices),
            ),
            "icon_size": DictElement(
                group=_DISPLAY,
                parameter_form=Integer(
                    title=Title("Icon size override"),
                    help_text=Help(
                        "Leave the field disabled to inherit the global Icon "
                        "defaults. Individual objects on the board can still "
                        "override this."
                    ),
                    unit_symbol="px",
                    prefill=DefaultValue(30),
                ),
            ),
            "rotation_interval": DictElement(
                required=True,
                group=_BEHAVIOR,
                # Modeled as CascadingSingleChoice so "off" is an explicit
                # branch instead of the magic value 0; the API endpoint
                # (and the host modal) flattens it back to the on-wire int.
                parameter_form=CascadingSingleChoice(
                    title=Title("Auto-rotate"),
                    help_text=Help(
                        "Show the next board in the rotation after the chosen "
                        "interval. Pick Off to keep this board open until the "
                        "operator switches manually."
                    ),
                    prefill=DefaultValue("off"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="off",
                            title=Title("Off"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="every",
                            title=Title("Every N seconds"),
                            parameter_form=Integer(
                                title=Title("Interval"),
                                unit_symbol="s",
                                prefill=DefaultValue(30),
                                custom_validate=(NumberInRange(min_value=1),),
                            ),
                        ),
                    ],
                ),
            ),
            "click_action": DictElement(
                required=True,
                group=_BEHAVIOR,
                parameter_form=BooleanChoice(
                    title=Title("Interactive"),
                    label=Label("Clicks open object details or follow links"),
                    help_text=Help(
                        "Turn off for read-only lobby / TV displays where clicks "
                        "should do nothing. When on (default), clicks open the "
                        "details slide-in, follow an object URL, or navigate to "
                        "a linked sub-board."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "show_in_lists": DictElement(
                required=True,
                group=_BEHAVIOR,
                parameter_form=BooleanChoice(
                    title=Title("Visibility"),
                    label=Label("Show this board in the boards list"),
                    help_text=Help(
                        "When unchecked, the board is hidden from regular users "
                        "in the boards list and dashboard. Direct links continue "
                        "to work for users who already have view permission."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "hover_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Hover template"),
                    help_text=Help(
                        "Leave unchecked to inherit the global Hover template "
                        "(Settings → Object defaults). When enabled, overrides "
                        "the global default for this board only. "
                        "Placeholders: {{name}}, {{state}}, {{output}}, "
                        "{{host}}, {{service}}. "
                        "Example: '{{name}}: {{state}}' renders as 'db-prod-01: CRIT'."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "context_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Context template"),
                    help_text=Help(
                        "Leave unchecked to inherit the global Context template "
                        "(Settings → Object defaults). When enabled, overrides "
                        "the global default for this board only. Same "
                        "placeholders as the hover template. "
                        "Example: 'Service {{service}} on {{host}}' renders as "
                        "'Service HTTP on web-srv-01'."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
        },
    )


# Metadata fields the FormSpec covers; used by the API to slice
# BoardRead → form-data and merge form-data → BoardUpdate. Anything not
# in this set stays out of the FormSpec contract.
METADATA_FIELDS = (
    "alias",
    "connection_id",
    "icon_size",
    "rotation_interval",
    "click_action",
    "show_in_lists",
    "hover_template",
    "context_template",
)


def rotation_to_form(interval: object) -> list[object]:
    """Flat ``rotation_interval`` int → CascadingSingleChoice wire shape."""
    if isinstance(interval, int) and interval > 0:
        return ["every", interval]
    return ["off", None]


def rotation_from_form(cascading: object) -> int:
    """CascadingSingleChoice wire shape → flat ``rotation_interval`` int."""
    if isinstance(cascading, list | tuple) and len(cascading) == 2:
        choice, value = cascading
        if choice == "every" and isinstance(value, int):
            return int(value)
    return 0


_TOPOLOGY = OrbDictGroup(
    title=Title("Hosts & Layer"),
    help_text=Help(
        "Which slice of the host graph this Flow board renders, and how "
        "many service rows are drawn per host."
    ),
    key="topology",
)


def flow_view_spec() -> Dictionary:
    """FormSpec for the per-board fields of :class:`schemas.board.FlowView`.

    Mirrors the field ranges declared on the Pydantic model so the
    serialized schema and the on-wire validation can't drift.
    Every field is optional — unchecked means "use the global default".
    """
    return Dictionary(
        title=Title("Hosts & Layer"),
        elements={
            "root": DictElement(
                group=_TOPOLOGY,
                parameter_form=OrbHostString(
                    title=Title("Root host"),
                    help_text=Help(
                        "Host the topology is anchored on. Leave unchecked "
                        "to render the full topology."
                    ),
                    prefill=InputHint("Choose root host…"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "child_layers": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Child layers"),
                    help_text=Help(
                        "Hops downward from the root. -1 means unlimited "
                        "(default), 0–20 otherwise. Leave unchecked to "
                        "inherit the global default."
                    ),
                    unit_symbol="layers",
                    prefill=DefaultValue(-1),
                    custom_validate=(NumberInRange(min_value=-1, max_value=20),),
                ),
            ),
            "parent_layers": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Parent layers"),
                    help_text=Help(
                        "Hops upward from the root. -1 means unlimited, "
                        "0 means none (default), max 20. Leave unchecked "
                        "to inherit the global default."
                    ),
                    unit_symbol="layers",
                    prefill=DefaultValue(0),
                    custom_validate=(NumberInRange(min_value=-1, max_value=20),),
                ),
            ),
            "top_affected_hosts": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Hosts with service detail"),
                    help_text=Help(
                        "How many top-affected hosts get service detail "
                        "(0–1000). Leave unchecked to inherit the global "
                        "default (25)."
                    ),
                    unit_symbol="hosts",
                    prefill=DefaultValue(25),
                    custom_validate=(NumberInRange(min_value=0, max_value=1000),),
                ),
            ),
            "max_services_per_host": DictElement(
                group=_TOPOLOGY,
                parameter_form=Integer(
                    title=Title("Services per host"),
                    help_text=Help(
                        "Maximum services rendered per host (0–500). "
                        "Leave unchecked to inherit the global default (50)."
                    ),
                    unit_symbol="services",
                    prefill=DefaultValue(50),
                    custom_validate=(NumberInRange(min_value=0, max_value=500),),
                ),
            ),
        },
    )
