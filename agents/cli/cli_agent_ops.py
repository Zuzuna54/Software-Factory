"""
Agent management operations for the CLI tool.

This module contains functions for creating, listing, and managing
agent entities in the system.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from infra.db.models import Agent
from sqlalchemy.future import select

from .cli_core import AgentCLI, logger
from .cli_utils import ensure_uuid, get_uuid_str, generate_uuid


async def create_agent(
    cli: AgentCLI,
    agent_id: Optional[str] = None,
    agent_type: str = "test",
    agent_name: str = "Test Agent",
    agent_role: str = "test",
    capabilities: Optional[List[str]] = None,
    **kwargs,
) -> str:
    """
    Create a new agent in the database.

    Args:
        cli: The AgentCLI instance
        agent_id: Optional agent ID (UUID string, generated if not provided)
        agent_type: Type of agent
        agent_name: Name of agent
        agent_role: Role of agent
        capabilities: List of agent capabilities
        **kwargs: Additional agent attributes

    Returns:
        Agent ID (UUID string)
    """
    # Generate UUID if not provided, or convert to UUID object
    agent_id_obj = generate_uuid() if agent_id is None else ensure_uuid(agent_id)
    if agent_id_obj is None:
        # This can happen if an invalid UUID string was provided
        agent_id_obj = generate_uuid()
        logger.warning(
            f"Invalid UUID format provided, generated new UUID: {agent_id_obj}"
        )

    # Prepare capabilities in JSONB format
    capabilities_json = {"capabilities": capabilities or []}

    # Create agent record in database
    try:
        # Create Agent instance
        agent = Agent(
            agent_id=agent_id_obj,
            agent_type=agent_type,
            agent_name=agent_name,
            agent_role=agent_role,
            capabilities=capabilities_json,
            status="active",
            system_prompt=kwargs.get(
                "system_prompt", f"You are {agent_name}, a {agent_type} agent."
            ),
            extra_data=kwargs.get("extra_data", {}),
        )

        # Store in database using transaction
        async with cli.db_client.transaction() as session:
            session.add(agent)
            await session.flush()  # Ensure the record is created

        # Convert UUID to string
        agent_id_str = str(agent_id_obj)

        # Register with protocol (registers in memory but also tries to save to DB)
        cli.protocol.register_agent(agent_id_str, agent_type, agent_name)

        logger.info(f"Created agent: {agent_id_str}")
        return agent_id_str

    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise


async def list_agents(cli: AgentCLI, status: str = "active") -> List[Dict[str, Any]]:
    """
    List all agents from the database.

    Args:
        cli: The AgentCLI instance
        status: Filter agents by status

    Returns:
        List of agent details
    """
    try:
        # Query database for agents with the specified status
        if status == "all":
            agents = await cli.db_client.get_all(Agent)
        else:
            agents = await cli.db_client.get_all(Agent, status=status)

        # No agents found
        if not agents:
            logger.info("No agents found in the database")
            return []

        # Convert to dictionary format for display
        result = [
            {
                "id": str(agent.agent_id),
                "name": agent.agent_name,
                "type": agent.agent_type,
                "role": agent.agent_role,
                "status": agent.status,
                "created_at": (
                    agent.created_at.isoformat() if agent.created_at else None
                ),
            }
            for agent in agents
        ]

        logger.info(f"Found {len(result)} agents")
        return result

    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return []


async def get_agent(cli: AgentCLI, agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Get agent details from the database.

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent to retrieve

    Returns:
        Agent details if found, None otherwise
    """
    try:
        # Convert to UUID object
        agent_id_obj = ensure_uuid(agent_id)
        if agent_id_obj is None:
            logger.error(f"Invalid agent ID format: {agent_id}")
            return None

        # Query database for agent using agent_id as the id column
        agent = await cli.db_client.get_by_id(Agent, agent_id_obj, id_column="agent_id")

        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return None

        # Convert to dictionary format with all details
        return {
            "id": str(agent.agent_id),
            "name": agent.agent_name,
            "type": agent.agent_type,
            "role": agent.agent_role,
            "capabilities": agent.capabilities,
            "status": agent.status,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "system_prompt": agent.system_prompt,
            "extra_data": agent.extra_data,
        }
    except Exception as e:
        logger.error(f"Error getting agent: {str(e)}")
        return None


async def update_agent(cli: AgentCLI, agent_id: str, **kwargs) -> bool:
    """
    Update agent properties in the database.

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent to update
        **kwargs: Agent properties to update

    Returns:
        True if update was successful, False otherwise
    """
    try:
        # Convert to UUID object
        agent_id_obj = ensure_uuid(agent_id)
        if agent_id_obj is None:
            logger.error(f"Invalid agent ID format: {agent_id}")
            return False

        # Get the agent from database using agent_id as the id column
        agent = await cli.db_client.get_by_id(Agent, agent_id_obj, id_column="agent_id")
        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return False

        # Update agent properties
        if "agent_name" in kwargs:
            agent.agent_name = kwargs["agent_name"]
        if "agent_type" in kwargs:
            agent.agent_type = kwargs["agent_type"]
        if "agent_role" in kwargs:
            agent.agent_role = kwargs["agent_role"]
        if "status" in kwargs:
            agent.status = kwargs["status"]
        if "system_prompt" in kwargs:
            agent.system_prompt = kwargs["system_prompt"]
        if "capabilities" in kwargs:
            agent.capabilities = {"capabilities": kwargs["capabilities"]}
        if "extra_data" in kwargs:
            agent.extra_data = kwargs["extra_data"]

        # Save updates to database using the session
        async with cli.db_client.transaction() as session:
            session.add(agent)
            await session.flush()

        logger.info(f"Updated agent: {agent_id}")
        return True

    except Exception as e:
        logger.error(f"Error updating agent: {str(e)}")
        return False


async def delete_agent(cli: AgentCLI, agent_id: str) -> bool:
    """
    Mark an agent as inactive in the database (soft delete).

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent to delete

    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        # Convert to UUID object
        agent_id_obj = ensure_uuid(agent_id)
        if agent_id_obj is None:
            logger.error(f"Invalid agent ID format: {agent_id}")
            return False

        # Get the agent from database
        agent = await cli.db_client.get_by_id(Agent, agent_id_obj, id_column="agent_id")
        if not agent:
            logger.warning(f"Agent not found: {agent_id}")
            return False

        # Update status to inactive
        agent.status = "inactive"

        # Save to database
        async with cli.db_client.transaction() as session:
            session.add(agent)
            await session.flush()

        # Remove from protocol's in-memory registry
        cli.protocol.unregister_agent(agent_id)
        logger.info(f"Deleted agent: {agent_id}")

        return True

    except Exception as e:
        logger.error(f"Error deleting agent: {str(e)}")
        return False


async def get_agent_messages(
    cli: AgentCLI,
    agent_id: str,
    as_sender: bool = True,
    as_recipient: bool = True,
    limit: int = 10,
):
    """
    Get messages for an agent.

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent
        as_sender: Whether to include messages sent by the agent
        as_recipient: Whether to include messages received by the agent
        limit: Maximum number of messages to retrieve

    Returns:
        List of messages for the agent
    """
    agent_id_obj = ensure_uuid(agent_id)
    if agent_id_obj is None:
        logger.error(f"Invalid agent ID format: {agent_id}")
        return []

    return await cli.protocol.get_agent_messages(
        agent_id=str(agent_id_obj),
        as_sender=as_sender,
        as_recipient=as_recipient,
        limit=limit,
    )
