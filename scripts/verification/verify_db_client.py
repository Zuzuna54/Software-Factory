#!/usr/bin/env python
"""
Simplified test for PostgreSQL database client.
"""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import text, Column, String, Integer, Table, MetaData
from agents.db import get_postgres_client


async def simple_test():
    """Test basic PostgreSQL database client functionality."""
    print("\n----- Testing PostgreSQL Database Client -----")

    # Initialize the database client
    print("Initializing PostgreSQL client...")
    database_url = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory"
    )
    db_client = get_postgres_client(database_url=database_url)

    # Test connection
    print("\nTesting database connection...")
    version = await db_client.fetch_one("SELECT version()")
    print(f"Connected to: {version['version'][:50]}...")

    # Create a test table
    test_table = f"simple_test_{uuid.uuid4().hex[:8]}"
    print(f"\nCreating test table '{test_table}'...")

    create_sql = text(
        f"""
    CREATE TABLE {test_table} (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL
    )
    """
    )

    try:
        # Use transaction to create the table
        async with db_client.transaction() as session:
            await session.execute(create_sql)
            print(f"✅ Table {test_table} created successfully")

            # Insert data within the same transaction
            print(f"Inserting data into {test_table}...")
            insert_sql = text(f"INSERT INTO {test_table} (name) VALUES (:name)")
            await session.execute(insert_sql, {"name": "Test Record"})
            print("✅ Data inserted successfully")

        # Query data after transaction is committed
        print(f"\nQuerying data from {test_table}...")
        select_sql = text(f"SELECT * FROM {test_table}")
        results = await db_client.execute(select_sql)
        print(f"Query results: {results}")

        # Drop table
        print(f"\nCleaning up: dropping {test_table}...")
        drop_sql = text(f"DROP TABLE {test_table}")
        await db_client.execute(drop_sql)
        print(f"✅ Table {test_table} dropped successfully")

        print("\n✅ Simple database test completed successfully!")

    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        # Close the client
        await db_client.close()


if __name__ == "__main__":
    asyncio.run(simple_test())
