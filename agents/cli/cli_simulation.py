"""
Simulation scenarios for the CLI tool.

This module contains functions for running predefined simulation
scenarios to test agent interactions.
"""

import uuid

from .cli_core import AgentCLI, logger
from .cli_agent_ops import (
    create_agent,
    list_agents,
    get_agent,
    get_agent_messages,
)
from .cli_conversation_ops import (
    create_conversation,
    list_conversations,
    select_conversation,
    get_conversation_messages,
    get_conversation_summary,
)
from .cli_message_ops import (
    send_request,
    send_inform,
    send_propose,
    send_confirm,
    send_alert,
)


async def run_simulation(cli: AgentCLI, scenario: str) -> None:
    """
    Run a predefined simulation scenario.

    Args:
        cli: The AgentCLI instance
        scenario: Scenario to run ('basic', 'planning', 'problem-solving')
    """
    logger.info(f"Running {scenario} simulation...")

    # List registered agents before starting
    initial_agents = list_agents(cli)
    if initial_agents:
        logger.info(f"Initial agents: {', '.join(initial_agents)}")
    else:
        logger.info("No agents registered initially")

    if scenario == "basic":
        await run_basic_simulation(cli)
    elif scenario == "planning":
        await run_planning_simulation(cli)
    elif scenario == "problem-solving":
        await run_problem_solving_simulation(cli)
    else:
        logger.error(f"Unknown scenario: {scenario}")

    # List all agents after simulation
    final_agents = list_agents(cli)
    logger.info(f"Registered agents after simulation: {', '.join(final_agents)}")

    # List all conversations after simulation
    conversations = list_conversations(cli)
    logger.info(f"Conversations after simulation: {', '.join(conversations)}")


async def run_basic_simulation(cli: AgentCLI):
    """Run the basic simulation scenario."""
    # Create agents with valid UUIDs
    agent1_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Planner Agent")
    agent2_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Executor Agent")

    # Display agent details
    planner_agent = get_agent(cli, agent1_id)
    logger.info(f"Created Planner agent: {planner_agent}")

    executor_agent = get_agent(cli, agent2_id)
    logger.info(f"Created Executor agent: {executor_agent}")

    # Create conversation
    conversation_id = create_conversation(cli, topic="Basic Interaction")

    # List and select conversation to demonstrate these functions
    all_conversations = list_conversations(cli)
    logger.info(f"Available conversations: {all_conversations}")

    # Select the conversation we just created (should already be selected, but demonstrating the function)
    select_conversation(cli, conversation_id)
    logger.info(f"Selected conversation: {conversation_id}")

    # Send a request
    request = await send_request(
        cli,
        sender_id=agent1_id,
        recipient_id=agent2_id,
        action="process_data",
        parameters={"file": "data.csv", "filter": "status=active"},
        priority=4,
    )

    # Send a response (only if request was successful)
    if request:
        await send_inform(
            cli,
            sender_id=agent2_id,
            recipient_id=agent1_id,
            information_type="result",
            data={"processed": 100, "filtered": 75},
            in_reply_to=request.message_id,
        )
    else:
        # Send without in_reply_to if request failed
        await send_inform(
            cli,
            sender_id=agent2_id,
            recipient_id=agent1_id,
            information_type="result",
            data={"processed": 100, "filtered": 75},
        )

    # Send an alert
    await send_alert(
        cli,
        sender_id=agent2_id,
        recipient_id=agent1_id,
        alert_type="performance",
        severity=2,
        details="Processing took longer than expected",
        suggested_actions=["optimize filter", "reduce data set"],
    )

    # Show results
    messages = await get_conversation_messages(cli, conversation_id)
    logger.info(f"\nSimulation completed with {len(messages)} messages")

    # View messages for a specific agent
    planner_messages = await get_agent_messages(cli, agent1_id, limit=10)
    logger.info(f"\nMessages for Planner Agent ({len(planner_messages)}):")
    for msg in planner_messages:
        logger.info(f"  - {msg.message_type.value}: {msg.content.get('action', 'N/A')}")

    executor_messages = await get_agent_messages(cli, agent2_id, limit=10)
    logger.info(f"\nMessages for Executor Agent ({len(executor_messages)}):")
    for msg in executor_messages:
        logger.info(f"  - {msg.message_type.value}")

    # Show context window if available
    if cli.current_conversation:
        context = cli.current_conversation.get_context()
        logger.info(f"\nContext Window ({len(context)} messages):")
        for message in context:
            logger.info(f"  - {message}")
    else:
        logger.info("\nNo context window available")


async def run_planning_simulation(cli: AgentCLI):
    """Run the planning simulation scenario."""
    # Create agents with valid UUIDs
    planner_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Planner Agent")
    analyst_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Analyst Agent")
    executor_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Executor Agent")

    # Display details of the agents
    logger.info(f"Planner agent details: {get_agent(cli, planner_id)}")
    logger.info(f"Analyst agent details: {get_agent(cli, analyst_id)}")
    logger.info(f"Executor agent details: {get_agent(cli, executor_id)}")

    # Create conversation
    conversation_id = create_conversation(cli, topic="Project Planning")

    # List conversations to show the newly created one
    conversations = list_conversations(cli)
    logger.info(f"Available conversations: {conversations}")

    # Planner proposes a plan
    proposal = await send_propose(
        cli,
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
        confirmation = await send_confirm(
            cli,
            sender_id=analyst_id,
            recipient_id=planner_id,
            confirmation_type="plan_review",
            confirmed_item_id=proposal.message_id,
            comments="Plan looks good, but we need to add a validation step",
        )

        # Continue only if confirmation was sent successfully
        if confirmation:
            # Planner updates plan
            revised_proposal = await send_propose(
                cli,
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
                approval = await send_confirm(
                    cli,
                    sender_id=analyst_id,
                    recipient_id=planner_id,
                    confirmation_type="plan_approval",
                    confirmed_item_id=revised_proposal.message_id,
                    comments="Revised plan approved",
                )

                # Continue only if approval was sent successfully
                if approval:
                    # Planner assigns tasks to executor
                    await send_request(
                        cli,
                        sender_id=planner_id,
                        recipient_id=executor_id,
                        action="implement_plan",
                        parameters={"plan_id": revised_proposal.message_id},
                        priority=5,
                    )

    # Check messages for each agent
    for agent_id in [planner_id, analyst_id, executor_id]:
        agent_messages = await get_agent_messages(cli, agent_id)
        agent_name = get_agent(cli, agent_id).get("name", agent_id)
        logger.info(f"\nMessages for {agent_name} ({len(agent_messages)}):")
        for i, msg in enumerate(agent_messages):
            logger.info(
                f"  {i+1}. {msg.message_type.value} to/from {msg.recipient_id if msg.sender_id == agent_id else msg.sender_id}"
            )

    # Show results
    messages = await get_conversation_messages(cli, conversation_id)
    logger.info(f"\nSimulation completed with {len(messages)} messages")

    # Get conversation summary
    summary = await get_conversation_summary(cli, conversation_id)
    logger.info(f"\nConversation summary: {summary}")

    # Show thread structure if proposal exists and conversation exists
    if proposal and cli.current_conversation:
        try:
            thread = await cli.current_conversation.get_thread(proposal.message_id)
            logger.info(
                f"\nThread for initial proposal ({len(thread['replies'])} replies):"
            )
            for message in thread["replies"]:
                logger.info(f"  - {message}")
        except Exception as e:
            logger.error(f"\nCould not get thread: {str(e)}")
    else:
        logger.info("\nNo thread information available")


async def run_problem_solving_simulation(cli: AgentCLI):
    """Run the problem-solving simulation scenario."""
    # Create agents with valid UUIDs
    detector_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Problem Detector")
    analyzer_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Problem Analyzer")
    solver_id = create_agent(cli, agent_id=str(uuid.uuid4()), name="Problem Solver")

    # List all agents to verify creation
    all_agents = list_agents(cli)
    logger.info(f"All agents after creation: {all_agents}")

    # Get agent details
    detector_details = get_agent(cli, detector_id)
    logger.info(f"Detector agent details: {detector_details}")

    # Create conversation
    conversation_id = create_conversation(cli, topic="Problem Solving")

    # List and select conversation explicitly
    available_conversations = list_conversations(cli)
    logger.info(f"Available conversations: {available_conversations}")
    select_conversation(cli, conversation_id)
    logger.info(f"Selected conversation for problem solving: {conversation_id}")

    # Detector reports a problem
    alert = await send_alert(
        cli,
        sender_id=detector_id,
        recipient_id=analyzer_id,
        alert_type="system_error",
        severity=4,
        details="Database connection failures detected in production",
        suggested_actions=["check connection pool", "review recent changes"],
    )

    if alert:
        # Analyzer requests more information
        info_request = await send_request(
            cli,
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
            details = await send_inform(
                cli,
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
                diagnosis = await send_inform(
                    cli,
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
                    solution = await send_propose(
                        cli,
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
                        await send_confirm(
                            cli,
                            sender_id=analyzer_id,
                            recipient_id=solver_id,
                            confirmation_type="solution_approval",
                            confirmed_item_id=solution.message_id,
                            comments="Proceed with the recommended solution",
                        )

    # Check messages for each agent
    for agent_id in [detector_id, analyzer_id, solver_id]:
        agent_messages = await get_agent_messages(cli, agent_id)
        agent_name = get_agent(cli, agent_id).get("name", agent_id)
        logger.info(f"\nMessages for {agent_name} ({len(agent_messages)}):")
        for i, msg in enumerate(agent_messages):
            if i < 3:  # Show first 3 messages to avoid too much output
                logger.info(
                    f"  {i+1}. {msg.message_type.value} with {msg.recipient_id if msg.sender_id == agent_id else msg.sender_id}"
                )

    # Show results
    messages = await get_conversation_messages(cli, conversation_id)
    logger.info(f"\nSimulation completed with {len(messages)} messages")

    # Show conversation summary
    try:
        summary = await get_conversation_summary(cli, conversation_id)
        logger.info("\nConversation Summary:")
        for key, value in summary.items():
            if key not in ["metadata", "created_at", "last_activity", "duration"]:
                logger.info(f"  {key}: {value}")
    except Exception as e:
        logger.error(f"\nCould not get conversation summary: {str(e)}")
