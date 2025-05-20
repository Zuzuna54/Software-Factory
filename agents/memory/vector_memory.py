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

from infra.db.models import Artifact
from agents.llm import LLMProvider
from .vector_memory_functions.memory_item import MemoryItem
from .vector_memory_functions.utils import cosine_similarity, list_to_pgvector
from .vector_memory_functions.store import store_logic
from .vector_memory_functions.retrieve import retrieve_logic
from .vector_memory_functions.retrieve_by_id import retrieve_by_id_logic
from .vector_memory_functions.delete import delete_logic
from .vector_memory_functions.chunk_and_store import chunk_and_store_text_logic
from .vector_memory_functions.retrieve_by_tags import retrieve_by_tags_logic
from .vector_memory_functions.retrieve_by_category import retrieve_by_category_logic
from .vector_memory_functions.get_memory_stats import get_memory_stats_logic

logger = logging.getLogger(__name__)

# Constants for memory management
DEFAULT_CHUNK_SIZE = 1000  # characters per chunk
DEFAULT_CONTEXT_WINDOW_SIZE = 10  # number of items in context window
DEFAULT_SIMILARITY_THRESHOLD = 0.75  # cosine similarity threshold


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
        # Type hint for items needs to be accessible here, MemoryItem is imported.
        return await store_logic(self, items, generate_embeddings, update_if_exists)

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
        return await retrieve_logic(
            self, query, category, tags, time_range, limit, include_context
        )

    async def retrieve_by_id(self, artifact_id: uuid.UUID) -> Optional[MemoryItem]:
        """
        Retrieve a specific memory item by its artifact ID.

        Args:
            artifact_id: The ID of the artifact to retrieve

        Returns:
            The memory item if found, None otherwise
        """
        return await retrieve_by_id_logic(self, artifact_id)

    async def delete(self, artifact_id: uuid.UUID) -> bool:
        """
        Delete a memory item.

        Args:
            artifact_id: The ID of the artifact to delete

        Returns:
            True if deletion successful, False otherwise
        """
        return await delete_logic(self, artifact_id)

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

        for item_obj in self.context_window:
            # Apply filters if specified
            if category and item_obj.category != category:
                continue

            if tags and not all(tag in item_obj.tags for tag in tags):
                continue

            # Skip items without embeddings
            if not item_obj.embedding:
                continue

            # Calculate cosine similarity using the utility function
            similarity = cosine_similarity(query_embedding, item_obj.embedding)

            # Include if above threshold
            if similarity >= self.similarity_threshold:
                # Store similarity in metadata for later sorting
                item_obj.metadata["similarity"] = similarity
                matches.append(item_obj)

        # Sort by similarity (descending)
        return sorted(
            matches, key=lambda x: x.metadata.get("similarity", 0), reverse=True
        )

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
        return await chunk_and_store_text_logic(self, text, category, tags, metadata)

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
        return await retrieve_by_tags_logic(self, tags, match_all, limit)

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
        return await retrieve_by_category_logic(self, category, limit)

    async def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the memory system.

        Returns:
            Dictionary with memory statistics
        """
        return await get_memory_stats_logic(self)
