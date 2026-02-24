"""Map CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.deps import get_current_user, require_admin
from app.models.user import User
from app.schemas.map import MapConfig, MapCreate, MapObject, MapRead, MapUpdate
from app.services import map_service

router = APIRouter()


@router.get("", response_model=list[MapRead])
async def list_maps(_: User = Depends(get_current_user)) -> list[MapRead]:
    return map_service.list_maps()


@router.post("", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def create_map(
    data: MapCreate, _: User = Depends(require_admin)
) -> MapConfig:
    try:
        return map_service.create_map(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{name}", response_model=MapConfig)
async def get_map(name: str, _: User = Depends(get_current_user)) -> MapConfig:
    cfg = map_service.get_map(name)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg


@router.put("/{name}", response_model=MapConfig)
async def update_map(
    name: str, data: MapUpdate, _: User = Depends(require_admin)
) -> MapConfig:
    cfg = map_service.update_map(name, data)
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_map(name: str, _: User = Depends(require_admin)) -> None:
    if not map_service.delete_map(name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")


# ----- Object sub-resources -----

@router.post("/{name}/objects", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def add_object(
    name: str, obj: MapObject, _: User = Depends(require_admin)
) -> MapConfig:
    try:
        cfg = map_service.add_object(name, obj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found")
    return cfg


@router.put("/{name}/objects/{obj_id}", response_model=MapObject)
async def update_object(
    name: str, obj_id: str, updates: dict, _: User = Depends(require_admin)
) -> MapObject:
    obj = map_service.update_object(name, obj_id, updates)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    return obj


@router.delete("/{name}/objects/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    name: str, obj_id: str, _: User = Depends(require_admin)
) -> None:
    if not map_service.delete_object(name, obj_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
