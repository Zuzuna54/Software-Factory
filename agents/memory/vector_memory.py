# agents/memory/vector_memory.py

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

from ..db.postgres import PostgresClient

logger = logging.getLogger(__name__)


class VectorMemory:
    """Vector-based memory system for semantic search using pgvector (Iteration 1 Version)."""

    # Assuming a fixed embedding dimension based on the blueprint
    EMBEDDING_DIM = 1536

    def __init__(self, db_client: PostgresClient):
        if db_client is None:
            raise ValueError("PostgresClient instance is required for VectorMemory.")
        self.db_client = db_client
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the vector memory tables if they don't exist idempotently."""
        async with self._init_lock:
            if self._initialized:
                logger.debug("VectorMemory already initialized.")
                return

            logger.info("Initializing VectorMemory system...")
            try:
                # Ensure pgvector extension is available (idempotent)
                await self.db_client.execute("CREATE EXTENSION IF NOT EXISTS pgvector;")

                # Create vector_embeddings table (if not exists)
                # This schema matches the one in iteration_1.md
                await self.db_client.execute(
                    f"""
                CREATE TABLE IF NOT EXISTS vector_embeddings (
                    id SERIAL PRIMARY KEY,
                    entity_type VARCHAR(50) NOT NULL,
                    entity_id VARCHAR(255) NOT NULL,
                    embedding VECTOR({self.EMBEDDING_DIM}) NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(entity_type, entity_id)
                );
                """
                )

                # Create index for faster similarity search (if not exists)
                # Using cosine distance as it's common for semantic similarity
                await self.db_client.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_vector_embeddings_cosine ON vector_embeddings
                USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
                """
                )

                # Create index for entity type and ID for faster lookups/updates
                await self.db_client.execute(
                    """
                CREATE INDEX IF NOT EXISTS idx_vector_embeddings_entity ON vector_embeddings(entity_type, entity_id);
                """
                )

                self._initialized = True
                logger.info("VectorMemory system initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize VectorMemory: {e}", exc_info=True)
                raise  # Propagate the error

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()
        if not self._initialized:
            raise RuntimeError("VectorMemory failed to initialize.")

    async def store_embedding(
        self,
        entity_type: str,
        entity_id: str,
        embedding: List[float],
        metadata: Dict[str, Any] = None,
    ) -> None:
        """Store or update an embedding vector for an entity."""
        await self._ensure_initialized()

        if len(embedding) != self.EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dimension mismatch. Expected {self.EMBEDDING_DIM}, got {len(embedding)}."
            )

        query = f"""
        INSERT INTO vector_embeddings (entity_type, entity_id, embedding, metadata)
        VALUES ($1, $2, $3::vector({self.EMBEDDING_DIM}), $4)
        ON CONFLICT (entity_type, entity_id)
        DO UPDATE SET
            embedding = EXCLUDED.embedding,
            metadata = EXCLUDED.metadata,
            created_at = NOW() # Update timestamp on conflict as well
        """

        try:
            await self.db_client.execute(
                query, entity_type, entity_id, embedding, json.dumps(metadata or {})
            )
            logger.debug(f"Stored/Updated embedding for {entity_type}:{entity_id}")
        except Exception as e:
            logger.error(
                f"Error storing embedding for {entity_type}:{entity_id}: {e}",
                exc_info=True,
            )
            raise

    async def search_similar(
        self,
        entity_type: str,
        query_embedding: List[float],
        threshold: float = 0.7,  # Cosine similarity threshold
        limit: int = 10,
    ) -> List[str]:
        """Search for entities similar to the query embedding within a specific type."""
        await self._ensure_initialized()

        if len(query_embedding) != self.EMBEDDING_DIM:
            raise ValueError(
                f"Query embedding dimension mismatch. Expected {self.EMBEDDING_DIM}, got {len(query_embedding)}."
            )

        # Using cosine similarity: 1 - (embedding <=> query) > threshold
        # <=> operator calculates cosine distance (0=identical, 1=orthogonal, 2=opposite)
        # So similarity = 1 - distance
        query = f"""
        SELECT
            entity_id
        FROM
            vector_embeddings
        WHERE
            entity_type = $2
            AND 1 - (embedding <=> $1::vector({self.EMBEDDING_DIM})) > $3
        ORDER BY
            embedding <=> $1::vector({self.EMBEDDING_DIM}) ASC -- Order by distance (ascending) which is similarity (descending)
        LIMIT $4
        """

        try:
            results = await self.db_client.fetch_all(
                query, query_embedding, entity_type, threshold, limit
            )
            entity_ids = [row["entity_id"] for row in results]
            logger.debug(
                f"Found {len(entity_ids)} similar entities of type '{entity_type}'"
            )
            return entity_ids
        except Exception as e:
            logger.error(
                f"Error searching similar embeddings for type '{entity_type}': {e}",
                exc_info=True,
            )
            raise

    async def get_embedding(
        self, entity_type: str, entity_id: str
    ) -> Optional[List[float]]:
        """Retrieve the embedding for a specific entity."""
        await self._ensure_initialized()
        query = """
        SELECT embedding
        FROM vector_embeddings
        WHERE entity_type = $1 AND entity_id = $2
        """
        try:
            result = await self.db_client.fetch_one(query, entity_type, entity_id)
            if result and result["embedding"]:
                # asyncpg returns vector as string '[1.0,2.0,...]', need to parse
                embedding_str = result["embedding"]
                return json.loads(embedding_str)
            return None
        except Exception as e:
            logger.error(
                f"Error retrieving embedding for {entity_type}:{entity_id}: {e}",
                exc_info=True,
            )
            raise

    async def delete_embedding(self, entity_type: str, entity_id: str) -> bool:
        """Delete an embedding from the vector memory."""
        await self._ensure_initialized()
        query = """
        DELETE FROM vector_embeddings
        WHERE entity_type = $1 AND entity_id = $2
        RETURNING id
        """
        try:
            result = await self.db_client.fetch_one(query, entity_type, entity_id)
            success = result is not None
            if success:
                logger.debug(f"Deleted embedding for {entity_type}:{entity_id}")
            else:
                logger.warning(
                    f"Embedding for {entity_type}:{entity_id} not found for deletion"
                )
            return success
        except Exception as e:
            logger.error(
                f"Error deleting embedding for {entity_type}:{entity_id}: {e}",
                exc_info=True,
            )
            raise

    async def list_entity_types(self) -> List[str]:
        """List all distinct entity types stored in the vector memory."""
        await self._ensure_initialized()
        query = (
            "SELECT DISTINCT entity_type FROM vector_embeddings ORDER BY entity_type;"
        )
        try:
            results = await self.db_client.fetch_all(query)
            return [row["entity_type"] for row in results]
        except Exception as e:
            logger.error(f"Error listing entity types: {e}", exc_info=True)
            raise

    async def count_embeddings(self, entity_type: Optional[str] = None) -> int:
        """Count the number of embeddings, optionally filtered by entity type."""
        await self._ensure_initialized()
        try:
            if entity_type:
                query = "SELECT COUNT(*) as count FROM vector_embeddings WHERE entity_type = $1"
                result = await self.db_client.fetch_one(query, entity_type)
            else:
                query = "SELECT COUNT(*) as count FROM vector_embeddings"
                result = await self.db_client.fetch_one(query)
            return result["count"] if result else 0
        except Exception as e:
            logger.error(
                f"Error counting embeddings (type: {entity_type}): {e}", exc_info=True
            )
            raise
