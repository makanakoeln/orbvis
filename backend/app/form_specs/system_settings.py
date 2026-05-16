# Copyright (C) 2025 OrbVis - License: GNU General Public License v2
"""FormSpec for the System admin surface (runtime + integration).

Kept separate from ``global_settings.py`` so the Settings page can keep its
„Defaults for new boards and objects" subtitle honest — system-wide toggles
that survive across boards live here.
"""

from __future__ import annotations

from app.form_specs import OrbDictGroup

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    InputHint,
    SingleChoice,
    SingleChoiceElement,
    String,
)

_LOGGING = OrbDictGroup(
    title=Title("Logging"),
    help_text=Help("Backend log verbosity. Empty falls back to the LOG_LEVEL env var."),
    key="logging",
)
_CHECKMK = OrbDictGroup(
    title=Title("Checkmk integration"),
    help_text=Help("URL fallback used by connections without their own checkmk_url."),
    key="checkmk",
)


def system_settings_spec() -> Dictionary:
    return Dictionary(
        title=Title("System"),
        help_text=Help(
            "Runtime and integration options. Changes take effect immediately "
            "and apply across all boards."
        ),
        elements={
            "log_level": DictElement(
                group=_LOGGING,
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
                    prefill=DefaultValue("INFO"),
                ),
            ),
            "checkmk_url": DictElement(
                group=_CHECKMK,
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
        },
    )
