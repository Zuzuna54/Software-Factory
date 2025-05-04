# Iteration 1: Core Agent SDK & Logging System

## Overview

This phase establishes the foundational software components for our autonomous AI development team. We'll implement the core agent framework, communication protocols, and logging system that will enable all subsequent agent interactions.

## Why This Phase Matters

The agent SDK created during this phase will serve as the foundation for all specialized agents in our system. By implementing robust logging from the start, we ensure complete transparency into agent reasoning and activities. The vector memory system will enable semantic search capabilities critical for context retrieval and knowledge sharing among agents.

## Expected Outcomes

After completing this phase, we will have:

1. A functional `BaseAgent` class that all specialized agents will inherit from
2. LLM integration with a selected provider (Google Vertex AI with Gemini models)
3. A comprehensive logging system recording all agent activities to PostgreSQL
4. Vector memory implementation for semantic search capabilities
5. A basic CLI for testing agent interactions

## Implementation Tasks

### Task 1: LLM Provider Selection and Integration

**What needs to be done:**
Select and integrate with an LLM provider (Google Vertex AI with Gemini models) that will power our agent system.

**Why this task is necessary:**
LLMs are the core reasoning engine for all agents. Properly abstracting this integration allows us to switch providers if needed and ensures consistent interaction patterns across the system.

**Files to be created:**

- `agents/llm/base.py` - Abstract base class for LLM providers
- `agents/llm/vertex_gemini_provider.py` - Google Vertex AI Gemini implementation
- `agents/llm/__init__.py` - Package initialization

**Implementation guidelines:**

```python
# agents/llm/base.py

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Generate a text completion for the given prompt."""
        pass

    @abstractmethod
    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Generate a chat completion for the given messages."""
        pass

    @abstractmethod
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for the given text."""
        pass

    @abstractmethod
    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Call functions based on LLM reasoning."""
        pass
```

```python
# agents/llm/vertex_gemini_provider.py

import os
import json
from typing import Dict, List, Any, Optional
import aiohttp
from .base import LLMProvider
from google.cloud import aiplatform
from google.oauth2 import service_account

class VertexGeminiProvider(LLMProvider):
    """Google Vertex AI Gemini LLM provider."""

    def __init__(self, model: str = "gemini-2.5-pro", project: Optional[str] = None, location: Optional[str] = "us-central1"):
        self.project = project or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location
        if not self.project:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable or project parameter is required")

        # Initialize Vertex AI
        aiplatform.init(project=self.project, location=self.location)

        # Load the model
        self.model_instance = aiplatform.GenerativeModel(model)
        self.embedding_model = aiplatform.language_models.TextEmbeddingModel.from_pretrained("text-embedding-004") # Use a standard embedding model
        self.model_name = model


    async def generate_completion(
        self,
        prompt: str,
        max_tokens: int = 8192, # Gemini 2.5 Pro has a large context window
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Generate a text completion using Vertex AI Gemini."""

        # Gemini API uses a different format, often combining system + prompt
        full_prompt = f"{system_message}\n\n{prompt}" if system_message else prompt

        response = await self.model_instance.generate_content_async(
            full_prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        return response.text

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 8192,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> str:
        """Generate a chat completion using Vertex AI Gemini."""

        # Convert messages to Vertex AI format
        # Note: Vertex AI format might differ slightly, check documentation
        history = []
        for msg in messages:
            history.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})

        chat = self.model_instance.start_chat(history=history)

        response = await chat.send_message_async(
            messages[-1]["content"], # Assuming last message is user query
             generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )

        return response.text

    async def generate_embeddings(self, text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
        """Generate embeddings using Vertex AI Text Embedding Model."""

        embeddings = await self.embedding_model.get_embeddings_async([{ "content": text, "task_type": task_type }])
        return embeddings[0].values

    async def function_calling(
        self,
        messages: List[Dict[str, str]],
        functions: List[Dict[str, Any]],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """Call functions based on Gemini reasoning."""

        # Convert messages to Vertex AI format
        history = []
        for msg in messages:
            history.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})

        # Convert function definitions to Vertex AI Tool format
        tools = [aiplatform.gapic.Tool(function_declarations=functions)]

        chat = self.model_instance.start_chat(history=history)

        # Send message with tools
        response = await chat.send_message_async(
            messages[-1]["content"],
            tools=tools,
             generation_config={
                "temperature": temperature,
            }
        )

        # Check for function call in response
        function_call = response.candidates[0].content.parts[0].function_call
        if function_call:
             return {
                "function_name": function_call.name,
                "function_args": type(function_call).to_dict(function_call.args),
                "content": "" # Usually no text content when function is called
            }
        else:
            return {"content": response.text, "function_name": None, "function_args": None}
```

### Task 2: Base Agent Class Implementation

**What needs to be done:**
Create a foundational `BaseAgent` class that will serve as the parent class for all specialized agent types.

**Why this task is necessary:**
A well-designed base agent class ensures consistent behavior across all agent types and reduces code duplication by centralizing common functionality.

**Files to be created:**

- `agents/base_agent.py` - Base agent class definition
- `agents/__init__.py` - Package initialization

**Implementation guidelines:**

```python
# agents/base_agent.py

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from .llm.base import LLMProvider
from .memory.vector_memory import VectorMemory
from .db.postgres import PostgresClient

class BaseAgent:
    """Base class for all agent types in the system."""

    def __init__(
        self,
        agent_id: Optional[str] = None,
        agent_type: str = "base",
        agent_name: str = "BaseAgent",
        llm_provider: LLMProvider = None,
        db_client: PostgresClient = None,
        vector_memory: VectorMemory = None,
        capabilities: Dict[str, Any] = None
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.llm_provider = llm_provider
        self.db_client = db_client
        self.vector_memory = vector_memory
        self.capabilities = capabilities or {}
        self.logger = logging.getLogger(f"agent.{agent_type}.{self.agent_id}")

        # Ensure the agent is registered in the database
        asyncio.create_task(self._register_agent())

    async def _register_agent(self) -> None:
        """Register this agent in the database if it doesn't exist."""
        if not self.db_client:
            self.logger.warning("No database client provided, skipping agent registration")
            return

        # Check if agent already exists
        query = """
        SELECT agent_id FROM agents WHERE agent_id = $1
        """
        result = await self.db_client.fetch_one(query, self.agent_id)

        if not result:
            # Agent doesn't exist, create it
            query = """
            INSERT INTO agents (agent_id, agent_type, agent_name, capabilities)
            VALUES ($1, $2, $3, $4)
            """
            await self.db_client.execute(
                query,
                self.agent_id,
                self.agent_type,
                self.agent_name,
                json.dumps(self.capabilities)
            )
            self.logger.info(f"Agent {self.agent_id} ({self.agent_name}) registered in database")

    async def send_message(
        self,
        receiver_id: str,
        content: str,
        message_type: str = "INFORM",
        related_task_id: Optional[str] = None,
        metadata: Dict[str, Any] = None,
        parent_message_id: Optional[str] = None
    ) -> str:
        """Send a message to another agent and log it to the database."""
        if not self.db_client:
            self.logger.warning("No database client provided, message will not be stored")
            return "message-not-stored"

        message_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # Store message in database
        query = """
        INSERT INTO agent_messages (
            message_id, timestamp, sender_id, receiver_id,
            message_type, content, related_task_id,
            metadata, parent_message_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING message_id
        """

        await self.db_client.execute(
            query,
            message_id,
            timestamp,
            self.agent_id,
            receiver_id,
            message_type,
            content,
            related_task_id,
            json.dumps(metadata or {}),
            parent_message_id
        )

        # Store vector embedding for semantic search
        if self.vector_memory and self.llm_provider:
            embedding = await self.llm_provider.generate_embeddings(content)
            await self.vector_memory.store_embedding(
                "agent_messages",
                message_id,
                embedding
            )

        # Log activity
        await self.log_activity(
            activity_type="MessageSent",
            description=f"Sent {message_type} message to {receiver_id}",
            related_files=[],
            input_data={"receiver_id": receiver_id, "type": message_type},
            output_data={"message_id": message_id, "content_preview": content[:100]}
        )

        self.logger.info(f"Message sent: {message_id} to {receiver_id} (type: {message_type})")
        return message_id

    async def receive_messages(
        self,
        since_timestamp: Optional[datetime] = None,
        message_type: Optional[str] = None,
        sender_id: Optional[str] = None,
        related_task_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve messages sent to this agent with optional filters."""
        if not self.db_client:
            self.logger.warning("No database client provided, cannot retrieve messages")
            return []

        conditions = ["receiver_id = $1"]
        params = [self.agent_id]
        param_idx = 2

        if since_timestamp:
            conditions.append(f"timestamp > ${param_idx}")
            params.append(since_timestamp)
            param_idx += 1

        if message_type:
            conditions.append(f"message_type = ${param_idx}")
            params.append(message_type)
            param_idx += 1

        if sender_id:
            conditions.append(f"sender_id = ${param_idx}")
            params.append(sender_id)
            param_idx += 1

        if related_task_id:
            conditions.append(f"related_task_id = ${param_idx}")
            params.append(related_task_id)
            param_idx += 1

        query = f"""
        SELECT
            message_id, timestamp, sender_id, message_type,
            content, related_task_id, metadata, parent_message_id
        FROM agent_messages
        WHERE {" AND ".join(conditions)}
        ORDER BY timestamp DESC
        LIMIT {limit}
        """

        results = await self.db_client.fetch_all(query, *params)

        messages = []
        for row in results:
            messages.append({
                "message_id": row["message_id"],
                "timestamp": row["timestamp"],
                "sender_id": row["sender_id"],
                "message_type": row["message_type"],
                "content": row["content"],
                "related_task_id": row["related_task_id"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "parent_message_id": row["parent_message_id"]
            })

        await self.log_activity(
            activity_type="MessagesRetrieved",
            description=f"Retrieved {len(messages)} messages",
            related_files=[],
            input_data={"filters": {
                "since": str(since_timestamp) if since_timestamp else None,
                "type": message_type,
                "sender": sender_id,
                "task": related_task_id
            }},
            output_data={"count": len(messages)}
        )

        return messages

    async def search_messages(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for messages semantically similar to the query text."""
        if not self.vector_memory or not self.llm_provider or not self.db_client:
            self.logger.warning("Vector memory, LLM provider, or DB client not available")
            return []

        # Generate embedding for query
        query_embedding = await self.llm_provider.generate_embeddings(query_text)

        # Search for similar messages
        similar_ids = await self.vector_memory.search_similar(
            "agent_messages",
            query_embedding,
            limit=limit
        )

        if not similar_ids:
            return []

        # Fetch the actual messages
        placeholders = ", ".join(f"${i+1}" for i in range(len(similar_ids)))
        query = f"""
        SELECT
            message_id, timestamp, sender_id, receiver_id,
            message_type, content, related_task_id, metadata
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
                "content": row["content"],
                "related_task_id": row["related_task_id"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
            })

        await self.log_activity(
            activity_type="MessageSearch",
            description=f"Searched messages similar to: {query_text[:100]}",
            related_files=[],
            input_data={"query": query_text},
            output_data={"result_count": len(messages)}
        )

        return messages

    async def log_activity(
        self,
        activity_type: str,
        description: str,
        thought_process: Optional[str] = None,
        related_files: List[str] = None,
        input_data: Dict[str, Any] = None,
        output_data: Dict[str, Any] = None,
        decisions_made: Dict[str, Any] = None,
        execution_time_ms: Optional[int] = None
    ) -> str:
        """Log an activity performed by this agent to the database."""
        if not self.db_client:
            self.logger.warning("No database client provided, activity will not be logged")
            return "activity-not-logged"

        activity_id = str(uuid.uuid4())
        timestamp = datetime.now()

        query = """
        INSERT INTO agent_activities (
            activity_id, agent_id, timestamp, activity_type,
            description, thought_process, related_files,
            input_data, output_data, decisions_made, execution_time_ms
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        RETURNING activity_id
        """

        await self.db_client.execute(
            query,
            activity_id,
            self.agent_id,
            timestamp,
            activity_type,
            description,
            thought_process,
            related_files or [],
            json.dumps(input_data or {}),
            json.dumps(output_data or {}),
            json.dumps(decisions_made or {}),
            execution_time_ms
        )

        self.logger.info(f"Activity logged: {activity_id} ({activity_type})")
        return activity_id

    async def think(self, prompt: str, system_message: Optional[str] = None) -> Tuple[str, str]:
        """Perform internal reasoning using the LLM provider and log the thought process."""
        if not self.llm_provider:
            error_msg = "No LLM provider available for thinking"
            self.logger.error(error_msg)
            return "", error_msg

        start_time = datetime.now()

        try:
            thought = await self.llm_provider.generate_completion(
                prompt,
                system_message=system_message
            )

            execution_time = (datetime.now() - start_time).total_milliseconds()

            # Log the thinking activity
            await self.log_activity(
                activity_type="Thinking",
                description=f"Internal reasoning on: {prompt[:100]}...",
                thought_process=thought,
                input_data={"prompt": prompt},
                output_data={"thought": thought[:100] + "..."},
                execution_time_ms=execution_time
            )

            return thought, ""
        except Exception as e:
            error_msg = f"Error during thinking: {str(e)}"
            self.logger.error(error_msg)

            await self.log_activity(
                activity_type="ThinkingError",
                description="Error during internal reasoning",
                input_data={"prompt": prompt},
                output_data={"error": str(e)}
            )

            return "", error_msg

    def __str__(self) -> str:
        return f"{self.agent_type}(id={self.agent_id}, name={self.agent_name})"
```

### Task 3: Vector Memory Implementation

**What needs to be done:**
Create a vector memory system that enables semantic search capabilities across the shared knowledge base.

**Why this task is necessary:**
Vector memory is essential for efficient knowledge retrieval and enables agents to find relevant context based on semantic similarity rather than exact keyword matches.

**Files to be created:**

- `agents/memory/vector_memory.py` - Vector memory implementation
- `agents/memory/__init__.py` - Package initialization

**Implementation guidelines:**

```python
# agents/memory/vector_memory.py

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

class VectorMemory:
    """Vector-based memory system for semantic search using pgvector."""

    def __init__(self, db_client):
        self.db_client = db_client
        self.logger = logging.getLogger("agent.memory.vector")

    async def initialize(self) -> None:
        """Initialize the vector memory tables if they don't exist."""
        # Ensure pgvector extension is available
        await self.db_client.execute("CREATE EXTENSION IF NOT EXISTS pgvector;")

        # Create vector_embeddings table if it doesn't exist
        await self.db_client.execute("""
        CREATE TABLE IF NOT EXISTS vector_embeddings (
            id SERIAL PRIMARY KEY,
            entity_type VARCHAR(50) NOT NULL,
            entity_id VARCHAR(255) NOT NULL,
            embedding VECTOR(1536) NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(entity_type, entity_id)
        );
        """)

        # Create index for faster similarity search
        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_vector_embeddings ON vector_embeddings
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)

    async def store_embedding(
        self,
        entity_type: str,
        entity_id: str,
        embedding: List[float],
        metadata: Dict[str, Any] = None
    ) -> None:
        """Store an embedding vector for an entity."""
        query = """
        INSERT INTO vector_embeddings (entity_type, entity_id, embedding, metadata)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (entity_type, entity_id)
        DO UPDATE SET
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata,
            created_at = NOW()
        """

        await self.db_client.execute(
            query,
            entity_type,
            entity_id,
            embedding,
            json.dumps(metadata or {})
        )

        self.logger.debug(f"Stored embedding for {entity_type}:{entity_id}")

    async def search_similar(
        self,
        entity_type: str,
        query_embedding: List[float],
        threshold: float = 0.7,
        limit: int = 10
    ) -> List[str]:
        """Search for entities similar to the query embedding."""
        query = """
        SELECT
            entity_id,
            1 - (embedding <=> $1) AS similarity
        FROM
            vector_embeddings
        WHERE
            entity_type = $2
            AND 1 - (embedding <=> $1) > $3
        ORDER BY
            similarity DESC
        LIMIT $4
        """

        results = await self.db_client.fetch_all(
            query,
            query_embedding,
            entity_type,
            threshold,
            limit
        )

        entity_ids = [row["entity_id"] for row in results]

        self.logger.debug(f"Found {len(entity_ids)} similar {entity_type} entities")
        return entity_ids

    async def get_embedding(self, entity_type: str, entity_id: str) -> Optional[List[float]]:
        """Retrieve the embedding for a specific entity."""
        query = """
        SELECT embedding
        FROM vector_embeddings
        WHERE entity_type = $1 AND entity_id = $2
        """

        result = await self.db_client.fetch_one(query, entity_type, entity_id)

        if result:
            return result["embedding"]
        return None

    async def delete_embedding(self, entity_type: str, entity_id: str) -> bool:
        """Delete an embedding from the vector memory."""
        query = """
        DELETE FROM vector_embeddings
        WHERE entity_type = $1 AND entity_id = $2
        RETURNING id
        """

        result = await self.db_client.fetch_one(query, entity_type, entity_id)

        success = result is not None
        if success:
            self.logger.debug(f"Deleted embedding for {entity_type}:{entity_id}")
        else:
            self.logger.warning(f"Embedding for {entity_type}:{entity_id} not found for deletion")

        return success

    async def list_entity_types(self) -> List[str]:
        """List all entity types stored in the vector memory."""
        query = """
        SELECT DISTINCT entity_type
        FROM vector_embeddings
        """

        results = await self.db_client.fetch_all(query)
        return [row["entity_type"] for row in results]

    async def count_embeddings(self, entity_type: Optional[str] = None) -> int:
        """Count the number of embeddings, optionally filtered by entity type."""
        if entity_type:
            query = """
            SELECT COUNT(*) as count
            FROM vector_embeddings
            WHERE entity_type = $1
            """
            result = await self.db_client.fetch_one(query, entity_type)
        else:
            query = "SELECT COUNT(*) as count FROM vector_embeddings"
            result = await self.db_client.fetch_one(query)

        return result["count"] if result else 0
```

## Post-Implementation Verification

After completing all tasks, verify the implementation by:

1. Running unit tests for all components
2. Testing the messaging system between two BaseAgent instances using the structured communication protocol
3. Verifying that all activities are properly logged to PostgreSQL
4. Testing vector memory with sample embeddings and search queries
5. Ensuring the CLI tool can correctly interact with agents
6. Verifying that the agent communication protocol correctly formats and parses different message types

All components should be fully operational and ready for extending into specialized agents in the next phase.
