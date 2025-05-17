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
        try:
            response, metadata = await llm_provider.generate_text(
                "Explain the concept of autonomous AI agents in 3 sentences."
            )
            print(f"✅ Text completion successful: {response[:100]}...")
            print(f"Metadata: {metadata}")
        except Exception as e:
            print(f"❌ Text completion failed: {str(e)}")
            return False

        # 2. Test chat completion generation
        print("\nTesting chat completion generation...")
        chat_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": "What are the key components of a multi-agent system?",
            },
        ]

        response, metadata = await llm_provider.generate_chat_completion(chat_messages)
        print(f"✅ Chat completion successful: {response[:100]}...")
        print(f"Metadata: {metadata}")

        # 3. Test embedding generation
        print("\nTesting embedding generation...")
        try:
            texts = ["Vector embeddings allow for semantic similarity search."]
            embeddings, metadata = await llm_provider.generate_embeddings(texts)

            if embeddings and isinstance(embeddings, list) and len(embeddings) > 0:
                print(
                    f"✅ Embedding generation successful. Dimensions: {len(embeddings[0])}"
                )
                print(f"Metadata: {metadata}")
            else:
                print("❌ Embedding generation failed: Invalid result format")
                return False
        except Exception as e:
            print(f"❌ Embedding generation failed: {str(e)}")
            return False

        # 4. Test function calling
        print("\nTesting function calling...")
        try:
            functions = [
                {
                    "name": "get_weather",
                    "description": "Get the current weather in a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. San Francisco, CA",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "The temperature unit",
                            },
                        },
                        "required": ["location"],
                    },
                }
            ]

            messages = [
                {"role": "user", "content": "What's the weather like in New York?"}
            ]

            response, metadata = await llm_provider.function_calling(
                messages, functions
            )

            if response:
                print(f"✅ Function calling successful")
                print(f"Result: {response}")
                print(f"Metadata: {metadata}")
            else:
                print("❌ Function calling failed: No result returned")
                return False
        except Exception as e:
            print(f"❌ Function calling failed: {str(e)}")
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
