"""Async SQLAlchemy database setup."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables on startup and apply lightweight column migrations."""
    # Import all models so metadata is populated
    import app.models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Add columns introduced after initial schema (SQLite has no IF NOT EXISTS for columns)
        await _add_column_if_missing(conn, "users", "theme", "VARCHAR(10) NOT NULL DEFAULT 'system'")


async def _add_column_if_missing(conn, table: str, column: str, definition: str) -> None:
    """Add a column to an existing table if it does not yet exist (SQLite-compatible)."""
    from sqlalchemy import text

    result = await conn.execute(text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in result.fetchall()}
    if column not in existing:
        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
