# agents/tests/test_postgres.py

import pytest
import uuid
import asyncpg

# from ..db.postgres import PostgresClient
from agents.db.postgres import PostgresClient

pytestmark = pytest.mark.asyncio

# Fixture db_client is provided by conftest.py


@pytest.mark.asyncio
async def test_db_connection(db_client):
    """Test that the database client can connect and execute a simple query."""
    result = await db_client.fetch_val("SELECT 1 + 1")
    assert result == 2


async def test_execute_insert_fetch(db_client: PostgresClient):
    """Test basic INSERT and SELECT operations."""
    agent_id = str(uuid.uuid4())
    agent_type = "test_insert"
    agent_name = "Test Insert Agent"

    # Use execute for INSERT
    await db_client.execute(
        "INSERT INTO agents (agent_id, agent_type, agent_name, active) VALUES ($1, $2, $3, $4)",
        agent_id,
        agent_type,
        agent_name,
        True,
    )

    # Use fetch_one to retrieve
    row = await db_client.fetch_one(
        "SELECT * FROM agents WHERE agent_id = $1", agent_id
    )
    assert row is not None
    assert row["agent_id"] == uuid.UUID(agent_id)
    assert row["agent_type"] == agent_type
    assert row["agent_name"] == agent_name

    # Use fetch_val to get a single value
    name = await db_client.fetch_val(
        "SELECT agent_name FROM agents WHERE agent_id = $1", agent_id
    )
    assert name == agent_name


async def test_fetch_all(db_client: PostgresClient):
    """Test fetching multiple rows."""
    # Insert a couple of agents
    agent_ids = [str(uuid.uuid4()) for _ in range(3)]
    agent_type = "test_fetch_all"
    for i, agent_id in enumerate(agent_ids):
        await db_client.execute(
            "INSERT INTO agents (agent_id, agent_type, agent_name, active) VALUES ($1, $2, $3, $4)",
            agent_id,
            agent_type,
            f"Fetch Agent {i}",
            True,
        )

    # Fetch all agents of this type
    rows = await db_client.fetch_all(
        "SELECT * FROM agents WHERE agent_type = $1 ORDER BY agent_name", agent_type
    )
    assert len(rows) == 3
    assert rows[0]["agent_name"] == "Fetch Agent 0"
    assert rows[1]["agent_name"] == "Fetch Agent 1"
    assert rows[2]["agent_name"] == "Fetch Agent 2"


async def test_transaction_commit(db_client: PostgresClient):
    """Test that transactions commit changes."""
    agent_id = str(uuid.uuid4())
    agent_type = "test_transaction_commit"
    agent_name = "Commit Agent"

    async with db_client.transaction() as conn:  # Use the transaction context manager
        await conn.execute(
            "INSERT INTO agents (agent_id, agent_type, agent_name, active) VALUES ($1, $2, $3, $4)",
            agent_id,
            agent_type,
            agent_name,
            True,
        )

    # Verify data is present outside transaction
    row = await db_client.fetch_one(
        "SELECT * FROM agents WHERE agent_id = $1", agent_id
    )
    assert row is not None
    assert row["agent_name"] == agent_name


async def test_transaction_rollback(db_client: PostgresClient):
    """Test that transactions rollback changes on error."""
    agent_id = str(uuid.uuid4())
    agent_type = "test_transaction_rollback"
    agent_name = "Rollback Agent"

    try:
        async with db_client.transaction() as conn:
            await conn.execute(
                "INSERT INTO agents (agent_id, agent_type, agent_name, active) VALUES ($1, $2, $3, $4)",
                agent_id,
                agent_type,
                agent_name,
                True,
            )
            # Simulate an error
            raise ValueError("Simulated error during transaction")
    except ValueError as e:
        assert "Simulated error" in str(e)
    else:
        pytest.fail("Transaction did not raise the simulated error")

    # Verify data is NOT present outside transaction
    row = await db_client.fetch_one(
        "SELECT * FROM agents WHERE agent_id = $1", agent_id
    )
    assert row is None


async def test_execute_many(db_client: PostgresClient):
    """Test executing a query multiple times with different args."""
    agent_type = "test_execute_many"
    args_list = [
        (str(uuid.uuid4()), agent_type, "ExecMany 1", True),
        (str(uuid.uuid4()), agent_type, "ExecMany 2", True),
    ]

    query = "INSERT INTO agents (agent_id, agent_type, agent_name, active) VALUES ($1, $2, $3, $4)"

    await db_client.execute_many(query, args_list)

    # Verify inserts
    rows = await db_client.fetch_all(
        "SELECT agent_name FROM agents WHERE agent_type = $1 ORDER BY agent_name",
        agent_type,
    )
    assert len(rows) == 2
    assert rows[0]["agent_name"] == "ExecMany 1"
    assert rows[1]["agent_name"] == "ExecMany 2"
