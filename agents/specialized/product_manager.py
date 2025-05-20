"""
Product Manager Agent for the Autonomous AI Development Team

Responsible for requirement analysis, user story creation, and feature prioritization.
"""

import uuid
import json

# import asyncio # Keep for type hints if needed
from typing import Dict, List, Any, Optional, Union

# from datetime import datetime # No longer used directly here

# from sqlalchemy import select, insert # No longer used directly here
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base_agent import BaseAgent
from agents.logging.activity_logger import (
    # ActivityLogger, # Already initialized in BaseAgent
    # ActivityCategory, # Used in logic files
    ActivityLevel,
    # AgentActivity, # Not directly used here
)
from agents.llm import VertexGeminiProvider
from agents.memory.vector_memory import (
    VectorMemory,
)  # Keep MemoryItem if used as type hint

# from infra.db.models import RequirementsArtifact, ProjectVision, ProjectRoadmap # Used in logic files
# from infra.db.models.artifacts import UserStoryArtifact, FeatureArtifact # Used in logic files
from infra.db.models import ProjectRoadmap  # For generate_roadmap return type

from agents.db.postgres import PostgresClient

# Import the refactored logic functions
from .product_manager_functions import (
    analyze_requirements_logic,
    articulate_vision_logic,
    create_user_stories_logic,
    define_acceptance_criteria_logic,
    generate_roadmap_logic,
    prioritize_features_logic,
    product_manager_think_logic,
)


class ProductManagerAgent(BaseAgent):
    """
    Product Manager Agent for translating high-level requirements into structured tasks.

    Capabilities:
    - Requirement analysis
    - User story creation
    - Feature prioritization
    - Acceptance criteria definition
    - Project vision articulation
    """

    def __init__(
        self,
        agent_id: Optional[uuid.UUID] = None,
        agent_name: str = "Product Manager",
        system_prompt: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        db_client: Optional[PostgresClient] = None,
        llm_provider: Optional[VertexGeminiProvider] = None,
        vector_memory: Optional[VectorMemory] = None,
        min_log_level: Optional[ActivityLevel] = None,
        **kwargs,
    ):
        """
        Initialize a new Product Manager agent.

        Args:
            agent_id: Unique identifier for the agent (generated if not provided)
            agent_name: Human-readable name for the agent
            system_prompt: System prompt for the agent's LLM
            db_session: Database session for persistent operations
            db_client: Database client for communication operations
            llm_provider: LLM provider for natural language capabilities
            vector_memory: Vector memory for semantic retrieval
            min_log_level: Minimum log level for ActivityLogger
            **kwargs: Additional agent-specific configuration
        """
        # Default system prompt for product manager if none provided
        if system_prompt is None:
            system_prompt = """You are a Product Manager agent in an autonomous AI development team.
            Your role is to analyze requirements, create user stories, prioritize features,
            define acceptance criteria, and articulate the project vision.
            Always consider business value, user needs, and technical feasibility.
            Produce clear, structured, and actionable outputs."""

        # Initialize base agent with product_manager type
        super().__init__(
            agent_id=agent_id,
            agent_type="product_manager",
            agent_name=agent_name,
            agent_role="Analyzes requirements, creates user stories, and prioritizes features",
            capabilities=[
                "requirement_analysis",
                "user_story_creation",
                "feature_prioritization",
                "acceptance_criteria_definition",
                "project_vision_articulation",
            ],
            system_prompt=system_prompt,
            db_session=db_session,
            db_client=db_client,
            llm_provider=llm_provider,
            vector_memory=vector_memory,
            min_log_level=min_log_level,
            **kwargs,
        )

    async def analyze_requirements(
        self,
        description: str,
        project_id: uuid.UUID,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await analyze_requirements_logic(self, description, project_id, context)

    async def create_user_stories(
        self,
        requirements: Dict[str, Any],
        project_id: uuid.UUID,
        epic_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        return await create_user_stories_logic(self, requirements, project_id, epic_id)

    async def define_acceptance_criteria(
        self,
        user_story_id: uuid.UUID,
        user_story_description: str,
    ) -> List[Dict[str, str]]:
        return await define_acceptance_criteria_logic(
            self, user_story_id, user_story_description
        )

    async def prioritize_features(
        self,
        project_id: uuid.UUID,
        features_arg: Optional[List[Dict[str, Any]]] = None,
        prioritization_criteria: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        return await prioritize_features_logic(
            self, project_id, features_arg, prioritization_criteria
        )

    async def articulate_vision(
        self,
        project_id: uuid.UUID,
        project_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return await articulate_vision_logic(
            self, project_id, project_description, context
        )

    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return await product_manager_think_logic(self, context)

    # Keep helper methods that are simple and directly related to the class structure,
    # or if they are meant to be overridden by subclasses in a way that logic functions aren't.
    # In this case, _priority_to_int and _parse_llm_json_output were general utility, so moved.

    # def _priority_to_int(self, priority_str: str) -> int:
    #     return priority_to_int(priority_str) # Now calls the imported function

    # async def _parse_llm_json_output(
    #     self,
    #     json_string: str,
    #     llm_metadata: Dict[str, Any],
    #     calling_method_name: str = "unknown_method",
    #     expected_type: type = list,
    # ) -> Union[List[Any], Dict[str, Any]]:
    #     # Pass self.activity_logger to the logic function
    #     return await parse_llm_json_output(
    #         self.activity_logger, json_string, llm_metadata, calling_method_name, expected_type
    #     )

    async def generate_roadmap(self, project_id: uuid.UUID) -> ProjectRoadmap:
        return await generate_roadmap_logic(self, project_id)
