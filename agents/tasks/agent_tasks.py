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
from ..llm.vertex_gemini_provider import GeminiApiProvider
from ..memory.vector_memory import EnhancedVectorMemory
from ..communication.protocol import (
    CommunicationProtocol,
)  # Need protocol for Scrum Master messages

# Import BaseAgent to access _register_agent or similar logic
from ..base_agent import BaseAgent

# Set up task-specific logger
logger = get_task_logger(__name__)


# Store the loop used by the task to ensure consistency
_task_loops = {}


def run_async(coroutine, task_id=None):
    """
    Run an async coroutine in a synchronous Celery task context,
    managing the event loop consistently per task.
    """
    global _task_loops
    loop = None
    if task_id and task_id in _task_loops:
        loop = _task_loops[task_id]
        logger.debug(f"Reusing existing event loop for task {task_id}")
    else:
        try:
            # Try to get the current running loop if one exists (e.g., uvloop worker)
            loop = asyncio.get_running_loop()
            logger.debug("Using existing running event loop.")
        except RuntimeError:
            # If no loop is running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            logger.debug("Created new event loop.")
            if task_id:
                _task_loops[task_id] = loop

    if loop.is_running():
        # If the loop is already running, schedule the coroutine
        # This can be tricky; ensure_future might be better if called from async context
        logger.warning(
            "Event loop is already running. Scheduling coroutine. This might cause issues."
        )
        future = asyncio.ensure_future(coroutine, loop=loop)
        # Avoid blocking if possible, but this might be necessary depending on worker
        # This line could still cause issues if the outer context isn't async
        # Consider alternative Celery worker types (gevent, eventlet) if this persists.
        # Changed from wait_for(None) which might block forever.
        # Let's try returning the future directly? Or maybe run_coroutine_threadsafe is needed?
        # For now, let's revert to run_until_complete even if running, assuming it won't deadlock
        # in the typical Celery worker setup. This is risky.
        # return asyncio.wait_for(future, timeout=None) # Old problematic line
        logger.warning(
            "Running loop detected, attempting run_until_complete - potential deadlock risk!"
        )
        # Fall through to run_until_complete - This might be wrong if loop is truly running from outside.

    # If the loop isn't running OR we fell through from the running check:
    result = loop.run_until_complete(coroutine)
    # Clean up loop reference if we created it specifically for this task
    # Let's keep the loop reuse logic intact for now, cleanup will happen in task finally block
    # if task_id and task_id in _task_loops and loop is _task_loops[task_id]:
    #     pass # Cleanup handled in the task's finally block
    return result


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
    db_client = components.get("db_client")
    if db_client:
        try:
            await db_client.close()
            logger.info("Database connection closed.")
        except Exception as e:
            # Catch potential errors during close, e.g., if already closed
            logger.error(f"Error closing database connection: {e}", exc_info=True)
    # Add cleanup for other components if needed


@shared_task(bind=True)
def analyze_requirements_task(self, project_description: str) -> Dict[str, Any]:
    """
    Celery task wrapper for ProductManagerAgent.analyze_requirements.
    """
    logger.info(
        f"[Task ID: {self.request.id}] Starting requirement analysis for project."
    )
    components = {}
    task_id = self.request.id
    try:
        components = run_async(_initialize_components(), task_id=task_id)

        pm_agent = ProductManagerAgent(
            db_client=components["db_client"],
            llm_provider=components["llm_provider"],
            vector_memory=components["vector_memory"],
            comm_protocol=components["comm_protocol"],
        )
        # --- Register agent before use ---
        run_async(pm_agent.complete_initialization(), task_id=task_id)
        # --------------------------------

        result = run_async(
            pm_agent.analyze_requirements(project_description), task_id=task_id
        )
        logger.info(f"[Task ID: {task_id}] Requirement analysis completed.")
        return result

    except Exception as e:
        logger.error(
            f"[Task ID: {task_id}] Error in requirement analysis task: {str(e)}",
            exc_info=True,
        )
        # Ensure cleanup happens even if task logic fails
        # The finally block already handles this
        # run_async(_cleanup_components(components), task_id=task_id)
        return {"error": str(e)}
    finally:
        if components:
            logger.debug(f"Running cleanup for task {task_id}")
            run_async(_cleanup_components(components), task_id=task_id)
        # Clean up loop reference after task finishes
        global _task_loops
        if task_id in _task_loops:
            try:
                # Check if loop is closable (might not be if shared/running)
                loop = _task_loops[task_id]
                if not loop.is_running() and not loop.is_closed():
                    # loop.close() # Closing loop might be too aggressive
                    logger.debug(
                        f"Loop for task {task_id} is not running, potential for close."
                    )
                del _task_loops[task_id]
                logger.debug(f"Cleaned up loop reference for task {task_id}")
            except Exception as loop_clean_e:
                logger.error(
                    f"Error during loop cleanup for task {task_id}: {loop_clean_e}"
                )


@shared_task(bind=True)
def plan_sprint_task(
    self, project_id: str, sprint_duration_days: int = 14
) -> Dict[str, Any]:
    """
    Celery task wrapper for ScrumMasterAgent.plan_sprint.
    Manages its own event loop using asyncio.run().
    """
    logger.info(
        f"[Task ID: {self.request.id}] Starting sprint planning for {sprint_duration_days} days."
    )
    task_id = self.request.id

    async def _async_main() -> Dict[str, Any]:
        components = {}
        try:
            # Initialize components within this async context/loop
            logger.debug(f"Task {task_id}: Initializing components...")
            components = await _initialize_components()  # No run_async needed
            logger.debug(f"Task {task_id}: Components initialized.")

            sm_agent = ScrumMasterAgent(
                db_client=components["db_client"],
                llm_provider=components["llm_provider"],
                vector_memory=components["vector_memory"],
                comm_protocol=components["comm_protocol"],
                agent_name="ScrumMasterTaskRunner",
            )
            logger.debug(f"Task {task_id}: ScrumMasterAgent instantiated.")

            # Complete initialization within this async context/loop
            logger.debug(f"Task {task_id}: Running complete_initialization...")
            await sm_agent.complete_initialization()  # No run_async needed
            logger.debug(f"Task {task_id}: complete_initialization finished.")

            # Run the main agent logic
            logger.debug(f"Task {task_id}: Running plan_sprint...")
            result = await sm_agent.plan_sprint(
                project_id, sprint_duration_days
            )  # No run_async needed
            logger.info(
                f"[Task ID: {task_id}] Sprint planning processing completed."
            )  # Changed log message
            return result

        except Exception as e:
            # Log error from within the async context if possible
            logger.error(
                f"[Task ID: {task_id}] Error during async execution in _async_main: {str(e)}",
                exc_info=True,
            )
            # Re-raise the exception so asyncio.run() catches it
            raise
        finally:
            # Cleanup components regardless of success or failure within _async_main
            if components:
                logger.debug(
                    f"Task {task_id}: Running cleanup in _async_main finally block"
                )
                await _cleanup_components(components)  # No run_async needed

    # Run the entire async logic within asyncio.run()
    try:
        # Setting debug=True can sometimes provide more asyncio context on errors
        # result = asyncio.run(_async_main(), debug=True)
        result = asyncio.run(_async_main())
        # Log final success outcome of the task
        logger.info(f"[Task ID: {task_id}] Task completed successfully.")
        return result
    except Exception as e:
        # Catch any unexpected errors from asyncio.run() or re-raised from _async_main
        logger.error(
            f"[Task ID: {task_id}] Top-level task error caught: {str(e)}", exc_info=True
        )
        return {"error": f"Top-level task error: {str(e)}"}


@shared_task(bind=True)
def assign_task_to_agent_task(self, task_id: str, agent_id: str) -> Dict[str, Any]:
    """
    Celery task wrapper for ScrumMasterAgent.assign_task.
    """
    logger.info(
        f"[Task ID: {self.request.id}] Assigning task {task_id} to agent {agent_id}."
    )
    celery_task_id = self.request.id  # Capture for run_async

    async def _async_main() -> Dict[str, Any]:
        components = {}
        try:
            logger.debug(
                f"Task {celery_task_id}: Initializing components for assign_task..."
            )
            components = await _initialize_components()
            logger.debug(
                f"Task {celery_task_id}: Components initialized for assign_task."
            )

            sm_agent = ScrumMasterAgent(
                db_client=components["db_client"],
                llm_provider=components["llm_provider"],
                vector_memory=components[
                    "vector_memory"
                ],  # Ensure vector_memory is passed
                comm_protocol=components["comm_protocol"],
                # agent_id can be omitted to generate a new one for this task-specific agent
                agent_name=f"ScrumMasterAssigner-{celery_task_id[:8]}",  # Unique name
            )
            logger.debug(
                f"Task {celery_task_id}: ScrumMasterAgent (for assign_task) instantiated."
            )

            await sm_agent.complete_initialization()
            logger.debug(
                f"Task {celery_task_id}: ScrumMasterAgent (for assign_task) initialization completed."
            )

            success = await sm_agent.assign_task(task_id, agent_id)
            logger.info(
                f"[Task ID: {celery_task_id}] Task assignment completed (Success: {success})."
            )
            return {"success": success, "task_id": task_id, "agent_id": agent_id}
        except Exception as e:
            logger.error(
                f"[Task ID: {celery_task_id}] Error in task assignment: {str(e)}",
                exc_info=True,
            )
            return {"error": str(e), "task_id": task_id, "agent_id": agent_id}
        finally:
            if components:
                logger.debug(
                    f"Task {celery_task_id}: Running cleanup in assign_task _async_main finally block"
                )
                await _cleanup_components(components)

    return asyncio.run(_async_main())


@shared_task(bind=True)
def update_task_status_task(
    self,
    task_id: str,
    status: str,
    agent_id_updater: Optional[str] = None,  # Renamed agent_id to avoid clash
) -> Dict[str, Any]:
    """
    Celery task wrapper for ScrumMasterAgent.update_task_status.
    """
    logger.info(
        f"[Task ID: {self.request.id}] Updating task {task_id} to status {status}. Updater: {agent_id_updater}"
    )
    celery_task_id = self.request.id  # Capture for run_async

    async def _async_main() -> Dict[str, Any]:
        components = {}
        try:
            logger.debug(
                f"Task {celery_task_id}: Initializing components for update_task_status..."
            )
            components = await _initialize_components()
            logger.debug(
                f"Task {celery_task_id}: Components initialized for update_task_status."
            )

            sm_agent = ScrumMasterAgent(
                db_client=components["db_client"],
                llm_provider=components["llm_provider"],
                vector_memory=components[
                    "vector_memory"
                ],  # Ensure vector_memory is passed
                comm_protocol=components["comm_protocol"],
                agent_name=f"ScrumMasterUpdater-{celery_task_id[:8]}",  # Unique name
            )
            logger.debug(
                f"Task {celery_task_id}: ScrumMasterAgent (for update_task_status) instantiated."
            )

            await sm_agent.complete_initialization()
            logger.debug(
                f"Task {celery_task_id}: ScrumMasterAgent (for update_task_status) initialization completed."
            )

            success = await sm_agent.update_task_status(
                task_id, status, agent_id_updater
            )
            logger.info(
                f"[Task ID: {celery_task_id}] Task status update completed (Success: {success})."
            )
            return {"success": success, "task_id": task_id, "new_status": status}
        except Exception as e:
            logger.error(
                f"[Task ID: {celery_task_id}] Error in task status update: {str(e)}",
                exc_info=True,
            )
            return {"error": str(e), "task_id": task_id, "status_attempted": status}
        finally:
            if components:
                logger.debug(
                    f"Task {celery_task_id}: Running cleanup in update_task_status _async_main finally block"
                )
                await _cleanup_components(components)

    return asyncio.run(_async_main())
