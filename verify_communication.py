#!/usr/bin/env python
"""
Verification test for agent-to-agent communication protocol.
"""

import asyncio
import uuid
import time
from datetime import datetime

from agents.communication import (
    Message,
    MessageType,
    Protocol,
    Conversation,
    create_request,
    create_inform,
    create_propose,
    create_confirm,
    create_alert,
)
from agents.db import get_postgres_client


async def test_communication_protocol():
    """Test agent-to-agent communication protocol."""
    print("\n----- Testing Agent-to-Agent Communication Protocol -----")

    test_start_time = datetime.utcnow()

    # Create test agent IDs
    sender_id = str(uuid.uuid4())
    recipient_id = str(uuid.uuid4())

    try:
        # Initialize database client
        print("Initializing database client...")
        database_url = (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory"
        )
        db_client = get_postgres_client(database_url=database_url)

        # Initialize protocol
        protocol = Protocol(db_client=db_client, validate_recipients=False)

        # Register test agents
        print("Registering test agents...")
        protocol.register_agent(
            sender_id, agent_type="sender", agent_name="Test Sender Agent"
        )
        protocol.register_agent(
            recipient_id, agent_type="receiver", agent_name="Test Receiver Agent"
        )

        # Wait a bit for async operations to complete
        await asyncio.sleep(1)
        print(f"Registered sender agent: {sender_id}")
        print(f"Registered recipient agent: {recipient_id}")

        # Create a test conversation
        conversation = Conversation(
            protocol=protocol, topic="Test Conversation", metadata={"test": True}
        )
        conversation_id = conversation.conversation_id
        print(f"Created test conversation: {conversation_id}")

        # 1. Test REQUEST message
        print("\nTesting REQUEST message...")
        request_start = time.time()
        request_message = create_request(
            sender_id=sender_id,
            recipient_id=recipient_id,
            action="test_action",
            parameters={"param1": "value1", "param2": 123},
            priority=3,
            conversation_id=conversation_id,
        )

        request_sent = await conversation.add_message(request_message)
        request_duration = time.time() - request_start

        if request_sent:
            print(f"✅ REQUEST message sent successfully ({request_duration:.2f}s)")
            print(f"Message ID: {request_message.message_id}")
        else:
            print(f"❌ Failed to send REQUEST message")
            return False

        # 2. Test INFORM message
        print("\nTesting INFORM message (as reply)...")
        inform_start = time.time()
        inform_message = create_inform(
            sender_id=recipient_id,
            recipient_id=sender_id,
            information_type="test_result",
            data={"result": "success", "details": "Test completed"},
            in_reply_to=request_message.message_id,
            conversation_id=conversation_id,
        )

        inform_sent = await conversation.add_message(inform_message)
        inform_duration = time.time() - inform_start

        if inform_sent:
            print(f"✅ INFORM message sent successfully ({inform_duration:.2f}s)")
            print(f"Message ID: {inform_message.message_id}")
        else:
            print(f"❌ Failed to send INFORM message")
            return False

        # 3. Test PROPOSE message
        print("\nTesting PROPOSE message...")
        propose_start = time.time()
        propose_message = create_propose(
            sender_id=sender_id,
            recipient_id=recipient_id,
            proposal_type="test_proposal",
            proposal={"action": "do_something", "when": "now"},
            alternatives=[{"action": "do_alternative", "when": "later"}],
            reasoning="This is the best approach because of X and Y",
            conversation_id=conversation_id,
        )

        propose_sent = await conversation.add_message(propose_message)
        propose_duration = time.time() - propose_start

        if propose_sent:
            print(f"✅ PROPOSE message sent successfully ({propose_duration:.2f}s)")
            print(f"Message ID: {propose_message.message_id}")
        else:
            print(f"❌ Failed to send PROPOSE message")
            return False

        # 4. Test CONFIRM message
        print("\nTesting CONFIRM message (as reply to proposal)...")
        confirm_start = time.time()
        confirm_message = create_confirm(
            sender_id=recipient_id,
            recipient_id=sender_id,
            confirmation_type="proposal_acceptance",
            confirmed_item_id=propose_message.message_id,
            comments="I agree with the proposal",
            conversation_id=conversation_id,
        )

        confirm_sent = await conversation.add_message(confirm_message)
        confirm_duration = time.time() - confirm_start

        if confirm_sent:
            print(f"✅ CONFIRM message sent successfully ({confirm_duration:.2f}s)")
            print(f"Message ID: {confirm_message.message_id}")
        else:
            print(f"❌ Failed to send CONFIRM message")
            return False

        # 5. Test ALERT message
        print("\nTesting ALERT message...")
        alert_start = time.time()
        alert_message = create_alert(
            sender_id=recipient_id,
            recipient_id=sender_id,
            alert_type="test_alert",
            severity=2,
            details="Something unexpected happened",
            suggested_actions=["review", "retry"],
            conversation_id=conversation_id,
        )

        alert_sent = await conversation.add_message(alert_message)
        alert_duration = time.time() - alert_start

        if alert_sent:
            print(f"✅ ALERT message sent successfully ({alert_duration:.2f}s)")
            print(f"Message ID: {alert_message.message_id}")
        else:
            print(f"❌ Failed to send ALERT message")
            return False

        # 6. Test conversation message retrieval
        print("\nTesting conversation message retrieval...")
        retrieval_start = time.time()
        messages = await protocol.get_conversation_messages(conversation_id)
        retrieval_duration = time.time() - retrieval_start

        if messages and len(messages) == 5:
            print(
                f"✅ Retrieved {len(messages)} messages from conversation ({retrieval_duration:.2f}s)"
            )
        else:
            print(
                f"❌ Failed to retrieve expected message count. Got {len(messages) if messages else 0}, expected 5"
            )
            return False

        # 7. Test threading functionality
        print("\nTesting message threading...")
        thread_start = time.time()
        thread = await conversation.get_thread(request_message.message_id)
        thread_duration = time.time() - thread_start

        if (
            thread
            and thread["message"].message_id == request_message.message_id
            and len(thread["replies"]) == 1
        ):
            print(f"✅ Message threading successful ({thread_duration:.2f}s)")
            print(
                f"Found {len(thread['replies'])} direct replies to the REQUEST message"
            )
        else:
            print(f"❌ Message threading failed or didn't return expected results")
            return False

        # 8. Test conversation context
        print("\nTesting conversation context...")
        context = conversation.get_context()

        if context and len(context) > 0:
            print(f"✅ Conversation context retrieved successfully")
            print(f"Context contains {len(context)} messages")
        else:
            print(f"❌ Failed to retrieve conversation context")
            return False

        # 9. Clean up test data
        print("\nCleaning up test data...")
        # No need to clean up test data for this verification test since we're testing database operations
        # If we really want to clean up, we should use a proper transaction in the test itself
        print("Skipping cleanup to avoid UUID conversion issues.")

        # All tests passed!
        test_end_time = datetime.utcnow()
        duration = (test_end_time - test_start_time).total_seconds()
        print(
            f"\n✅ All communication protocol tests passed successfully in {duration:.2f} seconds!"
        )

        # Close the database client
        await db_client.close()
        return True

    except Exception as e:
        print(f"❌ Error during communication protocol testing: {str(e)}")
        return False


if __name__ == "__main__":
    asyncio.run(test_communication_protocol())
