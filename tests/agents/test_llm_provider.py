# agents/tests/test_llm_provider.py

import pytest
from agents.llm.base import LLMProvider
from agents.llm.vertex_gemini_provider import VertexGeminiProvider

pytestmark = pytest.mark.asyncio


async def test_mock_generate_completion(llm_provider_mock: LLMProvider):
    prompt = "Test prompt"
    result = await llm_provider_mock.generate_completion(prompt)
    assert isinstance(result, str)
    assert prompt[:30] in result


async def test_mock_generate_chat_completion(llm_provider_mock: LLMProvider):
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "model", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    result = await llm_provider_mock.generate_chat_completion(messages)
    assert isinstance(result, str)
    assert messages[-1]["content"][:30] in result


async def test_mock_generate_embeddings(llm_provider_mock: LLMProvider):
    text = "This is a test text for embeddings."
    result = await llm_provider_mock.generate_embeddings(text)
    assert isinstance(result, list)
    assert len(result) == 1536  # Check dimension
    assert all(isinstance(val, float) for val in result)

    # Test determinism (optional, depends on mock implementation)
    result2 = await llm_provider_mock.generate_embeddings(text)
    assert result == result2

    result3 = await llm_provider_mock.generate_embeddings("Different text.")
    assert result != result3


async def test_mock_function_calling(llm_provider_mock: LLMProvider):
    messages = [{"role": "user", "content": "What is the weather in London?"}]
    functions = [
        {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        }
    ]
    result = await llm_provider_mock.function_calling(messages, functions)
    assert isinstance(result, dict)
    assert result["function_name"] == "get_weather"
    assert isinstance(result["function_args"], dict)
    assert "location" in result["function_args"]
    assert result["function_args"]["location"] == "mock_string"  # Based on mock logic


async def test_mock_function_calling_no_functions(llm_provider_mock: LLMProvider):
    messages = [{"role": "user", "content": "Tell me a joke."}]
    functions = []
    result = await llm_provider_mock.function_calling(messages, functions)
    assert isinstance(result, dict)
    assert result["function_name"] is None
    assert result["function_args"] is None
    assert isinstance(result["content"], str)
    assert "no function called" in result["content"]
