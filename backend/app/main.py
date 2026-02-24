"""NagVis 2 FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.api.v1 import auth, maps, states, users, roles

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    logger.info("Starting NagVis 2 backend…")
    await init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Shutting down NagVis 2 backend.")


app = FastAPI(
    title="NagVis 2 API",
    version="2.0.0",
    description="REST API for NagVis 2 – monitoring visualization",
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


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
