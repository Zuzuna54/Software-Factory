# Iteration 1: Core Agent SDK & Logging System (Part 2)

## Continued from Part 1

### Task 4: PostgreSQL Database Client

**What needs to be done:**
Implement a PostgreSQL database client that provides a clean interface for connecting to and querying the database.

**Why this task is necessary:**
A consistent database interface is essential for all agent operations and ensures proper connection management, transaction handling, and error reporting.

**Files to be created:**

- `agents/db/postgres.py` - PostgreSQL client implementation
- `agents/db/__init__.py` - Package initialization

**Implementation guidelines:**

```python
# agents/db/postgres.py

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import asyncpg
from asyncpg import Pool

class PostgresClient:
    """Asynchronous PostgreSQL client for the agent system."""

    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.environ.get(
            "DATABASE_URL",
            "postgresql://agent_user:agent_password@localhost:5432/agent_team"
        )
        self.pool: Optional[Pool] = None
        self.logger = logging.getLogger("agent.db.postgres")

    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        if self.pool is not None:
            self.logger.warning("Connection pool already initialized")
            return

        try:
            self.pool = await asyncpg.create_pool(
                dsn=self.connection_string,
                min_size=5,
                max_size=20
            )
            self.logger.info("PostgreSQL connection pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {str(e)}")
            raise

    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool is None:
            self.logger.warning("Connection pool not initialized")
            return

        await self.pool.close()
        self.pool = None
        self.logger.info("PostgreSQL connection pool closed")

    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return results."""
        if self.pool is None:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            self.logger.error(f"Query execution error: {str(e)}")
            self.logger.debug(f"Failed query: {query}")
            raise

    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Execute a query and return the first row as a dictionary."""
        if self.pool is None:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                if row:
                    return dict(row)
                return None
        except Exception as e:
            self.logger.error(f"Query fetch_one error: {str(e)}")
            self.logger.debug(f"Failed query: {query}")
            raise

    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dictionaries."""
        if self.pool is None:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            self.logger.error(f"Query fetch_all error: {str(e)}")
            self.logger.debug(f"Failed query: {query}")
            raise

    async def fetch_val(self, query: str, *args) -> Any:
        """Execute a query and return a single value."""
        if self.pool is None:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                return await conn.fetchval(query, *args)
        except Exception as e:
            self.logger.error(f"Query fetch_val error: {str(e)}")
            self.logger.debug(f"Failed query: {query}")
            raise

    async def transaction(self):
        """Start a transaction. Used as an async context manager."""
        if self.pool is None:
            await self.initialize()

        return self.pool.acquire()

    async def execute_many(self, query: str, args_list: List[Tuple]) -> None:
        """Execute a query many times with different arguments."""
        if self.pool is None:
            await self.initialize()

        try:
            async with self.pool.acquire() as conn:
                # Prepare the statement
                stmt = await conn.prepare(query)

                # Execute in a transaction
                async with conn.transaction():
                    for args in args_list:
                        await stmt.execute(*args)
        except Exception as e:
            self.logger.error(f"Query execute_many error: {str(e)}")
            self.logger.debug(f"Failed query: {query}")
            raise
```

### Task 5: CLI Tool for Agent Testing

**What needs to be done:**
Create a command-line interface tool for testing agent interactions and functionality.

**Why this task is necessary:**
A CLI tool allows developers to easily test agent behaviors without needing to build a complete application.

**Files to be created:**

- `agents/cli/agent_cli.py` - Command-line interface implementation
- `agents/cli/__init__.py` - Package initialization

**Implementation guidelines:**

```python
# agents/cli/agent_cli.py

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..base_agent import BaseAgent
from ..db.postgres import PostgresClient
from ..llm.anthropic_provider import AnthropicProvider
from ..memory.vector_memory import VectorMemory

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('agent_cli.log')
    ]
)

logger = logging.getLogger("agent.cli")

class AgentCLI:
    """Command-line interface for testing agent interactions."""

    def __init__(self):
        self.db_client = None
        self.llm_provider = None
        self.vector_memory = None
        self.agents: Dict[str, BaseAgent] = {}

    async def initialize(self) -> None:
        """Initialize the CLI and required services."""
        # Initialize database client
        self.db_client = PostgresClient()
        await self.db_client.initialize()

        # Initialize LLM provider
        self.llm_provider = AnthropicProvider()

        # Initialize vector memory
        self.vector_memory = VectorMemory(self.db_client)
        await self.vector_memory.initialize()

        logger.info("CLI services initialized")

    async def create_agent(
        self,
        agent_type: str,
        agent_name: str,
        capabilities: Dict[str, Any] = None
    ) -> str:
        """Create a new agent of the specified type."""
        # For now, we only support BaseAgent
        # In future iterations, we'll add specialized agent types
        agent = BaseAgent(
            agent_type=agent_type,
            agent_name=agent_name,
            llm_provider=self.llm_provider,
            db_client=self.db_client,
            vector_memory=self.vector_memory,
            capabilities=capabilities or {}
        )

        self.agents[agent.agent_id] = agent
        logger.info(f"Created agent: {agent_type} - {agent_name} (ID: {agent.agent_id})")
        return agent.agent_id

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents in the system."""
        if not self.db_client:
            logger.error("Database client not initialized")
            return []

        query = """
        SELECT agent_id, agent_type, agent_name, created_at, capabilities, active
        FROM agents
        ORDER BY created_at DESC
        """

        results = await self.db_client.fetch_all(query)

        agents = []
        for row in results:
            agents.append({
                "agent_id": row["agent_id"],
                "agent_type": row["agent_type"],
                "agent_name": row["agent_name"],
                "created_at": row["created_at"],
                "capabilities": json.loads(row["capabilities"]) if row["capabilities"] else {},
                "active": row["active"]
            })

        return agents

    async def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type: str = "INFORM"
    ) -> str:
        """Send a message from one agent to another."""
        if sender_id not in self.agents:
            logger.error(f"Sender agent {sender_id} not found")
            return ""

        message_id = await self.agents[sender_id].send_message(
            receiver_id=receiver_id,
            content=content,
            message_type=message_type
        )

        logger.info(f"Message sent: {sender_id} -> {receiver_id}")
        return message_id

    async def get_agent_messages(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent messages sent to the specified agent."""
        if agent_id not in self.agents:
            logger.error(f"Agent {agent_id} not found")
            return []

        messages = await self.agents[agent_id].receive_messages(limit=limit)
        return messages

    async def search_knowledge(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for knowledge related to the query."""
        if not self.llm_provider or not self.vector_memory:
            logger.error("LLM provider or vector memory not initialized")
            return []

        # Generate embedding for query
        embedding = await self.llm_provider.generate_embeddings(query)

        # Search for similar items (currently only messages)
        similar_ids = await self.vector_memory.search_similar(
            "agent_messages",
            embedding,
            limit=limit
        )

        if not similar_ids or not self.db_client:
            return []

        # Fetch the actual messages
        placeholders = ", ".join(f"${i+1}" for i in range(len(similar_ids)))
        query = f"""
        SELECT
            message_id, timestamp, sender_id, receiver_id,
            message_type, content
        FROM agent_messages
        WHERE message_id IN ({placeholders})
        """

        results = await self.db_client.fetch_all(query, *similar_ids)

        messages = []
        for row in results:
            messages.append({
                "message_id": row["message_id"],
                "timestamp": row["timestamp"],
                "sender_id": row["sender_id"],
                "receiver_id": row["receiver_id"],
                "message_type": row["message_type"],
                "content": row["content"]
            })

        return messages

    async def get_agent_activities(
        self,
        agent_id: str,
        activity_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent activities for the specified agent."""
        if not self.db_client:
            logger.error("Database client not initialized")
            return []

        conditions = ["agent_id = $1"]
        params = [agent_id]

        if activity_type:
            conditions.append("activity_type = $2")
            params.append(activity_type)

        query = f"""
        SELECT
            activity_id, timestamp, activity_type,
            description, thought_process
        FROM agent_activities
        WHERE {" AND ".join(conditions)}
        ORDER BY timestamp DESC
        LIMIT {limit}
        """

        results = await self.db_client.fetch_all(query, *params)

        activities = []
        for row in results:
            activities.append({
                "activity_id": row["activity_id"],
                "timestamp": row["timestamp"],
                "activity_type": row["activity_type"],
                "description": row["description"],
                "thought_process": row["thought_process"]
            })

        return activities

    async def close(self) -> None:
        """Close all connections and resources."""
        if self.db_client:
            await self.db_client.close()

        logger.info("CLI resources closed")

async def main():
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(description="Agent CLI Tool")
    parser.add_argument("--create-agent", action="store_true", help="Create a new agent")
    parser.add_argument("--list-agents", action="store_true", help="List all agents")
    parser.add_argument("--send-message", action="store_true", help="Send a message between agents")
    parser.add_argument("--get-messages", action="store_true", help="Get messages for an agent")
    parser.add_argument("--search", action="store_true", help="Search the knowledge base")
    parser.add_argument("--get-activities", action="store_true", help="Get agent activities")
    parser.add_argument("--agent-type", type=str, help="Type of agent to create")
    parser.add_argument("--agent-name", type=str, help="Name of agent to create")
    parser.add_argument("--sender-id", type=str, help="Sender agent ID")
    parser.add_argument("--receiver-id", type=str, help="Receiver agent ID")
    parser.add_argument("--agent-id", type=str, help="Agent ID")
    parser.add_argument("--message-type", type=str, default="INFORM", help="Message type")
    parser.add_argument("--content", type=str, help="Message content")
    parser.add_argument("--query", type=str, help="Search query")
    parser.add_argument("--limit", type=int, default=10, help="Result limit")
    parser.add_argument("--activity-type", type=str, help="Activity type filter")

    args = parser.parse_args()

    # Initialize CLI
    cli = AgentCLI()
    await cli.initialize()

    try:
        if args.create_agent:
            if not args.agent_type or not args.agent_name:
                print("Error: agent-type and agent-name are required for creating an agent")
                return

            agent_id = await cli.create_agent(args.agent_type, args.agent_name)
            print(f"Created agent with ID: {agent_id}")

        elif args.list_agents:
            agents = await cli.list_agents()
            print(json.dumps(agents, default=str, indent=2))

        elif args.send_message:
            if not args.sender_id or not args.receiver_id or not args.content:
                print("Error: sender-id, receiver-id, and content are required for sending a message")
                return

            message_id = await cli.send_message(
                args.sender_id,
                args.receiver_id,
                args.content,
                args.message_type
            )
            print(f"Message sent with ID: {message_id}")

        elif args.get_messages:
            if not args.agent_id:
                print("Error: agent-id is required for getting messages")
                return

            messages = await cli.get_agent_messages(args.agent_id, args.limit)
            print(json.dumps(messages, default=str, indent=2))

        elif args.search:
            if not args.query:
                print("Error: query is required for searching")
                return

            results = await cli.search_knowledge(args.query, args.limit)
            print(json.dumps(results, default=str, indent=2))

        elif args.get_activities:
            if not args.agent_id:
                print("Error: agent-id is required for getting activities")
                return

            activities = await cli.get_agent_activities(
                args.agent_id,
                args.activity_type,
                args.limit
            )
            print(json.dumps(activities, default=str, indent=2))

        else:
            print("No action specified. Use --help for usage information.")

    finally:
        await cli.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Task 6: Structured Agent Communication Protocol

**What needs to be done:**
Implement a structured communication protocol for agent-to-agent interactions using standardized message types and formats.

**Why this task is necessary:**
A structured communication protocol ensures consistent, semantically rich interactions between agents and enables efficient parsing and handling of requests and responses.

**Files to be created:**

- `agents/communication/protocol.py` - Communication protocol implementation
- `agents/communication/__init__.py` - Package initialization

**Implementation guidelines:**

```python
# agents/communication/protocol.py

import json
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
import uuid
from datetime import datetime

class MessageType(Enum):
    """Standardized message types for agent-to-agent communication."""
    REQUEST = "REQUEST"  # Ask another agent to do something
    INFORM = "INFORM"    # Provide information or results
    PROPOSE = "PROPOSE"  # Suggest a plan or design
    CONFIRM = "CONFIRM"  # Indicate agreement on a plan or output
    ALERT = "ALERT"      # Notify of a problem or important event
    BUG_REPORT = "BUG_REPORT"  # Report a specific bug
    TASK_ASSIGNMENT = "TASK_ASSIGNMENT"  # Assign a task to an agent
    TASK_UPDATE = "TASK_UPDATE"  # Update on task status
    REVIEW_REQUEST = "REVIEW_REQUEST"  # Request a review of work
    REVIEW_FEEDBACK = "REVIEW_FEEDBACK"  # Provide review feedback

@dataclass
class AgentMessage:
    """Structured message format for agent-to-agent communication."""
    sender: str
    receiver: str
    message_type: MessageType
    content: str
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    related_task: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary format for storage or transmission."""
        result = asdict(self)
        result["message_type"] = self.message_type.value
        result["created_at"] = self.created_at.isoformat()
        return result

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create AgentMessage from dictionary."""
        # Convert string message type to enum
        if isinstance(data.get("message_type"), str):
            data["message_type"] = MessageType(data["message_type"])

        # Convert string timestamp to datetime
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMessage':
        """Create AgentMessage from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class CommunicationProtocol:
    """Manager for agent-to-agent communication protocol."""

    def __init__(self):
        self.logger = logging.getLogger("agent.communication")

    def create_request(
        self,
        sender: str,
        receiver: str,
        content: str,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create a REQUEST message asking another agent to do something."""
        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.REQUEST,
            content=content,
            related_task=related_task,
            metadata=metadata or {}
        )

    def create_inform(
        self,
        sender: str,
        receiver: str,
        content: str,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create an INFORM message providing information or results."""
        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.INFORM,
            content=content,
            related_task=related_task,
            metadata=metadata or {}
        )

    def create_propose(
        self,
        sender: str,
        receiver: str,
        content: str,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create a PROPOSE message suggesting a plan or design."""
        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.PROPOSE,
            content=content,
            related_task=related_task,
            metadata=metadata or {}
        )

    def create_confirm(
        self,
        sender: str,
        receiver: str,
        content: str,
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create a CONFIRM message indicating agreement."""
        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.CONFIRM,
            content=content,
            related_task=related_task,
            metadata=metadata or {}
        )

    def create_alert(
        self,
        sender: str,
        receiver: str,
        content: str,
        severity: str = "MEDIUM",
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create an ALERT message notifying of a problem or important event."""
        alert_metadata = metadata or {}
        alert_metadata["severity"] = severity

        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.ALERT,
            content=content,
            related_task=related_task,
            metadata=alert_metadata
        )

    def create_bug_report(
        self,
        sender: str,
        receiver: str,
        content: str,
        test_failure: Optional[str] = None,
        severity: str = "MEDIUM",
        related_task: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentMessage:
        """Create a BUG_REPORT message with details about a bug."""
        bug_metadata = metadata or {}
        bug_metadata["severity"] = severity
        if test_failure:
            bug_metadata["test_failure"] = test_failure

        return AgentMessage(
            sender=sender,
            receiver=receiver,
            message_type=MessageType.BUG_REPORT,
            content=content,
            related_task=related_task,
            metadata=bug_metadata
        )

    def parse_message(self, message_data: Union[str, Dict[str, Any]]) -> AgentMessage:
        """Parse message data into an AgentMessage object."""
        if isinstance(message_data, str):
            return AgentMessage.from_json(message_data)
        else:
            return AgentMessage.from_dict(message_data)
```

### Task 7: Unit Testing Setup

**What needs to be done:**
Implement a comprehensive testing framework for all agent components.

**Why this task is necessary:**
Robust testing ensures that all components function correctly and catch regressions early.

**Files to be created:**

- `agents/tests/test_base_agent.py` - Tests for the base agent class
- `agents/tests/test_llm_provider.py` - Tests for LLM providers
- `agents/tests/test_vector_memory.py` - Tests for vector memory
- `agents/tests/test_postgres.py` - Tests for PostgreSQL client
- `agents/tests/conftest.py` - Pytest fixtures and configuration
- `agents/tests/communication.py` - Tests for Communication protocol

**Implementation guidelines:**

```python
# agents/tests/conftest.py

import asyncio
import os
import pytest
import uuid
from typing import Dict, Any, List, Generator, AsyncGenerator

from ..db.postgres import PostgresClient
from ..llm.anthropic_provider import AnthropicProvider
from ..memory.vector_memory import VectorMemory
from ..base_agent import BaseAgent

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def db_client() -> AsyncGenerator[PostgresClient, None]:
    """Create a database client for tests."""
    # Use a separate test database
    test_db_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://agent_user:agent_password@localhost:5432/agent_team_test"
    )

    client = PostgresClient(test_db_url)
    await client.initialize()

    # Clear test data before starting
    await client.execute("DELETE FROM agent_activities")
    await client.execute("DELETE FROM agent_messages")
    await client.execute("DELETE FROM vector_embeddings")
    await client.execute("DELETE FROM agents")

    yield client

    # Clean up
    await client.close()

@pytest.fixture(scope="session")
def llm_provider_mock() -> AnthropicProvider:
    """Create a mock LLM provider for tests."""
    # For tests, we'll use a mock provider that returns predetermined responses
    class MockLLMProvider:
        async def generate_completion(self, prompt, **kwargs):
            return f"Completion response for: {prompt[:20]}..."

        async def generate_chat_completion(self, messages, **kwargs):
            return f"Chat response for {len(messages)} messages"

        async def generate_embeddings(self, text):
            # Generate a deterministic but unique embedding based on the text
            # This is just for testing - real embeddings would be provided by the LLM API
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            hash_bytes = hash_obj.digest()

            # Create a 1536-dimensional vector from the hash
            # (repeating the hash bytes to reach the desired dimension)
            embedding = []
            for i in range(1536):
                embedding.append(float(hash_bytes[i % 16]) / 255.0)

            return embedding

        async def function_calling(self, messages, functions, **kwargs):
            return {
                "function_name": functions[0]["name"] if functions else None,
                "function_args": {"test_arg": "test_value"},
                "content": "Function calling response"
            }

    return MockLLMProvider()

@pytest.fixture(scope="session")
async def vector_memory(db_client) -> AsyncGenerator[VectorMemory, None]:
    """Create a vector memory instance for tests."""
    memory = VectorMemory(db_client)
    await memory.initialize()
    yield memory

@pytest.fixture
async def base_agent(db_client, llm_provider_mock, vector_memory) -> AsyncGenerator[BaseAgent, None]:
    """Create a base agent for testing."""
    agent = BaseAgent(
        agent_type="test",
        agent_name="TestAgent",
        llm_provider=llm_provider_mock,
        db_client=db_client,
        vector_memory=vector_memory
    )

    yield agent
```

## Post-Implementation Testing and Documentation

Before finalizing this phase, we need to complete several post-implementation tasks:

1. Create comprehensive documentation for the Agent SDK, including:

   - API references for all classes
   - Usage examples for common scenarios
   - Integration guides for new agent types

2. Perform thorough testing of all components:

   - Run the automated test suite for all modules
   - Conduct manual testing with the CLI tool
   - Verify database schema and connections

3. Create sample scripts for agent interactions to demonstrate functionality

4. Document any known limitations and future improvement plans

After completing these tasks, we'll have a robust foundation for building specialized agents in subsequent iterations.
