#!/usr/bin/env python
"""
Verification test for CLI tool.
"""

import asyncio
import uuid
import time
import subprocess
import sys
from datetime import datetime


async def test_cli_tool():
    """Test the CLI tool for agent interactions."""
    print("\n----- Testing CLI Tool for Agent Testing -----")

    test_start_time = datetime.utcnow()

    try:
        # Make sure we can run the CLI directly
        print("Testing CLI import and module execution...")
        import agents.cli.agent_cli as agent_cli

        if hasattr(agent_cli, "main") and callable(agent_cli.main):
            print(f"✅ CLI module imports successfully and has a main function")
        else:
            print(f"❌ CLI module does not have expected structure")
            return False

        # Test CLI execution through shell script
        print("\nTesting CLI shell script execution...")
        result = subprocess.run(
            ["./agents/cli/agent_cli.sh", "--help"], capture_output=True, text=True
        )

        if result.returncode == 0 and "usage:" in result.stdout.lower():
            print(f"✅ CLI shell script executes successfully")
            print(f"Output: {result.stdout.splitlines()[0]}")
        else:
            print(f"❌ CLI shell script failed to execute properly")
            print(f"Error: {result.stderr}")
            return False

        # Test agent creation
        print("\nTesting agent creation...")
        agent_name = f"Test Agent {uuid.uuid4().hex[:8]}"
        result = subprocess.run(
            ["./agents/cli/agent_cli.sh", "agent", "create", "--name", agent_name],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and "Created agent" in result.stdout:
            print(f"✅ Agent creation successful")
            agent_id = result.stdout.strip().split()[-1]
            print(f"Created agent with ID: {agent_id}")
        else:
            print(f"❌ Agent creation failed")
            print(f"Error: {result.stderr}")
            return False

        # Test agent listing
        print("\nTesting agent listing...")
        result = subprocess.run(
            ["./agents/cli/agent_cli.sh", "agent", "list"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and "Agents:" in result.stdout:
            print(f"✅ Agent listing successful")
            print(f"Found agents: {len(result.stdout.splitlines()) - 1}")
        else:
            print(f"❌ Agent listing failed")
            print(f"Error: {result.stderr}")
            return False

        # Test conversation creation
        print("\nTesting conversation creation...")
        conversation_topic = f"Test Conversation {uuid.uuid4().hex[:8]}"
        result = subprocess.run(
            [
                "./agents/cli/agent_cli.sh",
                "conversation",
                "create",
                "--topic",
                conversation_topic,
            ],
            capture_output=True,
            text=True,
        )

        if (
            result.returncode == 0
            and "Created and selected conversation" in result.stdout
        ):
            print(f"✅ Conversation creation successful")
            conversation_id = result.stdout.strip().split()[-1]
            print(f"Created conversation with ID: {conversation_id}")
        else:
            print(f"❌ Conversation creation failed")
            print(f"Error: {result.stderr}")
            return False

        # Test conversation listing
        print("\nTesting conversation listing...")
        result = subprocess.run(
            ["./agents/cli/agent_cli.sh", "conversation", "list"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and "Conversations:" in result.stdout:
            print(f"✅ Conversation listing successful")
            print(f"Found conversations: {len(result.stdout.splitlines()) - 1}")
        else:
            print(f"❌ Conversation listing failed")
            print(f"Error: {result.stderr}")
            return False

        # Test message sending (REQUEST type)
        print("\nTesting message sending (REQUEST)...")
        result = subprocess.run(
            [
                "./agents/cli/agent_cli.sh",
                "message",
                "request",
                "--sender",
                agent_id,
                "--recipient",
                agent_id,  # Send to self for simplicity
                "--action",
                "test_action",
                "--parameters",
                '{"test": true, "value": 123}',
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and "Request sent" in result.stdout:
            print(f"✅ Message sending (REQUEST) successful")
            message_id = result.stdout.strip().split()[-1]
            print(f"Sent message with ID: {message_id}")
        else:
            print(f"❌ Message sending (REQUEST) failed")
            print(f"Error: {result.stderr}")
            return False

        # Test message listing
        print("\nTesting message listing...")
        result = subprocess.run(
            ["./agents/cli/agent_cli.sh", "message", "list"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and (
            ("Messages" in result.stdout and agent_id in result.stdout)
            or "No messages" in result.stdout
        ):
            print(f"✅ Message listing successful")
        else:
            print(f"❌ Message listing failed")
            print(f"Error: {result.stderr}")
            return False

        # Test simulation run
        print("\nTesting simulation run...")
        result = subprocess.run(
            ["./agents/cli/agent_cli.sh", "simulation", "run", "basic"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and "Simulation completed" in result.stdout:
            print(f"✅ Simulation run successful")
            message_count = [
                line
                for line in result.stdout.splitlines()
                if "Simulation completed with" in line
            ]
            if message_count:
                print(message_count[0])
        else:
            print(f"❌ Simulation run failed")
            print(f"Error: {result.stderr}")
            return False

        # All tests passed!
        test_end_time = datetime.utcnow()
        duration = (test_end_time - test_start_time).total_seconds()
        print(f"\n✅ All CLI tool tests passed successfully in {duration:.2f} seconds!")
        return True

    except Exception as e:
        print(f"❌ Error during CLI tool testing: {str(e)}")
        return False


if __name__ == "__main__":
    asyncio.run(test_cli_tool())
