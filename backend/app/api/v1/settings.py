"""Global + system settings endpoints.

The flat ``GET/PUT /settings`` + ``GET/PUT /settings/system`` endpoints are
cmk-free and always available — they back the Standalone admin UI via the
legacy Vue forms. The ``/form``, ``/schema`` siblings reshape the flat
records into the FormSpec wire payload the vendored dispatcher renders;
they only register when :mod:`cmk.rulesets.v1` is importable.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from app.api.v1.deps import get_current_user, require_configure
from app.form_specs import FORM_SPECS_AVAILABLE
from app.models.user import User
from app.object_options import LINE_STYLES
from app.schemas.settings import GlobalSettings, SystemSettings
from app.services import settings_service

if FORM_SPECS_AVAILABLE:
    from app.form_specs import serialize_form_spec
    from app.form_specs._wire_types import AnyWireFormSpec
    from app.form_specs.global_settings import global_settings_spec
    from app.form_specs.system_settings import system_settings_spec
    from app.services import connection_service

router = APIRouter()


# ── Global (board / object defaults) ──────────────────────────────────────


@router.get("", response_model=GlobalSettings, response_model_exclude_none=True)
async def get_settings(current_user: User = Depends(get_current_user)) -> GlobalSettings:
    """Return saved defaults, omitting Optional fields that are unset.

    The FormSpec frontend uses ``key in data`` to decide whether an optional
    field's toggle is active — sending ``null`` would render an empty input
    behind an "active" checkbox, which is confusing. Drop ``null`` so the
    toggle stays off and the InputHint placeholder takes over.
    """
    return settings_service.get_global_settings()


@router.put("", response_model=GlobalSettings)
async def update_settings(
    data: GlobalSettings, _: User = Depends(require_configure)
) -> GlobalSettings:
    return settings_service.save_global_settings(data)


# ── System (runtime / integration) ────────────────────────────────────────


@router.get("/system", response_model=SystemSettings, response_model_exclude_none=True)
async def get_system_settings(_: User = Depends(get_current_user)) -> SystemSettings:
    return settings_service.get_system_settings()


@router.put("/system", response_model=SystemSettings)
async def update_system_settings(
    data: SystemSettings, _: User = Depends(require_configure)
) -> SystemSettings:
    return settings_service.save_system_settings(data)


@router.get("/object-options")
async def get_object_options(
    _: User = Depends(get_current_user),
) -> dict[str, list[dict[str, str]]]:
    """Canonical name+title catalogues for per-object choice fields.

    Served as plain JSON (not FormSpec) because the per-object EditPanel
    in the frontend renders these via its own non-FormSpec dropdowns —
    same data backs both Global Settings FormSpec and the EditPanel.
    """
    return {
        "line_styles": [{"name": name, "title": title} for name, title in LINE_STYLES],
    }


# ── FormSpec form view ────────────────────────────────────────────────────
#
# Storage on disk + the regular ``GET/PUT /settings`` endpoints stay flat
# (``label_show``, ``label_size``, …) so every existing consumer keeps
# working unchanged. The ``/form`` pair below reshapes that flat record
# into the nested CascadingSingleChoice payload the FormSpec dispatcher
# expects, and unpacks it again on save. Hidden ⇒ flat ``label_show=False``
# while preserving the last-known tuning values, so the operator can
# toggle Show off → on without losing their color/size tweaks.

if FORM_SPECS_AVAILABLE:

    def _to_form(s: GlobalSettings) -> dict[str, Any]:
        labels: list[Any]
        if s.label_show:
            labels = [
                "shown",
                {
                    "size": s.label_size,
                    "color": s.label_color,
                    "background": s.label_background,
                },
            ]
        else:
            labels = ["hidden", None]
        return {
            "default_backend_id": s.default_backend_id,
            "default_map_type": s.default_map_type,
            "default_render_mode": s.default_render_mode,
            "view_type": s.view_type,
            "icon_size": s.icon_size,
            "line_style": s.line_style,
            "url_target": s.url_target,
            "labels": labels,
            # Optional templates / URLs only included when set, matching the flat
            # ``response_model_exclude_none`` behaviour upstream.
            **({"hover_template": s.hover_template} if s.hover_template is not None else {}),
            **({"context_template": s.context_template} if s.context_template is not None else {}),
            **({"default_tile_url": s.default_tile_url} if s.default_tile_url is not None else {}),
        }

    def _from_form(form: dict[str, Any], current: GlobalSettings) -> GlobalSettings:
        labels = form.get("labels")
        if not isinstance(labels, list) or len(labels) != 2:
            raise HTTPException(status_code=422, detail="labels must be a [kind, payload] pair")
        kind, payload = labels
        if kind == "shown":
            if not isinstance(payload, dict):
                raise HTTPException(
                    status_code=422, detail="labels.shown payload must be an object"
                )
            label_show = True
            label_size = int(payload.get("size", current.label_size))
            label_color = str(payload.get("color", current.label_color))
            label_background = str(payload.get("background", current.label_background))
        elif kind == "hidden":
            # Preserve last-known tuning values — toggling Show off shouldn't
            # erase the operator's careful color/size choices.
            label_show = False
            label_size = current.label_size
            label_color = current.label_color
            label_background = current.label_background
        else:
            raise HTTPException(status_code=422, detail=f"unknown labels branch: {kind!r}")

        try:
            return GlobalSettings(
                icon_size=int(form.get("icon_size", current.icon_size)),
                view_type=str(form.get("view_type", current.view_type)),
                url_target=str(form.get("url_target", current.url_target)),
                # Stacking order is no longer exposed in the Global Settings
                # UI — preserve whatever is already on disk.
                z=current.z,
                line_style=str(form.get("line_style") or current.line_style),
                label_show=label_show,
                label_size=label_size,
                label_color=label_color,
                label_background=label_background,
                hover_template=form.get("hover_template"),
                context_template=form.get("context_template"),
                default_backend_id=str(form.get("default_backend_id", current.default_backend_id)),
                default_map_type=str(form.get("default_map_type", current.default_map_type)),
                default_render_mode=(
                    "nagvis_classic"
                    if form.get("default_render_mode") == "nagvis_classic"
                    else "default"
                ),
                default_tile_url=form.get("default_tile_url") or None,
            )
        except ValidationError as e:
            # Re-shape Pydantic's loc=["label_color"] into the nested form
            # loc=["labels", "shown", "color"] so the FormEdit highlights the
            # actual rendered field instead of a key that doesn't exist in
            # the form view.
            flat_to_nested = {
                "label_size": ["labels", "shown", "size"],
                "label_color": ["labels", "shown", "color"],
                "label_background": ["labels", "shown", "background"],
            }
            details: list[dict[str, Any]] = []
            for err in e.errors():
                loc: list[Any] = list(err.get("loc") or [])
                first = str(loc[0]) if loc else ""
                if first in flat_to_nested:
                    loc = list(flat_to_nested[first]) + loc[1:]
                details.append(
                    {
                        "loc": loc,
                        "msg": err.get("msg"),
                        "type": err.get("type"),
                        "input": err.get("input"),
                    }
                )
            raise HTTPException(status_code=422, detail=details) from e

    @router.get("/form")
    async def get_settings_form(_: User = Depends(get_current_user)) -> dict[str, object]:
        return _to_form(settings_service.get_global_settings())

    @router.put("/form")
    async def update_settings_form(
        data: dict[str, object],
        _: User = Depends(require_configure),
    ) -> dict[str, object]:
        current = settings_service.get_global_settings()
        flat = _from_form(dict(data), current)
        return _to_form(settings_service.save_global_settings(flat))

    @router.get("/schema")
    async def get_settings_schema(
        _: User = Depends(require_configure),
    ) -> AnyWireFormSpec:
        # Default-Connection is a SingleChoice over actual connection IDs — load
        # them here so the FormSpec validates the saved value against real targets
        # instead of accepting a typo.
        connection_choices = [(c.id, c.label) for c in connection_service.load_all()]
        return serialize_form_spec(global_settings_spec(connection_choices))

    def _optional_str(v: object) -> str | None:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return v
        raise ValueError(f"expected string, got {type(v).__name__}")

    def _optional_int(v: object) -> int | None:
        if v is None or v == "":
            return None
        if isinstance(v, bool):
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            return int(v)
        raise ValueError(f"expected int-like value, got {type(v).__name__}")

    def _system_to_form(s: SystemSettings) -> dict[str, object]:
        """Flat SystemSettings → FormSpec wire shape.

        Maps the storage shape (``log_level: LogLevel | None``) into the
        FormSpec singleton-with-sentinel shape (``log_level: "env_default"
        | "DEBUG" | …``). The two int knobs piggy-back unchanged but get
        dropped when ``None`` so the optional-toggle stays inactive.
        """
        out: dict[str, object] = {
            "log_level": s.log_level if s.log_level is not None else "env_default",
        }
        if s.checkmk_url is not None:
            out["checkmk_url"] = s.checkmk_url
        if s.state_refresh_interval is not None:
            out["state_refresh_interval"] = s.state_refresh_interval
        if s.access_token_expire_minutes is not None:
            out["access_token_expire_minutes"] = s.access_token_expire_minutes
        out["enable_folder_boards"] = s.enable_folder_boards
        out["enable_graph_objects"] = s.enable_graph_objects
        return out

    def _system_from_form(form: dict[str, object]) -> SystemSettings:
        raw_level = form.get("log_level", "env_default")
        log_level: object
        if raw_level == "env_default":
            log_level = None
        else:
            log_level = raw_level
        try:
            return SystemSettings(
                log_level=log_level,  # type: ignore[arg-type]
                checkmk_url=_optional_str(form.get("checkmk_url")),
                state_refresh_interval=_optional_int(form.get("state_refresh_interval")),
                access_token_expire_minutes=_optional_int(form.get("access_token_expire_minutes")),
                enable_folder_boards=bool(form.get("enable_folder_boards", False)),
                enable_graph_objects=bool(form.get("enable_graph_objects", True)),
            )
        except ValidationError as e:
            details: list[dict[str, object]] = []
            for err in e.errors():
                details.append(
                    {
                        "loc": list(err.get("loc") or []),
                        "msg": err.get("msg"),
                        "type": err.get("type"),
                        "input": err.get("input"),
                    }
                )
            raise HTTPException(status_code=422, detail=details) from e

    @router.get("/system/form")
    async def get_system_settings_form(_: User = Depends(get_current_user)) -> dict[str, object]:
        return _system_to_form(settings_service.get_system_settings())

    @router.put("/system/form")
    async def update_system_settings_form(
        data: dict[str, object],
        _: User = Depends(require_configure),
    ) -> dict[str, object]:
        flat = _system_from_form(dict(data))
        return _system_to_form(settings_service.save_system_settings(flat))

    @router.get("/system/schema")
    async def get_system_settings_schema(_: User = Depends(require_configure)) -> AnyWireFormSpec:
        return serialize_form_spec(system_settings_spec())
