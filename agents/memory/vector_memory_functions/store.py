import uuid
import logging
from typing import List, Union, Optional, Any, Dict
from datetime import datetime

from sqlalchemy import insert, update
from infra.db.models import Artifact  # Assuming direct import for Artifact model

# Assuming MemoryItem is imported where this function is called, or pass it if needed
# from .memory_item import MemoryItem
# Assuming LLMProvider is accessible via agent.llm_provider
# from agents.llm import LLMProvider

logger = logging.getLogger(__name__)


async def _generate_embeddings_logic(agent: Any, items: List["MemoryItem"]) -> None:
    """
    Generate embeddings for memory items.
    Args:
        agent: The VectorMemory instance (or an object with llm_provider).
        items: List of memory items to generate embeddings for.
    """
    texts = [item.content for item in items]
    try:
        embeddings, _ = await agent.llm_provider.generate_embeddings(texts)
        for i, item_obj in enumerate(
            items
        ):  # Renamed item to item_obj to avoid conflict with outer scope if nested
            item_obj.embedding = embeddings[i]
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        # Continue without embeddings, they can be generated later


async def _create_artifact_logic(agent: Any, item: "MemoryItem") -> uuid.UUID:
    """
    Create a new artifact in the database from a memory item.
    Args:
        agent: The VectorMemory instance (or an object with db_session, agent_id).
        item: The memory item to create an artifact from.
    Returns:
        The ID of the created artifact.
    """
    now = datetime.utcnow()
    artifact_id = uuid.uuid4()

    project_id_to_use = item.metadata.get("project_id")
    if not project_id_to_use:
        if hasattr(agent, "project_id") and agent.project_id:
            project_id_to_use = agent.project_id
        elif agent.agent_id:
            logger.warning(
                f"Missing project_id for artifact creation by agent {agent.agent_id}. Generating a placeholder ID."
            )
            project_id_to_use = uuid.uuid4()
        else:
            project_id_to_use = uuid.UUID("00000000-0000-0000-0000-000000000000")

    artifact_data = {
        "artifact_id": artifact_id,
        "artifact_type": item.category,
        "title": item.metadata.get("title", item.content[:100]),
        "created_at": now,
        "created_by": agent.agent_id,
        "status": item.metadata.get("status", "active"),
        "metadata_": {
            "content": item.content,
            "content_type": item.content_type,
            "tags": item.tags,
            "importance": item.importance,
            "original_timestamp": item.created_at.isoformat(),
            "version": item.metadata.get("version", 1),
            **item.metadata,
        },
        "content_vector": item.embedding,
        "project_id": project_id_to_use,
        "description": item.metadata.get("description", item.content[:255]),
    }
    if (
        "project_id" in artifact_data["metadata_"]
    ):  # Ensure project_id is not duplicated
        del artifact_data["metadata_"]["project_id"]

    stmt = insert(Artifact).values(**artifact_data)
    await agent.db_session.execute(stmt)
    # The commit should ideally be handled by the caller of store_logic,
    # or store_logic should manage a transaction if it's the top-level DB operation.
    # For now, assume commit happens after a batch of operations or higher up.
    # await agent.db_session.commit() # Deferred to main store_logic or its caller
    return artifact_id


async def _update_artifact_logic(agent: Any, item: "MemoryItem") -> None:
    """
    Update an existing artifact in the database.
    Args:
        agent: The VectorMemory instance (or an object with db_session, agent_id).
        item: The memory item to update the artifact from.
    """
    now = datetime.utcnow()

    # Prepare metadata for the 'metadata_' field, including the original content and version
    metadata_field_content = {
        "content": item.content,  # Store original content
        "content_type": item.content_type,
        "tags": item.tags,
        "importance": item.importance,
        "original_timestamp": item.created_at.isoformat(),
        "last_updated": now.isoformat(),
        "version": item.metadata.get("version", 1),  # Store version
        **item.metadata,  # Include other original metadata
    }
    if (
        "project_id" in metadata_field_content
        and item.metadata.get("project_id") == item.artifact_id
    ):
        # This condition seems wrong, project_id usually isn't the same as artifact_id.
        # And project_id is a top-level field of Artifact, not usually in metadata_ for update.
        # Let's assume item.metadata might contain a new project_id, but Artifact.project_id is not typically updated.
        pass

    update_values = {
        # "title": item.metadata.get("title", item.content[:100]), # Title update could be optional
        # "status": item.metadata.get("status"), # Status update could be optional
        "metadata_": metadata_field_content,
        "content_vector": item.embedding,
        "updated_at": now,  # Let DB handle this with onupdate if configured
        "last_modified_by": agent.agent_id,
        # description could also be updated based on new content if desired
        "description": item.metadata.get("description", item.content[:255]),
    }

    # Filter out None values, so we only update fields that are explicitly set.
    # However, for metadata_ and content_vector, we usually want to update them even if new embedding is None (to clear it).
    # For this refactor, keeping it similar to original: direct assignment.
    # The original _update_artifact was missing title, status, description updates. Added description.
    # Original _update_artifact was:
    # update_data = {
    #     "content": item.content, # This was problematic for base Artifact table
    #     "last_modified_at": now,
    #     "last_modified_by": self.agent_id,
    #     "extra_data": { ... } # Should be metadata_
    #     "content_vector": item.embedding,
    # }
    # The new Artifact model has 'description', and 'content' is in metadata_ for generic memory items.
    # If item.category implies a child table with direct 'content', that needs specific handling.
    # For now, this logic assumes generic Artifact updates primarily via metadata_ and description.

    stmt = (
        update(Artifact)
        .where(Artifact.artifact_id == item.artifact_id)
        .values(**update_values)
    )
    await agent.db_session.execute(stmt)
    # await agent.db_session.commit() # Deferred


async def store_logic(
    agent: Any,
    items: Union["MemoryItem", List["MemoryItem"]],
    generate_embeddings: bool = True,
    update_if_exists: bool = True,
) -> List[uuid.UUID]:
    """
    Store one or more memory items.
    Args:
        agent: The VectorMemory instance.
        items: A single memory item or list of items to store.
        generate_embeddings: Whether to generate embeddings for the items.
        update_if_exists: Whether to update existing items if they exist.
    Returns:
        List of artifact IDs for the stored items.
    """
    if isinstance(
        items, MemoryItem
    ):  # MemoryItem will be imported in the main vector_memory.py
        single_item = True
        items_list = [items]
    else:
        single_item = False
        items_list = items

    if generate_embeddings:
        items_to_embed = [
            item_obj for item_obj in items_list if item_obj.embedding is None
        ]
        if items_to_embed:
            await _generate_embeddings_logic(agent, items_to_embed)

    artifact_ids = []
    try:
        for item_obj in items_list:
            if item_obj.artifact_id:
                if update_if_exists:
                    await _update_artifact_logic(agent, item_obj)
                artifact_ids.append(item_obj.artifact_id)
                agent.cache[item_obj.artifact_id] = item_obj
            else:
                new_artifact_id = await _create_artifact_logic(agent, item_obj)
                artifact_ids.append(new_artifact_id)
                item_obj.artifact_id = new_artifact_id  # Update item with new ID
                agent.cache[new_artifact_id] = item_obj

            agent._update_context_window(
                item_obj
            )  # Assumes _update_context_window is still a method on agent (VectorMemory instance)

        await agent.db_session.commit()  # Commit once after all operations in the batch
    except Exception as e:
        logger.error(f"Error during batch store operation, rolling back: {str(e)}")
        await agent.db_session.rollback()
        raise  # Re-raise the exception after rollback
        # Alternatively, return empty list or specific error indicators
        # For now, re-raising to make failure clear. artifact_ids might be partially populated.

    return artifact_ids
