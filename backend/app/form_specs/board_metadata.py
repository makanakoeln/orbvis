# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the metadata subset of a board.

Covers the fields the Pilot vendor renders cleanly: alias, connection,
icon-size override, rotation, templates, click action and visibility.

Type-specific view geometry (worldmap lat/lng/zoom, flow root, radar
filter) plus background image stay in the existing custom Vue surface
because they need live previews / pickers FormSpec doesn't ship.
"""

from __future__ import annotations

from app.form_specs import OrbDictGroup

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    InputHint,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    String,
)

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
    title=Title("Tooltip & context-menu templates"),
    help_text=Help(
        "Override the global hover / context-menu fallback for this board. "
        "Placeholders: {{name}}, {{state}}, {{output}}, {{host}}, {{service}}."
    ),
    key="templates",
)


def _connection_form(choices: list[tuple[str, str]] | None) -> SingleChoice | String:
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
                title=Title(f"{label} ({cid})") if label != cid else Title(cid),
            )
            for cid, label in choices
        ],
    )


def board_metadata_spec(
    connection_choices: list[tuple[str, str]] | None = None,
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
            "rotation_interval": DictElement(
                required=True,
                group=_BEHAVIOR,
                parameter_form=Integer(
                    title=Title("Auto-rotate interval"),
                    help_text=Help(
                        "Seconds until the next board is shown in the rotation. "
                        "0 disables auto-rotate for this board."
                    ),
                    unit_symbol="s",
                    prefill=DefaultValue(0),
                ),
            ),
            "click_action": DictElement(
                required=True,
                group=_BEHAVIOR,
                parameter_form=SingleChoice(
                    title=Title("Click action"),
                    elements=[
                        SingleChoiceElement(name="link", title=Title("Open link")),
                        SingleChoiceElement(name="none", title=Title("No action")),
                    ],
                    prefill=DefaultValue("link"),
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
            "icon_size": DictElement(
                group=_DISPLAY,
                parameter_form=Integer(
                    title=Title("Icon size override"),
                    help_text=Help("Leave empty to inherit the global Icon defaults."),
                    unit_symbol="px",
                ),
            ),
            "hover_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Hover template"),
                    help_text=Help("Overrides the global hover template for this board."),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "context_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Context template"),
                    help_text=Help(
                        "Right-click context-menu fallback. Same placeholders as "
                        "the hover template."
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
