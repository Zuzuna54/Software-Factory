# CLI Refactoring Plan: Database-First Operations

## Executive Summary

This document outlines a comprehensive plan to refactor the Software Factory CLI tool from an in-memory implementation to a fully database-integrated solution. The current implementation stores agent and conversation data in memory, which limits testing capabilities and doesn't properly exercise the database functionality. The refactored CLI will leverage the existing PostgreSQL client and database models to ensure all operations are persisted, providing a more realistic testing environment for the autonomous multi-agent system.

## Current State Analysis

### Database Implementation

The system uses PostgreSQL with the following key components:

1. **Database Client:**

   - `PostgresClient` in `agents/db/postgres.py` provides a robust async client with connection pooling, transaction management, and comprehensive error handling.
   - Functions include: `execute`, `execute_many`, `fetch_one`, `fetch_value`, `execute_in_transaction`, and model operations like `get_by_id`, `get_all`, `create`, `update`, `delete`, and `count`.

2. **Database Models:**

   - Core models in `infra/db/models/core.py` include: `Agent`, `AgentMessage`, `AgentActivity`, `Artifact`, `Task`, `Meeting`, and `MeetingConversation`.
   - Artifact-specific models in `infra/db/models/artifacts.py` include various specialized artifact types.
   - All models extend the `Base` class from SQLAlchemy ORM.

3. **Communication Protocol:**
   - The `Protocol` class in `agents/communication/protocol.py` already performs database operations for message persistence.
   - Register agent functionality attempts to write to the database but has UUID format issues.

### CLI Implementation

1. **Core Structure:**

   - `AgentCLI` class in `cli_core.py` maintains in-memory dictionaries for agents and conversations.
   - Database client is initialized but primarily used for the Protocol instance.

2. **Agent Operations:**

   - `create_agent` in `cli_agent_ops.py` stores agent data in memory.
   - `register_agent` in `Protocol` class attempts database persistence but has UUID format issues.

3. **Conversation Management:**

   - Conversations are stored in memory with no database persistence.

4. **Message Operations:**

   - Messages are persisted to the database through the Protocol.

5. **Component Testing:**
   - New `cli_component_ops.py` module provides functions for testing specific components.
   - These operations do interact with the database directly.

## Deficiencies in Current Implementation

1. **In-Memory Storage:**

   - Agent and conversation data is not persisted between CLI commands.
   - State is reset when the CLI is restarted, preventing long-running tests.

2. **Inconsistent Database Usage:**

   - Some operations (messages) use the database while others (agents, conversations) don't.
   - UUID format issues when trying to register agents with non-UUID format IDs.

3. **Limited Testing Capabilities:**

   - Cannot effectively test database client across multiple sessions.
   - Impossible to validate database state between CLI commands.

4. **Incomplete Component Testing:**
   - Missing database commands for comprehensive database testing.
   - Incomplete logging and agent operations.

## Refactoring Plan

### Phase 1: Database-First Agent Management

1. **Update `cli_core.py`:**

   - Modify `AgentCLI` to remove in-memory agent storage
   - Add database session management for direct model operations

2. **Refactor `cli_agent_ops.py`:**

   - Replace in-memory agent storage with database operations
   - Implement the following functions with database persistence:
     - `create_agent`: Create agent record in database using proper UUID format
     - `list_agents`: Query agents table for all agents
     - `get_agent`: Query agents table by ID
     - `update_agent`: Update agent record in database
     - `delete_agent`: Mark agent as inactive in database

3. **Fix UUID handling:**
   - Add utility functions to validate and convert between string IDs and UUID objects
   - Ensure all IDs passed to database operations are valid UUIDs

### Phase 2: Database-First Conversation Management

1. **Create Database Model:**

   - Add `Conversation` model to store conversation metadata

2. **Refactor `cli_conversation_ops.py`:**
   - Replace in-memory conversation storage with database operations
   - Implement functions with database persistence:
     - `create_conversation`: Create conversation record in database
     - `list_conversations`: Query conversations table
     - `select_conversation`: Fetch conversation from database (store current ID in CLI instance)
     - `get_conversation_summary`: Query conversation by ID
     - `get_conversation_messages`: Query messages associated with conversation

### Phase 3: Enhanced Component Testing Commands

1. **Expand Database Testing Commands:**

   - Add `db pool-status`: Show connection pool statistics
   - Add `db metrics`: Show query performance metrics
   - Add `db tables`: List all tables with record counts

2. **Expand Agent Testing Commands:**

   - Add `agent create-base`: Create a BaseAgent instance
   - Add `agent think`: Test agent thinking capability
   - Add `agent capabilities`: Set/get agent capabilities
   - Add `agent status`: Change agent status
   - Add `agent error-sim`: Simulate error conditions

3. **Add LLM Testing Commands:**

   - Add `llm chat-completion`: Test chat completion generation
   - Add `llm function-call`: Test function calling
   - Add `llm models`: List available models

4. **Expand Memory Testing Commands:**

   - Add `memory context`: Test context window management
   - Add `memory index`: Test memory indexing operations
   - Add `memory stats`: Show memory usage statistics

5. **Expand Conversation Testing Commands:**

   - Add `conversation visualize`: Generate conversation visualization
   - Add `conversation inject`: Inject a message into a conversation
   - Add `conversation simulate-failure`: Test error handling
   - Add `conversation export`: Export conversation to file

6. **Add Logging Commands:**
   - Add `log list`: List recent log entries
   - Add `log search`: Search for specific log entries
   - Add `log verify`: Verify logging for a specific operation
   - Add `log metrics`: Show logging metrics
   - Add `log export`: Export logs to file

## Implementation Details

### 1. Database-First Agent Management

```python
# cli_core.py updates

class AgentCLI:
    def __init__(self, db_url: Optional[str] = None):
        # Get database URL from environment if not provided
        self.db_url = db_url or os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory",
        )

        # Current conversation ID
        self.current_conversation_id: Optional[str] = None

        # Protocol instance (initialized on first use)
        self._protocol: Optional[Protocol] = None

        # Database client (initialized on first use)
        self._db_client = None

    # Remove self.agents and self.conversations dictionaries
    # Rest of the class remains the same
```

```python
# cli_agent_ops.py updates

async def create_agent(
    cli: AgentCLI,
    agent_id: Optional[str] = None,
    agent_type: str = "test",
    agent_name: str = "Test Agent",
    agent_role: str = "test",
    capabilities: Optional[List[str]] = None,
    **kwargs
) -> str:
    """Create a new agent in the database."""
    # Generate UUID if not provided
    agent_id_uuid = uuid.uuid4() if agent_id is None else uuid.UUID(agent_id)

    # Convert capabilities to JSONB format
    capabilities_json = {
        "capabilities": capabilities or []
    }

    # Create agent record
    try:
        from infra.db.models import Agent

        # Create Agent instance
        agent = Agent(
            agent_id=agent_id_uuid,
            agent_type=agent_type,
            agent_name=agent_name,
            agent_role=agent_role,
            capabilities=capabilities_json,
            status="active",
            system_prompt=f"You are {agent_name}, a {agent_type} agent.",
            extra_data=kwargs.get("extra_data", {})
        )

        # Store in database
        async with cli.db_client.transaction() as session:
            session.add(agent)

        # Register with protocol
        cli.protocol.register_agent(str(agent_id_uuid), agent_type, agent_name)

        logger.info(f"Created agent: {agent_id_uuid}")
        return str(agent_id_uuid)
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise

async def list_agents(cli: AgentCLI, status: str = "active") -> List[Dict[str, Any]]:
    """List all agents from the database."""
    try:
        from infra.db.models import Agent

        # Query database for agents
        agents = await cli.db_client.get_all(Agent, status=status)

        # Convert to dictionary format
        return [
            {
                "id": str(agent.agent_id),
                "name": agent.agent_name,
                "type": agent.agent_type,
                "role": agent.agent_role,
                "status": agent.status,
                "created_at": agent.created_at.isoformat() if agent.created_at else None
            }
            for agent in agents
        ]
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return []

async def get_agent(cli: AgentCLI, agent_id: str) -> Optional[Dict[str, Any]]:
    """Get agent details from the database."""
    try:
        from infra.db.models import Agent

        # Convert to UUID
        agent_id_uuid = uuid.UUID(agent_id)

        # Query database for agent
        agent = await cli.db_client.get_by_id(Agent, agent_id_uuid)

        if not agent:
            return None

        # Convert to dictionary
        return {
            "id": str(agent.agent_id),
            "name": agent.agent_name,
            "type": agent.agent_type,
            "role": agent.agent_role,
            "capabilities": agent.capabilities,
            "status": agent.status,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "system_prompt": agent.system_prompt,
            "extra_data": agent.extra_data
        }
    except Exception as e:
        logger.error(f"Error getting agent: {str(e)}")
        return None
```

### 2. Database-First Conversation Management

```python
# First add Conversation model to infra/db/models/core.py

class Conversation(Base):
    """Model for tracking conversations between agents"""

    __tablename__ = "conversations"
    __mapper_args__ = {"exclude_properties": ["id"]}

    conversation_id = Column(UUID, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    topic = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="active")
    participant_ids = Column(ARRAY(UUID), nullable=True)
    metadata = Column(JSONB, nullable=True)

    # Relationships through back-populates
    messages = relationship("AgentMessage", back_populates="conversation")
```

```python
# cli_conversation_ops.py updates

async def create_conversation(
    cli: AgentCLI,
    conversation_id: Optional[str] = None,
    topic: Optional[str] = None,
    **kwargs
) -> str:
    """Create a new conversation in the database."""
    # Generate UUID if not provided
    conv_id_uuid = uuid.uuid4() if conversation_id is None else uuid.UUID(conversation_id)

    # Create conversation record
    try:
        from infra.db.models import Conversation

        # Create Conversation instance
        conversation = Conversation(
            conversation_id=conv_id_uuid,
            topic=topic or "Untitled Conversation",
            status="active",
            metadata=kwargs.get("metadata", {})
        )

        # Store in database
        async with cli.db_client.transaction() as session:
            session.add(conversation)

        # Set as current conversation
        cli.current_conversation_id = str(conv_id_uuid)

        logger.info(f"Created conversation: {conv_id_uuid}")
        return str(conv_id_uuid)
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise

async def list_conversations(cli: AgentCLI, status: str = "active") -> List[Dict[str, Any]]:
    """List all conversations from the database."""
    try:
        from infra.db.models import Conversation

        # Query database for conversations
        conversations = await cli.db_client.get_all(Conversation, status=status)

        # Convert to dictionary format
        return [
            {
                "id": str(conv.conversation_id),
                "topic": conv.topic,
                "status": conv.status,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "is_current": str(conv.conversation_id) == cli.current_conversation_id
            }
            for conv in conversations
        ]
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        return []
```

### 3. Component Testing Implementation

```python
# cli_component_ops.py updates for db commands

async def db_pool_status(cli: AgentCLI) -> Dict[str, Any]:
    """Get database connection pool status."""
    try:
        stats = await cli.db_client.get_connection_stats()
        return {
            "pool_size": stats["pool_size"],
            "checked_out": stats["checked_out"],
            "overflow": stats["overflow"],
            "checkedin": stats["checkedin"],
            "status": "operational" if await cli.db_client.check_connection() else "error"
        }
    except Exception as e:
        logger.error(f"Error getting pool status: {str(e)}")
        return {"status": "error", "error": str(e)}

async def db_tables(cli: AgentCLI) -> Dict[str, Any]:
    """List all tables in the database with record counts."""
    try:
        # Query for all tables
        tables_query = """
        SELECT
            table_name
        FROM
            information_schema.tables
        WHERE
            table_schema = 'public'
        ORDER BY
            table_name
        """
        tables = await cli.db_client.execute(tables_query)

        # Get record count for each table
        results = {}
        for table in tables:
            table_name = table["table_name"]
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count = await cli.db_client.fetch_value(count_query, column="count")
            results[table_name] = count

        return {
            "tables": results,
            "total_tables": len(results),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        return {"status": "error", "error": str(e)}
```

## Database Schema Updates

1. **Add Conversation Model Migration:**

   - Create a new migration script to add the Conversation table
   - Add foreign key from AgentMessage to Conversation

2. **Update Agent Message Model:**
   - Add conversation_id field to link messages to conversations

## Testing and Validation

1. **Test Script Creation:**

   - Create comprehensive test scripts for all refactored functionality
   - Test database persistence across multiple CLI commands

2. **Error Handling:**

   - Test error scenarios (database unavailable, constraint violations)
   - Ensure proper user feedback for errors

3. **Performance Testing:**
   - Test with large datasets to ensure performance
   - Optimize queries for common operations

## Implementation Timeline

1. **Phase 1 (Database-First Agent Management):** 2 days
2. **Phase 2 (Database-First Conversation Management):** 2 days
3. **Phase 3 (Enhanced Component Testing Commands):** 3 days
4. **Phase 4 (Database Schema Validation):** 2 days
5. **Testing and Documentation:** 2 days

Total estimated time: 11 development days

## Conclusion

Refactoring the CLI to be database-first will significantly enhance its utility for testing the autonomous multi-agent system. By ensuring all operations are persisted to the database, we can more effectively test the system's functionality, validate database operations, and ensure the robustness of the communication protocol. This refactoring will transform the CLI from a simple command tool into a comprehensive system validation framework.
