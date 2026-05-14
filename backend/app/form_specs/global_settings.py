# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the Global Settings admin surface.

Pilot scope mirrors the Pydantic ``GlobalSettings`` model 1:1 for every
field that maps cleanly to a vendored FormSpec component. Colour fields
and optional discriminated unions wait for follow-up vendor work — they
fall back to the existing Pydantic-backed POST until then.
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


def global_settings_spec() -> Dictionary:
    return Dictionary(
        title=Title("Global Settings"),
        elements={
            "icon_size": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Icon size"),
                    help_text=Help("Default pixel size for object icons on a board."),
                    unit_symbol="px",
                    prefill=DefaultValue(30),
                ),
            ),
            "view_type": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("View type"),
                    elements=[
                        SingleChoiceElement(name="icon", title=Title("Icon")),
                        SingleChoiceElement(name="text", title=Title("Text only")),
                        SingleChoiceElement(name="gadget", title=Title("Gadget")),
                    ],
                    prefill=DefaultValue("icon"),
                ),
            ),
            "z": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Stacking order (Z)"),
                    help_text=Help("Higher value = drawn in front."),
                    prefill=DefaultValue(1),
                ),
            ),
            "url_target": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Link target"),
                    elements=[
                        SingleChoiceElement(name="_blank", title=Title("New tab")),
                        SingleChoiceElement(name="_self", title=Title("Same tab")),
                        SingleChoiceElement(name="_top", title=Title("Top frame")),
                    ],
                    prefill=DefaultValue("_blank"),
                ),
            ),
            "label_show": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("Show object labels"),
                    label=Label("Display labels under each object"),
                    prefill=DefaultValue(True),
                ),
            ),
            "label_size": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Label size"),
                    unit_symbol="px",
                    prefill=DefaultValue(11),
                ),
            ),
            "label_x": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Label X offset"),
                    prefill=DefaultValue(0),
                ),
            ),
            "label_y": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Label Y offset"),
                    prefill=DefaultValue(0),
                ),
            ),
            "default_backend_id": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Default connection"),
                    help_text=Help("Connection ID pre-selected when creating a new board."),
                ),
            ),
            "default_map_type": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Default board type"),
                    elements=[
                        SingleChoiceElement(name="static", title=Title("Static board")),
                        SingleChoiceElement(name="worldmap", title=Title("Geo board")),
                        SingleChoiceElement(name="flow", title=Title("Flow board")),
                        SingleChoiceElement(name="radar", title=Title("Radar")),
                    ],
                    prefill=DefaultValue("static"),
                ),
            ),
            "hover_template": DictElement(
                parameter_form=String(
                    title=Title("Hover template"),
                    help_text=Help(
                        "Global fallback shown on hover when a board or object has no "
                        "template of its own. Use {{name}}, {{state}}, {{output}} etc."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                ),
            ),
            "context_template": DictElement(
                parameter_form=String(
                    title=Title("Context template"),
                    help_text=Help(
                        "Right-click context-menu fallback. Same placeholders as the "
                        "hover template."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                ),
            ),
            "checkmk_url": DictElement(
                parameter_form=String(
                    title=Title("Checkmk base URL"),
                    help_text=Help(
                        "Fallback Checkmk URL for connections without their own. "
                        "Auto-populated when OrbVis runs inside a Checkmk OMD site."
                    ),
                    prefill=InputHint("https://checkmk.example.com/mysite"),
                ),
            ),
            "log_level": DictElement(
                parameter_form=SingleChoice(
                    title=Title("Log level"),
                    help_text=Help(
                        "Backend log threshold. Empty falls back to the LOG_LEVEL "
                        "environment variable."
                    ),
                    elements=[
                        SingleChoiceElement(name="DEBUG", title=Title("Debug")),
                        SingleChoiceElement(name="INFO", title=Title("Info")),
                        SingleChoiceElement(name="WARNING", title=Title("Warning")),
                        SingleChoiceElement(name="ERROR", title=Title("Error")),
                        SingleChoiceElement(name="CRITICAL", title=Title("Critical")),
                    ],
                ),
            ),
        },
    )
