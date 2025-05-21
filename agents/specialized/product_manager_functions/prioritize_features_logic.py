"""
Logic for the prioritize_features method of the ProductManagerAgent.
"""

import uuid
import json
import logging  # Added for self.logger equivalent
from typing import List, Dict, Any, Optional

from sqlalchemy import select

# from sqlalchemy.ext.asyncio import AsyncSession # Not directly used here but often by agent.db_session

from agents.logging.activity_logger import ActivityCategory, ActivityLevel
from infra.db.models.artifacts import (
    FeatureArtifact,
)  # Assuming this is the correct model
from .parse_llm_json_output import parse_llm_json_output


# Get a logger instance, similar to self.logger
logger = logging.getLogger(__name__)


async def prioritize_features_logic(
    agent: Any,  # ProductManagerAgent instance
    project_id: uuid.UUID,
    features_arg: Optional[List[Dict[str, Any]]] = None,
    prioritization_criteria: Optional[
        Dict[str, float]
    ] = None,  # This was not used in original, keeping for signature consistency
) -> List[Dict[str, Any]]:
    operation_name = "prioritize_features"
    agent.activity_logger.start_timer(operation_name)
    execution_time_s = 0  # Initialize execution_time_s
    try:
        await agent.activity_logger.log_activity(
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
                    item_id_str = str(
                        item_in_arg.get("artifact_id", item_in_arg.get("id"))
                    )
                elif hasattr(item_in_arg, "artifact_id") and isinstance(
                    getattr(item_in_arg, "artifact_id"), uuid.UUID
                ):
                    item_id_str = str(item_in_arg.artifact_id)
                elif hasattr(item_in_arg, "id") and isinstance(
                    getattr(item_in_arg, "id"), uuid.UUID
                ):
                    await agent.activity_logger.log_activity(
                        activity_type="warning_ambiguous_id_in_features_arg",
                        description=f"Feature object in features_arg for project {project_id} has 'id' but not 'artifact_id'. Using 'id'. Object type: {type(item_in_arg)}",
                        category=ActivityCategory.WARNING,
                        level=ActivityLevel.WARNING,
                        details={
                            "project_id": str(project_id),
                            "item_details": str(item_in_arg)[:200],
                        },
                    )
                    item_id_str = str(item_in_arg.id)

                if item_id_str and item_id_str.lower() != "none":
                    try:
                        feature_ids_from_arg.append(uuid.UUID(item_id_str))
                    except ValueError:
                        await agent.activity_logger.log_activity(
                            activity_type="warning_invalid_uuid_in_features_arg",
                            description=f"Invalid UUID string '{item_id_str}' encountered in features_arg for project {project_id}. Skipping.",
                            category=ActivityCategory.WARNING,
                            level=ActivityLevel.WARNING,
                            details={
                                "project_id": str(project_id),
                                "invalid_id_str": item_id_str,
                            },
                        )

            if feature_ids_from_arg and agent.db_session:
                await agent.activity_logger.log_activity(
                    activity_type="debug_retrieving_features_from_db",
                    description=f"Retrieving FeatureArtifacts from DB based on {len(feature_ids_from_arg)} IDs from features_arg for project {project_id}",
                    category=ActivityCategory.DATABASE,
                    details={
                        "project_id": str(project_id),
                        "queried_ids_count": len(feature_ids_from_arg),
                        "queried_ids_sample": [
                            str(fid) for fid in feature_ids_from_arg[:3]
                        ],
                        "status_filter": "pending",
                    },
                    level=ActivityLevel.DEBUG,
                )
                stmt = select(FeatureArtifact).where(
                    FeatureArtifact.project_id == project_id,
                    FeatureArtifact.artifact_id.in_(feature_ids_from_arg),
                    FeatureArtifact.status == "pending",
                )
                result = await agent.db_session.execute(stmt)
                features_from_db = result.scalars().all()
                await agent.activity_logger.log_activity(
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
        elif agent.db_session:  # if features_arg is None, fetch all pending for project
            features_from_db = (
                (
                    await agent.db_session.execute(
                        select(FeatureArtifact)
                        .where(FeatureArtifact.project_id == project_id)
                        .where(FeatureArtifact.status == "pending")
                    )
                )
                .scalars()
                .all()
            )

        if not features_from_db:
            await agent.activity_logger.log_activity(
                activity_type="feature_prioritization_completed_no_features",
                description=f"No features found/provided to prioritize for project {project_id}",
                category=ActivityCategory.THINKING,
                level=ActivityLevel.INFO,
                details={"project_id": str(project_id)},
            )
            await agent.activity_logger.stop_timer(operation_name, success=True)
            return []

        feature_details_list = []
        for feature_orm in features_from_db:
            desc_text = getattr(feature_orm, "content", None) or getattr(
                feature_orm, "description", ""
            )
            feature_details_list.append(
                f"  - ID: {feature_orm.artifact_id}, Title: {feature_orm.title}, Current Priority: {feature_orm.priority}, Description: {desc_text}"
            )
        feature_details_prompt_text = "\n".join(feature_details_list)

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
        if not agent.llm_provider:
            logger.error(
                f"LLM provider not available for prioritize_features, project {project_id}"
            )
            await agent.activity_logger.stop_timer(operation_name, success=False)
            return []  # Or raise an error

        llm_output_text, llm_metadata = await agent.llm_provider.generate_text(prompt)
        await agent.activity_logger.log_activity(
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

        llm_output = await parse_llm_json_output(  # Use the helper function
            activity_logger=agent.activity_logger,
            json_string=llm_output_text,
            llm_metadata=llm_metadata,
            calling_method_name="prioritize_features",
            expected_type=list,
        )

        if not llm_output:
            logger.error(
                f"Failed to parse LLM output for feature prioritization or output was empty for project {project_id}.",
                extra={
                    "project_id": project_id,
                    "llm_output_text": llm_output_text,
                },
            )
            await agent.activity_logger.log_activity(
                agent_id=agent.agent_id,
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
            await agent.activity_logger.stop_timer(
                operation_name, success=False
            )  # Stop timer here
            return []

        updated_features = []
        priority_map = {
            "High": 1,
            "Medium": 2,
            "Low": 3,
            "Critical": 0,
            "Essential": 1,
            "Important": 2,
            "Normal": 2,
            "Optional": 3,
            "Trivial": 4,
        }
        default_priority_int = 3  # Default to Low

        for prioritized_feature_data in llm_output:
            if not isinstance(prioritized_feature_data, dict):
                logger.warning(
                    f"LLM output item is not a dict: {prioritized_feature_data}. Skipping."
                )
                continue
            feature_id = prioritized_feature_data.get("id")
            if not feature_id:
                logger.warning(
                    f"LLM output for prioritized feature missing 'id'. Skipping. Data: {prioritized_feature_data}",
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
                logger.warning(
                    f"Could not find original FeatureArtifact with id {feature_id} "
                    f"from LLM output in the database query results for project {project_id}. Skipping update for this feature.",
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

            priority_str = prioritized_feature_data.get("priority")
            priority_int = default_priority_int
            if priority_str:
                priority_int = priority_map.get(
                    priority_str.capitalize(), default_priority_int
                )
                if priority_str.capitalize() not in priority_map:
                    logger.warning(
                        f"Unmapped priority string '{priority_str}' from LLM for feature {feature_id} in project {project_id}. "
                        f"Defaulting to priority {default_priority_int}.",
                    )
            else:
                logger.warning(
                    f"LLM output for prioritized feature {feature_id} in project {project_id} missing 'priority'. "
                    f"Defaulting to priority {default_priority_int}.",
                )

            original_orm_object_to_update.priority = priority_int
            original_orm_object_to_update.status = "reviewed"
            current_extra_data = (
                original_orm_object_to_update.extra_data
                if original_orm_object_to_update.extra_data is not None
                else {}
            )
            current_extra_data.update(
                {
                    "prioritization": {
                        "rationale": prioritized_feature_data.get("rationale"),
                        "rank": prioritized_feature_data.get("rank"),
                    }
                }
            )
            original_orm_object_to_update.extra_data = current_extra_data

            if agent.db_session:
                agent.db_session.add(original_orm_object_to_update)
                await agent.db_session.commit()  # Commit per feature as in original, or batch?
            else:
                logger.error(
                    f"DB session not available when trying to commit feature {feature_id} for project {project_id}"
                )

            # Determine the content for the 'content' field in updated_features
            # It should be the original description of the feature.
            # The FeatureArtifact model might store this in 'content' or 'description'.
            feature_content_value = getattr(
                original_orm_object_to_update, "content", None
            ) or getattr(original_orm_object_to_update, "description", None)
            parsed_content = {}
            if isinstance(feature_content_value, str):
                try:
                    parsed_content = json.loads(feature_content_value)
                except json.JSONDecodeError:
                    # If content is a plain string and not JSON, keep it as a string under a specific key or handle as per requirements
                    # For now, defaulting to placing it in a dict if it's not JSON.
                    # This might need adjustment based on how non-JSON string content should be handled.
                    parsed_content = {"description_text": feature_content_value}
            elif isinstance(feature_content_value, dict):  # If it's already a dict
                parsed_content = feature_content_value
            # If it's None or some other type, parsed_content remains an empty dict, or handle as error/warning

            updated_features.append(
                {
                    "id": str(original_orm_object_to_update.artifact_id),
                    "title": original_orm_object_to_update.title,
                    "priority": original_orm_object_to_update.priority,  # This is now an int
                    "status": original_orm_object_to_update.status,
                    "content": parsed_content,  # Use the parsed JSON content
                    "extra_data": original_orm_object_to_update.extra_data,
                }
            )

        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=True
        )
        await agent.activity_logger.log_activity(
            activity_type="feature_prioritization_completed",
            description=f"Completed feature prioritization for project {project_id}",
            category=ActivityCategory.THINKING,
            level=ActivityLevel.INFO,
            details={
                "project_id": str(project_id),
                "feature_count": len(updated_features),
            },
            execution_time_ms=int(execution_time_s * 1000),  # Added execution time
        )
        return updated_features
    except Exception as e:
        if agent.db_session:
            await agent.db_session.rollback()
        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=False
        )
        await agent.activity_logger.log_error(
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
