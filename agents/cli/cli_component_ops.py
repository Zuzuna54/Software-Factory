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
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid
import random

from .cli_core import AgentCLI, logger

# Add SQLAlchemy text import
from sqlalchemy import text


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
    Test database transaction functionality.

    Args:
        cli: The AgentCLI instance

    Returns:
        Dictionary with results and metadata
    """
    start_time = datetime.now()

    try:
        # First transaction - count agents
        agent_count = 0
        async with cli.db_client.transaction() as session:
            result = await session.execute(text("SELECT COUNT(*) as count FROM agents"))
            row = result.fetchone()
            agent_count = row.count if row else 0

        # Second transaction - check transaction isolation
        isolation_level = "unknown"
        async with cli.db_client.transaction() as session:
            result = await session.execute(text("SHOW transaction_isolation"))
            row = result.fetchone()
            isolation_level = row[0] if row else "unknown"

        return {
            "success": True,
            "result": {
                "agent_count": agent_count,
                "transaction_isolation": isolation_level,
                "db_supports_transactions": True,
            },
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
            "message": "Basic transaction functionality test completed successfully",
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


async def db_metrics(cli: AgentCLI) -> Dict[str, Any]:
    """
    Show database query performance metrics.

    Args:
        cli: The AgentCLI instance

    Returns:
        Dictionary with query performance metrics
    """
    try:
        # Query for index usage statistics
        index_stats_query = """
        SELECT
            schemaname,
            relname AS table_name,
            indexrelname AS index_name,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM
            pg_stat_user_indexes
        ORDER BY
            idx_scan DESC
        LIMIT 10
        """
        index_stats = await cli.db_client.execute(index_stats_query)

        # Query for table statistics
        table_stats_query = """
        SELECT
            schemaname,
            relname AS table_name,
            seq_scan,
            seq_tup_read,
            n_tup_ins,
            n_tup_upd,
            n_tup_del,
            n_live_tup,
            n_dead_tup
        FROM
            pg_stat_user_tables
        ORDER BY
            n_live_tup DESC
        LIMIT 10
        """
        table_stats = await cli.db_client.execute(table_stats_query)

        # Query for slow queries if pg_stat_statements is available
        try:
            slow_queries_query = """
            SELECT
                query,
                calls,
                total_exec_time,
                min_exec_time,
                max_exec_time,
                mean_exec_time,
                rows
            FROM
                pg_stat_statements
            ORDER BY
                total_exec_time DESC
            LIMIT 5
            """
            slow_queries = await cli.db_client.execute(slow_queries_query)
        except Exception:
            # pg_stat_statements might not be available
            logger.info("pg_stat_statements not available, skipping slow queries")
            slow_queries = []

        # Query for database size
        db_size_query = """
        SELECT
            pg_database.datname,
            pg_size_pretty(pg_database_size(pg_database.datname)) AS size
        FROM
            pg_database
        WHERE
            datname = current_database()
        """
        db_size = await cli.db_client.execute(db_size_query)

        return {
            "status": "success",
            "index_stats": index_stats,
            "table_stats": table_stats,
            "slow_queries": slow_queries,
            "database_size": db_size[0] if db_size else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting database metrics: {str(e)}")
        return {"status": "error", "error": str(e)}


async def test_chat_completion(
    cli: AgentCLI,
    messages: List[Dict[str, str]],
    model: str = "gemini-pro",
    max_tokens: int = 100,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """
    Test LLM provider's chat completion.

    Args:
        cli: The AgentCLI instance
        messages: List of messages in the conversation
        model: LLM model name
        max_tokens: Maximum tokens in response
        temperature: Temperature for sampling (0.0-1.0)

    Returns:
        Dictionary with completion and metadata
    """
    start_time = datetime.now()

    try:
        # For now, we'll mock this as we don't want to make actual API calls in the test
        # In a real implementation, you would use the actual LLM provider

        system_message = next(
            (msg["content"] for msg in messages if msg["role"] == "system"),
            "You are a helpful assistant.",
        )
        user_messages = [msg["content"] for msg in messages if msg["role"] == "user"]
        last_user_message = user_messages[-1] if user_messages else "Hello"

        completion = f"This is a mock chat response to: {last_user_message}\n\n"
        completion += (
            f"I'm acting as instructed in the system message: {system_message}\n"
        )
        completion += f"This response was generated with temperature={temperature} and max_tokens={max_tokens}."

        tokens = len(completion.split())

        return {
            "status": "success",
            "model": model,
            "completion": completion,
            "finish_reason": "stop",
            "tokens": {
                "prompt": sum(len(msg["content"].split()) for msg in messages),
                "completion": tokens,
                "total": sum(len(msg["content"].split()) for msg in messages) + tokens,
            },
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"Chat completion error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def test_function_call(
    cli: AgentCLI,
    prompt: str,
    functions: List[Dict[str, Any]],
    model: str = "gemini-pro",
) -> Dict[str, Any]:
    """
    Test LLM provider's function calling capability.

    Args:
        cli: The AgentCLI instance
        prompt: User prompt for function calling
        functions: List of function definitions
        model: LLM model name

    Returns:
        Dictionary with function call results
    """
    start_time = datetime.now()

    try:
        # For now, we'll mock this as we don't want to make actual API calls in the test
        # In a real implementation, you would use the actual LLM provider

        # Choose a function from the provided list based on the prompt
        function_names = [f["name"] for f in functions]

        # Simple keyword matching to determine which function to call
        matched_function = None
        matched_function_def = None

        for function in functions:
            function_name = function["name"]
            if function_name.lower() in prompt.lower():
                matched_function = function_name
                matched_function_def = function
                break

        # If no match found, pick the first function
        if not matched_function and functions:
            matched_function = functions[0]["name"]
            matched_function_def = functions[0]

        # Prepare a mock function call response
        if matched_function:
            # Extract required parameters from function definition
            required_params = {}
            if (
                "parameters" in matched_function_def
                and "properties" in matched_function_def["parameters"]
            ):
                for param_name, param_details in matched_function_def["parameters"][
                    "properties"
                ].items():
                    # Mock parameter values based on type
                    if param_details.get("type") == "string":
                        required_params[param_name] = f"sample_{param_name}"
                    elif (
                        param_details.get("type") == "number"
                        or param_details.get("type") == "integer"
                    ):
                        required_params[param_name] = 42
                    elif param_details.get("type") == "boolean":
                        required_params[param_name] = True
                    else:
                        required_params[param_name] = None

            function_call = {"name": matched_function, "arguments": required_params}
        else:
            function_call = None

        return {
            "status": "success",
            "model": model,
            "prompt": prompt,
            "available_functions": function_names,
            "function_call": function_call,
            "message": (
                "The model chose to call a function."
                if function_call
                else "The model chose not to call a function."
            ),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"Function call error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def list_llm_models(cli: AgentCLI) -> Dict[str, Any]:
    """
    List available LLM models.

    Args:
        cli: The AgentCLI instance

    Returns:
        Dictionary with available models
    """
    try:
        # For now, we'll return a mock list of models
        # In a real implementation, you would fetch this from the LLM provider

        models = [
            {
                "id": "gemini-pro",
                "name": "Gemini Pro",
                "description": "Google's Gemini Pro model for general text generation and reasoning",
                "capabilities": ["text-generation", "chat", "function-calling"],
                "max_tokens": 32000,
                "pricing": {
                    "input": "$0.000125 / 1K tokens",
                    "output": "$0.000375 / 1K tokens",
                },
            },
            {
                "id": "gemini-pro-vision",
                "name": "Gemini Pro Vision",
                "description": "Multimodal model for text and image understanding",
                "capabilities": ["text-generation", "chat", "image-understanding"],
                "max_tokens": 32000,
                "pricing": {
                    "input": "$0.0025 / 1K tokens",
                    "output": "$0.0075 / 1K tokens",
                },
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "description": "Latest model with improved performance and longer context",
                "capabilities": [
                    "text-generation",
                    "chat",
                    "function-calling",
                    "code-generation",
                ],
                "max_tokens": 128000,
                "pricing": {
                    "input": "$0.0005 / 1K tokens",
                    "output": "$0.0015 / 1K tokens",
                },
            },
            {
                "id": "gemini-embedding",
                "name": "Gemini Embedding",
                "description": "Text embedding model for semantic search and similarity",
                "capabilities": ["embeddings"],
                "dimensions": 3072,
                "pricing": {"input": "$0.0001 / 1K tokens", "output": "$0.00"},
            },
        ]

        # Get default model if configured
        default_model = "gemini-pro"

        return {
            "status": "success",
            "models": models,
            "default_model": default_model,
            "count": len(models),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return {"status": "error", "error": str(e)}


async def test_memory_context(
    cli: AgentCLI, context_items: List[str], query: str, max_tokens: int = 1000
) -> Dict[str, Any]:
    """
    Test context window management for memory.

    Args:
        cli: The AgentCLI instance
        context_items: List of text items to include in context
        query: Query to test against the context
        max_tokens: Maximum tokens for context window

    Returns:
        Dictionary with context management results
    """
    start_time = datetime.now()

    try:
        # For demonstration purposes, we'll simulate context window management

        # Calculate approximate token count for each item
        token_counts = [len(item.split()) for item in context_items]
        total_tokens = sum(token_counts)

        # Simulate context window truncation if needed
        included_items = []
        truncated_items = []
        running_token_count = 0

        for i, item in enumerate(context_items):
            if running_token_count + token_counts[i] <= max_tokens:
                included_items.append(item)
                running_token_count += token_counts[i]
            else:
                truncated_items.append(item)

        # Simulate relevance ranking
        relevance_scores = []
        for item in included_items:
            # Simple relevance scoring based on word overlap
            query_words = set(query.lower().split())
            item_words = set(item.lower().split())
            overlap = len(query_words.intersection(item_words))
            relevance = overlap / max(len(query_words), 1)
            relevance_scores.append(relevance)

        # Sort items by relevance
        sorted_items = [
            {"text": item, "relevance": score, "tokens": len(item.split())}
            for item, score in zip(included_items, relevance_scores)
        ]
        sorted_items.sort(key=lambda x: x["relevance"], reverse=True)

        return {
            "status": "success",
            "context_management": {
                "total_items": len(context_items),
                "included_items": len(included_items),
                "truncated_items": len(truncated_items),
                "total_tokens": total_tokens,
                "included_tokens": running_token_count,
                "max_tokens": max_tokens,
                "utilization": f"{running_token_count / max_tokens * 100:.1f}%",
            },
            "items_by_relevance": sorted_items,
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"Memory context test error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def test_memory_index(
    cli: AgentCLI,
    index_operation: str,
    content: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    item_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Test memory indexing operations.

    Args:
        cli: The AgentCLI instance
        index_operation: Operation to perform (add, update, delete, get)
        content: Content to index (for add/update operations)
        metadata: Metadata for the indexed content
        item_id: ID of the item to operate on (for update/delete/get)

    Returns:
        Dictionary with indexing operation results
    """
    start_time = datetime.now()

    try:
        # For demonstration purposes, we'll simulate memory indexing

        # Validate the operation
        valid_operations = ["add", "update", "delete", "get"]
        if index_operation not in valid_operations:
            return {
                "status": "error",
                "error": f"Invalid operation: {index_operation}. Must be one of: {', '.join(valid_operations)}",
            }

        # Generate a mock item ID if needed
        if index_operation == "add" and not item_id:
            item_id = str(uuid.uuid4())

        # Check requirements for each operation
        if index_operation in ["add", "update"] and not content:
            return {
                "status": "error",
                "error": f"Content is required for {index_operation} operation",
            }

        if index_operation in ["update", "delete", "get"] and not item_id:
            return {
                "status": "error",
                "error": f"Item ID is required for {index_operation} operation",
            }

        # Simulate vector embedding
        if content:
            # Mock embedding generation (just using a fixed vector size)
            embedding_dimension = 3072
            mock_embedding = [
                0.0
            ] * embedding_dimension  # Normally would be actual embedding values

            # For demo, set the first few values to something based on content length
            for i in range(min(10, len(content))):
                if i < embedding_dimension:
                    mock_embedding[i] = (ord(content[i]) % 10) / 10.0
        else:
            mock_embedding = None

        # Simulate the requested operation
        if index_operation == "add":
            result = {
                "operation": "add",
                "item_id": item_id,
                "status": "success",
                "content_length": len(content) if content else 0,
                "embedding_dimension": 3072,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
        elif index_operation == "update":
            result = {
                "operation": "update",
                "item_id": item_id,
                "status": "success",
                "content_length": len(content) if content else 0,
                "embedding_dimension": 3072,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow().isoformat(),
            }
        elif index_operation == "delete":
            result = {
                "operation": "delete",
                "item_id": item_id,
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
            }
        elif index_operation == "get":
            # For get, we'll mock some content and metadata
            mock_content = f"This is mock content for item {item_id}"
            mock_metadata = metadata or {
                "type": "test",
                "created_at": datetime.utcnow().isoformat(),
            }

            result = {
                "operation": "get",
                "item_id": item_id,
                "status": "success",
                "content": mock_content,
                "content_length": len(mock_content),
                "embedding_dimension": 3072,
                "metadata": mock_metadata,
                "timestamp": datetime.utcnow().isoformat(),
            }

        return {
            "status": "success",
            "result": result,
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }
    except Exception as e:
        logger.error(f"Memory index test error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }


async def get_memory_stats(cli: AgentCLI) -> Dict[str, Any]:
    """
    Show memory usage statistics.

    Args:
        cli: The AgentCLI instance

    Returns:
        Dictionary with memory usage statistics
    """
    try:
        # Query for vector table statistics if available
        try:
            vector_stats_query = """
            SELECT
                count(*) as total_vectors,
                pg_size_pretty(pg_total_relation_size('agent_messages')) as table_size
            FROM
                agent_messages
            WHERE
                context_vector IS NOT NULL
            """
            vector_stats = await cli.db_client.execute(vector_stats_query)

            # Get total vectors by dimension
            dimension_query = """
            SELECT
                pgv_dim(context_vector) as dimension,
                count(*) as count
            FROM
                agent_messages
            WHERE
                context_vector IS NOT NULL
            GROUP BY
                pgv_dim(context_vector)
            """
            dimension_stats = await cli.db_client.execute(dimension_query)
        except Exception as e:
            logger.error(f"Error getting vector stats: {str(e)}")
            vector_stats = []
            dimension_stats = []

        # Get general database statistics for memory-related tables
        tables_query = """
        SELECT
            relname as table_name,
            n_live_tup as row_count,
            pg_size_pretty(pg_total_relation_size(oid)) as total_size
        FROM
            pg_stat_user_tables
        WHERE
            relname IN ('agent_messages', 'artifacts')
        ORDER BY
            n_live_tup DESC
        """
        table_stats = await cli.db_client.execute(tables_query)

        return {
            "status": "success",
            "vector_stats": (
                vector_stats[0]
                if vector_stats
                else {"total_vectors": 0, "table_size": "0 bytes"}
            ),
            "dimension_stats": dimension_stats,
            "table_stats": table_stats,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {str(e)}")
        return {"status": "error", "error": str(e)}


async def test_db_query(
    cli: AgentCLI,
    query: str,
    params: Optional[Dict[str, Any]] = None,
    explain: bool = False,
    timeout: Optional[int] = 10,
) -> Dict[str, Any]:
    """
    Test a database query execution.

    Args:
        cli: The AgentCLI instance
        query: SQL query to execute
        params: Optional parameters for the query
        explain: Whether to run EXPLAIN on the query
        timeout: Query timeout in seconds (None for no timeout)

    Returns:
        Dictionary with query results
    """
    try:
        start_time = datetime.utcnow()
        valid_query_prefixes = ["SELECT", "WITH", "EXPLAIN"]

        # Basic safety validation to prevent destructive queries
        if not any(
            query.strip().upper().startswith(prefix) for prefix in valid_query_prefixes
        ):
            return {
                "status": "error",
                "error": "Only SELECT, WITH, and EXPLAIN queries are allowed for testing",
            }

        # Apply EXPLAIN if requested
        if explain and not query.strip().upper().startswith("EXPLAIN"):
            query = f"EXPLAIN (ANALYZE, VERBOSE, BUFFERS) {query}"

        # Set timeout if specified
        timeout_text = ""
        if timeout is not None:
            timeout_text = f" SET LOCAL statement_timeout = {timeout * 1000}; "

        # Execute the query
        async with cli.db_client.engine.begin() as conn:
            if timeout is not None:
                await conn.execute(f"SET LOCAL statement_timeout = {timeout * 1000};")

            result = await conn.execute(query, params or {})

            # Process results
            if result.returns_rows:
                rows = result.fetchall()
                columns = result.keys()

                # Convert to list of dicts for JSON serialization
                results_list = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        # Handle special PostgreSQL types
                        value = row[i]
                        if hasattr(value, "isoformat"):
                            value = value.isoformat()
                        row_dict[col] = value
                    results_list.append(row_dict)

                return {
                    "status": "success",
                    "query": query,
                    "params": params,
                    "row_count": len(results_list),
                    "column_count": len(columns),
                    "columns": list(columns),
                    "rows": results_list[:100],  # Limit rows to avoid huge responses
                    "truncated": len(results_list) > 100,
                    "execution_time_ms": (
                        datetime.utcnow() - start_time
                    ).total_seconds()
                    * 1000,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                return {
                    "status": "success",
                    "query": query,
                    "params": params,
                    "message": "Query executed successfully (no rows returned)",
                    "execution_time_ms": (
                        datetime.utcnow() - start_time
                    ).total_seconds()
                    * 1000,
                    "timestamp": datetime.utcnow().isoformat(),
                }
    except Exception as e:
        logger.error(f"Error executing database query: {str(e)}")
        return {
            "status": "error",
            "query": query,
            "params": params,
            "error": str(e),
            "execution_time_ms": (datetime.utcnow() - start_time).total_seconds()
            * 1000,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def test_db_transaction_isolation(
    cli: AgentCLI,
    isolation_level: str = "READ COMMITTED",
    concurrency: int = 2,
    test_type: str = "read_phenomena",
) -> Dict[str, Any]:
    """
    Test database transaction isolation levels.

    Args:
        cli: The AgentCLI instance
        isolation_level: Transaction isolation level
        concurrency: Number of concurrent transactions to test
        test_type: Type of test to perform (read_phenomena, write_conflict)

    Returns:
        Dictionary with test results
    """
    try:
        start_time = datetime.utcnow()

        # Validate isolation level
        valid_isolation_levels = [
            "READ UNCOMMITTED",
            "READ COMMITTED",
            "REPEATABLE READ",
            "SERIALIZABLE",
        ]
        if isolation_level not in valid_isolation_levels:
            return {
                "status": "error",
                "error": f"Invalid isolation level: {isolation_level}. Valid levels: {', '.join(valid_isolation_levels)}",
            }

        # Validate test type
        valid_test_types = ["read_phenomena", "write_conflict", "deadlock"]
        if test_type not in valid_test_types:
            return {
                "status": "error",
                "error": f"Invalid test type: {test_type}. Valid types: {', '.join(valid_test_types)}",
            }

        # Set up temporary test table
        test_table_name = f"isolation_test_{uuid.uuid4().hex[:8]}"

        async with cli.db_client.engine.begin() as conn:
            # Create test table
            await conn.execute(
                f"""
            CREATE TEMPORARY TABLE {test_table_name} (
                id SERIAL PRIMARY KEY,
                value INTEGER,
                updated_at TIMESTAMP DEFAULT NOW()
            )
            """
            )

            # Insert initial data
            await conn.execute(
                f"""
            INSERT INTO {test_table_name} (value)
            SELECT generate_series FROM generate_series(1, 10)
            """
            )

        # Run different test types
        results = {
            "isolation_level": isolation_level,
            "test_type": test_type,
            "concurrent_transactions": concurrency,
            "test_table": test_table_name,
            "phenomena_detected": [],
            "execution_time_ms": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if test_type == "read_phenomena":
            # Test for isolation phenomena: dirty reads, non-repeatable reads, phantom reads
            results["testing_for"] = [
                "dirty_reads",
                "non_repeatable_reads",
                "phantom_reads",
            ]

            # Start first transaction
            async with cli.db_client.engine.begin() as conn1:
                await conn1.execute(
                    f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                )

                # Perform first read
                result1 = await conn1.execute(f"SELECT COUNT(*) FROM {test_table_name}")
                initial_count = result1.scalar()

                # Start concurrent transaction
                async with cli.db_client.engine.begin() as conn2:
                    await conn2.execute(
                        f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                    )

                    # Modify data in the second transaction
                    await conn2.execute(
                        f"INSERT INTO {test_table_name} (value) VALUES (99)"
                    )
                    await conn2.execute(
                        f"UPDATE {test_table_name} SET value = value * 2 WHERE id = 1"
                    )

                    # With lower isolation levels, we won't commit the second transaction yet
                    # to test for dirty reads
                    if isolation_level == "READ UNCOMMITTED":
                        # Check for dirty reads (can see uncommitted changes)
                        result1 = await conn1.execute(
                            f"SELECT COUNT(*) FROM {test_table_name}"
                        )
                        dirty_count = result1.scalar()

                        if dirty_count > initial_count:
                            results["phenomena_detected"].append("dirty_reads")

                    # Now commit the concurrent transaction
                    # (automatically committed by the context manager)

                # After the concurrent transaction is committed, check for non-repeatable reads and phantom reads
                result1 = await conn1.execute(f"SELECT COUNT(*) FROM {test_table_name}")
                final_count = result1.scalar()

                if final_count > initial_count and isolation_level in [
                    "READ COMMITTED",
                    "READ UNCOMMITTED",
                ]:
                    results["phenomena_detected"].append("phantom_reads")

                result1 = await conn1.execute(
                    f"SELECT value FROM {test_table_name} WHERE id = 1"
                )
                final_value = result1.scalar()

                result1 = await conn1.execute(
                    f"SELECT value FROM {test_table_name} WHERE id = 1"
                )
                initial_value = 1

                if final_value != initial_value and isolation_level in [
                    "READ COMMITTED",
                    "READ UNCOMMITTED",
                ]:
                    results["phenomena_detected"].append("non_repeatable_reads")

        elif test_type == "write_conflict":
            # Test for write conflicts and optimistic concurrency control
            results["testing_for"] = ["write_conflicts", "concurrency_control"]

            # Start multiple concurrent transactions
            tasks = []

            async def update_row(session_id, row_id):
                try:
                    async with cli.db_client.engine.begin() as conn:
                        await conn.execute(
                            f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                        )

                        # Read the current value
                        result = await conn.execute(
                            f"SELECT value FROM {test_table_name} WHERE id = {row_id}"
                        )
                        current_value = result.scalar()

                        # Simulate some processing time
                        await asyncio.sleep(0.1)

                        # Update with new value
                        new_value = current_value + session_id
                        await conn.execute(
                            f"UPDATE {test_table_name} SET value = {new_value}, updated_at = NOW() WHERE id = {row_id}"
                        )

                        return {
                            "session_id": session_id,
                            "row_id": row_id,
                            "old_value": current_value,
                            "new_value": new_value,
                            "status": "success",
                        }
                except Exception as e:
                    return {
                        "session_id": session_id,
                        "row_id": row_id,
                        "status": "error",
                        "error": str(e),
                    }

            # Execute concurrent updates
            for i in range(1, concurrency + 1):
                # Each transaction updates the same row
                tasks.append(update_row(i, 1))

            update_results = await asyncio.gather(*tasks)

            # Check for write conflicts
            successful_updates = [r for r in update_results if r["status"] == "success"]
            failed_updates = [r for r in update_results if r["status"] == "error"]

            results["update_operations"] = len(update_results)
            results["successful_updates"] = len(successful_updates)
            results["failed_updates"] = len(failed_updates)

            # Analyze end result
            async with cli.db_client.engine.begin() as conn:
                result = await conn.execute(
                    f"SELECT value FROM {test_table_name} WHERE id = 1"
                )
                final_value = result.scalar()
                results["final_value"] = final_value

                # In SERIALIZABLE, some transactions should fail or be serialized
                if isolation_level == "SERIALIZABLE" and concurrency > 1:
                    if len(failed_updates) == 0:
                        results["phenomena_detected"].append("serialization_anomaly")

        elif test_type == "deadlock":
            # Test for deadlock detection
            results["testing_for"] = ["deadlock_detection", "lock_wait_timeout"]

            async def transaction_a():
                try:
                    async with cli.db_client.engine.begin() as conn:
                        await conn.execute(
                            f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                        )

                        # Lock row 1
                        await conn.execute(
                            f"UPDATE {test_table_name} SET value = value WHERE id = 1"
                        )

                        # Simulate delay to ensure transaction interleaving
                        await asyncio.sleep(0.5)

                        # Try to lock row 2
                        await conn.execute(
                            f"UPDATE {test_table_name} SET value = value WHERE id = 2"
                        )
                        return {"transaction": "A", "status": "success"}
                except Exception as e:
                    return {"transaction": "A", "status": "error", "error": str(e)}

            async def transaction_b():
                try:
                    # Add a small delay to ensure transaction A runs first
                    await asyncio.sleep(0.1)

                    async with cli.db_client.engine.begin() as conn:
                        await conn.execute(
                            f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                        )

                        # Lock row 2
                        await conn.execute(
                            f"UPDATE {test_table_name} SET value = value WHERE id = 2"
                        )

                        # Simulate delay
                        await asyncio.sleep(0.5)

                        # Try to lock row 1, which should cause a deadlock
                        await conn.execute(
                            f"UPDATE {test_table_name} SET value = value WHERE id = 1"
                        )
                        return {"transaction": "B", "status": "success"}
                except Exception as e:
                    return {"transaction": "B", "status": "error", "error": str(e)}

            # Run both transactions concurrently
            tasks = [transaction_a(), transaction_b()]
            deadlock_results = await asyncio.gather(*tasks, return_exceptions=True)

            # At least one transaction should fail with a deadlock error
            error_transactions = [t for t in deadlock_results if t["status"] == "error"]

            results["transaction_results"] = deadlock_results
            results["deadlock_detected"] = any(
                "deadlock detected" in str(t.get("error", "")).lower()
                for t in error_transactions
            )

            if results["deadlock_detected"]:
                results["phenomena_detected"].append("deadlock_resolution")

        # Clean up test table
        async with cli.db_client.engine.begin() as conn:
            await conn.execute(f"DROP TABLE IF EXISTS {test_table_name}")

        results["execution_time_ms"] = (
            datetime.utcnow() - start_time
        ).total_seconds() * 1000
        results["status"] = "success"
        return results

    except Exception as e:
        logger.error(f"Error testing transaction isolation: {str(e)}")
        return {
            "status": "error",
            "isolation_level": isolation_level,
            "test_type": test_type,
            "error": str(e),
            "execution_time_ms": (datetime.utcnow() - start_time).total_seconds()
            * 1000,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def get_db_performance_stats(
    cli: AgentCLI,
    include_queries: bool = True,
    include_tables: bool = True,
    include_indexes: bool = True,
    min_calls: int = 5,
) -> Dict[str, Any]:
    """
    Get database performance statistics.

    Args:
        cli: The AgentCLI instance
        include_queries: Whether to include query statistics
        include_tables: Whether to include table statistics
        include_indexes: Whether to include index statistics
        min_calls: Minimum number of calls for query statistics

    Returns:
        Dictionary with database performance statistics
    """
    try:
        start_time = datetime.utcnow()
        results = {"status": "success", "timestamp": datetime.utcnow().isoformat()}

        async with cli.db_client.engine.begin() as conn:
            # Get database size
            size_query = """
            SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                   pg_database_size(current_database()) as db_size_bytes
            """
            result = await conn.execute(size_query)
            row = result.fetchone()
            results["database_size"] = {"formatted": row[0], "bytes": row[1]}

            # Get connection statistics
            connections_query = """
            SELECT 
                max_conn,
                used,
                res_for_super,
                max_conn - used - res_for_super AS available
            FROM
                (SELECT count(*) used FROM pg_stat_activity) t1,
                (SELECT setting::int res_for_super FROM pg_settings WHERE name='superuser_reserved_connections') t2,
                (SELECT setting::int max_conn FROM pg_settings WHERE name='max_connections') t3
            """
            result = await conn.execute(connections_query)
            row = result.fetchone()
            results["connections"] = {
                "max": row[0],
                "used": row[1],
                "reserved": row[2],
                "available": row[3],
            }

            # Get table statistics if requested
            if include_tables:
                tables_query = """
                SELECT
                    schemaname,
                    relname as table_name,
                    pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                    pg_size_pretty(pg_relation_size(relid)) as table_size,
                    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as index_size,
                    seq_scan,
                    idx_scan,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_tuples,
                    n_dead_tup as dead_tuples,
                    CASE WHEN seq_scan > 0 THEN 100 * idx_scan / seq_scan ELSE 0 END as index_use_ratio
                FROM
                    pg_stat_user_tables
                ORDER BY
                    pg_total_relation_size(relid) DESC
                LIMIT 20
                """
                result = await conn.execute(tables_query)
                results["tables"] = [dict(row) for row in result.fetchall()]

            # Get index statistics if requested
            if include_indexes:
                indexes_query = """
                SELECT
                    schemaname,
                    relname as table_name,
                    indexrelname as index_name,
                    pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch,
                    CASE WHEN idx_scan > 0 THEN idx_tup_read / idx_scan ELSE 0 END as avg_tuples_per_scan
                FROM
                    pg_stat_user_indexes
                WHERE
                    idx_scan > 0
                ORDER BY
                    idx_scan DESC, pg_relation_size(indexrelid) DESC
                LIMIT 20
                """
                result = await conn.execute(indexes_query)
                results["indexes"] = [dict(row) for row in result.fetchall()]

            # Get query statistics if requested
            if include_queries:
                # We need pg_stat_statements extension for this
                # First check if it's available
                extension_query = """
                SELECT count(*) FROM pg_extension WHERE extname = 'pg_stat_statements'
                """
                result = await conn.execute(extension_query)
                has_pg_stat_statements = result.scalar() > 0

                if has_pg_stat_statements:
                    queries_query = f"""
                    SELECT
                        substring(query, 1, 80) as query_sample,
                        calls,
                        total_time,
                        min_time,
                        max_time,
                        mean_time,
                        stddev_time,
                        rows
                    FROM
                        pg_stat_statements
                    WHERE
                        calls >= {min_calls}
                    ORDER BY
                        total_time DESC
                    LIMIT 20
                    """
                    result = await conn.execute(queries_query)
                    results["query_statistics"] = [
                        dict(row) for row in result.fetchall()
                    ]
                else:
                    results["query_statistics_available"] = False
                    results["query_statistics_error"] = (
                        "pg_stat_statements extension is not enabled"
                    )

            # Get lock information
            locks_query = """
            SELECT
                locktype,
                relation::regclass as relation,
                mode,
                count(*) as count
            FROM
                pg_locks
            WHERE
                locktype = 'relation'
            GROUP BY
                locktype, relation, mode
            ORDER BY
                count DESC
            LIMIT 10
            """
            result = await conn.execute(locks_query)
            results["locks"] = [dict(row) for row in result.fetchall()]

            # Get cache hit ratio
            cache_query = """
            SELECT 
                sum(heap_blks_read) as heap_read,
                sum(heap_blks_hit) as heap_hit,
                CASE WHEN sum(heap_blks_hit) + sum(heap_blks_read) > 0 
                    THEN round(100 * sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)), 2)
                    ELSE 0
                END as cache_hit_ratio
            FROM 
                pg_statio_user_tables
            """
            result = await conn.execute(cache_query)
            results["cache_statistics"] = dict(result.fetchone())

        results["execution_time_ms"] = (
            datetime.utcnow() - start_time
        ).total_seconds() * 1000
        return results

    except Exception as e:
        logger.error(f"Error getting database performance stats: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "execution_time_ms": (datetime.utcnow() - start_time).total_seconds()
            * 1000,
            "timestamp": datetime.utcnow().isoformat(),
        }


async def test_log_levels(
    cli: AgentCLI, message: str = "Log test message", include_context: bool = True
) -> Dict[str, Any]:
    """
    Test logging at all different levels.

    Args:
        cli: The AgentCLI instance
        message: Message to log at different levels
        include_context: Whether to include context data in the log entries

    Returns:
        Dictionary with log test results
    """
    try:
        start_time = datetime.utcnow()
        results = {
            "status": "success",
            "log_entries": [],
            "timestamp": start_time.isoformat(),
        }

        # Configure logging with a memory handler to capture the output
        test_logger = logging.getLogger("test_logger")
        test_logger.setLevel(logging.DEBUG)

        # Use a string IO as a buffer to capture log output
        from io import StringIO

        log_stream = StringIO()
        stream_handler = logging.StreamHandler(log_stream)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        stream_handler.setFormatter(formatter)
        test_logger.addHandler(stream_handler)

        # Sample context data to include if requested
        context = (
            {
                "agent_id": str(uuid.uuid4()),
                "session_id": str(uuid.uuid4()),
                "operation": "log_test",
                "component": "test_logger",
                "metadata": {"user": "test_user", "environment": "testing"},
            }
            if include_context
            else None
        )

        # Define the log levels to test
        log_levels = [
            ("DEBUG", logging.DEBUG, test_logger.debug),
            ("INFO", logging.INFO, test_logger.info),
            ("WARNING", logging.WARNING, test_logger.warning),
            ("ERROR", logging.ERROR, test_logger.error),
            ("CRITICAL", logging.CRITICAL, test_logger.critical),
        ]

        # Log a message at each level
        for level_name, level_num, log_method in log_levels:
            if include_context:
                log_method(f"{message} ({level_name})", extra={"context": context})
            else:
                log_method(f"{message} ({level_name})")

            # Add entry to results
            results["log_entries"].append(
                {
                    "level": level_name,
                    "level_num": level_num,
                    "message": f"{message} ({level_name})",
                    "context": context,
                    "time": datetime.utcnow().isoformat(),
                }
            )

        # Also log to the agent's logger system if available
        if hasattr(cli, "logger") and cli.logger:
            cli.logger.debug(f"{message} (DEBUG) - from CLI")
            cli.logger.info(f"{message} (INFO) - from CLI")
            cli.logger.warning(f"{message} (WARNING) - from CLI")
            cli.logger.error(f"{message} (ERROR) - from CLI")
            cli.logger.critical(f"{message} (CRITICAL) - from CLI")

            results["agent_logger_used"] = True

        # Capture the log output
        log_output = log_stream.getvalue()
        results["log_output"] = log_output

        # Clean up the test logger
        test_logger.removeHandler(stream_handler)
        stream_handler.close()
        log_stream.close()

        return results
    except Exception as e:
        logger.error(f"Error testing log levels: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def get_log_entries(
    cli: AgentCLI,
    level: str = "INFO",
    component: Optional[str] = None,
    agent_id: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 50,
    search_term: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve log entries based on various filters.

    Args:
        cli: The AgentCLI instance
        level: Minimum log level to retrieve
        component: Optional component name to filter
        agent_id: Optional agent ID to filter
        start_time: Optional start time for logs (ISO format)
        end_time: Optional end time for logs (ISO format)
        limit: Maximum number of log entries to retrieve
        search_term: Optional search term to filter messages

    Returns:
        Dictionary with filtered log entries
    """
    try:
        # Map log level strings to numeric values
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        # Validate log level
        if level not in level_map:
            return {
                "status": "error",
                "error": f"Invalid log level: {level}. Valid levels: {', '.join(level_map.keys())}",
            }

        numeric_level = level_map[level]

        # Parse time filters if provided
        start_datetime = datetime.fromisoformat(start_time) if start_time else None
        end_datetime = datetime.fromisoformat(end_time) if end_time else None

        # Mock implementation - in a real implementation, this would query a logging database
        # or read log files from disk. Here we just generate some sample data.

        # Generate sample log entries
        components = (
            ["agent", "protocol", "db", "llm", "memory", "cli"]
            if not component
            else [component]
        )
        levels = [l for l, n in level_map.items() if n >= numeric_level]

        # Generate random timestamps within the given range
        if not start_datetime:
            start_datetime = datetime.utcnow() - timedelta(hours=1)
        if not end_datetime:
            end_datetime = datetime.utcnow()

        time_span = (end_datetime - start_datetime).total_seconds()

        # Generate log entries
        log_entries = []
        for _ in range(
            min(limit * 2, 200)
        ):  # Generate more than we need so we can filter
            rand_component = random.choice(components)
            rand_level = random.choice(levels)
            rand_time_offset = random.uniform(0, time_span)
            entry_time = start_datetime + timedelta(seconds=rand_time_offset)

            # Create a sample log message
            message = f"Sample {rand_level} log entry for {rand_component}"

            # Add some context to make the logs more realistic
            if rand_level == "ERROR":
                message += ": Connection timeout"
            elif rand_level == "WARNING":
                message += ": Slow response detected"
            elif rand_level == "INFO":
                message += ": Operation completed successfully"
            elif rand_level == "DEBUG":
                message += ": Processing request data"
            elif rand_level == "CRITICAL":
                message += ": Service unavailable"

            # Include agent ID in the entry if specified
            entry_agent_id = agent_id or str(uuid.uuid4())

            entry = {
                "timestamp": entry_time.isoformat(),
                "level": rand_level,
                "component": rand_component,
                "message": message,
                "agent_id": entry_agent_id,
                "context": {
                    "session_id": str(uuid.uuid4()),
                    "operation_id": str(uuid.uuid4()),
                    "user": "test_user",
                },
            }

            log_entries.append(entry)

        # Apply search term filter if provided
        if search_term:
            log_entries = [
                entry
                for entry in log_entries
                if search_term.lower() in entry["message"].lower()
            ]

        # Sort by timestamp
        log_entries.sort(key=lambda e: e["timestamp"], reverse=True)

        # Apply limit
        log_entries = log_entries[:limit]

        return {
            "status": "success",
            "entries": log_entries,
            "count": len(log_entries),
            "filters": {
                "level": level,
                "component": component,
                "agent_id": agent_id,
                "start_time": start_time,
                "end_time": end_time,
                "search_term": search_term,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error retrieving log entries: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


async def configure_logging(
    cli: AgentCLI,
    default_level: str = "INFO",
    component_levels: Optional[Dict[str, str]] = None,
    log_to_file: bool = False,
    log_file: Optional[str] = None,
    log_format: str = "standard",
    max_file_size_mb: int = 10,
    backup_count: int = 5,
) -> Dict[str, Any]:
    """
    Configure the logging system.

    Args:
        cli: The AgentCLI instance
        default_level: Default logging level
        component_levels: Dictionary mapping component names to log levels
        log_to_file: Whether to log to a file
        log_file: Path to the log file
        log_format: Log format (standard, json, simple)
        max_file_size_mb: Maximum log file size in MB
        backup_count: Number of backup files to keep

    Returns:
        Dictionary with configuration results
    """
    try:
        # Map log level strings to numeric values
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }

        # Validate log level
        if default_level not in level_map:
            return {
                "status": "error",
                "error": f"Invalid log level: {default_level}. Valid levels: {', '.join(level_map.keys())}",
            }

        # Validate component levels if provided
        if component_levels:
            for component, level in component_levels.items():
                if level not in level_map:
                    return {
                        "status": "error",
                        "error": f"Invalid log level for {component}: {level}. Valid levels: {', '.join(level_map.keys())}",
                    }

        # Validate log format
        valid_formats = ["standard", "json", "simple"]
        if log_format not in valid_formats:
            return {
                "status": "error",
                "error": f"Invalid log format: {log_format}. Valid formats: {', '.join(valid_formats)}",
            }

        # Set root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(level_map[default_level])

        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level_map[default_level])

        # Set formatter based on format
        if log_format == "standard":
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        elif log_format == "json":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
            )
        else:  # simple
            formatter = logging.Formatter("%(levelname)s: %(message)s")

        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # Add file handler if requested
        if log_to_file:
            if not log_file:
                log_file = f"./agent_cli_{datetime.utcnow().strftime('%Y%m%d')}.log"

            # Use a rotating file handler
            from logging.handlers import RotatingFileHandler

            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count,
            )
            file_handler.setLevel(level_map[default_level])
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        # Set component-specific levels if provided
        if component_levels:
            for component, level in component_levels.items():
                component_logger = logging.getLogger(component)
                component_logger.setLevel(level_map[level])

        # Log a test message
        logger.info(
            f"Logging configuration updated: defaultLevel={default_level}, format={log_format}"
        )

        return {
            "status": "success",
            "configuration": {
                "default_level": default_level,
                "component_levels": component_levels or {},
                "log_to_file": log_to_file,
                "log_file": log_file if log_to_file else None,
                "log_format": log_format,
                "max_file_size_mb": max_file_size_mb if log_to_file else None,
                "backup_count": backup_count if log_to_file else None,
            },
            "handlers": {"console": True, "file": log_to_file},
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error configuring logging: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
