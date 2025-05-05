# agents/tasks/agent_tasks.py

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, List
from uuid import uuid4

from celery import shared_task
from celery.utils.log import get_task_logger

# Corrected imports based on project structure
from ..db.postgres import PostgresClient
from ..specialized.product_manager import ProductManagerAgent
from ..specialized.scrum_master import ScrumMasterAgent
from ..llm import GeminiApiProvider
from ..memory.vector_memory import EnhancedVectorMemory
from ..communication.protocol import (
    CommunicationProtocol,
)  # Need protocol for Scrum Master messages

# Set up task-specific logger
logger = get_task_logger(__name__)


# Helper function to create/get event loop and run async tasks
def run_async(coroutine):
    """Run an async coroutine in a synchronous Celery task context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Check if the loop is already running (e.g., within another async context)
    if loop.is_running():
        # If loop is running, we can create a future and wait for it
        # This might happen if Celery worker is run with uvloop or similar
        future = asyncio.ensure_future(coroutine)
        # This might still block if called from a truly sync context, depends on worker setup
        return future.result()  # Be cautious with blocking here
    else:
        return loop.run_until_complete(coroutine)


async def _initialize_components() -> Dict[str, Any]:
    """Helper coroutine to initialize async components for a task."""
    db_client = PostgresClient()
    await db_client.initialize()  # Initialize DB connection pool

    # Use VertexGeminiProvider as per Iteration 1 implementation
    # Requires GOOGLE_APPLICATION_CREDENTIALS and potentially other env vars
    llm_provider = GeminiApiProvider()

    vector_memory = EnhancedVectorMemory(db_client=db_client)
    await vector_memory.initialize()

    comm_protocol = CommunicationProtocol()

    return {
        "db_client": db_client,
        "llm_provider": llm_provider,
        "vector_memory": vector_memory,
        "comm_protocol": comm_protocol,
    }


async def _cleanup_components(components: Dict[str, Any]):
    """Helper coroutine to clean up async components."""
    if components.get("db_client"):
        await components["db_client"].close()
        logger.info("Database connection closed.")


@shared_task(bind=True)
def analyze_requirements_task(self, project_description: str) -> Dict[str, Any]:
    """
    Celery task wrapper for ProductManagerAgent.analyze_requirements.
    """
    logger.info(
        f"[Task ID: {self.request.id}] Starting requirement analysis for project."
    )
    components = {}
    try:
        components = run_async(_initialize_components())

        pm_agent = ProductManagerAgent(
            db_client=components["db_client"],
            llm_provider=components["llm_provider"],
            vector_memory=components["vector_memory"],
            comm_protocol=components["comm_protocol"],  # BaseAgent needs this
        )

        result = run_async(pm_agent.analyze_requirements(project_description))
        logger.info(f"[Task ID: {self.request.id}] Requirement analysis completed.")
        return result

    except Exception as e:
        logger.error(
            f"[Task ID: {self.request.id}] Error in requirement analysis task: {str(e)}",
            exc_info=True,
        )
        return {"error": str(e)}
    finally:
        if components:
            run_async(_cleanup_components(components))


@shared_task(bind=True)
def plan_sprint_task(
    self, backlog_items: List[Dict[str, Any]], sprint_duration_days: int = 14
) -> Dict[str, Any]:
    """
    Celery task wrapper for ScrumMasterAgent.plan_sprint.
    """
    logger.info(
        f"[Task ID: {self.request.id}] Starting sprint planning for {sprint_duration_days} days."
    )
    components = {}
    try:
        components = run_async(_initialize_components())

        # ScrumMasterAgent also needs communication protocol for notifications
        sm_agent = ScrumMasterAgent(
            db_client=components["db_client"],
            llm_provider=components["llm_provider"],
            vector_memory=components["vector_memory"],
            comm_protocol=components["comm_protocol"],
            # Missing ceremonies and meetings modules - they aren't part of this task's scope
        )

        result = run_async(sm_agent.plan_sprint(backlog_items, sprint_duration_days))
        logger.info(f"[Task ID: {self.request.id}] Sprint planning completed.")
        return result

    except Exception as e:
        logger.error(
            f"[Task ID: {self.request.id}] Error in sprint planning task: {str(e)}",
            exc_info=True,
        )
        return {"error": str(e)}
    finally:
        if components:
            run_async(_cleanup_components(components))


@shared_task(bind=True)
def assign_task_to_agent_task(self, task_id: str, agent_id: str) -> Dict[str, Any]:
    """
    Celery task wrapper for ScrumMasterAgent.assign_task.
    """
    logger.info(
        f"[Task ID: {self.request.id}] Assigning task {task_id} to agent {agent_id}."
    )
    components = {}
    try:
        # Only need DB and Comm protocol for this specific action
        db_client = PostgresClient()
        run_async(db_client.initialize())
        comm_protocol = CommunicationProtocol()
        components = {"db_client": db_client, "comm_protocol": comm_protocol}

        # Minimal ScrumMaster for this task
        sm_agent = ScrumMasterAgent(
            db_client=db_client,
            comm_protocol=comm_protocol,
            # Other components not needed for just assigning
        )

        success = run_async(sm_agent.assign_task(task_id, agent_id))
        logger.info(
            f"[Task ID: {self.request.id}] Task assignment completed (Success: {success})."
        )
        return {"success": success, "task_id": task_id, "agent_id": agent_id}

    except Exception as e:
        logger.error(
            f"[Task ID: {self.request.id}] Error in task assignment: {str(e)}",
            exc_info=True,
        )
        return {"error": str(e), "task_id": task_id, "agent_id": agent_id}
    finally:
        if components:
            run_async(_cleanup_components(components))


@shared_task(bind=True)
def update_task_status_task(
    self, task_id: str, status: str, agent_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Celery task wrapper for ScrumMasterAgent.update_task_status.
    """
    logger.info(
        f"[Task ID: {self.request.id}] Updating task {task_id} status to {status}. Agent notified: {agent_id}"
    )
    components = {}
    try:
        # Only need DB and Comm protocol for this specific action
        db_client = PostgresClient()
        run_async(db_client.initialize())
        comm_protocol = CommunicationProtocol()
        components = {"db_client": db_client, "comm_protocol": comm_protocol}

        sm_agent = ScrumMasterAgent(db_client=db_client, comm_protocol=comm_protocol)

        success = run_async(sm_agent.update_task_status(task_id, status, agent_id))
        logger.info(
            f"[Task ID: {self.request.id}] Task status update completed (Success: {success})."
        )
        return {"success": success, "task_id": task_id, "status": status}

    except Exception as e:
        logger.error(
            f"[Task ID: {self.request.id}] Error in task status update: {str(e)}",
            exc_info=True,
        )
        return {"error": str(e), "task_id": task_id, "status": status}
    finally:
        if components:
            run_async(_cleanup_components(components))
