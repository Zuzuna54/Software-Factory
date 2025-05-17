"""
Database clients for interacting with various databases.
"""

from .postgres import PostgresClient

__all__ = ["PostgresClient", "get_postgres_client"]

_postgres_instance = None


def get_postgres_client(
    database_url: str = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
    pool_recycle: int = 1800,
    echo: bool = False,
) -> PostgresClient:
    """
    Get or create a PostgreSQL client instance.

    Uses a singleton pattern to reuse the same client across the application.

    Args:
        database_url: Database connection URL (SQLAlchemy format)
        pool_size: Size of the connection pool
        max_overflow: Maximum number of connections to allow beyond the pool size
        pool_timeout: Number of seconds to wait for a connection before timing out
        pool_recycle: Number of seconds after which a connection is recycled
        echo: If True, log all SQL statements (for debugging)

    Returns:
        PostgreSQL client instance
    """
    global _postgres_instance

    if _postgres_instance is None and database_url is not None:
        _postgres_instance = PostgresClient(
            database_url=database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            echo=echo,
        )

    if _postgres_instance is None:
        raise ValueError(
            "PostgreSQL client not initialized. "
            "Provide database_url on first call to get_postgres_client()."
        )

    return _postgres_instance
