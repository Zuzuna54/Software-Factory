# agents/cli/agent_cli.py

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Adjust imports based on actual project structure
# Assumes the CLI is run from the project root or the agents package is installed
try:
    from ..base_agent import BaseAgent
    from ..db.postgres import PostgresClient
    from ..llm.vertex_gemini_provider import VertexGeminiProvider
    from ..memory.vector_memory import VectorMemory
    from ..communication.protocol import (
        CommunicationProtocol,
        AgentMessage,
        MessageType,
    )
except ImportError:
    # Fallback for running script directly during development
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from agents.base_agent import BaseAgent
    from agents.db.postgres import PostgresClient
    from agents.llm.vertex_gemini_provider import VertexGeminiProvider
    from agents.memory.vector_memory import VectorMemory
    from agents.communication.protocol import (
        CommunicationProtocol,
        AgentMessage,
        MessageType,
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


class AgentCLI:
    """Command-line interface for testing agent interactions."""

    def __init__(self):
        self.db_client: Optional[PostgresClient] = None
        self.llm_provider: Optional[VertexGeminiProvider] = None
        self.vector_memory: Optional[VectorMemory] = None
        self.comm_protocol: CommunicationProtocol = (
            CommunicationProtocol()
        )  # Use the protocol helper
        self.agents: Dict[str, BaseAgent] = {}  # In-memory store for agent instances
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the CLI and required services."""
        if self._initialized:
            return
        logger.info("Initializing CLI services...")
        try:
            # Initialize database client
            self.db_client = PostgresClient()  # Reads URL from ENV or uses default
            await self.db_client.initialize()

            # Initialize LLM provider (ensure GOOGLE_CLOUD_PROJECT is set in env)
            self.llm_provider = VertexGeminiProvider()

            # Initialize vector memory
            self.vector_memory = VectorMemory(self.db_client)
            await self.vector_memory.initialize()

            self._initialized = True
            logger.info("CLI services initialized successfully.")
        except Exception as e:
            logger.error(f"CLI Initialization failed: {e}", exc_info=True)
            # Exit or handle? For a CLI, exiting might be appropriate.
            sys.exit(1)

    async def _ensure_initialized(self):
        if not self._initialized:
            await self.initialize()
        if not self._initialized:
            raise RuntimeError("CLI Services could not be initialized.")

    async def create_agent(
        self, agent_type: str, agent_name: str, capabilities_json: Optional[str] = None
    ) -> Optional[str]:
        """Create a new agent instance and register it."""
        await self._ensure_initialized()

        capabilities = {}
        if capabilities_json:
            try:
                capabilities = json.loads(capabilities_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format for capabilities: {e}")
                return None

        # For now, we only instantiate BaseAgent. Later, use a factory pattern.
        # TODO: Implement agent factory based on agent_type
        if agent_type != "base":
            logger.warning(
                f"Only 'base' agent type supported currently. Creating BaseAgent."
            )
            agent_type = "base"  # Force base type for now

        agent = BaseAgent(
            agent_type=agent_type,
            agent_name=agent_name,
            llm_provider=self.llm_provider,
            db_client=self.db_client,
            vector_memory=self.vector_memory,
            comm_protocol=self.comm_protocol,  # Pass protocol instance
            capabilities=capabilities,
        )

        # BaseAgent constructor now handles registration via asyncio task
        # Wait a moment to allow registration task to potentially complete
        await asyncio.sleep(0.1)

        self.agents[agent.agent_id] = agent  # Keep track of the instance locally
        logger.info(
            f"Created agent: {agent_type} - {agent_name} (ID: {agent.agent_id})"
        )
        print(f"Agent Created: ID = {agent.agent_id}")
        return agent.agent_id

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
        """Send a message from one agent to another via the protocol."""
        await self._ensure_initialized()

        # Find the sending agent instance (if created via this CLI session)
        # Note: This only works for agents created in the current CLI session.
        # A more robust CLI might load agent details from DB instead of requiring local instance.
        sender_agent = self.agents.get(sender_id)
        if not sender_agent:
            logger.error(
                f"Sender agent {sender_id} not found in this CLI session. Cannot send message."
            )
            print(f"Error: Sender agent {sender_id} not managed by this CLI session.")
            return None

        try:
            message_type = MessageType(message_type_str.upper())
        except ValueError:
            logger.error(f"Invalid message type: {message_type_str}")
            print(
                f"Error: Invalid message type '{message_type_str}'. Valid types: {[t.value for t in MessageType]}"
            )
            return None

        metadata = {}
        if metadata_json:
            try:
                metadata = json.loads(metadata_json)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON format for metadata: {e}")
                print(f"Error: Invalid JSON for metadata: {e}")
                return None

        # Use the CommunicationProtocol to create the message object
        message = self.comm_protocol._create_message(  # Using internal helper for flexibility here
            sender=sender_id,
            receiver=receiver_id,
            message_type=message_type,
            content=content,
            conversation_id=conv_id,
            related_task=task_id,
            metadata=metadata,
        )

        # Use the agent's send_message method
        message_id = await sender_agent.send_message(message)

        if message_id:
            logger.info(f"Message {message_id} sent: {sender_id} -> {receiver_id}")
            print(f"Message Sent: ID = {message_id}")
            return message_id
        else:
            logger.error(f"Failed to send message from {sender_id} to {receiver_id}")
            print("Error: Failed to send message.")
            return None

    async def get_agent_messages(
        self, agent_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent messages received by the specified agent."""
        await self._ensure_initialized()

        # Find agent instance if managed by CLI, otherwise create a temporary one to use receive_messages
        agent = self.agents.get(agent_id)
        if not agent:
            # Create a temporary BaseAgent instance just to use the receive_messages method
            # This allows checking messages for agents not created in this session
            logger.warning(
                f"Agent {agent_id} not in CLI memory, creating temporary instance to fetch messages."
            )
            agent = BaseAgent(
                agent_id=agent_id,
                db_client=self.db_client,
                comm_protocol=self.comm_protocol,
                # No LLM/Memory needed just to receive
            )
            # We don't store this temp agent in self.agents

        messages = await agent.receive_messages(limit=limit)
        # Convert AgentMessage objects back to dicts for printing
        return [msg.to_dict() for msg in messages]

    async def search_knowledge(
        self, query: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for knowledge (currently messages) related to the query using vector search."""
        await self._ensure_initialized()
        if not self.vector_memory or not self.llm_provider or not self.db_client:
            logger.error(
                "Required components (DB, LLM, Memory) not available for search."
            )
            return []

        # Use a temporary BaseAgent instance to perform the search
        # This avoids needing a specific agent instance just for searching
        temp_search_agent = BaseAgent(
            llm_provider=self.llm_provider,
            db_client=self.db_client,
            vector_memory=self.vector_memory,
            comm_protocol=self.comm_protocol,
        )

        similar_messages = await temp_search_agent.search_messages(query, limit)
        return [msg.to_dict() for msg in similar_messages]

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
            conditions.append(
                f"activity_type ILIKE ${param_idx}"
            )  # Use ILIKE for case-insensitivity
            params.append(f"%{activity_type}%")  # Allow partial matching
            param_idx += 1

        query = f"""
        SELECT
            activity_id, timestamp, activity_type,
            description, thought_process, input_data, output_data,
            decisions_made, execution_time_ms, related_task_id
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
        "create", help="Create a new agent"
    )
    parser_agent_create.add_argument(
        "--type", type=str, default="base", help="Type of agent (default: base)"
    )
    parser_agent_create.add_argument(
        "--name", type=str, required=True, help="Name for the new agent"
    )
    parser_agent_create.add_argument(
        "--capabilities", type=str, help="JSON string of agent capabilities"
    )

    # agent list
    parser_agent_list = agent_subparsers.add_parser(
        "list", help="List registered agents"
    )

    # agent activities
    parser_agent_activities = agent_subparsers.add_parser(
        "activities", help="Show agent activities"
    )
    parser_agent_activities.add_argument(
        "--id", type=str, required=True, help="Agent ID"
    )
    parser_agent_activities.add_argument(
        "--type",
        type=str,
        help="Filter by activity type (case-insensitive, partial match)",
    )
    parser_agent_activities.add_argument(
        "--limit", type=int, default=10, help="Max number of activities to show"
    )

    # --- Message Commands ---
    parser_msg = subparsers.add_parser("message", help="Manage messages")
    msg_subparsers = parser_msg.add_subparsers(
        dest="message_command", help="Message actions", required=True
    )

    # message send
    parser_msg_send = msg_subparsers.add_parser("send", help="Send a message")
    parser_msg_send.add_argument(
        "--sender",
        type=str,
        required=True,
        help="Sender agent ID (must be managed by this CLI session)",
    )
    parser_msg_send.add_argument(
        "--receiver", type=str, required=True, help="Receiver agent ID"
    )
    parser_msg_send.add_argument(
        "--content", type=str, required=True, help="Message content"
    )
    parser_msg_send.add_argument(
        "--type",
        type=str,
        default="INFORM",
        help=f"Message type (e.g., {', '.join([t.value for t in MessageType])})",
        choices=[t.value for t in MessageType],
    )
    parser_msg_send.add_argument("--conv-id", type=str, help="Optional conversation ID")
    parser_msg_send.add_argument("--task-id", type=str, help="Optional related task ID")
    parser_msg_send.add_argument(
        "--metadata", type=str, help="Optional JSON string for metadata"
    )

    # message receive
    parser_msg_receive = msg_subparsers.add_parser(
        "receive", help="Receive messages for an agent"
    )
    parser_msg_receive.add_argument(
        "--id", type=str, required=True, help="Agent ID to receive messages for"
    )
    parser_msg_receive.add_argument(
        "--limit", type=int, default=10, help="Max number of messages to show"
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
        "search", help="Search knowledge (currently messages)"
    )
    parser_knowledge_search.add_argument(
        "--query", type=str, required=True, help="Search query text"
    )
    parser_knowledge_search.add_argument(
        "--limit", type=int, default=5, help="Max number of results"
    )

    # --- Parse args ---
    args = parser.parse_args()

    # --- Execute command ---
    cli = AgentCLI()
    try:
        await cli.initialize()

        if args.command == "agent":
            if args.agent_command == "create":
                await cli.create_agent(args.type, args.name, args.capabilities)
            elif args.agent_command == "list":
                agents = await cli.list_agents()
                print(json.dumps(agents, indent=2))
            elif args.agent_command == "activities":
                activities = await cli.get_agent_activities(
                    args.id, args.type, args.limit
                )
                print(json.dumps(activities, indent=2))

        elif args.command == "message":
            if args.message_command == "send":
                await cli.send_message(
                    args.sender,
                    args.receiver,
                    args.content,
                    args.type,
                    args.conv_id,
                    args.task_id,
                    args.metadata,
                )
            elif args.message_command == "receive":
                messages = await cli.get_agent_messages(args.id, args.limit)
                print(json.dumps(messages, indent=2))

        elif args.command == "knowledge":
            if args.knowledge_command == "search":
                results = await cli.search_knowledge(args.query, args.limit)
                print(json.dumps(results, indent=2))

    except Exception as e:
        logger.error(f"CLI command failed: {e}", exc_info=True)
        print(f"Error: {e}")
    finally:
        await cli.close()


def main():
    if __name__ == "__main__":
        try:
            asyncio.run(run_cli())
        except KeyboardInterrupt:
            print("\nCLI interrupted by user.")
            sys.exit(0)


main()
