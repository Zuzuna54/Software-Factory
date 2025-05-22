import uuid
import logging
from typing import List, Optional

from agents.memory.vector_memory import MemoryItem

# Assuming MemoryItem is defined elsewhere and will be imported appropriately
# from agents.memory.vector_memory import MemoryItem # This might be needed if not passed directly

logger = logging.getLogger(__name__)


async def store_memory_item_logic(
    agent, item: "MemoryItem"
) -> Optional[List[uuid.UUID]]:
    """Store a MemoryItem using the agent's VectorMemory."""
    if not agent.vector_memory:
        logger.warning(
            f"Agent {agent.agent_id} has no VectorMemory initialized. Cannot store item."
        )
        return None
    try:
        return await agent.vector_memory.store(item)
    except Exception as e:
        logger.error(f"Error storing memory item for agent {agent.agent_id}: {e}")
        # It's good practice to log the error with agent's activity_logger if available and relevant
        # await agent.activity_logger.log_error(...)
        return None
