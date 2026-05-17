"""OrbVis FastAPI application entry point."""

import asyncio
import logging
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict

from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, inspect, select, text

from app.core.middleware import (
    CSRFOriginMiddleware,
    MethodOverrideMiddleware,
    SecurityHeadersMiddleware,
)

from alembic import command

_version_candidates = [
    Path(__file__).parent / "VERSION",  # bundled in wheel via force-include
    Path(__file__).parent.parent.parent / "VERSION",  # repo root or $ORBVIS_DIR
    Path(__file__).parent.parent / "VERSION",  # inside backend/
]
APP_VERSION = next((p.read_text().strip() for p in _version_candidates if p.is_file()), "0.0.0")

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
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.form_specs._helpers import set_localizer
from app.integrations import checkmk as cmk_integration
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.schemas.connection import ConnectionConfig
from app.seed_boards import seed_demo_boards
from app.seed_images import seed_builtin_images
from app.services import board_service, connection_service, settings_service
from app.services.state_service import register_connection

# Resolve log level: explicit log_level setting wins; otherwise debug → DEBUG,
# default INFO. Setting changes require a restart (no live reconfiguration).
_log_level = settings.log_level or ("DEBUG" if settings.debug else "INFO")
logging.basicConfig(
    level=getattr(logging, _log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def _ensure_admin_user() -> None:
    """Create default admin user with a random password if no users exist yet."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            password = secrets.token_urlsafe(16)
            admin = User(
                name="admin",
                password=hash_password(password),
                is_active=True,
                is_admin=True,
                must_change_password=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("Created default admin user")
            # Print once to stdout so it's visible in container/service logs.
            # Never log the password – stdout is not captured by structured loggers.
            sep = "=" * 60
            print(f"\n{sep}", flush=True)
            print(f"  Default admin created: admin / {password}", flush=True)
            print("  Change this password immediately!", flush=True)
            print(f"{sep}\n", flush=True)


async def _seed_default_roles() -> None:
    """Create default roles with permissions idempotently on startup."""

    class _PermDef(TypedDict):
        mod: str
        act: str
        obj: str

    class _RoleDef(TypedDict):
        name: str
        permissions: list[_PermDef]

    defaults: list[_RoleDef] = [
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

    async with AsyncSessionLocal() as db:
        for role_def in defaults:
            result = await db.execute(select(Role).where(Role.name == role_def["name"]))
            role = result.scalar_one_or_none()
            if role is None:
                role = Role(name=role_def["name"])
                db.add(role)
                await db.flush()
                await db.refresh(role)

            for p in role_def["permissions"]:
                perm_result = await db.execute(
                    select(Permission).where(
                        Permission.mod == p["mod"],
                        Permission.act == p["act"],
                        Permission.obj == p["obj"],
                    )
                )
                perm = perm_result.scalar_one_or_none()
                if perm is None:
                    perm = Permission(mod=p["mod"], act=p["act"], obj=p["obj"])
                    db.add(perm)
                    await db.flush()
                    await db.refresh(perm)

                if perm not in role.permissions:
                    role.permissions.append(perm)

        await db.commit()
    logger.info("Default roles seeded.")


def _run_migrations() -> None:
    """Apply alembic migrations on startup (synchronous).

    Called directly from the lifespan — migrations complete in milliseconds
    so briefly blocking the event loop during startup is fine.

    Handles three cases:
    - Fresh DB: alembic creates all tables normally.
    - Legacy install: tables exist without migration history → stamp at head.
    - Partial migration: ``alembic_version`` table empty (DDL ran but version
      row was never committed) → stamp at head.
    """
    _alembic_ini_candidates = (
        Path(__file__).parent / "alembic.ini",  # bundled in wheel
        Path(__file__).parent.parent / "alembic.ini",  # source checkout
    )
    alembic_ini = next(
        (p for p in _alembic_ini_candidates if p.is_file()),
        _alembic_ini_candidates[0],
    )

    def _make_config() -> Config:
        cfg = Config(str(alembic_ini))
        # script_location is relative in alembic.ini; resolve to absolute so
        # alembic finds env.py / versions/ regardless of cwd.
        cfg.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
        return cfg

    sync_url = settings.sync_database_url

    engine = create_engine(sync_url)
    try:
        tables = inspect(engine).get_table_names()
        if "users" in tables:
            # Existing tables — check whether migration history is present and valid
            needs_stamp = "alembic_version" not in tables
            if not needs_stamp:
                with engine.connect() as conn:
                    row = conn.execute(
                        text("SELECT version_num FROM alembic_version LIMIT 1")
                    ).fetchone()
                needs_stamp = row is None
            if needs_stamp:
                logger.info("Stamping existing database at alembic head.")
                command.stamp(_make_config(), "head")
            else:
                logger.info("Database already at head, skipping migrations.")
            return
    finally:
        engine.dispose()

    command.upgrade(_make_config(), "head")
    logger.info("Database migrations applied.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    cmk_integration.setup()

    # Wire FormSpec strings (Title/Help/Label/Message + raw labels via tr())
    # through the Checkmk gettext catalog once cmk.* is importable. Standalone
    # / MKP builds keep the identity default — no behaviour change there.
    try:
        from cmk.gui.i18n import _ as _cmk_gettext

        set_localizer(_cmk_gettext)
        logger.debug("FormSpec localizer wired to cmk.gui.i18n._")
    except ImportError:
        pass

    # SECRET_KEY enforcement lives in app.core.config — production-mode startup
    # without a key already fails at Settings() instantiation.

    logger.info("Starting OrbVis backend…")
    sep = "=" * 60
    print(f"\n{sep}", flush=True)
    port = os.environ.get("ORBVIS_PORT", "8082")
    host_port = "" if port == "80" else f":{port}"
    print("  OrbVis is starting up.", flush=True)
    print(f"  Open in your browser: http://localhost{host_port}/orbvis", flush=True)
    print(f"{sep}\n", flush=True)
    await asyncio.to_thread(_run_migrations)
    logger.info("Database initialized.")

    settings_service.apply_log_level(settings_service.get_system_settings().log_level)

    # One-shot data migration: rename pre-rename `backends.json` and rewrite
    # `backend_id` keys in board files. Idempotent on subsequent boots.
    connection_service.migrate_legacy_filename()
    board_service.migrate_legacy_keys()

    # Always provide the built-in test connection (no config needed)
    register_connection("test", TestConnection())

    # Load and activate all persisted connection configs
    connection_service.activate_all()

    # In Checkmk/OMD mode: auto-set global checkmk_url if not configured yet
    if settings.checkmk_omd_root and settings.checkmk_site:
        _sys = settings_service.get_system_settings()
        if not _sys.checkmk_url:
            _sys.checkmk_url = f"/{settings.checkmk_site}"
            settings_service.save_system_settings(_sys)
            logger.info("Auto-set global checkmk_url to /%s", settings.checkmk_site)

    # In Checkmk/OMD mode: auto-create a Livestatus connection if none exists yet
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

    # In SSO/CMK mode authentication is handled externally — no local admin needed
    if not settings.checkmk_omd_root:
        await _ensure_admin_user()
    await _seed_default_roles()
    await asyncio.gather(
        asyncio.to_thread(seed_demo_boards, Path(settings.boards_dir)),
        asyncio.to_thread(seed_builtin_images, Path(settings.boards_dir).parent / "images"),
    )

    warmup_task = asyncio.create_task(connection_service.warmup_loop())

    yield
    logger.info("Shutting down OrbVis backend.")
    # Flush any pending debounced board writes before the process exits.
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


@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html() -> HTMLResponse:
    # Relative URLs so the page works under any reverse-proxy prefix
    # (e.g. /<SITE>/orbvis/api/docs in a Checkmk OMD site). The Swagger-UI
    # assets are served by Apache from the bundled CMK files; see install_cmk.sh.
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
    # Explicit lists instead of "*" so CORS preflights only advertise surface
    # we actually use. Keeps the attack surface minimal when the app is
    # embedded or served from additional origins.
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
# Gzip JSON responses above 1 KiB. Hot endpoints (board states, autocomplete
# host/service lists) are highly compressible; saves ~70 % over the wire.
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


@app.get("/api/changelog")
async def get_changelog() -> PlainTextResponse:
    return PlainTextResponse(_CHANGELOG)


# Serve background images uploaded via the API
_bg_dir = Path(settings.boards_dir) / "backgrounds"
_bg_dir.mkdir(parents=True, exist_ok=True)
app.mount("/boards/backgrounds", StaticFiles(directory=str(_bg_dir)), name="backgrounds")

# Serve image set images
_images_dir = Path(settings.boards_dir).parent / "images"
_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")
