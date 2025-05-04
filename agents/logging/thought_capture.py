# agents/logging/thought_capture.py

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..db.postgres import PostgresClient
from ..memory.vector_memory import EnhancedVectorMemory  # Correct import
from ..llm.base import LLMProvider


class ThoughtCapture:
    """
    System for capturing, storing, and retrieving agent thought processes.
    """

    def __init__(
        self,
        db_client: PostgresClient,
        vector_memory: Optional[EnhancedVectorMemory] = None,
        llm_provider: Optional[LLMProvider] = None,
    ):
        if db_client is None:
            raise ValueError("PostgresClient instance is required for ThoughtCapture.")
        self.db_client = db_client
        self.vector_memory = vector_memory
        self.llm_provider = llm_provider
        self.logger = logging.getLogger("agent.logging.thought")
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the thought capture system idempotently."""
        async with self._init_lock:
            if self._initialized:
                self.logger.debug("ThoughtCapture already initialized.")
                return

            self.logger.info("Initializing ThoughtCapture system...")
            try:
                # Create thought_processes table if it doesn't exist (schema.sql handles this)
                # Verify required indexes exist (idempotent)
                await self.db_client.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_thought_processes_agent_id ON thought_processes(agent_id);
                """
                )

                await self.db_client.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_thought_processes_task_id ON thought_processes(related_task_id);
                """
                )

                await self.db_client.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_thought_processes_tags ON thought_processes USING GIN(tags);
                """
                )

                self._initialized = True
                self.logger.info("Thought capture system initialized successfully.")

                # Register with vector memory if available
                await self._register_with_vector_memory()

            except Exception as e:
                self.logger.error(
                    f"Failed to initialize ThoughtCapture: {e}", exc_info=True
                )
                raise  # Propagate the error

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()
        if not self._initialized:
            raise RuntimeError("ThoughtCapture failed to initialize.")

    async def _register_with_vector_memory(self):
        """Register the ThoughtProcess entity type with vector memory if available."""
        if self.vector_memory:
            try:
                await self.vector_memory._ensure_initialized()  # Ensure vector memory is ready
                self.vector_memory.register_entity_type(
                    entity_type="ThoughtProcess",
                    schema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string", "format": "uuid"},
                            "reasoning_path": {"type": "string"},
                            "conclusion": {"type": "string"},
                            "context": {"type": "string"},
                            "related_task_id": {
                                "type": ["string", "null"],
                                "format": "uuid",
                            },
                            "tags": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                    # Optional: Add a content extractor if needed
                    # content_extractor=lambda data: f"Context: {data.get('context','')}\nReasoning: {data.get('reasoning_path','')}"
                )
                self.logger.info(
                    "Registered ThoughtProcess entity type with vector memory"
                )
            except Exception as e:
                self.logger.error(
                    f"Error registering ThoughtProcess with vector memory: {e}",
                    exc_info=True,
                )
        else:
            self.logger.debug(
                "Vector memory not available, skipping ThoughtProcess registration."
            )

    async def capture_thought_process(
        self,
        agent_id: str,
        context: str,
        thought_steps: List[Dict[str, Any]],
        reasoning_path: str,
        conclusion: Optional[str] = None,
        related_task_id: Optional[str] = None,
        related_files: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Capture and store an agent's thought process.

        Args:
            agent_id: ID of the agent
            context: The context or prompt that initiated the thinking
            thought_steps: List of structured thought steps (with timestamp, content, etc.)
            reasoning_path: The overall reasoning path/narrative
            conclusion: The final conclusion or decision reached
            related_task_id: Optional ID of the related task
            related_files: Optional list of related file paths
            metadata: Additional metadata about the thought process
            tags: List of tags for categorization

        Returns:
            The thought process ID (UUID as string) or None on failure.
        """
        await self._ensure_initialized()

        # Generate UUID for the thought process
        thought_id = str(uuid4())

        # Store in database
        query = """
        INSERT INTO thought_processes (
            id, agent_id, timestamp, context,
            thought_steps, reasoning_path, conclusion,
            related_task_id, related_files, metadata, tags
        )
        VALUES ($1, $2, NOW(), $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
        """

        try:
            result = await self.db_client.fetch_one(
                query,
                thought_id,
                agent_id,
                context,
                json.dumps(thought_steps),
                reasoning_path,
                conclusion,
                related_task_id,
                related_files or [],
                json.dumps(metadata or {}),
                tags or [],
            )
            if not result or not result["id"]:
                self.logger.error(
                    f"Failed to store thought process for agent {agent_id} - no ID returned."
                )
                return None

            # Store in vector memory if available
            if self.vector_memory and self.llm_provider:
                await self._store_thought_embedding(
                    thought_id=thought_id,
                    agent_id=agent_id,
                    context=context,
                    reasoning_path=reasoning_path,
                    conclusion=conclusion,
                    related_task_id=related_task_id,
                    tags=tags,
                )

            self.logger.info(f"Captured thought process: {thought_id}")
            return thought_id
        except Exception as e:
            self.logger.error(
                f"Error capturing thought process for agent {agent_id}: {e}",
                exc_info=True,
            )
            return None  # Indicate failure

    async def _store_thought_embedding(
        self,
        thought_id: str,
        agent_id: str,
        context: str,
        reasoning_path: str,
        conclusion: Optional[str],
        related_task_id: Optional[str],
        tags: Optional[List[str]],
    ):
        """Helper to generate and store embedding for a thought process."""
        try:
            # Combine relevant text for embedding
            embedable_content = f"Context: {context}\nReasoning: {reasoning_path}\nConclusion: {conclusion or 'N/A'}"

            # Generate embedding
            embedding = await self.llm_provider.generate_embeddings(embedable_content)
            if not embedding:
                self.logger.warning(
                    f"Could not generate embedding for thought {thought_id}"
                )
                return

            # Store in vector memory
            await self.vector_memory.store_entity(
                entity_type="ThoughtProcess",
                entity_id=thought_id,
                content=embedable_content,  # Store the text used for embedding
                embedding=embedding,
                metadata={
                    "agent_id": agent_id,
                    "related_task_id": related_task_id,
                    "timestamp": time.time(),  # Store timestamp of embedding creation
                    "conclusion_present": conclusion is not None,
                },
                tags=tags or [],
            )

            # Create relationships if related to task
            if related_task_id:
                await self.vector_memory.create_relationship(
                    source_entity_type="ThoughtProcess",
                    source_entity_id=thought_id,
                    target_entity_type="Task",  # Assuming tasks are stored with entity_type "Task"
                    target_entity_id=related_task_id,
                    relationship_type="relatedToTask",
                )

            self.logger.debug(f"Stored thought process embedding: {thought_id}")

        except Exception as e:
            self.logger.error(
                f"Error storing thought embedding {thought_id}: {e}", exc_info=True
            )

    async def get_thought_process(self, thought_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific thought process by ID.

        Args:
            thought_id: ID of the thought process to retrieve

        Returns:
            The thought process data or None if not found
        """
        await self._ensure_initialized()

        query = """
        SELECT
            id, agent_id, timestamp, context,
            thought_steps, reasoning_path, conclusion,
            related_task_id, related_files, metadata, tags
        FROM thought_processes
        WHERE id = $1
        """
        try:
            result = await self.db_client.fetch_one(query, thought_id)

            if not result:
                return None

            return {
                "id": str(result["id"]),
                "agent_id": str(result["agent_id"]),
                "timestamp": result["timestamp"],
                "context": result["context"],
                "thought_steps": json.loads(result["thought_steps"]),
                "reasoning_path": result["reasoning_path"],
                "conclusion": result["conclusion"],
                "related_task_id": (
                    str(result["related_task_id"])
                    if result["related_task_id"]
                    else None
                ),
                "related_files": result["related_files"],
                "metadata": (
                    json.loads(result["metadata"]) if result["metadata"] else {}
                ),
                "tags": result["tags"] or [],
            }
        except Exception as e:
            self.logger.error(
                f"Error retrieving thought process {thought_id}: {e}", exc_info=True
            )
            return None

    async def search_thoughts(
        self,
        query: str,
        agent_id: Optional[str] = None,
        related_task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
        threshold: float = 0.7,  # Added threshold
    ) -> List[Dict[str, Any]]:
        """
        Search for thought processes using semantic search.

        Args:
            query: Natural language query to search for
            agent_id: Optional filter by agent ID
            related_task_id: Optional filter by related task ID
            tags: Optional filter by tags
            limit: Maximum number of results to return
            threshold: Minimum similarity score

        Returns:
            List of matching thought processes with similarity score
        """
        await self._ensure_initialized()
        if not self.vector_memory or not self.llm_provider:
            self.logger.error(
                "Vector memory or LLM provider not available for thought search"
            )
            return []

        # Generate embedding for the query
        try:
            query_embedding = await self.llm_provider.generate_embeddings(query)
            if not query_embedding:
                self.logger.warning(
                    f"Failed to generate embedding for thought search query: {query[:100]}..."
                )
                return []
        except Exception as e:
            self.logger.error(
                f"Error generating embedding for thought search query: {e}",
                exc_info=True,
            )
            return []

        # Prepare metadata filter for vector search
        vector_metadata_filter = {}
        if agent_id:
            vector_metadata_filter["agent_id"] = agent_id
        if related_task_id:
            vector_metadata_filter["related_task_id"] = related_task_id

        # Search for similar thought processes in vector memory
        try:
            similar_thoughts_vectors = await self.vector_memory.search_similar(
                query_embedding=query_embedding,
                entity_types=["ThoughtProcess"],
                tags=tags,
                metadata_filter=vector_metadata_filter,
                limit=limit,
                threshold=threshold,
            )
        except Exception as e:
            self.logger.error(
                f"Error searching vector memory for thoughts: {e}", exc_info=True
            )
            return []

        # Fetch full thought process data for each result from the main table
        results = []
        thought_ids = [t["entity_id"] for t in similar_thoughts_vectors]

        if not thought_ids:
            self.logger.debug("No similar thoughts found in vector memory.")
            return []

        # Create placeholders for the IN clause
        placeholders = ", ".join([f"${i+1}" for i in range(len(thought_ids))])
        db_query = f"""
        SELECT * FROM thought_processes WHERE id IN ({placeholders})
        """
        try:
            full_thoughts_data = await self.db_client.fetch_all(db_query, *thought_ids)

            # Create a map for easy lookup
            thoughts_map = {str(row["id"]): dict(row) for row in full_thoughts_data}

            # Combine data, adding similarity score
            for vector_result in similar_thoughts_vectors:
                thought_id = vector_result["entity_id"]
                if thought_id in thoughts_map:
                    full_thought = thoughts_map[thought_id]
                    # Structure the result nicely
                    results.append(
                        {
                            "id": thought_id,
                            "agent_id": str(full_thought["agent_id"]),
                            "timestamp": full_thought["timestamp"],
                            "context": full_thought["context"],
                            "thought_steps": json.loads(full_thought["thought_steps"]),
                            "reasoning_path": full_thought["reasoning_path"],
                            "conclusion": full_thought["conclusion"],
                            "related_task_id": (
                                str(full_thought["related_task_id"])
                                if full_thought["related_task_id"]
                                else None
                            ),
                            "related_files": full_thought["related_files"],
                            "metadata": (
                                json.loads(full_thought["metadata"])
                                if full_thought["metadata"]
                                else {}
                            ),
                            "tags": full_thought["tags"] or [],
                            "similarity": vector_result["similarity"],
                        }
                    )
                else:
                    self.logger.warning(
                        f"Thought ID {thought_id} found in vector search but not in main table."
                    )

        except Exception as e:
            self.logger.error(f"Error retrieving full thought data: {e}", exc_info=True)

        # Sort final results by similarity (descending)
        results.sort(key=lambda x: x.get("similarity", 0), reverse=True)

        self.logger.debug(
            f"Found {len(results)} thought processes for query: {query[:50]}..."
        )
        return results
