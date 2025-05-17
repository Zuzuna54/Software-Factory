#!/usr/bin/env python
"""
Verification test for vector memory implementation.
"""

import asyncio
import uuid
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from agents.memory.vector_memory import VectorMemory, MemoryItem
from agents.llm import get_llm_provider


async def test_vector_memory():
    """Test vector memory storage and retrieval capabilities."""
    print("\n----- Testing Vector Memory Implementation -----")

    # Create database connection
    database_url = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory"
    )
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    test_start_time = datetime.utcnow()
    test_prefix = f"test_{uuid.uuid4().hex[:8]}"

    try:
        async with async_session() as db_session:
            # Initialize llm provider
            print("Initializing LLM provider...")
            llm_provider = get_llm_provider()

            # Initialize vector memory
            print("Initializing vector memory...")
            memory = VectorMemory(db_session=db_session, llm_provider=llm_provider)

            # 1. Test storing an item
            print("\nTesting memory item storage...")
            test_content = "This is a test memory item for verification purposes."
            test_category = "verification"
            test_tags = ["test", "verification", "memory"]

            store_start = time.time()
            memory_item = MemoryItem(
                content=test_content,
                artifact_id=str(uuid.uuid4()),
                content_type="text",
                category=test_category,
                tags=test_tags,
                importance=3,
                metadata={"test_id": test_prefix},
            )

            stored_id = await memory.store(memory_item, generate_embeddings=True)
            store_duration = time.time() - store_start

            if stored_id:
                print(f"✅ Memory item stored successfully ({store_duration:.2f}s)")
                print(f"Memory ID: {stored_id}")
            else:
                print(f"❌ Failed to store memory item")
                return False

            # 2. Test retrieving by ID
            print("\nTesting retrieve by ID...")
            retrieve_start = time.time()
            retrieved_item = await memory.retrieve_by_id(stored_id)
            retrieve_duration = time.time() - retrieve_start

            if retrieved_item and retrieved_item.content == test_content:
                print(
                    f"✅ Memory item retrieved successfully by ID ({retrieve_duration:.2f}s)"
                )
            else:
                print(f"❌ Failed to retrieve memory item by ID")
                return False

            # 3. Test semantic search
            print("\nTesting semantic search...")
            search_query = "verification test memory"

            search_start = time.time()
            search_results = await memory.retrieve(
                query=search_query, limit=5, category=test_category
            )
            search_duration = time.time() - search_start

            if (
                search_results
                and len(search_results) > 0
                and search_results[0].artifact_id == stored_id
            ):
                print(f"✅ Semantic search successful ({search_duration:.2f}s)")
                print(
                    f"Found {len(search_results)} results, top result matches stored item"
                )
            else:
                print(f"❌ Semantic search failed or didn't return expected results")
                return False

            # 4. Test tag filtering
            print("\nTesting retrieval by tags...")
            tag_start = time.time()
            tag_results = await memory.retrieve_by_tags(
                tags=["verification", "test"], require_all=True
            )
            tag_duration = time.time() - tag_start

            if (
                tag_results
                and len(tag_results) > 0
                and any(i.artifact_id == stored_id for i in tag_results)
            ):
                print(f"✅ Tag filtering successful ({tag_duration:.2f}s)")
                print(f"Found {len(tag_results)} results with required tags")
            else:
                print(f"❌ Tag filtering failed or didn't return expected results")
                return False

            # 5. Test chunking functionality
            print("\nTesting text chunking and storage...")
            long_text = (
                "This is a long text that should be split into multiple chunks. " * 10
            )

            chunk_start = time.time()
            chunk_ids = await memory.chunk_and_store_text(
                text=long_text,
                category=test_category,
                tags=["chunk_test"],
                metadata={"test_id": test_prefix},
            )
            chunk_duration = time.time() - chunk_start

            if chunk_ids and len(chunk_ids) > 1:
                print(f"✅ Text chunking successful ({chunk_duration:.2f}s)")
                print(f"Created {len(chunk_ids)} chunks from the long text")
            else:
                print(f"❌ Text chunking failed or didn't create multiple chunks")
                return False

            # 6. Test deletion
            print("\nTesting memory item deletion...")
            delete_start = time.time()
            delete_result = await memory.delete(stored_id)
            delete_duration = time.time() - delete_start

            if delete_result:
                print(f"✅ Memory item deleted successfully ({delete_duration:.2f}s)")
            else:
                print(f"❌ Failed to delete memory item")
                return False

            # 7. Clean up test data
            print("\nCleaning up test data...")
            # Delete all test items created during this test
            await db_session.execute(
                f"DELETE FROM artifacts WHERE metadata->>'test_id' = '{test_prefix}'"
            )
            await db_session.commit()

            # All tests passed!
            test_end_time = datetime.utcnow()
            duration = (test_end_time - test_start_time).total_seconds()
            print(
                f"\n✅ All vector memory tests passed successfully in {duration:.2f} seconds!"
            )
            return True

    except Exception as e:
        print(f"❌ Error during vector memory testing: {str(e)}")
        return False
    finally:
        # Close the engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_vector_memory())
