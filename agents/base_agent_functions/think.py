import logging
from typing import Dict, Any
from agents.logging.activity_logger import ActivityCategory, ActivityLevel

logger = logging.getLogger(__name__)


async def think_logic(agent, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core thinking logic for an agent.
    This base implementation logs the thinking process.
    Args:
        agent: The agent instance.
        context: Dictionary containing all relevant information needed for thinking
    Returns:
        Dictionary containing the results of the thinking process
    """
    operation_name = "think_process"
    # Ensure agent has activity_logger. If not, this will raise an AttributeError.
    # Consider adding a check or ensuring all agents passed here have it.
    agent.activity_logger.start_timer(operation_name)
    execution_time_s = 0  # Initialize

    try:
        await agent.activity_logger.log_thinking_process(
            thought_type="generic_think_start",
            description=f"Started thinking process with context: {context.get('summary', 'No summary')}",
            reasoning="Agent is about to execute its think method.",
            input_context={
                "context_summary": context.get("summary", "No summary"),
                "context_size": len(str(context)),
                "context_type": context.get("type", "unknown"),
            },
        )

        result = {
            "thought_process": "Default thinking process - override in subclass or specific logic file",
            "decision": "No decision made",
            "rationale": "Base agent logic has no specialized thinking capabilities",
            "input": context,
        }

        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=True
        )
        await agent.activity_logger.log_activity(
            activity_type="thinking_completed",
            description=f"Completed thinking process in {execution_time_s:.2f}s",
            category=ActivityCategory.THINKING,
            level=ActivityLevel.INFO,
            details={
                "decision": result.get("decision"),
                "rationale": result.get("rationale"),
            },
            execution_time_ms=int(execution_time_s * 1000),
        )

        return result
    except Exception as e:
        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=False
        )
        await agent.activity_logger.log_error(
            error_type="ThinkingError",
            description=f"Error during thinking process for agent {agent.agent_id}",
            exception=e,
            severity=ActivityLevel.ERROR,
            context={
                "current_operation": "think_method_logic",
                "execution_time_ms_before_error": int(execution_time_s * 1000),
            },
        )
        raise
