import logging
from typing import List, Optional, Tuple, Any
from datetime import datetime

from sqlalchemy import select, desc, and_
from infra.db.models import Artifact  # Assuming direct import

# MemoryItem will be imported in the main vector_memory.py and accessible via agent parameter
# from .memory_item import MemoryItem

logger = logging.getLogger(__name__)


async def retrieve_logic(
    agent: Any,  # Represents the VectorMemory instance
    query: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    time_range: Optional[Tuple[datetime, datetime]] = None,
    limit: int = 5,
    include_context: bool = True,  # This parameter is not used in the current simplified logic
) -> List["MemoryItem"]:
    """
    Retrieve memory items similar to the query.
    Args:
        agent: The VectorMemory instance.
        query: Text query for semantic search (currently not used for semantic match).
        category: Optional category filter.
        tags: Optional list of tags to filter by (currently only used for cache check).
        time_range: Optional tuple of (start_time, end_time) to filter by creation time.
        limit: Maximum number of results to return.
        include_context: Whether to include context window items in the search.
    Returns:
        List of memory items matching the criteria.
    """
    logger.info(
        f"Retrieving items with query: '{query}', category: {category}, tags: {tags}"
    )

    # Cache check (simplified from original)
    if agent.cache:
        cache_matches = []
        for (
            artifact_id,
            memory_item_obj,
        ) in agent.cache.items():  # memory_item_obj to avoid conflict
            if category and memory_item_obj.category != category:
                continue
            if tags and not all(tag in memory_item_obj.tags for tag in tags):
                continue
            cache_matches.append(memory_item_obj)

        if cache_matches:
            logger.info(f"Found {len(cache_matches)} matches in cache")
            # The original code did not call _update_context_window for cache hits here.
            # Adding it for consistency if desired, or assuming cache items are already managed regarding context window.
            # for match_item in cache_matches[:limit]:
            #     agent._update_context_window(match_item)
            return cache_matches[:limit]

    logger.info(
        "No cache matches found or tags didn't match, performing database search"
    )

    try:
        # Import MemoryItem class here as it's used for from_artifact
        from agents.memory.vector_memory_functions.memory_item import MemoryItem

        base_db_query = select(Artifact)
        if category:
            base_db_query = base_db_query.where(Artifact.artifact_type == category)
        if time_range:
            start_time, end_time = time_range
            base_db_query = base_db_query.where(
                and_(
                    Artifact.created_at >= start_time,
                    Artifact.created_at <= end_time,
                )
            )
        # Note: The original DB query in retrieve didn't filter by tags, only cache did.
        # If DB query should also filter by tags, that logic needs to be added here.

        base_db_query = base_db_query.order_by(desc(Artifact.created_at)).limit(limit)

        result = await agent.db_session.execute(base_db_query)
        artifacts = result.scalars().all()

        items_list = []  # Renamed from items to items_list
        for artifact_obj in artifacts:  # Renamed from artifact to artifact_obj
            memory_item_obj = MemoryItem.from_artifact(artifact_obj)
            agent._update_context_window(
                memory_item_obj
            )  # Assumes _update_context_window is method on agent
            agent.cache[artifact_obj.artifact_id] = memory_item_obj
            items_list.append(memory_item_obj)

        logger.info(f"Found {len(items_list)} matches in database")
        return items_list
    except Exception as e:
        logger.error(f"Error in memory retrieval: {e}")
        return []
