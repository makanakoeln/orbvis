"""Global settings schema.

Split into two Pydantic models that map 1:1 to the two admin surfaces:

- ``GlobalSettings`` — defaults applied to new boards/objects.
- ``SystemSettings`` — runtime / integration knobs (logging, Checkmk URL).

Storage stays a single ``settings.json`` with all fields flat; each model
parses what it knows and ignores the rest, so backwards compatibility with
older single-flat-file installations is automatic.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Hex (#rrggbb) or the literal "transparent". Mirrors the FormSpec MatchRegex
# in global_settings.py so the API rejects bad values the same way the UI does.
ColorString = Annotated[str, StringConstraints(pattern=r"^(#[0-9a-fA-F]{6}|transparent)$")]


class GlobalSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Object appearance
    icon_size: int = 30
    view_type: str = "icon"
    url_target: str = "_blank"
    z: int = 1
    line_style: str | None = None
    # Object labels
    label_show: bool = True
    label_size: int = 11
    label_color: ColorString = "#ffffff"
    label_background: ColorString = "transparent"
    label_x: int = 0
    label_y: int = 0
    # Object templates
    hover_template: str | None = None
    context_template: str | None = None
    # New-board defaults
    default_backend_id: str = "live_1"
    default_map_type: str = "static"


class SystemSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Overrides the LOG_LEVEL env var (and DEBUG-derived default) when set.
    log_level: LogLevel | None = None
    # Global Checkmk URL used as fallback when a connection has no checkmk_url set.
    # In Checkmk/OMD deployments this is auto-populated by the OrbVis backend on first boot.
    checkmk_url: str | None = None
