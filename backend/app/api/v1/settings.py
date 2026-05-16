"""Global settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, require_admin
from app.form_specs import serialize_form_spec
from app.form_specs.global_settings import global_settings_spec
from app.models.user import User
from app.schemas.settings import GlobalSettings
from app.services import connection_service, settings_service

router = APIRouter()


@router.get("", response_model=GlobalSettings, response_model_exclude_none=True)
async def get_settings(current_user: User = Depends(get_current_user)) -> GlobalSettings:
    """Return saved settings, omitting Optional fields that are unset.

    The FormSpec frontend uses ``key in data`` to decide whether an optional
    field's toggle is active — sending ``null`` would render an empty input
    behind an "active" checkbox, which is confusing. Drop ``null`` so the
    toggle stays off and the InputHint placeholder takes over.
    """
    return settings_service.get_settings()


@router.put("", response_model=GlobalSettings)
async def update_settings(data: GlobalSettings, _: User = Depends(require_admin)) -> GlobalSettings:
    return settings_service.save_settings(data)


@router.get("/schema")
async def get_settings_schema(
    _: User = Depends(require_admin),
) -> dict[str, object]:
    # Default-Connection is a SingleChoice over actual connection IDs — load
    # them here so the FormSpec validates the saved value against real targets
    # instead of accepting a typo.
    connection_ids = [c.id for c in connection_service.load_all()]
    return serialize_form_spec(global_settings_spec(connection_ids))
