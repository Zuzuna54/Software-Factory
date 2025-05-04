# Iteration 4: Shared Knowledge Base & Vector Memory

## Overview

This phase expands the vector memory and shared knowledge base capabilities of our system. We'll enhance the pgvector integration to store and retrieve embeddings for all content types, implement semantic search capabilities, and create cross-referencing between related artifacts. This enables agents to find relevant information from the shared knowledge base efficiently.

## Why This Phase Matters

A robust shared knowledge base is critical for agent coordination and context awareness. By enhancing vector memory capabilities, agents can efficiently retrieve relevant information from a large codebase and maintain coherence across the development process. This is essential for scaling to larger projects.

## Expected Outcomes

After completing this phase, we will have:

1. Enhanced pgvector integration for storing and retrieving embeddings
2. A `search_memory()` helper function for context-aware retrieval
3. Specialized indexes for different artifact types
4. Cross-referencing capabilities between related artifacts
5. Thought process capturing for transparent agent decision-making

## Implementation Tasks

### Task 1: Enhanced Vector Memory System

**What needs to be done:**
Expand the vector memory system to handle more sophisticated storage and retrieval operations.

**Why this task is necessary:**
A more robust vector memory system enables efficient semantic search across a variety of content types and supports complex agent reasoning.

**Files to be created/updated:**

- `agents/memory/enhanced_vector_memory.py` - Enhanced vector memory implementation

**Implementation guidelines:**

```python
# agents/memory/enhanced_vector_memory.py

import asyncio
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
import uuid

from ..db.postgres import PostgresClient

class EnhancedVectorMemory:
    """Enhanced vector-based memory system for semantic search using pgvector."""

    def __init__(self, db_client: PostgresClient):
        self.db_client = db_client
        self.logger = logging.getLogger("agent.memory.enhanced_vector")
        self.entity_types = {}  # Registry of entity types and their schemas

    async def initialize(self) -> None:
        """Initialize the vector memory tables if they don't exist."""
        # Ensure pgvector extension is available
        await self.db_client.execute("CREATE EXTENSION IF NOT EXISTS pgvector;")

        # Create enhanced vector storage
        await self.db_client.execute("""
        CREATE TABLE IF NOT EXISTS enhanced_vector_storage (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(50) NOT NULL,
            entity_id VARCHAR(255) NOT NULL,
            embedding VECTOR(1536) NOT NULL,
            content TEXT,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            tags TEXT[],
            UNIQUE(entity_type, entity_id)
        );
        """)

        # Create vector relationships table
        await self.db_client.execute("""
        CREATE TABLE IF NOT EXISTS vector_relationships (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_entity_type VARCHAR(50) NOT NULL,
            source_entity_id VARCHAR(255) NOT NULL,
            target_entity_type VARCHAR(50) NOT NULL,
            target_entity_id VARCHAR(255) NOT NULL,
            relationship_type VARCHAR(50) NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(source_entity_type, source_entity_id, target_entity_type, target_entity_id, relationship_type)
        );
        """)

        # Create indexes for faster similarity search
        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_enhanced_vector_entity_type
        ON enhanced_vector_storage(entity_type);
        """)

        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_enhanced_vector_tags
        ON enhanced_vector_storage USING GIN(tags);
        """)

        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_enhanced_vector_embedding
        ON enhanced_vector_storage USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """)

        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_vector_relationships_source
        ON vector_relationships(source_entity_type, source_entity_id);
        """)

        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_vector_relationships_target
        ON vector_relationships(target_entity_type, target_entity_id);
        """)

        self.logger.info("Enhanced vector memory system initialized")

    def register_entity_type(
        self,
        entity_type: str,
        schema: Dict[str, Any],
        content_extractor: Optional[Callable] = None
    ) -> None:
        """
        Register an entity type with its schema and optional content extractor.

        Args:
            entity_type: The type of entity (e.g., "Code", "UserStory")
            schema: JSON Schema defining the entity structure
            content_extractor: Optional function to extract embedable content
        """
        self.entity_types[entity_type] = {
            "schema": schema,
            "content_extractor": content_extractor
        }

        self.logger.info(f"Registered entity type: {entity_type}")

    async def store_entity(
        self,
        entity_type: str,
        entity_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any] = None,
        tags: List[str] = None
    ) -> str:
        """
        Store an entity with its embedding in the vector memory.

        Args:
            entity_type: Type of entity (e.g., "Code", "UserStory")
            entity_id: Unique identifier for the entity
            content: The raw content to be stored
            embedding: Vector embedding of the content
            metadata: Additional structured metadata
            tags: List of tags for categorization

        Returns:
            The entity ID
        """
        if not self.db_client:
            self.logger.error("No database client available")
            raise ValueError("Database client is required")

        query = """
        INSERT INTO enhanced_vector_storage (
            entity_type, entity_id, embedding, content,
            metadata, tags, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (entity_type, entity_id)
        DO UPDATE SET
            embedding = EXCLUDED.embedding,
            content = EXCLUDED.content,
            metadata = EXCLUDED.metadata,
            tags = EXCLUDED.tags,
            updated_at = NOW()
        RETURNING id
        """

        result = await self.db_client.fetch_one(
            query,
            entity_type,
            entity_id,
            embedding,
            content,
            json.dumps(metadata or {}),
            tags or []
        )

        self.logger.debug(f"Stored entity {entity_type}:{entity_id}")
        return str(result["id"]) if result else None

    async def search_similar(
        self,
        query_embedding: List[float],
        entity_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for entities similar to the query embedding with filtering options.

        Args:
            query_embedding: Vector embedding to search for
            entity_types: Optional list of entity types to filter by
            tags: Optional list of tags to filter by
            metadata_filter: Optional metadata conditions to filter by
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of matching entities with similarity scores
        """
        if not self.db_client:
            self.logger.error("No database client available")
            return []

        # Build the query conditions
        conditions = ["1 - (embedding <=> $1) > $2"]
        params = [query_embedding, threshold]
        param_idx = 3

        if entity_types:
            placeholders = ', '.join(f'${param_idx + i}' for i in range(len(entity_types)))
            conditions.append(f"entity_type IN ({placeholders})")
            params.extend(entity_types)
            param_idx += len(entity_types)

        if tags:
            # Filter entities that have at least one matching tag
            tag_conditions = []
            for tag in tags:
                tag_conditions.append(f"${param_idx} = ANY(tags)")
                params.append(tag)
                param_idx += 1
            if tag_conditions:
                conditions.append(f"({' OR '.join(tag_conditions)})")

        if metadata_filter:
            for key, value in metadata_filter.items():
                conditions.append(f"metadata->>${param_idx} = ${param_idx+1}")
                params.append(key)
                params.append(str(value))
                param_idx += 2

        # Build the final query
        query = f"""
        SELECT
            id, entity_type, entity_id, content,
            metadata, tags, created_at, updated_at,
            1 - (embedding <=> $1) AS similarity
        FROM
            enhanced_vector_storage
        WHERE
            {' AND '.join(conditions)}
        ORDER BY
            similarity DESC
        LIMIT ${param_idx}
        """

        params.append(limit)

        try:
            results = await self.db_client.fetch_all(query, *params)

            entities = []
            for row in results:
                entities.append({
                    "id": str(row["id"]),
                    "entity_type": row["entity_type"],
                    "entity_id": row["entity_id"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "tags": row["tags"] or [],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "similarity": float(row["similarity"])
                })

            self.logger.debug(f"Found {len(entities)} similar entities")
            return entities

        except Exception as e:
            self.logger.error(f"Error during similarity search: {str(e)}")
            return []

    async def create_relationship(
        self,
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        relationship_type: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Create a relationship between two entities.

        Args:
            source_entity_type: Type of the source entity
            source_entity_id: ID of the source entity
            target_entity_type: Type of the target entity
            target_entity_id: ID of the target entity
            relationship_type: Type of relationship (e.g., "implements", "tests")
            metadata: Additional metadata about the relationship

        Returns:
            The relationship ID
        """
        if not self.db_client:
            self.logger.error("No database client available")
            raise ValueError("Database client is required")

        query = """
        INSERT INTO vector_relationships (
            source_entity_type, source_entity_id,
            target_entity_type, target_entity_id,
            relationship_type, metadata
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (source_entity_type, source_entity_id, target_entity_type, target_entity_id, relationship_type)
        DO UPDATE SET
            metadata = EXCLUDED.metadata
        RETURNING id
        """

        result = await self.db_client.fetch_one(
            query,
            source_entity_type,
            source_entity_id,
            target_entity_type,
            target_entity_id,
            relationship_type,
            json.dumps(metadata or {})
        )

        self.logger.debug(
            f"Created relationship {relationship_type} from {source_entity_type}:{source_entity_id} "
            f"to {target_entity_type}:{target_entity_id}"
        )
        return str(result["id"]) if result else None

    async def get_related_entities(
        self,
        entity_type: str,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        target_entity_types: Optional[List[str]] = None,
        as_source: bool = True,
        as_target: bool = True,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get entities related to the specified entity.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            relationship_types: Optional list of relationship types to filter by
            target_entity_types: Optional list of target entity types to filter by
            as_source: Include relationships where the entity is the source
            as_target: Include relationships where the entity is the target
            limit: Maximum number of results to return

        Returns:
            List of related entities with relationship information
        """
        if not self.db_client:
            self.logger.error("No database client available")
            return []

        if not as_source and not as_target:
            self.logger.warning("Both as_source and as_target are False, returning empty list")
            return []

        # Prepare query parts for both directions
        queries = []
        query_params = []
        param_idx = 1

        if as_source:
            source_conditions = [f"source_entity_type = ${param_idx}", f"source_entity_id = ${param_idx+1}"]
            query_params.extend([entity_type, entity_id])
            param_idx += 2

            if relationship_types:
                placeholders = ', '.join(f'${param_idx + i}' for i in range(len(relationship_types)))
                source_conditions.append(f"relationship_type IN ({placeholders})")
                query_params.extend(relationship_types)
                param_idx += len(relationship_types)

            if target_entity_types:
                placeholders = ', '.join(f'${param_idx + i}' for i in range(len(target_entity_types)))
                source_conditions.append(f"target_entity_type IN ({placeholders})")
                query_params.extend(target_entity_types)
                param_idx += len(target_entity_types)

            source_query = f"""
            SELECT
                r.id, r.relationship_type, r.metadata,
                'outgoing' AS direction,
                r.target_entity_type AS related_entity_type,
                r.target_entity_id AS related_entity_id,
                e.content, e.metadata AS entity_metadata,
                e.tags, e.created_at, e.updated_at
            FROM
                vector_relationships r
            LEFT JOIN
                enhanced_vector_storage e ON
                    r.target_entity_type = e.entity_type AND
                    r.target_entity_id = e.entity_id
            WHERE
                {' AND '.join(source_conditions)}
            """
            queries.append(source_query)

        if as_target:
            target_conditions = [f"target_entity_type = ${param_idx}", f"target_entity_id = ${param_idx+1}"]
            query_params.extend([entity_type, entity_id])
            param_idx += 2

            if relationship_types:
                placeholders = ', '.join(f'${param_idx + i}' for i in range(len(relationship_types)))
                target_conditions.append(f"relationship_type IN ({placeholders})")
                query_params.extend(relationship_types)
                param_idx += len(relationship_types)

            if target_entity_types:
                placeholders = ', '.join(f'${param_idx + i}' for i in range(len(target_entity_types)))
                target_conditions.append(f"source_entity_type IN ({placeholders})")
                query_params.extend(target_entity_types)
                param_idx += len(target_entity_types)

            target_query = f"""
            SELECT
                r.id, r.relationship_type, r.metadata,
                'incoming' AS direction,
                r.source_entity_type AS related_entity_type,
                r.source_entity_id AS related_entity_id,
                e.content, e.metadata AS entity_metadata,
                e.tags, e.created_at, e.updated_at
            FROM
                vector_relationships r
            LEFT JOIN
                enhanced_vector_storage e ON
                    r.source_entity_type = e.entity_type AND
                    r.source_entity_id = e.entity_id
            WHERE
                {' AND '.join(target_conditions)}
            """
            queries.append(target_query)

        # Combine the queries
        combined_query = " UNION ALL ".join(queries) + f" LIMIT ${param_idx}"
        query_params.append(limit)

        try:
            results = await self.db_client.fetch_all(combined_query, *query_params)

            relationships = []
            for row in results:
                relationships.append({
                    "id": str(row["id"]),
                    "relationship_type": row["relationship_type"],
                    "direction": row["direction"],
                    "related_entity_type": row["related_entity_type"],
                    "related_entity_id": row["related_entity_id"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "content": row["content"],
                    "entity_metadata": json.loads(row["entity_metadata"]) if row["entity_metadata"] else {},
                    "tags": row["tags"] or [],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })

            self.logger.debug(f"Found {len(relationships)} relationships for {entity_type}:{entity_id}")
            return relationships

        except Exception as e:
            self.logger.error(f"Error getting related entities: {str(e)}")
            return []
```

### Task 2: Context-Aware Search Function

**What needs to be done:**
Implement a universal `search_memory()` helper function for context-aware retrieval across the knowledge base.

**Why this task is necessary:**
A consistent search interface enables agents to efficiently find relevant information without needing to know the underlying storage details.

**Files to be created:**

- `agents/memory/search.py` - Memory search implementation

**Implementation guidelines:**

```python
# agents/memory/search.py

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
import uuid

from ..db.postgres import PostgresClient
from ..llm.base import LLMProvider
from .enhanced_vector_memory import EnhancedVectorMemory

class MemorySearch:
    """Memory search utilities for finding relevant information in the knowledge base."""

    def __init__(
        self,
        db_client: PostgresClient,
        vector_memory: EnhancedVectorMemory,
        llm_provider: LLMProvider
    ):
        self.db_client = db_client
        self.vector_memory = vector_memory
        self.llm_provider = llm_provider
        self.logger = logging.getLogger("agent.memory.search")

    async def search_memory(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        expand_relationships: bool = False,
        include_content: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the memory for information related to the query.

        Args:
            query: Natural language query to search for
            entity_types: Optional list of entity types to search within
            tags: Optional list of tags to filter by
            metadata_filter: Optional metadata conditions to filter by
            limit: Maximum number of direct results to return
            expand_relationships: Whether to include related entities
            include_content: Whether to include the full content in results

        Returns:
            List of matching items from memory
        """
        if not self.llm_provider or not self.vector_memory:
            self.logger.error("LLM provider or vector memory not available")
            return []

        # Generate embedding for the query
        try:
            query_embedding = await self.llm_provider.generate_embeddings(query)
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            return []

        # Search for similar entities
        similar_entities = await self.vector_memory.search_similar(
            query_embedding=query_embedding,
            entity_types=entity_types,
            tags=tags,
            metadata_filter=metadata_filter,
            limit=limit
        )

        results = []
        expanded_entity_ids = set()  # Track entities we've already expanded

        # Process direct results
        for entity in similar_entities:
            result = {
                "id": entity["id"],
                "entity_type": entity["entity_type"],
                "entity_id": entity["entity_id"],
                "similarity": entity["similarity"],
                "metadata": entity["metadata"],
                "tags": entity["tags"],
                "created_at": entity["created_at"],
                "updated_at": entity["updated_at"],
                "match_type": "direct"
            }

            if include_content:
                result["content"] = entity["content"]

            results.append(result)
            expanded_entity_ids.add(f"{entity['entity_type']}:{entity['entity_id']}")

        # Expand relationships if requested
        if expand_relationships and similar_entities:
            for entity in similar_entities:
                # Skip if we've already processed this entity's relationships
                entity_key = f"{entity['entity_type']}:{entity['entity_id']}"
                if entity_key not in expanded_entity_ids:
                    continue

                related = await self.vector_memory.get_related_entities(
                    entity_type=entity["entity_type"],
                    entity_id=entity["entity_id"],
                    limit=5  # Limit relationships per entity
                )

                for rel in related:
                    related_key = f"{rel['related_entity_type']}:{rel['related_entity_id']}"

                    # Skip if we've already included this entity
                    if related_key in expanded_entity_ids:
                        continue

                    expanded_entity_ids.add(related_key)

                    result = {
                        "id": rel["id"],
                        "entity_type": rel["related_entity_type"],
                        "entity_id": rel["related_entity_id"],
                        "similarity": None,  # No direct similarity score
                        "metadata": rel["entity_metadata"],
                        "tags": rel["tags"],
                        "created_at": rel["created_at"],
                        "updated_at": rel["updated_at"],
                        "match_type": "related",
                        "relationship": {
                            "type": rel["relationship_type"],
                            "direction": rel["direction"],
                            "source": entity_key if rel["direction"] == "outgoing" else related_key,
                            "target": related_key if rel["direction"] == "outgoing" else entity_key,
                            "metadata": rel["metadata"]
                        }
                    }

                    if include_content:
                        result["content"] = rel["content"]

                    results.append(result)

                    # Don't let the results grow too large
                    if len(results) >= limit * 2:
                        break

                # Don't let the results grow too large
                if len(results) >= limit * 2:
                    break

        self.logger.debug(f"Found {len(results)} results for query: {query[:50]}...")
        return results

    async def analyze_results(
        self,
        query: str,
        search_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze search results to extract key insights and relevance.

        Args:
            query: The original search query
            search_results: Results from search_memory

        Returns:
            Analysis of the search results
        """
        if not self.llm_provider or not search_results:
            return {"relevant_count": 0, "summary": "No results to analyze."}

        system_message = """You are analyzing search results to determine their relevance to a query.
        Examine each result and provide:
        1. How many results are truly relevant to the query
        2. A brief summary of the key information found
        3. Any important connections or patterns in the results
        4. Suggestions for refining the search if needed

        Be concise and focus on the most important information."""

        # Prepare results for analysis
        result_summary = []
        for i, res in enumerate(search_results[:10]):  # Limit to top 10 for analysis
            content_preview = res.get("content", "")
            if content_preview:
                if len(content_preview) > 300:
                    content_preview = content_preview[:300] + "..."

            result_summary.append(f"""
            Result {i+1}:
            - Type: {res['entity_type']}
            - Match: {res.get('match_type', 'direct')}
            - Similarity: {res.get('similarity', 'N/A')}
            - Tags: {', '.join(res.get('tags', []))}
            - Preview: {content_preview}
            """)

        prompt = f"""
        Query: {query}

        Search Results:
        {''.join(result_summary)}

        Please analyze these results for relevance and key insights.
        """

        try:
            analysis_text, error = await self.llm_provider.generate_completion(
                prompt=prompt,
                system_message=system_message
            )

            if error:
                self.logger.error(f"Error analyzing results: {error}")
                return {"error": error}

            # Count how many results were considered relevant
            relevant_count = 0
            if search_results:
                # Simple heuristic: count results with similarity > 0.8 as relevant
                relevant_count = sum(1 for r in search_results if r.get('similarity', 0) > 0.8)

            return {
                "relevant_count": relevant_count,
                "total_count": len(search_results),
                "analysis": analysis_text,
                "query": query
            }

        except Exception as e:
            self.logger.error(f"Error during result analysis: {str(e)}")
            return {"error": str(e)}
```

### Task 3: Thought Process Capture Implementation

**What needs to be done:**
Enhance the logging system to capture and store agent thought processes during reasoning.

**Why this task is necessary:**
Transparency into agent decision-making is essential for debugging, auditing, and improving agent behaviors over time.

**Files to be created/updated:**

- `agents/logging/thought_capture.py` - Thought process capture implementation

**Implementation guidelines:**

```python
# agents/logging/thought_capture.py

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..db.postgres import PostgresClient
from ..memory.enhanced_vector_memory import EnhancedVectorMemory
from ..llm.base import LLMProvider

class ThoughtCapture:
    """
    System for capturing, storing, and retrieving agent thought processes.
    """

    def __init__(
        self,
        db_client: PostgresClient,
        vector_memory: Optional[EnhancedVectorMemory] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.db_client = db_client
        self.vector_memory = vector_memory
        self.llm_provider = llm_provider
        self.logger = logging.getLogger("agent.logging.thought")

    async def initialize(self) -> None:
        """Initialize the thought capture system."""
        # Create thought_processes table if it doesn't exist
        await self.db_client.execute("""
        CREATE TABLE IF NOT EXISTS thought_processes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
            context TEXT,
            thought_steps JSONB NOT NULL,
            reasoning_path TEXT NOT NULL,
            conclusion TEXT,
            related_task_id UUID,
            related_files TEXT[],
            metadata JSONB,
            tags TEXT[]
        );
        """)

        # Create index for faster retrieval
        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_thought_processes_agent_id ON thought_processes(agent_id);
        """)

        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_thought_processes_task_id ON thought_processes(related_task_id);
        """)

        await self.db_client.execute("""
        CREATE INDEX IF NOT EXISTS idx_thought_processes_tags ON thought_processes USING GIN(tags);
        """)

        self.logger.info("Thought capture system initialized")

        # Register with vector memory if available
        if self.vector_memory:
            try:
                self.vector_memory.register_entity_type(
                    entity_type="ThoughtProcess",
                    schema={
                        "type": "object",
                        "properties": {
                            "agent_id": {"type": "string"},
                            "reasoning_path": {"type": "string"},
                            "conclusion": {"type": "string"},
                            "context": {"type": "string"}
                        }
                    }
                )
                self.logger.info("Registered ThoughtProcess entity type with vector memory")
            except Exception as e:
                self.logger.error(f"Error registering with vector memory: {str(e)}")

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
        tags: Optional[List[str]] = None
    ) -> str:
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
            The thought process ID
        """
        if not self.db_client:
            self.logger.error("No database client available")
            raise ValueError("Database client is required")

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
            tags or []
        )

        # Store in vector memory if available
        if self.vector_memory and self.llm_provider:
            try:
                # Combine relevant text for embedding
                embedable_content = f"Context: {context}\nReasoning: {reasoning_path}\nConclusion: {conclusion or ''}"

                # Generate embedding
                embedding = await self.llm_provider.generate_embeddings(embedable_content)

                # Store in vector memory
                await self.vector_memory.store_entity(
                    entity_type="ThoughtProcess",
                    entity_id=thought_id,
                    content=embedable_content,
                    embedding=embedding,
                    metadata={
                        "agent_id": agent_id,
                        "related_task_id": related_task_id,
                        "timestamp": time.time()
                    },
                    tags=tags or []
                )

                # Create relationships if related to task
                if related_task_id:
                    await self.vector_memory.create_relationship(
                        source_entity_type="ThoughtProcess",
                        source_entity_id=thought_id,
                        target_entity_type="Task",
                        target_entity_id=related_task_id,
                        relationship_type="relatedTo"
                    )

                self.logger.debug(f"Stored thought process in vector memory: {thought_id}")

            except Exception as e:
                self.logger.error(f"Error storing thought in vector memory: {str(e)}")

        self.logger.info(f"Captured thought process: {thought_id}")
        return thought_id

    async def get_thought_process(self, thought_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific thought process by ID.

        Args:
            thought_id: ID of the thought process to retrieve

        Returns:
            The thought process data or None if not found
        """
        if not self.db_client:
            self.logger.error("No database client available")
            return None

        query = """
        SELECT
            id, agent_id, timestamp, context,
            thought_steps, reasoning_path, conclusion,
            related_task_id, related_files, metadata, tags
        FROM thought_processes
        WHERE id = $1
        """

        result = await self.db_client.fetch_one(query, thought_id)

        if not result:
            return None

        return {
            "id": str(result["id"]),
            "agent_id": result["agent_id"],
            "timestamp": result["timestamp"],
            "context": result["context"],
            "thought_steps": json.loads(result["thought_steps"]),
            "reasoning_path": result["reasoning_path"],
            "conclusion": result["conclusion"],
            "related_task_id": result["related_task_id"],
            "related_files": result["related_files"],
            "metadata": json.loads(result["metadata"]) if result["metadata"] else {},
            "tags": result["tags"] or []
        }

    async def search_thoughts(
        self,
        query: str,
        agent_id: Optional[str] = None,
        related_task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for thought processes using semantic search.

        Args:
            query: Natural language query to search for
            agent_id: Optional filter by agent ID
            related_task_id: Optional filter by related task ID
            tags: Optional filter by tags
            limit: Maximum number of results to return

        Returns:
            List of matching thought processes
        """
        if not self.vector_memory or not self.llm_provider:
            self.logger.error("Vector memory or LLM provider not available")
            return []

        # Generate embedding for the query
        try:
            query_embedding = await self.llm_provider.generate_embeddings(query)
        except Exception as e:
            self.logger.error(f"Error generating embedding: {str(e)}")
            return []

        # Prepare metadata filter
        metadata_filter = {}
        if agent_id:
            metadata_filter["agent_id"] = agent_id
        if related_task_id:
            metadata_filter["related_task_id"] = related_task_id

        # Search for similar thought processes
        similar_thoughts = await self.vector_memory.search_similar(
            query_embedding=query_embedding,
            entity_types=["ThoughtProcess"],
            tags=tags,
            metadata_filter=metadata_filter,
            limit=limit
        )

        # Fetch full thought process data for each result
        results = []
        for thought in similar_thoughts:
            full_thought = await self.get_thought_process(thought["entity_id"])
            if full_thought:
                full_thought["similarity"] = thought["similarity"]
                results.append(full_thought)

        self.logger.debug(f"Found {len(results)} thought processes for query: {query[:50]}...")
        return results
```

## Post-Implementation Verification

After completing all tasks, verify the implementation by:

1. Testing the enhanced vector memory with different entity types and relationships
2. Verifying that the search_memory() function can retrieve relevant information across content types
3. Testing the thought process capture and retrieval functionality
4. Creating and querying relationships between entities
5. Checking that vector embeddings are correctly stored and can be used for semantic search

This phase establishes a robust shared knowledge base that enables agents to maintain context and find relevant information efficiently, which is essential for building cohesive, complex applications.
