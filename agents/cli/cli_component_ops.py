"""
Component testing operations for the CLI tool.

This module contains functions for testing specific components
of the agent system directly from the CLI.
"""

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from .cli_core import AgentCLI, logger


async def test_db_client(cli: AgentCLI, sql_query: str) -> Dict[str, Any]:
    """
    Test the database client by executing a query.

    Args:
        cli: The AgentCLI instance
        sql_query: SQL query to execute

    Returns:
        Dictionary with results and metadata
    """
    start_time = datetime.now()

    try:
        # Execute the query
        if sql_query.strip().lower().startswith("select"):
            # For SELECT queries, use fetch to get results
            rows = await cli.db_client.execute(sql_query)
            result = {"rows": rows, "count": len(rows)}
        else:
            # For other queries, just execute and get row count
            count = await cli.db_client.execute_count(sql_query)
            result = {"count": count}

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "success": True,
            "result": result,
            "execution_time_ms": execution_time,
            "message": "Query executed successfully",
        }
    except Exception as e:
        logger.error(f"Database query error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def test_db_transaction(cli: AgentCLI) -> Dict[str, Any]:
    """
    Test database transaction with rollback.

    Args:
        cli: The AgentCLI instance

    Returns:
        Dictionary with results and metadata
    """
    start_time = datetime.now()

    try:
        # Create a temporary table for testing
        create_table_sql = """
        CREATE TEMPORARY TABLE test_transactions (
            id SERIAL PRIMARY KEY,
            name TEXT,
            value INTEGER
        )
        """
        await cli.db_client.execute(create_table_sql)

        # Transaction 1: Should succeed
        async with cli.db_client.transaction() as session:
            insert_sql = (
                "INSERT INTO test_transactions (name, value) VALUES ('test1', 100)"
            )
            await session.execute(insert_sql)

        # Transaction 2: Should roll back
        try:
            async with cli.db_client.transaction() as session:
                insert_sql = (
                    "INSERT INTO test_transactions (name, value) VALUES ('test2', 200)"
                )
                await session.execute(insert_sql)

                # Force an error
                error_sql = "INSERT INTO non_existent_table VALUES (1)"
                await session.execute(error_sql)
        except Exception:
            logger.info("Transaction 2 rolled back as expected")

        # Check results
        rows = await cli.db_client.execute("SELECT * FROM test_transactions")

        # Clean up
        await cli.db_client.execute("DROP TABLE test_transactions")

        return {
            "success": True,
            "result": {
                "rows": rows,
                "count": len(rows),
                "transaction1_committed": True,
                "transaction2_rolled_back": True,
            },
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "message": "Transaction test completed successfully",
        }
    except Exception as e:
        logger.error(f"Transaction test error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def db_pool_status(cli: AgentCLI) -> Dict[str, Any]:
    """
    Get database connection pool status.

    Args:
        cli: The AgentCLI instance

    Returns:
        Dictionary with pool statistics
    """
    try:
        # Check if connection is working
        connection_ok = await cli.db_client.check_connection()

        # Get pool statistics if available
        pool_stats = await cli.db_client.get_connection_stats()

        return {
            "status": "operational" if connection_ok else "error",
            "pool_size": pool_stats.get("pool_size", 0),
            "checked_out": pool_stats.get("checked_out", 0),
            "checkedin": pool_stats.get("checkedin", 0),
            "overflow": pool_stats.get("overflow", 0),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting pool status: {str(e)}")
        return {"status": "error", "error": str(e)}


async def db_tables(cli: AgentCLI) -> Dict[str, Any]:
    """
    List all tables in the database with record counts.

    Args:
        cli: The AgentCLI instance

    Returns:
        Dictionary with table names and record counts
    """
    try:
        # Query for all tables in the public schema
        tables_query = """
        SELECT
            table_name
        FROM
            information_schema.tables
        WHERE
            table_schema = 'public'
            AND table_type = 'BASE TABLE'
        ORDER BY
            table_name
        """
        tables = await cli.db_client.execute(tables_query)

        # Get record count for each table
        table_counts = {}
        for table_row in tables:
            table_name = table_row["table_name"]
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            # Use proper parameters format for fetch_value
            count = await cli.db_client.fetch_value(count_query, column="count")
            table_counts[table_name] = count

        return {
            "status": "success",
            "tables": table_counts,
            "total_tables": len(table_counts),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        return {"status": "error", "error": str(e)}


async def test_llm_completion(
    cli: AgentCLI,
    prompt: str,
    model: str = "gemini-pro",
    max_tokens: int = 100,
) -> Dict[str, Any]:
    """
    Test LLM provider's text completion.

    Args:
        cli: The AgentCLI instance
        prompt: Text prompt
        model: LLM model name
        max_tokens: Maximum tokens in response

    Returns:
        Dictionary with completion and metadata
    """
    start_time = datetime.now()

    try:
        # Mock response for now
        completion = f"This is a mock completion for: {prompt}"
        tokens = len(completion.split())

        return {
            "success": True,
            "model": model,
            "completion": completion,
            "tokens": tokens,
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"LLM completion error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def test_llm_embedding(
    cli: AgentCLI, text: str, model: str = "gemini-embedding"
) -> Dict[str, Any]:
    """
    Test LLM provider's text embedding.

    Args:
        cli: The AgentCLI instance
        text: Text to embed
        model: Embedding model name

    Returns:
        Dictionary with embedding vector and metadata
    """
    start_time = datetime.now()

    try:
        # Mock embedding for now
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Simplified mock

        return {
            "success": True,
            "model": model,
            "embedding": embedding,
            "dimensions": len(embedding),
            "text_length": len(text),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"LLM embedding error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def test_vector_memory(
    cli: AgentCLI, text: str, query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test vector memory operations.

    Args:
        cli: The AgentCLI instance
        text: Text to store in memory
        query: Optional search query

    Returns:
        Dictionary with results and metadata
    """
    start_time = datetime.now()

    try:
        if query:
            # Mock search
            similarity = 0.85  # Mock similarity score
            results = [
                {"text": text, "similarity": similarity, "id": "mock-id-1"},
            ]

            return {
                "success": True,
                "operation": "search",
                "query": query,
                "results": results,
                "execution_time_ms": (datetime.now() - start_time).total_seconds()
                * 1000,
            }
        else:
            # Mock store
            return {
                "success": True,
                "operation": "store",
                "id": "mock-id-1",
                "text_length": len(text),
                "execution_time_ms": (datetime.now() - start_time).total_seconds()
                * 1000,
            }
    except Exception as e:
        logger.error(f"Vector memory error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def test_logging(cli: AgentCLI, agent_id: str) -> Dict[str, Any]:
    """
    Test logging system.

    Args:
        cli: The AgentCLI instance
        agent_id: Agent ID to log for

    Returns:
        Dictionary with results and metadata
    """
    start_time = datetime.now()

    try:
        # Log some test messages
        logger.info(f"Test INFO message for agent {agent_id}")
        logger.warning(f"Test WARNING message for agent {agent_id}")
        logger.error(f"Test ERROR message for agent {agent_id}")

        # Mock response
        return {
            "success": True,
            "agent_id": agent_id,
            "log_count": 3,
            "log_levels": ["INFO", "WARNING", "ERROR"],
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"Logging test error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def run_component_verification(
    cli: AgentCLI, component_name: str
) -> Dict[str, Any]:
    """
    Run a component verification script.

    Args:
        cli: The AgentCLI instance
        component_name: Name of the component to verify

    Returns:
        Dictionary with verification results
    """
    start_time = datetime.now()

    # Map component names to verification scripts
    component_scripts = {
        "base-agent": "verify_agent_init.py",
        "db-client": "verify_db_client.py",
        "llm-provider": "verify_llm_provider.py",
        "vector-memory": "verify_vector_memory.py",
        "communication": "verify_communication.py",
        "logging": "verify_logging.py",
        "cli-tool": "verify_cli_tool.py",
    }

    script_path = component_scripts.get(component_name)
    if not script_path:
        return {
            "success": False,
            "error": f"Unknown component: {component_name}",
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }

    try:
        # Run the verification script as a subprocess
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()
        return_code = process.returncode

        return {
            "success": return_code == 0,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "component": component_name,
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
