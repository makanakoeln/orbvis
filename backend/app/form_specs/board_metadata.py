# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the metadata subset of a board.

Covers the fields the Pilot vendor renders cleanly: alias, connection,
icon-size override, rotation, templates, click action and visibility.

Type-specific view geometry (worldmap lat/lng/zoom, flow root, radar
filter) plus background image stay in the existing custom Vue surface
because they need live previews / pickers FormSpec doesn't ship.
"""

from __future__ import annotations

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    SingleChoice,
    SingleChoiceElement,
    String,
)


def board_metadata_spec() -> Dictionary:
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
                parameter_form=String(
                    title=Title("Display name"),
                    help_text=Help(
                        "Shown on board cards and in the header. Leave blank to "
                        "fall back to the technical name."
                    ),
                ),
            ),
            "connection_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Connection"),
                    help_text=Help(
                        "Connection ID this board pulls monitoring data from. "
                        "Individual objects can override this."
                    ),
                    prefill=InputHint("live_1"),
                ),
            ),
            "icon_size": DictElement(
                parameter_form=Integer(
                    title=Title("Icon size override"),
                    help_text=Help("Leave empty to inherit the global Icon defaults."),
                    unit_symbol="px",
                ),
            ),
            "rotation_interval": DictElement(
                required=True,
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
                parameter_form=BooleanChoice(
                    title=Title("Show in board list"),
                    label=Label("When disabled, this board is hidden from regular users"),
                    prefill=DefaultValue(True),
                ),
            ),
            "hover_template": DictElement(
                parameter_form=String(
                    title=Title("Hover template"),
                    help_text=Help(
                        "Overrides the global hover template for this board. "
                        "Available placeholders: {{name}}, {{state}}, {{output}}, "
                        "{{host}}, {{service}}."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                ),
            ),
            "context_template": DictElement(
                parameter_form=String(
                    title=Title("Context template"),
                    help_text=Help(
                        "Right-click context-menu fallback. Same placeholders as "
                        "the hover template."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
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
