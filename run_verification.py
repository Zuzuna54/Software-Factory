#!/usr/bin/env python
"""
Main verification script to run all tests for Iteration 1.
"""

import asyncio
import sys
import time
from datetime import datetime

from verify_agent_init import test_base_agent
from verify_llm_provider import test_llm_provider
from verify_vector_memory import test_vector_memory
from verify_db_client import test_postgres_client
from verify_communication import test_communication_protocol
from verify_cli_tool import test_cli_tool
from verify_logging import test_logging_system


async def run_all_tests():
    """Run all verification tests for Iteration 1 components."""
    print("\n===== Iteration 1 Verification Tests =====")
    print("Testing all components against verification criteria\n")

    overall_start_time = datetime.utcnow()
    results = {}

    # List of test functions and their descriptions
    tests = [
        (
            test_base_agent,
            "BaseAgent successfully initializes and performs basic operations",
        ),
        (
            test_llm_provider,
            "LLM provider correctly generates completions, chat responses, and embeddings",
        ),
        (
            test_vector_memory,
            "Agents can store and retrieve information using vector memory",
        ),
        (
            test_postgres_client,
            "Database client correctly executes queries and manages transactions",
        ),
        (
            test_communication_protocol,
            "Agents can send and receive messages using the communication protocol",
        ),
        (test_cli_tool, "CLI tool successfully creates and tests agent interactions"),
        (
            test_logging_system,
            "All agent activities are properly logged to the database",
        ),
    ]

    # Run each test and collect results
    for test_func, description in tests:
        print(f"\n{'=' * 80}")
        print(f"Testing: {description}")
        print(f"{'=' * 80}")

        try:
            start_time = time.time()
            success = await test_func()
            duration = time.time() - start_time

            results[description] = {
                "success": success,
                "duration": duration,
                "error": None,
            }

            if success:
                print(f"\n✅ Test passed: {description} ({duration:.2f}s)")
            else:
                print(f"\n❌ Test failed: {description} ({duration:.2f}s)")

        except Exception as e:
            print(f"\n❌ Test error: {description}")
            print(f"Error: {str(e)}")

            results[description] = {
                "success": False,
                "duration": time.time() - start_time,
                "error": str(e),
            }

    # Generate summary report
    print("\n\n===== Verification Summary =====")
    print(f"Tests completed at: {datetime.utcnow().isoformat()}")

    total_tests = len(tests)
    passed_tests = sum(1 for r in results.values() if r["success"])
    failed_tests = total_tests - passed_tests

    total_duration = (datetime.utcnow() - overall_start_time).total_seconds()

    print(f"\nTotal tests: {total_tests}")
    print(f"Passed tests: {passed_tests}")
    print(f"Failed tests: {failed_tests}")
    print(f"Total duration: {total_duration:.2f} seconds")

    # Detailed results
    print("\nDetailed Results:")
    for i, (description, result) in enumerate(results.items(), 1):
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{i}. {status} - {description} ({result['duration']:.2f}s)")
        if result["error"]:
            print(f"   Error: {result['error']}")

    # Overall pass/fail
    if failed_tests == 0:
        print("\n✅ ALL VERIFICATION CRITERIA PASSED")
        return True
    else:
        print(f"\n❌ VERIFICATION FAILED: {failed_tests} of {total_tests} tests failed")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
