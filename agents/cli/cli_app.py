"""
Command-line interface main entry point.

This module provides the main entry point for the CLI application,
including command parsing and handling.
"""

import argparse
import asyncio
import json
import sys

from .cli_core import AgentCLI, logger
from .cli_agent_ops import (
    create_agent,
    list_agents,
    get_agent,
    get_agent_messages,
    update_agent,
    delete_agent,
)
from .cli_conversation_ops import (
    create_conversation,
    list_conversations,
    select_conversation,
    get_conversation_summary,
    get_conversation_messages,
    update_conversation,
    delete_conversation,
)
from .cli_message_ops import (
    send_message,
    send_request,
    send_inform,
    send_propose,
    send_confirm,
    send_alert,
)
from .cli_simulation import run_simulation
from .cli_component_ops import (
    test_db_client,
    test_db_transaction,
    test_llm_completion,
    test_llm_embedding,
    test_vector_memory,
    test_logging,
    run_component_verification,
    db_pool_status,
    db_tables,
)
from agents.communication import MessageType


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Agent CLI for testing agent communication"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Agent commands
    agent_parser = subparsers.add_parser("agent", help="Agent management commands")
    agent_subparsers = agent_parser.add_subparsers(
        dest="subcommand", help="Agent subcommand"
    )

    # Agent create
    agent_create_parser = agent_subparsers.add_parser("create", help="Create an agent")
    agent_create_parser.add_argument("name", help="Agent name")
    agent_create_parser.add_argument("type", help="Agent type")
    agent_create_parser.add_argument(
        "--id", help="Optional agent ID (auto-generated if not provided)"
    )
    agent_create_parser.add_argument(
        "--config", help="Agent configuration as JSON string"
    )

    # Agent list
    agent_list_parser = agent_subparsers.add_parser("list", help="List agents")
    agent_list_parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive (deleted) agents",
    )

    # Agent show
    agent_show_parser = agent_subparsers.add_parser("show", help="Show agent details")
    agent_show_parser.add_argument("id", help="Agent ID")

    # Agent update
    agent_update_parser = agent_subparsers.add_parser("update", help="Update an agent")
    agent_update_parser.add_argument("id", help="Agent ID")
    agent_update_parser.add_argument("--name", help="New agent name")
    agent_update_parser.add_argument("--type", help="New agent type")
    agent_update_parser.add_argument("--config", help="New agent configuration as JSON")

    # Agent delete
    agent_delete_parser = agent_subparsers.add_parser("delete", help="Delete an agent")
    agent_delete_parser.add_argument("id", help="Agent ID")

    # Conversation commands
    conversation_parser = subparsers.add_parser(
        "conversation", help="Conversation management commands"
    )
    conversation_subparsers = conversation_parser.add_subparsers(
        dest="subcommand", help="Conversation subcommand"
    )

    # Conversation create
    conversation_create_parser = conversation_subparsers.add_parser(
        "create", help="Create a conversation"
    )
    conversation_create_parser.add_argument(
        "--id", help="Optional conversation ID (auto-generated if not provided)"
    )
    conversation_create_parser.add_argument("--topic", help="Conversation topic")
    conversation_create_parser.add_argument(
        "--metadata", help="Conversation metadata as JSON string"
    )

    # Conversation list
    conversation_list_parser = conversation_subparsers.add_parser(
        "list", help="List conversations"
    )
    conversation_list_parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Include inactive (deleted) conversations",
    )

    # Conversation select
    conversation_select_parser = conversation_subparsers.add_parser(
        "select", help="Select a conversation"
    )
    conversation_select_parser.add_argument("id", help="Conversation ID")

    # Conversation show
    conversation_show_parser = conversation_subparsers.add_parser(
        "show", help="Show conversation details"
    )
    conversation_show_parser.add_argument("--id", help="Conversation ID")
    conversation_show_parser.add_argument(
        "--messages", action="store_true", help="Show messages in the conversation"
    )
    conversation_show_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum number of messages to show"
    )

    # Conversation update
    conversation_update_parser = conversation_subparsers.add_parser(
        "update", help="Update a conversation"
    )
    conversation_update_parser.add_argument("id", help="Conversation ID")
    conversation_update_parser.add_argument("--topic", help="New conversation topic")
    conversation_update_parser.add_argument("--status", help="New conversation status")
    conversation_update_parser.add_argument(
        "--metadata", help="New or updated metadata as JSON"
    )

    # Conversation delete
    conversation_delete_parser = conversation_subparsers.add_parser(
        "delete", help="Delete a conversation"
    )
    conversation_delete_parser.add_argument("id", help="Conversation ID")

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

    # New: Component testing commands
    component_parser = subparsers.add_parser(
        "component", help="Component testing commands"
    )
    component_subparsers = component_parser.add_subparsers(
        dest="subcommand", help="Component testing subcommand"
    )

    # Database client testing
    db_parser = component_subparsers.add_parser("db", help="Database client testing")
    db_subparsers = db_parser.add_subparsers(dest="db_command", help="Database command")

    # Simple query
    query_parser = db_subparsers.add_parser("query", help="Execute a database query")
    query_parser.add_argument("--sql", required=True, help="SQL query to execute")

    # Transaction test
    db_subparsers.add_parser("transaction", help="Test database transaction")

    # LLM provider testing
    llm_parser = component_subparsers.add_parser("llm", help="LLM provider testing")
    llm_subparsers = llm_parser.add_subparsers(dest="llm_command", help="LLM command")

    # Text completion
    completion_parser = llm_subparsers.add_parser(
        "completion", help="Generate text completion"
    )
    completion_parser.add_argument("--prompt", required=True, help="Text prompt")
    completion_parser.add_argument("--model", default="gemini-pro", help="Model name")
    completion_parser.add_argument(
        "--max-tokens", type=int, default=100, help="Maximum tokens"
    )

    # Embedding generation
    embedding_parser = llm_subparsers.add_parser(
        "embedding", help="Generate text embedding"
    )
    embedding_parser.add_argument("--text", required=True, help="Text to embed")
    embedding_parser.add_argument(
        "--model", default="gemini-embedding", help="Model name"
    )

    # Vector memory testing
    memory_parser = component_subparsers.add_parser(
        "memory", help="Vector memory testing"
    )
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command", help="Memory command"
    )

    # Store text
    store_parser = memory_subparsers.add_parser(
        "store", help="Store text in vector memory"
    )
    store_parser.add_argument("--text", required=True, help="Text to store")

    # Search memory
    search_parser = memory_subparsers.add_parser("search", help="Search vector memory")
    search_parser.add_argument("--text", required=True, help="Text to store")
    search_parser.add_argument("--query", required=True, help="Search query")

    # Logging testing
    log_parser = component_subparsers.add_parser("log", help="Logging system testing")
    log_parser.add_argument("--agent", required=True, help="Agent ID to log for")

    # Component verification
    verify_parser = component_subparsers.add_parser(
        "verify", help="Run component verification"
    )
    verify_parser.add_argument(
        "component_name",
        choices=[
            "base-agent",
            "db-client",
            "llm-provider",
            "vector-memory",
            "communication",
            "logging",
            "cli-tool",
        ],
        help="Component to verify",
    )

    # New: Database management commands
    db_parser = subparsers.add_parser("db", help="Database management commands")
    db_subparsers = db_parser.add_subparsers(
        dest="subcommand", help="Database subcommand"
    )

    # Pool status
    db_subparsers.add_parser("pool-status", help="Show database connection pool status")

    # Tables command
    db_subparsers.add_parser("tables", help="List all tables with record counts")

    return parser.parse_args()


async def handle_command(args: argparse.Namespace) -> None:
    """Handle the command specified by the parsed arguments."""
    cli = AgentCLI()

    try:
        if args.command == "agent":
            if args.subcommand == "create":
                agent_id = await create_agent(
                    cli,
                    args.id,
                    agent_name=args.name or "Test Agent",
                    agent_type=args.type or "test",
                    agent_role=args.type or "test",  # Default role to type
                )
                print(f"Created agent: {agent_id}")

            elif args.subcommand == "list":
                agents = await list_agents(
                    cli, status="all" if args.include_inactive else "active"
                )
                if agents:
                    print("Agents:")
                    for agent in agents:
                        print(f"  - {agent['id']}: {agent['name']} ({agent['type']})")
                else:
                    print("No agents")

            elif args.subcommand == "show":
                agent = await get_agent(cli, args.id)
                if agent:
                    print(f"Agent: {args.id}")
                    for key, value in agent.items():
                        if key not in ["capabilities", "extra_data"]:
                            print(f"  {key}: {value}")
                        else:
                            print(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    print(f"Agent not found: {args.id}")

            elif args.subcommand == "update":
                kwargs = {}
                if args.name:
                    kwargs["agent_name"] = args.name
                if args.type:
                    kwargs["agent_type"] = args.type
                if args.config:
                    kwargs["config"] = json.loads(args.config)

                success = await update_agent(cli, args.id, **kwargs)
                if success:
                    print(f"Updated agent: {args.id}")
                else:
                    print(f"Failed to update agent: {args.id}")

            elif args.subcommand == "delete":
                success = await delete_agent(cli, args.id)
                if success:
                    print(f"Deleted agent: {args.id}")
                else:
                    print(f"Failed to delete agent: {args.id}")

        elif args.command == "conversation":
            if args.subcommand == "create":
                metadata = None
                if args.metadata:
                    try:
                        metadata = json.loads(args.metadata)
                    except json.JSONDecodeError:
                        print("Error: Metadata must be valid JSON")
                        return

                conversation_id = await create_conversation(
                    cli, args.id, args.topic, metadata
                )
                print(f"Created and selected conversation: {conversation_id}")

            elif args.subcommand == "list":
                conversations = await list_conversations(cli, args.include_inactive)
                if conversations:
                    print(f"Found {len(conversations)} conversations:")
                    for conv in conversations:
                        conv_id = conv["conversation_id"]
                        topic = conv.get("topic", "No topic")
                        created = conv.get("created_at", "Unknown")
                        status = conv.get("status", "Unknown")

                        if conv_id == cli.current_conversation_id:
                            print(f"  - {conv_id} (current)")
                        else:
                            print(f"  - {conv_id}")
                        print(f"    Topic: {topic}")
                        print(f"    Created: {created}")
                        print(f"    Status: {status}")
                        print("")
                else:
                    print("No conversations found")

            elif args.subcommand == "select":
                if await select_conversation(cli, args.id):
                    print(f"Selected conversation: {args.id}")
                else:
                    print(f"Conversation not found: {args.id}")

            elif args.subcommand == "show":
                conversation_id = args.id or cli.current_conversation_id
                if not conversation_id:
                    print("No conversation selected")
                    return

                summary = await get_conversation_summary(cli, conversation_id)
                if summary:
                    print(f"Conversation: {summary['conversation_id']}")
                    for key, value in summary.items():
                        if key != "extra_data":
                            print(f"  {key}: {value}")

                    if summary.get("extra_data"):
                        print("\nExtra Data:")
                        for key, value in summary["extra_data"].items():
                            print(f"  {key}: {value}")

                if args.messages:
                    messages = await get_conversation_messages(
                        cli, conversation_id, args.limit
                    )
                    if messages:
                        print("\nMessages:")
                        for msg in messages:
                            print(
                                f"  [{msg['timestamp']}] {msg['sender']} -> {msg['recipient']}: {msg['type']}"
                            )
                            content = msg.get("content") or {}
                            if isinstance(content, dict):
                                for key, value in content.items():
                                    print(f"    {key}: {value}")
                            else:
                                print(f"    {content}")
                    else:
                        print("No messages")

            elif args.subcommand == "update":
                metadata = None
                if args.metadata:
                    try:
                        metadata = json.loads(args.metadata)
                    except json.JSONDecodeError:
                        print("Error: Metadata must be valid JSON")
                        return

                if await update_conversation(
                    cli, args.id, args.topic, args.status, metadata
                ):
                    print(f"Updated conversation: {args.id}")
                else:
                    print(f"Failed to update conversation: {args.id}")

            elif args.subcommand == "delete":
                if await delete_conversation(cli, args.id):
                    print(f"Deleted conversation: {args.id}")
                else:
                    print(f"Failed to delete conversation: {args.id}")

        elif args.command == "message":
            if args.subcommand == "send":
                try:
                    content = json.loads(args.content)
                except json.JSONDecodeError:
                    content = args.content

                msg_id = await send_message(
                    cli,
                    args.type,
                    args.sender,
                    args.recipient,
                    content,
                    args.reply_to,
                )
                print(f"Sent message: {msg_id}")

            elif args.subcommand == "request":
                try:
                    parameters = json.loads(args.parameters) if args.parameters else {}
                except json.JSONDecodeError:
                    print("Error: Parameters must be valid JSON")
                    return

                msg_id = await send_request(
                    cli,
                    args.sender,
                    args.recipient,
                    args.action,
                    parameters,
                    args.priority,
                    args.reply_to,
                )
                print(f"Sent request message: {msg_id}")

            elif args.subcommand == "inform":
                try:
                    data = json.loads(args.data)
                except json.JSONDecodeError:
                    print("Error: Data must be valid JSON")
                    return

                msg_id = await send_inform(
                    cli,
                    args.sender,
                    args.recipient,
                    args.type,
                    data,
                    args.reply_to,
                )
                print(f"Sent inform message: {msg_id}")

            elif args.subcommand == "list":
                messages = await get_agent_messages(cli, args.agent, limit=args.limit)
                if messages:
                    print("Messages:")
                    for msg in messages:
                        print(
                            f"  [{msg['timestamp']}] {msg['sender']} -> {msg['recipient']}: {msg['type']}"
                        )
                else:
                    print("No messages")

        elif args.command == "simulation":
            if args.subcommand == "run":
                await run_simulation(cli, args.scenario)

        # New: Component testing commands
        elif args.command == "component":
            if args.subcommand == "db":
                if args.db_command == "query":
                    result = await test_db_client(cli, args.sql)
                    print(json.dumps(result, indent=2))
                elif args.db_command == "transaction":
                    result = await test_db_transaction(cli)
                    print(json.dumps(result, indent=2))

            elif args.subcommand == "llm":
                if args.llm_command == "completion":
                    result = await test_llm_completion(
                        cli, args.prompt, args.model, args.max_tokens
                    )
                    print(json.dumps(result, indent=2))
                elif args.llm_command == "embedding":
                    result = await test_llm_embedding(cli, args.text, args.model)
                    print(json.dumps(result, indent=2))

            elif args.subcommand == "memory":
                if args.memory_command == "store":
                    result = await test_vector_memory(cli, args.text)
                    print(json.dumps(result, indent=2))
                elif args.memory_command == "search":
                    result = await test_vector_memory(cli, args.text, args.query)
                    print(json.dumps(result, indent=2))

            elif args.subcommand == "log":
                result = await test_logging(cli, args.agent)
                print(json.dumps(result, indent=2))

            elif args.subcommand == "verify":
                result = await run_component_verification(cli, args.component_name)
                print(f"Verification of {args.component_name}:")
                if result.get("success"):
                    print("✅ PASSED")
                else:
                    print("❌ FAILED")
                print("\nOutput:")
                print(result.get("stdout", ""))
                if result.get("stderr"):
                    print("\nErrors:")
                    print(result.get("stderr"))

        # New: Database management commands
        elif args.command == "db":
            if args.subcommand == "pool-status":
                result = await db_pool_status(cli)
                print(json.dumps(result, indent=2))
            elif args.subcommand == "tables":
                result = await db_tables(cli)
                print(json.dumps(result, indent=2))

        else:
            print("Unknown command. Use --help for usage information.")

    finally:
        await cli.close()


def main():
    """Main entry point for the CLI."""
    args = parse_args()
    if not args.command:
        print("No command specified. Use --help for usage information.")
        sys.exit(1)

    try:
        asyncio.run(handle_command(args))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
