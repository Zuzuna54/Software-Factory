# agents/factory.py

import logging
from typing import Dict, Any, Optional, Type

# Import Base Agent and Specialized Agents
from .base_agent import BaseAgent
from .specialized.product_manager import ProductManagerAgent
from .specialized.scrum_master import ScrumMasterAgent
from .specialized.backend_developer import BackendDeveloperAgent
from .specialized.qa_agent import QAAgent

# Import other agents as they are created (e.g., FrontendDeveloperAgent, DevOpsAgent)

# Import shared dependencies (types for hinting)
from .llm.base import LLMProvider
from .db.postgres import PostgresClient
from .memory.vector_memory import EnhancedVectorMemory
from .communication.protocol import CommunicationProtocol

logger = logging.getLogger("agent.factory")

# Mapping from type string to agent class
AGENT_TYPE_MAP: Dict[str, Type[BaseAgent]] = {
    "base": BaseAgent,
    "product_manager": ProductManagerAgent,
    "scrum_master": ScrumMasterAgent,
    "backend_developer": BackendDeveloperAgent,
    "qa": QAAgent,
    # Add other mappings here as agents are implemented
}


class AgentFactory:
    """Factory for creating agent instances based on type."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        db_client: Optional[PostgresClient] = None,
        vector_memory: Optional[EnhancedVectorMemory] = None,
        comm_protocol: Optional[CommunicationProtocol] = None,
        # Add other shared dependencies if needed (e.g., git_client)
    ):
        """Initialize the factory with shared dependencies."""
        self.shared_dependencies = {
            "llm_provider": llm_provider,
            "db_client": db_client,
            "vector_memory": vector_memory,
            "comm_protocol": comm_protocol,
            # Pass other dependencies here
        }
        logger.info("AgentFactory initialized with shared dependencies.")

    def create_agent(
        self,
        agent_type: str,
        agent_name: str,
        capabilities: Optional[Dict[str, Any]] = None,
        agent_id: Optional[
            str
        ] = None,  # Allow specifying ID if needed (e.g., recreating)
    ) -> BaseAgent:
        """
        Creates an agent instance of the specified type.

        Args:
            agent_type: The type of agent to create (e.g., 'product_manager').
            agent_name: The name for the agent instance.
            capabilities: Optional dictionary of capabilities for the agent.
            agent_id: Optional specific UUID for the agent.

        Returns:
            An instance of the specified agent class.

        Raises:
            ValueError: If the agent_type is unknown.
        """
        agent_class = AGENT_TYPE_MAP.get(agent_type.lower())

        if not agent_class:
            logger.error(f"Unknown agent type requested: {agent_type}")
            raise ValueError(
                f"Unknown agent type: {agent_type}. Known types: {list(AGENT_TYPE_MAP.keys())}"
            )

        # Prepare arguments for the agent constructor
        agent_args = {
            "agent_id": agent_id,
            "agent_type": agent_type.lower(),  # Ensure type is stored consistently
            "agent_name": agent_name,
            "capabilities": capabilities or {},
            **self.shared_dependencies,  # Pass shared dependencies
        }

        # Filter out None values from shared dependencies before passing
        filtered_args = {k: v for k, v in agent_args.items() if v is not None}

        try:
            logger.info(
                f"Creating agent of type '{agent_type}' with name '{agent_name}'"
            )
            # Instantiate the agent
            agent_instance = agent_class(**filtered_args)
            logger.info(
                f"Successfully created agent {agent_instance.agent_id} ({agent_name})"
            )
            return agent_instance
        except Exception as e:
            logger.error(
                f"Failed to instantiate agent type '{agent_type}' with name '{agent_name}': {e}",
                exc_info=True,
            )
            raise  # Re-raise the exception after logging
