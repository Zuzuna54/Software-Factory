import uuid
import logging
from typing import Optional, Any

from sqlalchemy import select
from infra.db.models import Artifact  # Assuming direct import

# from .memory_item import MemoryItem # Will be imported in main module

logger = logging.getLogger(__name__)


async def retrieve_by_id_logic(
    agent: Any, artifact_id: uuid.UUID
) -> Optional["MemoryItem"]:
    """
    Retrieve a specific memory item by its artifact ID.
    Args:
        agent: The VectorMemory instance.
        artifact_id: The ID of the artifact to retrieve.
    Returns:
        The memory item if found, None otherwise.
    """
    # Check cache first
    if artifact_id in agent.cache:
        item = agent.cache[artifact_id]
        agent._update_context_window(
            item
        )  # Assumes _update_context_window is method on agent
        return item

    try:
        # Import MemoryItem class here as it's used for from_artifact
        from agents.memory.vector_memory_functions.memory_item import MemoryItem

        query = select(Artifact).where(Artifact.artifact_id == artifact_id)
        result = await agent.db_session.execute(query)
        artifact = result.scalar_one_or_none()

        if not artifact:
            logger.warning(f"Artifact {artifact_id} not found")
            return None

        memory_item_obj = MemoryItem.from_artifact(
            artifact
        )  # Renamed to avoid conflict
        agent._update_context_window(
            memory_item_obj
        )  # Assumes _update_context_window is method on agent
        agent.cache[artifact_id] = memory_item_obj
        return memory_item_obj
    except Exception as e:
        logger.error(f"Error retrieving memory item by ID: {str(e)}")
        return None
