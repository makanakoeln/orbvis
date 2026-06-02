"""OrbVis FastAPI application entry point."""

import asyncio
import logging
import os
import secrets
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from app.core.middleware import (
    CSRFOriginMiddleware,
    MethodOverrideMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.version import APP_VERSION

_changelog_candidates = [
    Path(__file__).parent / "CHANGELOG.md",
    Path(__file__).parent.parent.parent / "CHANGELOG.md",
    Path(__file__).parent.parent / "CHANGELOG.md",
]
_CHANGELOG = next((p.read_text() for p in _changelog_candidates if p.is_file()), "")


from app.api.v1 import (
    auth,
    boards,
    connections,
    images,
    maps,
    roles,
    states,
    users,
)
from app.api.v1 import (
    metrics as metrics_api,
)
from app.api.v1 import (
    settings as settings_api,
)
from app.connections.test import TestConnection
from app.core.config import settings
from app.core.database import _connect, _ensure_schema
from app.core.security import hash_password
from app.form_specs import FORM_SPECS_AVAILABLE
from app.integrations import checkmk as cmk_integration

if FORM_SPECS_AVAILABLE:
    from app.form_specs._helpers import set_localizer
from app.schemas.connection import ConnectionConfig
from app.seed_boards import seed_demo_boards
from app.seed_images import seed_builtin_images
from app.services import board_service, connection_service, settings_service
from app.services.state_service import register_connection

_log_level = settings.log_level or ("DEBUG" if settings.debug else "INFO")
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def _ensure_admin_user_sync(conn: sqlite3.Connection) -> None:
    row = conn.execute("SELECT 1 FROM users LIMIT 1").fetchone()
    if row is not None:
        return
    password = secrets.token_urlsafe(16)
    conn.execute(
        """
        INSERT INTO users (name, password, is_active, is_admin, must_change_password)
        VALUES (?, ?, 1, 1, 1)
        """,
        ("admin", hash_password(password)),
    )
    logger.info("Created default admin user")
    # stdout-only — never log the password.
    sep = "=" * 60
    print(f"\n{sep}", flush=True)
    print(f"  Default admin created: admin / {password}", flush=True)
    print("  Change this password immediately!", flush=True)
    print(f"{sep}\n", flush=True)


class _PermDef(TypedDict):
    mod: str
    act: str
    obj: str


class _RoleDef(TypedDict):
    name: str
    permissions: list[_PermDef]


_DEFAULT_ROLES: list[_RoleDef] = [
    {
        "name": "Administrators",
        "permissions": [
            {"mod": "map", "act": "view", "obj": "*"},
            {"mod": "map", "act": "edit", "obj": "*"},
            {"mod": "user", "act": "edit", "obj": "*"},
        ],
    },
    {
        "name": "Viewers",
        "permissions": [
            {"mod": "map", "act": "view", "obj": "*"},
        ],
    },
]


def _seed_default_roles_sync(conn: sqlite3.Connection) -> None:
    for role_def in _DEFAULT_ROLES:
        row = conn.execute(
            "SELECT role_id FROM roles WHERE name = ?", (role_def["name"],)
        ).fetchone()
        if row is None:
            cursor = conn.execute("INSERT INTO roles (name) VALUES (?)", (role_def["name"],))
            role_id = cursor.lastrowid
        else:
            role_id = row["role_id"]

        for p in role_def["permissions"]:
            perm_row = conn.execute(
                "SELECT perm_id FROM permissions WHERE mod = ? AND act = ? AND obj = ?",
                (p["mod"], p["act"], p["obj"]),
            ).fetchone()
            if perm_row is None:
                cursor = conn.execute(
                    "INSERT INTO permissions (mod, act, obj) VALUES (?, ?, ?)",
                    (p["mod"], p["act"], p["obj"]),
                )
                perm_id = cursor.lastrowid
            else:
                perm_id = perm_row["perm_id"]
            conn.execute(
                "INSERT OR IGNORE INTO roles2perms (role_id, perm_id) VALUES (?, ?)",
                (role_id, perm_id),
            )
    logger.info("Default roles seeded.")


def _bootstrap_database() -> None:
    _ensure_schema()
    conn = _connect()
    try:
        # In SSO/CMK mode authentication is handled externally — no local admin needed.
        if not settings.checkmk_omd_root:
            _ensure_admin_user_sync(conn)
        _seed_default_roles_sync(conn)
    finally:
        conn.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    cmk_integration.setup()

    if FORM_SPECS_AVAILABLE:
        try:
            from cmk.gui.i18n import _ as _cmk_gettext

            set_localizer(_cmk_gettext)
            logger.debug("FormSpec localizer wired to cmk.gui.i18n._")
        except ImportError:
            pass

    logger.info("Starting OrbVis backend…")
    sep = "=" * 60
    print(f"\n{sep}", flush=True)
    port = os.environ.get("ORBVIS_PORT", "8082")
    host_port = "" if port == "80" else f":{port}"
    print("  OrbVis is starting up.", flush=True)
    print(f"  Open in your browser: http://localhost{host_port}/orbvis", flush=True)
    print(f"{sep}\n", flush=True)
    await asyncio.to_thread(_bootstrap_database)
    logger.info("Database initialized.")

    settings_service.apply_log_level(settings_service.get_system_settings().log_level)

    # One-shot data migration for legacy "backends.json" + "backend_id" keys.
    connection_service.migrate_legacy_filename()
    board_service.migrate_legacy_keys()

    register_connection("test", TestConnection())
    connection_service.activate_all()

    if settings.checkmk_omd_root and settings.checkmk_site:
        _sys = settings_service.get_system_settings()
        if not _sys.checkmk_url:
            _sys.checkmk_url = f"/{settings.checkmk_site}"
            settings_service.save_system_settings(_sys)
            logger.info("Auto-set global checkmk_url to /%s", settings.checkmk_site)

    if settings.checkmk_omd_root and settings.checkmk_site:
        conn_id = f"cmk_{settings.checkmk_site}"
        if not connection_service.load_all():
            socket_path = str(Path(settings.checkmk_omd_root) / "tmp" / "run" / "live")
            cfg = ConnectionConfig(
                id=conn_id,
                type="livestatus",
                label=f"Checkmk {settings.checkmk_site}",
                socket_path=socket_path,
                checkmk_url=f"/{settings.checkmk_site}",
                host=None,
                port=6557,
                timeout=10,
                icinga2_url=None,
                icinga2_username=None,
                icinga2_password=None,
                icinga2_verify_ssl=True,
            )
            connection_service.create(cfg)
            logger.info("Auto-created Checkmk connection '%s' → %s", conn_id, socket_path)

    await asyncio.gather(
        asyncio.to_thread(seed_demo_boards, Path(settings.boards_dir)),
        asyncio.to_thread(seed_builtin_images, Path(settings.boards_dir).parent / "images"),
    )

    warmup_task = asyncio.create_task(connection_service.warmup_loop())

    yield
    logger.info("Shutting down OrbVis backend.")
    board_service.flush_all()
    warmup_task.cancel()
    try:
        await warmup_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="OrbVis API",
    version=APP_VERSION,
    description="REST API for OrbVis – monitoring visualization",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


def _swagger_ui_5_available() -> bool:
    omd_root = settings.checkmk_omd_root
    if not omd_root:
        return True
    openapi_dir = Path(omd_root) / "share/check_mk/web/htdocs/openapi"
    if not openapi_dir.is_dir():
        return False
    for entry in openapi_dir.iterdir():
        if entry.name.startswith("swagger-ui-5.") and (entry / "swagger-ui-bundle.js").is_file():
            return True
    return False


_SWAGGER_UNAVAILABLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>OrbVis API – Swagger UI unavailable</title>
<style>
body{font-family:system-ui,sans-serif;max-width:640px;margin:4rem auto;padding:0 1rem;color:#222;line-height:1.5}
h1{font-size:1.4rem;margin-bottom:1rem}
code{background:#f3f3f3;padding:.1em .35em;border-radius:3px}
a{color:#1f6feb}
</style>
</head>
<body>
<h1>Interactive Swagger UI not available on this Checkmk site</h1>
<p>OrbVis emits an <strong>OpenAPI&nbsp;3.1</strong> schema. Rendering it requires
<strong>Swagger-UI&nbsp;5.x</strong>, which is shipped with <strong>Checkmk&nbsp;2.5</strong> and newer.
This site bundles only Swagger-UI&nbsp;3, which cannot render OpenAPI&nbsp;3.1.</p>
<p>The raw OpenAPI schema is still available at
<a href="openapi.json">openapi.json</a> and works with any external Swagger-UI&nbsp;5 / Redoc / Postman / Insomnia client.</p>
</body>
</html>
"""


@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    if not _swagger_ui_5_available():
        return HTMLResponse(_SWAGGER_UNAVAILABLE_HTML)
    return get_swagger_ui_html(
        openapi_url="openapi.json",
        title=f"{app.title} - Swagger UI",
        swagger_js_url="swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="swagger-ui/swagger-ui.css",
        swagger_favicon_url="swagger-ui/favicon-32x32.png",
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Authorization",
        "Content-Language",
        "Content-Type",
        "X-HTTP-Method-Override",
    ],
)
app.add_middleware(MethodOverrideMiddleware)
app.add_middleware(CSRFOriginMiddleware, allowed_origins=settings.allowed_origins)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(boards.router, prefix="/api/v1/boards", tags=["boards"])
app.include_router(states.router, prefix="/api/v1", tags=["states"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(connections.router, prefix="/api/v1/connections", tags=["connections"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(images.router, prefix="/api/v1/images", tags=["images"])
app.include_router(maps.router, prefix="/api/v1/maps", tags=["maps"])
app.include_router(metrics_api.router, prefix="/api/v1", tags=["metrics"])


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@app.get("/api/v1/capabilities")
async def get_capabilities() -> dict[str, bool]:
    return {"form_specs": FORM_SPECS_AVAILABLE}


@app.get("/api/changelog")
async def get_changelog() -> PlainTextResponse:
    return PlainTextResponse(_CHANGELOG)


_bg_dir = Path(settings.boards_dir) / "backgrounds"
_bg_dir.mkdir(parents=True, exist_ok=True)
app.mount("/boards/backgrounds", StaticFiles(directory=str(_bg_dir)), name="backgrounds")

_images_dir = Path(settings.boards_dir).parent / "images"
_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")
