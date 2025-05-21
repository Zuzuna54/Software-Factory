"""
Logic for the create_user_stories method of the ProductManagerAgent.
"""

import uuid
import json
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from agents.logging.activity_logger import ActivityCategory, ActivityLevel
from infra.db.models.artifacts import UserStoryArtifact
from .priority_to_int import priority_to_int


async def create_user_stories_logic(
    agent: Any,  # ProductManagerAgent instance
    requirements: Dict[str, Any],
    project_id: uuid.UUID,
    epic_id: Optional[uuid.UUID] = None,
) -> List[Dict[str, Any]]:
    operation_name = "create_user_stories"
    agent.activity_logger.start_timer(operation_name)
    execution_time_s = 0  # Initialize execution_time_s
    try:
        await agent.activity_logger.log_activity(
            activity_type="user_story_creation_started",
            description=f"Started creating user stories for project {project_id}",
            category=ActivityCategory.THINKING,
            level=ActivityLevel.INFO,
            details={
                "project_id": str(project_id),
                "requirement_count": sum(
                    len(reqs) for reqs in requirements.get("requirements", {}).values()
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

        generated_text, llm_metadata = await agent.llm_provider.generate_text(prompt)
        try:
            user_stories = json.loads(generated_text)
            if not isinstance(user_stories, list):
                user_stories = [user_stories]
        except json.JSONDecodeError:
            await agent.activity_logger.log_error(
                error_type="UserStoryCreationJSONDecodeError",
                description=f"Error decoding JSON for user story creation: {str(e)}",
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.ERROR,
                context={"project_id": str(project_id), "raw_response": generated_text},
            )

        if agent.db_session:
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
                        priority=priority_to_int(  # Use the helper function
                            story.get("priority", "Medium")
                        ),
                        created_by=agent.agent_id,
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
                    agent.db_session.add(story_artifact)
            await agent.db_session.commit()

        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=True
        )
        await agent.activity_logger.log_activity(
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
        if agent.db_session:
            await agent.db_session.rollback()
        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=False
        )
        await agent.activity_logger.log_error(
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
