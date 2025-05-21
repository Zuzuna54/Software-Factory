"""
Logic for the generate_roadmap method of the ProductManagerAgent.
"""

import json
import select
import uuid
from typing import Any

# from sqlalchemy.ext.asyncio import AsyncSession # Not used yet
from agents.logging import ActivityCategory, ActivityLevel
from infra.db.models import (
    ProjectRoadmap,
    Project,
    UserStoryArtifact,
    FeatureArtifact,
    EpicArtifact,
    ProjectVision,
)


# TODO: Implement the actual roadmap generation logic
async def generate_roadmap_logic(
    agent: Any, project_id: uuid.UUID  # ProductManagerAgent instance
) -> ProjectRoadmap:
    operation_name = "generate_roadmap"
    """_summary_

    Args:
        agent (Any): _description_
        project_id (uuid.UUID): _description_

    Returns:
        ProjectRoadmap: _description_
    """
    # Placeholder implementation - replace with actual logic
    # Implement the actual logic here
    # get project description from the db via Project model
    try:
        agent.activity_logger.start_timer("generate_roadmap")
        execution_time_ms = 0
        await agent.activity_logger.log_activity(
            activity_type="generate_roadmap_started",
            description=f"Roadmap generation started for project {project_id}",
            details={"project_id": str(project_id)},
            context={"project_description": description},
            category=ActivityCategory.SYSTEM,
            level=ActivityLevel.INFO,
            execution_time_ms=0,
        )

        project = await agent.db_session.execute(
            select(Project).where(Project.project_id == project_id)
        )
        description = project.description

        # Fetch the user stories, features, epics from the db via UserStoryArtifact, FeatureArtifact, EpicArtifact models
        user_stories = await agent.db_session.execute(
            select(UserStoryArtifact).where(UserStoryArtifact.project_id == project_id)
        )
        features = await agent.db_session.execute(
            select(FeatureArtifact).where(FeatureArtifact.project_id == project_id)
        )
        epics = await agent.db_session.execute(
            select(EpicArtifact).where(EpicArtifact.project_id == project_id)
        )
        vision = await agent.db_session.execute(
            select(ProjectVision).where(ProjectVision.project_id == project_id)
        )

        prompt = f"""
        Create a roadmap for the project {project_id} using the following information:
        - Project Description: {description}
        - Project Vision: {vision}
        - User Stories: {user_stories}
        - Features: {features}
        - Epics: {epics}

        Create a roadmap that is sequenced in a way that is easy to understand and follow, and that is aligned with the project vision.
        Ensure that the roadmap is not too detailed, but rather a high-level overview.
        
        Format your response as a JSON Object representing the roadmap.
        Each roadmap object should have the following fields:
        - name: string
        - dependencies: list of strings
        - time horizon: string
        - milestones: list of strings
        - deliverables: list of strings
        - risks: list of strings
        - feature_sequence: list of strings
        - phases: list of roadmap phases containing the following fields:
            - name: string
            - duration_weeks: int
            - goals: list of strings
            - status: string
            - description: string
            - dependencies: list of strings
        """
        generated_text = await agent.llm_provider.generate_text(prompt)
        try:
            roadmap_data = json.loads(generated_text)
        except json.JSONDecodeError as e:
            await agent.activity_logger.log_error(
                error_type="RoadmapGenerationJSONParseError",
                description=f"Failed to parse LLM response as JSON for project {project_id}: {str(e)}",
                exception=e,
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.ERROR,
                context={"project_id": str(project_id), "raw_response": generated_text},
            )
            raise

        if agent.db_session:
            new_roadmap = ProjectRoadmap(
                artifact_id=uuid.uuid4(),
                project_id=project_id,
                time_horizon=roadmap_data["time_horizon"],
                milestones=roadmap_data["milestones"],
                feature_sequence=roadmap_data["feature_sequence"],
                dependencies=roadmap_data["dependencies"],
                status="draft",
                timeline_start_date=None,
                timeline_end_date=None,
                phases=roadmap_data["phases"],
                deliverables=roadmap_data["deliverables"],
                risks=roadmap_data["risks"],
            )

            agent.db_session.add(new_roadmap)
            await agent.db_session.commit()
            execution_time_ms = agent.activity_logger.stop_timer("generate_roadmap")
            await agent.activity_logger.log_activity(
                activity_type="generate_roadmap_completed",
                description=f"Placeholder roadmap generated and saved for project {project_id}",
                details={"roadmap_id": str(new_roadmap.id)},
                context={"roadmap_data": roadmap_data},
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.INFO,
                execution_time_ms=execution_time_ms,
            )
            return new_roadmap
    except Exception as e:
        if agent.db_session:
            await agent.db_session.rollback()
        execution_time_ms = await agent.activity_logger.stop_timer(
            operation_name, success=False
        )
        await agent.activity_logger.log_activity(
            activity_type="generate_roadmap_failed_no_db",
            description=f"Roadmap generation failed for project {project_id} due to no DB session",
            details={"project_id": str(project_id)},
            category=ActivityCategory.SYSTEM,
            level=ActivityLevel.ERROR,
            execution_time_ms=execution_time_ms,
        )
        raise
