"""
Logic for the think method of the ProductManagerAgent.
"""

from typing import Dict, Any, List

from agents.logging.activity_logger import ActivityCategory, ActivityLevel
from agents.memory.vector_memory import MemoryItem  # For type hinting


async def product_manager_think_logic(
    agent: Any, context: Dict[str, Any]  # ProductManagerAgent instance
) -> Dict[str, Any]:
    """
    Core thinking method for the Product Manager agent.

    Args:
        agent: The ProductManagerAgent instance.
        context: Dictionary containing all relevant information needed for thinking.

    Returns:
        Dictionary containing the results of the thinking process.
    """
    operation_name = "product_manager_think_process"
    agent.activity_logger.start_timer(operation_name)
    execution_time_s = 0  # Initialize
    thought_type = "general_product_management"  # Default thought_type
    input_context_summary = {}  # Default input_context_summary

    try:
        thought_type = context.get("thought_type", "general_product_management")
        input_context_summary = {
            "context_summary": context.get("summary", "No summary provided"),
            "context_size": len(str(context)),
            "context_type": context.get("type", "unknown"),
            "thought_type_requested": thought_type,
        }

        await agent.activity_logger.log_thinking_process(
            thought_type=f"pm_{thought_type}_start",
            description=f"Started product management thinking: {thought_type}",
            reasoning="Agent is about to apply product management logic based on context.",
            input_context=input_context_summary,
        )

        relevant_info: List[str] = []  # Initialize with correct type
        if agent.vector_memory and context.get("query"):
            query_text = context["query"]
            # Use the retrieve_memories method from BaseAgent (which calls retrieve_memories_logic)
            # This assumes BaseAgent.retrieve_memories is available on the agent instance.
            memory_items: List[MemoryItem] = await agent.retrieve_memories(
                query_text=query_text, limit=5
            )
            relevant_info = [item.content for item in memory_items]
            input_context_summary["retrieved_memory_count"] = len(relevant_info)

        result_details = {}

        if thought_type == "requirement_analysis":
            result_details = {
                "focused_on": "Identifying functional, non-functional, technical, and business requirements",
                "consideration": "User needs, technical feasibility, and business goals",
                "output_format": "Structured requirements with categorization and priorities",
            }
        elif thought_type == "user_story_creation":
            result_details = {
                "focused_on": "User-centric problem statements and value delivery",
                "consideration": "User personas, goals, and expected benefits",
                "output_format": "User stories with clear format and acceptance criteria",
            }
        elif thought_type == "feature_prioritization":
            result_details = {
                "focused_on": "Business value, technical feasibility, user impact, risk, time to market",
                "consideration": "Strategic alignment, dependencies, resource constraints",
                "output_format": "Ranked features with scores and rationale",
            }
        elif thought_type == "vision_articulation":
            result_details = {
                "focused_on": "Aspirational yet achievable project vision",
                "consideration": "Target audience, key objectives, success metrics, constraints",
                "output_format": "Vision statement with supporting components",
            }
        else:  # general_product_management
            result_details = {
                "focused_on": "Identifying product needs and opportunities",
                "consideration": "Market demand, user feedback, technical capabilities",
                "output_format": "Structured analysis and recommendations",
            }

        result = {
            "thought_process": f"Product Management: {thought_type}",
            "decision": context.get(
                "decision_required", "Plan generated for product management task"
            ),
            "rationale": "Based on product management expertise and provided context.",
            "details": result_details,
            "relevant_context_from_memory": relevant_info,
            "input_context_summary": input_context_summary,
        }

        execution_time_s = await agent.activity_logger.stop_timer(
            operation_name, success=True
        )
        await agent.activity_logger.log_activity(
            activity_type=f"pm_thinking_{thought_type}_completed",
            description=f"Completed product management thinking: {thought_type} in {execution_time_s:.2f}s",
            category=ActivityCategory.THINKING,
            level=ActivityLevel.INFO,
            details={
                "decision": result.get("decision"),
                "rationale": result.get("rationale"),
                "thought_type": thought_type,
                "output_summary": result_details.get(
                    "output_format", "Generic PM output"
                ),
            },
            execution_time_ms=int(execution_time_s * 1000),
        )
        return result

    except Exception as e:
        # Ensure execution_time_s is set if an error occurs early
        if execution_time_s == 0 and agent.activity_logger._timers.get(operation_name):
            # if timer was started but not stopped, stop it now
            execution_time_s = await agent.activity_logger.stop_timer(
                operation_name, success=False
            )
        elif execution_time_s == 0:  # if timer was never started or already stopped
            execution_time_s = 0  # Or some other appropriate handling

        await agent.activity_logger.log_error(
            error_type="ProductManagerThinkingError",
            description=f"Error during product management thinking ({thought_type}): {str(e)}",
            exception=e,
            severity=ActivityLevel.ERROR,
            context={
                "current_operation": operation_name,
                "thought_type": thought_type,
                "input_context_summary": input_context_summary,  # Ensure this is defined
                "execution_time_ms_before_error": int(execution_time_s * 1000),
            },
        )
        raise
