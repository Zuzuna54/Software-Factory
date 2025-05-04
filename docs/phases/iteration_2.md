# Iteration 2: Scrum Master, Product Manager & Task Orchestration

## Overview

This phase focuses on implementing the core orchestration components and specialized agents that will coordinate all development activities. We'll create the Product Manager agent, which translates high-level requirements into structured tasks, and the Scrum Master agent, which manages task coordination and assignment. We'll also implement the task queue system for asynchronous processing.

## Why This Phase Matters

The orchestration layer is crucial for enabling autonomous software development. It allows multiple agents to work together in a coordinated manner, with clear task ownership and sequence control. The PM and Scrum Master agents embody the "brain" of our system, making planning decisions and coordinating execution.

## Expected Outcomes

After completing this phase, we will have:

1. A functional `ProductManagerAgent` that can analyze requirements and produce a structured backlog
2. A `ScrumMasterAgent` that manages task coordination and assignment
3. A Celery-based task queue system integrated with Redis for asynchronous processing
4. A comprehensive task tracking system in the database
5. Storage for various artifact types (requirements, user stories, features)
6. The ability to initiate a new project development cycle

## Implementation Tasks

### Task 1: Product Manager Agent Implementation

**What needs to be done:**
Implement the Product Manager agent that can translate high-level requirements into structured user stories and tasks.

**Why this task is necessary:**
The PM agent serves as the entry point for new project requirements and breaks them down into actionable development tasks.

**Files to be created:**

- `agents/specialized/product_manager.py` - Product Manager agent implementation

**Implementation guidelines:**

```python
# agents/specialized/product_manager.py

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..base_agent import BaseAgent
from ..memory.vector_memory import VectorMemory

class ProductManagerAgent(BaseAgent):
    """
    Product Manager Agent - Responsible for translating high-level requirements
    into structured tasks and user stories.
    """

    def __init__(self, **kwargs):
        super().__init__(
            agent_type="product_manager",
            agent_name="Product Manager",
            capabilities={
                "requirement_analysis": True,
                "user_story_creation": True,
                "prioritization": True,
                "acceptance_criteria": True,
                "project_vision": True
            },
            **kwargs
        )
        self.logger = logging.getLogger(f"agent.pm.{self.agent_id}")

    async def analyze_requirements(self, project_description: str) -> Dict[str, Any]:
        """
        Analyze a high-level project description and break it down into structured
        requirements and features.
        """
        system_message = """You are a Product Manager for a software development team.
        Analyze the project description and break it down into:
        1. A clear project vision statement
        2. Key features (3-7 major capabilities)
        3. User stories for each feature (following the "As a [role] I want [goal] so that [benefit]" format)
        4. Acceptance criteria for each user story
        5. Non-functional requirements (performance, security, etc.)

        Structure your response as a JSON object that can be parsed programmatically."""

        prompt = f"""Project Description:
        {project_description}

        Please analyze this description and provide a structured breakdown as specified."""

        # Log that we're starting the analysis
        await self.log_activity(
            activity_type="RequirementAnalysis",
            description="Analyzing project requirements",
            input_data={"project_description": project_description}
        )

        # Use the LLM to analyze requirements
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during requirement analysis: {error}")
            return {"error": error}

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find('{')
            end_idx = thought.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in the response")

            json_str = thought[start_idx:end_idx]
            requirements = json.loads(json_str)

            # Store the requirements in the database
            await self._store_requirements(requirements)

            # Log the successful analysis
            await self.log_activity(
                activity_type="RequirementAnalysisComplete",
                description="Successfully analyzed project requirements",
                input_data={"project_description": project_description},
                output_data={"requirements_summary": {
                    "vision": requirements.get("vision", ""),
                    "feature_count": len(requirements.get("features", [])),
                    "story_count": sum(len(f.get("user_stories", [])) for f in requirements.get("features", []))
                }}
            )

            return requirements

        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error parsing requirement analysis: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="RequirementAnalysisError",
                description="Failed to parse requirement analysis result",
                input_data={"project_description": project_description},
                output_data={"error": str(e), "raw_result": thought}
            )

            return {"error": error_msg, "raw_response": thought}

    async def _store_requirements(self, requirements: Dict[str, Any]) -> None:
        """Store the analyzed requirements in the database."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping requirement storage")
            return

        # Store project vision
        vision_id = str(uuid4())

        vision_query = """
        INSERT INTO project_vision (
            vision_id, project_id, title, vision_statement,
            target_audience, key_goals, success_metrics, constraints,
            created_by, status
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """

        # Use a default project ID for now
        # In a real system, we'd track different projects
        project_id = "default-project"

        await self.db_client.execute(
            vision_query,
            vision_id,
            project_id,
            requirements.get("title", "Untitled Project"),
            requirements.get("vision", ""),
            requirements.get("target_audience", ""),
            json.dumps(requirements.get("key_goals", [])),
            json.dumps(requirements.get("success_metrics", {})),
            json.dumps(requirements.get("constraints", [])),
            self.agent_id,
            "ACTIVE"
        )

        # Store features as requirement artifacts
        for feature in requirements.get("features", []):
            feature_id = str(uuid4())

            feature_query = """
            INSERT INTO artifacts (
                artifact_id, artifact_type, title, content,
                created_by, status, metadata, version
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """

            await self.db_client.execute(
                feature_query,
                feature_id,
                "Feature",
                feature.get("title", "Untitled Feature"),
                feature.get("description", ""),
                self.agent_id,
                "DRAFT",
                json.dumps({
                    "priority": feature.get("priority", "Medium"),
                    "complexity": feature.get("complexity", "Medium"),
                    "dependencies": feature.get("dependencies", [])
                }),
                1
            )

            # Store user stories for this feature
            for story in feature.get("user_stories", []):
                story_id = str(uuid4())

                story_query = """
                INSERT INTO artifacts (
                    artifact_id, artifact_type, title, content,
                    created_by, status, metadata, parent_id, version
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """

                await self.db_client.execute(
                    story_query,
                    story_id,
                    "UserStory",
                    story.get("title", "Untitled Story"),
                    story.get("description", ""),
                    self.agent_id,
                    "DRAFT",
                    json.dumps({
                        "as_a": story.get("as_a", ""),
                        "i_want": story.get("i_want", ""),
                        "so_that": story.get("so_that", ""),
                        "acceptance_criteria": story.get("acceptance_criteria", []),
                        "priority": story.get("priority", "Medium"),
                        "estimate": story.get("estimate", "Medium")
                    }),
                    feature_id,  # Parent is the feature
                    1
                )

        # Store non-functional requirements
        for nfr in requirements.get("non_functional_requirements", []):
            nfr_id = str(uuid4())

            nfr_query = """
            INSERT INTO artifacts (
                artifact_id, artifact_type, title, content,
                created_by, status, metadata, version
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """

            await self.db_client.execute(
                nfr_query,
                nfr_id,
                "NonFunctionalRequirement",
                nfr.get("title", "Untitled NFR"),
                nfr.get("description", ""),
                self.agent_id,
                "DRAFT",
                json.dumps({
                    "category": nfr.get("category", "Other"),
                    "priority": nfr.get("priority", "Medium"),
                    "metrics": nfr.get("metrics", [])
                }),
                1
            )

    async def prioritize_backlog(self, project_id: str) -> List[Dict[str, Any]]:
        """Prioritize the product backlog based on value, risk, and dependencies."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping backlog prioritization")
            return []

        # Fetch all features and user stories
        query = """
        SELECT
            artifact_id, artifact_type, title, content,
            parent_id, metadata
        FROM artifacts
        WHERE artifact_type IN ('Feature', 'UserStory')
        """

        artifacts = await self.db_client.fetch_all(query)

        # Organize artifacts into a structured format
        features = []
        stories_by_feature = {}

        for artifact in artifacts:
            if artifact["artifact_type"] == "Feature":
                feature_id = artifact["artifact_id"]
                metadata = json.loads(artifact["metadata"]) if artifact["metadata"] else {}

                features.append({
                    "id": feature_id,
                    "title": artifact["title"],
                    "description": artifact["content"],
                    "priority": metadata.get("priority", "Medium"),
                    "complexity": metadata.get("complexity", "Medium"),
                    "dependencies": metadata.get("dependencies", [])
                })

                stories_by_feature[feature_id] = []

            elif artifact["artifact_type"] == "UserStory":
                feature_id = artifact["parent_id"]
                if feature_id:
                    metadata = json.loads(artifact["metadata"]) if artifact["metadata"] else {}

                    if feature_id not in stories_by_feature:
                        stories_by_feature[feature_id] = []

                    stories_by_feature[feature_id].append({
                        "id": artifact["artifact_id"],
                        "title": artifact["title"],
                        "description": artifact["content"],
                        "as_a": metadata.get("as_a", ""),
                        "i_want": metadata.get("i_want", ""),
                        "so_that": metadata.get("so_that", ""),
                        "priority": metadata.get("priority", "Medium"),
                        "estimate": metadata.get("estimate", "Medium")
                    })

        # Add user stories to their respective features
        for feature in features:
            feature["user_stories"] = stories_by_feature.get(feature["id"], [])

        # Use LLM to help with prioritization
        system_message = """You are a Product Manager deciding the priority of features and user stories.
        Review the backlog items and assign priorities based on:
        1. Business value (high/medium/low)
        2. Technical risk (high/medium/low)
        3. Dependencies between items
        4. Implementation complexity

        Respond with a JSON object containing the prioritized backlog."""

        prompt = f"""Backlog Items to Prioritize:
        {json.dumps(features, indent=2)}

        Please analyze these items and provide a prioritized backlog with updated priority values."""

        # Log that we're starting prioritization
        await self.log_activity(
            activity_type="BacklogPrioritization",
            description="Prioritizing product backlog",
            input_data={"feature_count": len(features)}
        )

        # Use the LLM to prioritize
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during backlog prioritization: {error}")
            return []

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find('{')
            end_idx = thought.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in the response")

            json_str = thought[start_idx:end_idx]
            prioritized = json.loads(json_str)

            # Update priorities in the database
            await self._update_priorities(prioritized)

            # Log the successful prioritization
            await self.log_activity(
                activity_type="BacklogPrioritizationComplete",
                description="Successfully prioritized product backlog",
                output_data={"prioritized_features": len(prioritized.get("features", []))}
            )

            return prioritized.get("features", [])

        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error parsing backlog prioritization: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="BacklogPrioritizationError",
                description="Failed to parse backlog prioritization result",
                output_data={"error": str(e), "raw_result": thought}
            )

            return []

    async def _update_priorities(self, prioritized_backlog: Dict[str, Any]) -> None:
        """Update priorities in the database based on the prioritization results."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping priority updates")
            return

        # Update feature priorities
        for feature in prioritized_backlog.get("features", []):
            feature_id = feature.get("id")
            if not feature_id:
                continue

            # Fetch current metadata
            query = "SELECT metadata FROM artifacts WHERE artifact_id = $1"
            result = await self.db_client.fetch_one(query, feature_id)

            if not result:
                continue

            metadata = json.loads(result["metadata"]) if result["metadata"] else {}

            # Update metadata with new priorities
            metadata["priority"] = feature.get("priority", metadata.get("priority", "Medium"))
            metadata["business_value"] = feature.get("business_value", metadata.get("business_value", "Medium"))
            metadata["technical_risk"] = feature.get("technical_risk", metadata.get("technical_risk", "Medium"))

            # Save updated metadata
            update_query = "UPDATE artifacts SET metadata = $1 WHERE artifact_id = $2"
            await self.db_client.execute(update_query, json.dumps(metadata), feature_id)

            # Update user story priorities
            for story in feature.get("user_stories", []):
                story_id = story.get("id")
                if not story_id:
                    continue

                # Fetch current metadata
                query = "SELECT metadata FROM artifacts WHERE artifact_id = $1"
                result = await self.db_client.fetch_one(query, story_id)

                if not result:
                    continue

                metadata = json.loads(result["metadata"]) if result["metadata"] else {}

                # Update metadata with new priorities
                metadata["priority"] = story.get("priority", metadata.get("priority", "Medium"))

                # Save updated metadata
                update_query = "UPDATE artifacts SET metadata = $1 WHERE artifact_id = $2"
                await self.db_client.execute(update_query, json.dumps(metadata), story_id)
```

### Task 2: Scrum Master Agent Implementation

**What needs to be done:**
Implement the Scrum Master agent that coordinates all development activities and manages task assignment.

**Why this task is necessary:**
The Scrum Master agent serves as the orchestrator of the development process, ensuring that tasks are assigned to the right agents and tracked through completion.

**Files to be created:**

- `agents/specialized/scrum_master.py` - Scrum Master agent implementation

**Implementation guidelines:**

```python
# agents/specialized/scrum_master.py

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4
from datetime import datetime, timedelta

from ..base_agent import BaseAgent

class ScrumMasterAgent(BaseAgent):
    """
    Scrum Master Agent - Responsible for coordinating the development process,
    managing task assignments, and tracking progress.
    """

    def __init__(self, **kwargs):
        super().__init__(
            agent_type="scrum_master",
            agent_name="Scrum Master",
            capabilities={
                "sprint_planning": True,
                "task_assignment": True,
                "progress_tracking": True,
                "impediment_removal": True,
                "meeting_facilitation": True
            },
            **kwargs
        )
        self.logger = logging.getLogger(f"agent.sm.{self.agent_id}")
        self.sprint_id = None

    async def plan_sprint(self, backlog_items: List[Dict[str, Any]], sprint_duration_days: int = 14) -> Dict[str, Any]:
        """
        Plan a sprint based on prioritized backlog items.
        """
        system_message = """You are a Scrum Master planning a sprint.
        Review the backlog items and:
        1. Select appropriate items for the sprint based on priority and dependencies
        2. Break down features and user stories into specific tasks with estimates
        3. Ensure the sprint has a balanced workload and achievable goals
        4. Assign tasks to appropriate roles (Frontend, Backend, QA, etc.)

        Respond with a JSON object containing the sprint plan."""

        prompt = f"""Backlog Items to Consider:
        {json.dumps(backlog_items, indent=2)}

        Sprint Duration: {sprint_duration_days} days

        Please create a sprint plan selecting items that can be completed within the sprint duration."""

        # Log that we're starting sprint planning
        await self.log_activity(
            activity_type="SprintPlanning",
            description=f"Planning {sprint_duration_days}-day sprint",
            input_data={"backlog_item_count": len(backlog_items)}
        )

        # Use the LLM to plan the sprint
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during sprint planning: {error}")
            return {"error": error}

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find('{')
            end_idx = thought.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in the response")

            json_str = thought[start_idx:end_idx]
            sprint_plan = json.loads(json_str)

            # Create a new sprint in the database
            sprint_id = await self._create_sprint(sprint_plan, sprint_duration_days)
            self.sprint_id = sprint_id

            # Create tasks for the sprint
            await self._create_sprint_tasks(sprint_id, sprint_plan)

            # Log the successful sprint planning
            await self.log_activity(
                activity_type="SprintPlanningComplete",
                description="Successfully planned sprint",
                output_data={
                    "sprint_id": sprint_id,
                    "task_count": sum(len(feature.get("tasks", [])) for feature in sprint_plan.get("features", []))
                }
            )

            # Add sprint_id to the result
            sprint_plan["sprint_id"] = sprint_id

            return sprint_plan

        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error parsing sprint plan: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="SprintPlanningError",
                description="Failed to parse sprint planning result",
                output_data={"error": str(e), "raw_result": thought}
            )

            return {"error": error_msg, "raw_response": thought}

    async def _create_sprint(self, sprint_plan: Dict[str, Any], duration_days: int) -> str:
        """Create a new sprint in the database."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping sprint creation")
            return str(uuid4())

        sprint_id = str(uuid4())
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)

        query = """
        INSERT INTO sprints (
            sprint_id, sprint_name, start_date, end_date,
            goal, created_by, status
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        """

        await self.db_client.execute(
            query,
            sprint_id,
            sprint_plan.get("sprint_name", f"Sprint {start_date.strftime('%Y-%m-%d')}"),
            start_date,
            end_date,
            sprint_plan.get("sprint_goal", ""),
            self.agent_id,
            "PLANNING"
        )

        return sprint_id

    async def _create_sprint_tasks(self, sprint_id: str, sprint_plan: Dict[str, Any]) -> None:
        """Create tasks in the database for the sprint."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping task creation")
            return

        # Collect all tasks from the sprint plan
        all_tasks = []

        for feature in sprint_plan.get("features", []):
            feature_id = feature.get("id")

            # Add tasks from features directly
            for task in feature.get("tasks", []):
                all_tasks.append({
                    "title": task.get("title", "Untitled Task"),
                    "description": task.get("description", ""),
                    "role": task.get("role", "Developer"),
                    "estimate": task.get("estimate", 1),
                    "priority": task.get("priority", "Medium"),
                    "related_artifact_id": feature_id
                })

            # Add tasks from user stories
            for story in feature.get("user_stories", []):
                story_id = story.get("id")

                for task in story.get("tasks", []):
                    all_tasks.append({
                        "title": task.get("title", "Untitled Task"),
                        "description": task.get("description", ""),
                        "role": task.get("role", "Developer"),
                        "estimate": task.get("estimate", 1),
                        "priority": task.get("priority", "Medium"),
                        "related_artifact_id": story_id
                    })

        # Insert all tasks
        for task in all_tasks:
            task_id = str(uuid4())

            query = """
            INSERT INTO tasks (
                task_id, title, description, created_at, created_by,
                sprint_id, priority, status, estimated_effort,
                related_artifacts
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """

            await self.db_client.execute(
                query,
                task_id,
                task["title"],
                task["description"],
                datetime.now(),
                self.agent_id,
                sprint_id,
                task["priority"],
                "BACKLOG",
                task["estimate"],
                [task["related_artifact_id"]] if task.get("related_artifact_id") else []
            )

    async def start_sprint(self, sprint_id: str) -> bool:
        """Start a sprint that has been planned."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping sprint start")
            return False

        # Update sprint status
        query = """
        UPDATE sprints SET status = $1 WHERE sprint_id = $2
        """

        await self.db_client.execute(query, "IN_PROGRESS", sprint_id)

        # Set self.sprint_id
        self.sprint_id = sprint_id

        # Log the sprint start
        await self.log_activity(
            activity_type="SprintStart",
            description=f"Started sprint {sprint_id}",
            output_data={"sprint_id": sprint_id}
        )

        # Announce sprint start to team
        # This would notify other agents that the sprint has started
        # For now, we'll just log it
        self.logger.info(f"Sprint {sprint_id} has started")

        return True

    async def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping task assignment")
            return False

        # Update task assignment
        query = """
        UPDATE tasks SET assigned_to = $1, status = $2 WHERE task_id = $3
        """

        await self.db_client.execute(query, agent_id, "ASSIGNED", task_id)

        # Log the task assignment
        await self.log_activity(
            activity_type="TaskAssignment",
            description=f"Assigned task {task_id} to agent {agent_id}",
            output_data={"task_id": task_id, "agent_id": agent_id}
        )

        # Notify the assigned agent
        await self.send_message(
            receiver_id=agent_id,
            content=f"You have been assigned task {task_id}. Please begin work on it.",
            message_type="TASK_ASSIGNMENT",
            related_task_id=task_id
        )

        return True

    async def update_task_status(self, task_id: str, status: str, agent_id: Optional[str] = None) -> bool:
        """Update the status of a task."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping task status update")
            return False

        # Validate the status
        valid_statuses = ["BACKLOG", "ASSIGNED", "IN_PROGRESS", "REVIEW", "DONE"]
        if status not in valid_statuses:
            self.logger.error(f"Invalid task status: {status}")
            return False

        # Update task status
        query = """
        UPDATE tasks SET status = $1 WHERE task_id = $2
        """

        await self.db_client.execute(query, status, task_id)

        # Log the status update
        await self.log_activity(
            activity_type="TaskStatusUpdate",
            description=f"Updated task {task_id} status to {status}",
            output_data={"task_id": task_id, "status": status}
        )

        # Notify relevant agents if needed
        if agent_id:
            await self.send_message(
                receiver_id=agent_id,
                content=f"Task {task_id} status has been updated to {status}.",
                message_type="TASK_UPDATE",
                related_task_id=task_id
            )

        return True

    async def get_sprint_status(self, sprint_id: Optional[str] = None) -> Dict[str, Any]:
        """Get the current status of a sprint."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping sprint status check")
            return {}

        # Use current sprint if not specified
        sprint_id = sprint_id or self.sprint_id

        if not sprint_id:
            self.logger.error("No sprint ID provided or set")
            return {"error": "No sprint ID provided or set"}

        # Get sprint information
        sprint_query = """
        SELECT sprint_id, sprint_name, start_date, end_date, goal, status
        FROM sprints WHERE sprint_id = $1
        """

        sprint = await self.db_client.fetch_one(sprint_query, sprint_id)

        if not sprint:
            self.logger.error(f"Sprint {sprint_id} not found")
            return {"error": f"Sprint {sprint_id} not found"}

        # Get task status counts
        task_query = """
        SELECT status, COUNT(*) as count
        FROM tasks
        WHERE sprint_id = $1
        GROUP BY status
        """

        task_status = await self.db_client.fetch_all(task_query, sprint_id)

        status_counts = {}
        for row in task_status:
            status_counts[row["status"]] = row["count"]

        # Calculate sprint progress
        total_tasks = sum(status_counts.values())
        completed_tasks = status_counts.get("DONE", 0)
        progress_percent = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "sprint_id": sprint["sprint_id"],
            "sprint_name": sprint["sprint_name"],
            "start_date": sprint["start_date"],
            "end_date": sprint["end_date"],
            "goal": sprint["goal"],
            "status": sprint["status"],
            "task_status": status_counts,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "progress_percent": progress_percent
        }

    # Agile Ceremony Methods

    async def schedule_ceremonies(self, sprint_id: str) -> Dict[str, Any]:
        """
        Schedule all ceremonies for a sprint.

        Args:
            sprint_id: ID of the sprint to schedule ceremonies for

        Returns:
            Dictionary of scheduled ceremony IDs
        """
        if not hasattr(self, 'ceremonies') or not self.ceremonies:
            self.logger.error("Ceremonies module not initialized")
            return {"error": "Ceremonies module not initialized"}

        # Get sprint information and team members
        sprint_info = await self.get_sprint_status(sprint_id)
        if "error" in sprint_info:
            return sprint_info

        # Get team members (developer agents, QA agents, etc.)
        team_query = """
        SELECT agent_id, agent_type FROM agents
        WHERE agent_type IN ('backend_developer', 'frontend_developer', 'qa', 'devops')
        AND active = true
        """

        team_results = await self.db_client.fetch_all(team_query)
        team_members = [row["agent_id"] for row in team_results]

        # Get product manager
        pm_query = """
        SELECT agent_id FROM agents
        WHERE agent_type = 'product_manager'
        AND active = true
        LIMIT 1
        """

        pm_result = await self.db_client.fetch_one(pm_query)
        pm_id = pm_result["agent_id"] if pm_result else None

        if not pm_id:
            self.logger.warning("No active Product Manager found")

        # Calculate ceremony dates based on sprint start/end
        start_date = sprint_info["start_date"]
        end_date = sprint_info["end_date"]

        # Schedule Sprint Planning at start
        planning_id = await self.ceremonies.schedule_sprint_planning(
            scrum_master_id=self.agent_id,
            product_manager_id=pm_id,
            team_members=team_members,
            start_time=start_date
        )

        # Schedule Daily Standups for each day of the sprint
        standup_ids = []
        current_date = start_date
        while current_date < end_date:
            standup_id = await self.ceremonies.schedule_daily_standup(
                scrum_master_id=self.agent_id,
                team_members=team_members,
                start_time=current_date
            )
            standup_ids.append(standup_id)
            current_date = current_date + timedelta(days=1)

        # Schedule Sprint Review near end
        review_time = end_date - timedelta(hours=4)
        review_id = await self.ceremonies.schedule_sprint_review(
            scrum_master_id=self.agent_id,
            product_manager_id=pm_id,
            team_members=team_members,
            start_time=review_time
        )

        # Schedule Sprint Retrospective after review
        retro_time = end_date - timedelta(hours=2)
        retro_id = await self.ceremonies.schedule_sprint_retrospective(
            scrum_master_id=self.agent_id,
            team_members=team_members,
            start_time=retro_time
        )

        # Log the ceremony scheduling
        await self.log_activity(
            activity_type="CeremoniesScheduled",
            description=f"Scheduled all ceremonies for sprint {sprint_id}",
            output_data={
                "sprint_id": sprint_id,
                "planning_id": planning_id,
                "standup_count": len(standup_ids),
                "review_id": review_id,
                "retro_id": retro_id
            }
        )

        return {
            "sprint_id": sprint_id,
            "planning_id": planning_id,
            "standup_ids": standup_ids,
            "review_id": review_id,
            "retro_id": retro_id
        }

    async def facilitate_standup(self, meeting_id: str) -> Dict[str, Any]:
        """
        Facilitate a daily standup meeting.

        Args:
            meeting_id: ID of the standup meeting to facilitate

        Returns:
            Meeting summary and action items
        """
        if not hasattr(self, 'meetings') or not self.meetings:
            self.logger.error("Meetings module not initialized")
            return {"error": "Meetings module not initialized"}

        # Start the meeting
        meeting_info = await self.meetings.start_meeting(meeting_id)
        if "error" in meeting_info:
            return meeting_info

        # Get participant information
        participants = meeting_info["participants"]

        # Send welcome message
        welcome_msg = await self.meetings.send_message_to_meeting(
            meeting_id=meeting_id,
            speaker_id=self.agent_id,
            message="Welcome to our daily standup. Let's go around and share: 1) What you accomplished yesterday, 2) What you're working on today, and 3) Any blockers you're facing.",
            message_type="Facilitation"
        )

        # In a real implementation, we would now wait for each participant to respond
        # and potentially ask follow-up questions. For this blueprint, we'll simulate
        # the process with a simple loop.

        action_items = []
        blockers = []

        # Simulate getting updates from each participant
        for participant_id in participants:
            if participant_id == self.agent_id:
                continue  # Skip self

            # In reality, we would wait for their actual response
            # Here we're just recording a placeholder
            await self.meetings.send_message_to_meeting(
                meeting_id=meeting_id,
                speaker_id=self.agent_id,
                message=f"Let's hear from {participant_id}. What's your update?",
                message_type="Question"
            )

            # Simulate some blockers and action items for demonstration
            if participant_id.endswith('1'):  # Just a way to simulate some agents having blockers
                blockers.append({
                    "agent_id": participant_id,
                    "description": "Waiting on dependency from another task"
                })
                action_items.append({
                    "description": f"Follow up with {participant_id} on dependency issue",
                    "assigned_to": self.agent_id,
                    "due_date": datetime.now() + timedelta(days=1)
                })

        # Send closing message
        await self.meetings.send_message_to_meeting(
            meeting_id=meeting_id,
            speaker_id=self.agent_id,
            message=f"Thank you everyone. I've noted {len(blockers)} blockers and {len(action_items)} action items that we'll follow up on after the meeting.",
            message_type="Facilitation"
        )

        # Generate meeting summary
        summary = f"Daily standup with {len(participants)} participants. {len(blockers)} blockers identified and {len(action_items)} action items created."

        # End the meeting
        end_result = await self.meetings.end_meeting(
            meeting_id=meeting_id,
            summary=summary,
            decisions={},
            action_items=action_items
        )

        # Log the facilitation
        await self.log_activity(
            activity_type="StandupFacilitation",
            description=f"Facilitated standup meeting {meeting_id}",
            output_data={
                "meeting_id": meeting_id,
                "participant_count": len(participants),
                "blocker_count": len(blockers),
                "action_item_count": len(action_items)
            }
        )

        # Follow up on blockers
        for blocker in blockers:
            await self.send_message(
                receiver_id=blocker["agent_id"],
                content=f"I noticed you mentioned a blocker in standup: {blocker['description']}. Let me know if you need any help resolving this.",
                message_type="ALERT",
                metadata={"severity": "MEDIUM", "blocker_from_standup": True}
            )

        return {
            "meeting_id": meeting_id,
            "summary": summary,
            "blockers": blockers,
            "action_items": action_items
        }
```

### Task 3: Virtual Team Meetings and Agile Ceremonies

**What needs to be done:**
Implement structured virtual team meetings and agile ceremonies to enable systematic agent collaboration and agile workflow.

**Why this task is necessary:**
Agile ceremonies create a structured framework for agent coordination, ensuring that all agents synchronize effectively and maintain alignment on project goals and progress.

**Files to be created:**

- `agents/orchestration/ceremonies.py` - Agile ceremonies implementation
- `agents/orchestration/meetings.py` - Virtual team meetings implementation

**Implementation guidelines:**

```python
# agents/orchestration/ceremonies.py

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..db.postgres import PostgresClient
from ..communication.protocol import CommunicationProtocol, MessageType

class AgileCeremonies:
    """
    Implementation of Agile ceremonies for structured team collaboration.
    """

    def __init__(
        self,
        db_client: PostgresClient,
        comm_protocol: CommunicationProtocol
    ):
        self.db_client = db_client
        self.comm_protocol = comm_protocol
        self.logger = logging.getLogger("agent.ceremonies")

    async def initialize(self) -> None:
        """Initialize the ceremonies infrastructure."""
        # Create meetings table if it doesn't exist
        await self.db_client.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            meeting_id UUID PRIMARY KEY,
            meeting_type VARCHAR(50) NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            participants UUID[] NOT NULL,
            summary TEXT,
            decisions JSONB,
            action_items JSONB
        );
        """)

        # Create meeting conversations table
        await self.db_client.execute("""
        CREATE TABLE IF NOT EXISTS meeting_conversations (
            conversation_id UUID PRIMARY KEY,
            meeting_id UUID REFERENCES meetings(meeting_id),
            sequence_number INTEGER NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            speaker_id UUID NOT NULL,
            message TEXT NOT NULL,
            message_type VARCHAR(50),
            context JSONB
        );
        """)

        self.logger.info("Agile ceremonies infrastructure initialized")

    async def schedule_sprint_planning(
        self,
        scrum_master_id: str,
        product_manager_id: str,
        team_members: List[str],
        sprint_duration_days: int = 14,
        start_time: Optional[datetime] = None
    ) -> str:
        """
        Schedule a sprint planning meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            product_manager_id: ID of the Product Manager agent
            team_members: List of team member agent IDs
            sprint_duration_days: Duration of the sprint in days
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        # Create meeting record
        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id, product_manager_id] + team_members

        await self.db_client.execute(
            query,
            meeting_id,
            "SprintPlanning",
            start_time,
            participants
        )

        # Notify participants
        for agent_id in participants:
            # Create different messages for different roles
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Sprint Planning meeting (ID: {meeting_id}) scheduled for {start_time}. You will lead the meeting and ensure all items are properly planned."
            elif agent_id == product_manager_id:
                content = f"Sprint Planning meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare the prioritized backlog items for planning."
            else:
                content = f"Sprint Planning meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare to discuss capacity and task assignments."

            # Send notification message
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={"meeting_id": meeting_id, "meeting_type": "SprintPlanning"}
            )

            # Store the notification message
            # This would typically use your message sending infrastructure
            # For now, we'll just log it
            self.logger.info(f"Notification sent to {agent_id} about meeting {meeting_id}")

        self.logger.info(f"Sprint Planning meeting {meeting_id} scheduled for {start_time}")
        return meeting_id

    async def schedule_daily_standup(
        self,
        scrum_master_id: str,
        team_members: List[str],
        start_time: Optional[datetime] = None
    ) -> str:
        """
        Schedule a daily standup meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            team_members: List of team member agent IDs
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        # Create meeting record
        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id] + team_members

        await self.db_client.execute(
            query,
            meeting_id,
            "DailyStandup",
            start_time,
            participants
        )

        # Notify participants
        for agent_id in participants:
            # Create different messages for different roles
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Daily Standup meeting (ID: {meeting_id}) scheduled for {start_time}."
            else:
                content = f"Daily Standup meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare updates on: 1) What you accomplished yesterday, 2) What you'll work on today, 3) Any blockers."

            # Send notification message
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={"meeting_id": meeting_id, "meeting_type": "DailyStandup"}
            )

            # Store the notification message
            self.logger.info(f"Notification sent to {agent_id} about meeting {meeting_id}")

        self.logger.info(f"Daily Standup meeting {meeting_id} scheduled for {start_time}")
        return meeting_id

    async def schedule_sprint_review(
        self,
        scrum_master_id: str,
        product_manager_id: str,
        team_members: List[str],
        start_time: Optional[datetime] = None
    ) -> str:
        """
        Schedule a sprint review meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            product_manager_id: ID of the Product Manager agent
            team_members: List of team member agent IDs
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        # Create meeting record
        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id, product_manager_id] + team_members

        await self.db_client.execute(
            query,
            meeting_id,
            "SprintReview",
            start_time,
            participants
        )

        # Notify participants
        for agent_id in participants:
            # Create different messages for different roles
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Sprint Review meeting (ID: {meeting_id}) scheduled for {start_time}."
            elif agent_id == product_manager_id:
                content = f"Sprint Review meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare to evaluate the completed work against acceptance criteria."
            else:
                content = f"Sprint Review meeting (ID: {meeting_id}) scheduled for {start_time}. Please prepare to demonstrate your completed work."

            # Send notification message
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={"meeting_id": meeting_id, "meeting_type": "SprintReview"}
            )

            # Store the notification message
            self.logger.info(f"Notification sent to {agent_id} about meeting {meeting_id}")

        self.logger.info(f"Sprint Review meeting {meeting_id} scheduled for {start_time}")
        return meeting_id

    async def schedule_sprint_retrospective(
        self,
        scrum_master_id: str,
        team_members: List[str],
        start_time: Optional[datetime] = None
    ) -> str:
        """
        Schedule a sprint retrospective meeting.

        Args:
            scrum_master_id: ID of the Scrum Master agent
            team_members: List of team member agent IDs
            start_time: Start time for the meeting (defaults to now)

        Returns:
            The meeting ID
        """
        if start_time is None:
            start_time = datetime.now()

        meeting_id = str(uuid4())

        # Create meeting record
        query = """
        INSERT INTO meetings (
            meeting_id, meeting_type, start_time, participants
        )
        VALUES ($1, $2, $3, $4)
        """

        participants = [scrum_master_id] + team_members

        await self.db_client.execute(
            query,
            meeting_id,
            "SprintRetrospective",
            start_time,
            participants
        )

        # Notify participants
        for agent_id in participants:
            # Create different messages for different roles
            if agent_id == scrum_master_id:
                content = f"Please facilitate the Sprint Retrospective meeting (ID: {meeting_id}) scheduled for {start_time}. Focus on what went well, what could be improved, and action items."
            else:
                content = f"Sprint Retrospective meeting (ID: {meeting_id}) scheduled for {start_time}. Please reflect on: 1) What went well, 2) What could be improved, 3) Action items for next sprint."

            # Send notification message
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=content,
                metadata={"meeting_id": meeting_id, "meeting_type": "SprintRetrospective"}
            )

            # Store the notification message
            self.logger.info(f"Notification sent to {agent_id} about meeting {meeting_id}")

        self.logger.info(f"Sprint Retrospective meeting {meeting_id} scheduled for {start_time}")
        return meeting_id
```

```python
# agents/orchestration/meetings.py

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..db.postgres import PostgresClient
from ..communication.protocol import CommunicationProtocol, MessageType, AgentMessage

class VirtualTeamMeetings:
    """
    Implementation of virtual team meetings for agent collaboration.
    """

    def __init__(
        self,
        db_client: PostgresClient,
        comm_protocol: CommunicationProtocol
    ):
        self.db_client = db_client
        self.comm_protocol = comm_protocol
        self.logger = logging.getLogger("agent.meetings")
        self.active_meetings = {}  # Tracks currently active meetings

    async def start_meeting(self, meeting_id: str) -> Dict[str, Any]:
        """
        Start a scheduled meeting.

        Args:
            meeting_id: ID of the meeting to start

        Returns:
            Meeting information
        """
        # Get meeting information
        query = """
        SELECT meeting_type, participants, start_time
        FROM meetings
        WHERE meeting_id = $1
        """

        meeting_info = await self.db_client.fetch_one(query, meeting_id)

        if not meeting_info:
            error_msg = f"Meeting {meeting_id} not found"
            self.logger.error(error_msg)
            return {"error": error_msg}

        # Update meeting as in progress
        update_query = """
        UPDATE meetings
        SET start_time = $1
        WHERE meeting_id = $2
        """

        actual_start_time = datetime.now()
        await self.db_client.execute(update_query, actual_start_time, meeting_id)

        # Mark meeting as active
        self.active_meetings[meeting_id] = {
            "type": meeting_info["meeting_type"],
            "participants": meeting_info["participants"],
            "start_time": actual_start_time,
            "messages": []
        }

        # Notify participants that the meeting has started
        for agent_id in meeting_info["participants"]:
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=f"Meeting {meeting_id} ({meeting_info['meeting_type']}) has started.",
                metadata={"meeting_id": meeting_id, "meeting_type": meeting_info["meeting_type"]}
            )

            # Store the notification
            self.logger.info(f"Start notification sent to {agent_id} for meeting {meeting_id}")

        self.logger.info(f"Meeting {meeting_id} ({meeting_info['meeting_type']}) started at {actual_start_time}")

        return {
            "meeting_id": meeting_id,
            "type": meeting_info["meeting_type"],
            "start_time": actual_start_time,
            "participants": meeting_info["participants"]
        }

    async def end_meeting(
        self,
        meeting_id: str,
        summary: Optional[str] = None,
        decisions: Optional[Dict[str, Any]] = None,
        action_items: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        End an active meeting and record outcomes.

        Args:
            meeting_id: ID of the meeting to end
            summary: Optional summary of the meeting
            decisions: Optional decisions made in the meeting
            action_items: Optional action items from the meeting

        Returns:
            Meeting outcome information
        """
        # Check if meeting is active
        if meeting_id not in self.active_meetings:
            error_msg = f"Meeting {meeting_id} is not active"
            self.logger.error(error_msg)
            return {"error": error_msg}

        # Get meeting information
        meeting_info = self.active_meetings[meeting_id]

        # Update meeting as completed
        update_query = """
        UPDATE meetings
        SET end_time = $1, summary = $2, decisions = $3, action_items = $4
        WHERE meeting_id = $5
        """

        end_time = datetime.now()
        await self.db_client.execute(
            update_query,
            end_time,
            summary,
            json.dumps(decisions or {}),
            json.dumps(action_items or []),
            meeting_id
        )

        # Remove from active meetings
        del self.active_meetings[meeting_id]

        # Notify participants that the meeting has ended
        for agent_id in meeting_info["participants"]:
            notification = self.comm_protocol.create_inform(
                sender="SYSTEM",
                receiver=agent_id,
                content=f"Meeting {meeting_id} ({meeting_info['type']}) has ended.",
                metadata={
                    "meeting_id": meeting_id,
                    "meeting_type": meeting_info["type"],
                    "decisions_count": len(decisions or {}),
                    "action_items_count": len(action_items or [])
                }
            )

            # Store the notification
            self.logger.info(f"End notification sent to {agent_id} for meeting {meeting_id}")

        self.logger.info(f"Meeting {meeting_id} ({meeting_info['type']}) ended at {end_time}")

        return {
            "meeting_id": meeting_id,
            "type": meeting_info["type"],
            "start_time": meeting_info["start_time"],
            "end_time": end_time,
            "duration_minutes": (end_time - meeting_info["start_time"]).total_seconds() / 60,
            "summary": summary,
            "decisions": decisions,
            "action_items": action_items
        }

    async def send_message_to_meeting(
        self,
        meeting_id: str,
        speaker_id: str,
        message: str,
        message_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message in an active meeting.

        Args:
            meeting_id: ID of the meeting
            speaker_id: ID of the agent sending the message
            message: Content of the message
            message_type: Optional type of message (Question, Answer, Proposal, etc.)
            context: Optional context information

        Returns:
            Information about the recorded message
        """
        # Check if meeting is active
        if meeting_id not in self.active_meetings:
            error_msg = f"Meeting {meeting_id} is not active"
            self.logger.error(error_msg)
            return {"error": error_msg}

        # Check if speaker is a participant
        meeting_info = self.active_meetings[meeting_id]
        if speaker_id not in meeting_info["participants"]:
            error_msg = f"Agent {speaker_id} is not a participant in meeting {meeting_id}"
            self.logger.error(error_msg)
            return {"error": error_msg}

        # Get current sequence number
        sequence_number = len(meeting_info["messages"]) + 1

        # Record the message
        conversation_id = str(uuid4())
        timestamp = datetime.now()

        query = """
        INSERT INTO meeting_conversations (
            conversation_id, meeting_id, sequence_number,
            timestamp, speaker_id, message, message_type, context
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """

        await self.db_client.execute(
            query,
            conversation_id,
            meeting_id,
            sequence_number,
            timestamp,
            speaker_id,
            message,
            message_type,
            json.dumps(context or {})
        )

        # Update in-memory tracking
        message_info = {
            "conversation_id": conversation_id,
            "sequence_number": sequence_number,
            "timestamp": timestamp,
            "speaker_id": speaker_id,
            "message": message,
            "message_type": message_type,
            "context": context
        }
        meeting_info["messages"].append(message_info)

        # Broadcast to all participants
        for agent_id in meeting_info["participants"]:
            if agent_id != speaker_id:  # Don't send back to speaker
                notification = self.comm_protocol.create_inform(
                    sender=speaker_id,
                    receiver=agent_id,
                    content=message,
                    metadata={
                        "meeting_id": meeting_id,
                        "conversation_id": conversation_id,
                        "sequence_number": sequence_number,
                        "message_type": message_type
                    }
                )

                # Store the notification
                self.logger.debug(f"Meeting message broadcast to {agent_id}")

        self.logger.info(f"Message recorded in meeting {meeting_id}: {sequence_number} from {speaker_id}")

        return message_info

    async def get_meeting_transcript(self, meeting_id: str) -> List[Dict[str, Any]]:
        """
        Get the transcript of a meeting.

        Args:
            meeting_id: ID of the meeting

        Returns:
            List of messages in sequence order
        """
        query = """
        SELECT
            conversation_id, sequence_number, timestamp,
            speaker_id, message, message_type, context
        FROM meeting_conversations
        WHERE meeting_id = $1
        ORDER BY sequence_number
        """

        results = await self.db_client.fetch_all(query, meeting_id)

        transcript = []
        for row in results:
            transcript.append({
                "conversation_id": row["conversation_id"],
                "sequence_number": row["sequence_number"],
                "timestamp": row["timestamp"],
                "speaker_id": row["speaker_id"],
                "message": row["message"],
                "message_type": row["message_type"],
                "context": json.loads(row["context"]) if row["context"] else {}
            })

        self.logger.info(f"Retrieved transcript for meeting {meeting_id}: {len(transcript)} messages")
        return transcript
```

### Task 4: Celery Task Queue Integration

**What needs to be done:**
Implement a Celery-based task queue for asynchronous processing of agent tasks.

**Why this task is necessary:**
A task queue enables parallel processing of agent tasks and ensures that long-running operations don't block the main application flow.

**Files to be created:**

- `agents/tasks/celery_app.py` - Celery application configuration
- `agents/tasks/agent_tasks.py` - Task definitions

**Implementation guidelines:**

```python
# agents/tasks/celery_app.py

import os
from celery import Celery

# Configure Celery application
app = Celery(
    'agent_tasks',
    broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    include=['agents.tasks.agent_tasks']
)

# Configure Celery settings
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1
)
```

```python
# agents/tasks/agent_tasks.py

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from celery import shared_task
from celery.utils.log import get_task_logger

from ..db.postgres import PostgresClient
from ..specialized.product_manager import ProductManagerAgent
from ..specialized.scrum_master import ScrumMasterAgent
from ..llm.anthropic_provider import AnthropicProvider
from ..memory.vector_memory import VectorMemory

# Set up task-specific logger
logger = get_task_logger(__name__)

# Helper function to create a runner for async tasks
def run_async(coroutine):
    """Run an async coroutine in a synchronous context."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine)

@shared_task
def analyze_requirements(project_description: str) -> Dict[str, Any]:
    """
    Analyze a project description and break it down into structured requirements.
    This is a Celery task wrapper around the ProductManagerAgent.analyze_requirements method.
    """
    logger.info(f"Starting requirement analysis for project")

    try:
        # Create necessary components
        db_client = PostgresClient()
        run_async(db_client.initialize())

        llm_provider = AnthropicProvider()

        vector_memory = VectorMemory(db_client)
        run_async(vector_memory.initialize())

        # Create the PM agent
        pm_agent = ProductManagerAgent(
            db_client=db_client,
            llm_provider=llm_provider,
            vector_memory=vector_memory
        )

        # Run the analysis
        result = run_async(pm_agent.analyze_requirements(project_description))

        # Clean up
        run_async(db_client.close())

        return result

    except Exception as e:
        logger.error(f"Error in requirement analysis task: {str(e)}")
        return {"error": str(e)}

@shared_task
def plan_sprint(backlog_items: list, sprint_duration_days: int = 14) -> Dict[str, Any]:
    """
    Plan a sprint based on backlog items.
    This is a Celery task wrapper around the ScrumMasterAgent.plan_sprint method.
    """
    logger.info(f"Starting sprint planning for {sprint_duration_days} days")

    try:
        # Create necessary components
        db_client = PostgresClient()
        run_async(db_client.initialize())

        llm_provider = AnthropicProvider()

        vector_memory = VectorMemory(db_client)
        run_async(vector_memory.initialize())

        # Create the Scrum Master agent
        sm_agent = ScrumMasterAgent(
            db_client=db_client,
            llm_provider=llm_provider,
            vector_memory=vector_memory
        )

        # Run the sprint planning
        result = run_async(sm_agent.plan_sprint(backlog_items, sprint_duration_days))

        # Clean up
        run_async(db_client.close())

        return result

    except Exception as e:
        logger.error(f"Error in sprint planning task: {str(e)}")
        return {"error": str(e)}

@shared_task
def assign_task(task_id: str, agent_id: str) -> Dict[str, Any]:
    """
    Assign a task to an agent.
    This is a Celery task wrapper around the ScrumMasterAgent.assign_task method.
    """
    logger.info(f"Assigning task {task_id} to agent {agent_id}")

    try:
        # Create necessary components
        db_client = PostgresClient()
        run_async(db_client.initialize())

        # Create the Scrum Master agent
        sm_agent = ScrumMasterAgent(db_client=db_client)

        # Assign the task
        result = run_async(sm_agent.assign_task(task_id, agent_id))

        # Clean up
        run_async(db_client.close())

        return {"success": result, "task_id": task_id, "agent_id": agent_id}

    except Exception as e:
        logger.error(f"Error in task assignment: {str(e)}")
        return {"error": str(e)}

@shared_task
def update_task_status(task_id: str, status: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Update the status of a task.
    This is a Celery task wrapper around the ScrumMasterAgent.update_task_status method.
    """
    logger.info(f"Updating task {task_id} status to {status}")

    try:
        # Create necessary components
        db_client = PostgresClient()
        run_async(db_client.initialize())

        # Create the Scrum Master agent
        sm_agent = ScrumMasterAgent(db_client=db_client)

        # Update the task status
        result = run_async(sm_agent.update_task_status(task_id, status, agent_id))

        # Clean up
        run_async(db_client.close())

        return {"success": result, "task_id": task_id, "status": status}

    except Exception as e:
        logger.error(f"Error in task status update: {str(e)}")
        return {"error": str(e)}
```

## Post-Implementation Verification

After completing all tasks, verify the implementation by:

1. Testing the PM agent's ability to analyze requirements
2. Testing the Scrum Master agent's sprint planning capabilities
3. Verifying that tasks can be created, assigned, and tracked
4. Testing the structured agent communication protocol with different message types
5. Verifying that virtual team meetings can be scheduled, conducted, and recorded
6. Testing the Celery task queue with asynchronous operations
7. Checking that all interactions are properly logged in the database

This phase establishes the coordination layer for our autonomous development team. With the PM and Scrum Master agents in place, a robust task queue system, and structured communication and meeting protocols, we now have the backbone for orchestrating complex software development workflows using agile methodologies.
