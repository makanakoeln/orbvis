"""Global settings schema."""

from __future__ import annotations

from pydantic import BaseModel


class GlobalSettings(BaseModel):
    # Object defaults
    icon_size: int = 30
    view_type: str = "icon"
    label_show: bool = True
    label_size: int = 11
    label_color: str = "#ffffff"
    label_background: str = "transparent"
    label_x: int = 0
    label_y: int = 0
    url_target: str = "_blank"
    z: int = 1
    line_style: str | None = None
    # New map defaults
    default_backend_id: str = "live_1"
    default_map_type: str = "static"
    hover_template: str | None = None
    context_template: str | None = None
    # Global Checkmk URL used as fallback when a connection has no checkmk_url set.
    # In Checkmk/OMD deployments this is auto-populated by the backend on first boot.
    checkmk_url: str | None = None
