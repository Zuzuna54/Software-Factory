# agents/db/postgres.py

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import asyncpg
    from asyncpg import Pool
    from asyncpg.exceptions import (
        UniqueViolationError,
    )  # Import specific errors if needed
except ImportError:
    raise ImportError(
        "asyncpg library not installed. Please install it: pip install asyncpg"
    )

logger = logging.getLogger(__name__)


class PostgresClient:
    """Asynchronous PostgreSQL client for the agent system."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        min_pool_size: int = 5,
        max_pool_size: int = 20,
    ):
        self.connection_string = connection_string or os.environ.get(
            "DATABASE_URL",
            "postgresql://agent_user:agent_password@localhost:5432/agent_team",  # Default for local Docker
        )
        self.min_pool_size = min_pool_size
        self.max_pool_size = max_pool_size
        self.pool: Optional[Pool] = None
        self._initializing = False
        self._initialization_lock = asyncio.Lock()

        if not self.connection_string:
            raise ValueError(
                "Database connection string not provided. Set DATABASE_URL environment variable or pass connection_string."
            )

    async def initialize(self) -> None:
        """Initialize the database connection pool idempotently."""
        if self.pool is not None:
            logger.debug("Connection pool already initialized.")
            return

        async with self._initialization_lock:
            # Double check after acquiring lock
            if self.pool is not None:
                logger.debug(
                    "Connection pool already initialized by another coroutine."
                )
                return

            if self._initializing:
                logger.warning("Initialization already in progress, waiting...")
                # Basic wait, could implement more complex waiting if needed
                while self._initializing:
                    await asyncio.sleep(0.1)
                return

            self._initializing = True
            logger.info("Initializing PostgreSQL connection pool...")
            try:
                self.pool = await asyncpg.create_pool(
                    dsn=self.connection_string,
                    min_size=self.min_pool_size,
                    max_size=self.max_pool_size,
                )
                # Test connection
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                logger.info("PostgreSQL connection pool initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}", exc_info=True)
                # Reset pool to None on failure to allow retry
                self.pool = None
                raise  # Re-raise the exception to signal failure
            finally:
                self._initializing = False

    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool is None:
            logger.warning(
                "Attempted to close an uninitialized or already closed connection pool."
            )
            return

        logger.info("Closing PostgreSQL connection pool...")
        await self.pool.close()
        self.pool = None
        logger.info("PostgreSQL connection pool closed.")

    async def _ensure_initialized(self):
        """Ensure the pool is initialized before use."""
        if self.pool is None:
            await self.initialize()
        if self.pool is None:
            # This should ideally not happen if initialize() raises on failure
            raise ConnectionError(
                "Database pool is not initialized after attempting to initialize."
            )

    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return results (e.g., INSERT, UPDATE, DELETE)."""
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as conn:
                status = await conn.execute(query, *args)
                logger.debug(f"Executed query: {query[:100]}..., Status: {status}")
                return status
        except UniqueViolationError as e:
            logger.warning(f"Unique constraint violation during execute: {e}")
            raise  # Re-raise specific errors if needed for handling upstream
        except Exception as e:
            logger.error(
                f"Query execution error: {e} for query: {query[:100]}...", exc_info=True
            )
            raise

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return the first row as a dictionary."""
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                logger.debug(f"Fetched one row for query: {query[:100]}...")
                return dict(row) if row else None
        except Exception as e:
            logger.error(
                f"Query fetch_one error: {e} for query: {query[:100]}...", exc_info=True
            )
            raise

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dictionaries."""
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                logger.debug(f"Fetched {len(rows)} rows for query: {query[:100]}...")
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(
                f"Query fetch_all error: {e} for query: {query[:100]}...", exc_info=True
            )
            raise

    async def fetch_val(self, query: str, *args) -> Any:
        """Execute a query and return a single value from the first row."""
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as conn:
                value = await conn.fetchval(query, *args)
                logger.debug(f"Fetched value for query: {query[:100]}...")
                return value
        except Exception as e:
            logger.error(
                f"Query fetch_val error: {e} for query: {query[:100]}...", exc_info=True
            )
            raise

    def transaction(self):
        """Start a transaction. Used as an async context manager.

        Example:
            async with db_client.transaction() as conn:
                await conn.execute(...)
                await conn.execute(...)
        """
        if self.pool is None:
            # Raise error or initialize? Let's raise for clarity.
            raise ConnectionError(
                "Cannot start a transaction on an uninitialized pool. Call initialize() first."
            )
        # Note: The actual acquire/release logic is handled by asyncpg's pool context manager
        return self.pool.acquire()

    async def execute_many(self, query: str, args_list: List[Tuple]) -> None:
        """Execute a query many times with different arguments within a single transaction."""
        if not args_list:
            logger.debug("execute_many called with empty args_list, doing nothing.")
            return

        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as conn:
                # Execute in a transaction
                async with conn.transaction():
                    await conn.executemany(query, args_list)
                logger.debug(
                    f"Executed query many ({len(args_list)} items): {query[:100]}..."
                )
        except Exception as e:
            logger.error(
                f"Query execute_many error: {e} for query: {query[:100]}...",
                exc_info=True,
            )
            raise

    # Context manager support for easier setup/teardown
    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
