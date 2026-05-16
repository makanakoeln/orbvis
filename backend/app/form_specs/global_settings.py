# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the Global Settings admin surface (board / object defaults).

Two top-level groups feed the sidebar:

- ``board_defaults`` — selected when creating a new board.
- ``object_*`` — selected when placing a new object. Split into three
  sub-groups (``object_appearance`` / ``object_labels`` / ``object_templates``)
  so the frontend can render visual sub-sections under one sidebar entry.

Runtime / integration settings (logging, Checkmk URL) live in
``system_settings.py`` and have their own admin tab.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.form_specs import OrbDictGroup

from cmk.rulesets.v1 import Help, Label, Message, Title
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
from cmk.rulesets.v1.form_specs.validators import MatchRegex

_BOARD_DEFAULTS = OrbDictGroup(
    title=Title("Board defaults"),
    help_text=Help("Pre-selected values when creating a new board."),
    key="board_defaults",
)
_OBJECT_APPEARANCE = OrbDictGroup(
    title=Title("Appearance"),
    help_text=Help("How objects are rendered by default on a new board."),
    key="object_appearance",
)
_OBJECT_LABELS = OrbDictGroup(
    title=Title("Labels"),
    help_text=Help("Caption text shown next to icons."),
    key="object_labels",
)
_OBJECT_TEMPLATES = OrbDictGroup(
    title=Title("Templates"),
    help_text=Help(
        "Global fallbacks used when a board or object defines no template "
        "of its own. Placeholders: {{name}}, {{state}}, {{output}}."
    ),
    key="object_templates",
)

_COLOR_REGEX = r"^(#[0-9a-fA-F]{6}|transparent)$"
_COLOR_HELP = Help(
    "Hex code like '#1a73e8' or the literal 'transparent'. "
    "Native color picker is not part of the FormSpec component set yet."
)
_COLOR_ERROR = Message("Use a 6-digit hex code like '#ffffff' or the literal 'transparent'.")


def _default_connection_element(connection_ids: Sequence[str]) -> DictElement[object]:
    """Render Default connection as SingleChoice over actual connection IDs.

    A free-text String let a typo silently break every newly created board's
    state lookup. Empty list → keep field disabled with a helpful message.
    """
    if connection_ids:
        return DictElement(
            required=True,
            group=_BOARD_DEFAULTS,
            parameter_form=SingleChoice(
                title=Title("Default connection"),
                help_text=Help("Connection pre-selected when creating a new board."),
                elements=[
                    SingleChoiceElement(name=cid, title=Title(cid)) for cid in connection_ids
                ],
                prefill=DefaultValue(connection_ids[0]),
            ),
        )
    return DictElement(
        required=True,
        group=_BOARD_DEFAULTS,
        parameter_form=String(
            title=Title("Default connection"),
            help_text=Help(
                "Connection ID pre-selected when creating a new board. "
                "Create a connection first to enable selection from a list."
            ),
            field_size=FieldSize.LARGE,
        ),
    )


def global_settings_spec(connection_ids: Sequence[str] | None = None) -> Dictionary:
    cids = tuple(connection_ids or ())
    return Dictionary(
        title=Title("Global Settings"),
        help_text=Help(
            "Default values applied when creating new boards and objects. "
            "Per-board overrides take precedence."
        ),
        elements={
            # ── Board defaults ──
            "default_backend_id": _default_connection_element(cids),
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
            # ── Object defaults / Appearance ──
            "view_type": DictElement(
                required=True,
                group=_OBJECT_APPEARANCE,
                parameter_form=SingleChoice(
                    title=Title("View type"),
                    help_text=Help("How objects are rendered on a board."),
                    elements=[
                        SingleChoiceElement(name="icon", title=Title("Icon")),
                        SingleChoiceElement(name="text", title=Title("Text only")),
                        SingleChoiceElement(name="gadget", title=Title("Gadget")),
                    ],
                    prefill=DefaultValue("icon"),
                ),
            ),
            "icon_size": DictElement(
                required=True,
                group=_OBJECT_APPEARANCE,
                parameter_form=Integer(
                    title=Title("Icon size"),
                    help_text=Help("Default pixel size for object icons on a board."),
                    unit_symbol="px",
                    prefill=DefaultValue(30),
                ),
            ),
            "line_style": DictElement(
                group=_OBJECT_APPEARANCE,
                parameter_form=SingleChoice(
                    title=Title("Line style"),
                    help_text=Help("Default stroke style for connection lines."),
                    elements=[
                        SingleChoiceElement(name="solid", title=Title("Solid")),
                        SingleChoiceElement(name="dashed", title=Title("Dashed")),
                        SingleChoiceElement(name="dotted", title=Title("Dotted")),
                    ],
                ),
            ),
            "url_target": DictElement(
                required=True,
                group=_OBJECT_APPEARANCE,
                parameter_form=SingleChoice(
                    title=Title("Link target"),
                    help_text=Help("Where object links open."),
                    elements=[
                        SingleChoiceElement(name="_blank", title=Title("New tab")),
                        SingleChoiceElement(name="_self", title=Title("Same tab")),
                        SingleChoiceElement(name="_top", title=Title("Top frame")),
                    ],
                    prefill=DefaultValue("_blank"),
                ),
            ),
            "z": DictElement(
                required=True,
                group=_OBJECT_APPEARANCE,
                parameter_form=Integer(
                    title=Title("Stacking order (Z)"),
                    help_text=Help("Higher value = drawn in front. Touched once per install."),
                    prefill=DefaultValue(1),
                ),
            ),
            # ── Object defaults / Labels ──
            "label_show": DictElement(
                required=True,
                group=_OBJECT_LABELS,
                parameter_form=BooleanChoice(
                    title=Title("Show object labels"),
                    label=Label("Display labels under each object"),
                    prefill=DefaultValue(True),
                ),
            ),
            "label_size": DictElement(
                required=True,
                group=_OBJECT_LABELS,
                parameter_form=Integer(
                    title=Title("Label size"),
                    unit_symbol="px",
                    prefill=DefaultValue(11),
                ),
            ),
            "label_color": DictElement(
                required=True,
                group=_OBJECT_LABELS,
                parameter_form=String(
                    title=Title("Label color"),
                    help_text=_COLOR_HELP,
                    prefill=DefaultValue("#ffffff"),
                    custom_validate=(MatchRegex(_COLOR_REGEX, error_msg=_COLOR_ERROR),),
                ),
            ),
            "label_background": DictElement(
                required=True,
                group=_OBJECT_LABELS,
                parameter_form=String(
                    title=Title("Label background"),
                    help_text=_COLOR_HELP,
                    prefill=DefaultValue("transparent"),
                    custom_validate=(MatchRegex(_COLOR_REGEX, error_msg=_COLOR_ERROR),),
                ),
            ),
            "label_x": DictElement(
                required=True,
                group=_OBJECT_LABELS,
                parameter_form=Integer(
                    title=Title("Label X offset"),
                    help_text=Help("Horizontal shift. Set once per install."),
                    unit_symbol="px",
                    prefill=DefaultValue(0),
                ),
            ),
            "label_y": DictElement(
                required=True,
                group=_OBJECT_LABELS,
                parameter_form=Integer(
                    title=Title("Label Y offset"),
                    help_text=Help("Vertical shift. Set once per install."),
                    unit_symbol="px",
                    prefill=DefaultValue(0),
                ),
            ),
            # ── Object defaults / Templates ──
            "hover_template": DictElement(
                group=_OBJECT_TEMPLATES,
                parameter_form=String(
                    title=Title("Hover template"),
                    help_text=Help("Shown on hover when a board has no template of its own."),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
            "context_template": DictElement(
                group=_OBJECT_TEMPLATES,
                parameter_form=String(
                    title=Title("Context-menu template"),
                    help_text=Help(
                        "Right-click fallback. Same placeholders as the hover template."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                    field_size=FieldSize.LARGE,
                ),
            ),
        },
    )
