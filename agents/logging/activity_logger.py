"""
Comprehensive Logging System for tracking agent activities.

Features:
- Activity categorization
- Thought process capture
- Decision recording
- Input/output tracking
- Performance metrics
"""

import uuid
import json
import time
import enum
import logging
import traceback
from typing import Dict, List, Any, Optional, Union, Set
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update, delete, desc
from sqlalchemy.sql import text

from infra.db.models import AgentActivity, Agent

# Configure standard Python logging
logger = logging.getLogger(__name__)


class ActivityCategory(enum.Enum):
    """Categories of agent activities for classification."""

    THINKING = "thinking"  # Internal reasoning processes
    COMMUNICATION = "communication"  # Agent-to-agent interactions
    CODE = "code"  # Code generation, review, etc.
    DATABASE = "database"  # Database operations
    FILE_SYSTEM = "file_system"  # File system operations
    API = "api"  # External API calls
    DECISION = "decision"  # Important decision points
    ERROR = "error"  # Errors and exceptions
    PERFORMANCE = "performance"  # Performance metrics
    SYSTEM = "system"  # System-level operations
    OTHER = "other"  # Uncategorized activities


class ActivityLevel(enum.Enum):
    """Importance/severity levels for activities."""

    DEBUG = "debug"  # Verbose details for debugging
    INFO = "info"  # Normal operational information
    WARNING = "warning"  # Concerning but non-critical issues
    ERROR = "error"  # Errors that impact functionality
    CRITICAL = "critical"  # Severe errors requiring immediate attention


class ActivityLogger:
    """
    Comprehensive logging system for tracking agent activities.

    Features:
    - Activity categorization and prioritization
    - Thought process capture
    - Decision recording with reasoning
    - Input/output tracking
    - Performance metrics
    - Database persistence

    Every significant agent action should be logged to provide a
    complete audit trail and enable performance analysis.
    """

    def __init__(
        self,
        agent_id: Optional[uuid.UUID] = None,
        agent_name: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        min_level: ActivityLevel = ActivityLevel.INFO,
    ):
        """
        Initialize the activity logger.

        Args:
            agent_id: UUID of the agent performing activities (if applicable)
            agent_name: Human-readable name of the agent (for non-DB logging)
            db_session: SQLAlchemy async session for database persistence
            min_level: Minimum activity level to log
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.db_session = db_session
        self.min_level = min_level

        # Performance timing data
        self.timers: Dict[str, float] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}

        # Session tracking
        self.session_id = uuid.uuid4()
        self.session_start_time = datetime.utcnow()

        # Decision tracking
        self.decisions: List[Dict[str, Any]] = []

    async def log_activity(
        self,
        activity_type: str,
        description: str,
        category: ActivityCategory = ActivityCategory.OTHER,
        level: ActivityLevel = ActivityLevel.INFO,
        details: Optional[Dict[str, Any]] = None,
        thought_process: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        related_files: Optional[List[str]] = None,
        decisions_made: Optional[List[Dict[str, Any]]] = None,
        execution_time_ms: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[uuid.UUID]:
        """
        Log an agent activity with comprehensive details.

        Args:
            activity_type: Specific type of activity (e.g., "code_generation", "message_sent")
            description: Human-readable description of the activity
            category: High-level category for the activity
            level: Importance/severity level of the activity
            details: Additional structured details about the activity
            thought_process: Internal reasoning of the agent (if applicable)
            input_data: Structured input data that the agent worked with
            output_data: Structured output data that the agent produced
            related_files: List of file paths affected by the activity
            decisions_made: Structured record of decisions made during the activity
            execution_time_ms: Time taken to execute the activity in milliseconds
            tags: List of tags for easier searching/filtering

        Returns:
            UUID of the created activity record if stored in DB, None otherwise
        """
        # Skip logging if below minimum level
        if self._level_value(level) < self._level_value(self.min_level):
            return None

        timestamp = datetime.utcnow()

        # Compile all details for the log record
        activity_input_data = input_data or {}
        if details:
            # If details is provided for backward compatibility, merge it into input_data
            activity_input_data.update(details)

        # Add session tracking
        activity_input_data["session_id"] = str(self.session_id)
        activity_input_data["session_duration_s"] = (
            timestamp - self.session_start_time
        ).total_seconds()

        # Add additional data if provided
        if tags:
            activity_input_data["tags"] = tags

        # Log to Python logger first (always happens, even without DB)
        self._log_to_std_logger(
            activity_type, description, category, level, activity_input_data
        )

        # If no database session, we're done after standard logging
        if not self.db_session:
            return None

        # Create and store the activity record in the database
        activity_id = uuid.uuid4()

        try:
            # Create an AgentActivity instance using the correct field names
            activity_data = {
                "activity_id": activity_id,
                "agent_id": self.agent_id,
                "timestamp": timestamp,
                "activity_type": activity_type,
                "description": description,
                "thought_process": thought_process,
                "input_data": activity_input_data,
                "output_data": output_data,
                "related_files": related_files,
                "decisions_made": decisions_made,
                "execution_time_ms": execution_time_ms,
            }

            # Create an AgentActivity instance
            activity = AgentActivity(**activity_data)

            # Add to session and commit
            self.db_session.add(activity)
            await self.db_session.commit()

            return activity_id
        except Exception as e:
            logger.error(f"Failed to store activity log: {str(e)}")
            # Log the error through standard logging but don't try to store it in DB
            # to avoid infinite recursion
            error_details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "original_activity": {
                    "activity_type": activity_type,
                    "description": description,
                    "category": category.value,
                },
            }
            # Log to standard logger only, not to database
            self._log_to_std_logger(
                "logging_error",
                "Failed to store activity log in database",
                ActivityCategory.ERROR,
                ActivityLevel.ERROR,
                error_details,
            )
            return None

    async def log_decision(
        self,
        decision_type: str,
        description: str,
        options: List[Dict[str, Any]],
        chosen_option: Dict[str, Any],
        reasoning: str,
        confidence: float = 0.0,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> Optional[uuid.UUID]:
        """
        Log a decision made by an agent with detailed reasoning.

        Args:
            decision_type: Type of decision (e.g., "design_choice", "task_prioritization")
            description: Human-readable description of the decision
            options: List of all options that were considered
            chosen_option: The specific option that was selected
            reasoning: Detailed reasoning for why this option was chosen
            confidence: Confidence level in the decision (0.0 to 1.0)
            additional_context: Any additional context relevant to the decision

        Returns:
            UUID of the created activity record if stored in DB, None otherwise
        """
        decision_data = {
            "decision_type": decision_type,
            "options": options,
            "chosen_option": chosen_option,
            "reasoning": reasoning,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if additional_context:
            decision_data["context"] = additional_context

        # Add to the decisions history
        self.decisions.append(decision_data)

        return await self.log_activity(
            activity_type=f"decision_{decision_type}",
            description=description,
            category=ActivityCategory.DECISION,
            level=ActivityLevel.INFO,
            thought_process=reasoning,
            decisions_made=[decision_data],
            tags=["decision", decision_type],
        )

    async def log_error(
        self,
        error_type: str,
        description: str,
        exception: Optional[Exception] = None,
        severity: ActivityLevel = ActivityLevel.ERROR,
        context: Optional[Dict[str, Any]] = None,
        recovery_action: Optional[str] = None,
    ) -> Optional[uuid.UUID]:
        """
        Log an error or exception.

        Args:
            error_type: Type/category of error
            description: Human-readable error description
            exception: Exception object if available
            severity: Severity level of the error
            context: Context in which the error occurred
            recovery_action: Description of recovery action taken (if any)

        Returns:
            UUID of the created activity record if stored in DB, None otherwise
        """
        input_data = context or {}

        if exception:
            input_data["error_message"] = str(exception)
            input_data["error_type"] = exception.__class__.__name__
            input_data["traceback"] = traceback.format_exc()

        if recovery_action:
            input_data["recovery_action"] = recovery_action

        # Avoid infinite recursion with log_activity
        # First, try standard logging
        self._log_to_std_logger(
            error_type,
            description,
            ActivityCategory.ERROR,
            severity,
            input_data,
        )

        # If we don't have a database session, we're done
        if not self.db_session:
            return None

        # Otherwise, try to store directly in the database
        try:
            activity_id = uuid.uuid4()
            timestamp = datetime.utcnow()

            # Create an AgentActivity instance directly
            activity = AgentActivity(
                activity_id=activity_id,
                agent_id=self.agent_id,
                timestamp=timestamp,
                activity_type=error_type,
                description=description,
                input_data=input_data,
            )

            # Add to session and commit
            self.db_session.add(activity)
            await self.db_session.commit()

            return activity_id
        except Exception as e:
            # Just log to standard logger if we failed to log to db
            logger.error(f"Failed to store error log in database: {str(e)}")
            return None

    def start_timer(self, operation_name: str) -> None:
        """
        Start a timer for measuring operation duration.

        Args:
            operation_name: Name of the operation being timed
        """
        self.timers[operation_name] = time.time()

    async def stop_timer(
        self,
        operation_name: str,
        success: bool = True,
        log_activity: bool = True,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Stop a timer and record performance metrics.

        Args:
            operation_name: Name of the operation being timed
            success: Whether the operation completed successfully
            log_activity: Whether to log an activity for this timing
            additional_data: Additional context for the timing

        Returns:
            Duration of the operation in seconds
        """
        if operation_name not in self.timers:
            logger.warning(f"No timer started for operation: {operation_name}")
            return 0.0

        start_time = self.timers.pop(operation_name)
        duration_s = time.time() - start_time
        duration_ms = int(duration_s * 1000)

        # Update metrics for this operation type
        if operation_name not in self.metrics:
            self.metrics[operation_name] = {
                "count": 0,
                "total_ms": 0,
                "min_ms": float("inf"),
                "max_ms": 0,
                "success_count": 0,
                "failure_count": 0,
            }

        metrics = self.metrics[operation_name]
        metrics["count"] += 1
        metrics["total_ms"] += duration_ms
        metrics["min_ms"] = min(metrics["min_ms"], duration_ms)
        metrics["max_ms"] = max(metrics["max_ms"], duration_ms)

        if success:
            metrics["success_count"] += 1
        else:
            metrics["failure_count"] += 1

        # Log the timing information if requested
        if log_activity:
            performance_data = {
                "operation": operation_name,
                "duration_ms": duration_ms,
                "success": success,
                **(additional_data or {}),
            }

            await self.log_activity(
                activity_type="performance_measurement",
                description=f"Performance timing for {operation_name}: {duration_ms}ms",
                category=ActivityCategory.PERFORMANCE,
                level=ActivityLevel.DEBUG,
                input_data=performance_data,
                execution_time_ms=duration_ms,
                tags=["performance", "timing", operation_name],
            )

        return duration_s

    async def log_communication(
        self,
        message_type: str,
        sender_id: Union[uuid.UUID, str],
        recipient_id: Union[uuid.UUID, str],
        content_summary: str,
        message_id: Optional[uuid.UUID] = None,
        full_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[uuid.UUID]:
        """
        Log agent-to-agent communication.

        Args:
            message_type: Type of message (e.g., "request", "response")
            sender_id: ID of the agent sending the message
            recipient_id: ID of the agent receiving the message
            content_summary: Brief summary of message content
            message_id: UUID of the message if applicable
            full_content: Full message content if needed
            metadata: Additional message metadata

        Returns:
            UUID of the created activity record if stored in DB, None otherwise
        """
        comm_data = {
            "message_type": message_type,
            "sender_id": str(sender_id),
            "recipient_id": str(recipient_id),
            "content_summary": content_summary,
        }

        if message_id:
            comm_data["message_id"] = str(message_id)

        if full_content:
            comm_data["full_content"] = full_content

        if metadata:
            comm_data["metadata"] = metadata

        return await self.log_activity(
            activity_type=f"communication_{message_type}",
            description=f"{message_type.capitalize()} from {sender_id} to {recipient_id}: {content_summary[:50]}{'...' if len(content_summary) > 50 else ''}",
            category=ActivityCategory.COMMUNICATION,
            input_data=comm_data,
            tags=["communication", message_type],
        )

    async def log_thinking_process(
        self,
        thought_type: str,
        description: str,
        reasoning: str,
        input_context: Dict[str, Any],
        conclusion: Optional[str] = None,
        intermediate_steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[uuid.UUID]:
        """
        Log agent's thinking/reasoning process.

        Args:
            thought_type: Type of thinking (e.g., "problem_analysis", "solution_generation")
            description: Brief description of what the agent is thinking about
            reasoning: Detailed reasoning/thought process
            input_context: Input that prompted this thinking
            conclusion: Final conclusion reached (if any)
            intermediate_steps: Step-by-step reasoning (if available)

        Returns:
            UUID of the created activity record if stored in DB, None otherwise
        """
        thinking_data = {
            "reasoning": reasoning,
            "input_context": input_context,
        }

        if conclusion:
            thinking_data["conclusion"] = conclusion

        if intermediate_steps:
            thinking_data["steps"] = intermediate_steps

        return await self.log_activity(
            activity_type=f"thinking_{thought_type}",
            description=description,
            category=ActivityCategory.THINKING,
            thought_process=reasoning,
            input_data=thinking_data,
            tags=["thinking", thought_type],
        )

    async def get_recent_activities(
        self,
        limit: int = 50,
        activity_types: Optional[List[str]] = None,
        categories: Optional[List[ActivityCategory]] = None,
        min_level: Optional[ActivityLevel] = None,
        time_window: Optional[timedelta] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve recent activities matching specified criteria.

        Args:
            limit: Maximum number of activities to retrieve
            activity_types: Filter by specific activity types
            categories: Filter by activity categories
            min_level: Minimum activity level to include
            time_window: Only include activities within this time window
            tags: Filter by tags

        Returns:
            List of matching activity records
        """
        if not self.db_session:
            logger.warning("No database session available for querying activities")
            return []

        try:
            # Start with base query
            query = (
                select(AgentActivity)
                .order_by(desc(AgentActivity.timestamp))
                .limit(limit)
            )

            # Apply agent ID filter if available
            if self.agent_id:
                query = query.where(AgentActivity.agent_id == self.agent_id)

            # Apply time window filter if specified
            if time_window:
                cutoff_time = datetime.utcnow() - time_window
                query = query.where(AgentActivity.timestamp >= cutoff_time)

            # Execute query
            result = await self.db_session.execute(query)
            activities = result.scalars().all()

            # Apply post-query filters (these are on JSON fields so we filter in Python)
            filtered_activities = []

            for activity in activities:
                input_data = activity.input_data or {}

                # Filter by activity types
                if activity_types and activity.activity_type not in activity_types:
                    continue

                # Filter by categories
                if categories:
                    activity_category = input_data.get("category")
                    if not activity_category or activity_category not in [
                        c.value for c in categories
                    ]:
                        continue

                # Filter by minimum level
                if min_level:
                    activity_level = input_data.get("level")
                    if not activity_level or self._level_value(
                        ActivityLevel(activity_level)
                    ) < self._level_value(min_level):
                        continue

                # Filter by tags
                if tags:
                    activity_tags = input_data.get("tags", [])
                    if not all(tag in activity_tags for tag in tags):
                        continue

                # Convert to dict for easier consumption
                activity_dict = {
                    "activity_id": activity.activity_id,
                    "agent_id": activity.agent_id,
                    "timestamp": activity.timestamp,
                    "activity_type": activity.activity_type,
                    "description": activity.description,
                    "thought_process": activity.thought_process,
                    "input_data": activity.input_data,
                    "output_data": activity.output_data,
                    "related_files": activity.related_files,
                    "decisions_made": activity.decisions_made,
                    "execution_time_ms": activity.execution_time_ms,
                }

                filtered_activities.append(activity_dict)

            return filtered_activities
        except Exception as e:
            logger.error(f"Error retrieving activities: {str(e)}")
            return []

    async def get_agent_performance_metrics(
        self,
        time_window: Optional[timedelta] = None,
        operation_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve aggregated performance metrics for an agent.

        Args:
            time_window: Time window for metrics (None for all-time)
            operation_types: Specific operation types to include

        Returns:
            Dictionary of performance metrics
        """
        if not self.db_session or not self.agent_id:
            return self.metrics  # Return in-memory metrics if no DB

        try:
            # Build the base query
            query_str = """
            SELECT 
                activity_type,
                COUNT(*) as operation_count,
                AVG((input_data->>'execution_time_ms')::float) as avg_time_ms,
                MIN((input_data->>'execution_time_ms')::float) as min_time_ms,
                MAX((input_data->>'execution_time_ms')::float) as max_time_ms,
                SUM(CASE WHEN input_data->>'success' = 'true' THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN input_data->>'success' = 'false' THEN 1 ELSE 0 END) as failure_count
            FROM 
                agent_activities
            WHERE 
                agent_id = :agent_id
                AND (input_data->>'execution_time_ms') IS NOT NULL
            """

            params = {"agent_id": str(self.agent_id)}

            # Add time window condition if specified
            if time_window:
                query_str += " AND timestamp >= :cutoff_time"
                params["cutoff_time"] = datetime.utcnow() - time_window

            # Add operation types filter if specified
            if operation_types:
                placeholders = [f":op_type_{i}" for i in range(len(operation_types))]
                query_str += f" AND activity_type IN ({','.join(placeholders)})"
                for i, op_type in enumerate(operation_types):
                    params[f"op_type_{i}"] = op_type

            # Group by activity type
            query_str += " GROUP BY activity_type"

            # Execute the query
            result = await self.db_session.execute(text(query_str), params)
            rows = result.fetchall()

            # Format the results
            metrics = {}

            for row in rows:
                metrics[row.activity_type] = {
                    "count": row.operation_count,
                    "avg_ms": float(row.avg_time_ms),
                    "min_ms": float(row.min_time_ms),
                    "max_ms": float(row.max_time_ms),
                    "success_count": row.success_count,
                    "failure_count": row.failure_count,
                }

            return metrics
        except Exception as e:
            logger.error(f"Error retrieving performance metrics: {str(e)}")
            return self.metrics  # Fall back to in-memory metrics

    def get_decision_history(self) -> List[Dict[str, Any]]:
        """
        Get the history of decisions made in the current session.

        Returns:
            List of decision records
        """
        return self.decisions

    def _log_to_std_logger(
        self,
        activity_type: str,
        description: str,
        category: ActivityCategory,
        level: ActivityLevel,
        details: Dict[str, Any],
    ) -> None:
        """
        Log to the standard Python logger.

        Args:
            activity_type: Type of activity
            description: Human-readable description
            category: Activity category
            level: Severity/importance level
            details: Additional structured details
        """
        # Skip if below minimum level
        if self._level_value(level) < self._level_value(self.min_level):
            return

        log_func = getattr(logger, level.value)

        # Construct log message
        agent_prefix = f"[{self.agent_name or 'Anonymous'}] " if self.agent_name else ""
        message = (
            f"{agent_prefix}{category.value.upper()}/{activity_type}: {description}"
        )

        # Add extra context for structured logging
        extra = {
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "activity_type": activity_type,
            "category": category.value,
            "level": level.value,
        }

        # Log with details as extra context
        log_func(message, extra=extra)

    def _level_value(self, level: ActivityLevel) -> int:
        """
        Convert activity level to numeric value for comparison.

        Args:
            level: Activity level

        Returns:
            Numeric value (higher is more severe)
        """
        level_values = {
            ActivityLevel.DEBUG: 0,
            ActivityLevel.INFO: 1,
            ActivityLevel.WARNING: 2,
            ActivityLevel.ERROR: 3,
            ActivityLevel.CRITICAL: 4,
        }
        return level_values.get(level, 0)
