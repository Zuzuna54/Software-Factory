# agents/specialized/product_manager.py

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

from ..base_agent import BaseAgent
from ..memory.vector_memory import EnhancedVectorMemory


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
                "project_vision": True,
            },
            **kwargs,
        )
        self.logger = logging.getLogger(f"agent.pm.{self.agent_id}")
        self.vector_memory: Optional[EnhancedVectorMemory] = self.vector_memory

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
            input_data={"project_description": project_description},
        )

        # Use the LLM to analyze requirements
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during requirement analysis: {error}")
            return {"error": error}

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find("{")
            end_idx = thought.rfind("}") + 1

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
                output_data={
                    "requirements_summary": {
                        "vision": requirements.get("vision", ""),
                        "feature_count": len(requirements.get("features", [])),
                        "story_count": sum(
                            len(f.get("user_stories", []))
                            for f in requirements.get("features", [])
                        ),
                    }
                },
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
                output_data={"error": str(e), "raw_result": thought},
            )

            return {"error": error_msg, "raw_response": thought}

    async def _store_requirements(self, requirements: Dict[str, Any]) -> None:
        """Store the analyzed requirements in the database."""
        if not self.db_client:
            self.logger.warning(
                "No database client available, skipping requirement storage"
            )
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
            "ACTIVE",
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
                json.dumps(
                    {
                        "priority": feature.get("priority", "Medium"),
                        "complexity": feature.get("complexity", "Medium"),
                        "dependencies": feature.get("dependencies", []),
                    }
                ),
                1,
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
                    json.dumps(
                        {
                            "as_a": story.get("as_a", ""),
                            "i_want": story.get("i_want", ""),
                            "so_that": story.get("so_that", ""),
                            "acceptance_criteria": story.get("acceptance_criteria", []),
                            "priority": story.get("priority", "Medium"),
                            "estimate": story.get("estimate", "Medium"),
                        }
                    ),
                    feature_id,  # Parent is the feature
                    1,
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
                json.dumps(
                    {
                        "category": nfr.get("category", "Other"),
                        "priority": nfr.get("priority", "Medium"),
                        "metrics": nfr.get("metrics", []),
                    }
                ),
                1,
            )

    async def prioritize_backlog(self, project_id: str) -> List[Dict[str, Any]]:
        """Prioritize the product backlog based on value, risk, and dependencies."""
        if not self.db_client:
            self.logger.warning(
                "No database client available, skipping backlog prioritization"
            )
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
                metadata = (
                    json.loads(artifact["metadata"]) if artifact["metadata"] else {}
                )

                features.append(
                    {
                        "id": feature_id,
                        "title": artifact["title"],
                        "description": artifact["content"],
                        "priority": metadata.get("priority", "Medium"),
                        "complexity": metadata.get("complexity", "Medium"),
                        "dependencies": metadata.get("dependencies", []),
                    }
                )

                stories_by_feature[feature_id] = []

            elif artifact["artifact_type"] == "UserStory":
                feature_id = artifact["parent_id"]
                if feature_id:
                    metadata = (
                        json.loads(artifact["metadata"]) if artifact["metadata"] else {}
                    )

                    if feature_id not in stories_by_feature:
                        stories_by_feature[feature_id] = []

                    stories_by_feature[feature_id].append(
                        {
                            "id": artifact["artifact_id"],
                            "title": artifact["title"],
                            "description": artifact["content"],
                            "as_a": metadata.get("as_a", ""),
                            "i_want": metadata.get("i_want", ""),
                            "so_that": metadata.get("so_that", ""),
                            "priority": metadata.get("priority", "Medium"),
                            "estimate": metadata.get("estimate", "Medium"),
                        }
                    )

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
            input_data={"feature_count": len(features)},
        )

        # Use the LLM to prioritize
        thought, error = await self.think(prompt, system_message)

        if error:
            self.logger.error(f"Error during backlog prioritization: {error}")
            return []

        # Extract JSON from the response
        try:
            # Find JSON content in the response
            start_idx = thought.find("{")
            end_idx = thought.rfind("}") + 1

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
                output_data={
                    "prioritized_features": len(prioritized.get("features", []))
                },
            )

            return prioritized.get("features", [])

        except (json.JSONDecodeError, ValueError) as e:
            error_msg = f"Error parsing backlog prioritization: {str(e)}"
            self.logger.error(error_msg)

            # Log the error
            await self.log_activity(
                activity_type="BacklogPrioritizationError",
                description="Failed to parse backlog prioritization result",
                output_data={"error": str(e), "raw_result": thought},
            )

            return []

    async def _update_priorities(self, prioritized_backlog: Dict[str, Any]) -> None:
        """Update priorities in the database based on the prioritization results."""
        if not self.db_client:
            self.logger.warning(
                "No database client available, skipping priority updates"
            )
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
            metadata["priority"] = feature.get(
                "priority", metadata.get("priority", "Medium")
            )
            metadata["business_value"] = feature.get(
                "business_value", metadata.get("business_value", "Medium")
            )
            metadata["technical_risk"] = feature.get(
                "technical_risk", metadata.get("technical_risk", "Medium")
            )

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
                metadata["priority"] = story.get(
                    "priority", metadata.get("priority", "Medium")
                )

                # Save updated metadata
                update_query = (
                    "UPDATE artifacts SET metadata = $1 WHERE artifact_id = $2"
                )
                await self.db_client.execute(
                    update_query, json.dumps(metadata), story_id
                )
