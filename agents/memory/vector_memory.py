# agents/memory/vector_memory.py

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
        await self.db_client.execute(
            """
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
        """
        )

        # Create vector relationships table
        await self.db_client.execute(
            """
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
        """
        )

        # Create indexes for faster similarity search
        await self.db_client.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_enhanced_vector_entity_type
        ON enhanced_vector_storage(entity_type);
        """
        )

        await self.db_client.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_enhanced_vector_tags
        ON enhanced_vector_storage USING GIN(tags);
        """
        )

        await self.db_client.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_enhanced_vector_embedding
        ON enhanced_vector_storage USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        """
        )

        await self.db_client.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_vector_relationships_source
        ON vector_relationships(source_entity_type, source_entity_id);
        """
        )

        await self.db_client.execute(
            """
        CREATE INDEX IF NOT EXISTS idx_vector_relationships_target
        ON vector_relationships(target_entity_type, target_entity_id);
        """
        )

        self.logger.info("Enhanced vector memory system initialized")

    def register_entity_type(
        self,
        entity_type: str,
        schema: Dict[str, Any],
        content_extractor: Optional[Callable] = None,
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
            "content_extractor": content_extractor,
        }

        self.logger.info(f"Registered entity type: {entity_type}")

    async def store_entity(
        self,
        entity_type: str,
        entity_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any] = None,
        tags: List[str] = None,
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
            tags or [],
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
        threshold: float = 0.7,
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
            placeholders = ", ".join(
                f"${param_idx + i}" for i in range(len(entity_types))
            )
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
                entities.append(
                    {
                        "id": str(row["id"]),
                        "entity_type": row["entity_type"],
                        "entity_id": row["entity_id"],
                        "content": row["content"],
                        "metadata": (
                            json.loads(row["metadata"]) if row["metadata"] else {}
                        ),
                        "tags": row["tags"] or [],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                        "similarity": float(row["similarity"]),
                    }
                )

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
        metadata: Dict[str, Any] = None,
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
            json.dumps(metadata or {}),
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
        limit: int = 100,
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
            self.logger.warning(
                "Both as_source and as_target are False, returning empty list"
            )
            return []

        # Prepare query parts for both directions
        queries = []
        query_params = []
        param_idx = 1

        if as_source:
            source_conditions = [
                f"source_entity_type = ${param_idx}",
                f"source_entity_id = ${param_idx+1}",
            ]
            query_params.extend([entity_type, entity_id])
            param_idx += 2

            if relationship_types:
                placeholders = ", ".join(
                    f"${param_idx + i}" for i in range(len(relationship_types))
                )
                source_conditions.append(f"relationship_type IN ({placeholders})")
                query_params.extend(relationship_types)
                param_idx += len(relationship_types)

            if target_entity_types:
                placeholders = ", ".join(
                    f"${param_idx + i}" for i in range(len(target_entity_types))
                )
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
            target_conditions = [
                f"target_entity_type = ${param_idx}",
                f"target_entity_id = ${param_idx+1}",
            ]
            query_params.extend([entity_type, entity_id])
            param_idx += 2

            if relationship_types:
                placeholders = ", ".join(
                    f"${param_idx + i}" for i in range(len(relationship_types))
                )
                target_conditions.append(f"relationship_type IN ({placeholders})")
                query_params.extend(relationship_types)
                param_idx += len(relationship_types)

            if target_entity_types:
                placeholders = ", ".join(
                    f"${param_idx + i}" for i in range(len(target_entity_types))
                )
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
                relationships.append(
                    {
                        "id": str(row["id"]),
                        "relationship_type": row["relationship_type"],
                        "direction": row["direction"],
                        "related_entity_type": row["related_entity_type"],
                        "related_entity_id": row["related_entity_id"],
                        "metadata": (
                            json.loads(row["metadata"]) if row["metadata"] else {}
                        ),
                        "content": row["content"],
                        "entity_metadata": (
                            json.loads(row["entity_metadata"])
                            if row["entity_metadata"]
                            else {}
                        ),
                        "tags": row["tags"] or [],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"],
                    }
                )

            self.logger.debug(
                f"Found {len(relationships)} relationships for {entity_type}:{entity_id}"
            )
            return relationships

        except Exception as e:
            self.logger.error(f"Error getting related entities: {str(e)}")
            return []
