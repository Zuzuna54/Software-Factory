# agents/tests/conftest.py

import asyncio
import os
import pytest
import uuid
from typing import Dict, Any, List, Generator, AsyncGenerator
import logging

# Adjust relative paths if necessary
# from ..db.postgres import PostgresClient # Original failing import
from agents.db.postgres import PostgresClient  # Absolute import
from agents.llm.base import LLMProvider
from agents.llm.vertex_gemini_provider import (
    VertexGeminiProvider,
)  # Import the concrete class
from agents.memory.vector_memory import VectorMemory
from agents.base_agent import BaseAgent
from agents.communication.protocol import CommunicationProtocol

# Configure logging for tests (optional)
logging.basicConfig(level=logging.DEBUG)  # Show detailed logs during tests


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    # Use asyncio.new_event_loop() for thread safety if running tests in parallel
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_client() -> AsyncGenerator[PostgresClient, None]:
    """Create a database client connected to the TEST database."""
    # Ensure TEST_DATABASE_URL is set in the CI environment or locally
    test_db_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://agent_user:test_password@localhost:5432/agent_team_test",  # Match CI service password
    )
    if "agent_team_test" not in test_db_url:
        pytest.fail(
            "Potential risk: TEST_DATABASE_URL does not seem to point to a test database."
        )

    client = PostgresClient(test_db_url)
    try:
        await client.initialize()
        # Optional: Clear tables before session, although init.sql should handle it
        # For safety, explicit cleanup might be better
        async with client.transaction() as conn:
            await conn.execute("DELETE FROM agent_activities;")
            await conn.execute("DELETE FROM agent_messages;")
            await conn.execute("DELETE FROM vector_embeddings;")
            await conn.execute("DELETE FROM agents;")
            # Add other tables if needed
            logging.info("Cleared test database tables.")
        yield client
    except Exception as e:
        logging.error(f"Failed to initialize test DB client: {e}", exc_info=True)
        pytest.fail(f"Could not initialize test database: {e}")
    finally:
        if client.pool:
            await client.close()


@pytest.fixture(scope="session")
def llm_provider_mock() -> LLMProvider:  # Use base class type hint
    """Create a mock LLM provider for deterministic test responses."""

    class MockLLMProvider(LLMProvider):
        async def generate_completion(self, prompt, **kwargs):
            return f"Mock completion for: {prompt[:30]}..."

        async def generate_chat_completion(self, messages, **kwargs):
            last_msg = messages[-1]["content"] if messages else ""
            return f"Mock chat response to: {last_msg[:30]}..."

        async def generate_embeddings(self, text, task_type="RETRIEVAL_DOCUMENT"):
            # Simple deterministic embedding for testing
            import hashlib

            hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
            # Create a fixed-size list based on the hash
            embedding = [
                (hash_val + i) % 1000 / 1000.0 for i in range(1536)
            ]  # Ensure correct dimension
            return embedding

        async def function_calling(self, messages, functions, **kwargs):
            # Simulate calling the first function provided
            if functions:
                func_name = functions[0].get("name", "mock_function")
                args = {
                    param["name"]: f"mock_{param['type']}"
                    for param in functions[0]
                    .get("parameters", {})
                    .get("properties", {})
                    .values()
                }
                return {
                    "function_name": func_name,
                    "function_args": args,
                    "content": "",
                }
            else:
                return {
                    "content": "Mock response, no function called",
                    "function_name": None,
                    "function_args": None,
                }

    return MockLLMProvider()


@pytest.fixture(scope="function")  # Use function scope for isolation if state changes
async def vector_memory(db_client) -> AsyncGenerator[VectorMemory, None]:
    """Create a vector memory instance using the test DB client."""
    memory = VectorMemory(db_client)
    await memory.initialize()
    # Optional: Clear vector embeddings table before each test using this fixture
    # await db_client.execute("DELETE FROM vector_embeddings;")
    yield memory
    # Optional: Cleanup after test if needed


@pytest.fixture(scope="function")  # Function scope for test isolation
async def base_agent1(
    db_client: PostgresClient,
    llm_provider_mock: LLMProvider,
    vector_memory: VectorMemory,
) -> AsyncGenerator[BaseAgent, None]:
    """Create a base agent instance for testing."""
    agent = BaseAgent(
        agent_type="test",
        agent_name="TestAgent1",
        llm_provider=llm_provider_mock,
        db_client=db_client,
        vector_memory=vector_memory,
        comm_protocol=CommunicationProtocol(),  # Give it its own protocol instance
    )
    # Ensure agent registration completes before yielding
    # Find the asyncio task created in __init__ and await it, or add explicit register method
    # Quick workaround: short sleep
    await asyncio.sleep(0.1)
    yield agent
    # Cleanup: delete agent from DB?
    # await db_client.execute("DELETE FROM agents WHERE agent_id = $1", agent.agent_id)


@pytest.fixture(scope="function")
async def base_agent2(
    db_client: PostgresClient,
    llm_provider_mock: LLMProvider,
    vector_memory: VectorMemory,
) -> AsyncGenerator[BaseAgent, None]:
    """Create a second base agent instance for testing interactions."""
    agent = BaseAgent(
        agent_type="test",
        agent_name="TestAgent2",
        llm_provider=llm_provider_mock,
        db_client=db_client,
        vector_memory=vector_memory,
        comm_protocol=CommunicationProtocol(),
    )
    await asyncio.sleep(0.1)
    yield agent
    # Cleanup: delete agent from DB?
    # await db_client.execute("DELETE FROM agents WHERE agent_id = $1", agent.agent_id)


@pytest.fixture
def comm_protocol() -> CommunicationProtocol:
    """Provides a CommunicationProtocol instance."""
    return CommunicationProtocol()
