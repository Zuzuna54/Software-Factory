"""
Alembic environment configuration
"""

import asyncio
from logging.config import fileConfig
import os
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from infra.db.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from alembic.ini
database_url = config.get_main_option("sqlalchemy.url")
if not database_url.startswith("postgresql+asyncpg"):
    database_url = f"postgresql+asyncpg://{database_url[database_url.find('://')+3:]}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
    context.configure(
        url=database_url.replace("+asyncpg", ""),  # Use synchronous adapter for offline
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations in synchronous context"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table="alembic_version",
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Debug output to see what values we're working with
    print(f"Using database URL from alembic.ini: {database_url}")

    try:
        connectable = create_async_engine(database_url)

        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

        await connectable.dispose()
    except Exception as e:
        print(f"Error during migration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
