"""
Logic for the define_acceptance_criteria method of the ProductManagerAgent.
"""

import uuid
import json
from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.logging.activity_logger import ActivityCategory, ActivityLevel
from infra.db.models import (
    UserStoryArtifact,  # Changed from RequirementsArtifact
)


async def define_acceptance_criteria_logic(
    agent: Any,  # ProductManagerAgent instance
    user_story_id: uuid.UUID,
    user_story_description: str,
) -> List[Dict[str, str]]:
    operation_name = "define_acceptance_criteria"
    agent.activity_logger.start_timer(operation_name)
    execution_time_s = 0  # Initialize execution_time_s
    try:
        await agent.activity_logger.log_activity(
            activity_type="acceptance_criteria_definition_started",
            description=f"Started defining acceptance criteria for user story {user_story_id}",
            category=ActivityCategory.THINKING,
            level=ActivityLevel.INFO,
            details={
                "user_story_id": str(user_story_id),
                "user_story_description": user_story_description[:500],  # Log a summary
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

        generated_text, llm_metadata = await agent.llm_provider.generate_text(prompt)
        try:
            acceptance_criteria = json.loads(generated_text)
            if not isinstance(acceptance_criteria, list):
                acceptance_criteria = [acceptance_criteria]
        except json.JSONDecodeError:
            await agent.activity_logger.log_error(
                error_type="AcceptanceCriteriaDefinitionJSONDecodeError",
                description=f"Error decoding JSON for acceptance criteria definition: {str(e)}",
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.ERROR,
                context={
                    "user_story_id": str(user_story_id),
                    "raw_response": generated_text,
                },
            )

        if agent.db_session:
            # Assuming UserStoryArtifact is stored in RequirementsArtifact table or a related one
            # If UserStoryArtifact has its own model, replace RequirementsArtifact here
            query = select(UserStoryArtifact).where(
                UserStoryArtifact.artifact_id == user_story_id
            )
            result = await agent.db_session.execute(query)
            user_story_artifact = result.scalar_one_or_none()
            if user_story_artifact:
                # Assuming acceptance_criteria is a field in the artifact model (e.g. JSONB)
                if hasattr(
                    user_story_artifact, "acceptance_criteria"
                ):  # Check if the attribute exists
                    user_story_artifact.acceptance_criteria = acceptance_criteria
                elif hasattr(user_story_artifact, "extra_data") and isinstance(
                    user_story_artifact.extra_data, dict
                ):  # Fallback to extra_data if acceptance_criteria field doesn't exist or is None
                    user_story_artifact.extra_data["acceptance_criteria"] = (
                        acceptance_criteria
                    )
                else:  # Fallback: log a warning if no place to store
                    await agent.activity_logger.log_activity(
                        activity_type="warning_no_field_for_acceptance_criteria",
                        description=f"User story artifact {user_story_id} does not have a standard field (extra_data or acceptance_criteria) to store acceptance criteria.",
                        category=ActivityCategory.DATABASE,
                        level=ActivityLevel.WARNING,
                        details={
                            "user_story_id": str(user_story_id),
                            "data_to_store": acceptance_criteria,
                        },
                    )
                await agent.db_session.commit()
            else:
                await agent.activity_logger.log_activity(
                    activity_type="acceptance_criteria_warning_user_story_not_found",
                    description=f"User story {user_story_id} not found in database when trying to add acceptance criteria.",
                    category=ActivityCategory.DATABASE,
                    level=ActivityLevel.WARNING,
                    details={"user_story_id": str(user_story_id)},
                )

        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=True
        )
        await agent.activity_logger.log_activity(
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
        if agent.db_session:
            await agent.db_session.rollback()
        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=False
        )
        await agent.activity_logger.log_error(
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
