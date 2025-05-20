"""
Helper function to parse LLM JSON output.
"""

import json
import asyncio
from typing import Dict, List, Any, Union

from agents.logging.activity_logger import (
    ActivityLogger,
    ActivityCategory,
    ActivityLevel,
)


async def parse_llm_json_output(
    activity_logger: ActivityLogger,  # Added ActivityLogger instance
    json_string: str,
    llm_metadata: Dict[str, Any],
    calling_method_name: str = "unknown_method",
    expected_type: type = list,  # Default to list, can be dict
) -> Union[List[Any], Dict[str, Any]]:
    """
    Parse JSON string from LLM output, with error logging.

    Args:
        activity_logger: Instance of ActivityLogger for logging.
        json_string: The string potentially containing JSON.
        llm_metadata: Metadata from the LLM call for logging context.
        calling_method_name: Name of the method that called this parser.
        expected_type: The expected Python type after parsing (e.g., list, dict).

    Returns:
        Parsed JSON as a list or dict, or a default empty structure if parsing fails.
    """
    try:
        parsed_output = json.loads(json_string)
        if not isinstance(parsed_output, expected_type):
            # Log a warning if the type is not what was expected
            asyncio.create_task(
                activity_logger.log_activity(
                    activity_type=f"warning_llm_json_unexpected_type_{calling_method_name}",
                    description=f"LLM JSON output for {calling_method_name} was parsed but is not of expected type {expected_type.__name__}. Actual type: {type(parsed_output).__name__}.",
                    category=ActivityCategory.WARNING,
                    level=ActivityLevel.WARNING,
                    details={
                        "raw_json_string": json_string[:500],  # Log a snippet
                        "llm_metadata": llm_metadata,
                        "expected_type": expected_type.__name__,
                        "actual_type": type(parsed_output).__name__,
                    },
                )
            )
            # Return default for the expected type to prevent downstream errors
            return expected_type()
        return parsed_output
    except json.JSONDecodeError as e:
        asyncio.create_task(
            activity_logger.log_error(
                error_type=f"LLMJSONParseError_{calling_method_name}",
                description=f"Failed to parse LLM response as JSON in {calling_method_name}: {str(e)}",
                exception=e,
                severity=ActivityLevel.ERROR,
                context={
                    "raw_response": json_string,
                    "llm_metadata": llm_metadata,
                    "calling_method": calling_method_name,
                },
            )
        )
        # Return default for the expected type
        return expected_type()
    except (
        Exception
    ) as e_unexpected:  # Catch any other unexpected error during parsing attempt
        asyncio.create_task(
            activity_logger.log_error(
                error_type=f"LLMJSONParseUnexpectedError_{calling_method_name}",
                description=f"Unexpected error during LLM JSON parsing in {calling_method_name}: {str(e_unexpected)}",
                exception=e_unexpected,
                severity=ActivityLevel.ERROR,
                context={
                    "raw_response": json_string,
                    "llm_metadata": llm_metadata,
                    "calling_method": calling_method_name,
                },
            )
        )
        return expected_type()
