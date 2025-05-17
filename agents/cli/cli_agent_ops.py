"""
Agent management operations for the CLI tool.

This module contains functions for creating, listing, and managing
agent entities in the system.
"""

import uuid
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from infra.db.models import Agent
from sqlalchemy.future import select

from infra.db.models.core import Agent as AgentModel
from .cli_core import AgentCLI, logger
from .cli_utils import (
    ensure_uuid,
    get_uuid_str,
    generate_uuid,
    format_uuid,
    is_valid_uuid,
)


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


async def create_base_agent(
    cli: AgentCLI,
    agent_id: Optional[str] = None,
    agent_name: str = "Test Base Agent",
    system_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a BaseAgent instance for testing.

    Args:
        cli: The AgentCLI instance
        agent_id: Optional agent ID (auto-generated if not provided)
        agent_name: Name for the agent
        system_prompt: System prompt for the agent

    Returns:
        Dictionary with agent details
    """
    try:
        # Generate UUID if not provided
        if agent_id:
            agent_id = format_uuid(agent_id)
        else:
            agent_id = str(uuid.uuid4())

        # Create agent in database
        async with cli.db_client.session() as session:
            # Check if agent already exists
            existing = await session.execute(
                select(AgentModel).where(AgentModel.agent_id == uuid.UUID(agent_id))
            )
            if existing.scalar_one_or_none():
                logger.info(f"Agent already exists: {agent_id}")
                agent = existing.scalar_one()
            else:
                # Create new agent
                agent = AgentModel(
                    agent_id=uuid.UUID(agent_id),
                    agent_name=agent_name,
                    agent_type="base",
                    agent_role="test",
                    system_prompt=system_prompt
                    or f"You are {agent_name}, a test agent.",
                    status="active",
                    created_at=datetime.utcnow(),
                )
                session.add(agent)
                await session.commit()

        # Now create a BaseAgent instance
        from agents.base import BaseAgent

        # Initialize BaseAgent with the database agent
        base_agent = BaseAgent(
            agent_id=agent_id,
            agent_type="base",
            agent_name=agent_name,
            system_prompt=system_prompt,
            db_client=cli.db_client,
        )

        logger.info(f"Created BaseAgent: {agent_id}")

        return {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_type": "base",
            "system_prompt": system_prompt,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating base agent: {str(e)}")
        return {"status": "error", "error": str(e)}


async def test_agent_thinking(
    cli: AgentCLI, agent_id: str, prompt: str, max_tokens: int = 100
) -> Dict[str, Any]:
    """
    Test an agent's thinking capability.

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent
        prompt: Prompt for the agent to think about
        max_tokens: Maximum tokens for the response

    Returns:
        Dictionary with agent's thinking result
    """
    try:
        # Get agent details
        agent = await get_agent(cli, agent_id)
        if not agent:
            return {"status": "error", "error": f"Agent not found: {agent_id}"}

        # Create a BaseAgent instance
        from agents.base import BaseAgent

        base_agent = BaseAgent(
            agent_id=agent_id,
            agent_type=agent.get("type", "test"),
            agent_name=agent.get("name", "Test Agent"),
            system_prompt=agent.get("system_prompt", "You are a test agent."),
            db_client=cli.db_client,
        )

        # Mock thinking for now
        # In a real implementation, this would use the agent's actual thinking capability
        start_time = datetime.now()

        thinking_output = (
            f"Thinking about: {prompt}\n\n"
            + f"Analysis: This is a simulated thinking process for agent {agent_id}.\n"
            + f"The prompt was analyzed and processed according to my system prompt.\n"
            + f"This is a demonstration of the thinking capability."
        )

        # Log the thinking activity
        await base_agent.log_activity(
            activity_type="thinking",
            description=f"Test thinking on prompt: {prompt}",
            thought_process=thinking_output,
            input_data={"prompt": prompt},
            output_data={"thinking": thinking_output},
        )

        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "status": "success",
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "prompt": prompt,
            "thinking": thinking_output,
            "execution_time_ms": execution_time,
        }
    except Exception as e:
        logger.error(f"Error testing agent thinking: {str(e)}")
        return {"status": "error", "error": str(e)}


async def manage_agent_capabilities(
    cli: AgentCLI, agent_id: str, action: str, capabilities: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Set or get agent capabilities.

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent
        action: Action to perform (get, set, add, remove)
        capabilities: List of capabilities to set, add, or remove

    Returns:
        Dictionary with updated capabilities
    """
    try:
        # Get agent details
        agent = await get_agent(cli, agent_id)
        if not agent:
            return {"status": "error", "error": f"Agent not found: {agent_id}"}

        current_capabilities = agent.get("capabilities", {}).get("capabilities", [])

        if action == "get":
            return {
                "status": "success",
                "agent_id": agent_id,
                "agent_name": agent.get("name"),
                "capabilities": current_capabilities,
            }

        if capabilities is None and action != "get":
            return {
                "status": "error",
                "error": "Capabilities must be provided for set, add, or remove actions",
            }

        # Update capabilities based on action
        new_capabilities = current_capabilities.copy()

        if action == "set":
            new_capabilities = capabilities
        elif action == "add":
            for cap in capabilities:
                if cap not in new_capabilities:
                    new_capabilities.append(cap)
        elif action == "remove":
            new_capabilities = [
                cap for cap in new_capabilities if cap not in capabilities
            ]
        else:
            return {"status": "error", "error": f"Invalid action: {action}"}

        # Update agent in database
        async with cli.db_client.session() as session:
            result = await session.execute(
                select(AgentModel).where(AgentModel.agent_id == uuid.UUID(agent_id))
            )
            db_agent = result.scalar_one_or_none()

            if not db_agent:
                return {
                    "status": "error",
                    "error": f"Agent not found in database: {agent_id}",
                }

            db_agent.capabilities = {"capabilities": new_capabilities}
            await session.commit()

        return {
            "status": "success",
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "action": action,
            "previous_capabilities": current_capabilities,
            "updated_capabilities": new_capabilities,
        }
    except Exception as e:
        logger.error(f"Error managing agent capabilities: {str(e)}")
        return {"status": "error", "error": str(e)}


async def set_agent_status(cli: AgentCLI, agent_id: str, status: str) -> Dict[str, Any]:
    """
    Change agent status.

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent
        status: New agent status

    Returns:
        Dictionary with updated status
    """
    try:
        # Validate status
        valid_statuses = [
            "active",
            "inactive",
            "busy",
            "error",
            "initializing",
            "terminated",
        ]
        if status not in valid_statuses:
            return {
                "status": "error",
                "error": f"Invalid status: {status}. Valid statuses: {', '.join(valid_statuses)}",
            }

        # Get agent details
        agent = await get_agent(cli, agent_id)
        if not agent:
            return {"status": "error", "error": f"Agent not found: {agent_id}"}

        previous_status = agent.get("status")

        # Update agent status
        async with cli.db_client.session() as session:
            result = await session.execute(
                select(AgentModel).where(AgentModel.agent_id == uuid.UUID(agent_id))
            )
            db_agent = result.scalar_one_or_none()

            if not db_agent:
                return {
                    "status": "error",
                    "error": f"Agent not found in database: {agent_id}",
                }

            db_agent.status = status
            await session.commit()

        logger.info(
            f"Updated agent status: {agent_id} from {previous_status} to {status}"
        )

        return {
            "status": "success",
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "previous_status": previous_status,
            "new_status": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error setting agent status: {str(e)}")
        return {"status": "error", "error": str(e)}


async def simulate_agent_error(
    cli: AgentCLI, agent_id: str, error_type: str, recover: bool = True
) -> Dict[str, Any]:
    """
    Simulate an error condition for an agent.

    Args:
        cli: The AgentCLI instance
        agent_id: ID of the agent
        error_type: Type of error to simulate
        recover: Whether to automatically recover the agent

    Returns:
        Dictionary with simulation results
    """
    try:
        # Get agent details
        agent = await get_agent(cli, agent_id)
        if not agent:
            return {"status": "error", "error": f"Agent not found: {agent_id}"}

        # Validate error type
        valid_error_types = ["connection", "timeout", "permission", "memory", "runtime"]
        if error_type not in valid_error_types:
            return {
                "status": "error",
                "error": f"Invalid error type: {error_type}. Valid types: {', '.join(valid_error_types)}",
            }

        # Set error message based on type
        error_messages = {
            "connection": "Simulated connection error: Could not connect to required service",
            "timeout": "Simulated timeout error: Operation timed out after 30 seconds",
            "permission": "Simulated permission error: Insufficient permissions to perform operation",
            "memory": "Simulated memory error: Out of memory when processing large dataset",
            "runtime": "Simulated runtime error: Unexpected exception during execution",
        }

        error_message = error_messages.get(error_type)

        # Create a BaseAgent instance
        from agents.base import BaseAgent

        base_agent = BaseAgent(
            agent_id=agent_id,
            agent_type=agent.get("type", "test"),
            agent_name=agent.get("name", "Test Agent"),
            system_prompt=agent.get("system_prompt", "You are a test agent."),
            db_client=cli.db_client,
        )

        # Log the error activity
        await base_agent.log_activity(
            activity_type="error",
            description=f"Simulated {error_type} error",
            thought_process="Error simulation requested by CLI",
            input_data={"error_type": error_type, "recover": recover},
            output_data={"error_message": error_message},
        )

        # Set agent to error state
        previous_status = agent.get("status")
        async with cli.db_client.session() as session:
            result = await session.execute(
                select(AgentModel).where(AgentModel.agent_id == uuid.UUID(agent_id))
            )
            db_agent = result.scalar_one_or_none()

            if db_agent:
                db_agent.status = "error"
                db_agent.extra_data = {
                    **(db_agent.extra_data or {}),
                    "last_error": {
                        "type": error_type,
                        "message": error_message,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
                await session.commit()

        # Recover if requested
        if recover:
            await asyncio.sleep(2)  # Simulate recovery time

            async with cli.db_client.session() as session:
                result = await session.execute(
                    select(AgentModel).where(AgentModel.agent_id == uuid.UUID(agent_id))
                )
                db_agent = result.scalar_one_or_none()

                if db_agent:
                    db_agent.status = previous_status
                    db_agent.extra_data = {
                        **(db_agent.extra_data or {}),
                        "recovery": {
                            "timestamp": datetime.utcnow().isoformat(),
                            "recovered_from": error_type,
                        },
                    }
                    await session.commit()

            # Log recovery
            await base_agent.log_activity(
                activity_type="recovery",
                description=f"Recovered from simulated {error_type} error",
                thought_process="Automatic recovery after error simulation",
                input_data={"error_type": error_type},
                output_data={"result": "success"},
            )

        return {
            "status": "success",
            "agent_id": agent_id,
            "agent_name": agent.get("name"),
            "error_type": error_type,
            "error_message": error_message,
            "recovered": recover,
            "recovery_time_ms": 2000 if recover else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error simulating agent error: {str(e)}")
        return {"status": "error", "error": str(e)}
