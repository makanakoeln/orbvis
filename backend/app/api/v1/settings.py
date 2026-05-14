"""Global settings endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user, require_admin
from app.form_specs import serialize_form_spec
from app.form_specs.global_settings import global_settings_spec
from app.models.user import User
from app.schemas.settings import GlobalSettings
from app.services import settings_service

router = APIRouter()


@router.get("", response_model=GlobalSettings)
async def get_settings(current_user: User = Depends(get_current_user)) -> GlobalSettings:
    return settings_service.get_settings()


@router.put("", response_model=GlobalSettings)
async def update_settings(data: GlobalSettings, _: User = Depends(require_admin)) -> GlobalSettings:
    return settings_service.save_settings(data)


@router.get("/schema")
async def get_settings_schema(
    _: User = Depends(require_admin),
) -> dict[str, object]:
    return serialize_form_spec(global_settings_spec())
