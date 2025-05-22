"""
Utility functions for the CLI tool.

This module contains utility functions used across the CLI tool,
including UUID handling and validation.
"""

import logging
import uuid
from typing import Optional, Union

logger = logging.getLogger("agent_cli")


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID.

    Args:
        uuid_string: String to check

    Returns:
        True if the string is a valid UUID, False otherwise
    """
    try:
        uuid_obj = uuid.UUID(uuid_string)
        return str(uuid_obj) == uuid_string
    except (ValueError, AttributeError, TypeError):
        return False


def validate_uuid(id_value: str) -> bool:
    """
    Validate that a string is a valid UUID.

    Args:
        id_value: String to validate

    Returns:
        True if valid UUID, False otherwise

    Raises:
        ValueError: If the UUID is not valid
    """
    if not id_value:
        raise ValueError("UUID cannot be empty")

    if not is_valid_uuid(id_value):
        raise ValueError(f"Invalid UUID format: {id_value}")

    return True


def format_uuid(id_value: str) -> str:
    """
    Validate and format a UUID string.

    Args:
        id_value: String to format

    Returns:
        Formatted UUID string

    Raises:
        ValueError: If the UUID is not valid
    """
    validate_uuid(id_value)
    return str(uuid.UUID(id_value))


def ensure_uuid(id_value: Optional[Union[str, uuid.UUID]]) -> Optional[uuid.UUID]:
    """
    Convert a string or UUID to a UUID object.

    Args:
        id_value: String or UUID to convert

    Returns:
        UUID object or None if conversion fails
    """
    if id_value is None:
        return None

    if isinstance(id_value, uuid.UUID):
        return id_value

    try:
        return uuid.UUID(str(id_value))
    except (ValueError, AttributeError, TypeError) as e:
        logger.error(f"Invalid UUID format: {id_value}, Error: {str(e)}")
        return None


def get_uuid_str(id_value: Optional[Union[str, uuid.UUID]]) -> Optional[str]:
    """
    Convert a UUID object or string to a formatted UUID string.

    Args:
        id_value: UUID object or string to convert

    Returns:
        Formatted UUID string or None if conversion fails
    """
    if id_value is None:
        return None

    uuid_obj = ensure_uuid(id_value)
    if uuid_obj:
        return str(uuid_obj)
    return None


def generate_uuid() -> uuid.UUID:
    """
    Generate a new UUID.

    Returns:
        New UUID object
    """
    return uuid.uuid4()
