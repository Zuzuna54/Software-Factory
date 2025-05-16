# agents/cli/agent_cli.py

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import uuid  # Import uuid

# Add dotenv import
from dotenv import load_dotenv

# Local imports (adjust as needed)
try:
    from ..base_agent import BaseAgent
    from ..db.postgres import PostgresClient
    from ..llm.vertex_gemini_provider import GeminiApiProvider
    from ..memory.vector_memory import EnhancedVectorMemory  # Use EnhancedVectorMemory
    from ..communication.protocol import (
        CommunicationProtocol,
        AgentMessage,
        MessageType,
    )
    from ..factory import AgentFactory, AGENT_TYPE_MAP  # Import AGENT_TYPE_MAP

    # Import Celery task functions
    from ..tasks.agent_tasks import (
        analyze_requirements_task,
        plan_sprint_task,
        assign_task_to_agent_task,
        update_task_status_task,
        # Import other tasks as needed
    )
except ImportError:
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from agents.base_agent import BaseAgent
    from agents.db.postgres import PostgresClient
    from agents.llm.vertex_gemini_provider import GeminiApiProvider
    from agents.memory.vector_memory import EnhancedVectorMemory
    from agents.communication.protocol import (
        CommunicationProtocol,
        AgentMessage,
        MessageType,
    )
    from agents.factory import AgentFactory, AGENT_TYPE_MAP  # Import AGENT_TYPE_MAP

    # Import Celery task functions (also in except block for consistency)
    from agents.tasks.agent_tasks import (
        analyze_requirements_task,
        plan_sprint_task,
        assign_task_to_agent_task,
        update_task_status_task,
    )

# Set up logging for the CLI
log_file = "agent_cli.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to console
        logging.FileHandler(log_file),  # Log to file
    ],
)

logger = logging.getLogger("agent.cli")


# Map task names to functions for CLI dispatch
TASK_MAP = {
    "analyze_requirements": analyze_requirements_task,
    "plan_sprint": plan_sprint_task,
    "assign_task": assign_task_to_agent_task,
    "update_task_status": update_task_status_task,
}


class AgentCLI:
    """Command-line interface for testing agent interactions."""

    def __init__(self):
        self.db_client: Optional[PostgresClient] = None
        self.llm_provider: Optional[GeminiApiProvider] = None
        self.vector_memory: Optional[EnhancedVectorMemory] = None
        self.comm_protocol: CommunicationProtocol = CommunicationProtocol()
        self.agent_factory: Optional[AgentFactory] = (
            None  # Add factory instance variable
        )
        # self.agents: Dict[str, BaseAgent] = {} # No longer needed to track agents in memory
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the CLI and required services."""
        if self._initialized:
            return

        # Explicitly load .env from the project root
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )  # Get project root (Software Factory)
        dotenv_path = os.path.join(project_root, ".env")
        loaded = load_dotenv(dotenv_path=dotenv_path, override=True)
        if loaded:
            logger.info(f"Loaded environment variables from: {dotenv_path}")
        else:
            logger.warning(f"Could not find or load .env file at: {dotenv_path}")

        logger.info("Initializing CLI services...")
        try:
            # Initialize database client
            self.db_client = PostgresClient()
            await self.db_client.initialize()

            # Initialize LLM provider using the new class
            # It will now read the GEMINI_API_KEY loaded from .env
            self.llm_provider = GeminiApiProvider()

            # Initialize vector memory
            # Note: EnhancedVectorMemory might need llm_provider for embeddings.
            # The current GeminiApiProvider still tries to use Vertex for embeddings,
            # so this might still fail or attempt Vertex calls if not handled.
            # Remove the llm_provider argument as it's not accepted by the constructor
            self.vector_memory = EnhancedVectorMemory(
                self.db_client
            )  # Pass only db_client
            await self.vector_memory.initialize()

            # Initialize Agent Factory with shared dependencies
            self.agent_factory = AgentFactory(
                llm_provider=self.llm_provider,
                db_client=self.db_client,
                vector_memory=self.vector_memory,
                comm_protocol=self.comm_protocol,
            )

            self._initialized = True
            logger.info("CLI services initialized successfully.")
        except Exception as e:
            logger.error(f"CLI Initialization failed: {e}", exc_info=True)
            sys.exit(1)

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()
        if not self._initialized:
            raise RuntimeError("CLI Services could not be initialized.")

    async def create_agent(
        self, agent_type: str, agent_name: str, capabilities_json: Optional[str] = None
    ) -> Optional[str]:
        """Create a new agent instance, register it in DB, and return its ID."""
        await self._ensure_initialized()

        if not self.agent_factory:
            logger.error("Agent Factory is not initialized.")
            return None

        capabilities = {}
        if capabilities_json:
            try:
                capabilities = json.loads(capabilities_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format for capabilities: {e}")
                return None

        try:
            # 1. Create agent instance using the factory
            # The factory now handles passing dependencies
            agent_instance = self.agent_factory.create_agent(
                agent_type=agent_type,
                agent_name=agent_name,
                capabilities=capabilities,
                # agent_id is generated by default in BaseAgent constructor
            )

            # 2. Explicitly register the agent in the database
            # (Overwrites/confirms registration potentially started by BaseAgent.__init__)
            query_insert = """
            INSERT INTO agents (agent_id, agent_type, agent_name, capabilities, active)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (agent_id) DO UPDATE SET
                agent_type = EXCLUDED.agent_type,
                agent_name = EXCLUDED.agent_name,
                capabilities = EXCLUDED.capabilities,
                active = EXCLUDED.active
            """
            await self.db_client.execute(
                query_insert,
                agent_instance.agent_id,
                agent_instance.agent_type,
                agent_instance.agent_name,
                json.dumps(agent_instance.capabilities),
                True,  # Default to active
            )

            # Correct indentation (aligned with try):
            logger.info(
                f"Agent {agent_instance.agent_id} ({agent_instance.agent_name}) created and registered/updated in DB."
            )

            # Explicitly initialize ThoughtCapture synchronously after agent creation
            if agent_instance.thought_capture:
                try:
                    logger.debug(
                        f"Initializing ThoughtCapture for agent {agent_instance.agent_id}"
                    )
                    await agent_instance.thought_capture.initialize()
                    logger.debug(
                        f"ThoughtCapture initialized for agent {agent_instance.agent_id}"
                    )
                except Exception as tc_e:
                    logger.error(
                        f"Failed to initialize ThoughtCapture for agent {agent_instance.agent_id}: {tc_e}",
                        exc_info=True,
                    )
                    # Decide if this should be a fatal error for agent creation?
                    # For now, just log it.

            print(f"Agent Created: ID = {agent_instance.agent_id}")
            return agent_instance.agent_id

        except ValueError as e:
            # Handle unknown agent type from factory
            logger.error(f"Agent creation failed: {e}")
            print(f"Error: {e}")
            return None
        except Exception as e:
            # Handle other potential errors (DB connection, etc.)
            logger.error(
                f"Unexpected error creating agent {agent_name} of type {agent_type}: {e}",
                exc_info=True,
            )
            print(f"Error: Could not create agent. Check logs.")
            return None

    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents registered in the database."""
        await self._ensure_initialized()
        if not self.db_client:
            logger.error("Database client not available.")
            return []

        query = """
        SELECT agent_id, agent_type, agent_name, created_at, capabilities, active
        FROM agents
        ORDER BY created_at DESC
        """
        try:
            results = await self.db_client.fetch_all(query)
            agents_data = []
            for row in results:
                agents_data.append(
                    {
                        "agent_id": str(row["agent_id"]),
                        "agent_type": row["agent_type"],
                        "agent_name": row["agent_name"],
                        "created_at": row["created_at"].isoformat(),
                        "capabilities": (
                            json.loads(row["capabilities"])
                            if row["capabilities"]
                            else {}
                        ),
                        "active": row["active"],
                    }
                )
            return agents_data
        except Exception as e:
            logger.error(f"Failed to list agents from database: {e}", exc_info=True)
            return []

    # --- Task 3: Fix send_message ---
    async def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        content: str,
        message_type_str: str = "INFORM",
        conv_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> Optional[str]:
        """Send a message from one agent to another by logging it directly to DB."""
        await self._ensure_initialized()

        # Validate sender_id exists in the database
        sender_exists = await self._check_agent_exists(sender_id)
        if not sender_exists:
            logger.error(f"Sender agent {sender_id} not found in database.")
            print(f"Error: Sender agent ID {sender_id} does not exist.")
            return None

        # Validate receiver_id exists in the database
        receiver_exists = await self._check_agent_exists(receiver_id)
        if not receiver_exists:
            logger.error(f"Receiver agent {receiver_id} not found in database.")
            print(f"Error: Receiver agent ID {receiver_id} does not exist.")
            return None

        # Validate message type
        try:
            message_type = MessageType(message_type_str.upper())
        except ValueError:
            valid_types = [t.value for t in MessageType]
            logger.error(f"Invalid message type: {message_type_str}")
            print(
                f"Error: Invalid message type '{message_type_str}'. Valid: {valid_types}"
            )
            return None

        # Parse metadata JSON
        metadata = {}
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format for metadata: {e}")
                print(f"Error: Invalid JSON for metadata: {e}")
                return None

        # Create the message object using the protocol
        # Generate a new UUID for the message
        message_id = str(uuid.uuid4())
        created_at = datetime.now()

        # Store message directly in the database
        query_insert_msg = """
        INSERT INTO agent_messages (
            message_id, timestamp, sender_id, receiver_id,
            message_type, content, related_task_id,
            metadata
            -- parent_message_id - currently not handled by CLI
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING message_id
        """

        try:
            await self.db_client.execute(
                query_insert_msg,
                message_id,
                created_at,
                sender_id,
                receiver_id,
                message_type.value,
                content,
                task_id,
                json.dumps(metadata or {}),
            )
            logger.info(
                f"Message {message_id} logged to DB: {sender_id} -> {receiver_id}"
            )

            # Store vector embedding for the message (if components available)
            await self._store_message_embedding(
                message_id,
                content,
                sender_id,
                receiver_id,
                message_type.value,
                task_id,
                metadata,
            )

            print(f"Message Sent (Logged to DB): ID = {message_id}")
            return message_id

        except Exception as e:
            logger.error(
                f"Failed to log message to DB from {sender_id} to {receiver_id}: {e}",
                exc_info=True,
            )
            print("Error: Failed to send/log message. Check logs.")
            return None

    async def _check_agent_exists(self, agent_id: str) -> bool:
        """Check if an agent ID exists in the database."""
        query = "SELECT 1 FROM agents WHERE agent_id = $1"
        result = await self.db_client.fetch_one(query, agent_id)
        return result is not None

    async def _store_message_embedding(
        self,
        message_id: str,
        content: str,
        sender_id: str,
        receiver_id: str,
        msg_type: str,
        task_id: Optional[str],
        metadata: Dict[str, Any],
    ):
        """Generate and store vector embedding for a message."""
        if self.vector_memory and self.llm_provider:
            try:
                embedding = await self.llm_provider.generate_embeddings(content)
                if embedding:
                    await self.vector_memory.store_entity(
                        entity_type="AgentMessage",
                        entity_id=message_id,
                        content=content,
                        embedding=embedding,
                        metadata={
                            "sender": sender_id,
                            "receiver": receiver_id,
                            "type": msg_type,
                            "task_id": task_id,
                            **(metadata or {}),
                        },
                        tags=["communication", msg_type.lower()],
                    )
                    logger.debug(f"Stored embedding for message {message_id}")
                else:
                    logger.warning(
                        f"Failed to generate embedding for message {message_id} (using LLM provider: {type(self.llm_provider).__name__})"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to store embedding for message {message_id}: {e}",
                    exc_info=True,
                )
        else:
            logger.debug(
                "Skipping message embedding: Vector Memory or LLM Provider not available."
            )

    async def get_agent_messages(
        self, agent_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent messages received by the specified agent."""
        await self._ensure_initialized()
        if not self.db_client:
            logger.error("Database client not available.")
            return []

        # Fetch directly from DB instead of using agent instance
        query = """
        SELECT
            message_id, timestamp, sender_id, receiver_id,
            message_type, content, related_task_id, metadata
        FROM agent_messages
        WHERE receiver_id = $1
        ORDER BY timestamp DESC
        LIMIT $2
        """
        try:
            results = await self.db_client.fetch_all(query, agent_id, limit)
            messages = []
            for row in results:
                messages.append(
                    {
                        "message_id": str(row["message_id"]),
                        "timestamp": row["timestamp"].isoformat(),
                        "sender_id": str(row["sender_id"]),
                        "receiver_id": str(row["receiver_id"]),
                        "message_type": row["message_type"],
                        "content": row["content"],
                        "related_task_id": (
                            str(row["related_task_id"])
                            if row["related_task_id"]
                            else None
                        ),
                        "metadata": (
                            json.loads(row["metadata"]) if row["metadata"] else {}
                        ),
                    }
                )
            return messages
        except Exception as e:
            logger.error(
                f"Failed to fetch messages for agent {agent_id}: {e}", exc_info=True
            )
            return []

    async def search_knowledge(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for knowledge (currently messages) related to the query using vector search."""
        await self._ensure_initialized()
        if not self.vector_memory or not self.llm_provider:
            logger.error("Required components (LLM, Memory) not available for search.")
            return []

        try:
            query_embedding = await self.llm_provider.generate_embeddings(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding.")
                return []

            # Directly use vector_memory search
            similar_results = await self.vector_memory.search_similar(
                query_embedding=query_embedding,
                entity_types=["AgentMessage"],  # Example: search only messages
                limit=limit,
                # Add threshold if desired
            )

            # Format results (similar_results format depends on vector_memory implementation)
            # Assuming it returns a list of dicts with 'metadata' and 'similarity' keys
            formatted_results = []
            for res in similar_results:
                # Add similarity score if available
                res_data = res.get("metadata", {})
                res_data["similarity_score"] = res.get("similarity")
                res_data["entity_id"] = res.get("entity_id")  # Include the message ID
                formatted_results.append(res_data)

            return formatted_results

        except Exception as e:
            logger.error(f"Knowledge search failed: {e}", exc_info=True)
            return []

    async def get_agent_activities(
        self, agent_id: str, activity_type: Optional[str] = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent activities logged for the specified agent."""
        await self._ensure_initialized()
        if not self.db_client:
            logger.error("Database client not initialized.")
            return []

        conditions = ["agent_id = $1"]
        params: List[Any] = [agent_id]
        param_idx = 2

        if activity_type:
            conditions.append(f"activity_type ILIKE ${param_idx}")
            params.append(f"%{activity_type}%")
            param_idx += 1

        query = f"""
        SELECT
            activity_id, timestamp, activity_type,
            description, thought_process, input_data, output_data,
            decisions_made, execution_time_ms, related_task_id, related_files
        FROM agent_activities
        WHERE {" AND ".join(conditions)}
        ORDER BY timestamp DESC
        LIMIT ${param_idx}
        """
        params.append(limit)

        try:
            results = await self.db_client.fetch_all(query, *params)
            activities = []
            for row in results:
                activities.append(
                    {
                        "activity_id": str(row["activity_id"]),
                        "timestamp": row["timestamp"].isoformat(),
                        "agent_id": agent_id,  # Add agent_id for clarity
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
                            str(row["related_task_id"])
                            if row["related_task_id"]
                            else None
                        ),
                        "related_files": row["related_files"] or [],
                    }
                )
            return activities
        except Exception as e:
            logger.error(
                f"Failed to get activities for agent {agent_id}: {e}", exc_info=True
            )
            return []

    async def close(self) -> None:
        """Close database connections and other resources."""
        if self.db_client:
            await self.db_client.close()
        self._initialized = False
        logger.info("CLI resources closed.")

    # Method to fetch agent data and recreate instance (Helper)
    async def _get_agent_instance(self, agent_id: str) -> Optional[BaseAgent]:
        """Fetch agent data from DB and recreate the instance using the factory."""
        await self._ensure_initialized()
        if not self.db_client or not self.agent_factory:
            logger.error("DB Client or Agent Factory not initialized.")
            return None

        query = "SELECT agent_id, agent_type, agent_name, capabilities FROM agents WHERE agent_id = $1"
        agent_data = await self.db_client.fetch_one(query, agent_id)

        if not agent_data:
            logger.error(f"Agent with ID {agent_id} not found in database.")
            return None

        try:
            agent_instance = self.agent_factory.create_agent(
                agent_type=agent_data["agent_type"],
                agent_name=agent_data["agent_name"],
                capabilities=json.loads(agent_data["capabilities"] or "{}"),
                agent_id=str(agent_data["agent_id"]),  # Pass the existing ID
            )
            return agent_instance
        except Exception as e:
            logger.error(
                f"Failed to recreate agent instance {agent_id}: {e}", exc_info=True
            )
            return None

    # --- Invocation Methods ---

    async def invoke_analyze_requirements(
        self, agent_id: str, description: str
    ) -> Optional[Dict[str, Any]]:
        """Invoke the analyze_requirements method on a ProductManagerAgent."""
        agent_instance = await self._get_agent_instance(agent_id)
        if not agent_instance:
            print(f"Error: Could not find or recreate agent {agent_id}")
            return None

        # Check if the agent has the required method
        if not hasattr(agent_instance, "analyze_requirements") or not callable(
            getattr(agent_instance, "analyze_requirements")
        ):
            logger.error(
                f"Agent {agent_id} (type {agent_instance.agent_type}) does not have analyze_requirements method."
            )
            print(
                f"Error: Agent type {agent_instance.agent_type} cannot analyze requirements."
            )
            return None

        try:
            logger.info(f"Invoking analyze_requirements for agent {agent_id}...")
            result = await agent_instance.analyze_requirements(description)
            logger.info(f"analyze_requirements completed for agent {agent_id}")
            return result
        except Exception as e:
            logger.error(
                f"Error invoking analyze_requirements for agent {agent_id}: {e}",
                exc_info=True,
            )
            print("Error during invocation. Check logs.")
            return None

    async def invoke_run_tests(
        self, agent_id: str, test_paths: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Invoke the run_tests method on a QAAgent."""
        agent_instance = await self._get_agent_instance(agent_id)
        if not agent_instance:
            print(f"Error: Could not find or recreate agent {agent_id}")
            return None

        # Check if the agent has the required method
        if not hasattr(agent_instance, "run_tests") or not callable(
            getattr(agent_instance, "run_tests")
        ):
            logger.error(
                f"Agent {agent_id} (type {agent_instance.agent_type}) does not have run_tests method."
            )
            print(f"Error: Agent type {agent_instance.agent_type} cannot run tests.")
            return None

        try:
            logger.info(
                f"Invoking run_tests for agent {agent_id} with paths: {test_paths}..."
            )
            result = await agent_instance.run_tests(test_paths)
            logger.info(f"run_tests completed for agent {agent_id}")
            return result
        except Exception as e:
            logger.error(
                f"Error invoking run_tests for agent {agent_id}: {e}", exc_info=True
            )
            print("Error during invocation. Check logs.")
            return None

    # --- New Method for one processing cycle ---
    async def run_agent_cycle(self, agent_id: str):
        """Instantiate an agent and run one cycle of its processing loop."""
        await self._ensure_initialized()

        agent_instance = await self._get_agent_instance(agent_id)
        if not agent_instance:
            print(f"Error: Could not find or recreate agent {agent_id}")
            return

        # Ensure the agent has the loop method
        if not hasattr(agent_instance, "run_processing_loop"):
            print(
                f"Error: Agent {agent_id} does not have a run_processing_loop method."
            )
            return

        print(f"Running one processing cycle for agent {agent_id}...")
        try:
            # We need to call the internal methods directly for one cycle
            # instead of starting the infinite loop.
            if hasattr(agent_instance, "check_for_new_tasks"):
                print(f"Checking for new tasks...")
                await agent_instance.check_for_new_tasks()
            else:
                print(f"Agent {agent_id} missing check_for_new_tasks method.")

            if hasattr(agent_instance, "process_incoming_messages"):
                print(f"Processing incoming messages...")
                await agent_instance.process_incoming_messages()
            else:
                print(f"Agent {agent_id} missing process_incoming_messages method.")

            print(f"Processing cycle finished for agent {agent_id}.")

        except Exception as e:
            logger.error(
                f"Error during agent processing cycle for {agent_id}: {e}",
                exc_info=True,
            )
            print(f"Error during processing cycle. Check logs.")

    # --- New Method for Task Dispatch ---
    async def dispatch_celery_task(
        self,
        task_name: str,
        task_args: List[Any],
        task_kwargs: Dict[str, Any],
    ):
        """Dispatch a Celery task by name with provided arguments."""
        await self._ensure_initialized()

        logger.info(f"Attempting to dispatch Celery task: {task_name}")

        task_func = TASK_MAP.get(task_name)
        if not task_func:
            logger.error(f"Unknown task name specified for dispatch: {task_name}")
            print(
                f"Error: Unknown task name '{task_name}'. Known tasks: {list(TASK_MAP.keys())}"
            )
            return

        # Arguments are now pre-parsed, no need for JSON loading here

        try:
            # Use apply_async for more control
            task_result = task_func.apply_async(args=task_args, kwargs=task_kwargs)
            logger.info(f"Dispatched task '{task_name}' with ID: {task_result.id}")
            print(
                f"Dispatched task '{task_name}' with Celery task ID: {task_result.id}"
            )

        except Exception as e:
            logger.error(
                f"Failed to dispatch Celery task '{task_name}': {e}", exc_info=True
            )
            print(f"Error: Failed to dispatch task '{task_name}'. Check logs.")


async def run_cli():
    """Parses arguments and runs the appropriate CLI command."""
    parser = argparse.ArgumentParser(description="Autonomous Agent System CLI Tool")
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", required=True
    )

    # --- Agent Commands ---
    parser_agent = subparsers.add_parser("agent", help="Manage agents")
    agent_subparsers = parser_agent.add_subparsers(
        dest="agent_command", help="Agent actions", required=True
    )

    # agent create
    parser_agent_create = agent_subparsers.add_parser(
        "create", help="Create a new agent and register in DB"
    )
    parser_agent_create.add_argument(
        "--type",
        type=str,
        required=True,  # Make type required
        help=f"Type of agent. Known: {list(AGENT_TYPE_MAP.keys())}",
    )
    parser_agent_create.add_argument(
        "--name", type=str, required=True, help="Name for the new agent"
    )
    parser_agent_create.add_argument(
        "--capabilities",
        type=str,
        help="JSON string of agent capabilities, e.g., '{\"can_code\": true}'",
    )

    # agent list
    agent_subparsers.add_parser("list", help="List registered agents from DB")

    # agent activities
    parser_agent_activities = agent_subparsers.add_parser(
        "activities", help="Show agent activities from DB"
    )
    parser_agent_activities.add_argument(
        "--id", type=str, required=True, help="Agent ID"
    )
    parser_agent_activities.add_argument(
        "--type", type=str, help="Filter by activity type (e.g., CodeGeneration)"
    )
    parser_agent_activities.add_argument(
        "--limit", type=int, default=10, help="Maximum activities to show (default: 10)"
    )

    # Add agent invoke subcommands
    parser_agent_analyze = agent_subparsers.add_parser(
        "analyze-requirements",
        help="Invoke analyze_requirements on a Product Manager agent.",
    )
    parser_agent_analyze.add_argument(
        "--id", type=str, required=True, help="ID of the Product Manager agent."
    )
    parser_agent_analyze.add_argument(
        "--description", type=str, required=True, help="High-level project description."
    )

    parser_agent_run_tests = agent_subparsers.add_parser(
        "run-tests", help="Invoke run_tests on a QA agent."
    )
    parser_agent_run_tests.add_argument(
        "--id", type=str, required=True, help="ID of the QA agent."
    )
    parser_agent_run_tests.add_argument(
        "--paths",
        type=str,
        nargs="*",
        help="Optional list of specific test paths/files to run.",
    )

    # agent process-cycle (NEW COMMAND)
    parser_agent_cycle = agent_subparsers.add_parser(
        "process-cycle", help="Run one check/process cycle for an agent (for testing)."
    )
    parser_agent_cycle.add_argument(
        "--id", type=str, required=True, help="ID of the agent to run cycle for."
    )

    # --- Message Commands ---
    parser_message = subparsers.add_parser("message", help="Manage messages")
    message_subparsers = parser_message.add_subparsers(
        dest="message_command", help="Message actions", required=True
    )

    # message send
    parser_message_send = message_subparsers.add_parser(
        "send", help="Send a message (logs directly to DB)"
    )
    parser_message_send.add_argument(
        "--sender", type=str, required=True, help="Sender Agent ID (must exist in DB)"
    )
    parser_message_send.add_argument(
        "--receiver",
        type=str,
        required=True,
        help="Receiver Agent ID (must exist in DB)",
    )
    parser_message_send.add_argument(
        "--content", type=str, required=True, help="Message content"
    )
    parser_message_send.add_argument(
        "--type",
        type=str,
        default="INFORM",
        help=f"Message type (default: INFORM). Valid: {[t.value for t in MessageType]}",
    )
    parser_message_send.add_argument(
        "--conv_id", type=str, help="Optional conversation UUID"
    )
    parser_message_send.add_argument(
        "--task_id", type=str, help="Optional related task UUID"
    )
    parser_message_send.add_argument(
        "--metadata",
        type=str,
        help='Optional JSON string for metadata, e.g., \'{"priority": "high"}\'',
    )

    # message show
    parser_message_show = message_subparsers.add_parser(
        "show", help="Show messages received by an agent from DB"
    )
    parser_message_show.add_argument(
        "--id", type=str, required=True, help="Agent ID whose messages to show"
    )
    parser_message_show.add_argument(
        "--limit", type=int, default=10, help="Maximum messages to show (default: 10)"
    )

    # --- Knowledge Commands ---
    parser_knowledge = subparsers.add_parser(
        "knowledge", help="Interact with knowledge base"
    )
    knowledge_subparsers = parser_knowledge.add_subparsers(
        dest="knowledge_command", help="Knowledge actions", required=True
    )

    # knowledge search
    parser_knowledge_search = knowledge_subparsers.add_parser(
        "search", help="Search knowledge base (messages) via vector similarity"
    )
    parser_knowledge_search.add_argument(
        "--query", type=str, required=True, help="Search query string"
    )
    parser_knowledge_search.add_argument(
        "--limit", type=int, default=5, help="Maximum results (default: 5)"
    )

    # --- Task Commands ---
    parser_task = subparsers.add_parser("task", help="Manage Celery tasks")
    task_subparsers = parser_task.add_subparsers(
        dest="task_command", help="Task actions", required=True
    )

    # task dispatch
    parser_dispatch = task_subparsers.add_parser(
        "dispatch", help="Dispatch a specific background task (see subcommands)"
    )
    dispatch_subparsers = parser_dispatch.add_subparsers(
        dest="task_name", help="Specific task to dispatch", required=True
    )

    # task dispatch analyze_requirements
    parser_dispatch_analyze = dispatch_subparsers.add_parser(
        "analyze_requirements", help="Dispatch task to analyze project requirements."
    )
    parser_dispatch_analyze.add_argument(
        "--project_description",
        type=str,
        required=True,
        help="High-level project description.",
    )

    # task dispatch plan_sprint
    parser_dispatch_plan_sprint = dispatch_subparsers.add_parser(
        "plan_sprint", help="Dispatch task to plan a sprint for a project."
    )
    parser_dispatch_plan_sprint.add_argument(
        "--project_id",
        type=str,
        required=True,
        help="ID of the project (e.g., 'default-project')",
    )
    parser_dispatch_plan_sprint.add_argument(
        "--sprint_duration_days",
        type=int,
        default=14,
        help="Duration of the sprint in days (default: 14)",
    )

    # task dispatch assign_task
    parser_dispatch_assign = dispatch_subparsers.add_parser(
        "assign_task", help="Dispatch task to assign a task to an agent."
    )
    parser_dispatch_assign.add_argument(
        "--task_id", type=str, required=True, help="UUID of the task to assign."
    )
    parser_dispatch_assign.add_argument(
        "--agent_id",
        type=str,
        required=True,
        help="UUID of the agent to assign the task to.",
    )

    # task dispatch update_task_status
    parser_dispatch_update_status = dispatch_subparsers.add_parser(
        "update_task_status", help="Dispatch task to update a task's status."
    )
    parser_dispatch_update_status.add_argument(
        "--task_id", type=str, required=True, help="UUID of the task to update."
    )
    parser_dispatch_update_status.add_argument(
        "--status",
        type=str,
        required=True,
        help="New status (e.g., BACKLOG, IN_PROGRESS, DONE).",
    )
    parser_dispatch_update_status.add_argument(
        "--agent_id",
        type=str,
        help="(Optional) UUID of the agent performing the update.",
    )

    args = parser.parse_args()
    cli = AgentCLI()

    try:
        result = None  # Initialize result
        if args.command == "agent":
            if args.agent_command == "create":
                result = await cli.create_agent(
                    agent_type=args.type,
                    agent_name=args.name,
                    capabilities_json=args.capabilities,
                )
            elif args.agent_command == "list":
                result = await cli.list_agents()
                print(json.dumps(result, indent=2))
            elif args.agent_command == "activities":
                result = await cli.get_agent_activities(
                    agent_id=args.id, activity_type=args.type, limit=args.limit
                )
                print(json.dumps(result, indent=2))
            elif args.agent_command == "analyze-requirements":
                result = await cli.invoke_analyze_requirements(
                    agent_id=args.id, description=args.description
                )
                if result is not None:
                    print(json.dumps(result, indent=2))
            elif args.agent_command == "run-tests":
                result = await cli.invoke_run_tests(
                    agent_id=args.id, test_paths=args.paths
                )
                if result is not None:
                    print(json.dumps(result, indent=2))
            elif args.agent_command == "process-cycle":
                # process-cycle prints its own output
                await cli.run_agent_cycle(agent_id=args.id)

        elif args.command == "message":
            if args.message_command == "send":
                await cli.send_message(
                    sender_id=args.sender,
                    receiver_id=args.receiver,
                    content=args.content,
                    message_type_str=args.type,
                    conv_id=args.conv_id,
                    task_id=args.task_id,
                    metadata_json=args.metadata,
                )
            elif args.message_command == "show":
                result = await cli.get_agent_messages(
                    agent_id=args.id, limit=args.limit
                )
                print(json.dumps(result, indent=2))

        elif args.command == "knowledge":
            if args.knowledge_command == "search":
                result = await cli.search_knowledge(query=args.query, limit=args.limit)
                print(json.dumps(result, indent=2))

        elif args.command == "task":
            if args.task_command == "dispatch":
                # Construct kwargs from specific args for the dispatched task
                task_kwargs = {}
                if args.task_name == "analyze_requirements":
                    task_kwargs = {"project_description": args.project_description}
                elif args.task_name == "plan_sprint":
                    task_kwargs = {
                        "project_id": args.project_id,
                        "sprint_duration_days": args.sprint_duration_days,
                    }
                elif args.task_name == "assign_task":
                    task_kwargs = {"task_id": args.task_id, "agent_id": args.agent_id}
                elif args.task_name == "update_task_status":
                    task_kwargs = {"task_id": args.task_id, "status": args.status}
                    if args.agent_id:
                        task_kwargs["agent_id"] = args.agent_id

                await cli.dispatch_celery_task(
                    task_name=args.task_name,
                    task_args=[],  # No positional args for these tasks yet
                    task_kwargs=task_kwargs,
                )

    except Exception as e:
        logger.error(f"CLI command failed: {e}", exc_info=True)
        print(f"Error: An unexpected error occurred. Check logs in {log_file}")
    finally:
        await cli.close()


def main():
    # Add check for Python version if needed
    if sys.version_info < (3, 8):
        sys.exit("Python 3.8 or higher is required.")

    # Setup asyncio loop
    try:
        asyncio.run(run_cli())
    except KeyboardInterrupt:
        logger.info("CLI terminated by user.")
        print("\nCLI terminated.")


if __name__ == "__main__":
    main()
