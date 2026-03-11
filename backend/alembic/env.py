"""Alembic environment configuration."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.core.database import Base

# Import all models so Alembic can detect them
import app.models  # noqa: F401

config = context.config

# Use the synchronous URL for migrations — alembic doesn't need async drivers,
# and using aiosqlite here causes a deadlock when called from run_in_executor.
_sync_url = settings.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a plain synchronous engine.

    This avoids the asyncio deadlock that occurs when aiosqlite is used
    from within a thread-pool executor while the main event loop is blocked.
    """
    engine = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )
    with engine.connect() as connection:
        _do_run_migrations(connection)
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
