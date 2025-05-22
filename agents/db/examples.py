"""
Examples of using the PostgresClient for database operations.

These examples showcase various operations like:
- Basic connection and query execution
- Transaction management
- Working with models
- Error handling
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .postgres import PostgresClient


async def example_basic_queries(db_client: PostgresClient) -> None:
    """Example of basic query execution."""
    # Check connection
    is_connected = await db_client.check_connection()
    print(f"Database connection: {'OK' if is_connected else 'FAILED'}")

    # Execute a simple query
    users = await db_client.execute("SELECT id, username, email FROM users LIMIT 5")
    print(f"Found {len(users)} users:")
    for user in users:
        print(f"  - {user['username']} ({user['email']})")

    # Execute a parameterized query
    active_agents = await db_client.execute(
        "SELECT * FROM agents WHERE status = :status", {"status": "active"}
    )
    print(f"Found {len(active_agents)} active agents")

    # Fetch a single value
    count = await db_client.fetch_value("SELECT COUNT(*) FROM users")
    print(f"Total users: {count}")


async def example_transaction(db_client: PostgresClient) -> None:
    """Example of transaction management."""
    try:
        # Execute multiple statements in a transaction
        await db_client.execute_in_transaction(
            [
                (
                    "INSERT INTO logs (message) VALUES (:message)",
                    {"message": "Transaction started"},
                ),
                (
                    "UPDATE system_status SET status = :status",
                    {"status": "maintenance"},
                ),
                (
                    "INSERT INTO logs (message) VALUES (:message)",
                    {"message": "Status updated"},
                ),
            ]
        )
        print("Transaction completed successfully")
    except Exception as e:
        print(f"Transaction failed: {str(e)}")

    # Using the transaction context manager
    try:
        async with db_client.transaction() as session:
            await session.execute(
                "INSERT INTO logs (message) VALUES ('Manual transaction')"
            )
            await session.execute(
                "UPDATE system_status SET last_update = CURRENT_TIMESTAMP"
            )
        print("Manual transaction completed successfully")
    except Exception as e:
        print(f"Manual transaction failed: {str(e)}")


async def example_model_operations(db_client: PostgresClient) -> None:
    """Example of working with SQLAlchemy models."""
    from infra.db.models import Artifact, AgentActivity

    # Get by ID
    artifact = await db_client.get_by_id(
        Artifact, "123e4567-e89b-12d3-a456-426614174000"
    )
    if artifact:
        print(f"Found artifact: {artifact.title}")

    # Get all with filtering
    activities = await db_client.get_all(
        AgentActivity, limit=10, agent_id="agent-123", activity_type="reasoning"
    )
    print(f"Found {len(activities)} agent activities")

    # Create new record
    new_id = await db_client.create(
        Artifact,
        title="Example Artifact",
        content="This is an example artifact created via the PostgresClient",
        artifact_type="example",
        status="active",
    )
    print(f"Created new artifact with ID: {new_id}")

    # Update record
    updated = await db_client.update(
        Artifact, new_id, status="archived", last_modified_at="CURRENT_TIMESTAMP"
    )
    print(f"Artifact update: {'success' if updated else 'failed'}")

    # Count records
    count = await db_client.count(Artifact, artifact_type="example")
    print(f"Found {count} example artifacts")


@PostgresClient.retry(max_attempts=3, retry_delay=1.0)
async def example_retry_operation(db_client: PostgresClient) -> Dict[str, Any]:
    """Example of using the retry decorator."""
    # This operation will be retried up to 3 times if it fails
    result = await db_client.fetch_one(
        "SELECT * FROM potentially_flaky_table WHERE id = :id", {"id": 42}
    )
    return result or {}


async def run_examples() -> None:
    """Run all examples."""
    # Create database client
    from os import environ

    # Read from environment or use default
    db_url = environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory",
    )

    db_client = PostgresClient(database_url=db_url, pool_size=5, echo=False)

    try:
        # Run examples
        await example_basic_queries(db_client)
        await example_transaction(db_client)
        await example_model_operations(db_client)

        # Test retry functionality
        result = await example_retry_operation(db_client)
        print(f"Retry operation result: {result}")

        # Check connection stats
        stats = await db_client.get_connection_stats()
        print(f"Connection pool stats: {stats}")

    finally:
        # Close client
        await db_client.close()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run examples
    asyncio.run(run_examples())
