"""OrbVis FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


class MethodOverrideMiddleware:
    """Tunnel PATCH/PUT/DELETE through POST via X-HTTP-Method-Override header.

    Some reverse proxies (e.g. OMD/Checkmk Apache) block non-GET/POST methods.
    The frontend sends POST with X-HTTP-Method-Override: PATCH (etc.) and this
    middleware rewrites the ASGI scope method before routing, so all existing
    FastAPI routes work unchanged.
    """

    _ALLOWED = frozenset(("PATCH", "PUT", "DELETE"))

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "http" and scope["method"] == "POST":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            override = headers.get(b"x-http-method-override", b"").decode().upper()
            if override in self._ALLOWED:
                scope = {**scope, "method": override}
        await self.app(scope, receive, send)

from app.api.v1 import auth, backends, icons, maps, roles, settings as settings_api, states, users
from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db

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

    defaults = [
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


def _seed_demo_map() -> None:
    """Write the built-in demo map to disk if it doesn't already exist."""
    from app.schemas.map import MapConfig, MapGlobals, MapObject
    from app.services.map_service import _map_path, _save_map_file

    if _map_path("demo").exists():
        return

    # Layout overview (x: 150–900, y: 50–530)
    #
    #  [HOSTS]                     [SERVICES]       [GROUPS]     [SHAPE/MAP]
    #  localhost ─── router01      HTTP  PING        linux-srv    shape
    #       \       /              CPU▓  Disk▓       web-svc      map →
    #        fileserver
    #  ══ weathermap lines ══
    #  localhost→fileserver  (CPU Load perf data, line_type=20)
    #  router01→fileserver   (HTTP perf data,     line_type=20)
    #
    # Section x-offsets: Hosts 160-440, Services 540-680, Groups 760-800, Other 880

    cfg = MapConfig(
        name="demo",
        globals=MapGlobals(
            alias="OrbVis Demo",
            icon_size=28,
            backend_id="test",
            map_type="static",
            hover_template="{{name}}\nState: {{state}}\n{{output}}",
        ),
        objects=[
            # ── Hosts ───────────────────────────────────────────────────────
            MapObject(
                id="host-localhost",
                type="host",
                x=200, y=140,
                host_name="localhost",
                view_type="icon",
                label_show=True, label_text="localhost",
                label_x=0, label_y=34, label_size=11,
            ),
            MapObject(
                id="host-router01",
                type="host",
                x=420, y=140,
                host_name="router01",
                view_type="icon",
                label_show=True, label_text="router01",
                label_x=0, label_y=34, label_size=11,
            ),
            MapObject(
                id="host-fileserver",
                type="host",
                x=310, y=280,
                host_name="fileserver",
                view_type="icon",
                label_show=True, label_text="fileserver",
                label_x=0, label_y=34, label_size=11,
            ),

            # ── Lines ───────────────────────────────────────────────────────
            # Plain line: localhost ↔ router01 (color = host state)
            MapObject(
                id="line-loc-rtr",
                type="line",
                x=200, y=140,
                label_show=False,
                line_type=10,
                extra={"x2": 420, "y2": 140},
            ),
            # Weathermap: localhost → fileserver  (perf_data from CPU Load service)
            MapObject(
                id="wm-loc-fs",
                type="line",
                x=200, y=140,
                host_name="localhost",
                service_description="CPU Load",
                label_show=False,
                line_type=20,
                extra={"x2": 310, "y2": 280},
            ),
            # Weathermap: router01 → fileserver  (perf_data from HTTP service)
            MapObject(
                id="wm-rtr-fs",
                type="line",
                x=420, y=140,
                host_name="router01",
                service_description="HTTP",
                label_show=False,
                line_type=20,
                extra={"x2": 310, "y2": 280},
            ),

            # ── Services ────────────────────────────────────────────────────
            MapObject(
                id="svc-http",
                type="service",
                x=560, y=140,
                host_name="localhost",
                service_description="HTTP",
                view_type="icon",
                label_show=True,
                label_x=0, label_y=34, label_size=10,
            ),
            MapObject(
                id="svc-ping",
                type="service",
                x=680, y=140,
                host_name="router01",
                service_description="PING",
                view_type="icon",
                label_show=True,
                label_x=0, label_y=34, label_size=10,
            ),
            MapObject(
                id="svc-cpu-gauge",
                type="service",
                x=560, y=260,
                host_name="localhost",
                service_description="CPU Load",
                view_type="gadget",
                gadget_type="gauge",
                label_show=True,
                label_text="CPU Load",
                label_x=0, label_y=56, label_size=10,
            ),
            MapObject(
                id="svc-disk-bar",
                type="service",
                x=680, y=260,
                host_name="fileserver",
                service_description="Disk /",
                view_type="gadget",
                gadget_type="bar",
                label_show=True,
                label_text="Disk /",
                label_x=0, label_y=56, label_size=10,
            ),

            # ── Groups ──────────────────────────────────────────────────────
            MapObject(
                id="hg-linux",
                type="hostgroup",
                x=800, y=140,
                group_name="linux-servers",
                view_type="icon",
                label_show=True, label_text="linux-servers",
                label_x=0, label_y=34, label_size=11,
            ),
            MapObject(
                id="sg-web",
                type="servicegroup",
                x=800, y=280,
                group_name="web-services",
                view_type="icon",
                label_show=True, label_text="web-services",
                label_x=0, label_y=34, label_size=11,
            ),

            # ── Shape & Map link ────────────────────────────────────────────
            MapObject(
                id="shape-logo",
                type="shape",
                x=930, y=140,
                icon=None,
                view_type="icon",
                label_show=True,
                label_text="shape",
                label_x=0, label_y=34, label_size=10,
            ),
            MapObject(
                id="map-self",
                type="map",
                x=930, y=280,
                map_name="demo",
                view_type="icon",
                label_show=True,
                label_text="map → demo",
                label_x=0, label_y=34, label_size=10,
            ),

        ],
    )

    _save_map_file(cfg)
    logger.info("Seeded built-in demo map.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    from app.backends.test import TestBackend
    from app.services import backend_service
    from app.services.state_service import register_backend

    logger.info("Starting OrbVis backend…")
    sep = "=" * 60
    print(f"\n{sep}", flush=True)
    import os as _os
    port = _os.environ.get("ORBVIS_PORT", "8082")
    host_port = "" if port == "80" else f":{port}"
    print("  OrbVis is starting up.", flush=True)
    print(f"  Open in your browser: http://localhost{host_port}/orbvis", flush=True)
    print(f"{sep}\n", flush=True)
    await init_db()
    logger.info("Database initialized.")

    # Always provide the built-in test backend (no config needed)
    register_backend("test", TestBackend())

    # Load and activate all persisted backend configs
    backend_service.activate_all()

    # In SSO/CMK mode authentication is handled externally — no local admin needed
    if not settings.checkmk_omd_root:
        await _ensure_admin_user()
    await _seed_default_roles()
    _seed_demo_map()

    yield
    logger.info("Shutting down OrbVis backend.")


app = FastAPI(
    title="OrbVis API",
    version="2.0.0",
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

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(maps.router, prefix="/api/v1/maps", tags=["maps"])
app.include_router(states.router, prefix="/api/v1", tags=["states"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(backends.router, prefix="/api/v1/backends", tags=["backends"])
app.include_router(settings_api.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(icons.router, prefix="/api/v1/icons", tags=["icons"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


# Serve background images uploaded via the API
_bg_dir = Path(settings.maps_dir) / "backgrounds"
_bg_dir.mkdir(parents=True, exist_ok=True)
app.mount("/maps/backgrounds", StaticFiles(directory=str(_bg_dir)), name="backgrounds")

# Serve icon set images
_icons_dir = Path(settings.maps_dir).parent / "icons"
_icons_dir.mkdir(parents=True, exist_ok=True)
app.mount("/icons", StaticFiles(directory=str(_icons_dir)), name="icons")
