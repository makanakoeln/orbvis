"""Orbvis FastAPI application entry point."""

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup and shutdown."""
    from app.backends.test import TestBackend
    from app.services import backend_service
    from app.services.state_service import register_backend

    logger.info("Starting Orbvis backend…")
    await init_db()
    logger.info("Database initialized.")

    # Always provide the built-in test backend (no config needed)
    register_backend("test", TestBackend())

    # Load and activate all persisted backend configs
    backend_service.activate_all()

    await _ensure_admin_user()

    yield
    logger.info("Shutting down Orbvis backend.")


app = FastAPI(
    title="Orbvis API",
    version="2.0.0",
    description="REST API for Orbvis – monitoring visualization",
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
