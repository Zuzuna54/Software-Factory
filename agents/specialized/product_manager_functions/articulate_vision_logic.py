"""
Logic for the articulate_vision method of the ProductManagerAgent.
"""

import select
import uuid
import json
from typing import Dict, Any, Optional
from infra.db.models import Project
from agents.logging import ActivityCategory, ActivityLevel
from infra.db.models import ProjectVision


async def articulate_vision_logic(
    agent: Any,  # ProductManagerAgent instance
    project_id: uuid.UUID,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    operation_name = "articulate_vision"
    agent.activity_logger.start_timer(operation_name)
    execution_time_s = 0  # Initialize execution_time_s
    try:

        project = await agent.db_session.execute(
            select(Project).where(Project.project_id == project_id)
        )
        project_description = project.description
        await agent.activity_logger.log_activity(
            activity_type="vision_articulation_started",
            description=f"Started articulating vision for project {project_id}",
            category=ActivityCategory.SYSTEM,
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
        vision: Dict[str, Any] = {}  # Initialize vision

        generated_text, llm_metadata = await agent.llm_provider.generate_text(prompt)
        await agent.activity_logger.log_activity(
            activity_type="debug_llm_generated_text_vision",
            description=f"Raw generated text from LLM for articulate_vision: {project_id}",
            category=ActivityCategory.SYSTEM,
            level=ActivityLevel.INFO,
            details={
                "project_id": str(project_id),
                "generated_text": generated_text,
                "llm_metadata": llm_metadata,
            },
        )

        try:
            vision = json.loads(generated_text)
        except json.JSONDecodeError as e:
            await agent.activity_logger.log_error(
                error_type="VisionArticulationJSONDecodeError",
                description=f"Error decoding JSON for vision articulation: {str(e)}",
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.ERROR,
                context={
                    "project_id": str(project_id),
                    "raw_response": generated_text,
                    "error_message": str(e),
                },
            )

        if agent.db_session:
            project_vision_data = ProjectVision(
                title=f"Project Vision for {project_id}",
                description=vision.get(
                    "vision_statement",
                    "No explicit description provided in vision object.",
                ),
                project_id=project_id,
                created_by=agent.agent_id,
                vision_statement=vision.get(
                    "vision_statement", "Vision not articulated."
                ),
                target_audience=vision.get("target_audience"),
                key_goals=vision.get(
                    "key_goals", []
                ),  # Ensure default is a list for JSONB
                success_metrics=vision.get(
                    "success_metrics", {}
                ),  # Ensure default is a dict for JSONB
                constraints=vision.get(
                    "constraints", []
                ),  # Ensure default is a list for JSONB
                status="articulated",
            )
            agent.db_session.add(project_vision_data)
            await agent.db_session.commit()

        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=True
        )
        await agent.activity_logger.log_activity(
            activity_type="vision_articulation_completed",
            description=f"Completed vision articulation for project {project_id}",
            category=ActivityCategory.SYSTEM,
            level=ActivityLevel.INFO,
            details={
                "project_id": str(project_id),
                "vision_statement_length": len(vision.get("vision_statement", "")),
            },
            execution_time_ms=int(execution_time_s * 1000),
        )
        return vision
    except Exception as e:
        if agent.db_session:
            await agent.db_session.rollback()
        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=False
        )
        await agent.activity_logger.log_error(
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
