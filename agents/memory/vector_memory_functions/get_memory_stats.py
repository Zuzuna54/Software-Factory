import logging
from typing import Dict, Any

from sqlalchemy import select, func
from infra.db.models import Artifact  # Assuming direct import

logger = logging.getLogger(__name__)


async def get_memory_stats_logic(agent: Any) -> Dict[str, Any]:
    """
    Get statistics about the memory system.
    Args:
        agent: The VectorMemory instance.
    Returns:
        Dictionary with memory statistics.
    """
    try:
        count_query = select(func.count()).select_from(Artifact)
        result = await agent.db_session.execute(count_query)
        total_count = result.scalar_one()

        category_query = select(Artifact.artifact_type, func.count()).group_by(
            Artifact.artifact_type
        )
        result = await agent.db_session.execute(category_query)
        categories = {category: count for category, count in result.all()}

        newest_query = select(func.max(Artifact.created_at)).select_from(Artifact)
        result = await agent.db_session.execute(newest_query)
        newest_date = result.scalar_one()

        oldest_query = select(func.min(Artifact.created_at)).select_from(Artifact)
        result = await agent.db_session.execute(oldest_query)
        oldest_date = result.scalar_one()

        return {
            "total_memories": total_count,
            "by_category": categories,
            "newest_memory": newest_date.isoformat() if newest_date else None,
            "oldest_memory": oldest_date.isoformat() if oldest_date else None,
            "context_window_size": len(agent.context_window),
            "cache_size": len(agent.cache),
        }
    except Exception as e:
        logger.error(f"Error getting memory stats: {str(e)}")
        return {
            "error": str(e),
            "context_window_size": len(agent.context_window),
            "cache_size": len(agent.cache),
        }
