# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the System admin surface (runtime + integration).

Kept separate from ``global_settings.py`` so the Settings page can keep its
„Defaults for new maps and objects" subtitle honest — system-wide toggles
that survive across maps live here.
"""

from __future__ import annotations

from cmk.orbvis_backend.form_specs import OrbDictGroup

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
from cmk.rulesets.v1.form_specs.validators import MatchRegex, NumberInRange

# Single "Server" group bundles log verbosity, poll cadence and session
# lifetime. Splitting them into Logging / Runtime / etc. produced 1-field
# sidebar sections that looked broken; the operator audit flagged the same
# concern, so they live together under one heading.
_SERVER = OrbDictGroup(
    title=Title("Server runtime"),
    help_text=Help("Log verbosity, poll cadence and session lifetime — applies to every map."),
    key="server",
)
_CHECKMK = OrbDictGroup(
    title=Title("Checkmk integration"),
    help_text=Help("URL fallback used by connections without their own checkmk_url."),
    key="checkmk",
)
_FEATURES = OrbDictGroup(
    title=Title("Features"),
    help_text=Help("Opt-in map types and capabilities."),
    key="features",
)

# Reject path-only strings like ``/SITE`` that look like a URL but break
# every per-connection fallback. The base URL has to be a proper absolute
# http(s) URL the browser can hit.
_URL_REGEX = r"^https?://.+"
_URL_ERROR = Message("Must be a full URL starting with http:// or https://.")


def system_settings_spec() -> Dictionary:
    return Dictionary(
        title=Title("System"),
        help_text=Help(
            "Runtime and integration options. Changes take effect immediately "
            "and apply across all maps."
        ),
        elements={
            # ``env_default`` is a sentinel branch (not a real Python log
            # level) — the /system/form mapper turns it into ``None`` so
            # the runtime falls back to the LOG_LEVEL env var. Avoids the
            # confusing optional-toggle the upstream FormDictionary draws
            # when ``required`` is unset.
            "log_level": DictElement(
                required=True,
                group=_SERVER,
                parameter_form=SingleChoice(
                    title=Title("Log level"),
                    help_text=Help(
                        "Choose 'Use environment default' to follow the LOG_LEVEL "
                        "environment variable. Any explicit level here overrides it."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="env_default", title=Title("Use environment default")
                        ),
                        SingleChoiceElement(name="DEBUG", title=Title("Debug")),
                        SingleChoiceElement(name="INFO", title=Title("Info")),
                        SingleChoiceElement(name="WARNING", title=Title("Warning")),
                        SingleChoiceElement(name="ERROR", title=Title("Error")),
                        SingleChoiceElement(name="CRITICAL", title=Title("Critical")),
                    ],
                    prefill=DefaultValue("env_default"),
                ),
            ),
            "checkmk_url": DictElement(
                group=_CHECKMK,
                parameter_form=String(
                    title=Title("Checkmk base URL"),
                    help_text=Help(
                        "Fallback Checkmk URL used when a connection has no checkmk_url "
                        "of its own. Auto-populated on OMD deployments; set explicitly "
                        "in dev setups. Must be a full http(s) URL — leave unset to "
                        "rely on per-connection values only."
                    ),
                    prefill=InputHint("https://checkmk.example.com/mysite"),
                    field_size=FieldSize.LARGE,
                    custom_validate=(MatchRegex(_URL_REGEX, error_msg=_URL_ERROR),),
                ),
            ),
            "state_refresh_interval": DictElement(
                group=_SERVER,
                parameter_form=Integer(
                    title=Title("State refresh interval"),
                    help_text=Help(
                        "How often the backend re-polls connection state. Lower = "
                        "more live but more load on the monitoring backend. "
                        "Unchecked uses the STATE_REFRESH_INTERVAL env default."
                    ),
                    unit_symbol="s",
                    prefill=DefaultValue(5),
                    custom_validate=(NumberInRange(min_value=1, max_value=300),),
                ),
            ),
            "access_token_expire_minutes": DictElement(
                group=_SERVER,
                parameter_form=Integer(
                    title=Title("Login session lifetime"),
                    help_text=Help(
                        "How long an access token stays valid before the browser has "
                        "to silently refresh. Short = more re-auth, better revocation. "
                        "Unchecked uses the ACCESS_TOKEN_EXPIRE_MINUTES env default."
                    ),
                    unit_symbol="min",
                    prefill=DefaultValue(60),
                    custom_validate=(NumberInRange(min_value=5, max_value=1440),),
                ),
            ),
            "enable_folder_maps": DictElement(
                required=True,
                group=_FEATURES,
                parameter_form=BooleanChoice(
                    title=Title("Folder maps"),
                    label=Label("Offer the SETUP folder-tree map type"),
                    help_text=Help(
                        "Adds the Folder map type to the map-type picker when "
                        "creating or editing a map. Existing folder maps keep "
                        "rendering even while this is off."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
            "enable_graph_objects": DictElement(
                required=True,
                group=_FEATURES,
                parameter_form=BooleanChoice(
                    title=Title("Graph objects"),
                    label=Label("Offer the (experimental) graph object type"),
                    help_text=Help(
                        "Adds the Graph object to the add-object picker when editing "
                        "a map. Existing graph objects keep rendering even while "
                        "this is off."
                    ),
                    prefill=DefaultValue(True),
                ),
            ),
            "enable_presentation_maps": DictElement(
                required=True,
                group=_FEATURES,
                parameter_form=BooleanChoice(
                    title=Title("Presentation maps"),
                    label=Label("Offer the (experimental) presentation map type"),
                    help_text=Help(
                        "Adds the Presentation map type — a design-first, slide-style "
                        "surface — to the map-type picker. Existing presentation maps "
                        "keep rendering even while this is off."
                    ),
                    prefill=DefaultValue(False),
                ),
            ),
        },
    )
