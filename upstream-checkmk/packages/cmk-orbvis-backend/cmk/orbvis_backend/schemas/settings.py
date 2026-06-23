#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Global settings schema.

Split into two Pydantic models that map 1:1 to the two admin surfaces:

- ``GlobalSettings`` — defaults applied to new maps/objects.
- ``SystemSettings`` — runtime / integration knobs (logging, Checkmk URL).

Storage stays a single ``settings.json`` with all fields flat; each model
parses what it knows and ignores the rest, so backwards compatibility with
older single-flat-file installations is automatic.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from cmk.orbvis_backend.schemas._validators import coerce_user_url

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Hex (#rrggbb) or the literal "transparent". Mirrors the FormSpec MatchRegex
# in global_settings.py so the API rejects bad values the same way the UI does.
# A BeforeValidator (not StringConstraints) so the 422 detail carries a
# human-readable msg the FormEdit can surface verbatim, instead of Pydantic's
# default "String should match pattern '^(#…)$'" regex dump.
_COLOR_RE = re.compile(r"^(#[0-9a-fA-F]{6}|transparent)$")


def _validate_color(v: object) -> str:
    if not isinstance(v, str) or not _COLOR_RE.match(v):
        raise ValueError("Use a 6-digit hex code like '#ffffff' or the literal 'transparent'.")
    return v


ColorString = Annotated[str, BeforeValidator(_validate_color)]


def _validate_icon_size(v: object) -> int:
    if not isinstance(v, int) or isinstance(v, bool):
        raise ValueError("Icon size must be an integer between 8 and 256 pixels.")
    if v < 8 or v > 256:
        raise ValueError("Icon size must be between 8 and 256 pixels.")
    return v


# Same BeforeValidator trick as ColorString: hand-rolled message wins
# over Pydantic's default "Input should be greater than or equal to 8"
# when surfaced through the FormEdit validation banner.
IconSize = Annotated[int, BeforeValidator(_validate_icon_size)]


class GlobalSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Object appearance
    icon_size: IconSize = Field(default=30)
    view_type: str = "icon"
    # Older settings.json may store legacy frame targets like "_top"; coerce to
    # a value the FormSpec dropdown can render with its title.
    url_target: Annotated[
        str,
        BeforeValidator(lambda v: v if v in {"_blank", "_self"} else "_blank"),
    ] = "_blank"
    z: int = 1
    # ``None`` is a legacy state from before the FormSpec migration — coerce it
    # so the dropdown renders the factory default instead of an empty field.
    line_style: Annotated[str, BeforeValidator(lambda v: v or "plain")] = "plain"
    # Object labels
    label_show: bool = True
    label_size: int = 11
    label_color: ColorString = "#ffffff"
    label_background: ColorString = "transparent"
    # Object templates
    hover_template: str | None = None
    context_template: str | None = None
    # New-map defaults
    default_backend_id: str = "live_1"
    default_map_type: str = "static"
    default_render_mode: Literal["default", "nagvis_classic"] = "default"
    # Default tile URL applied to new Geo maps. ``None`` keeps the per-map
    # default the MapSettingsModal already picks (CartoDB dark in dark mode).
    default_tile_url: Annotated[str | None, BeforeValidator(coerce_user_url)] = None
    # Instance-wide default for the Home maps overview: visual card grid
    # (default) or scannable table. The per-operator preference lives in the
    # browser's localStorage (useMapListViewMode) and overrides this.
    map_list_view: Literal["cards", "table"] = "cards"


class SystemSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Overrides the LOG_LEVEL env var (and DEBUG-derived default) when set.
    log_level: LogLevel | None = None
    # Global Checkmk URL used as fallback when a connection has no checkmk_url set.
    # In Checkmk/OMD deployments this is auto-populated by the OrbVis backend on first boot.
    # Empty string allowed for "no override"; non-empty must be a proper http(s) URL.
    checkmk_url: str | None = None
    # Runtime knobs that used to live in env-only ``core/config.py``. Migrated
    # here so an operator can tune them without restarting the backend, and
    # so the values survive site upgrades that re-render the env file.
    # ``None`` falls back to the ``Settings`` env default at request time.
    state_refresh_interval: Annotated[int, Field(ge=1, le=300)] | None = None
    access_token_expire_minutes: Annotated[int, Field(ge=5, le=1440)] | None = None
    # Feature flag: expose the (newer) SETUP folder-tree map type in the
    # map-type picker. Off by default so operators opt in explicitly; existing
    # folder maps keep rendering regardless.
    enable_folder_maps: bool = False
    # Feature flag: offer the (still experimental) graph object type in the
    # add-object picker. On by default; existing graph objects keep rendering
    # even when an operator turns it off.
    enable_graph_objects: bool = True
    # Feature flag: offer the (experimental) presentation map type in the
    # map-type picker. Off by default so operators opt in explicitly; existing
    # presentation maps keep rendering regardless.
    enable_presentation_maps: bool = False
