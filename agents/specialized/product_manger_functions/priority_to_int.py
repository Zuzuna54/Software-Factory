"""
Helper function to convert priority strings to integers.
"""


def priority_to_int(priority_str: str) -> int:
    """
    Convert string priority to integer for database storage.

    Args:
        priority_str: Priority as string (High, Medium, Low, etc.)

    Returns:
        Integer priority (1 is highest)
    """
    priority_map = {"critical": 1, "high": 2, "medium": 3, "low": 4, "optional": 5}

    # Normalize the string
    normalized = priority_str.lower().strip()

    # Return the mapped priority or a default
    return priority_map.get(normalized, 3)  # Default to Medium (3)
