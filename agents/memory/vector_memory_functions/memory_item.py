import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json

from infra.db.models.artifacts import Artifact

logger = logging.getLogger(__name__)

# Placeholder for Artifact type, assuming it's defined elsewhere if needed for type hints
# from infra.db.models import Artifact


class MemoryItem:
    """Represents an item in the agent's memory."""

    def __init__(
        self,
        content: str,
        artifact_id: Optional[uuid.UUID] = None,
        content_type: str = "text",
        category: str = "general",
        tags: List[str] = None,
        importance: float = 0.5,
        created_at: Optional[datetime] = None,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a memory item.

        Args:
            content: The text content of the memory
            artifact_id: Optional ID of an existing artifact this memory is related to
            content_type: Type of content (e.g., 'text', 'code', 'image_description')
            category: Category for organizing memories (e.g., 'conversation', 'knowledge')
            tags: List of tags for filtering and retrieval
            importance: A value from 0 to 1 indicating importance (higher = more important)
            created_at: When this memory was created
            embedding: Vector embedding of the content if already computed
            metadata: Additional metadata associated with this memory
        """
        self.content = content
        self.artifact_id = artifact_id
        self.content_type = content_type
        self.category = category
        self.tags = tags or []
        self.importance = importance
        self.created_at = created_at or datetime.utcnow()
        self.embedding = embedding
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert memory item to dictionary."""
        return {
            "content": self.content,
            "artifact_id": str(self.artifact_id) if self.artifact_id else None,
            "content_type": self.content_type,
            "category": self.category,
            "tags": self.tags,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        """Create memory item from dictionary."""
        artifact_id = data.get("artifact_id")
        if artifact_id and isinstance(artifact_id, str):
            artifact_id = uuid.UUID(artifact_id)

        created_at = data.get("created_at")
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            content=data["content"],
            artifact_id=artifact_id,
            content_type=data.get("content_type", "text"),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            importance=data.get("importance", 0.5),
            created_at=created_at,
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def from_artifact(cls, artifact: "Artifact") -> "MemoryItem":
        if artifact is None:
            logger.warning("MemoryItem.from_artifact received a None artifact.")
            return cls(content="Error: Null artifact provided", category="error")

        content = artifact.content or ""
        tags = []

        # Safely process extra_data to ensure metadata_val is a dict
        metadata_val = artifact.extra_data
        if isinstance(metadata_val, str):
            try:
                parsed_json = json.loads(metadata_val)
                if isinstance(parsed_json, dict):
                    metadata_val = parsed_json
                else:
                    metadata_val = {
                        "raw_extra_data": metadata_val,
                        "parsed_non_dict_extra_data": parsed_json,
                    }
            except json.JSONDecodeError:
                metadata_val = {"raw_extra_data": metadata_val}
        elif not isinstance(metadata_val, dict):
            metadata_val = {}  # Default to empty dict if None or other non-dict type

        # Now metadata_val is guaranteed to be a dict
        tags = metadata_val.get("tags", [])
        if not isinstance(tags, list):  # Ensure tags is a list
            logger.warning(
                f"Tags field in metadata for artifact {artifact.artifact_id} was not a list, defaulting to empty. Found: {tags}"
            )
            tags = []

        project_id_from_meta = metadata_val.get("project_id")
        category = metadata_val.get("category", artifact.artifact_type)
        importance = metadata_val.get("importance", 0.5)
        content_type = metadata_val.get("content_type", "text")
        last_accessed_at_str = metadata_val.get("last_accessed_at")

        last_accessed_at_dt = None
        if isinstance(last_accessed_at_str, str):
            try:
                last_accessed_at_dt = datetime.fromisoformat(
                    last_accessed_at_str.replace("Z", "+00:00")
                )
            except ValueError:
                logger.warning(
                    f"Could not parse last_accessed_at string: {last_accessed_at_str} for artifact {artifact.artifact_id}"
                )
        elif isinstance(last_accessed_at_str, datetime):
            last_accessed_at_dt = last_accessed_at_str

        # Store last_accessed_at in metadata if it exists
        if last_accessed_at_dt:
            metadata_val["last_accessed_at"] = last_accessed_at_dt.isoformat()

        # Handle project_id: artifact.project_id is UUID, project_id_from_meta might be str
        final_project_id = artifact.project_id
        if not final_project_id and project_id_from_meta:
            try:
                final_project_id = uuid.UUID(str(project_id_from_meta))
            except ValueError:
                logger.warning(
                    f"Invalid UUID string for project_id in metadata: {project_id_from_meta} for artifact {artifact.artifact_id}"
                )

        # Store project_id in metadata
        if final_project_id:
            metadata_val["project_id"] = str(final_project_id)

        # Handle embedding: Artifact model might not always have an embedding attribute directly
        embedding_value = None
        if hasattr(artifact, "embedding") and artifact.embedding is not None:
            embedding_value = artifact.embedding
        elif "embedding" in metadata_val and metadata_val["embedding"] is not None:
            # Fallback to checking metadata if not on artifact directly (e.g. older schema or indirect storage)
            embedding_value = metadata_val["embedding"]

        return cls(
            artifact_id=artifact.artifact_id,
            content=content,
            content_type=content_type,
            category=category,
            tags=tags,
            embedding=embedding_value,
            importance=float(importance),  # Ensure importance is float
            created_at=artifact.created_at,
            metadata=metadata_val,
        )
