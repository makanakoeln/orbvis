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

from app.form_specs import OrbColorString, OrbDictGroup
from app.object_options import LINE_STYLES

from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Integer,
    MultilineText,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import MatchRegex, NumberInRange

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
_COLOR_ERROR = Message("Use a 6-digit hex code like '#ffffff' or the literal 'transparent'.")


def _default_connection_element(
    connection_choices: Sequence[tuple[str, str]],
) -> DictElement[object]:
    """Render Connection as SingleChoice over actual connections.

    A free-text String let a typo silently break every newly created board's
    state lookup. Empty list → keep field disabled with a helpful message
    that nudges the operator toward the Connections page first.
    """
    if connection_choices:
        return DictElement(
            required=True,
            group=_BOARD_DEFAULTS,
            parameter_form=SingleChoice(
                title=Title("Connection"),
                help_text=Help("Pre-selected when creating a new board."),
                elements=[
                    SingleChoiceElement(name=cid, title=Title(label or cid))
                    for cid, label in connection_choices
                ],
                prefill=DefaultValue(connection_choices[0][0]),
            ),
        )
    return DictElement(
        required=True,
        group=_BOARD_DEFAULTS,
        parameter_form=String(
            title=Title("Connection"),
            help_text=Help(
                "No connections configured yet. Open Administration → Connections "
                "and add one — then come back here to set it as the default."
            ),
            field_size=FieldSize.LARGE,
        ),
    )


def global_settings_spec(
    connection_choices: Sequence[tuple[str, str]] | None = None,
) -> Dictionary:
    choices = tuple(connection_choices or ())
    return Dictionary(
        title=Title("Global Settings"),
        help_text=Help(
            "Default values applied when creating new boards and objects. "
            "Per-board overrides take precedence."
        ),
        elements={
            # ── Board defaults ──
            "default_backend_id": _default_connection_element(choices),
            "default_map_type": DictElement(
                required=True,
                group=_BOARD_DEFAULTS,
                parameter_form=SingleChoice(
                    title=Title("Board type"),
                    help_text=Help("Pre-selected board type in the 'New board' modal."),
                    elements=[
                        SingleChoiceElement(name="static", title=Title("Static board")),
                        SingleChoiceElement(name="worldmap", title=Title("Geo board")),
                        SingleChoiceElement(name="flow", title=Title("Flow board")),
                        SingleChoiceElement(name="radar", title=Title("Radar")),
                    ],
                    prefill=DefaultValue("static"),
                ),
            ),
            "default_render_mode": DictElement(
                required=True,
                group=_BOARD_DEFAULTS,
                parameter_form=SingleChoice(
                    title=Title("Rendering style"),
                    help_text=Help(
                        "Pre-selected rendering style for new boards. NagVis-classic "
                        "anchors objects top-left with flat textboxes on a light "
                        "canvas; imported NagVis maps switch to it automatically "
                        "regardless of this default."
                    ),
                    elements=[
                        SingleChoiceElement(name="default", title=Title("OrbVis (default)")),
                        SingleChoiceElement(name="nagvis_classic", title=Title("NagVis-classic")),
                    ],
                    prefill=DefaultValue("default"),
                ),
            ),
            # Optional — most installs use the same tile server everywhere, so
            # pin it here once instead of pasting the URL into every Geo board.
            # ``None`` keeps each board's per-board ``tile_url`` choice intact.
            "default_tile_url": DictElement(
                group=_BOARD_DEFAULTS,
                parameter_form=String(
                    title=Title("Default tile URL (Geo boards)"),
                    help_text=Help(
                        "Map-tile server applied to new Geo boards. Use the OSM-style "
                        "template syntax with {z}/{x}/{y}. Leave unset to let each "
                        "board pick its own default."
                    ),
                    prefill=InputHint("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"),
                    field_size=FieldSize.LARGE,
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
                    custom_validate=(NumberInRange(min_value=8, max_value=256),),
                ),
            ),
            # Elements come from app.object_options.LINE_STYLES — the
            # canonical name+title list also served by the registry endpoint.
            # The per-object EditPanel hits that same endpoint at boot, so the
            # two surfaces can never drift again.
            "line_style": DictElement(
                required=True,
                group=_OBJECT_APPEARANCE,
                parameter_form=SingleChoice(
                    title=Title("Line style"),
                    help_text=Help(
                        "Default stroke style for new objects of type 'line'. "
                        "Has no effect on icons, text or gadgets."
                    ),
                    elements=[
                        SingleChoiceElement(name=name, title=Title(title))
                        for name, title in LINE_STYLES
                    ],
                    prefill=DefaultValue("plain"),
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
                    ],
                    prefill=DefaultValue("_blank"),
                ),
            ),
            # "Stacking order (Z)" intentionally omitted from the Global
            # Settings UI — default 1 is fine for ~every install, and the
            # per-object EditPanel exposes the field where it actually
            # matters (the few maps that need explicit layering). Pydantic
            # storage keeps the field with default=1 for backward-compat.
            # ── Object defaults / Labels ──
            # CascadingSingleChoice is the canonical FormSpec way to model
            # "field only matters when this toggle is on". The endpoint
            # ``GET /settings/form`` maps this nested shape onto the flat
            # ``label_*`` keys still used by every board renderer; the
            # hidden branch keeps the saved tuning values around so the
            # operator can flip Show off → on without losing color/size.
            "labels": DictElement(
                required=True,
                group=_OBJECT_LABELS,
                parameter_form=CascadingSingleChoice(
                    title=Title("Object labels"),
                    help_text=Help("Caption text shown next to icons."),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="hidden",
                            title=Title("Don't display labels"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="shown",
                            title=Title("Display labels under each object"),
                            parameter_form=Dictionary(
                                elements={
                                    "size": DictElement(
                                        required=True,
                                        parameter_form=Integer(
                                            title=Title("Size"),
                                            unit_symbol="px",
                                            prefill=DefaultValue(11),
                                        ),
                                    ),
                                    "color": DictElement(
                                        required=True,
                                        parameter_form=OrbColorString(
                                            title=Title("Color"),
                                            prefill=DefaultValue("#ffffff"),
                                            custom_validate=(
                                                MatchRegex(_COLOR_REGEX, error_msg=_COLOR_ERROR),
                                            ),
                                        ),
                                    ),
                                    "background": DictElement(
                                        required=True,
                                        parameter_form=OrbColorString(
                                            title=Title("Background"),
                                            prefill=DefaultValue("transparent"),
                                            custom_validate=(
                                                MatchRegex(_COLOR_REGEX, error_msg=_COLOR_ERROR),
                                            ),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    ],
                    prefill=DefaultValue("shown"),
                ),
            ),
            # ── Object defaults / Templates ──
            # MultilineText (not String) because realistic templates run
            # several lines — HTML markup, multiple placeholders, leading
            # newline for layout. A single-line field forces operators to
            # type unreadable one-liners.
            "hover_template": DictElement(
                group=_OBJECT_TEMPLATES,
                parameter_form=MultilineText(
                    title=Title("Hover template"),
                    help_text=Help("Shown on hover when a board has no template of its own."),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                ),
            ),
            "context_template": DictElement(
                group=_OBJECT_TEMPLATES,
                parameter_form=MultilineText(
                    title=Title("Context-menu template"),
                    help_text=Help(
                        "Right-click fallback. Same placeholders as the hover template."
                    ),
                    prefill=InputHint("e.g. {{name}} is {{state}}"),
                ),
            ),
        },
    )
