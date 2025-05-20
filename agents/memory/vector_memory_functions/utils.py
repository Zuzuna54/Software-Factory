import logging
from typing import List, Any, Optional
import numpy as np

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not vec1 or not vec2:
        return 0.0

    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)

    # Handle zero vectors
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(np.dot(vec1_np, vec2_np) / (norm1 * norm2))


def list_to_pgvector(
    embedding: List[float],
) -> Optional[Any]:  # Return type is pgvector.sqlalchemy.Vector
    """Convert a list of floats to pgvector format."""
    if not embedding:
        return None

    try:
        # Convert list to Vector type
        from pgvector.sqlalchemy import Vector  # Keep import local to where it's used

        return Vector(embedding)
    except ImportError:
        logger.error(
            "pgvector.sqlalchemy.Vector could not be imported. pgvector might not be installed correctly."
        )
        return None
    except Exception as e:
        logger.error(f"Error converting to pgvector: {e}")
        return None
