"""
PostgreSQL database client for asynchronous database operations.

Features:
- Connection pooling
- Asynchronous query execution
- Transaction management
- Error handling and logging
"""

import asyncio
import contextlib
import functools
import logging
import time
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
    Type,
    AsyncGenerator,
)

from sqlalchemy import Row, TextClause, select, text, insert, update, delete, func
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session

logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar("T")
ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class PostgresClient:
    """
    Asynchronous PostgreSQL client with connection pooling and transaction management.

    Provides a clean interface for executing queries and managing transactions
    with comprehensive error handling and logging.
    """

    def __init__(
        self,
        database_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        echo: bool = False,
    ):
        """
        Initialize the PostgreSQL client.

        Args:
            database_url: Database connection URL (SQLAlchemy format)
            pool_size: Size of the connection pool
            max_overflow: Maximum number of connections to allow beyond the pool size
            pool_timeout: Number of seconds to wait for a connection before timing out
            pool_recycle: Number of seconds after which a connection is recycled
            echo: If True, log all SQL statements (for debugging)
        """
        self.database_url = database_url
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo,
            pool_pre_ping=True,  # Verify connections before using them
        )
        self.async_session_factory = async_sessionmaker(
            bind=self.engine, expire_on_commit=False
        )
        self.logger = logger

    async def close(self) -> None:
        """Close all connections in the pool."""
        await self.engine.dispose()
        self.logger.info("Database connection pool closed")

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create and manage a database session.

        Usage:
            async with db_client.session() as session:
                result = await session.execute(query)

        Yields:
            An async SQLAlchemy session
        """
        session = self.async_session_factory()
        try:
            yield session
        except Exception as e:
            await session.rollback()
            self.logger.error(f"Session error: {str(e)}")
            raise
        finally:
            await session.close()

    @contextlib.asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create a session and begin a transaction.

        Automatically commits or rolls back the transaction.

        Usage:
            async with db_client.transaction() as session:
                result = await session.execute(query)

        Yields:
            An async SQLAlchemy session with an active transaction
        """
        async with self.session() as session:
            async with session.begin():
                try:
                    yield session
                except Exception as e:
                    self.logger.error(
                        f"Transaction error: {str(e)}\n{traceback.format_exc()}"
                    )
                    raise

    async def execute(
        self,
        query: Union[str, TextClause],
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SQL query and return the results.

        Args:
            query: SQL query string or TextClause
            params: Query parameters
            timeout: Query timeout in seconds

        Returns:
            List of dictionaries with the query results
        """
        start_time = time.time()
        params = params or {}

        if isinstance(query, str):
            query = text(query)

        try:
            async with self.session() as session:
                # Set statement timeout if specified
                if timeout:
                    await session.execute(
                        text(f"SET statement_timeout = {int(timeout * 1000)}")
                    )

                # Execute query
                cursor = await session.execute(query, params)

                result = []

                # Try to get results - this will work for SELECT statements
                try:
                    # Get column names
                    columns = cursor.keys()
                    # Convert rows to dictionaries
                    result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                except Exception:
                    # This is likely a statement that doesn't return rows (INSERT, CREATE, etc.)
                    # Just return an empty result list
                    pass

                # Reset statement timeout
                if timeout:
                    await session.execute(text("SET statement_timeout = 0"))

                execution_time = time.time() - start_time
                self.logger.debug(f"Query executed in {execution_time:.3f}s: {query}")

                return result
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self.logger.error(f"Query timeout after {execution_time:.3f}s: {query}")
            raise
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(
                f"Query error after {execution_time:.3f}s: {str(e)}\nQuery: {query}\nParameters: {params}"
            )
            raise

    async def execute_many(
        self,
        query: Union[str, TextClause],
        params_list: List[Dict[str, Any]],
    ) -> None:
        """
        Execute a SQL query with multiple sets of parameters.

        Args:
            query: SQL query string or TextClause
            params_list: List of parameter dictionaries
        """
        if not params_list:
            return

        if isinstance(query, str):
            query = text(query)

        try:
            async with self.transaction() as session:
                for params in params_list:
                    await session.execute(query, params)

            self.logger.debug(f"Executed batch query {len(params_list)} times: {query}")
        except Exception as e:
            self.logger.error(f"Batch query error: {str(e)}\nQuery: {query}")
            raise

    async def fetch_one(
        self,
        query: Union[str, TextClause],
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a SQL query and return the first result or None.

        Args:
            query: SQL query string or TextClause
            params: Query parameters

        Returns:
            A dictionary with the first result or None if no results
        """
        results = await self.execute(query, params)
        return results[0] if results else None

    async def fetch_value(
        self,
        query: Union[str, TextClause],
        params: Optional[Dict[str, Any]] = None,
        column: str = None,
    ) -> Any:
        """
        Execute a SQL query and return a single value.

        Args:
            query: SQL query string or TextClause
            params: Query parameters
            column: Column name to return (if None, returns the first column)

        Returns:
            The value of the specified column from the first row
        """
        result = await self.fetch_one(query, params)
        if not result:
            return None

        if column is None:
            # Return the first column value
            return next(iter(result.values()))

        return result.get(column)

    async def execute_in_transaction(
        self,
        queries: List[Tuple[Union[str, TextClause], Optional[Dict[str, Any]]]],
    ) -> None:
        """
        Execute multiple SQL queries in a single transaction.

        Args:
            queries: List of (query, params) tuples
        """
        try:
            async with self.transaction() as session:
                for query, params in queries:
                    if isinstance(query, str):
                        query = text(query)
                    await session.execute(query, params or {})

            self.logger.debug(f"Executed {len(queries)} queries in transaction")
        except Exception as e:
            self.logger.error(f"Transaction error: {str(e)}\n{traceback.format_exc()}")
            raise

    async def check_connection(self) -> bool:
        """
        Check if the database connection is working.

        Returns:
            True if the connection is working, False otherwise
        """
        try:
            await self.fetch_value("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"Connection check failed: {str(e)}")
            return False

    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the connection pool.

        Returns:
            Dictionary with connection pool statistics
        """
        return {
            "pool_size": self.engine.pool.size(),
            "checked_out": self.engine.pool.checkedout(),
            "overflow": self.engine.pool.overflow(),
            "checkedin": self.engine.pool.checkedin(),
        }

    @staticmethod
    def retry(
        max_attempts: int = 3,
        retry_delay: float = 0.5,
        backoff_factor: float = 2.0,
        exceptions: Tuple[Exception, ...] = (Exception,),
    ) -> Callable[[Callable[..., T]], Callable[..., T]]:
        """
        Decorator to retry a database operation on failure.

        Args:
            max_attempts: Maximum number of attempts
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Factor by which to increase the delay on each retry
            exceptions: Tuple of exceptions to catch and retry

        Returns:
            Decorator function
        """

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                last_exception = None
                delay = retry_delay

                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                            f"Retrying in {delay:.2f}s..."
                        )

                        if attempt < max_attempts:
                            await asyncio.sleep(delay)
                            delay *= backoff_factor
                        else:
                            logger.error(
                                f"All {max_attempts} attempts failed. Last error: {str(e)}"
                            )
                            raise

                # This should never happen, but added for type safety
                assert last_exception is not None
                raise last_exception

            return wrapper

        return decorator

    # Model operations

    async def get_by_id(
        self, model_class: Type[ModelT], id_value: Any, id_column: str = "id"
    ) -> Optional[ModelT]:
        """
        Get a model instance by its ID.

        Args:
            model_class: The SQLAlchemy model class
            id_value: The ID value to look up
            id_column: The name of the ID column (default: "id")

        Returns:
            The model instance if found, None otherwise
        """
        try:
            async with self.session() as session:
                stmt = select(model_class).where(
                    getattr(model_class, id_column) == id_value
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
        except Exception as e:
            self.logger.error(f"Error getting {model_class.__name__} by ID: {str(e)}")
            return None

    async def get_all(
        self,
        model_class: Type[ModelT],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[Any] = None,
        **filters,
    ) -> List[ModelT]:
        """
        Get all instances of a model with optional filtering.

        Args:
            model_class: The SQLAlchemy model class
            limit: Maximum number of results to return
            offset: Number of results to skip
            order_by: Column or expression to order by
            **filters: Equality filters to apply (e.g., status="active")

        Returns:
            List of model instances
        """
        try:
            async with self.session() as session:
                stmt = select(model_class)

                # Apply filters
                for key, value in filters.items():
                    if hasattr(model_class, key):
                        stmt = stmt.where(getattr(model_class, key) == value)

                # Apply ordering
                if order_by is not None:
                    stmt = stmt.order_by(order_by)

                # Apply pagination
                if limit is not None:
                    stmt = stmt.limit(limit)
                if offset is not None:
                    stmt = stmt.offset(offset)

                result = await session.execute(stmt)
                return list(result.scalars().all())
        except Exception as e:
            self.logger.error(f"Error getting all {model_class.__name__}: {str(e)}")
            return []

    async def create(self, model_class: Type[ModelT], **values) -> Optional[Any]:
        """
        Create a new instance of a model.

        Args:
            model_class: The SQLAlchemy model class
            **values: Values to set on the new instance

        Returns:
            The ID of the created instance if successful, None otherwise
        """
        try:
            async with self.transaction() as session:
                stmt = insert(model_class).values(**values).returning(model_class.id)
                result = await session.execute(stmt)
                return result.scalar_one()
        except Exception as e:
            self.logger.error(f"Error creating {model_class.__name__}: {str(e)}")
            return None

    async def update(
        self, model_class: Type[ModelT], id_value: Any, id_column: str = "id", **values
    ) -> bool:
        """
        Update an existing model instance.

        Args:
            model_class: The SQLAlchemy model class
            id_value: The ID value of the instance to update
            id_column: The name of the ID column (default: "id")
            **values: Values to update

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.transaction() as session:
                stmt = (
                    update(model_class)
                    .where(getattr(model_class, id_column) == id_value)
                    .values(**values)
                )
                result = await session.execute(stmt)
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error updating {model_class.__name__}: {str(e)}")
            return False

    async def delete(
        self, model_class: Type[ModelT], id_value: Any, id_column: str = "id"
    ) -> bool:
        """
        Delete a model instance.

        Args:
            model_class: The SQLAlchemy model class
            id_value: The ID value of the instance to delete
            id_column: The name of the ID column (default: "id")

        Returns:
            True if successful, False otherwise
        """
        try:
            async with self.transaction() as session:
                stmt = delete(model_class).where(
                    getattr(model_class, id_column) == id_value
                )
                result = await session.execute(stmt)
                return result.rowcount > 0
        except Exception as e:
            self.logger.error(f"Error deleting {model_class.__name__}: {str(e)}")
            return False

    async def count(self, model_class: Type[ModelT], **filters) -> int:
        """
        Count the number of instances of a model with optional filtering.

        Args:
            model_class: The SQLAlchemy model class
            **filters: Equality filters to apply (e.g., status="active")

        Returns:
            The count of matching instances
        """
        try:
            async with self.session() as session:
                stmt = select(func.count()).select_from(model_class)

                # Apply filters
                for key, value in filters.items():
                    if hasattr(model_class, key):
                        stmt = stmt.where(getattr(model_class, key) == value)

                result = await session.execute(stmt)
                return result.scalar_one()
        except Exception as e:
            self.logger.error(f"Error counting {model_class.__name__}: {str(e)}")
            return 0


# Create an async generator for use with context managers
from typing import AsyncGenerator
