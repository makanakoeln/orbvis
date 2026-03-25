"""OrbVis FastAPI application entry point."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TypedDict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_version_candidates = [
    Path(__file__).parent.parent.parent / "VERSION",  # repo root or $ORBVIS_DIR
    Path(__file__).parent.parent / "VERSION",  # inside backend/
]
APP_VERSION = next((p.read_text().strip() for p in _version_candidates if p.is_file()), "0.0.0")


class SecurityHeadersMiddleware:
    """Add security-related HTTP headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers += [
                    (b"x-content-type-options", b"nosniff"),
                    (b"x-frame-options", b"SAMEORIGIN"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"x-xss-protection", b"1; mode=block"),
                ]
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class MethodOverrideMiddleware:
    """Tunnel PATCH/PUT/DELETE through POST via X-HTTP-Method-Override header.

    Some reverse proxies (e.g. OMD/Checkmk Apache) block non-GET/POST methods.
    The frontend sends POST with X-HTTP-Method-Override: PATCH (etc.) and this
    middleware rewrites the ASGI scope method before routing, so all existing
    FastAPI routes work unchanged.
    """

    _ALLOWED = frozenset(("PATCH", "PUT", "DELETE"))

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            override = headers.get(b"x-http-method-override", b"").decode().upper()
            if override in self._ALLOWED:
                scope = {**scope, "method": override}
        await self.app(scope, receive, send)


from app.api.v1 import (
    auth,
    backends,
    boards,
    images,
    roles,
    states,
    users,
)
from app.api.v1 import (
    settings as settings_api,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


async def _ensure_admin_user() -> None:
    """Create default admin user with a random password if no users exist yet."""
    import secrets as _secrets

    from sqlalchemy import select

    from app.core.security import hash_password
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none() is None:
            password = _secrets.token_urlsafe(16)
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
    from sqlalchemy import select

    from app.models.permission import Permission
    from app.models.role import Role

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


_DEMO_BG_SVG = """\
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="640">
  <!-- Section: Hosts + Lines -->
  <rect x="190" y="16" width="470" height="610" rx="10"
        fill="#4f46e5" fill-opacity="0.06" stroke="#4f46e5" stroke-opacity="0.2" stroke-width="1"/>
  <text x="425" y="40" text-anchor="middle"
        font-family="monospace" font-size="9" font-weight="bold" letter-spacing="2"
        fill="#818cf8">HOSTS + LINES</text>
  <!-- Section: Services + Gadgets -->
  <rect x="690" y="16" width="305" height="610" rx="10"
        fill="#10b981" fill-opacity="0.05" stroke="#10b981" stroke-opacity="0.2" stroke-width="1"/>
  <text x="842" y="40" text-anchor="middle"
        font-family="monospace" font-size="9" font-weight="bold" letter-spacing="2"
        fill="#34d399">SERVICES + GADGETS</text>
  <!-- Section: Groups -->
  <rect x="1015" y="16" width="155" height="610" rx="10"
        fill="#f59e0b" fill-opacity="0.05" stroke="#f59e0b" stroke-opacity="0.2" stroke-width="1"/>
  <text x="1092" y="40" text-anchor="middle"
        font-family="monospace" font-size="9" font-weight="bold" letter-spacing="2"
        fill="#fbbf24">GROUPS</text>
  <!-- Section: Image + Map -->
  <rect x="1195" y="16" width="205" height="610" rx="10"
        fill="#a78bfa" fill-opacity="0.05" stroke="#a78bfa" stroke-opacity="0.2" stroke-width="1"/>
  <text x="1297" y="40" text-anchor="middle"
        font-family="monospace" font-size="9" font-weight="bold" letter-spacing="2"
        fill="#c4b5fd">SHAPE + MAP</text>
  <!-- Row type labels in left margin -->
  <text x="95" y="194" text-anchor="middle" font-family="monospace" font-size="8" fill="#6b7280">icon view</text>
  <text x="95" y="359" text-anchor="middle" font-family="monospace" font-size="8" fill="#6b7280">gauge / bar</text>
  <text x="95" y="524" text-anchor="middle" font-family="monospace" font-size="8" fill="#6b7280">traffic light</text>
</svg>
"""


def _seed_demo_map() -> None:
    """Write the built-in demo map to disk if it doesn't already exist."""
    from app.schemas.board import (
        BoardConfig,
        BoardObject,
        BoardUpdate,
        DisplayConfig,
        LabelConfig,
        StaticView,
    )
    from app.services.board_service import _board_path, _save_board_file, get_board, update_board

    # Always ensure the background SVG is present on disk
    bg_dir = Path(settings.boards_dir) / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)
    bg_file = bg_dir / "demo.svg"
    if not bg_file.exists():
        bg_file.write_text(_DEMO_BG_SVG, encoding="utf-8")

    if _board_path("demo-static").exists():
        # Upgrade existing demo board: set background_image if not yet configured
        existing = get_board("demo-static")
        if existing and not existing.background_image:
            update_board("demo-static", BoardUpdate(background_image="demo.svg"))
        return

    # Layout overview (x: 150–900, y: 50–530)
    #
    #  [HOSTS]                     [SERVICES]       [GROUPS]     [IMAGE/MAP]
    #  localhost ─── router01      HTTP  PING        linux-srv    image
    #       \       /              CPU▓  Disk▓       web-svc      map →
    #        fileserver
    #  ══ weathermap lines ══
    #  localhost→fileserver  (CPU Load perf data, line_style=weathermap)
    #  router01→fileserver   (HTTP perf data,     line_style=weathermap)
    #
    # Section x-offsets: Hosts 160-440, Services 540-680, Groups 760-800, Other 880

    cfg = BoardConfig(
        name="demo-static",
        alias="Static Board (Demo)",
        icon_size=28,
        backend_id="test",
        view=StaticView(),
        hover_template="{{name}}\nState: {{state}}\n{{output}}",
        background_image="demo.svg",
        objects=[
            # ── Hosts ───────────────────────────────────────────────────────
            BoardObject(
                id="host-localhost",
                type="host",
                x=270,
                y=190,
                host_name="localhost",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, text="localhost", x=0, y=34, size=11),
            ),
            BoardObject(
                id="host-router01",
                type="host",
                x=570,
                y=190,
                host_name="router01",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, text="router01", x=0, y=34, size=11),
            ),
            BoardObject(
                id="host-fileserver",
                type="host",
                x=420,
                y=380,
                host_name="fileserver",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, text="fileserver", x=0, y=34, size=11),
            ),
            # ── Lines ───────────────────────────────────────────────────────
            # Plain line: localhost ↔ router01 (color = host state)
            BoardObject(
                id="line-loc-rtr",
                type="line",
                x=270,
                y=190,
                x2=570,
                y2=190,
                label=LabelConfig(show=False),
                line_style="plain",
            ),
            # Weathermap: localhost → fileserver  (perf_data from CPU Load service)
            BoardObject(
                id="wm-loc-fs",
                type="line",
                x=270,
                y=190,
                x2=420,
                y2=380,
                host_name="localhost",
                service_description="CPU Load",
                label=LabelConfig(show=False),
                line_style="weathermap",
            ),
            # Weathermap: router01 → fileserver  (perf_data from HTTP service)
            BoardObject(
                id="wm-rtr-fs",
                type="line",
                x=570,
                y=190,
                x2=420,
                y2=380,
                host_name="router01",
                service_description="HTTP",
                label=LabelConfig(show=False),
                line_style="weathermap",
            ),
            # ── Services ────────────────────────────────────────────────────
            BoardObject(
                id="svc-http",
                type="service",
                x=760,
                y=190,
                host_name="localhost",
                service_description="HTTP",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, x=0, y=34, size=10),
            ),
            BoardObject(
                id="svc-ping",
                type="service",
                x=925,
                y=190,
                host_name="router01",
                service_description="PING",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, x=0, y=34, size=10),
            ),
            BoardObject(
                id="svc-cpu-gauge",
                type="service",
                x=760,
                y=355,
                host_name="localhost",
                service_description="CPU Load",
                display=DisplayConfig(mode="gadget", gadget_type="gauge"),
                label=LabelConfig(show=True, text="CPU Load", x=0, y=56, size=10),
            ),
            BoardObject(
                id="svc-disk-bar",
                type="service",
                x=925,
                y=355,
                host_name="fileserver",
                service_description="Disk /",
                display=DisplayConfig(mode="gadget", gadget_type="bar"),
                label=LabelConfig(show=True, text="Disk /", x=0, y=56, size=10),
            ),
            BoardObject(
                id="svc-memory-tl",
                type="service",
                x=842,
                y=520,
                host_name="mailserver",
                service_description="Memory",
                display=DisplayConfig(mode="gadget", gadget_type="trafficlight"),
                label=LabelConfig(show=True, text="Memory", x=0, y=56, size=10),
            ),
            # ── Groups ──────────────────────────────────────────────────────
            BoardObject(
                id="hg-linux",
                type="hostgroup",
                x=1092,
                y=190,
                group_name="linux-servers",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, text="linux-servers", x=0, y=34, size=11),
            ),
            BoardObject(
                id="sg-web",
                type="servicegroup",
                x=1092,
                y=380,
                group_name="web-services",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, text="web-services", x=0, y=34, size=11),
            ),
            # ── Image & Map link ────────────────────────────────────────────
            BoardObject(
                id="image-logo",
                type="image",
                x=1265,
                y=190,
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, text="image", x=0, y=34, size=10),
            ),
            BoardObject(
                id="map-self",
                type="map",
                x=1265,
                y=380,
                map_name="demo-static",
                display=DisplayConfig(mode="icon"),
                label=LabelConfig(show=True, text="map → demo", x=0, y=34, size=10),
            ),
        ],
    )

    _save_board_file(cfg)
    logger.info("Seeded built-in demo board.")


def _seed_demo_worldmap() -> None:
    """Write the built-in world demo map to disk if it doesn't already exist."""
    from app.schemas.board import BoardConfig, BoardObject, DisplayConfig, LabelConfig, WorldmapView
    from app.services.board_service import _board_path, _save_board_file

    if _board_path("demo-world").exists():
        return

    # Five demo hosts placed at real European cities + one service per host (slightly offset).
    # fileserver is DOWN in the TestBackend → shows as red marker on the map.
    cfg = BoardConfig(
        name="demo-world",
        readonly=True,
        alias="Geo Board (Demo)",
        backend_id="test",
        icon_size=28,
        view=WorldmapView(lat=50.5, lng=8.0, zoom=5),
        hover_template="{{name}}\nState: {{state}}\n{{output}}",
        objects=[
            # ── Hosts ────────────────────────────────────────────────────────
            BoardObject(
                id="wh-router01",
                type="host",
                lat=50.11,
                lng=8.68,
                x=0,
                y=0,
                host_name="router01",
                label=LabelConfig(show=True, text="router01\nFrankfurt", x=0, y=34, size=11),
            ),
            BoardObject(
                id="wh-switch01",
                type="host",
                lat=52.37,
                lng=4.90,
                x=0,
                y=0,
                host_name="switch01",
                label=LabelConfig(show=True, text="switch01\nAmsterdam", x=0, y=34, size=11),
            ),
            BoardObject(
                id="wh-localhost",
                type="host",
                lat=51.51,
                lng=-0.13,
                x=0,
                y=0,
                host_name="localhost",
                label=LabelConfig(show=True, text="localhost\nLondon", x=0, y=34, size=11),
            ),
            BoardObject(
                id="wh-fileserver",
                type="host",
                lat=48.86,
                lng=2.35,
                x=0,
                y=0,
                host_name="fileserver",
                label=LabelConfig(show=True, text="fileserver\nParis", x=0, y=34, size=11),
            ),
            BoardObject(
                id="wh-mailserver",
                type="host",
                lat=48.14,
                lng=11.58,
                x=0,
                y=0,
                host_name="mailserver",
                label=LabelConfig(show=True, text="mailserver\nMunich", x=0, y=34, size=11),
            ),
            # ── Services ─────────────────────────────────────────────────────
            BoardObject(
                id="ws-http",
                type="service",
                lat=51.55,
                lng=-0.20,
                x=0,
                y=0,
                host_name="localhost",
                service_description="HTTP",
                label=LabelConfig(show=True, text="HTTP", x=0, y=34, size=10),
            ),
            BoardObject(
                id="ws-cpu",
                type="service",
                lat=50.16,
                lng=8.82,
                x=0,
                y=0,
                host_name="router01",
                service_description="CPU Load",
                display=DisplayConfig(mode="gadget", gadget_type="gauge"),
                label=LabelConfig(show=True, text="CPU Load", x=0, y=56, size=10),
            ),
            BoardObject(
                id="ws-disk",
                type="service",
                lat=48.82,
                lng=2.48,
                x=0,
                y=0,
                host_name="fileserver",
                service_description="Disk /",
                label=LabelConfig(show=True, text="Disk /", x=0, y=34, size=10),
            ),
        ],
    )

    _save_board_file(cfg)
    logger.info("Seeded built-in world demo board.")


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
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    from alembic import command

    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")

    engine = create_engine(sync_url)
    try:
        tables = inspect(engine).get_table_names()
        if "users" in tables:
            # Existing tables — check whether migration history is present and valid
            needs_stamp = "alembic_version" not in tables
            if not needs_stamp and "alembic_version" in tables:
                with engine.connect() as conn:
                    row = conn.execute(
                        text("SELECT version_num FROM alembic_version LIMIT 1")
                    ).fetchone()
                needs_stamp = row is None
            if needs_stamp:
                logger.info("Stamping existing database at alembic head.")
                command.stamp(Config(str(alembic_ini)), "head")
            else:
                logger.info("Database already at head, skipping migrations.")
            return
    finally:
        engine.dispose()

    command.upgrade(Config(str(alembic_ini)), "head")
    logger.info("Database migrations applied.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    from app.integrations import checkmk as cmk_integration

    cmk_integration.setup()

    from app.backends.test import TestBackend
    from app.services import backend_service
    from app.services.state_service import register_backend

    if settings.secret_key == "change-me-in-production":
        logger.critical(
            "SECURITY: SECRET_KEY is set to the default insecure value! "
            "Set a strong SECRET_KEY environment variable before running in production."
        )

    logger.info("Starting OrbVis backend…")
    sep = "=" * 60
    print(f"\n{sep}", flush=True)
    import os as _os

    port = _os.environ.get("ORBVIS_PORT", "8082")
    host_port = "" if port == "80" else f":{port}"
    print("  OrbVis is starting up.", flush=True)
    print(f"  Open in your browser: http://localhost{host_port}/orbvis", flush=True)
    print(f"{sep}\n", flush=True)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_migrations)
    logger.info("Database initialized.")

    # Always provide the built-in test backend (no config needed)
    register_backend("test", TestBackend())

    # Load and activate all persisted backend configs
    backend_service.activate_all()

    # In Checkmk/OMD mode: auto-create a Livestatus connection if none exists yet
    if settings.checkmk_omd_root and settings.checkmk_site:
        conn_id = f"cmk_{settings.checkmk_site}"
        if not backend_service.load_all():
            from app.schemas.backend import BackendConfig

            socket_path = str(Path(settings.checkmk_omd_root) / "tmp" / "run" / "live")
            cfg = BackendConfig(
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
            backend_service.create(cfg)
            logger.info("Auto-created Checkmk connection '%s' → %s", conn_id, socket_path)

    # In SSO/CMK mode authentication is handled externally — no local admin needed
    if not settings.checkmk_omd_root:
        await _ensure_admin_user()
    await _seed_default_roles()
    _seed_demo_map()
    _seed_demo_worldmap()

    from app.seed_images import seed_builtin_images

    seed_builtin_images(Path(settings.boards_dir).parent / "images")

    yield
    logger.info("Shutting down OrbVis backend.")


app = FastAPI(
    title="OrbVis API",
    version=APP_VERSION,
    description="REST API for OrbVis – monitoring visualization",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MethodOverrideMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(boards.router, prefix="/api/v1/boards", tags=["boards"])
app.include_router(states.router, prefix="/api/v1", tags=["states"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(backends.router, prefix="/api/v1/backends", tags=["backends"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(images.router, prefix="/api/v1/images", tags=["images"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/api/changelog")
async def get_changelog():
    for candidate in [
        Path(__file__).parent.parent.parent / "CHANGELOG.md",
        Path(__file__).parent.parent / "CHANGELOG.md",
    ]:
        if candidate.is_file():
            return PlainTextResponse(candidate.read_text())
    return PlainTextResponse("")


# Serve background images uploaded via the API
_bg_dir = Path(settings.boards_dir) / "backgrounds"
_bg_dir.mkdir(parents=True, exist_ok=True)
app.mount("/boards/backgrounds", StaticFiles(directory=str(_bg_dir)), name="backgrounds")

# Serve image set images
_images_dir = Path(settings.boards_dir).parent / "images"
_images_dir.mkdir(parents=True, exist_ok=True)
app.mount("/images", StaticFiles(directory=str(_images_dir)), name="images")
