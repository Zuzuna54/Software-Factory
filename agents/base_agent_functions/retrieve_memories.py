import logging
from typing import List, Optional

from agents.memory.vector_memory import MemoryItem

# from agents.memory.vector_memory import MemoryItem # Potentially needed

logger = logging.getLogger(__name__)


async def retrieve_memories_logic(
    agent,
    query_text: str,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
) -> List["MemoryItem"]:
    """Retrieve memories using the agent's VectorMemory."""
    if not agent.vector_memory:
        logger.warning(
            f"Agent {agent.agent_id} has no VectorMemory initialized. Cannot retrieve memories."
        )
        return []
    try:
        return await agent.vector_memory.retrieve(
            query=query_text, category=category, tags=tags, limit=limit
        )
    except Exception as e:
        logger.error(f"Error retrieving memories for agent {agent.agent_id}: {e}")
        # await agent.activity_logger.log_error(...)
        return []
