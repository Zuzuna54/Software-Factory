"""
Product Manager Agent for the Autonomous AI Development Team

Responsible for requirement analysis, user story creation, and feature prioritization.
"""

import uuid
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from agents.base_agent import BaseAgent
from agents.logging.activity_logger import (
    ActivityLogger,
    ActivityCategory,
    ActivityLevel,
    AgentActivity,
)
from agents.llm import VertexGeminiProvider
from agents.memory.vector_memory import MemoryItem, VectorMemory
from infra.db.models import RequirementsArtifact, ProjectVision, ProjectRoadmap
from infra.db.models.artifacts import UserStoryArtifact, FeatureArtifact

# Added imports for db_client and ActivityLogger
from agents.db.postgres import PostgresClient


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
        operation_name = "analyze_requirements"
        self.activity_logger.start_timer(operation_name)
        try:
            await self.activity_logger.log_activity(
                activity_type="requirement_analysis_started",
                description=f"Started analyzing requirements for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "description_length": len(description),
                    "context": context or {},
                },
            )

            prompt = f"""Analyze the following project description and generate a structured list of functional requirements.
                        Project Description:
            {description}

                        Context: {json.dumps(context) if context else "N/A"}

                        Output a JSON object with a single top-level key "requirements".
                        The "requirements" key should map to an object where keys are requirement types (e.g., "functional").
                        Each requirement type should map to a list of requirement objects.
                        Each requirement object must have:
                        - "statement": (string) The requirement statement.
                        - "priority": (string) "High", "Medium", or "Low".
                        - "rationale": (string) Justification for the requirement.

                        Example:
                        {{
                        "requirements": {{
                            "functional": [
                            {{
                                "statement": "User can log in with email and password.",
                                "priority": "High",
                                "rationale": "Core access functionality."
                            }}
                            ]
                        }}
                        }}
                        Focus on "functional" requirements for now.
                        Do not suggest non-functional requirements or implementation challenges.
                        Provide at least 5 functional requirements if possible from the description.
                        Ensure the output is a single, valid JSON object.
                    """

            structured_requirements: Dict[str, Any] = {}
            if self.llm_provider:
                generated_text, llm_metadata = await self.llm_provider.generate_text(
                    prompt
                )
                await self.activity_logger.log_activity(
                    activity_type="debug_analyze_requirements_llm_raw_output",
                    description=f"Raw LLM output for analyze_requirements, project {project_id}",
                    category=ActivityCategory.OTHER,
                    level=ActivityLevel.DEBUG,
                    details={
                        "project_id": str(project_id),
                        "generated_text": generated_text,
                        "llm_metadata": llm_metadata,
                    },
                )
                try:
                    structured_requirements = json.loads(generated_text)
                except json.JSONDecodeError as e:
                    await self.activity_logger.log_error(
                        error_type="RequirementAnalysisJSONParseError",
                        description=f"Failed to parse LLM response as JSON for project {project_id}: {str(e)}",
                        exception=e,
                        severity=ActivityLevel.ERROR,
                        context={
                            "project_id": str(project_id),
                            "raw_response": generated_text,
                        },
                    )
                    structured_requirements = {
                        "requirements": {},
                        "parsing_error": f"LLM response was not valid JSON: {str(e)}",
                        "raw_response": generated_text,
                    }
            else:
                await self.activity_logger.log_activity(
                    activity_type="analyze_requirements_no_llm_provider",
                    description=f"No LLM provider for analyze_requirements, project {project_id}. Returning empty.",
                    category=ActivityCategory.WARNING,
                    level=ActivityLevel.WARNING,
                    details={"project_id": str(project_id)},
                )
                structured_requirements = {
                    "requirements": {},
                    "note": "Placeholder requirements - LLM provider not available",
                }

            if self.db_session:
                requirements_data = structured_requirements.get("requirements")
                if isinstance(requirements_data, dict):
                    created_requirements_details = []
                    for req_type, reqs in requirements_data.items():
                        if isinstance(reqs, list):
                            for req_data in reqs:
                                if (
                                    isinstance(req_data, dict)
                                    and "statement" in req_data
                                ):
                                    if not req_data.get("statement"):
                                        await self.activity_logger.log_activity(
                                            activity_type="skip_requirement_empty_statement",
                                            description=f"Skipping requirement due to missing or empty statement: {req_data}",
                                            category=ActivityCategory.WARNING,
                                            level=ActivityLevel.WARNING,
                                            details={"project_id": str(project_id)},
                                        )
                                        continue

                                    await self.activity_logger.log_activity(
                                        activity_type="extracted_requirement_statement",
                                        description=f"Extracted requirement statement: '{req_data.get('statement')}' (Type: {type(req_data.get('statement'))})",
                                        category=ActivityCategory.OTHER,
                                        level=ActivityLevel.DEBUG,
                                        details={"project_id": str(project_id)},
                                    )

                                    requirement_artifact = RequirementsArtifact(
                                        project_id=project_id,
                                        artifact_id=uuid.uuid4(),
                                        created_by=self.agent_id,
                                        title=req_data.get(
                                            "statement", "Unnamed Requirement"
                                        )[:255],
                                        content=req_data.get("statement"),
                                        status=req_data.get("status", "Pending"),
                                        priority=self._priority_to_int(
                                            req_data.get("priority", "Medium")
                                        ),
                                        reasoning=req_data.get("rationale"),
                                        stakeholder_value=req_data.get(
                                            "business_value", ""
                                        ),
                                        extra_data={
                                            "requirement_type": req_type,
                                            "challenges": req_data.get(
                                                "challenges",
                                                [],
                                            ),
                                            "raw_input": description[:1000],
                                        },
                                    )
                                    self.db_session.add(requirement_artifact)
                                    created_requirements_details.append(req_data)
                    await self.db_session.commit()
                    await self.activity_logger.log_activity(
                        activity_type="debug_commit_requirements",
                        description=f"Committed {len(created_requirements_details)} requirement artifacts in agent.",
                        category=ActivityCategory.DATABASE,
                        level=ActivityLevel.DEBUG,
                        details={
                            "project_id": str(project_id),
                            "count": len(created_requirements_details),
                        },
                    )

                    # IMMEDIATE INTERNAL VERIFICATION QUERY (will query committed data)
                    try:
                        verify_stmt = select(RequirementsArtifact).where(
                            RequirementsArtifact.project_id == project_id,
                            RequirementsArtifact.created_by == self.agent_id,
                        )
                        results = (
                            (await self.db_session.execute(verify_stmt)).scalars().all()
                        )
                        await self.activity_logger.log_activity(
                            activity_type="debug_internal_req_verification",
                            description=f"Internal verification query found {len(results)} requirements artifacts after commit.",
                            category=ActivityCategory.DATABASE,
                            level=ActivityLevel.DEBUG,
                            details={
                                "project_id": str(project_id),
                                "count_found": len(results),
                                "ids_found": [str(r.artifact_id) for r in results],
                            },
                        )
                    except Exception as e_verify:
                        await self.activity_logger.log_activity(
                            activity_type="error_internal_req_verification",
                            description=f"Error during internal verification query: {str(e_verify)}",
                            category=ActivityCategory.DATABASE,
                            level=ActivityLevel.ERROR,
                            details={
                                "project_id": str(project_id),
                                "error_message": str(e_verify),
                            },
                        )
                else:
                    await self.activity_logger.log_activity(
                        activity_type="analyze_requirements_invalid_structure",
                        description=f"LLM response for project {project_id} lacked 'requirements' dict or it was malformed.",
                        category=ActivityCategory.WARNING,
                        level=ActivityLevel.WARNING,
                        details={
                            "project_id": str(project_id),
                            "parsed_data": structured_requirements,
                        },
                    )
            else:
                await self.activity_logger.log_activity(
                    activity_type="analyze_requirements_invalid_structure",
                    description=f"LLM response for project {project_id} lacked 'requirements' dict or it was malformed.",
                    category=ActivityCategory.WARNING,
                    level=ActivityLevel.WARNING,
                    details={
                        "project_id": str(project_id),
                        "parsed_data": structured_requirements,
                    },
                )

            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=True
            )
            await self.activity_logger.log_activity(
                activity_type="requirement_analysis_completed",
                description=f"Completed requirements analysis for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "requirement_count": sum(
                        len(reqs)
                        for reqs in structured_requirements.get(
                            "requirements", {}
                        ).values()
                    ),
                },
                execution_time_ms=int(execution_time_s * 1000),
            )
            return structured_requirements
        except Exception as e:
            # Log error before raising
            await self.activity_logger.log_error(
                error_type="RequirementAnalysisError",
                description=f"Error during requirements analysis for project {project_id}: {str(e)}",
                exception=e,
                severity=ActivityLevel.ERROR,
                context={
                    "project_id": str(project_id),
                    "description_length": len(description),
                    "execution_time_ms_before_error": int(execution_time_s * 1000),
                },
            )
            if self.db_session:  # Ensure session exists before rollback
                await self.db_session.rollback()
                await self.activity_logger.log_activity(
                    activity_type="error_commit_requirements_rollback",
                    description=f"Rolled back transaction after error during requirements analysis. Error: {str(e)}",
                    category=ActivityCategory.DATABASE,
                    level=ActivityLevel.ERROR,  # This is an error condition
                    details={"project_id": str(project_id), "error_message": str(e)},
                )
            raise

    async def create_user_stories(
        self,
        requirements: Dict[str, Any],
        project_id: uuid.UUID,
        epic_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        start_time = (
            datetime.utcnow()
        )  # Old timer, replaced by activity_logger.start_timer
        operation_name = "create_user_stories"
        self.activity_logger.start_timer(operation_name)
        try:
            await self.activity_logger.log_activity(
                activity_type="user_story_creation_started",
                description=f"Started creating user stories for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "requirement_count": sum(
                        len(reqs)
                        for reqs in requirements.get("requirements", {}).values()
                    ),
                    "epic_id": str(epic_id) if epic_id else None,
                },
            )
            prompt = f"""
            Convert the following structured requirements into well-formed user stories
            following the format: "As a [type of user], I want [goal] so that [benefit]"

            REQUIREMENTS:
            {json.dumps(requirements)}

            For each user story:
            1. Create a clear title
            2. Write a detailed description in the standard format
            3. Specify the type of user
            4. Identify the primary goal
            5. Explain the benefit/value
            6. Add any notes about implementation considerations

            Create only the most essential user stories that cover the requirements.
            Combine requirements into cohesive stories where appropriate.
            Focus on delivering value to end users.

            Format your response as a JSON array of user story objects.
            """
            if self.llm_provider:
                generated_text, llm_metadata = await self.llm_provider.generate_text(
                    prompt
                )
                try:
                    user_stories = json.loads(generated_text)
                    if not isinstance(user_stories, list):
                        user_stories = [user_stories]
                except json.JSONDecodeError:
                    user_stories = [
                        {
                            "title": "Error parsing user stories",
                            "description": "Unable to parse LLM response as JSON",
                            "raw_response": generated_text,
                            "parsing_error": "LLM response was not valid JSON",
                        }
                    ]
            else:
                user_stories = [
                    {
                        "title": "Sample User Story",
                        "description": "As a user, I want to log in so that I can access my account",
                        "user_type": "User",
                        "goal": "Log in to the system",
                        "benefit": "Access my account",
                        "notes": "Placeholder user story - LLM provider not available",
                    }
                ]
            if self.db_session:
                for story in user_stories:
                    if isinstance(story, dict):
                        notes_data = story.get("notes", "")
                        if isinstance(notes_data, list):
                            processed_reasoning = "\n".join(str(n) for n in notes_data)
                        else:
                            processed_reasoning = str(notes_data)

                        story_artifact = UserStoryArtifact(
                            project_id=project_id,
                            title=story.get("title", "")[:255],
                            content=story.get("description", ""),
                            priority=self._priority_to_int(
                                story.get("priority", "Medium")
                            ),
                            created_by=self.agent_id,
                            reasoning=processed_reasoning,
                            status="Draft",
                            parent_id=epic_id,
                            stakeholder_value=story.get("benefit", ""),
                            extra_data={
                                "user_type": story.get("user_type", ""),
                                "goal": story.get("goal", ""),
                                "benefit": story.get("benefit", ""),
                            },
                        )
                        self.db_session.add(story_artifact)
                await self.db_session.commit()

            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=True
            )
            await self.activity_logger.log_activity(
                activity_type="user_story_creation_completed",
                description=f"Completed user story creation for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "user_story_count": len(user_stories),
                    "epic_id": str(epic_id) if epic_id else None,
                },
                execution_time_ms=int(execution_time_s * 1000),
            )
            return user_stories
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=False
            )
            await self.activity_logger.log_error(
                error_type="UserStoryCreationError",
                description=f"Error during user story creation for project {project_id}: {str(e)}",
                exception=e,
                severity=ActivityLevel.ERROR,
                context={
                    "project_id": str(project_id),
                    "epic_id": str(epic_id) if epic_id else None,
                    "execution_time_ms_before_error": int(execution_time_s * 1000),
                },
            )
            raise

    async def define_acceptance_criteria(
        self,
        user_story_id: uuid.UUID,
        user_story_description: str,
    ) -> List[Dict[str, str]]:
        operation_name = "define_acceptance_criteria"
        self.activity_logger.start_timer(operation_name)
        try:
            await self.activity_logger.log_activity(
                activity_type="acceptance_criteria_definition_started",
                description=f"Started defining acceptance criteria for user story {user_story_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "user_story_id": str(user_story_id),
                    "user_story_description": user_story_description[
                        :500
                    ],  # Log a summary
                },
            )
            prompt = f"""
            Create detailed acceptance criteria for the following user story:
            
            USER STORY:
            {user_story_description}
            
            Instructions:
            - Generate 1-2 concise acceptance criteria.
            - Each criterion MUST be a JSON object.
            - Each JSON object MUST have the keys: "title" (string), "given" (string), "when" (string), "then" (string).
            
            Format your response as a JSON array of acceptance criteria objects.
            """
            if self.llm_provider:
                generated_text, llm_metadata = await self.llm_provider.generate_text(
                    prompt
                )
                try:
                    acceptance_criteria = json.loads(generated_text)
                    if not isinstance(acceptance_criteria, list):
                        acceptance_criteria = [acceptance_criteria]
                except json.JSONDecodeError:
                    acceptance_criteria = [
                        {
                            "title": "Error parsing acceptance criteria",
                            "description": "Unable to parse LLM response as JSON",
                            "raw_response": generated_text,
                            "parsing_error": "LLM response was not valid JSON",
                        }
                    ]
            else:
                acceptance_criteria = [
                    {
                        "title": "Successful Login",
                        "given": "User has valid credentials",
                        "when": "User submits login form",
                        "then": "User is authenticated and redirected to dashboard",
                        "edge_cases": "Handles rate limiting and lockout",
                    }
                ]
            if self.db_session:
                query = select(RequirementsArtifact).where(
                    RequirementsArtifact.artifact_id == user_story_id
                )
                result = await self.db_session.execute(query)
                user_story = result.scalar_one_or_none()
                if user_story:
                    user_story.acceptance_criteria = acceptance_criteria
                    await self.db_session.commit()
                else:
                    # Use activity_logger for warnings too
                    await self.activity_logger.log_activity(
                        activity_type="acceptance_criteria_warning_user_story_not_found",
                        description=f"User story {user_story_id} not found in database when trying to add acceptance criteria.",
                        category=ActivityCategory.DATABASE,
                        level=ActivityLevel.WARNING,
                        details={"user_story_id": str(user_story_id)},
                    )

            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=True
            )
            await self.activity_logger.log_activity(
                activity_type="acceptance_criteria_definition_completed",
                description=f"Completed acceptance criteria for user story {user_story_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "user_story_id": str(user_story_id),
                    "acceptance_criteria_count": len(acceptance_criteria),
                },
                execution_time_ms=int(execution_time_s * 1000),
            )
            return acceptance_criteria
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=False
            )
            await self.activity_logger.log_error(
                error_type="AcceptanceCriteriaDefinitionError",
                description=f"Error during acceptance criteria definition for user story {user_story_id}: {str(e)}",
                exception=e,
                severity=ActivityLevel.ERROR,
                context={
                    "user_story_id": str(user_story_id),
                    "execution_time_ms_before_error": int(execution_time_s * 1000),
                },
            )
            raise

    async def prioritize_features(
        self,
        project_id: uuid.UUID,
        features_arg: Optional[List[Dict[str, Any]]] = None,
        prioritization_criteria: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        operation_name = "prioritize_features"
        self.activity_logger.start_timer(operation_name)
        try:
            await self.activity_logger.log_activity(
                activity_type="feature_prioritization_started",
                description=f"Started prioritizing features for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "feature_count": (
                        len(features_arg) if features_arg else "retrieving from DB"
                    ),
                    "prioritization_criteria": prioritization_criteria,
                },
            )

            features_from_db: List[FeatureArtifact] = []
            if features_arg:
                feature_ids_from_arg = []
                for item_in_arg in features_arg:
                    item_id_str = None
                    if isinstance(item_in_arg, dict):
                        # If it's a dict (e.g., from LLM), it might have 'id' or 'artifact_id'
                        # For consistency with ORM, prefer 'artifact_id' if available, else 'id'
                        item_id_str = str(
                            item_in_arg.get("artifact_id", item_in_arg.get("id"))
                        )
                    elif hasattr(item_in_arg, "artifact_id") and isinstance(
                        getattr(item_in_arg, "artifact_id"), uuid.UUID
                    ):
                        item_id_str = str(item_in_arg.artifact_id)
                    elif hasattr(
                        item_in_arg, "id"
                    ) and isinstance(  # Fallback for older dicts if any
                        getattr(item_in_arg, "id"), uuid.UUID
                    ):
                        # Log a warning if we fall back to 'id' for an ORM-like object
                        await self.activity_logger.log_activity(
                            activity_type="warning_ambiguous_id_in_features_arg",
                            description=f"Feature object in features_arg for project {project_id} has 'id' but not 'artifact_id'. Using 'id'. Object type: {type(item_in_arg)}",
                            category=ActivityCategory.WARNING,
                            level=ActivityLevel.WARNING,
                            details={
                                "project_id": str(project_id),
                                "item_details": str(item_in_arg)[
                                    :200
                                ],  # Log part of the item for debugging
                            },
                        )
                        item_id_str = str(item_in_arg.id)

                    if (
                        item_id_str and item_id_str.lower() != "none"
                    ):  # Basic check for valid UUID string
                        try:
                            feature_ids_from_arg.append(uuid.UUID(item_id_str))
                        except ValueError:
                            await self.activity_logger.log_activity(
                                activity_type="warning_invalid_uuid_in_features_arg",
                                description=f"Invalid UUID string '{item_id_str}' encountered in features_arg for project {project_id}. Skipping.",
                                category=ActivityCategory.WARNING,
                                level=ActivityLevel.WARNING,
                                details={
                                    "project_id": str(project_id),
                                    "invalid_id_str": item_id_str,
                                },
                            )

                if feature_ids_from_arg:
                    await self.activity_logger.log_activity(
                        activity_type="debug_retrieving_features_from_db",
                        description=f"Retrieving FeatureArtifacts from DB based on {len(feature_ids_from_arg)} IDs from features_arg for project {project_id}",
                        category=ActivityCategory.DATABASE,
                        details={
                            "project_id": str(project_id),
                            "queried_ids_count": len(feature_ids_from_arg),
                            "queried_ids_sample": [
                                str(fid) for fid in feature_ids_from_arg[:3]
                            ],  # Log a sample
                            "status_filter": "pending",
                        },
                        level=ActivityLevel.DEBUG,
                    )
                    stmt = select(FeatureArtifact).where(
                        FeatureArtifact.project_id == project_id,
                        FeatureArtifact.artifact_id.in_(feature_ids_from_arg),
                        FeatureArtifact.status == "pending",
                    )
                    result = await self.db_session.execute(stmt)
                    features_from_db = result.scalars().all()
                    await self.activity_logger.log_activity(
                        activity_type="debug_features_retrieved_from_db_for_prioritization",
                        description="Features retrieved from DB based on features_arg IDs for prioritization",
                        category=ActivityCategory.DATABASE,
                        details={
                            "project_id": str(project_id),
                            "retrieved_count": len(features_from_db),
                            "queried_ids": [str(fid) for fid in feature_ids_from_arg],
                            "status_filter": "pending",
                        },
                        level=ActivityLevel.DEBUG,
                    )
            else:
                features_from_db = (
                    (
                        await self.db_session.execute(
                            select(FeatureArtifact)
                            .where(FeatureArtifact.project_id == project_id)
                            .where(FeatureArtifact.status == "pending")
                        )
                    )
                    .scalars()
                    .all()
                )

            if not features_from_db:
                await self.activity_logger.log_activity(
                    activity_type="feature_prioritization_completed_no_features",
                    description=f"No features found/provided to prioritize for project {project_id}",
                    category=ActivityCategory.THINKING,
                    level=ActivityLevel.INFO,
                    details={"project_id": str(project_id)},
                )
                await self.activity_logger.stop_timer(operation_name, success=True)
                return []

            feature_details_prompt_text = "\n".join(
                (
                    f"  - ID: {feature_orm.artifact_id}, Title: {feature_orm.title}, Current Priority: {feature_orm.priority}, Description: {feature_orm.description}"
                    for feature_orm in features_from_db
                )
            )
            prompt = f"""
Analyze the following software features for project '{project_id}':
{feature_details_prompt_text}

Prioritization Criteria (and their weights):
- business_value: 0.3
- technical_feasibility: 0.2
- user_impact: 0.3
- risk: 0.1 (lower is better, e.g. 1 for high risk, 5 for low risk)
- time_to_market: 0.1 (lower is better, e.g. 1 for long, 5 for short)

Based on these criteria, provide a prioritized list of these features.
Your output **MUST** be a JSON list of objects. Each object **MUST** include:
- "id": The **exact ID** of the feature as provided in the input. Do NOT generate new IDs.
- "title": The title of the feature.
- "priority": The new priority ("High", "Medium", or "Low") based on your analysis.
- "rank": An integer rank (1 being the highest priority).
- "rationale": A brief justification for the new priority and rank.

Focus on providing concise, actionable prioritization. Do not include any preamble or explanation outside the JSON structure.
Example of a single item in the JSON list:
{{
  "id": "existing_feature_id_123",
  "title": "Example Feature Title",
  "priority": "High",
  "rank": 1,
  "rationale": "High business value and user impact."
}}

Return **only** the JSON list.
"""
            llm_output_text, llm_metadata = await self.llm_provider.generate_text(
                prompt
            )
            await self.activity_logger.log_activity(
                activity_type="debug_prioritize_features_llm_raw_output",
                description=f"Raw LLM output for prioritize_features, project {project_id}",
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.DEBUG,
                details={
                    "project_id": str(project_id),
                    "generated_text": llm_output_text,
                    "llm_metadata": llm_metadata,
                },
            )

            llm_output = await self._parse_llm_json_output(
                json_string=llm_output_text,
                llm_metadata=llm_metadata,
                calling_method_name="prioritize_features",
                expected_type=list,
            )

            if not llm_output:
                self.logger.error(
                    "Failed to parse LLM output for feature prioritization or output was empty.",
                    extra={
                        "project_id": project_id,
                        "llm_output_text": llm_output_text,
                    },
                )
                # performance_tracker.record(success=False) # TODO: Uncomment when performance_tracker is properly integrated
                # Log error for telemetry
                await self.activity_logger.log_activity(
                    agent_id=self.agent_id,
                    activity_type="error_parsing_llm_prioritization_output",
                    description=(
                        f"Failed to parse LLM JSON output or received empty list "
                        f"during feature prioritization for project {project_id}."
                    ),
                    details={
                        "project_id": project_id,
                        "raw_llm_output": llm_output_text,
                        "parsed_output_type": type(llm_output).__name__,
                        "parsed_output_is_empty": not bool(llm_output),
                    },
                    level=ActivityLevel.ERROR,
                    category=ActivityCategory.AGENT_INTERNAL,
                )
                return []

            updated_features = []

            priority_map = {
                "High": 1,
                "Medium": 2,
                "Low": 3,
                # Add other potential variations if LLM is inconsistent
                "Critical": 0,
                "Essential": 1,
                "Important": 2,
                "Normal": 2,
                "Optional": 3,
                "Trivial": 4,
            }
            default_priority_int = 3  # Default to Low if mapping fails

            for prioritized_feature_data in llm_output:
                feature_id = prioritized_feature_data.get("id")
                if not feature_id:
                    self.logger.warning(
                        "LLM output for prioritized feature missing 'id'. Skipping.",
                        extra={"feature_data": prioritized_feature_data},
                    )
                    continue

                original_orm_object_to_update = next(
                    (
                        f_orm
                        for f_orm in features_from_db
                        if str(f_orm.artifact_id) == feature_id
                    ),
                    None,
                )

                if not original_orm_object_to_update:
                    self.logger.warning(
                        f"Could not find original FeatureArtifact with id {feature_id} "
                        f"from LLM output in the database query results. Skipping update for this feature.",
                        extra={
                            "project_id": project_id,
                            "missing_feature_id": feature_id,
                            "llm_provided_data": prioritized_feature_data,
                            "queried_feature_ids": [
                                str(f.artifact_id) for f in features_from_db
                            ],
                        },
                    )
                    continue

                # Convert string priority to integer
                priority_str = prioritized_feature_data.get("priority")
                priority_int = default_priority_int  # Default
                if priority_str:
                    priority_int = priority_map.get(
                        priority_str.capitalize(), default_priority_int
                    )
                    if priority_str.capitalize() not in priority_map:
                        self.logger.warning(
                            f"Unmapped priority string '{priority_str}' from LLM for feature {feature_id}. "
                            f"Defaulting to priority {default_priority_int}.",
                            extra={
                                "project_id": project_id,
                                "feature_id": feature_id,
                                "received_priority_str": priority_str,
                                "defaulted_to_priority_int": default_priority_int,
                            },
                        )
                else:
                    self.logger.warning(
                        f"LLM output for prioritized feature {feature_id} missing 'priority'. "
                        f"Defaulting to priority {default_priority_int}.",
                        extra={
                            "project_id": project_id,
                            "feature_id": feature_id,
                            "llm_feature_data": prioritized_feature_data,
                            "defaulted_to_priority_int": default_priority_int,
                        },
                    )

                # Update the ORM object
                original_orm_object_to_update.priority = priority_int
                original_orm_object_to_update.status = "reviewed"
                # Store rank and rationale in the extra_data field as JSON
                update_details_for_extra_data = {
                    "prioritization": {
                        "rationale": prioritized_feature_data.get("rationale"),
                        "rank": prioritized_feature_data.get("rank"),
                    }
                }
                # Ensure extra_data is initialized if it's None
                if original_orm_object_to_update.extra_data is None:
                    original_orm_object_to_update.extra_data = {}

                original_orm_object_to_update.extra_data.update(
                    update_details_for_extra_data
                )

                # The main 'content' field of the FeatureArtifact should remain as is (e.g., the feature description)
                # For this method, we are only updating priority, status, and prioritization-specific extra_data.

                self.db_session.add(original_orm_object_to_update)

                updated_features.append(
                    {
                        "id": str(original_orm_object_to_update.artifact_id),
                        "title": original_orm_object_to_update.title,
                        "priority": original_orm_object_to_update.priority,
                        "status": original_orm_object_to_update.status,
                        "content": json.loads(
                            original_orm_object_to_update.content
                            if original_orm_object_to_update.content
                            else "{}"
                        ),  # Keep original content
                        "extra_data": original_orm_object_to_update.extra_data,  # Return updated extra_data
                    }
                )

                await self.db_session.commit()
            await self.activity_logger.stop_timer(operation_name, success=True)

            await self.activity_logger.log_activity(
                activity_type="feature_prioritization_completed",
                description=f"Completed feature prioritization for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "feature_count": len(updated_features),
                },
            )
            return updated_features
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=False
            )
            await self.activity_logger.log_error(
                error_type="FeaturePrioritizationError",
                description=f"Error during feature prioritization for project {project_id}: {str(e)}",
                exception=e,
                severity=ActivityLevel.ERROR,
                context={
                    "project_id": str(project_id),
                    "execution_time_ms_before_error": int(execution_time_s * 1000),
                },
            )
            raise

    async def articulate_vision(
        self,
        project_id: uuid.UUID,
        project_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        operation_name = "articulate_vision"
        self.activity_logger.start_timer(operation_name)
        try:
            await self.activity_logger.log_activity(
                activity_type="vision_articulation_started",
                description=f"Started articulating vision for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "description_length": len(project_description),
                    "context": context,
                },
            )
            prompt = f"""
            Create a compelling project vision statement based on the following project description:
            
            PROJECT DESCRIPTION:
            {project_description}
            
            {f'ADDITIONAL CONTEXT: {json.dumps(context)}' if context else ''}
            
            Your task is to generate a project vision based on the provided information.
            Make the vision aspirational yet achievable, focused on value, and aligned with stakeholder needs.
            The vision should provide clear direction but allow flexibility in implementation.
            
            Your response MUST BE ONLY a single, valid JSON object conforming to the schema below.
            Do not include any other text, explanations, or markdown formatting outside of this JSON object.
            The JSON schema is as follows:
            {{{{
              "vision_statement": "A concise, inspiring vision statement describing what the project aims to achieve.",
              "target_audience": "The primary audience or users who will benefit from this project.",
              "key_goals": ["A list of 3-5 main objectives the project will accomplish."],
              "success_metrics": {{{{
                "metric_name_1": "Description of how success is measured for this key metric.",
                "example_metric_2": "Another example metric and its measurement."
              }}}},
              "constraints": ["A list of notable limitations or boundaries for the project."],
              "unique_value_proposition": "A clear statement explaining what makes this project special or different."
            }}}}
            """
            if self.llm_provider:
                generated_text, llm_metadata = await self.llm_provider.generate_text(
                    prompt
                )
                # Log the raw generated_text from LLM
                await self.activity_logger.log_activity(
                    activity_type="debug_llm_generated_text_vision",  # Differentiated type
                    description=f"Raw generated text from LLM for articulate_vision: {project_id}",
                    category=ActivityCategory.SYSTEM,  # Changed category from DEBUG to SYSTEM
                    level=ActivityLevel.INFO,  # Or DEBUG
                    details={
                        "project_id": str(project_id),
                        "generated_text": generated_text,
                        "llm_metadata": llm_metadata,
                    },
                )

                try:
                    vision = json.loads(generated_text)
                    if not isinstance(vision, dict):  # Ensure it's a dict
                        # If it's not a dict (e.g. LLM returned a list or just a string)
                        await self.activity_logger.log_error(
                            error_type="VisionArticulationJSONTypeError",
                            description=f"LLM response for vision articulation was not a JSON object for project {project_id}",
                            severity=ActivityLevel.ERROR,
                            context={
                                "project_id": str(project_id),
                                "raw_response": generated_text,
                                "parsed_type": type(vision).__name__,
                            },
                        )
                        vision = {  # Fallback structure
                            "vision_statement": "Error: LLM response was not a JSON object.",
                            "parsing_error": "LLM response was not a JSON object",
                            "raw_response": generated_text,
                        }

                except json.JSONDecodeError as e:
                    await self.activity_logger.log_error(
                        error_type="VisionArticulationJSONParseError",
                        description=f"Failed to parse LLM response for vision as JSON for project {project_id}: {str(e)}",
                        exception=e,
                        severity=ActivityLevel.ERROR,
                        context={
                            "project_id": str(project_id),
                            "raw_response": generated_text,
                        },
                    )
                    vision = {  # Fallback structure
                        "vision_statement": f"Error parsing LLM response: {str(e)}",
                        "parsing_error": f"LLM response was not valid JSON: {str(e)}",
                        "raw_response": generated_text,
                    }
            else:
                await self.activity_logger.log_activity(
                    activity_type="articulate_vision_no_llm_provider",
                    description=f"No LLM provider for articulate_vision, project {project_id}. Returning placeholder.",
                    category=ActivityCategory.WARNING,
                    level=ActivityLevel.WARNING,
                    details={"project_id": str(project_id)},
                )
                vision = {
                    "vision_statement": "Build a transformative platform that helps users achieve their goals efficiently (placeholder)",
                    "target_audience": "Placeholder - LLM provider not available",
                    "key_goals": ["Goal 1", "Goal 2", "Goal 3"],
                    "success_metrics": {
                        "metric1": "description",
                        "metric2": "description",
                    },
                    "constraints": ["Constraint 1", "Constraint 2"],
                    "unique_value_proposition": "Placeholder unique value proposition",
                }

            # Log the generated vision before saving
            await self.activity_logger.log_activity(
                activity_type="debug_vision_content_before_save",
                description=f"Generated vision content for project {project_id}",
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.INFO,
                details={
                    "vision_dict": vision,
                    "statement_to_be_saved": vision.get(
                        "vision_statement", "Vision not articulated."
                    ),
                },
            )

            if self.db_session:
                project_vision = ProjectVision(
                    title=f"Project Vision for {project_id}",
                    description=vision.get("description", "No description provided."),
                    project_id=project_id,
                    created_by=self.agent_id,
                    vision_statement=vision.get(
                        "vision_statement", "Vision not articulated."
                    ),
                    target_audience=vision.get("target_audience"),
                    key_goals=vision.get("key_goals", {}),
                    success_metrics=vision.get("success_metrics", {}),
                    constraints=vision.get("constraints", {}),
                    status="articulated",
                )
                self.db_session.add(project_vision)
                await self.db_session.commit()

            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=True
            )
            await self.activity_logger.log_activity(
                activity_type="vision_articulation_completed",
                description=f"Completed vision articulation for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "project_id": str(project_id),
                    "vision_statement_length": len(vision.get("vision_statement", "")),
                },
                execution_time_ms=int(execution_time_s * 1000),
            )
            return vision
        except Exception as e:
            if self.db_session:
                await self.db_session.rollback()
            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=False
            )
            await self.activity_logger.log_error(
                error_type="VisionArticulationError",
                description=f"Error during vision articulation for project {project_id}: {str(e)}",
                exception=e,
                severity=ActivityLevel.ERROR,
                context={
                    "project_id": str(project_id),
                    "execution_time_ms_before_error": int(execution_time_s * 1000),
                },
            )
            raise

    async def think(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override the base think method to provide specialized product management thinking.

        Args:
            context: Dictionary containing all relevant information needed for thinking

        Returns:
            Dictionary containing the results of the thinking process
        """
        operation_name = "product_manager_think_process"
        self.activity_logger.start_timer(operation_name)
        execution_time_s = 0  # Initialize

        try:
            thought_type = context.get("thought_type", "general_product_management")
            input_context_summary = {
                "context_summary": context.get("summary", "No summary provided"),
                "context_size": len(str(context)),
                "context_type": context.get("type", "unknown"),
                "thought_type_requested": thought_type,
            }

            await self.activity_logger.log_thinking_process(
                thought_type=f"pm_{thought_type}_start",
                description=f"Started product management thinking: {thought_type}",
                reasoning="Agent is about to apply product management logic based on context.",
                input_context=input_context_summary,
            )

            # Retrieve relevant information from vector memory if available
            relevant_info = []
            if self.vector_memory and context.get("query"):  # Check if query key exists
                query_text = context["query"]
                # Use the retrieve_memories method from BaseAgent
                memory_items: List[MemoryItem] = await self.retrieve_memories(
                    query_text=query_text, limit=5
                )
                relevant_info = [item.content for item in memory_items]
                input_context_summary["retrieved_memory_count"] = len(relevant_info)

            # Determine what kind of thinking is required based on context
            # This section defines the "thought process" documentation rather than executing the actions.
            # The actual actions (analyze_requirements, etc.) are called separately.
            # This think method is more about planning or reflecting on what to do.

            result_details = {}

            if thought_type == "requirement_analysis":
                result_details = {
                    "focused_on": "Identifying functional, non-functional, technical, and business requirements",
                    "consideration": "User needs, technical feasibility, and business goals",
                    "output_format": "Structured requirements with categorization and priorities",
                }
            elif thought_type == "user_story_creation":
                result_details = {
                    "focused_on": "User-centric problem statements and value delivery",
                    "consideration": "User personas, goals, and expected benefits",
                    "output_format": "User stories with clear format and acceptance criteria",
                }
            elif thought_type == "feature_prioritization":
                result_details = {
                    "focused_on": "Business value, technical feasibility, user impact, risk, time to market",
                    "consideration": "Strategic alignment, dependencies, resource constraints",
                    "output_format": "Ranked features with scores and rationale",
                }
            elif thought_type == "vision_articulation":
                result_details = {
                    "focused_on": "Aspirational yet achievable project vision",
                    "consideration": "Target audience, key objectives, success metrics, constraints",
                    "output_format": "Vision statement with supporting components",
                }
            else:  # general_product_management
                result_details = {
                    "focused_on": "Identifying product needs and opportunities",
                    "consideration": "Market demand, user feedback, technical capabilities",
                    "output_format": "Structured analysis and recommendations",
                }

            # Construct the main result dictionary
            result = {
                "thought_process": f"Product Management: {thought_type}",
                "decision": context.get(
                    "decision_required", "Plan generated for product management task"
                ),
                "rationale": "Based on product management expertise and provided context.",
                "details": result_details,
                "relevant_context_from_memory": relevant_info,
                "input_context_summary": input_context_summary,
            }

            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=True
            )
            await self.activity_logger.log_activity(
                activity_type=f"pm_thinking_{thought_type}_completed",
                description=f"Completed product management thinking: {thought_type} in {execution_time_s:.2f}s",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={
                    "decision": result.get("decision"),
                    "rationale": result.get("rationale"),
                    "thought_type": thought_type,
                    "output_summary": result_details.get(
                        "output_format", "Generic PM output"
                    ),
                },
                execution_time_ms=int(execution_time_s * 1000),
            )
            return result

        except Exception as e:
            execution_time_s = await self.activity_logger.stop_timer(
                operation_name, success=False
            )
            await self.activity_logger.log_error(
                error_type="ProductManagerThinkingError",
                description=f"Error during product management thinking ({thought_type}): {str(e)}",
                exception=e,
                severity=ActivityLevel.ERROR,
                context={
                    "current_operation": operation_name,
                    "thought_type": thought_type,
                    "input_context_summary": input_context_summary,
                    "execution_time_ms_before_error": int(execution_time_s * 1000),
                },
            )
            raise

    def _priority_to_int(self, priority_str: str) -> int:
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

    async def _parse_llm_json_output(
        self,
        json_string: str,
        llm_metadata: Dict[str, Any],
        calling_method_name: str = "unknown_method",
        expected_type: type = list,  # Default to list, can be dict
    ) -> Union[List[Any], Dict[str, Any]]:
        """
        Parse JSON string from LLM output, with error logging.

        Args:
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
                    self.activity_logger.log_activity(
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
                self.activity_logger.log_error(
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
                self.activity_logger.log_error(
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

    async def generate_roadmap(self, project_id: uuid.UUID) -> ProjectRoadmap:
        # Implementation of generate_roadmap method
        pass
