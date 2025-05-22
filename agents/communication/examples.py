"""
Examples of using the agent-to-agent communication protocol.

These examples demonstrate:
- Creating and sending different types of messages
- Working with conversations
- Message threading
- Retrieving conversation history
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents.db import get_postgres_client
from .message import (
    Message,
    MessageType,
    create_request,
    create_inform,
    create_propose,
    create_confirm,
    create_alert,
)
from .protocol import Protocol
from .conversation import Conversation


# Example message handlers
async def handle_request(message: Message) -> None:
    """Example handler for REQUEST messages."""
    print(f"Handling REQUEST: {message}")
    print(f"Action requested: {message.content.get('action')}")

    # In a real implementation, this would execute the requested action
    # and send back a response


async def handle_inform(message: Message) -> None:
    """Example handler for INFORM messages."""
    print(f"Handling INFORM: {message}")
    print(f"Information type: {message.content.get('information_type')}")
    print(f"Data: {message.content.get('data')}")


async def handle_alert(message: Message) -> None:
    """Example handler for ALERT messages."""
    print(f"Handling ALERT: {message}")
    print(f"Alert type: {message.content.get('alert_type')}")
    print(f"Severity: {message.content.get('severity')}")
    print(f"Details: {message.content.get('details')}")

    # In a real implementation, this would trigger appropriate alert handling


async def example_simple_messaging(protocol: Protocol) -> None:
    """Example of basic messaging between agents."""
    # Register some agents
    protocol.register_agent("agent-1")
    protocol.register_agent("agent-2")

    # Register message handlers
    protocol.register_handler(MessageType.REQUEST, handle_request)
    protocol.register_handler(MessageType.INFORM, handle_inform)
    protocol.register_handler(MessageType.ALERT, handle_alert)

    # Create and send various message types
    print("\n--- Example: Simple Messaging ---")

    # Request message
    request = create_request(
        sender_id="agent-1",
        recipient_id="agent-2",
        action="process_data",
        parameters={"file_path": "/data/example.csv", "output_format": "json"},
        priority=4,
    )
    success = await protocol.send_message(request)
    print(f"Request sent: {success}")

    # Inform message (as a reply to the request)
    inform = create_inform(
        sender_id="agent-2",
        recipient_id="agent-1",
        information_type="process_results",
        data={"status": "completed", "records_processed": 1000},
        in_reply_to=request.message_id,
    )
    success = await protocol.send_message(inform)
    print(f"Inform sent: {success}")

    # Alert message
    alert = create_alert(
        sender_id="agent-2",
        recipient_id="agent-1",
        alert_type="resource_warning",
        severity=3,
        details="Memory usage exceeding 80% threshold",
    )
    success = await protocol.send_message(alert)
    print(f"Alert sent: {success}")

    # Retrieve messages
    agent1_messages = await protocol.get_agent_messages("agent-1", limit=10)
    print(f"Agent 1 has {len(agent1_messages)} messages")

    agent2_messages = await protocol.get_agent_messages("agent-2", limit=10)
    print(f"Agent 2 has {len(agent2_messages)} messages")


async def example_conversation(protocol: Protocol) -> None:
    """Example of managing a conversation between agents."""
    print("\n--- Example: Conversation Management ---")

    # Create a conversation
    conversation = Conversation(
        protocol=protocol,
        topic="Data Analysis Planning",
        metadata={"project": "Example Project", "priority": "high"},
    )

    print(f"Created conversation: {conversation.conversation_id}")

    # Add messages to the conversation

    # Initial proposal
    proposal = create_propose(
        sender_id="agent-1",
        recipient_id="agent-2",
        proposal_type="analysis_plan",
        proposal={
            "steps": [
                "Data collection",
                "Preprocessing",
                "Feature extraction",
                "Model training",
            ],
            "timeline": "3 days",
        },
        reasoning="Based on project requirements and available data",
    )
    await conversation.add_message(proposal)

    # Confirmation of the proposal
    confirmation = create_confirm(
        sender_id="agent-2",
        recipient_id="agent-1",
        confirmation_type="plan_approval",
        confirmed_item_id=proposal.message_id,
        comments="Looks good, but let's add a validation step",
        in_reply_to=proposal.message_id,
    )
    await conversation.add_message(confirmation)

    # Request for specific action
    request = create_request(
        sender_id="agent-2",
        recipient_id="agent-1",
        action="prepare_dataset",
        parameters={"source": "customer_data", "target_size": "10GB"},
        in_reply_to=confirmation.message_id,
    )
    await conversation.add_message(request)

    # Get conversation summary
    summary = await conversation.get_summary()
    print("Conversation Summary:")
    for key, value in summary.items():
        if key != "metadata":
            print(f"  {key}: {value}")

    # Get context window
    context = conversation.get_context()
    print(f"\nContext Window ({len(context)} messages):")
    for message in context:
        print(f"  {message}")

    # Get thread structure for the proposal
    thread = await conversation.get_thread(proposal.message_id)
    print(f"\nThread for proposal {proposal.message_id}:")
    print(f"  Root: {len(thread['root'])} message")
    print(f"  Replies: {len(thread['replies'])} messages")


async def example_message_persistence(protocol: Protocol) -> None:
    """Example of message persistence and retrieval."""
    print("\n--- Example: Message Persistence and Retrieval ---")

    # Get a message by ID
    message_id = (
        "some-message-id"  # Replace with an actual message ID from previous examples
    )
    message = await protocol.get_message(message_id)

    if message:
        print(f"Retrieved message: {message}")

        # Count messages in the conversation
        count = await protocol.count_messages(conversation_id=message.conversation_id)
        print(f"Conversation has {count} messages")
    else:
        print(f"Message {message_id} not found")


async def run_examples() -> None:
    """Run all the communication protocol examples."""
    # Set up database client
    from os import environ

    # Get database URL from environment or use default
    db_url = environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory",
    )

    # Create database client
    db_client = get_postgres_client(database_url=db_url)

    # Create protocol
    protocol = Protocol(db_client=db_client, validate_recipients=False)

    try:
        # Run examples
        await example_simple_messaging(protocol)
        await example_conversation(protocol)

        # For this example, we'll use the first message from the conversation example
        # This requires that example_conversation be run first and succeed
        if hasattr(run_examples, "first_message_id"):
            await example_message_persistence(protocol)
    except Exception as e:
        print(f"Error running examples: {str(e)}")
    finally:
        # Close database client
        await db_client.close()


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run examples
    asyncio.run(run_examples())
