import logging
from typing import List, Any

from sqlalchemy import select
from infra.db.models import Artifact  # Assuming direct import

# from .memory_item import MemoryItem

logger = logging.getLogger(__name__)


async def retrieve_by_tags_logic(
    agent: Any,  # VectorMemory instance
    tags: List[str],
    match_all: bool = True,
    limit: int = 10,
) -> List["MemoryItem"]:
    """
    Retrieve memory items by tags.
    Args:
        agent: The VectorMemory instance.
        tags: List of tags to match.
        match_all: If True, all tags must match; if False, any tag can match.
        limit: Maximum number of results to return.
    Returns:
        List of memory items matching the tags.
    """
    try:
        from agents.memory.vector_memory_functions.memory_item import (
            MemoryItem,
        )  # Local import

        # The original logic for retrieve_by_tags was simplified for testing and did not use SQL for tag filtering.
        # It selected `limit` artifacts and then manually filtered them.
        # Replicating that logic here.
        # For a production system, tag filtering should ideally be done in the DB query if possible (e.g., using JSONB operators or array overlaps).

        # First, try cache (not in original simplified retrieve_by_tags, but good practice)
        cached_matches = []
        if agent.cache:
            for artifact_id, mem_item in agent.cache.items():
                # Ensure mem_item.tags is a list
                artifact_tags = getattr(mem_item, "tags", [])
                if not isinstance(artifact_tags, list):
                    artifact_tags = (
                        []
                    )  # Default to empty list if tags attribute is not a list

                if match_all:
                    if all(tag in artifact_tags for tag in tags):
                        cached_matches.append(mem_item)
                else:
                    if any(tag in artifact_tags for tag in tags):
                        cached_matches.append(mem_item)
            if cached_matches:
                logger.info(
                    f"Found {len(cached_matches)} matches for tags {tags} in cache."
                )
                # Sort by importance or creation date if needed, for now just take limit
                return cached_matches[:limit]

        # If not enough from cache, query DB (original simplified logic)
        db_query = (
            select(Artifact).order_by(desc(Artifact.created_at)).limit(limit * 5)
        )  # Fetch more to filter in memory

        result = await agent.db_session.execute(db_query)
        artifacts = result.scalars().all()

        filtered_items = []
        for artifact_obj in artifacts:
            # MemoryItem.from_artifact extracts tags from artifact.metadata_["tags"]
            memory_item_obj = MemoryItem.from_artifact(artifact_obj)

            item_tags = (
                memory_item_obj.tags
            )  # These are already extracted by from_artifact

            match = False
            if match_all:
                if all(tag in item_tags for tag in tags):
                    match = True
            else:
                if any(tag in item_tags for tag in tags):
                    match = True

            if match:
                agent._update_context_window(memory_item_obj)
                agent.cache[artifact_obj.artifact_id] = memory_item_obj
                filtered_items.append(memory_item_obj)
                if len(filtered_items) >= limit:
                    break

        logger.info(
            f"Found {len(filtered_items)} matches for tags {tags} from database."
        )
        return filtered_items

    except Exception as e:
        logger.error(f"Error retrieving by tags {tags}: {str(e)}")
        return []
