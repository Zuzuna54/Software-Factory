"""
Logic for the analyze_requirements method of the ProductManagerAgent.
"""

import uuid
import json
from typing import Dict, Any, Optional

from sqlalchemy import select

from agents.logging.activity_logger import ActivityCategory, ActivityLevel
from infra.db.models import RequirementsArtifact
from .priority_to_int import priority_to_int


async def analyze_requirements_logic(
    agent: Any,  # ProductManagerAgent instance
    description: str,
    project_id: uuid.UUID,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    operation_name = "analyze_requirements"
    agent.activity_logger.start_timer(operation_name)
    execution_time_s = 0  # Initialize execution_time_s
    try:
        await agent.activity_logger.log_activity(
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
        if agent.llm_provider:
            generated_text, llm_metadata = await agent.llm_provider.generate_text(
                prompt
            )
            await agent.activity_logger.log_activity(
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
                await agent.activity_logger.log_error(
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
            await agent.activity_logger.log_activity(
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

        if agent.db_session:
            requirements_data = structured_requirements.get("requirements")
            if isinstance(requirements_data, dict):
                created_requirements_details = []
                for req_type, reqs in requirements_data.items():
                    if isinstance(reqs, list):
                        for req_data in reqs:
                            if isinstance(req_data, dict) and "statement" in req_data:
                                if not req_data.get("statement"):
                                    await agent.activity_logger.log_activity(
                                        activity_type="skip_requirement_empty_statement",
                                        description=f"Skipping requirement due to missing or empty statement: {req_data}",
                                        category=ActivityCategory.WARNING,
                                        level=ActivityLevel.WARNING,
                                        details={"project_id": str(project_id)},
                                    )
                                    continue

                                await agent.activity_logger.log_activity(
                                    activity_type="extracted_requirement_statement",
                                    description=f"Extracted requirement statement: '{req_data.get('statement')}' (Type: {type(req_data.get('statement'))})",
                                    category=ActivityCategory.OTHER,
                                    level=ActivityLevel.DEBUG,
                                    details={"project_id": str(project_id)},
                                )

                                requirement_artifact = RequirementsArtifact(
                                    project_id=project_id,
                                    artifact_id=uuid.uuid4(),
                                    created_by=agent.agent_id,
                                    title=req_data.get(
                                        "statement", "Unnamed Requirement"
                                    )[:255],
                                    content=req_data.get("statement"),
                                    status=req_data.get("status", "Pending"),
                                    priority=priority_to_int(  # Use the helper function
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
                                agent.db_session.add(requirement_artifact)
                                created_requirements_details.append(req_data)
                await agent.db_session.commit()
                await agent.activity_logger.log_activity(
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
                        RequirementsArtifact.created_by == agent.agent_id,
                    )
                    results = (
                        (await agent.db_session.execute(verify_stmt)).scalars().all()
                    )
                    await agent.activity_logger.log_activity(
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
                    await agent.activity_logger.log_activity(
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
                await agent.activity_logger.log_activity(
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
            await agent.activity_logger.log_activity(
                activity_type="analyze_requirements_no_db_session",  # Corrected activity type
                description=f"No DB session available for analyze_requirements, project {project_id}. Requirements not saved.",
                category=ActivityCategory.WARNING,
                level=ActivityLevel.WARNING,
                details={
                    "project_id": str(project_id),
                },
            )

        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=True
        )
        await agent.activity_logger.log_activity(
            activity_type="requirement_analysis_completed",
            description=f"Completed requirements analysis for project {project_id}",
            category=ActivityCategory.THINKING,
            level=ActivityLevel.INFO,
            details={
                "project_id": str(project_id),
                "requirement_count": sum(
                    len(reqs)
                    for reqs in structured_requirements.get("requirements", {}).values()
                ),
            },
            execution_time_ms=int(execution_time_s * 1000),
        )
        return structured_requirements
    except Exception as e:
        # Log error before raising
        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=False
        )  # stop timer on error
        await agent.activity_logger.log_error(
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
        if agent.db_session:  # Ensure session exists before rollback
            await agent.db_session.rollback()
            await agent.activity_logger.log_activity(
                activity_type="error_commit_requirements_rollback",
                description=f"Rolled back transaction after error during requirements analysis. Error: {str(e)}",
                category=ActivityCategory.DATABASE,
                level=ActivityLevel.ERROR,  # This is an error condition
                details={"project_id": str(project_id), "error_message": str(e)},
            )
        raise
