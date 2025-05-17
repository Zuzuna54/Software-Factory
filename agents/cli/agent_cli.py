"""
Command-line interface for testing agent interactions.

Features:
- Command parsing
- Agent initialization
- Interaction simulations
- Results display
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from agents.db import get_postgres_client
from agents.communication import (
    Message,
    MessageType,
    Protocol,
    Conversation,
)
from agents.communication.message import (
    create_request,
    create_inform,
    create_propose,
    create_confirm,
    create_alert,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("agent_cli")


class AgentCLI:
    """
    Command-line interface for testing agent interactions.

    Features:
    - Agent creation and configuration
    - Message sending between agents
    - Conversation management
    - Results display
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the agent CLI.

        Args:
            db_url: Optional database URL (read from environment if not provided)
        """
        # Get database URL from environment if not provided
        self.db_url = db_url or os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory",
        )

        # Agent registry
        self.agents: Dict[str, Dict[str, Any]] = {}

        # Conversation registry
        self.conversations: Dict[str, Conversation] = {}

        # Current conversation
        self.current_conversation_id: Optional[str] = None

        # Protocol instance (initialized on first use)
        self._protocol: Optional[Protocol] = None

        # Database client (initialized on first use)
        self._db_client = None

    @property
    def protocol(self) -> Protocol:
        """Get or create the protocol instance."""
        if self._protocol is None:
            # Initialize database client
            self._db_client = get_postgres_client(database_url=self.db_url)

            # Initialize protocol
            self._protocol = Protocol(
                db_client=self._db_client,
                validate_recipients=False,  # Allow unregistered agents for testing
            )

        return self._protocol

    @property
    def current_conversation(self) -> Optional[Conversation]:
        """Get the current conversation if set."""
        if self.current_conversation_id:
            return self.conversations.get(self.current_conversation_id)
        return None

    async def close(self):
        """Clean up resources."""
        if self._db_client:
            await self._db_client.close()

    # Agent management

    def create_agent(self, agent_id: Optional[str] = None, **kwargs) -> str:
        """
        Create a new agent.

        Args:
            agent_id: Optional agent ID (generated if not provided)
            **kwargs: Additional agent attributes

        Returns:
            Agent ID
        """
        agent_id = agent_id or f"agent-{len(self.agents) + 1}"

        # Register agent
        self.agents[agent_id] = {
            "id": agent_id,
            "created_at": datetime.utcnow(),
            **kwargs,
        }

        # Register with protocol
        self.protocol.register_agent(agent_id)

        logger.info(f"Created agent: {agent_id}")
        return agent_id

    def list_agents(self) -> List[str]:
        """
        List all registered agents.

        Returns:
            List of agent IDs
        """
        return list(self.agents.keys())

    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get agent details.

        Args:
            agent_id: ID of the agent to retrieve

        Returns:
            Agent details if found, None otherwise
        """
        return self.agents.get(agent_id)

    # Conversation management

    def create_conversation(
        self,
        conversation_id: Optional[str] = None,
        topic: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new conversation.

        Args:
            conversation_id: Optional conversation ID (generated if not provided)
            topic: Optional topic for the conversation
            metadata: Optional additional metadata for the conversation

        Returns:
            Conversation ID
        """
        # Create conversation
        conversation = Conversation(
            protocol=self.protocol,
            conversation_id=conversation_id,
            topic=topic,
            metadata=metadata,
        )

        # Register conversation
        self.conversations[conversation.conversation_id] = conversation

        # Set as current conversation
        self.current_conversation_id = conversation.conversation_id

        logger.info(f"Created conversation: {conversation.conversation_id}")
        return conversation.conversation_id

    def list_conversations(self) -> List[str]:
        """
        List all conversations.

        Returns:
            List of conversation IDs
        """
        return list(self.conversations.keys())

    def select_conversation(self, conversation_id: str) -> bool:
        """
        Select a conversation as the current conversation.

        Args:
            conversation_id: ID of the conversation to select

        Returns:
            True if the conversation was selected, False otherwise
        """
        if conversation_id in self.conversations:
            self.current_conversation_id = conversation_id
            logger.info(f"Selected conversation: {conversation_id}")
            return True

        logger.error(f"Conversation not found: {conversation_id}")
        return False

    async def get_conversation_summary(
        self, conversation_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a summary of a conversation.

        Args:
            conversation_id: Optional conversation ID (current conversation if not provided)

        Returns:
            Dictionary with conversation summary information, or None if not found
        """
        conversation_id = conversation_id or self.current_conversation_id

        if not conversation_id:
            logger.error("No conversation selected")
            return None

        conversation = self.conversations.get(conversation_id)
        if not conversation:
            logger.error(f"Conversation not found: {conversation_id}")
            return None

        return await conversation.get_summary()

    # Message operations

    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: MessageType,
        content: Dict[str, Any],
        conversation_id: Optional[str] = None,
        in_reply_to: Optional[str] = None,
    ) -> Optional[Message]:
        """
        Send a message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            message_type: Type of message (REQUEST, INFORM, etc.)
            content: Message content
            conversation_id: Optional conversation ID (current conversation if not provided)
            in_reply_to: Optional ID of the message this is replying to

        Returns:
            The message if sent successfully, None otherwise
        """
        # Check if sender exists
        if sender_id not in self.agents:
            logger.error(f"Sender agent not found: {sender_id}")
            return None

        # Check if recipient exists
        if recipient_id not in self.agents:
            logger.error(f"Recipient agent not found: {recipient_id}")
            return None

        # Determine conversation
        if conversation_id:
            # Use specified conversation
            if conversation_id not in self.conversations:
                logger.error(f"Conversation not found: {conversation_id}")
                return None
            conversation = self.conversations[conversation_id]
        elif self.current_conversation_id:
            # Use current conversation
            conversation = self.conversations[self.current_conversation_id]
        else:
            # Create a new conversation
            conversation_id = self.create_conversation(
                topic=f"Conversation between {sender_id} and {recipient_id}"
            )
            conversation = self.conversations[conversation_id]

        # Create message
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            conversation_id=conversation.conversation_id,
            in_reply_to=in_reply_to,
        )

        # Send through conversation
        success = await conversation.add_message(message)

        if success:
            logger.info(f"Message sent: {message.message_id}")
            return message

        logger.error("Failed to send message")
        return None

    async def send_request(
        self,
        sender_id: str,
        recipient_id: str,
        action: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: int = 3,
        **kwargs,
    ) -> Optional[Message]:
        """
        Send a request message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            action: The action being requested
            parameters: Parameters for the requested action
            priority: Priority of the request (1-5, with 5 being highest)
            **kwargs: Additional message arguments

        Returns:
            The message if sent successfully, None otherwise
        """
        message = create_request(
            sender_id=sender_id,
            recipient_id=recipient_id,
            action=action,
            parameters=parameters,
            priority=priority,
            **kwargs,
        )

        if self.current_conversation:
            success = await self.current_conversation.add_message(message)
            return message if success else None

        success = await self.protocol.send_message(message)
        return message if success else None

    async def send_inform(
        self,
        sender_id: str,
        recipient_id: str,
        information_type: str,
        data: Any,
        **kwargs,
    ) -> Optional[Message]:
        """
        Send an inform message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            information_type: Type of information being provided
            data: The actual information or results
            **kwargs: Additional message arguments

        Returns:
            The message if sent successfully, None otherwise
        """
        message = create_inform(
            sender_id=sender_id,
            recipient_id=recipient_id,
            information_type=information_type,
            data=data,
            **kwargs,
        )

        if self.current_conversation:
            success = await self.current_conversation.add_message(message)
            return message if success else None

        success = await self.protocol.send_message(message)
        return message if success else None

    async def send_propose(
        self,
        sender_id: str,
        recipient_id: str,
        proposal_type: str,
        proposal: Dict[str, Any],
        alternatives: Optional[List[Dict[str, Any]]] = None,
        reasoning: Optional[str] = None,
        **kwargs,
    ) -> Optional[Message]:
        """
        Send a propose message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            proposal_type: Type of proposal
            proposal: The actual proposal content
            alternatives: Alternative proposals if any
            reasoning: Reasoning behind the proposal
            **kwargs: Additional message arguments

        Returns:
            The message if sent successfully, None otherwise
        """
        message = create_propose(
            sender_id=sender_id,
            recipient_id=recipient_id,
            proposal_type=proposal_type,
            proposal=proposal,
            alternatives=alternatives,
            reasoning=reasoning,
            **kwargs,
        )

        if self.current_conversation:
            success = await self.current_conversation.add_message(message)
            return message if success else None

        success = await self.protocol.send_message(message)
        return message if success else None

    async def send_confirm(
        self,
        sender_id: str,
        recipient_id: str,
        confirmation_type: str,
        confirmed_item_id: str,
        comments: Optional[str] = None,
        **kwargs,
    ) -> Optional[Message]:
        """
        Send a confirm message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            confirmation_type: Type of confirmation
            confirmed_item_id: ID of the item being confirmed
            comments: Optional comments on the confirmation
            **kwargs: Additional message arguments

        Returns:
            The message if sent successfully, None otherwise
        """
        message = create_confirm(
            sender_id=sender_id,
            recipient_id=recipient_id,
            confirmation_type=confirmation_type,
            confirmed_item_id=confirmed_item_id,
            comments=comments,
            **kwargs,
        )

        if self.current_conversation:
            success = await self.current_conversation.add_message(message)
            return message if success else None

        success = await self.protocol.send_message(message)
        return message if success else None

    async def send_alert(
        self,
        sender_id: str,
        recipient_id: str,
        alert_type: str,
        severity: int,
        details: str,
        suggested_actions: Optional[List[str]] = None,
        **kwargs,
    ) -> Optional[Message]:
        """
        Send an alert message.

        Args:
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            alert_type: Type of alert
            severity: Severity of the alert (1-5, with 5 being highest)
            details: Details of the alert
            suggested_actions: Suggested actions to address the problem
            **kwargs: Additional message arguments

        Returns:
            The message if sent successfully, None otherwise
        """
        message = create_alert(
            sender_id=sender_id,
            recipient_id=recipient_id,
            alert_type=alert_type,
            severity=severity,
            details=details,
            suggested_actions=suggested_actions,
            **kwargs,
        )

        if self.current_conversation:
            success = await self.current_conversation.add_message(message)
            return message if success else None

        success = await self.protocol.send_message(message)
        return message if success else None

    # History and retrieval

    async def get_agent_messages(
        self,
        agent_id: str,
        as_sender: bool = True,
        as_recipient: bool = True,
        limit: int = 10,
    ) -> List[Message]:
        """
        Get messages for an agent.

        Args:
            agent_id: ID of the agent
            as_sender: Whether to include messages sent by the agent
            as_recipient: Whether to include messages received by the agent
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages for the agent
        """
        return await self.protocol.get_agent_messages(
            agent_id=agent_id,
            as_sender=as_sender,
            as_recipient=as_recipient,
            limit=limit,
        )

    async def get_conversation_messages(
        self,
        conversation_id: Optional[str] = None,
        limit: int = 10,
    ) -> List[Message]:
        """
        Get messages in a conversation.

        Args:
            conversation_id: Optional conversation ID (current conversation if not provided)
            limit: Maximum number of messages to retrieve

        Returns:
            List of messages in the conversation
        """
        conversation_id = conversation_id or self.current_conversation_id

        if not conversation_id:
            logger.error("No conversation selected")
            return []

        return await self.protocol.get_conversation_messages(
            conversation_id=conversation_id,
            limit=limit,
        )


# Command parser and runner
def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Agent testing CLI")

    # Main command groups
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Agent commands
    agent_parser = subparsers.add_parser("agent", help="Agent management commands")
    agent_subparsers = agent_parser.add_subparsers(
        dest="subcommand", help="Agent subcommand"
    )

    # Create agent
    create_agent_parser = agent_subparsers.add_parser(
        "create", help="Create a new agent"
    )
    create_agent_parser.add_argument(
        "--id", help="Agent ID (generated if not provided)"
    )
    create_agent_parser.add_argument("--name", help="Agent name")
    create_agent_parser.add_argument("--type", help="Agent type")

    # List agents
    agent_subparsers.add_parser("list", help="List all agents")

    # Show agent details
    show_agent_parser = agent_subparsers.add_parser("show", help="Show agent details")
    show_agent_parser.add_argument("id", help="Agent ID")

    # Conversation commands
    conversation_parser = subparsers.add_parser(
        "conversation", help="Conversation management commands"
    )
    conversation_subparsers = conversation_parser.add_subparsers(
        dest="subcommand", help="Conversation subcommand"
    )

    # Create conversation
    create_conversation_parser = conversation_subparsers.add_parser(
        "create", help="Create a new conversation"
    )
    create_conversation_parser.add_argument(
        "--id", help="Conversation ID (generated if not provided)"
    )
    create_conversation_parser.add_argument("--topic", help="Conversation topic")

    # List conversations
    conversation_subparsers.add_parser("list", help="List all conversations")

    # Select conversation
    select_conversation_parser = conversation_subparsers.add_parser(
        "select", help="Select a conversation"
    )
    select_conversation_parser.add_argument("id", help="Conversation ID")

    # Show conversation details
    show_conversation_parser = conversation_subparsers.add_parser(
        "show", help="Show conversation details"
    )
    show_conversation_parser.add_argument(
        "--id", help="Conversation ID (current if not provided)"
    )
    show_conversation_parser.add_argument(
        "--messages", action="store_true", help="Show messages in the conversation"
    )
    show_conversation_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of messages to show"
    )

    # Message commands
    message_parser = subparsers.add_parser("message", help="Message commands")
    message_subparsers = message_parser.add_subparsers(
        dest="subcommand", help="Message subcommand"
    )

    # Send message
    send_parser = message_subparsers.add_parser("send", help="Send a message")
    send_parser.add_argument(
        "--type",
        choices=[t.value for t in MessageType],
        required=True,
        help="Message type",
    )
    send_parser.add_argument("--sender", required=True, help="Sender agent ID")
    send_parser.add_argument("--recipient", required=True, help="Recipient agent ID")
    send_parser.add_argument(
        "--content", required=True, help="Message content (JSON string)"
    )
    send_parser.add_argument("--reply-to", help="ID of the message this is replying to")

    # Send request message
    request_parser = message_subparsers.add_parser(
        "request", help="Send a request message"
    )
    request_parser.add_argument("--sender", required=True, help="Sender agent ID")
    request_parser.add_argument("--recipient", required=True, help="Recipient agent ID")
    request_parser.add_argument("--action", required=True, help="Action to request")
    request_parser.add_argument(
        "--parameters", help="Parameters for the action (JSON string)"
    )
    request_parser.add_argument(
        "--priority", type=int, default=3, help="Priority (1-5)"
    )
    request_parser.add_argument(
        "--reply-to", help="ID of the message this is replying to"
    )

    # Send inform message
    inform_parser = message_subparsers.add_parser(
        "inform", help="Send an inform message"
    )
    inform_parser.add_argument("--sender", required=True, help="Sender agent ID")
    inform_parser.add_argument("--recipient", required=True, help="Recipient agent ID")
    inform_parser.add_argument("--type", required=True, help="Type of information")
    inform_parser.add_argument(
        "--data", required=True, help="Information data (JSON string)"
    )
    inform_parser.add_argument(
        "--reply-to", help="ID of the message this is replying to"
    )

    # List messages
    list_parser = message_subparsers.add_parser("list", help="List messages")
    list_parser.add_argument("--agent", help="Agent ID to filter by")
    list_parser.add_argument("--conversation", help="Conversation ID to filter by")
    list_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of messages to show"
    )

    # Simulation commands
    simulation_parser = subparsers.add_parser("simulation", help="Simulation commands")
    simulation_subparsers = simulation_parser.add_subparsers(
        dest="subcommand", help="Simulation subcommand"
    )

    # Run a predefined simulation
    run_parser = simulation_subparsers.add_parser(
        "run", help="Run a predefined simulation"
    )
    run_parser.add_argument(
        "scenario",
        choices=["basic", "planning", "problem-solving"],
        help="Scenario to run",
    )

    return parser.parse_args()


async def handle_command(args: argparse.Namespace) -> None:
    """Handle a command."""
    cli = AgentCLI()

    try:
        if args.command == "agent":
            if args.subcommand == "create":
                agent_id = cli.create_agent(args.id, name=args.name, type=args.type)
                print(f"Created agent: {agent_id}")

            elif args.subcommand == "list":
                agents = cli.list_agents()
                if agents:
                    print("Agents:")
                    for agent_id in agents:
                        print(f"  - {agent_id}")
                else:
                    print("No agents")

            elif args.subcommand == "show":
                agent = cli.get_agent(args.id)
                if agent:
                    print(f"Agent: {args.id}")
                    for key, value in agent.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"Agent not found: {args.id}")

        elif args.command == "conversation":
            if args.subcommand == "create":
                conversation_id = cli.create_conversation(args.id, args.topic)
                print(f"Created and selected conversation: {conversation_id}")

            elif args.subcommand == "list":
                conversations = cli.list_conversations()
                if conversations:
                    print("Conversations:")
                    for conversation_id in conversations:
                        if conversation_id == cli.current_conversation_id:
                            print(f"  - {conversation_id} (current)")
                        else:
                            print(f"  - {conversation_id}")
                else:
                    print("No conversations")

            elif args.subcommand == "select":
                if cli.select_conversation(args.id):
                    print(f"Selected conversation: {args.id}")
                else:
                    print(f"Conversation not found: {args.id}")

            elif args.subcommand == "show":
                conversation_id = args.id or cli.current_conversation_id
                if not conversation_id:
                    print("No conversation selected")
                    return

                summary = await cli.get_conversation_summary(conversation_id)
                if summary:
                    print(f"Conversation: {conversation_id}")
                    for key, value in summary.items():
                        if key != "metadata":
                            print(f"  {key}: {value}")

                if args.messages:
                    messages = await cli.get_conversation_messages(
                        conversation_id, args.limit
                    )
                    if messages:
                        print(f"\nMessages ({len(messages)}):")
                        for msg in messages:
                            print(
                                f"  - {msg.created_at.isoformat()} | {msg.sender_id} -> {msg.recipient_id} [{msg.message_type.value}]"
                            )
                    else:
                        print("\nNo messages")

        elif args.command == "message":
            if args.subcommand == "send":
                content = json.loads(args.content)
                message = await cli.send_message(
                    sender_id=args.sender,
                    recipient_id=args.recipient,
                    message_type=MessageType(args.type),
                    content=content,
                    in_reply_to=args.reply_to,
                )
                if message:
                    print(f"Message sent: {message.message_id}")
                else:
                    print("Failed to send message")

            elif args.subcommand == "request":
                parameters = json.loads(args.parameters) if args.parameters else None
                message = await cli.send_request(
                    sender_id=args.sender,
                    recipient_id=args.recipient,
                    action=args.action,
                    parameters=parameters,
                    priority=args.priority,
                    in_reply_to=args.reply_to,
                )
                if message:
                    print(f"Request sent: {message.message_id}")
                else:
                    print("Failed to send request")

            elif args.subcommand == "inform":
                data = json.loads(args.data)
                message = await cli.send_inform(
                    sender_id=args.sender,
                    recipient_id=args.recipient,
                    information_type=args.type,
                    data=data,
                    in_reply_to=args.reply_to,
                )
                if message:
                    print(f"Information sent: {message.message_id}")
                else:
                    print("Failed to send information")

            elif args.subcommand == "list":
                if args.agent:
                    messages = await cli.get_agent_messages(
                        args.agent, limit=args.limit
                    )
                    if messages:
                        print(f"Messages for agent {args.agent} ({len(messages)}):")
                        for msg in messages:
                            print(
                                f"  - {msg.created_at.isoformat()} | {msg.sender_id} -> {msg.recipient_id} [{msg.message_type.value}]"
                            )
                    else:
                        print(f"No messages for agent {args.agent}")

                elif args.conversation or cli.current_conversation_id:
                    conversation_id = args.conversation or cli.current_conversation_id
                    messages = await cli.get_conversation_messages(
                        conversation_id, args.limit
                    )
                    if messages:
                        print(
                            f"Messages in conversation {conversation_id} ({len(messages)}):"
                        )
                        for msg in messages:
                            print(
                                f"  - {msg.created_at.isoformat()} | {msg.sender_id} -> {msg.recipient_id} [{msg.message_type.value}]"
                            )
                    else:
                        print(f"No messages in conversation {conversation_id}")

                else:
                    print("No agent or conversation specified")

        elif args.command == "simulation":
            if args.subcommand == "run":
                await run_simulation(cli, args.scenario)

    finally:
        await cli.close()


async def run_simulation(cli: AgentCLI, scenario: str) -> None:
    """
    Run a predefined simulation scenario.

    Args:
        cli: The AgentCLI instance
        scenario: Scenario to run ('basic', 'planning', 'problem-solving')
    """
    print(f"Running {scenario} simulation...")

    if scenario == "basic":
        # Create agents with valid UUIDs
        agent1_id = cli.create_agent(agent_id=str(uuid.uuid4()), name="Planner Agent")
        agent2_id = cli.create_agent(agent_id=str(uuid.uuid4()), name="Executor Agent")

        # Create conversation
        conversation_id = cli.create_conversation(topic="Basic Interaction")

        # Send a request
        request = await cli.send_request(
            sender_id=agent1_id,
            recipient_id=agent2_id,
            action="process_data",
            parameters={"file": "data.csv", "filter": "status=active"},
            priority=4,
        )

        # Send a response (only if request was successful)
        if request:
            await cli.send_inform(
                sender_id=agent2_id,
                recipient_id=agent1_id,
                information_type="result",
                data={"processed": 100, "filtered": 75},
                in_reply_to=request.message_id,
            )
        else:
            # Send without in_reply_to if request failed
            await cli.send_inform(
                sender_id=agent2_id,
                recipient_id=agent1_id,
                information_type="result",
                data={"processed": 100, "filtered": 75},
            )

        # Send an alert
        await cli.send_alert(
            sender_id=agent2_id,
            recipient_id=agent1_id,
            alert_type="performance",
            severity=2,
            details="Processing took longer than expected",
            suggested_actions=["optimize filter", "reduce data set"],
        )

        # Show results
        messages = await cli.get_conversation_messages(conversation_id)
        print(f"\nSimulation completed with {len(messages)} messages")

        # Show context window if available
        if cli.current_conversation:
            context = cli.current_conversation.get_context()
            print(f"\nContext Window ({len(context)} messages):")
            for message in context:
                print(f"  - {message}")
        else:
            print("\nNo context window available")

    elif scenario == "planning":
        # Create agents with valid UUIDs
        planner_id = cli.create_agent(agent_id=str(uuid.uuid4()), name="Planner Agent")
        analyst_id = cli.create_agent(agent_id=str(uuid.uuid4()), name="Analyst Agent")
        executor_id = cli.create_agent(
            agent_id=str(uuid.uuid4()), name="Executor Agent"
        )

        # Create conversation
        conversation_id = cli.create_conversation(topic="Project Planning")

        # Planner proposes a plan
        proposal = await cli.send_propose(
            sender_id=planner_id,
            recipient_id=analyst_id,
            proposal_type="project_plan",
            proposal={
                "steps": ["Data collection", "Analysis", "Implementation", "Testing"],
                "timeline": "2 weeks",
            },
            reasoning="Based on project requirements and resource availability",
        )

        # Continue only if proposal was sent successfully
        if proposal:
            # Analyst reviews plan
            confirmation = await cli.send_confirm(
                sender_id=analyst_id,
                recipient_id=planner_id,
                confirmation_type="plan_review",
                confirmed_item_id=proposal.message_id,
                comments="Plan looks good, but we need to add a validation step",
            )

            # Continue only if confirmation was sent successfully
            if confirmation:
                # Planner updates plan
                revised_proposal = await cli.send_propose(
                    sender_id=planner_id,
                    recipient_id=analyst_id,
                    proposal_type="revised_project_plan",
                    proposal={
                        "steps": [
                            "Data collection",
                            "Analysis",
                            "Implementation",
                            "Validation",
                            "Testing",
                        ],
                        "timeline": "2.5 weeks",
                    },
                    reasoning="Added validation step as requested",
                    in_reply_to=confirmation.message_id,
                )

                # Continue only if revised proposal was sent successfully
                if revised_proposal:
                    # Analyst approves revised plan
                    approval = await cli.send_confirm(
                        sender_id=analyst_id,
                        recipient_id=planner_id,
                        confirmation_type="plan_approval",
                        confirmed_item_id=revised_proposal.message_id,
                        comments="Revised plan approved",
                    )

                    # Continue only if approval was sent successfully
                    if approval:
                        # Planner assigns tasks to executor
                        await cli.send_request(
                            sender_id=planner_id,
                            recipient_id=executor_id,
                            action="implement_plan",
                            parameters={"plan_id": revised_proposal.message_id},
                            priority=5,
                        )

        # Show results
        messages = await cli.get_conversation_messages(conversation_id)
        print(f"\nSimulation completed with {len(messages)} messages")

        # Show thread structure if proposal exists and conversation exists
        if proposal and cli.current_conversation:
            try:
                thread = await cli.current_conversation.get_thread(proposal.message_id)
                print(
                    f"\nThread for initial proposal ({len(thread['replies'])} replies):"
                )
                for message in thread["replies"]:
                    print(f"  - {message}")
            except Exception as e:
                print(f"\nCould not get thread: {str(e)}")
        else:
            print("\nNo thread information available")

    elif scenario == "problem-solving":
        # Create agents with valid UUIDs
        detector_id = cli.create_agent(
            agent_id=str(uuid.uuid4()), name="Problem Detector"
        )
        analyzer_id = cli.create_agent(
            agent_id=str(uuid.uuid4()), name="Problem Analyzer"
        )
        solver_id = cli.create_agent(agent_id=str(uuid.uuid4()), name="Problem Solver")

        # Create conversation
        conversation_id = cli.create_conversation(topic="Problem Solving")

        # Detector reports a problem
        alert = await cli.send_alert(
            sender_id=detector_id,
            recipient_id=analyzer_id,
            alert_type="system_error",
            severity=4,
            details="Database connection failures detected in production",
            suggested_actions=["check connection pool", "review recent changes"],
        )

        if alert:
            # Analyzer requests more information
            info_request = await cli.send_request(
                sender_id=analyzer_id,
                recipient_id=detector_id,
                action="provide_details",
                parameters={
                    "error_id": alert.message_id,
                    "fields": ["stack_trace", "frequency", "affected_services"],
                },
                priority=4,
                in_reply_to=alert.message_id,
            )

            if info_request:
                # Detector provides details
                details = await cli.send_inform(
                    sender_id=detector_id,
                    recipient_id=analyzer_id,
                    information_type="error_details",
                    data={
                        "stack_trace": "Connection timeout after 30s",
                        "frequency": "Every 5 minutes",
                        "affected_services": ["user-api", "payment-service"],
                    },
                    in_reply_to=info_request.message_id,
                )

                # Proceed only if details were sent successfully
                if details:
                    # Analyzer diagnoses problem
                    diagnosis = await cli.send_inform(
                        sender_id=analyzer_id,
                        recipient_id=solver_id,
                        information_type="problem_diagnosis",
                        data={
                            "root_cause": "Connection pool exhaustion",
                            "evidence": [
                                "timeout errors",
                                "high frequency",
                                "multiple services affected",
                            ],
                            "confidence": 0.85,
                        },
                    )

                    if diagnosis:
                        # Solver proposes solution
                        solution = await cli.send_propose(
                            sender_id=solver_id,
                            recipient_id=analyzer_id,
                            proposal_type="solution",
                            proposal={
                                "action": "increase_connection_pool",
                                "parameters": {"new_size": 50, "timeout": 60},
                                "expected_outcome": "Resolve connection failures",
                            },
                            alternatives=[
                                {
                                    "action": "add_connection_retry",
                                    "parameters": {
                                        "max_retries": 3,
                                        "backoff": "exponential",
                                    },
                                    "expected_outcome": "Mitigate intermittent failures",
                                }
                            ],
                            in_reply_to=diagnosis.message_id,
                        )

                        if solution:
                            # Analyzer approves solution
                            await cli.send_confirm(
                                sender_id=analyzer_id,
                                recipient_id=solver_id,
                                confirmation_type="solution_approval",
                                confirmed_item_id=solution.message_id,
                                comments="Proceed with the recommended solution",
                            )

        # Show results
        messages = await cli.get_conversation_messages(conversation_id)
        print(f"\nSimulation completed with {len(messages)} messages")

        # Show conversation summary
        try:
            summary = await cli.get_conversation_summary(conversation_id)
            print("\nConversation Summary:")
            for key, value in summary.items():
                if key not in ["metadata", "created_at", "last_activity", "duration"]:
                    print(f"  {key}: {value}")
        except Exception as e:
            print(f"\nCould not get conversation summary: {str(e)}")


def main():
    """Main entry point."""
    args = parse_args()

    if not args.command:
        print("No command specified")
        return

    # Run the command handler
    asyncio.run(handle_command(args))


if __name__ == "__main__":
    main()
