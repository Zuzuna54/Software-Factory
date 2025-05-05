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

    # Match the dimension specified in project overview and used by the embedding model
    EMBEDDING_DIM = 3072

    def __init__(self, db_client: PostgresClient):
        if db_client is None:
            raise ValueError(
                "PostgresClient instance is required for EnhancedVectorMemory."
            )
        self.db_client = db_client
        self.logger = logging.getLogger("agent.memory.enhanced_vector")
        self.entity_types = {}  # Registry of entity types and their schemas
        # Defer initialization until called
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the vector memory tables if they don't exist idempotently."""
        async with self._init_lock:
            if self._initialized:
                self.logger.debug("EnhancedVectorMemory already initialized.")
                return

            self.logger.info("Initializing EnhancedVectorMemory system...")
            try:
                # Ensure pgvector extension is available
                await self.db_client.execute("CREATE EXTENSION IF NOT EXISTS pgvector;")

                # Create enhanced vector storage table (uses schema.sql definition)
                # No need to run CREATE TABLE here as schema.sql handles it.
                # We verify required indexes exist.

                # Create indexes for faster similarity search (idempotent)
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

                # Use HNSW index type and halfvec operator class for high-dimensional halfvec
                await self.db_client.execute(
                    f"""
                CREATE INDEX IF NOT EXISTS idx_enhanced_vector_embedding
                ON enhanced_vector_storage USING hnsw (embedding halfvec_cosine_ops);
                """
                )

                # Create indexes for vector relationships (idempotent)
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

                self._initialized = True
                self.logger.info(
                    "Enhanced vector memory system initialized successfully."
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to initialize EnhancedVectorMemory: {e}", exc_info=True
                )
                raise  # Propagate the error

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()
        if not self._initialized:
            raise RuntimeError("EnhancedVectorMemory failed to initialize.")

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
    ) -> Optional[str]:
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
            The internal UUID of the stored record, or None on failure.
        """
        await self._ensure_initialized()

        if len(embedding) != self.EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension mismatch. Expected {self.EMBEDDING_DIM}, got {len(embedding)}."
            )

        query = f"""
        INSERT INTO enhanced_vector_storage (
            entity_type, entity_id, embedding, content,
            metadata, tags, updated_at
        )
        VALUES ($1, $2, $3::halfvec({self.EMBEDDING_DIM}), $4, $5, $6, NOW())
        ON CONFLICT (entity_type, entity_id)
        DO UPDATE SET
            embedding = EXCLUDED.embedding,
            content = EXCLUDED.content,
            metadata = EXCLUDED.metadata,
            tags = EXCLUDED.tags,
            updated_at = NOW()
        RETURNING id
        """

        try:
            # Convert the embedding list to its string representation
            embedding_str = str(embedding)

            result = await self.db_client.fetch_one(
                query,
                entity_type,
                entity_id,
                embedding_str,
                content,
                json.dumps(metadata or {}),
                tags or [],
            )

            if result:
                self.logger.debug(f"Stored/Updated entity {entity_type}:{entity_id}")
                return str(result["id"])
            else:
                self.logger.error(
                    f"Failed to store/update entity {entity_type}:{entity_id} - no ID returned."
                )
                return None
        except Exception as e:
            self.logger.error(
                f"Error storing entity {entity_type}:{entity_id}: {e}",
                exc_info=True,
            )
            raise

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
            metadata_filter: Optional metadata conditions to filter by (exact match on top-level keys)
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold (0-1)

        Returns:
            List of matching entities with similarity scores
        """
        await self._ensure_initialized()

        if len(query_embedding) != self.EMBEDDING_DIM:
            raise ValueError(
                f"Query embedding dimension mismatch. Expected {self.EMBEDDING_DIM}, got {len(query_embedding)}."
            )

        # Build the query conditions
        conditions = [f"1 - (embedding <=> $1::halfvec({self.EMBEDDING_DIM})) > $2"]
        params: List[Any] = [str(query_embedding), threshold]
        param_idx = 3

        if entity_types:
            placeholders = ", ".join(
                f"${param_idx + i}" for i in range(len(entity_types))
            )
            conditions.append(f"entity_type IN ({placeholders})")
            params.extend(entity_types)
            param_idx += len(entity_types)

        if tags:
            # Filter entities that have all specified tags
            conditions.append(
                f"tags @> ${param_idx}"
            )  # Using array containment operator
            params.append(tags)
            param_idx += 1

        if metadata_filter:
            # Simple top-level key exact match for now
            # More complex filtering (nested keys, operators) would require more logic
            conditions.append(f"metadata @> ${param_idx}")
            params.append(json.dumps(metadata_filter))
            param_idx += 1

        # Build the final query
        query = f"""
        SELECT
            id, entity_type, entity_id, content,
            metadata, tags, created_at, updated_at,
            1 - (embedding <=> $1::halfvec({self.EMBEDDING_DIM})) AS similarity
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

            self.logger.debug(
                f"Found {len(entities)} similar entities via search_similar"
            )
            return entities

        except Exception as e:
            self.logger.error(f"Error during similarity search: {e}", exc_info=True)
            return []  # Return empty list on error

    async def create_relationship(
        self,
        source_entity_type: str,
        source_entity_id: str,
        target_entity_type: str,
        target_entity_id: str,
        relationship_type: str,
        metadata: Dict[str, Any] = None,
    ) -> Optional[str]:
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
            The relationship ID (UUID as string) or None on failure.
        """
        await self._ensure_initialized()
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
        try:
            result = await self.db_client.fetch_one(
                query,
                source_entity_type,
                source_entity_id,
                target_entity_type,
                target_entity_id,
                relationship_type,
                json.dumps(metadata or {}),
            )

            if result:
                self.logger.debug(
                    f"Created/Updated relationship {relationship_type} from {source_entity_type}:{source_entity_id} "
                    f"to {target_entity_type}:{target_entity_id}"
                )
                return str(result["id"])
            else:
                self.logger.error(
                    f"Failed to create/update relationship {relationship_type} - no ID returned."
                )
                return None
        except Exception as e:
            self.logger.error(
                f"Error creating relationship {relationship_type}: {e}",
                exc_info=True,
            )
            raise

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
        Get entities related to the specified entity, including their details.

        Args:
            entity_type: Type of the entity
            entity_id: ID of the entity
            relationship_types: Optional list of relationship types to filter by
            target_entity_types: Optional list of related entity types to filter by
            as_source: Include relationships where the entity is the source
            as_target: Include relationships where the entity is the target
            limit: Maximum number of results to return

        Returns:
            List of related entities with relationship and entity details
        """
        await self._ensure_initialized()
        if not as_source and not as_target:
            self.logger.warning(
                "Both as_source and as_target are False, returning empty list"
            )
            return []

        # Parameters will be built dynamically
        query_params: List[Any] = []
        param_idx = 1
        union_parts: List[str] = []

        # --- Query for outgoing relationships (entity is source) ---
        if as_source:
            source_conditions = [
                f"r.source_entity_type = ${param_idx}",
                f"r.source_entity_id = ${param_idx+1}",
            ]
            query_params.extend([entity_type, entity_id])
            current_idx = param_idx + 2

            if relationship_types:
                placeholders = ", ".join(
                    f"${current_idx + i}" for i in range(len(relationship_types))
                )
                source_conditions.append(f"r.relationship_type IN ({placeholders})")
                query_params.extend(relationship_types)
                current_idx += len(relationship_types)

            if target_entity_types:
                placeholders = ", ".join(
                    f"${current_idx + i}" for i in range(len(target_entity_types))
                )
                source_conditions.append(f"r.target_entity_type IN ({placeholders})")
                query_params.extend(target_entity_types)
                current_idx += len(target_entity_types)

            source_query = f"""
            SELECT
                r.id AS relationship_id, r.relationship_type, r.metadata AS relationship_metadata,
                'outgoing' AS direction,
                r.target_entity_type AS related_entity_type,
                r.target_entity_id AS related_entity_id,
                e.id AS entity_internal_id, e.content, e.metadata AS entity_metadata,
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
            union_parts.append(source_query)
            param_idx = current_idx  # Update param index for the next part

        # --- Query for incoming relationships (entity is target) ---
        if as_target:
            target_conditions = [
                f"r.target_entity_type = ${param_idx}",
                f"r.target_entity_id = ${param_idx+1}",
            ]
            query_params.extend([entity_type, entity_id])
            current_idx = param_idx + 2

            if relationship_types:
                placeholders = ", ".join(
                    f"${current_idx + i}" for i in range(len(relationship_types))
                )
                target_conditions.append(f"r.relationship_type IN ({placeholders})")
                query_params.extend(relationship_types)
                current_idx += len(relationship_types)

            # Note: target_entity_types filter applies to the *source* when looking at incoming relationships
            if target_entity_types:
                placeholders = ", ".join(
                    f"${current_idx + i}" for i in range(len(target_entity_types))
                )
                target_conditions.append(f"r.source_entity_type IN ({placeholders})")
                query_params.extend(target_entity_types)
                current_idx += len(target_entity_types)

            target_query = f"""
            SELECT
                r.id AS relationship_id, r.relationship_type, r.metadata AS relationship_metadata,
                'incoming' AS direction,
                r.source_entity_type AS related_entity_type,
                r.source_entity_id AS related_entity_id,
                e.id AS entity_internal_id, e.content, e.metadata AS entity_metadata,
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
            union_parts.append(target_query)
            param_idx = current_idx  # Update param index for the final limit

        # Combine the queries if needed
        if not union_parts:
            return []  # Should not happen if logic above is correct

        combined_query = " UNION ALL ".join(union_parts)
        # Add final limit
        combined_query += f" LIMIT ${param_idx}"
        query_params.append(limit)

        try:
            results = await self.db_client.fetch_all(combined_query, *query_params)

            relationships = []
            for row in results:
                relationships.append(
                    {
                        "relationship_id": str(row["relationship_id"]),
                        "relationship_type": row["relationship_type"],
                        "direction": row["direction"],
                        "related_entity": {
                            "internal_id": (
                                str(row["entity_internal_id"])
                                if row["entity_internal_id"]
                                else None
                            ),
                            "entity_type": row["related_entity_type"],
                            "entity_id": row["related_entity_id"],
                            "content": row["content"],
                            "metadata": (
                                json.loads(row["entity_metadata"])
                                if row["entity_metadata"]
                                else {}
                            ),
                            "tags": row["tags"] or [],
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                        },
                        "relationship_metadata": (
                            json.loads(row["relationship_metadata"])
                            if row["relationship_metadata"]
                            else {}
                        ),
                    }
                )

            self.logger.debug(
                f"Found {len(relationships)} relationships for {entity_type}:{entity_id}"
            )
            return relationships

        except Exception as e:
            self.logger.error(
                f"Error getting related entities for {entity_type}:{entity_id}: {e}",
                exc_info=True,
            )
            return []  # Return empty list on error
