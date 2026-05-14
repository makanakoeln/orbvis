# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the Global Settings admin surface.

Mirrors the Pydantic ``GlobalSettings`` model 1:1 for every field that maps
cleanly to a vendored FormSpec component. Grouped into topical sections so
the vendored FormDictionary renders them as labelled groups instead of a
flat list.
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

_DEFAULTS = OrbDictGroup(
    title=Title("Object defaults"),
    help_text=Help("Applied to newly placed objects unless the board overrides them."),
    key="defaults",
)
_LABELS = OrbDictGroup(
    title=Title("Labels"),
    help_text=Help("Caption text shown next to icons."),
    key="labels",
)
_BOARD_DEFAULTS = OrbDictGroup(
    title=Title("Board defaults"),
    help_text=Help("Pre-selected values when creating a new board."),
    key="board_defaults",
)
_TEMPLATES = OrbDictGroup(
    title=Title("Tooltip & context-menu templates"),
    help_text=Help(
        "Global fallbacks used when a board or object defines no template "
        "of its own. Placeholders: {{name}}, {{state}}, {{output}}."
    ),
    key="templates",
)
_SYSTEM = OrbDictGroup(
    title=Title("System"),
    help_text=Help("Runtime / integration options."),
    key="system",
)


def global_settings_spec() -> Dictionary:
    return Dictionary(
        title=Title("Global Settings"),
        help_text=Help(
            "Default values applied when creating new boards and objects. "
            "Per-board overrides take precedence."
        ),
        elements={
            "icon_size": DictElement(
                required=True,
                group=_DEFAULTS,
                parameter_form=Integer(
                    title=Title("Icon size"),
                    help_text=Help("Default pixel size for object icons on a board."),
                    unit_symbol="px",
                    prefill=DefaultValue(30),
                ),
            ),
            "view_type": DictElement(
                required=True,
                group=_DEFAULTS,
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
                group=_DEFAULTS,
                parameter_form=Integer(
                    title=Title("Stacking order (Z)"),
                    help_text=Help("Higher value = drawn in front."),
                    prefill=DefaultValue(1),
                ),
            ),
            "url_target": DictElement(
                required=True,
                group=_DEFAULTS,
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
                group=_LABELS,
                parameter_form=BooleanChoice(
                    title=Title("Show object labels"),
                    label=Label("Display labels under each object"),
                    prefill=DefaultValue(True),
                ),
            ),
            "label_size": DictElement(
                required=True,
                group=_LABELS,
                parameter_form=Integer(
                    title=Title("Label size"),
                    unit_symbol="px",
                    prefill=DefaultValue(11),
                ),
            ),
            "label_x": DictElement(
                required=True,
                group=_LABELS,
                parameter_form=Integer(
                    title=Title("Label X offset"),
                    prefill=DefaultValue(0),
                ),
            ),
            "label_y": DictElement(
                required=True,
                group=_LABELS,
                parameter_form=Integer(
                    title=Title("Label Y offset"),
                    prefill=DefaultValue(0),
                ),
            ),
            "default_backend_id": DictElement(
                required=True,
                group=_BOARD_DEFAULTS,
                parameter_form=String(
                    title=Title("Default connection"),
                    help_text=Help("Connection ID pre-selected when creating a new board."),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "default_map_type": DictElement(
                required=True,
                group=_BOARD_DEFAULTS,
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
            "checkmk_url": DictElement(
                group=_BOARD_DEFAULTS,
                parameter_form=String(
                    title=Title("Checkmk base URL"),
                    help_text=Help(
                        "Fallback Checkmk URL for connections without their own. "
                        "Auto-populated when OrbVis runs inside a Checkmk OMD site."
                    ),
                    prefill=InputHint("https://checkmk.example.com/mysite"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "hover_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Hover template"),
                    help_text=Help("Shown on hover when a board has no template of its own."),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "context_template": DictElement(
                group=_TEMPLATES,
                parameter_form=String(
                    title=Title("Context-menu template"),
                    help_text=Help(
                        "Right-click fallback. Same placeholders as the hover template."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "log_level": DictElement(
                group=_SYSTEM,
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
