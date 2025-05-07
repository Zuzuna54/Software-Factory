# app/api/endpoints/tasks.py

import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from agents.tasks.agent_tasks import (
    analyze_requirements_task,
    plan_sprint_task,
    assign_task_to_agent_task,
    update_task_status_task,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Pydantic Models for Payloads ---


class AnalyzeRequirementsPayload(BaseModel):
    project_description: str = Field(
        ..., description="High-level description of the project."
    )


class PlanSprintPayload(BaseModel):
    project_id: str = Field(
        ...,
        description="ID of the project for which to plan the sprint (e.g., 'default-project').",
    )
    sprint_duration_days: int = Field(14, description="Duration of the sprint in days.")


class AssignTaskPayload(BaseModel):
    task_id: str = Field(..., description="UUID of the task to assign.")
    agent_id: str = Field(..., description="UUID of the agent to assign the task to.")


class UpdateTaskStatusPayload(BaseModel):
    task_id: str = Field(..., description="UUID of the task to update.")
    status: str = Field(
        ..., description="New status for the task (e.g., 'IN_PROGRESS', 'DONE')."
    )
    agent_id: Optional[str] = Field(
        None, description="Optional UUID of the agent performing the update."
    )


class DispatchResponse(BaseModel):
    message: str
    task_name: str
    celery_task_id: Optional[str] = None


# --- API Endpoints ---


@router.post("/dispatch/analyze-requirements", response_model=DispatchResponse)
async def dispatch_analyze_requirements(payload: AnalyzeRequirementsPayload):
    """Dispatches the analyze_requirements Celery task."""
    task_name = "analyze_requirements"
    logger.info(f"API trigger for task: {task_name}")
    try:
        task_result = analyze_requirements_task.delay(
            project_description=payload.project_description
        )
        return DispatchResponse(
            message=f"{task_name} task dispatched.",
            task_name=task_name,
            celery_task_id=task_result.id,
        )
    except Exception as e:
        logger.error(f"Error dispatching {task_name} task via API: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to dispatch task: {str(e)}"
        )


@router.post("/dispatch/plan-sprint", response_model=DispatchResponse)
async def dispatch_plan_sprint(payload: PlanSprintPayload):
    """Dispatches the plan_sprint Celery task."""
    task_name = "plan_sprint"
    logger.info(f"API trigger for task: {task_name}")
    try:
        task_result = plan_sprint_task.delay(
            project_id=payload.project_id,
            sprint_duration_days=payload.sprint_duration_days,
        )
        return DispatchResponse(
            message=f"{task_name} task dispatched.",
            task_name=task_name,
            celery_task_id=task_result.id,
        )
    except Exception as e:
        logger.error(f"Error dispatching {task_name} task via API: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to dispatch task: {str(e)}"
        )


@router.post("/dispatch/assign-task", response_model=DispatchResponse)
async def dispatch_assign_task(payload: AssignTaskPayload):
    """Dispatches the assign_task_to_agent Celery task."""
    task_name = "assign_task"
    logger.info(f"API trigger for task: {task_name}")
    try:
        task_result = assign_task_to_agent_task.delay(
            task_id=payload.task_id, agent_id=payload.agent_id
        )
        return DispatchResponse(
            message=f"{task_name} task dispatched.",
            task_name=task_name,
            celery_task_id=task_result.id,
        )
    except Exception as e:
        logger.error(f"Error dispatching {task_name} task via API: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to dispatch task: {str(e)}"
        )


@router.post("/dispatch/update-task-status", response_model=DispatchResponse)
async def dispatch_update_task_status(payload: UpdateTaskStatusPayload):
    """Dispatches the update_task_status Celery task."""
    task_name = "update_task_status"
    logger.info(f"API trigger for task: {task_name}")
    try:
        task_result = update_task_status_task.delay(
            task_id=payload.task_id, status=payload.status, agent_id=payload.agent_id
        )
        return DispatchResponse(
            message=f"{task_name} task dispatched.",
            task_name=task_name,
            celery_task_id=task_result.id,
        )
    except Exception as e:
        logger.error(f"Error dispatching {task_name} task via API: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to dispatch task: {str(e)}"
        )


# Add more endpoints here to dispatch other Celery tasks as needed
