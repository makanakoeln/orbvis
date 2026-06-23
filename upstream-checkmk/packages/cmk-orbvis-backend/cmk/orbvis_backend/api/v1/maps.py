#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Map CRUD endpoints."""

from __future__ import annotations

import asyncio
import io
import json
import os
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import JSONResponse

from cmk.orbvis_backend.api.v1.deps import (
    can_edit_map,
    can_view_map,
    get_current_user,
    require_admin,
    require_create_map,
)
from cmk.orbvis_backend.api.v1.types import MapName
from cmk.orbvis_backend.core.config import settings
from cmk.orbvis_backend.core.database import get_db
from cmk.orbvis_backend.core.image_security import (
    BACKGROUND_MIME_TYPES,
    BACKGROUND_SUFFIXES,
    is_valid_image,
)
from cmk.orbvis_backend.form_specs import FORM_SPECS_AVAILABLE
from cmk.orbvis_backend.models.user import User
from cmk.orbvis_backend.schemas.map import (
    MapBulkDelete,
    MapBulkDeleteFailure,
    MapBulkDeleteResult,
    MapBulkEdit,
    MapBulkEditFailure,
    MapBulkEditResult,
    MapBulkExport,
    MapClone,
    MapConfig,
    MapCreate,
    MapObject,
    MapObjectUpdate,
    MapOrderItem,
    MapPermissionsRead,
    MapRead,
    MapUpdate,
)
from cmk.orbvis_backend.services import map_service, connection_service, state_service
from cmk.orbvis_backend.services.cfg_parser import cfg_to_map

if FORM_SPECS_AVAILABLE:
    from cmk.orbvis_backend.form_specs import serialize_form_spec
    from cmk.orbvis_backend.form_specs._wire_types import AnyWireFormSpec
    from cmk.orbvis_backend.form_specs.map_metadata import (
        BULK_METADATA_FIELDS,
        METADATA_FIELDS,
        map_bulk_metadata_spec,
        map_metadata_spec,
        flow_view_spec,
        rotation_from_form,
        rotation_to_form,
    )

router = APIRouter()

_MAX_BACKGROUND_BYTES = 10 * 1024 * 1024  # 10 MB


def _require_template_admin(
    user: User,
    hover_template: object,
    context_template: object,
    hover_url: object = None,
) -> None:
    """Templates (and hover URLs) render in *other* users' browsers — a
    non-admin editor could plant XSS through them, so editing stays admin-only.
    """
    if not user.is_admin and (
        hover_template is not None or context_template is not None or hover_url is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editing hover/context templates requires admin privileges",
        )


def _require_map_view(name: str, user: User) -> None:
    if not can_view_map(user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No view permission for this map"
        )


def _require_map_edit(name: str, user: User) -> None:
    if not can_edit_map(user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No edit permission for this map"
        )


def _require_not_readonly(name: str) -> None:
    cfg = map_service.get_map(name)
    if cfg and cfg.readonly:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This map is read-only")


@router.get("", response_model=list[MapRead])
async def list_maps(current_user: User = Depends(get_current_user)) -> list[MapRead]:
    all_maps = map_service.list_maps()
    if current_user.is_admin:
        for m in all_maps:
            m.can_edit = True
        return all_maps
    visible: list[MapRead] = []
    for m in all_maps:
        if can_view_map(current_user, m.name):
            m.can_edit = can_edit_map(current_user, m.name)
            visible.append(m)
    return visible


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_maps(
    order: list[MapOrderItem], _: User = Depends(require_create_map)
) -> None:
    """Update sort_order for multiple maps at once. Body: [{"name": "...", "sort_order": 0}, ...]"""
    map_service.reorder_maps([(item.name, item.sort_order) for item in order])


@router.post("", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def create_map(data: MapCreate, _: User = Depends(require_create_map)) -> MapConfig:
    try:
        return map_service.create_map(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.get("/{name}", response_model=MapConfig)
async def get_map(name: MapName, current_user: User = Depends(get_current_user)) -> MapConfig:
    _require_map_view(name, current_user)
    cfg = map_service.get_map(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
        )
    return cfg


if FORM_SPECS_AVAILABLE:

    def _form_data_to_update_payload(
        form_data: dict[str, object], allowed_fields: tuple[str, ...]
    ) -> dict[str, object]:
        # click_action: BooleanChoice bool → "link"/"none" literal.
        # rotation_interval: CascadingSingleChoice tuple → flat int (0=off).
        payload = {field: form_data[field] for field in allowed_fields if field in form_data}
        if isinstance(payload.get("click_action"), bool):
            payload["click_action"] = "link" if payload["click_action"] else "none"
        if "rotation_interval" in payload:
            payload["rotation_interval"] = rotation_from_form(payload["rotation_interval"])
        return payload

    @router.get("/-/metadata-schema")
    async def get_map_metadata_schema(
        _: User = Depends(get_current_user),
    ) -> AnyWireFormSpec:
        connection_choices = [(c.id, c.label) for c in connection_service.load_all()]
        return serialize_form_spec(map_metadata_spec(connection_choices=connection_choices))

    @router.get("/-/flow-view-schema")
    async def get_map_flow_view_schema(
        _: User = Depends(get_current_user),
    ) -> AnyWireFormSpec:
        return serialize_form_spec(flow_view_spec())

    @router.get("/{name}/metadata")
    async def get_map_metadata(
        name: MapName, current_user: User = Depends(get_current_user)
    ) -> dict[str, object]:
        _require_map_view(name, current_user)
        cfg = map_service.get_map(name)
        if cfg is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
            )
        payload: dict[str, object] = {field: getattr(cfg, field, None) for field in METADATA_FIELDS}
        payload["rotation_interval"] = rotation_to_form(payload.get("rotation_interval"))
        return payload

    @router.put("/{name}/metadata", response_model=MapConfig)
    async def update_map_metadata(
        name: MapName,
        form_data: dict[str, object],
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> MapConfig:
        _require_map_edit(name, current_user)
        _require_not_readonly(name)
        _require_template_admin(
            current_user, form_data.get("hover_template"), form_data.get("context_template")
        )
        update_payload = _form_data_to_update_payload(form_data, METADATA_FIELDS)
        update = MapUpdate.model_validate(update_payload)
        expected_version = _parse_if_match(request.headers.get("If-Match"))
        try:
            cfg = map_service.update_map(name, update, expected_version=expected_version)
        except map_service.StaleMapError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"reason": "stale_map", "current_version": exc.current_version},
            ) from exc
        if cfg is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
            )
        return cfg

    @router.get("/-/bulk-metadata-schema")
    async def get_map_bulk_metadata_schema(
        _: User = Depends(require_create_map),
    ) -> AnyWireFormSpec:
        connection_choices = [(c.id, c.label) for c in connection_service.load_all()]
        return serialize_form_spec(map_bulk_metadata_spec(connection_choices=connection_choices))

    @router.post("/bulk-edit", response_model=MapBulkEditResult)
    async def bulk_edit_maps(
        payload: MapBulkEdit, current_user: User = Depends(require_create_map)
    ) -> MapBulkEditResult:
        update_payload = _form_data_to_update_payload(payload.updates, BULK_METADATA_FIELDS)
        _require_template_admin(
            current_user,
            update_payload.get("hover_template"),
            update_payload.get("context_template"),
        )
        update = MapUpdate.model_validate(update_payload)
        updated: list[str] = []
        failed: list[MapBulkEditFailure] = []
        seen: set[str] = set()
        for name in payload.names:
            if name in seen:
                continue
            seen.add(name)
            cfg = map_service.get_map(name)
            if cfg is None:
                failed.append(MapBulkEditFailure(name=name, reason="not found"))
                continue
            if cfg.readonly:
                failed.append(MapBulkEditFailure(name=name, reason="readonly"))
                continue
            try:
                result = map_service.update_map(name, update)
            except Exception as exc:
                failed.append(MapBulkEditFailure(name=name, reason=str(exc)))
                continue
            if result is None:
                failed.append(MapBulkEditFailure(name=name, reason="not found"))
            else:
                updated.append(name)
        return MapBulkEditResult(updated=updated, failed=failed)


@router.get("/{name}/auto-objects", response_model=list[MapObject])
async def get_auto_objects(
    name: MapName, current_user: User = Depends(get_current_user)
) -> list[MapObject]:
    """Return objects synthesised from a worldmap automap source.

    Empty for maps without ``auto_source`` configured. The objects are
    transient — they're never persisted, so the editor only ever sees the
    operator's curated set.
    """
    _require_map_view(name, current_user)
    cfg = map_service.get_map(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
        )
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        return []
    inflated = await state_service.inflate_auto_objects(cfg, connection)
    persisted_ids = {o.id for o in cfg.objects}
    return [o for o in inflated if o.id not in persisted_ids]


@router.put("/{name}", response_model=MapConfig)
async def update_map(
    name: MapName,
    data: MapUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> MapConfig:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    _require_template_admin(current_user, data.hover_template, data.context_template)
    expected_version = _parse_if_match(request.headers.get("If-Match"))
    try:
        cfg = map_service.update_map(name, data, expected_version=expected_version)
    except map_service.StaleMapError as exc:
        # 412 fits when If-Match was provided; 409 is the looser conflict signal
        # used by clients that don't surface the precondition. The body carries
        # ``current_version`` so the client can refetch and merge.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "stale_map", "current_version": exc.current_version},
        ) from exc
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
        )
    return cfg


def _parse_if_match(value: str | None) -> int | None:
    """Parse the version embedded in an ``If-Match`` header.

    Accepts both bare integers (``If-Match: 7``) and strong-quoted ETags
    (``If-Match: "7"``). Returns ``None`` for empty / unparseable values so
    callers without optimistic-locking awareness keep working.
    """
    if not value:
        return None
    s = value.strip().strip('"')
    try:
        return int(s)
    except ValueError:
        return None


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_map(name: MapName, _: User = Depends(require_create_map)) -> None:
    if not map_service.delete_map(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
        )


@router.post("/bulk-delete", response_model=MapBulkDeleteResult)
async def bulk_delete_maps(
    payload: MapBulkDelete, _: User = Depends(require_create_map)
) -> MapBulkDeleteResult:
    deleted: list[str] = []
    failed: list[MapBulkDeleteFailure] = []
    seen: set[str] = set()
    for name in payload.names:
        if name in seen:
            continue
        seen.add(name)
        try:
            if map_service.delete_map(name):
                deleted.append(name)
            else:
                failed.append(MapBulkDeleteFailure(name=name, reason="not found"))
        except Exception as exc:
            failed.append(MapBulkDeleteFailure(name=name, reason=str(exc)))
    return MapBulkDeleteResult(deleted=deleted, failed=failed)


@router.post("/bulk-export")
async def bulk_export_maps(
    payload: MapBulkExport, current_user: User = Depends(get_current_user)
) -> Response:
    # Maps the user can't view are skipped silently — matches how the
    # list endpoint filters them out, so the archive can't leak metadata.
    buf = io.BytesIO()
    seen: set[str] = set()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in payload.names:
            if name in seen:
                continue
            seen.add(name)
            if not (current_user.is_admin or can_view_map(current_user, name)):
                continue
            cfg = map_service.get_map(name)
            if cfg is None:
                continue
            zf.writestr(f"{name}.json", json.dumps(cfg.model_dump(mode="json"), indent=2))
    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="orbvis-maps.zip"'},
    )


@router.post("/{name}/clone", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def clone_map(
    name: MapName, data: MapClone, _: User = Depends(require_create_map)
) -> MapConfig:
    try:
        return map_service.clone_map(name, data.new_name, data.alias)
    except ValueError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc) else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc)) from None


@router.post("/import", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def import_map(
    data: dict[str, object], overwrite: bool = False, _: User = Depends(require_create_map)
) -> MapConfig:
    try:
        return map_service.import_map(data, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/import/cfg", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def import_cfg(
    file: UploadFile = File(...),
    overwrite: bool = False,
    _: User = Depends(require_create_map),
) -> MapConfig:
    """Import a legacy .cfg map file and convert it to an OrbVis map."""
    if not file.filename or not file.filename.lower().endswith(".cfg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only .cfg files are accepted"
        )
    content = (await file.read()).decode("utf-8", errors="replace")
    # Legacy NagVis map files may carry spaces/umlauts in the filename; map
    # names are file-backed and restricted, so map to the safe charset instead
    # of failing the import.
    map_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(file.filename).stem) or "imported_map"
    data = cfg_to_map(content, map_name)
    # Imported connection ids (typically the source-site name) almost never match
    # the OrbVis-side ids (live_1, live_2, …). Without remapping the imported
    # map references a non-existent connection and every state lookup fails
    # silently — the user just sees stale gray icons. Fall back to the first
    # *real* (non-test) registered connection; only fall through to the demo
    # TestConnection if that is the only thing configured.
    imported_bid = data.get("connection_id")
    if isinstance(imported_bid, str) and state_service.get_connection(imported_bid) is None:
        available = state_service.list_connection_ids()
        real = [bid for bid in available if bid != "test"]
        if real:
            data["connection_id"] = real[0]
        elif available:
            data["connection_id"] = available[0]
    try:
        return map_service.import_map(data, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


# ----- Map permissions (read) -----


@router.get("/{name}/permissions", response_model=MapPermissionsRead)
async def get_map_permissions(
    name: MapName,
    _: User = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> MapPermissionsRead:
    def _query() -> MapPermissionsRead:
        rows = db.execute(
            """
            SELECT r.name AS role_name, p.act
            FROM permissions p
            JOIN roles2perms r2p ON r2p.perm_id = p.perm_id
            JOIN roles r        ON r.role_id = r2p.role_id
            WHERE p.mod = 'map' AND p.obj = ?
            """,
            (name,),
        ).fetchall()
        view_roles: list[str] = []
        edit_roles: list[str] = []
        for row in rows:
            if row["act"] == "view" and row["role_name"] not in view_roles:
                view_roles.append(row["role_name"])
            elif row["act"] == "edit" and row["role_name"] not in edit_roles:
                edit_roles.append(row["role_name"])
        return MapPermissionsRead(view=view_roles, edit=edit_roles)

    return await asyncio.to_thread(_query)


# ----- Background image -----


@router.post("/{name}/background")
async def upload_background(
    name: MapName,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    if map_service.get_map(name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
        )
    if file.content_type not in BACKGROUND_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported image type"
        )

    contents = await file.read(_MAX_BACKGROUND_BYTES + 1)
    if len(contents) > _MAX_BACKGROUND_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Background image must not exceed {_MAX_BACKGROUND_BYTES // 1024 // 1024} MB",
        )
    if not is_valid_image(contents):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match a supported image format",
        )

    raw_suffix = Path(file.filename or "").suffix.lower()
    suffix = raw_suffix if raw_suffix in BACKGROUND_SUFFIXES else ".png"

    bg_dir = Path(settings.maps_dir) / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{name}{suffix}"
    dest = bg_dir / filename

    fd, tmp_path = tempfile.mkstemp(dir=bg_dir, prefix=f"{name}.", suffix=suffix)
    try:
        try:
            os.write(fd, contents)
        finally:
            os.close(fd)
        Path(tmp_path).replace(dest)
    except Exception:
        Path(tmp_path).unlink(missing_ok=True)
        raise

    # Drop siblings with other formats — map config holds only one filename.
    for stale in bg_dir.glob(f"{name}.*"):
        if stale.resolve() == dest.resolve():
            continue
        stale.unlink(missing_ok=True)

    updated = map_service.update_map(name, MapUpdate(background_image=filename))
    return JSONResponse({"filename": filename, "version": updated.version if updated else None})


@router.delete("/{name}/background")
async def delete_background(
    name: MapName, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    if map_service.get_map(name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
        )
    bg_dir = Path(settings.maps_dir) / "backgrounds"
    for f in bg_dir.glob(f"{name}.*"):
        f.unlink(missing_ok=True)
    updated = map_service.update_map(name, MapUpdate(background_image=None))
    return JSONResponse({"version": updated.version if updated else None})


# ----- Object sub-resources -----


@router.post("/{name}/objects", response_model=MapConfig, status_code=status.HTTP_201_CREATED)
async def add_object(
    name: MapName, obj: MapObject, current_user: User = Depends(get_current_user)
) -> MapConfig:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    try:
        cfg = map_service.add_object(name, obj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Map '{name}' not found"
        )
    return cfg


@router.put("/{name}/objects/{obj_id}", response_model=MapObject)
async def update_object(
    name: MapName,
    obj_id: str,
    updates: MapObjectUpdate,
    current_user: User = Depends(get_current_user),
) -> MapObject:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    _require_template_admin(
        current_user, updates.hover_template, updates.context_template, updates.hover_url
    )
    obj = map_service.update_object(name, obj_id, updates)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    return obj


@router.delete("/{name}/objects/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    name: MapName, obj_id: str, current_user: User = Depends(get_current_user)
) -> None:
    _require_map_edit(name, current_user)
    _require_not_readonly(name)
    if not map_service.delete_object(name, obj_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
