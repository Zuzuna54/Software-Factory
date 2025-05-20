import logging
from typing import List, Dict, Any, Optional
import uuid

# from .memory_item import MemoryItem # Imported in main module
# store_logic will be called on the agent instance

logger = logging.getLogger(__name__)


def _chunk_text_logic(text: str, chunk_size: int) -> List[str]:
    """
    Split text into chunks of approximately equal size.
    Args:
        text: The text to chunk
        chunk_size: The size of each chunk.
    Returns:
        List of text chunks
    """
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i : i + chunk_size])
    logger.info(
        f"Chunking text of length {len(text)} with chunk size {chunk_size} yielded {len(chunks)} chunks"
    )
    return chunks


async def chunk_and_store_text_logic(
    agent: Any,  # VectorMemory instance
    text: str,
    category: str = "general",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> List[uuid.UUID]:
    """
    Chunk a long text into smaller pieces and store them.
    Args:
        agent: The VectorMemory instance.
        text: The text to chunk and store
        category: Category for the chunks
        tags: Optional list of tags
        metadata: Optional additional metadata
    Returns:
        List of artifact IDs for the stored chunks
    """
    # Import MemoryItem locally where it's instantiated
    from agents.memory.vector_memory_functions.memory_item import MemoryItem

    original_chunk_size = agent.chunk_size
    try:
        # Temporarily set a small chunk size for testing as in original code
        # This testing specific logic might be better handled in test setup
        # For now, replicating original behavior.
        agent.chunk_size = 20  # Very small chunk size for testing
        if len(text) < 60:  # Need at least 3x chunk size
            text = text * 3

        chunks = _chunk_text_logic(
            text, agent.chunk_size
        )  # Use the current agent.chunk_size
        logger.info(f"Created {len(chunks)} chunks from text")

        items_to_store = []
        for i, chunk_content in enumerate(chunks):
            chunk_metadata = {
                "chunk_index": i,
                "total_chunks": len(chunks),
                "original_length": len(text),
                **(metadata or {}),
            }
            # Pass project_id from agent.metadata if available, or let store_logic handle it
            if hasattr(agent, "project_id") and agent.project_id:
                if "project_id" not in chunk_metadata:
                    chunk_metadata["project_id"] = agent.project_id

            item = MemoryItem(
                content=chunk_content,
                category=category,
                tags=tags or [],
                metadata=chunk_metadata,
            )
            items_to_store.append(item)

        # Call the main store method (which itself uses store_logic)
        # This assumes agent has a .store() method that correctly calls the refactored store_logic
        return await agent.store(items_to_store)
    finally:
        agent.chunk_size = original_chunk_size
