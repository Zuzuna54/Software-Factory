"""
Vector-based memory system for semantic storage and retrieval.
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import select, insert, delete, update, text, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import or_, and_
from pgvector.sqlalchemy import Vector

from infra.db.models import Artifact
from agents.llm import LLMProvider

logger = logging.getLogger(__name__)

# Constants for memory management
DEFAULT_CHUNK_SIZE = 1000  # characters per chunk
DEFAULT_CONTEXT_WINDOW_SIZE = 10  # number of items in context window
DEFAULT_SIMILARITY_THRESHOLD = 0.75  # cosine similarity threshold


class MemoryItem:
    """Represents an item in the agent's memory."""

    def __init__(
        self,
        content: str,
        artifact_id: Optional[uuid.UUID] = None,
        content_type: str = "text",
        category: str = "general",
        tags: List[str] = None,
        importance: float = 0.5,
        created_at: Optional[datetime] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a memory item.

        Args:
            content: The text content of the memory
            artifact_id: Optional ID of an existing artifact this memory is related to
            content_type: Type of content (e.g., 'text', 'code', 'image_description')
            category: Category for organizing memories (e.g., 'conversation', 'knowledge')
            tags: List of tags for filtering and retrieval
            importance: A value from 0 to 1 indicating importance (higher = more important)
            created_at: When this memory was created
            embedding: Vector embedding of the content if already computed
            metadata: Additional metadata associated with this memory
        """
        self.content = content
        self.artifact_id = artifact_id
        self.content_type = content_type
        self.category = category
        self.tags = tags or []
        self.importance = importance
        self.created_at = created_at or datetime.utcnow()
        self.embedding = embedding
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory item to dictionary."""
        return {
            "content": self.content,
            "artifact_id": str(self.artifact_id) if self.artifact_id else None,
            "content_type": self.content_type,
            "category": self.category,
            "tags": self.tags,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        """Create memory item from dictionary."""
        artifact_id = data.get("artifact_id")
        if artifact_id and isinstance(artifact_id, str):
            artifact_id = uuid.UUID(artifact_id)

        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            content=data["content"],
            artifact_id=artifact_id,
            content_type=data.get("content_type", "text"),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            importance=data.get("importance", 0.5),
            created_at=created_at,
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_artifact(cls, artifact: Any) -> "MemoryItem":
        """Create memory item from an artifact object."""
        return cls(
            content=artifact.content,
            artifact_id=(
                artifact.artifact_id
                if hasattr(artifact, "artifact_id")
                else artifact.id
            ),
            content_type="artifact",
            category=artifact.artifact_type,
            tags=[],  # Could extract tags from artifact.extra_data if defined
            importance=0.8,  # Artifacts tend to be important by default
            created_at=artifact.created_at,
            embedding=None,  # Will be filled in later if available
            metadata={
                "title": (
                    artifact.title if hasattr(artifact, "title") else artifact.name
                ),
                "version": getattr(artifact, "version", 1),
                "status": getattr(artifact, "status", "active"),
            },
        )


class VectorMemory:
    """
    Vector-based memory system for semantic storage and retrieval.

    Features:
    - Store text with associated vector embeddings
    - Semantic search for similar content
    - Categorization and indexing for efficient retrieval
    - Context window management to maintain relevant information
    """

    def __init__(
        self,
        db_session: AsyncSession,
        llm_provider: LLMProvider,
        agent_id: Optional[uuid.UUID] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        context_window_size: int = DEFAULT_CONTEXT_WINDOW_SIZE,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        """
        Initialize the vector memory system.

        Args:
            db_session: Database session for storage and retrieval
            llm_provider: LLM provider for generating embeddings
            agent_id: Optional ID of the agent this memory belongs to
            chunk_size: Maximum characters per memory chunk
            context_window_size: Number of items in context window
            similarity_threshold: Minimum similarity score for matches
        """
        self.db_session = db_session
        self.llm_provider = llm_provider
        self.agent_id = agent_id
        self.chunk_size = chunk_size
        self.context_window_size = context_window_size
        self.similarity_threshold = similarity_threshold

        # In-memory context window for recently accessed items
        self.context_window: List[MemoryItem] = []

        # Cache for frequently accessed items to reduce database load
        self.cache: Dict[uuid.UUID, MemoryItem] = {}

        # Initialize logger
        self.logger = logging.getLogger(f"{__name__}.VectorMemory")

    async def store(
        self,
        items: Union[MemoryItem, List[MemoryItem]],
        generate_embeddings: bool = True,
        update_if_exists: bool = True,
    ) -> List[uuid.UUID]:
        """
        Store one or more memory items.

        Args:
            items: A single memory item or list of items to store
            generate_embeddings: Whether to generate embeddings for the items
            update_if_exists: Whether to update existing items if they exist

        Returns:
            List of artifact IDs for the stored items
        """
        if isinstance(items, MemoryItem):
            items = [items]

        # Generate embeddings if requested and not already present
        if generate_embeddings:
            items_to_embed = [item for item in items if item.embedding is None]
            if items_to_embed:
                await self._generate_embeddings(items_to_embed)

        artifact_ids = []

        for item in items:
            try:
                # Check if item is related to an existing artifact
                if item.artifact_id:
                    # Update existing artifact if update_if_exists is True
                    if update_if_exists:
                        await self._update_artifact(item)
                    artifact_ids.append(item.artifact_id)

                    # Update cache
                    self.cache[item.artifact_id] = item
                else:
                    # Create new artifact
                    artifact_id = await self._create_artifact(item)
                    artifact_ids.append(artifact_id)

                    # Update the item with the new artifact_id
                    item.artifact_id = artifact_id

                    # Update cache
                    self.cache[artifact_id] = item

                # Update context window
                self._update_context_window(item)
            except Exception as e:
                self.logger.error(f"Error storing memory item: {str(e)}")
                # Continue storing other items even if one fails

        return artifact_ids

    async def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        limit: int = 5,
        include_context: bool = True,
    ) -> List[MemoryItem]:
        """
        Retrieve memory items similar to the query.

        Args:
            query: Text query for semantic search
            category: Optional category filter
            tags: Optional list of tags to filter by
            time_range: Optional tuple of (start_time, end_time) to filter by creation time
            limit: Maximum number of results to return
            include_context: Whether to include context window items in the search

        Returns:
            List of memory items matching the query, ranked by relevance
        """
        # Generate embedding for query
        embedding, _ = await self._get_embedding(query)

        # First search context window for matches
        context_matches = []
        if include_context and self.context_window:
            context_matches = self._search_context_window(embedding, category, tags)

        # Prepare query for database search
        query_items = []

        # Start with base query
        base_query = select(Artifact)

        # Add filter conditions
        if category:
            base_query = base_query.where(Artifact.artifact_type == category)

        if time_range:
            start_time, end_time = time_range
            base_query = base_query.where(
                and_(Artifact.created_at >= start_time, Artifact.created_at <= end_time)
            )

        # Add embedding similarity calculation
        # Note: pgvector supports special operators for this (<#> for cosine distance)
        pgvector_embedding = self._list_to_pgvector(embedding)
        similarity_query = base_query.order_by(
            Artifact.content_vector.cosine_distance(pgvector_embedding)
        ).limit(limit)

        # Execute query
        try:
            result = await self.db_session.execute(similarity_query)
            db_artifacts = result.scalars().all()

            # Convert to memory items and calculate similarity
            db_matches = []
            for artifact in db_artifacts:
                memory_item = MemoryItem.from_artifact(artifact)

                # Get embedding from artifact
                if (
                    hasattr(artifact, "content_vector")
                    and artifact.content_vector is not None
                ):
                    memory_item.embedding = list(artifact.content_vector)

                # Add to context window
                self._update_context_window(memory_item)

                # Add to cache
                artifact_id = (
                    artifact.artifact_id
                    if hasattr(artifact, "artifact_id")
                    else artifact.id
                )
                self.cache[artifact_id] = memory_item

                db_matches.append(memory_item)

            # Combine and deduplicate results
            all_matches = []
            artifact_ids_seen = set()

            # First add context matches
            for item in context_matches:
                if item.artifact_id not in artifact_ids_seen:
                    all_matches.append(item)
                    artifact_ids_seen.add(item.artifact_id)

            # Then add database matches
            for item in db_matches:
                if item.artifact_id not in artifact_ids_seen:
                    all_matches.append(item)
                    artifact_ids_seen.add(item.artifact_id)

            # Sort by similarity (approximate by order in results)
            return all_matches[:limit]
        except Exception as e:
            self.logger.error(f"Error in semantic search: {str(e)}")
            return context_matches[:limit]  # Return context matches as fallback

    async def retrieve_by_id(self, artifact_id: uuid.UUID) -> Optional[MemoryItem]:
        """
        Retrieve a specific memory item by its artifact ID.

        Args:
            artifact_id: The ID of the artifact to retrieve

        Returns:
            The memory item if found, None otherwise
        """
        # Check cache first
        if artifact_id in self.cache:
            item = self.cache[artifact_id]
            self._update_context_window(item)
            return item

        # Query database
        try:
            query = select(Artifact).where(
                or_(Artifact.artifact_id == artifact_id, Artifact.id == artifact_id)
            )
            result = await self.db_session.execute(query)
            artifact = result.scalar_one_or_none()

            if artifact:
                # Convert to memory item
                memory_item = MemoryItem.from_artifact(artifact)

                # Get embedding from artifact
                if (
                    hasattr(artifact, "content_vector")
                    and artifact.content_vector is not None
                ):
                    memory_item.embedding = list(artifact.content_vector)

                # Update context window
                self._update_context_window(memory_item)

                # Update cache
                self.cache[artifact_id] = memory_item

                return memory_item
            return None
        except Exception as e:
            self.logger.error(f"Error retrieving by ID: {str(e)}")
            return None

    async def delete(self, artifact_id: uuid.UUID) -> bool:
        """
        Delete a memory item.

        Args:
            artifact_id: The ID of the artifact to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Delete from database
            query = delete(Artifact).where(
                or_(Artifact.artifact_id == artifact_id, Artifact.id == artifact_id)
            )
            await self.db_session.execute(query)
            await self.db_session.commit()

            # Remove from cache
            if artifact_id in self.cache:
                del self.cache[artifact_id]

            # Remove from context window
            self.context_window = [
                item for item in self.context_window if item.artifact_id != artifact_id
            ]

            return True
        except Exception as e:
            self.logger.error(f"Error deleting memory: {str(e)}")
            return False

    def get_context_window(self) -> List[MemoryItem]:
        """
        Get the current context window.

        Returns:
            List of memory items in the context window
        """
        return self.context_window.copy()

    def clear_context_window(self) -> None:
        """Clear the context window."""
        self.context_window.clear()

    def _update_context_window(self, item: MemoryItem) -> None:
        """
        Update the context window with a new item.

        Args:
            item: The memory item to add to the context window
        """
        # Remove item if already in context window
        self.context_window = [
            i for i in self.context_window if i.artifact_id != item.artifact_id
        ]

        # Add item to front of context window
        self.context_window.insert(0, item)

        # Trim context window if needed
        if len(self.context_window) > self.context_window_size:
            self.context_window = self.context_window[: self.context_window_size]

    def _search_context_window(
        self,
        query_embedding: List[float],
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[MemoryItem]:
        """
        Search the context window for matching items.

        Args:
            query_embedding: The embedding vector for the query
            category: Optional category filter
            tags: Optional list of tags to filter by

        Returns:
            List of matching memory items, sorted by similarity
        """
        matches = []

        for item in self.context_window:
            # Apply filters if specified
            if category and item.category != category:
                continue

            if tags and not all(tag in item.tags for tag in tags):
                continue

            # Skip items without embeddings
            if not item.embedding:
                continue

            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_embedding, item.embedding)

            # Include if above threshold
            if similarity >= self.similarity_threshold:
                # Store similarity in metadata for later sorting
                item.metadata["similarity"] = similarity
                matches.append(item)

        # Sort by similarity (descending)
        return sorted(
            matches, key=lambda x: x.metadata.get("similarity", 0), reverse=True
        )

    @staticmethod
    def _cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not vec1 or not vec2:
            return 0.0

        vec1 = np.array(vec1)
        vec2 = np.array(vec2)

        # Handle zero vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    @staticmethod
    def _list_to_pgvector(embedding: List[float]) -> Any:
        """Convert a list of floats to pgvector format."""
        return Vector(embedding)

    async def _generate_embeddings(self, items: List[MemoryItem]) -> None:
        """
        Generate embeddings for memory items.

        Args:
            items: List of memory items to generate embeddings for
        """
        texts = [item.content for item in items]

        try:
            # Generate embeddings using the LLM provider
            embeddings, _ = await self.llm_provider.generate_embeddings(texts)

            # Assign embeddings to items
            for i, item in enumerate(items):
                item.embedding = embeddings[i]

        except Exception as e:
            self.logger.error(f"Error generating embeddings: {str(e)}")
            # Continue without embeddings, they can be generated later

    async def _get_embedding(self, text: str) -> Tuple[List[float], Dict[str, Any]]:
        """
        Get embedding for a single text.

        Args:
            text: The text to generate embedding for

        Returns:
            Tuple of (embedding, metadata)
        """
        try:
            embeddings, metadata = await self.llm_provider.generate_embeddings([text])
            return embeddings[0], metadata
        except Exception as e:
            self.logger.error(f"Error getting embedding: {str(e)}")
            # Return empty embedding as fallback
            return [], {}

    async def _create_artifact(self, item: MemoryItem) -> uuid.UUID:
        """
        Create a new artifact in the database from a memory item.

        Args:
            item: The memory item to create an artifact from

        Returns:
            The ID of the created artifact
        """
        now = datetime.utcnow()
        artifact_id = uuid.uuid4()

        # Prepare data for artifact
        artifact_data = {
            "artifact_id": artifact_id,
            "artifact_type": item.category,
            "title": item.metadata.get("title", item.content[:100]),
            "content": item.content,
            "created_at": now,
            "created_by": self.agent_id,
            "status": item.metadata.get("status", "active"),
            "extra_data": {
                "content_type": item.content_type,
                "tags": item.tags,
                "importance": item.importance,
                "original_timestamp": item.created_at.isoformat(),
                **item.metadata,
            },
            "version": item.metadata.get("version", 1),
            "content_vector": item.embedding,
        }

        # Insert into database
        stmt = insert(Artifact).values(**artifact_data)
        await self.db_session.execute(stmt)
        await self.db_session.commit()

        return artifact_id

    async def _update_artifact(self, item: MemoryItem) -> None:
        """
        Update an existing artifact in the database.

        Args:
            item: The memory item to update the artifact from
        """
        now = datetime.utcnow()

        # Prepare update data
        update_data = {
            "content": item.content,
            "last_modified_at": now,
            "last_modified_by": self.agent_id,
            "extra_data": {
                "content_type": item.content_type,
                "tags": item.tags,
                "importance": item.importance,
                "original_timestamp": item.created_at.isoformat(),
                "last_updated": now.isoformat(),
                **item.metadata,
            },
            "content_vector": item.embedding,
        }

        # Update in database
        stmt = (
            update(Artifact)
            .where(
                or_(
                    Artifact.artifact_id == item.artifact_id,
                    Artifact.id == item.artifact_id,
                )
            )
            .values(**update_data)
        )
        await self.db_session.execute(stmt)
        await self.db_session.commit()

    async def chunk_and_store_text(
        self,
        text: str,
        category: str = "general",
        tags: List[str] = None,
        metadata: Dict[str, Any] = None,
    ) -> List[uuid.UUID]:
        """
        Chunk a long text into smaller pieces and store them.

        Args:
            text: The text to chunk and store
            category: Category for the chunks
            tags: Optional list of tags
            metadata: Optional additional metadata

        Returns:
            List of artifact IDs for the stored chunks
        """
        # Only chunk if text exceeds chunk size
        if len(text) <= self.chunk_size:
            item = MemoryItem(
                content=text,
                category=category,
                tags=tags or [],
                metadata=metadata or {},
            )
            return await self.store(item)

        # Split text into chunks
        chunks = self._chunk_text(text)

        # Create memory items for each chunk
        items = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = {
                "chunk_index": i,
                "total_chunks": len(chunks),
                "original_length": len(text),
                **(metadata or {}),
            }

            item = MemoryItem(
                content=chunk,
                category=category,
                tags=tags or [],
                metadata=chunk_metadata,
            )
            items.append(item)

        # Store all chunks
        return await self.store(items)

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks of approximately equal size.

        Args:
            text: The text to chunk

        Returns:
            List of text chunks
        """
        # Simple chunking by character count
        chunks = []
        for i in range(0, len(text), self.chunk_size):
            chunks.append(text[i : i + self.chunk_size])

        return chunks

    async def retrieve_by_tags(
        self, tags: List[str], match_all: bool = True, limit: int = 10
    ) -> List[MemoryItem]:
        """
        Retrieve memory items by tags.

        Args:
            tags: List of tags to match
            match_all: If True, all tags must match; if False, any tag can match
            limit: Maximum number of results to return

        Returns:
            List of memory items matching the tags
        """
        try:
            # Build query based on tag matching criteria
            query = select(Artifact)

            # Sadly, we can't easily query JSONB arrays in SQLAlchemy directly
            # We'll need to use raw SQL expression for this
            tags_json = str(tags).replace("'", '"')  # Format tags for JSON query

            if match_all:
                # All tags must be contained in the extra_data->tags array
                tag_condition = text(f"extra_data->'tags' @> '{tags_json}'::jsonb")
            else:
                # Any tag must overlap with the extra_data->tags array
                tag_condition = text(f"extra_data->'tags' ?| array{tags_json}")

            query = query.where(tag_condition).limit(limit)

            # Execute query
            result = await self.db_session.execute(query)
            artifacts = result.scalars().all()

            # Convert to memory items
            items = []
            for artifact in artifacts:
                memory_item = MemoryItem.from_artifact(artifact)

                # Update context window and cache
                self._update_context_window(memory_item)
                artifact_id = (
                    artifact.artifact_id
                    if hasattr(artifact, "artifact_id")
                    else artifact.id
                )
                self.cache[artifact_id] = memory_item

                items.append(memory_item)

            return items
        except Exception as e:
            self.logger.error(f"Error retrieving by tags: {str(e)}")
            return []

    async def retrieve_by_category(
        self, category: str, limit: int = 10
    ) -> List[MemoryItem]:
        """
        Retrieve memory items by category.

        Args:
            category: Category to match
            limit: Maximum number of results to return

        Returns:
            List of memory items in the category
        """
        try:
            # Simple query by artifact_type
            query = (
                select(Artifact)
                .where(Artifact.artifact_type == category)
                .order_by(desc(Artifact.created_at))
                .limit(limit)
            )

            # Execute query
            result = await self.db_session.execute(query)
            artifacts = result.scalars().all()

            # Convert to memory items
            items = []
            for artifact in artifacts:
                memory_item = MemoryItem.from_artifact(artifact)

                # Update context window and cache
                self._update_context_window(memory_item)
                artifact_id = (
                    artifact.artifact_id
                    if hasattr(artifact, "artifact_id")
                    else artifact.id
                )
                self.cache[artifact_id] = memory_item

                items.append(memory_item)

            return items
        except Exception as e:
            self.logger.error(f"Error retrieving by category: {str(e)}")
            return []

    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory system.

        Returns:
            Dictionary with memory statistics
        """
        try:
            # Count total artifacts
            count_query = select(func.count()).select_from(Artifact)
            result = await self.db_session.execute(count_query)
            total_count = result.scalar_one()

            # Count by category
            category_query = select(Artifact.artifact_type, func.count()).group_by(
                Artifact.artifact_type
            )
            result = await self.db_session.execute(category_query)
            categories = {category: count for category, count in result.all()}

            # Get oldest and newest
            newest_query = select(func.max(Artifact.created_at)).select_from(Artifact)
            result = await self.db_session.execute(newest_query)
            newest_date = result.scalar_one()

            oldest_query = select(func.min(Artifact.created_at)).select_from(Artifact)
            result = await self.db_session.execute(oldest_query)
            oldest_date = result.scalar_one()

            return {
                "total_memories": total_count,
                "by_category": categories,
                "newest_memory": newest_date.isoformat() if newest_date else None,
                "oldest_memory": oldest_date.isoformat() if oldest_date else None,
                "context_window_size": len(self.context_window),
                "cache_size": len(self.cache),
            }
        except Exception as e:
            self.logger.error(f"Error getting memory stats: {str(e)}")
            return {
                "error": str(e),
                "context_window_size": len(self.context_window),
                "cache_size": len(self.cache),
            }
