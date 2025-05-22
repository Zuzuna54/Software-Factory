import uuid
import logging
from typing import Any

from sqlalchemy import (
    delete as sqlalchemy_delete,
)  # Alias to avoid confusion with method name
from infra.db.models import Artifact  # Assuming direct import

logger = logging.getLogger(__name__)


async def delete_logic(agent: Any, artifact_id: uuid.UUID) -> bool:
    """
    Delete a memory item.
    Args:
        agent: The VectorMemory instance.
        artifact_id: The ID of the artifact to delete.
    Returns:
        True if deletion successful, False otherwise.
    """
    try:
        stmt = sqlalchemy_delete(Artifact).where(Artifact.artifact_id == artifact_id)
        await agent.db_session.execute(stmt)
        await agent.db_session.commit()  # Commit after delete

        if artifact_id in agent.cache:
            del agent.cache[artifact_id]

        # Remove from context window. Relies on artifact_id attribute of items in context_window.
        agent.context_window = [
            item for item in agent.context_window if item.artifact_id != artifact_id
        ]
        return True
    except Exception as e:
        logger.error(f"Error deleting memory item {artifact_id}: {str(e)}")
        await agent.db_session.rollback()  # Rollback on error
        return False
