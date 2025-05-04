# agents/tests/test_vector_memory.py

import pytest
import random
from ..memory.vector_memory import VectorMemory
from ..db.postgres import PostgresClient

pytestmark = pytest.mark.asyncio

# Constants
ENTITY_TYPE_TEST = "test_messages"
EMBEDDING_DIM = 1536  # Should match VectorMemory.EMBEDDING_DIM


# Helper to create a random embedding
def random_embedding(dim: int) -> list[float]:
    return [random.random() for _ in range(dim)]


async def test_initialize_vector_memory(vector_memory: VectorMemory):
    """Test that VectorMemory initializes correctly (creates table/index)."""
    # The fixture already initializes, this test just ensures it doesn't fail
    assert vector_memory._initialized
    # Check if table exists (optional, depends on DB client capabilities)
    # table_exists = await vector_memory.db_client.fetch_val(...)
    # assert table_exists


async def test_store_and_get_embedding(vector_memory: VectorMemory):
    """Test storing and retrieving a single embedding."""
    entity_id = "msg_001"
    embedding = random_embedding(EMBEDDING_DIM)
    metadata = {"sender": "agent_A", "timestamp": "2024-01-01T10:00:00"}

    await vector_memory.store_embedding(
        ENTITY_TYPE_TEST, entity_id, embedding, metadata
    )

    retrieved_embedding = await vector_memory.get_embedding(ENTITY_TYPE_TEST, entity_id)

    assert retrieved_embedding is not None
    assert len(retrieved_embedding) == EMBEDDING_DIM
    # Compare floats with tolerance due to potential precision issues
    assert pytest.approx(retrieved_embedding) == embedding

    # Test retrieving metadata (requires modifying get_embedding or adding get_metadata)
    # metadata_from_db = await vector_memory.get_metadata(ENTITY_TYPE_TEST, entity_id)
    # assert metadata_from_db == metadata


async def test_store_embedding_conflict_update(vector_memory: VectorMemory):
    """Test that storing an embedding for an existing entity updates it."""
    entity_id = "msg_conflict"
    embedding1 = random_embedding(EMBEDDING_DIM)
    metadata1 = {"version": 1}
    await vector_memory.store_embedding(
        ENTITY_TYPE_TEST, entity_id, embedding1, metadata1
    )

    embedding2 = random_embedding(EMBEDDING_DIM)
    metadata2 = {"version": 2}
    await vector_memory.store_embedding(
        ENTITY_TYPE_TEST, entity_id, embedding2, metadata2
    )

    retrieved_embedding = await vector_memory.get_embedding(ENTITY_TYPE_TEST, entity_id)
    assert retrieved_embedding is not None
    assert pytest.approx(retrieved_embedding) == embedding2
    assert retrieved_embedding != embedding1

    # Verify count remains 1 for this entity_id
    count = await vector_memory.count_embeddings(ENTITY_TYPE_TEST)
    # Note: This count will include other test entities unless cleared per-test
    # A better check might involve querying the specific entity ID


async def test_delete_embedding(vector_memory: VectorMemory):
    """Test deleting an embedding."""
    entity_id = "msg_to_delete"
    embedding = random_embedding(EMBEDDING_DIM)
    await vector_memory.store_embedding(ENTITY_TYPE_TEST, entity_id, embedding)

    # Ensure it exists
    assert await vector_memory.get_embedding(ENTITY_TYPE_TEST, entity_id) is not None

    # Delete it
    deleted = await vector_memory.delete_embedding(ENTITY_TYPE_TEST, entity_id)
    assert deleted

    # Ensure it's gone
    assert await vector_memory.get_embedding(ENTITY_TYPE_TEST, entity_id) is None

    # Test deleting non-existent
    deleted_again = await vector_memory.delete_embedding(ENTITY_TYPE_TEST, entity_id)
    assert not deleted_again


async def test_search_similar_embeddings(vector_memory: VectorMemory):
    """Test searching for similar embeddings."""
    # Store a few embeddings
    entity_ids = [f"search_msg_{i:03d}" for i in range(5)]
    embeddings = [random_embedding(EMBEDDING_DIM) for _ in range(5)]

    for i, entity_id in enumerate(entity_ids):
        await vector_memory.store_embedding(ENTITY_TYPE_TEST, entity_id, embeddings[i])

    # Query embedding close to the first stored embedding
    query_embedding = embeddings[0][:]  # Create a copy
    query_embedding[0] += 0.001  # Slightly modify

    similar_ids = await vector_memory.search_similar(
        ENTITY_TYPE_TEST,
        query_embedding,
        threshold=0.95,  # High threshold since it's very similar
        limit=3,
    )

    assert len(similar_ids) >= 1
    assert entity_ids[0] in similar_ids
    # The order should have entity_ids[0] first due to closeness
    assert similar_ids[0] == entity_ids[0]

    # Test with a lower threshold (should match more, potentially all)
    similar_ids_low_thresh = await vector_memory.search_similar(
        ENTITY_TYPE_TEST, query_embedding, threshold=0.1, limit=10  # Low threshold
    )
    assert len(similar_ids_low_thresh) >= 1  # Should find at least the closest one
    # Depending on random values, might find more

    # Test limit
    similar_ids_limit_1 = await vector_memory.search_similar(
        ENTITY_TYPE_TEST, query_embedding, threshold=0.1, limit=1
    )
    assert len(similar_ids_limit_1) == 1
    assert similar_ids_limit_1[0] == entity_ids[0]


async def test_list_and_count_embeddings(vector_memory: VectorMemory):
    """Test listing entity types and counting embeddings."""
    # Ensure previous tests added embeddings for ENTITY_TYPE_TEST
    await vector_memory.store_embedding(
        "other_type", "item_1", random_embedding(EMBEDDING_DIM)
    )
    await vector_memory.store_embedding(
        "other_type", "item_2", random_embedding(EMBEDDING_DIM)
    )

    entity_types = await vector_memory.list_entity_types()
    assert isinstance(entity_types, list)
    assert ENTITY_TYPE_TEST in entity_types
    assert "other_type" in entity_types

    total_count = await vector_memory.count_embeddings()
    assert total_count >= 7  # 5 from search test + 2 here + potentially others

    test_type_count = await vector_memory.count_embeddings(ENTITY_TYPE_TEST)
    assert test_type_count >= 5

    other_type_count = await vector_memory.count_embeddings("other_type")
    assert other_type_count == 2

    non_existent_count = await vector_memory.count_embeddings("non_existent_type")
    assert non_existent_count == 0
