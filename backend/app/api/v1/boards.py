"""Board CRUD endpoints."""

from __future__ import annotations

import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.v1.deps import (
    can_edit_board,
    can_view_board,
    get_current_user,
    require_admin,
)
from app.api.v1.types import BoardName
from app.core.config import settings
from app.core.database import get_db
from app.core.image_security import (
    BACKGROUND_MIME_TYPES,
    BACKGROUND_SUFFIXES,
    is_valid_image,
)
from app.form_specs import FORM_SPECS_AVAILABLE
from app.models.user import User
from app.schemas.board import (
    BoardClone,
    BoardConfig,
    BoardCreate,
    BoardObject,
    BoardObjectUpdate,
    BoardPermissionsRead,
    BoardRead,
    BoardUpdate,
)
from app.services import board_service, connection_service, state_service
from app.services.cfg_parser import cfg_to_board

if FORM_SPECS_AVAILABLE:
    from app.form_specs import serialize_form_spec
    from app.form_specs._wire_types import AnyWireFormSpec
    from app.form_specs.board_metadata import (
        METADATA_FIELDS,
        board_metadata_spec,
        flow_view_spec,
        rotation_from_form,
        rotation_to_form,
    )

router = APIRouter()

_MAX_BACKGROUND_BYTES = 10 * 1024 * 1024  # 10 MB


def _require_board_view(name: str, user: User) -> None:
    if not can_view_board(user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No view permission for this board"
        )


def _require_board_edit(name: str, user: User) -> None:
    if not can_edit_board(user, name):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No edit permission for this board"
        )


def _require_not_readonly(name: str) -> None:
    cfg = board_service.get_board(name)
    if cfg and cfg.readonly:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This board is read-only")


@router.get("", response_model=list[BoardRead])
async def list_boards(current_user: User = Depends(get_current_user)) -> list[BoardRead]:
    all_boards = board_service.list_boards()
    if current_user.is_admin:
        return all_boards
    return [m for m in all_boards if can_view_board(current_user, m.name)]


@router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_boards(
    order: list[dict[str, int | str]], _: User = Depends(require_admin)
) -> None:
    """Update sort_order for multiple boards at once. Body: [{"name": "...", "sort_order": 0}, ...]"""
    board_service.reorder_boards(
        [
            (str(item["name"]), int(item["sort_order"]))
            for item in order
            if "name" in item and "sort_order" in item
        ]
    )


@router.post("", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def create_board(data: BoardCreate, _: User = Depends(require_admin)) -> BoardConfig:
    try:
        return board_service.create_board(data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.get("/{name}", response_model=BoardConfig)
async def get_board(name: BoardName, current_user: User = Depends(get_current_user)) -> BoardConfig:
    _require_board_view(name, current_user)
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    return cfg


if FORM_SPECS_AVAILABLE:

    @router.get("/-/metadata-schema")
    async def get_board_metadata_schema(
        _: User = Depends(get_current_user),
    ) -> AnyWireFormSpec:
        connections = connection_service.load_all()

        async def _alive(cid: str) -> bool:
            backend = state_service.get_connection(cid)
            if backend is None:
                return False
            try:
                return await backend.is_available()
            except Exception:
                return False

        ids = [c.id for c in connections]
        alives = await asyncio.gather(*(_alive(cid) for cid in ids))
        health = dict(zip(ids, alives, strict=True))
        connection_choices = [
            (c.id, c.label or c.id, c.type, health.get(c.id, False)) for c in connections
        ]
        return serialize_form_spec(board_metadata_spec(connection_choices=connection_choices))

    @router.get("/-/flow-view-schema")
    async def get_board_flow_view_schema(
        _: User = Depends(get_current_user),
    ) -> AnyWireFormSpec:
        return serialize_form_spec(flow_view_spec())

    @router.get("/{name}/metadata")
    async def get_board_metadata(
        name: BoardName, current_user: User = Depends(get_current_user)
    ) -> dict[str, object]:
        _require_board_view(name, current_user)
        cfg = board_service.get_board(name)
        if cfg is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
            )
        payload: dict[str, object] = {field: getattr(cfg, field, None) for field in METADATA_FIELDS}
        payload["rotation_interval"] = rotation_to_form(payload.get("rotation_interval"))
        return payload

    @router.put("/{name}/metadata", response_model=BoardConfig)
    async def update_board_metadata(
        name: BoardName,
        form_data: dict[str, object],
        request: Request,
        current_user: User = Depends(get_current_user),
    ) -> BoardConfig:
        _require_board_edit(name, current_user)
        _require_not_readonly(name)
        if not current_user.is_admin and (
            form_data.get("hover_template") is not None
            or form_data.get("context_template") is not None
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Editing hover/context templates requires admin privileges",
            )
        update_payload = {
            field: form_data[field] for field in METADATA_FIELDS if field in form_data
        }
        # FormSpec renders click_action as a BooleanChoice ("Interactive") so
        # the form-data shape is bool. Map back to the on-wire literal that
        # BoardUpdate validates.
        if isinstance(update_payload.get("click_action"), bool):
            update_payload["click_action"] = "link" if update_payload["click_action"] else "none"
        if "rotation_interval" in update_payload:
            update_payload["rotation_interval"] = rotation_from_form(
                update_payload["rotation_interval"]
            )
        update = BoardUpdate.model_validate(update_payload)
        expected_version = _parse_if_match(request.headers.get("If-Match"))
        try:
            cfg = board_service.update_board(name, update, expected_version=expected_version)
        except board_service.StaleBoardError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"reason": "stale_board", "current_version": exc.current_version},
            ) from exc
        if cfg is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
            )
        return cfg


@router.get("/{name}/auto-objects", response_model=list[BoardObject])
async def get_auto_objects(
    name: BoardName, current_user: User = Depends(get_current_user)
) -> list[BoardObject]:
    """Return objects synthesised from a worldmap automap source.

    Empty for boards without ``auto_source`` configured. The objects are
    transient — they're never persisted, so the editor only ever sees the
    operator's curated set.
    """
    from app.services import state_service

    _require_board_view(name, current_user)
    cfg = board_service.get_board(name)
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    connection = state_service.get_connection(cfg.connection_id)
    if connection is None:
        return []
    inflated = await state_service.inflate_auto_objects(cfg, connection)
    persisted_ids = {o.id for o in cfg.objects}
    return [o for o in inflated if o.id not in persisted_ids]


@router.put("/{name}", response_model=BoardConfig)
async def update_board(
    name: BoardName,
    data: BoardUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> BoardConfig:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    if not current_user.is_admin and (
        data.hover_template is not None or data.context_template is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editing hover/context templates requires admin privileges",
        )
    expected_version = _parse_if_match(request.headers.get("If-Match"))
    try:
        cfg = board_service.update_board(name, data, expected_version=expected_version)
    except board_service.StaleBoardError as exc:
        # 412 fits when If-Match was provided; 409 is the looser conflict signal
        # used by clients that don't surface the precondition. The body carries
        # ``current_version`` so the client can refetch and merge.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "stale_board", "current_version": exc.current_version},
        ) from exc
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
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
async def delete_board(name: BoardName, _: User = Depends(require_admin)) -> None:
    if not board_service.delete_board(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )


@router.post("/{name}/clone", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def clone_board(
    name: BoardName, data: BoardClone, _: User = Depends(require_admin)
) -> BoardConfig:
    try:
        return board_service.clone_board(name, data.new_name, data.alias)
    except ValueError as exc:
        code = status.HTTP_404_NOT_FOUND if "not found" in str(exc) else status.HTTP_409_CONFLICT
        raise HTTPException(status_code=code, detail=str(exc)) from None


@router.post("/import", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def import_board(
    data: dict[str, object], overwrite: bool = False, _: User = Depends(require_admin)
) -> BoardConfig:
    try:
        return board_service.import_board(data, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/import/cfg", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def import_cfg(
    file: UploadFile = File(...),
    overwrite: bool = False,
    _: User = Depends(require_admin),
) -> BoardConfig:
    """Import a legacy .cfg map file and convert it to an OrbVis board."""
    if not file.filename or not file.filename.lower().endswith(".cfg"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only .cfg files are accepted"
        )
    content = (await file.read()).decode("utf-8", errors="replace")
    map_name = Path(file.filename).stem
    data = cfg_to_board(content, map_name)
    # Imported connection ids (typically the source-site name) almost never match
    # the OrbVis-side ids (live_1, live_2, …). Without remapping the imported
    # board references a non-existent connection and every state lookup fails
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
        return board_service.import_board(data, overwrite=overwrite)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None


# ----- Board permissions (read) -----


@router.get("/{name}/permissions", response_model=BoardPermissionsRead)
async def get_board_permissions(
    name: BoardName,
    _: User = Depends(require_admin),
    db: sqlite3.Connection = Depends(get_db),
) -> BoardPermissionsRead:
    def _query() -> BoardPermissionsRead:
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
        return BoardPermissionsRead(view=view_roles, edit=edit_roles)

    return await asyncio.to_thread(_query)


# ----- Background image -----


@router.post("/{name}/background")
async def upload_background(
    name: BoardName,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    if board_service.get_board(name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
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

    bg_dir = Path(settings.boards_dir) / "backgrounds"
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

    # Drop siblings with other formats — board config holds only one filename.
    for stale in bg_dir.glob(f"{name}.*"):
        if stale.resolve() == dest.resolve():
            continue
        stale.unlink(missing_ok=True)

    updated = board_service.update_board(name, BoardUpdate(background_image=filename))
    return JSONResponse({"filename": filename, "version": updated.version if updated else None})


@router.delete("/{name}/background")
async def delete_background(
    name: BoardName, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    if board_service.get_board(name) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    bg_dir = Path(settings.boards_dir) / "backgrounds"
    for f in bg_dir.glob(f"{name}.*"):
        f.unlink(missing_ok=True)
    updated = board_service.update_board(name, BoardUpdate(background_image=None))
    return JSONResponse({"version": updated.version if updated else None})


# ----- Object sub-resources -----


@router.post("/{name}/objects", response_model=BoardConfig, status_code=status.HTTP_201_CREATED)
async def add_object(
    name: BoardName, obj: BoardObject, current_user: User = Depends(get_current_user)
) -> BoardConfig:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    try:
        cfg = board_service.add_object(name, obj)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    if cfg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Board '{name}' not found"
        )
    return cfg


@router.put("/{name}/objects/{obj_id}", response_model=BoardObject)
async def update_object(
    name: BoardName,
    obj_id: str,
    updates: BoardObjectUpdate,
    current_user: User = Depends(get_current_user),
) -> BoardObject:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    # Templates render as HTML in other users' browsers, so a non-admin editor
    # could plant XSS via hover_template/context_template. Hover URL is treated
    # the same way (a malicious URL fires when another user hovers the object).
    if not current_user.is_admin and (
        updates.hover_template is not None
        or updates.context_template is not None
        or updates.hover_url is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editing hover/context templates requires admin privileges",
        )
    obj = board_service.update_object(name, obj_id, updates)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
    return obj


@router.delete("/{name}/objects/{obj_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    name: BoardName, obj_id: str, current_user: User = Depends(get_current_user)
) -> None:
    _require_board_edit(name, current_user)
    _require_not_readonly(name)
    if not board_service.delete_object(name, obj_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
