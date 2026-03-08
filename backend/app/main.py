"""OrbVis FastAPI application entry point."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import auth, backends, maps, roles, states, users
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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    from app.backends.test import TestBackend
    from app.services import backend_service
    from app.services.state_service import register_backend

    logger.info("Starting OrbVis backend…")
    await init_db()
    logger.info("Database initialized.")

    # Always provide the built-in test backend (no config needed)
    register_backend("test", TestBackend())

    # Load and activate all persisted backend configs
    backend_service.activate_all()

    await _ensure_admin_user()
    await _seed_default_roles()

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

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(maps.router, prefix="/api/v1/maps", tags=["maps"])
app.include_router(states.router, prefix="/api/v1", tags=["states"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(roles.router, prefix="/api/v1/roles", tags=["roles"])
app.include_router(backends.router, prefix="/api/v1/backends", tags=["backends"])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}


# Serve background images uploaded via the API
_bg_dir = Path(settings.maps_dir) / "backgrounds"
_bg_dir.mkdir(parents=True, exist_ok=True)
app.mount("/maps/backgrounds", StaticFiles(directory=str(_bg_dir)), name="backgrounds")
