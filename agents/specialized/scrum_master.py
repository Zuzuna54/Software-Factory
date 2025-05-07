# agents/specialized/scrum_master.py

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4
from datetime import datetime, timedelta

from ..base_agent import BaseAgent


class ScrumMasterAgent(BaseAgent):
    """
    Scrum Master Agent - Responsible for coordinating the development process,
    managing task assignments, and tracking progress.
    """

    DEFAULT_CAPABILITIES = {
        "can_manage_sprints": True,
        "can_facilitate_meetings": True,
        "can_remove_impediments": True,
    }

    def __init__(self, **kwargs):
        """Initialize the Scrum Master Agent."""
        # Merge default capabilities
        capabilities = self.DEFAULT_CAPABILITIES.copy()
        if "capabilities" in kwargs:
            capabilities.update(kwargs["capabilities"])
        kwargs["capabilities"] = capabilities

        # Call superclass init, letting kwargs handle agent_type
        super().__init__(**kwargs)

        self.logger.info(
            f"ScrumMasterAgent {self.agent_id} ({self.agent_name}) initialized."
        )
        self.sprint_id = None
        # Placeholder for ceremony and meeting modules - these should be injected or initialized
        self.ceremonies = kwargs.get("ceremonies_module", None)
        self.meetings = kwargs.get("meetings_module", None)

    async def plan_sprint(
        self, project_id: str, sprint_duration_days: int = 14
    ) -> Dict[str, Any]:
        """
        Plan a sprint based on prioritized backlog items fetched by project_id.
        """
        # Fetch backlog items (Features and User Stories) from DB based on project_id
        if not self.db_client:
            self.logger.error("Database client not available for fetching backlog.")
            return {"error": "Database client not available."}

        backlog_query = """
        SELECT artifact_id, artifact_type, title, content, metadata, parent_id
        FROM artifacts
        WHERE project_id = $1 AND artifact_type IN ('Feature', 'UserStory')
        ORDER BY created_at ASC
        """
        try:
            db_results = await self.db_client.fetch_all(backlog_query, project_id)
            backlog_items = []
            stories_by_feature = {}
            features_map = {}

            # First pass: collect features and group stories
            for row in db_results:
                artifact_id = str(row["artifact_id"])
                metadata = json.loads(row["metadata"] or "{}")
                item = {
                    "id": artifact_id,
                    "title": row["title"],
                    "description": row["content"],
                    "priority": metadata.get("priority", "Medium"),
                    "estimate": metadata.get("estimate", "Medium"),
                    "complexity": metadata.get("complexity", "Medium"),
                    "dependencies": metadata.get("dependencies", []),
                }
                if row["artifact_type"] == "Feature":
                    item["user_stories"] = []
                    backlog_items.append(item)
                    features_map[artifact_id] = item
                elif row["artifact_type"] == "UserStory":
                    parent_id = str(row["parent_id"]) if row["parent_id"] else None
                    if parent_id:
                        if parent_id not in stories_by_feature:
                            stories_by_feature[parent_id] = []
                        item["as_a"] = metadata.get("as_a", "")
                        item["i_want"] = metadata.get("i_want", "")
                        item["so_that"] = metadata.get("so_that", "")
                        item["acceptance_criteria"] = metadata.get(
                            "acceptance_criteria", []
                        )
                        stories_by_feature[parent_id].append(item)

            # Second pass: attach stories to features
            for feature_id, stories in stories_by_feature.items():
                if feature_id in features_map:
                    features_map[feature_id]["user_stories"] = stories

        except Exception as e:
            self.logger.error(
                f"Failed to fetch backlog for project {project_id}: {e}", exc_info=True
            )
            return {"error": f"Failed to fetch backlog: {str(e)}"}

        # Original system message and prompt logic follows, using the fetched backlog_items
        system_message = """You are an expert Scrum Master meticulously planning a sprint.
        Your primary goal is to break down selected backlog items (Features and User Stories) into granular, actionable tasks suitable for different roles (Backend, Frontend, QA).

        Instructions:
        1. Review the provided 'Backlog Items to Consider'. Select items appropriate for the sprint duration, prioritizing based on metadata.
        2. For **EVERY** selected Feature AND **EVERY** selected User Story within that Feature, you **MUST** generate a list of detailed, specific, actionable tasks required to complete it.
        3. Tasks **MUST** be granular. Examples: "Implement GET /api/weather endpoint", "Design database schema for forecast data", "Create React component for current weather card", "Write Playwright tests for weather widget interaction", "Set up CI/CD pipeline for widget deployment".
        4. Tasks **MUST** be assigned to a specific role: "Backend", "Frontend", "QA", or "DevOps".
        5. The generated tasks **MUST** be included as a JSON list under a key named **EXACTLY** `"tasks"`. This `"tasks"` key **MUST** exist within **BOTH** the selected Feature object AND **EACH** selected User Story object in the final JSON output.
        6. **EACH** task object within the `"tasks"` list **MUST** contain the following keys:
           - `"title"`: (string) A concise, descriptive task title.
           - `"description"`: (string) A brief explanation of the task.
           - `"role"`: (string) The assigned role (e.g., "Backend", "Frontend", "QA", "DevOps").
           - `"estimate"`: (number) An estimated effort (e.g., hours or story points).
           - `"priority"`: (number) An integer representing priority (e.g., 1 for High, 2 for Medium, 3 for Low).

        7. Structure the response as a **single, valid JSON object**. The root object must contain `"sprint_name"`, `"duration"`, `"goal"`, and `"selected_items"`. The `"selected_items"` list contains Feature objects. Feature objects contain User Story objects in a `"user_stories"` list. **BOTH** Feature and User Story objects **MUST** contain the `"tasks"` list if tasks were generated for them.

        Example Snippet of Desired JSON Structure:
        ```json
        {
          "sprint_name": "Example Sprint",
          "duration": 7,
          "goal": "Achieve X and Y.",
          "selected_items": [
            {
              "id": "feature-id-1",
              "title": "Feature One",
              // ... other feature fields ...
              "tasks": [
                { "title": "Feature-level task 1", "description": "...", "role": "Backend", "estimate": 4, "priority": 1 },
                { "title": "Feature-level task 2", "description": "...", "role": "DevOps", "estimate": 2, "priority": 2 }
              ],
              "user_stories": [
                {
                  "id": "story-id-1a",
                  "title": "User Story 1a",
                  // ... other story fields ...
                  "tasks": [
                    { "title": "Story 1a task 1", "description": "...", "role": "Frontend", "estimate": 8, "priority": 1 },
                    { "title": "Story 1a task 2", "description": "...", "role": "QA", "estimate": 3, "priority": 2 }
                  ]
                }
              ]
            }
          ]
        }
        ```

        **CRITICAL**: Ensure the `"tasks"` list is populated correctly within **BOTH** features and user stories as shown in the example. If no items are selected for the sprint, return an empty sprint plan JSON as described in the prompt.
        Respond ONLY with the valid JSON object, enclosed in triple backticks like this:
        ```json
        { ... your JSON plan ... }
        ```"""

        prompt = f"""Backlog Items to Consider for Project ID '{project_id}':
        {json.dumps(backlog_items, indent=2)}

        Sprint Duration: {sprint_duration_days} days

        Please create a sprint plan selecting items that can be completed within the sprint duration.
        If the 'Backlog Items to Consider' list is empty, return a valid JSON object representing an empty sprint plan with an appropriate name, the specified duration, an empty goal, and an empty list for 'selected_items'.
        Ensure your entire response is ONLY the valid JSON object."""

        # Log that we're starting sprint planning
        await self.log_activity(
            activity_type="SprintPlanning",
            description=f"Planning {sprint_duration_days}-day sprint",
            input_data={"project_id": project_id},
        )

        # Use the LLM to plan the sprint
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during sprint planning: {error}")
            return {"error": error}

        # Extract JSON from the response
        self.logger.debug(
            f"Raw thought received: {thought[:500]}..."
        )  # Log raw LLM output
        try:
            # Find JSON content within ```json ... ``` blocks
            json_match = re.search(r"```json\n(.*)\n```", thought, re.DOTALL)
            if not json_match:
                # Fallback: try finding JSON object directly (less reliable)
                self.logger.warning(
                    "Could not find ```json block, attempting direct JSON parse."
                )
                start_idx = thought.find("{")
                end_idx = thought.rfind("}") + 1
                if start_idx == -1 or end_idx == 0:
                    raise ValueError(
                        "No JSON object or ```json block found in the response"
                    )
                json_str = thought[start_idx:end_idx]
            else:
                json_str = json_match.group(1).strip()

            self.logger.debug(f"Attempting to parse JSON: {json_str[:500]}...")
            sprint_plan = json.loads(json_str)
            self.logger.info("Successfully parsed sprint plan JSON from LLM response.")

            # Create a new sprint in the database
            sprint_id = await self._create_sprint(
                project_id, sprint_plan, sprint_duration_days
            )
            self.sprint_id = sprint_id

            # Create tasks for the sprint
            await self._create_sprint_tasks(sprint_id, sprint_plan)

            # Log the successful sprint planning
            await self.log_activity(
                activity_type="SprintPlanningComplete",
                description="Successfully planned sprint",
                output_data={
                    "sprint_id": sprint_id,
                    "task_count": sum(
                        len(feature.get("tasks", []))
                        for feature in sprint_plan.get("features", [])
                    ),
                },
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
                output_data={"error": str(e), "raw_result": thought},
            )

            return {"error": error_msg, "raw_response": thought}

    async def _create_sprint(
        self, project_id: str, sprint_plan: Dict[str, Any], duration_days: int
    ) -> str:
        """Create a new sprint in the database."""
        if not self.db_client:
            self.logger.warning(
                "No database client available, skipping sprint creation"
            )
            return str(uuid4())

        sprint_id = str(uuid4())
        start_date = datetime.now()
        end_date = start_date + timedelta(days=duration_days)

        query = """
        INSERT INTO sprints (
            sprint_id, project_id, sprint_name, start_date, end_date,
            goal, created_by, status
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """

        await self.db_client.execute(
            query,
            sprint_id,
            project_id,
            sprint_plan.get("sprint_name", f"Sprint {start_date.strftime('%Y-%m-%d')}"),
            start_date,
            end_date,
            sprint_plan.get("sprint_goal", ""),
            self.agent_id,
            "PLANNING",
        )

        return sprint_id

    async def _create_sprint_tasks(
        self, sprint_id: str, sprint_plan: Dict[str, Any]
    ) -> None:
        """Create tasks in the database for the sprint."""
        if not self.db_client:
            self.logger.warning("No database client available, skipping task creation")
            return

        # Collect all tasks from the sprint plan
        all_tasks = []
        self.logger.info(
            f"Starting task creation for sprint {sprint_id}. Parsing sprint plan: {json.dumps(sprint_plan, indent=2)}"
        )

        for feature in sprint_plan.get(
            "selected_items", []
        ):  # Changed from "features" to "selected_items"
            feature_id = feature.get("id")
            self.logger.debug(
                f"Processing feature '{feature.get('title')}' (ID: {feature_id}) for tasks."
            )

            # Add tasks from features directly
            for task_data in feature.get("tasks", []):
                self.logger.debug(
                    f"  Found task under feature: {task_data.get('title')}"
                )
                all_tasks.append(
                    {
                        "title": task_data.get("title", "Untitled Task"),
                        "description": task_data.get("description", ""),
                        "role": task_data.get("role", "Developer"),
                        "estimate": task_data.get("estimate", 1),
                        "priority": task_data.get("priority", "Medium"),
                        "related_artifact_id": feature_id,
                        "source": "feature_task",
                    }
                )

            # Add tasks from user stories
            for story in feature.get("user_stories", []):
                story_id = story.get("id")
                self.logger.debug(
                    f"  Processing user story '{story.get('title')}' (ID: {story_id}) under feature '{feature.get('title')}' for tasks."
                )

                for task_data in story.get("tasks", []):
                    self.logger.debug(
                        f"    Found task under user story: {task_data.get('title')}"
                    )
                    all_tasks.append(
                        {
                            "title": task_data.get("title", "Untitled Task"),
                            "description": task_data.get("description", ""),
                            "role": task_data.get("role", "Developer"),
                            "estimate": task_data.get("estimate", 1),
                            "priority": task_data.get("priority", "Medium"),
                            "related_artifact_id": story_id,
                            "source": "story_task",
                        }
                    )

        self.logger.info(
            f"Collected {len(all_tasks)} tasks to create for sprint {sprint_id}."
        )
        if not all_tasks:
            self.logger.warning(
                f"No tasks found in sprint plan for sprint {sprint_id}. Sprint plan details: {json.dumps(sprint_plan, indent=2)}"
            )
            return

        # Insert all tasks
        tasks_created_count = 0
        for i, task_detail in enumerate(all_tasks):
            task_id = str(uuid4())
            self.logger.debug(
                f"Attempting to create task {i+1}/{len(all_tasks)} (ID: {task_id}): {task_detail}"
            )

            query = """
            INSERT INTO tasks (
                task_id, title, description, created_at, created_by,
                sprint_id, priority, status, estimated_effort,
                related_artifacts
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """

            params = [
                task_id,
                task_detail["title"],
                task_detail["description"],
                datetime.now(),
                self.agent_id,
                sprint_id,
                task_detail["priority"],
                "BACKLOG",  # Default status
                task_detail["estimate"],
                (
                    [task_detail["related_artifact_id"]]
                    if task_detail.get("related_artifact_id")
                    else []
                ),
            ]

            self.logger.debug(
                f"Executing SQL for task {task_id}: Query='{query.strip()}', Params='{params}'"
            )

            try:
                await self.db_client.execute(query, *params)
                self.logger.info(
                    f"Successfully created task {task_id} ('{task_detail['title']}') for sprint {sprint_id}."
                )
                tasks_created_count += 1
            except Exception as e:
                self.logger.error(
                    f"Failed to create task {task_id} ('{task_detail['title']}') for sprint {sprint_id}. Error: {e}",
                    exc_info=True,
                )

        self.logger.info(
            f"Finished task creation attempt for sprint {sprint_id}. Successfully created {tasks_created_count}/{len(all_tasks)} tasks."
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
            output_data={"sprint_id": sprint_id},
        )

        # Announce sprint start to team
        # This would notify other agents that the sprint has started
        # For now, we'll just log it
        self.logger.info(f"Sprint {sprint_id} has started")

        return True

    async def assign_task(self, task_id: str, agent_id: str) -> bool:
        """Assign a task to an agent."""
        if not self.db_client:
            self.logger.warning(
                "No database client available, skipping task assignment"
            )
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
            output_data={"task_id": task_id, "agent_id": agent_id},
        )

        # Notify the assigned agent
        await self.send_message(
            receiver_id=agent_id,
            content=f"You have been assigned task {task_id}. Please begin work on it.",
            message_type="TASK_ASSIGNMENT",
            related_task_id=task_id,
        )

        return True

    async def update_task_status(
        self, task_id: str, status: str, agent_id: Optional[str] = None
    ) -> bool:
        """Update the status of a task."""
        if not self.db_client:
            self.logger.warning(
                "No database client available, skipping task status update"
            )
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
            output_data={"task_id": task_id, "status": status},
        )

        # Notify relevant agents if needed
        if agent_id:
            await self.send_message(
                receiver_id=agent_id,
                content=f"Task {task_id} status has been updated to {status}.",
                message_type="TASK_UPDATE",
                related_task_id=task_id,
            )

        return True

    async def get_sprint_status(
        self, sprint_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get the current status of a sprint."""
        if not self.db_client:
            self.logger.warning(
                "No database client available, skipping sprint status check"
            )
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
        progress_percent = (
            (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        )

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
            "progress_percent": progress_percent,
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
        if not self.ceremonies:
            self.logger.error("Ceremonies module not initialized or provided")
            return {"error": "Ceremonies module not initialized"}
        if not self.db_client:
            self.logger.error("DB client not available for scheduling ceremonies")
            return {"error": "DB client not available"}

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
        team_members = [
            str(row["agent_id"]) for row in team_results
        ]  # Convert UUIDs to strings

        # Get product manager
        pm_query = """
        SELECT agent_id FROM agents
        WHERE agent_type = 'product_manager'
        AND active = true
        LIMIT 1
        """

        pm_result = await self.db_client.fetch_one(pm_query)
        pm_id = (
            str(pm_result["agent_id"]) if pm_result else None
        )  # Convert UUID to string

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
            start_time=start_date,
        )

        # Schedule Daily Standups for each day of the sprint
        standup_ids = []
        current_date = start_date
        while current_date < end_date:
            # Schedule standup at a reasonable time, e.g., 9 AM
            standup_time = datetime(
                current_date.year, current_date.month, current_date.day, 9, 0, 0
            )
            if standup_time.weekday() < 5:  # Only schedule on weekdays
                standup_id = await self.ceremonies.schedule_daily_standup(
                    scrum_master_id=self.agent_id,
                    team_members=team_members,
                    start_time=standup_time,
                )
                standup_ids.append(standup_id)
            current_date = current_date + timedelta(days=1)

        # Schedule Sprint Review near end
        review_time = end_date - timedelta(hours=4)
        review_id = await self.ceremonies.schedule_sprint_review(
            scrum_master_id=self.agent_id,
            product_manager_id=pm_id,
            team_members=team_members,
            start_time=review_time,
        )

        # Schedule Sprint Retrospective after review
        retro_time = end_date - timedelta(hours=2)
        retro_id = await self.ceremonies.schedule_sprint_retrospective(
            scrum_master_id=self.agent_id,
            team_members=team_members,
            start_time=retro_time,
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
                "retro_id": retro_id,
            },
        )

        return {
            "sprint_id": sprint_id,
            "planning_id": planning_id,
            "standup_ids": standup_ids,
            "review_id": review_id,
            "retro_id": retro_id,
        }

    async def facilitate_standup(self, meeting_id: str) -> Dict[str, Any]:
        """
        Facilitate a daily standup meeting.

        Args:
            meeting_id: ID of the standup meeting to facilitate

        Returns:
            Meeting summary and action items
        """
        if not self.meetings:
            self.logger.error("Meetings module not initialized or provided")
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
            message_type="Facilitation",
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
                message_type="Question",
            )

            # Simulate some blockers and action items for demonstration
            if participant_id.endswith(
                "1"
            ):  # Just a way to simulate some agents having blockers
                blockers.append(
                    {
                        "agent_id": participant_id,
                        "description": "Waiting on dependency from another task",
                    }
                )
                action_items.append(
                    {
                        "description": f"Follow up with {participant_id} on dependency issue",
                        "assigned_to": self.agent_id,
                        "due_date": (datetime.now() + timedelta(days=1)).isoformat(),
                    }
                )

        # Send closing message
        await self.meetings.send_message_to_meeting(
            meeting_id=meeting_id,
            speaker_id=self.agent_id,
            message=f"Thank you everyone. I've noted {len(blockers)} blockers and {len(action_items)} action items that we'll follow up on after the meeting.",
            message_type="Facilitation",
        )

        # Generate meeting summary
        summary = f"Daily standup with {len(participants)} participants. {len(blockers)} blockers identified and {len(action_items)} action items created."

        # End the meeting
        end_result = await self.meetings.end_meeting(
            meeting_id=meeting_id,
            summary=summary,
            decisions={},
            action_items=action_items,
        )

        # Log the facilitation
        await self.log_activity(
            activity_type="StandupFacilitation",
            description=f"Facilitated standup meeting {meeting_id}",
            output_data={
                "meeting_id": meeting_id,
                "participant_count": len(participants),
                "blocker_count": len(blockers),
                "action_item_count": len(action_items),
            },
        )

        # Follow up on blockers
        for blocker in blockers:
            await self.send_message(
                receiver_id=blocker["agent_id"],
                content=f"I noticed you mentioned a blocker in standup: {blocker['description']}. Let me know if you need any help resolving this.",
                message_type="ALERT",
                metadata={"severity": "MEDIUM", "blocker_from_standup": True},
            )

        return {
            "meeting_id": meeting_id,
            "summary": summary,
            "blockers": blockers,
            "action_items": action_items,
        }
