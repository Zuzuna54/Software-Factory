#!/usr/bin/env python
"""
Verification test for LLM provider integration.
"""

import asyncio
import os
import time
from datetime import datetime

from agents.llm.vertex_gemini_provider import VertexGeminiProvider


async def test_llm_provider():
    """Test LLM provider integration with Google Vertex AI Gemini models."""
    print("\n----- Testing LLM Provider Integration -----")

    test_start_time = datetime.utcnow()

    try:
        # Initialize the LLM provider
        print("Initializing LLM provider...")
        llm_provider = VertexGeminiProvider()

        # 1. Test text completion generation
        print("\nTesting text completion generation...")
        completion_prompt = (
            "Write a one-sentence description of what an autonomous agent does."
        )

        completion_start = time.time()
        completion_result = await llm_provider.generate_text(completion_prompt)
        completion_duration = time.time() - completion_start

        if (
            completion_result
            and isinstance(completion_result, str)
            and len(completion_result) > 10
        ):
            print(f"✅ Text completion successful ({completion_duration:.2f}s)")
            print(f"Result: {completion_result[:100]}...")
        else:
            print(f"❌ Text completion failed")
            return False

        # 2. Test chat completion generation
        print("\nTesting chat completion generation...")
        chat_messages = [
            {
                "role": "user",
                "content": "What are the benefits of using vector embeddings for semantic search?",
            }
        ]

        chat_start = time.time()
        chat_result = await llm_provider.generate_chat_response(chat_messages)
        chat_duration = time.time() - chat_start

        if chat_result and isinstance(chat_result, str) and len(chat_result) > 10:
            print(f"✅ Chat completion successful ({chat_duration:.2f}s)")
            print(f"Result: {chat_result[:100]}...")
        else:
            print(f"❌ Chat completion failed")
            return False

        # 3. Test embedding generation
        print("\nTesting embedding generation...")
        embedding_text = "This is a test text for embedding generation to verify vector functionality."

        embedding_start = time.time()
        embedding_result = await llm_provider.generate_embedding(embedding_text)
        embedding_duration = time.time() - embedding_start

        if embedding_result is not None and len(embedding_result) > 0:
            print(f"✅ Embedding generation successful ({embedding_duration:.2f}s)")
            print(f"Embedding dimensions: {len(embedding_result)}")
        else:
            print(f"❌ Embedding generation failed")
            return False

        # 4. Test function calling
        print("\nTesting function calling...")
        function_spec = {
            "name": "search_database",
            "description": "Search for records in a database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                    },
                },
                "required": ["query"],
            },
        }

        functions = [function_spec]
        function_prompt = (
            "I need to find all customer records related to renewable energy projects."
        )

        function_start = time.time()
        function_result = await llm_provider.generate_function_call(
            function_prompt, functions
        )
        function_duration = time.time() - function_start

        if (
            function_result
            and isinstance(function_result, dict)
            and "name" in function_result
        ):
            print(f"✅ Function calling successful ({function_duration:.2f}s)")
            print(f"Function call: {function_result}")
        else:
            print(f"❌ Function calling failed")
            return False

        # All tests passed!
        test_end_time = datetime.utcnow()
        duration = (test_end_time - test_start_time).total_seconds()
        print(
            f"\n✅ All LLM provider tests passed successfully in {duration:.2f} seconds!"
        )
        return True

    except Exception as e:
        print(f"❌ Error during LLM provider testing: {str(e)}")
        return False


if __name__ == "__main__":
    asyncio.run(test_llm_provider())
