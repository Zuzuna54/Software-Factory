# app/api/endpoints/dashboard.py
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
import json

# Assuming db client setup elsewhere or via dependency injection
# For simplicity, create a placeholder client function
from agents.db.postgres import PostgresClient  # Assuming you have this

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Dependency for DB Client (replace with your actual DI setup) ---
async def get_db_client():
    # In a real app, use dependency injection (e.g., FastAPI's Depends)
    # For now, creating a new client instance per request (not ideal)
    client = PostgresClient()
    try:
        await client.initialize()
        yield client
    finally:
        await client.close()


# ----------------------------------------------------------------------


@router.get("/agents", response_model=List[Dict[str, Any]], tags=["dashboard"])
async def list_all_agents(db: PostgresClient = Depends(get_db_client)):
    """List all registered agents."""
    query = """
    SELECT agent_id, agent_type, agent_name, created_at, capabilities, active
    FROM agents
    ORDER BY created_at DESC
    """
    try:
        results = await db.fetch_all(query)
        agents_data = []
        for row in results:
            agents_data.append(
                {
                    "agent_id": str(row["agent_id"]),
                    "agent_type": row["agent_type"],
                    "agent_name": row["agent_name"],
                    "created_at": row["created_at"].isoformat(),
                    "capabilities": (
                        json.loads(row["capabilities"]) if row["capabilities"] else {}
                    ),
                    "active": row["active"],
                }
            )
        return agents_data
    except Exception as e:
        logger.error(f"Failed to list agents from database: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve agents")


@router.get("/agents/{agent_id}", response_model=Dict[str, Any], tags=["dashboard"])
async def get_agent_details(agent_id: str, db: PostgresClient = Depends(get_db_client)):
    """Get details for a specific agent."""
    # Fetch agent info
    agent_query = "SELECT * FROM agents WHERE agent_id = $1"
    agent_info = await db.fetch_one(agent_query, agent_id)
    if not agent_info:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Fetch recent activities (e.g., last 10)
    activity_query = """
    SELECT activity_id, timestamp, activity_type, description
    FROM agent_activities WHERE agent_id = $1
    ORDER BY timestamp DESC LIMIT 10
    """
    activities = await db.fetch_all(activity_query, agent_id)

    # Fetch recent messages (e.g., last 10 sent/received)
    messages_query = """
    SELECT message_id, timestamp, sender_id, receiver_id, message_type, LEFT(content, 100) as content_preview
    FROM agent_messages WHERE sender_id = $1 OR receiver_id = $1
    ORDER BY timestamp DESC LIMIT 10
    """
    messages = await db.fetch_all(messages_query, agent_id)

    return {
        "details": {
            "agent_id": str(agent_info["agent_id"]),
            "agent_type": agent_info["agent_type"],
            "agent_name": agent_info["agent_name"],
            "created_at": agent_info["created_at"].isoformat(),
            "capabilities": (
                json.loads(agent_info["capabilities"])
                if agent_info["capabilities"]
                else {}
            ),
            "active": agent_info["active"],
        },
        "recent_activities": [
            {
                "activity_id": str(row["activity_id"]),
                "timestamp": row["timestamp"].isoformat(),
                "activity_type": row["activity_type"],
                "description": row["description"],
            }
            for row in activities
        ],
        "recent_messages": [
            {
                "message_id": str(row["message_id"]),
                "timestamp": row["timestamp"].isoformat(),
                "sender_id": str(row["sender_id"]),
                "receiver_id": str(row["receiver_id"]),
                "message_type": row["message_type"],
                "content_preview": row["content_preview"],
            }
            for row in messages
        ],
    }


@router.get("/logs", response_model=List[Dict[str, Any]], tags=["dashboard"])
async def get_system_logs(
    limit: int = 100,
    offset: int = 0,
    agent_id: Optional[str] = None,
    activity_type: Optional[str] = None,
    db: PostgresClient = Depends(get_db_client),
):
    """Get system activity logs with optional filtering."""
    conditions = []
    params = []
    param_idx = 1

    if agent_id:
        conditions.append(f"agent_id = ${param_idx}")
        params.append(agent_id)
        param_idx += 1

    if activity_type:
        conditions.append(f"activity_type ILIKE ${param_idx}")
        params.append(f"%{activity_type}%")
        param_idx += 1

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    query = f"""
    SELECT
        activity_id, agent_id, timestamp, activity_type,
        description, thought_process, input_data, output_data,
        decisions_made, execution_time_ms, related_task_id, related_files
    FROM agent_activities
    {where_clause}
    ORDER BY timestamp DESC
    LIMIT ${param_idx} OFFSET ${param_idx + 1}
    """
    params.extend([limit, offset])

    try:
        results = await db.fetch_all(query, *params)
        logs = []
        for row in results:
            logs.append(
                {
                    "activity_id": str(row["activity_id"]),
                    "agent_id": str(row["agent_id"]) if row["agent_id"] else None,
                    "timestamp": row["timestamp"].isoformat(),
                    "activity_type": row["activity_type"],
                    "description": row["description"],
                    "thought_process": row["thought_process"],
                    "input_data": (
                        json.loads(row["input_data"]) if row["input_data"] else {}
                    ),
                    "output_data": (
                        json.loads(row["output_data"]) if row["output_data"] else {}
                    ),
                    "decisions_made": (
                        json.loads(row["decisions_made"])
                        if row["decisions_made"]
                        else {}
                    ),
                    "execution_time_ms": row["execution_time_ms"],
                    "related_task_id": (
                        str(row["related_task_id"]) if row["related_task_id"] else None
                    ),
                    "related_files": row["related_files"] or [],
                }
            )
        return logs
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")
