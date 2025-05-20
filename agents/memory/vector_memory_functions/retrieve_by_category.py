import logging
from typing import List, Any

from sqlalchemy import select, desc
from infra.db.models import Artifact  # Assuming direct import

# from .memory_item import MemoryItem

logger = logging.getLogger(__name__)


async def retrieve_by_category_logic(
    agent: Any, category: str, limit: int = 10  # VectorMemory instance
) -> List["MemoryItem"]:
    """
    Retrieve memory items by category.
    Args:
        agent: The VectorMemory instance.
        category: Category to match.
        limit: Maximum number of results to return.
    Returns:
        List of memory items in the category.
    """
    try:
        from agents.memory.vector_memory_functions.memory_item import (
            MemoryItem,
        )  # Local import

        # First, try cache
        cached_matches = []
        if agent.cache:
            for artifact_id, mem_item in agent.cache.items():
                if mem_item.category == category:
                    cached_matches.append(mem_item)
            if cached_matches:
                logger.info(
                    f"Found {len(cached_matches)} matches for category '{category}' in cache."
                )
                # Sort by importance or creation date if needed
                # For now, just returning up to limit, assuming cache might not be ordered optimally for this specific query.
                # To be fully consistent with DB query, might need to sort cache results too or fetch more.
                return sorted(cached_matches, key=lambda x: x.created_at, reverse=True)[
                    :limit
                ]

        db_query = (
            select(Artifact)
            .where(Artifact.artifact_type == category)
            .order_by(desc(Artifact.created_at))
            .limit(limit)
        )

        result = await agent.db_session.execute(db_query)
        artifacts = result.scalars().all()

        items_list = []
        for artifact_obj in artifacts:
            memory_item_obj = MemoryItem.from_artifact(artifact_obj)
            agent._update_context_window(memory_item_obj)
            agent.cache[artifact_obj.artifact_id] = memory_item_obj
            items_list.append(memory_item_obj)

        logger.info(
            f"Found {len(items_list)} matches for category '{category}' from database."
        )
        return items_list
    except Exception as e:
        logger.error(f"Error retrieving by category {category}: {str(e)}")
        return []
