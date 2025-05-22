import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
import uuid
import logging
import json
from typing import Dict, List, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# Agent and helper imports
from agents.specialized.product_manager import ProductManagerAgent
from agents.llm.vertex_gemini_provider import VertexGeminiProvider
from agents.db.postgres import PostgresClient
from agents.logging.activity_logger import (
    ActivityCategory,  # For log verification
    ActivityLevel,  # Added for min_log_level
)

# Database model imports
from infra.db.models import (
    Agent,
    AgentActivity,
    ProjectVision,
    RequirementsArtifact,
    Project,
    Base,  # Ensure Base is imported
    # Assuming ProjectRoadmap might be used or relevant, though not directly tested here
)
from infra.db.models.artifacts import (
    Artifact,
    DesignArtifact,
    FeatureArtifact,
    ImplementationArtifact,
    UserStoryArtifact,
    ProjectRoadmap,
)

# Configure basic logging for the script
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/software_factory"
TEST_PROJECT_ID = uuid.uuid4()  # Consistent Project ID for this test run
TEST_PROJECT_DESCRIPTION = (
    "Develop a next-generation AI-powered platform for automated cooking. "
    "The platform should allow users to select recipes, order ingredients, "
    "and have a robotic chef prepare the meals. Key features include "
    "a voice-controlled interface, dietary customization, and learning user preferences."
)


# --- Database Setup and Teardown (Adapted from verify_base_agent_refactor.py) ---
async def setup_test_database(db_url: str) -> PostgresClient:
    logger.info(f"Setting up test database client for: {db_url}")
    db = PostgresClient(database_url=db_url)
    async with db.engine.connect() as conn:
        # Drop all tables first to ensure a clean slate
        logger.info("Dropping all existing tables...")
        await conn.run_sync(Agent.metadata.drop_all)
        logger.info("All existing tables dropped.")

        # Create all tables based on the current model definitions
        logger.info("Creating all tables from metadata...")
        await conn.run_sync(Agent.metadata.create_all)
        # Removed checkfirst=True to ensure tables are (re)created as per models

        # No need to explicitly create other metadata sets if all models share the same Base.metadata
        await conn.commit()
    logger.info("Database client set up, all tables created.")
    return db


async def cleanup_test_database(db: PostgresClient):
    logger.info("Cleaning up test database client (disposing engine)...")
    if db and db.engine:
        await db.engine.dispose()
    logger.info("Test database cleaned up.")


# --- Main Verification Logic ---
async def verify_product_manager_agent_functionality():
    logger.info(
        f"Starting ProductManagerAgent verification for project_id: {TEST_PROJECT_ID}..."
    )
    db_client: Optional[PostgresClient] = None
    pm_agent: Optional[ProductManagerAgent] = None

    try:
        # 1. Initialize DB Client and LLM Provider
        db_client = await setup_test_database(TEST_DATABASE_URL)
        llm_provider = VertexGeminiProvider()  # Assumes it's configured
        logger.info("PostgresClient and VertexGeminiProvider initialized.")

        async with db_client.session() as session:  # This is the AsyncSession
            logger.info("Database session obtained.")

            # 2. Initialize ProductManagerAgent
            agent_id = uuid.uuid4()
            agent_name = "TestProductManagerAgent"
            pm_agent = ProductManagerAgent(
                agent_id=agent_id,
                agent_name=agent_name,
                db_session=session,
                db_client=db_client,
                llm_provider=llm_provider,
                min_log_level=ActivityLevel.DEBUG,  # Set min_log_level to DEBUG
            )
            await pm_agent.initialize()  # Register agent
            logger.info(
                f"ProductManagerAgent '{pm_agent.agent_name}' initialized with ID: {pm_agent.agent_id}"
            )

            # Verify agent creation in DB
            db_agent_record = await session.get(Agent, agent_id)
            assert db_agent_record is not None, f"Agent {agent_id} not found in DB."
            assert (
                db_agent_record.agent_name == agent_name
            ), "Agent name mismatch in DB."
            logger.info(f"Agent {agent_id} successfully created/verified in database.")

            # Create a Project record for the test
            test_project = Project(
                project_id=TEST_PROJECT_ID,
                name=f"Test Project {TEST_PROJECT_ID}",
                description=TEST_PROJECT_DESCRIPTION,
                created_by=agent_id,
            )
            session.add(test_project)
            await session.flush()  # Ensure it's persisted before artifact creation
            await session.commit()  # Commit to make it available for FK constraint
            logger.info(f"Test Project {TEST_PROJECT_ID} created in database.")

            # --- Test articulate_vision ---
            logger.info(f"Testing articulate_vision for project {TEST_PROJECT_ID}...")
            vision_context = {
                "target_market": "home_users",
                "strategic_goals": ["innovation", "market_disruption"],
            }
            vision_result = await pm_agent.articulate_vision(
                project_id=TEST_PROJECT_ID,
                project_description=TEST_PROJECT_DESCRIPTION,
                context=vision_context,
            )
            assert isinstance(
                vision_result, dict
            ), "articulate_vision should return a dict."
            assert (
                "vision_statement" in vision_result
            ), "Vision result missing 'vision_statement'."
            assert (
                len(vision_result["vision_statement"]) > 0
            ), "Vision statement is empty."
            logger.info(
                f"articulate_vision returned: {vision_result.get('vision_statement', '')[:100]}..."
            )

            # Verify ProjectVision in DB
            pv_stmt = select(ProjectVision).where(
                ProjectVision.project_id == TEST_PROJECT_ID
            )
            pv_record = (await session.execute(pv_stmt)).scalar_one_or_none()
            assert pv_record is not None, "ProjectVision record not found in DB."
            assert (
                pv_record.vision_statement == vision_result["vision_statement"]
            ), "Vision statement mismatch in DB."
            assert (
                pv_record.created_by == agent_id
            ), "ProjectVision created_by mismatch."
            logger.info(
                f"ProjectVision record for project {TEST_PROJECT_ID} verified in DB."
            )

            # Verify Activity Log for vision articulation
            # (Simplified check, more specific checks can be added)
            vision_activity_stmt = select(AgentActivity).where(
                AgentActivity.agent_id == agent_id,
                AgentActivity.activity_type == "vision_articulation_completed",
            )
            vision_log = (await session.execute(vision_activity_stmt)).scalars().first()
            assert (
                vision_log is not None
            ), "vision_articulation_completed activity not logged."
            assert vision_log.input_data["project_id"] == str(
                TEST_PROJECT_ID
            ), "Logged project_id mismatch."
            logger.info("vision_articulation_completed activity verified.")

            # --- Test analyze_requirements ---
            logger.info(
                f"Testing analyze_requirements for project {TEST_PROJECT_ID}..."
            )
            requirements_context = {
                "source": "Initial client brief",
                "stakeholders": ["CEO", "Lead Engineer"],
            }
            requirements_result = await pm_agent.analyze_requirements(
                description=TEST_PROJECT_DESCRIPTION,
                project_id=TEST_PROJECT_ID,
                context=requirements_context,
            )
            assert isinstance(
                requirements_result, dict
            ), "analyze_requirements should return a dict."
            assert (
                "requirements" in requirements_result
            ), "Requirements result missing 'requirements' key."
            assert isinstance(
                requirements_result["requirements"], dict
            ), "'requirements' should be a dict."
            logger.info(
                f"analyze_requirements returned {sum(len(v) for v in requirements_result['requirements'].values())} requirement items."
            )

            # Verify RequirementsArtifact (type="Requirement") in DB
            req_stmt = select(RequirementsArtifact).where(
                RequirementsArtifact.project_id == TEST_PROJECT_ID
            )
            req_records = (await session.execute(req_stmt)).scalars().all()
            assert len(req_records) > 0, "No Requirement artifacts found in DB."
            logger.info(
                f"Found {len(req_records)} Requirement artifacts in DB for project {TEST_PROJECT_ID}."
            )
            # Add more specific checks on req_records content if needed

            # --- Test create_user_stories ---
            logger.info(f"Testing create_user_stories for project {TEST_PROJECT_ID}...")
            # Assume requirements_result holds the output from analyze_requirements
            user_stories_result = await pm_agent.create_user_stories(
                requirements=requirements_result,  # Use output from previous step
                project_id=TEST_PROJECT_ID,
            )
            assert isinstance(
                user_stories_result, list
            ), "create_user_stories should return a list."
            assert len(user_stories_result) > 0, "No user stories were created."
            first_story = user_stories_result[0]
            assert (
                "title" in first_story and "description" in first_story
            ), "User story missing title or description."
            logger.info(
                f"create_user_stories created {len(user_stories_result)} user stories. First story: '{first_story['title']}'"
            )

            # Verify RequirementsArtifact (type="UserStory") in DB
            us_stmt = select(UserStoryArtifact).where(
                UserStoryArtifact.project_id == TEST_PROJECT_ID
            )
            us_records = (await session.execute(us_stmt)).scalars().all()
            assert len(us_records) == len(
                user_stories_result
            ), "Mismatch in number of UserStory artifacts in DB."
            logger.info(
                f"Found {len(us_records)} UserStory artifacts in DB for project {TEST_PROJECT_ID}."
            )

            # --- Test define_acceptance_criteria ---
            if us_records:  # Proceed if user stories were created and found
                target_user_story_record = us_records[0]
                target_user_story_id = target_user_story_record.artifact_id
                target_user_story_description = target_user_story_record.content
                logger.info(
                    f"Testing define_acceptance_criteria for user story {target_user_story_id}..."
                )

                ac_result = await pm_agent.define_acceptance_criteria(
                    user_story_id=target_user_story_id,
                    user_story_description=target_user_story_description,
                )
                assert isinstance(
                    ac_result, list
                ), "define_acceptance_criteria should return a list."
                assert len(ac_result) > 0, "No acceptance criteria were defined."
                first_ac = ac_result[0]
                assert (
                    "title" in first_ac and "then" in first_ac
                ), "Acceptance criterion missing title or 'then' clause."
                logger.info(
                    f"define_acceptance_criteria defined {len(ac_result)} ACs. First AC: '{first_ac['title']}'"
                )

                # Verify RequirementsArtifact.acceptance_criteria in DB
                await session.refresh(
                    target_user_story_record
                )  # Refresh to get latest data
                assert (
                    target_user_story_record.acceptance_criteria is not None
                ), "Acceptance criteria not saved to DB."
                assert len(target_user_story_record.acceptance_criteria) == len(
                    ac_result
                ), "Mismatch in AC count in DB."
                logger.info(
                    f"Acceptance criteria for user story {target_user_story_id} verified in DB."
                )
            else:
                logger.warning(
                    "Skipping define_acceptance_criteria test as no user stories were available."
                )

            # --- Test prioritize_features ---
            logger.info(f"Testing prioritize_features for project {TEST_PROJECT_ID}...")

            mock_features_for_prioritization_input = []
            if not pm_agent.db_session:
                raise RuntimeError(
                    "Product manager's db_session is not initialized before prioritize_features test."
                )

            agent_id_for_artifacts = pm_agent.agent_id
            assert (
                agent_id_for_artifacts is not None
            ), "Agent ID is None, cannot create artifacts."

            async with (
                pm_agent.db_session.begin_nested()
                if pm_agent.db_session.in_transaction()
                else pm_agent.db_session.begin()
            ):
                for i in range(3):
                    feature = FeatureArtifact(
                        project_id=TEST_PROJECT_ID,
                        title=f"Mock Feature {i+1} for Prioritization",
                        description=f"This is mock feature {i+1} to be prioritized.",
                        status="pending",
                        priority=0,
                        created_by=agent_id_for_artifacts,
                        content="{}",  # Added default content
                    )
                    pm_agent.db_session.add(feature)
                await pm_agent.db_session.commit()  # Commit to get IDs

            # Query them back using the agent's session to ensure they have IDs
            stmt = (
                select(FeatureArtifact)
                .where(
                    FeatureArtifact.project_id == TEST_PROJECT_ID,
                    FeatureArtifact.title.like("Mock Feature % for Prioritization"),
                )
                .order_by(FeatureArtifact.title)
            )
            result = await pm_agent.db_session.execute(stmt)
            mock_features_for_prioritization_input = result.scalars().all()

            print(
                f"DEBUG: Retrieved {len(mock_features_for_prioritization_input)} mock features for prioritization input:"
            )
            for f in mock_features_for_prioritization_input:
                print(
                    f"DEBUG: - ID: {f.artifact_id}, Title: {f.title}, Status: {f.status}"
                )

            if len(mock_features_for_prioritization_input) != 3:
                all_features_stmt = select(FeatureArtifact).where(
                    FeatureArtifact.project_id == TEST_PROJECT_ID
                )
                all_features_result = await pm_agent.db_session.execute(
                    all_features_stmt
                )
                all_project_features = all_features_result.scalars().all()
                print(
                    f"DEBUG: All features in DB for project {TEST_PROJECT_ID} after attempting to create mocks: {len(all_project_features)}"
                )
                for f_db in all_project_features:
                    print(
                        f"DEBUG:   - DB ID: {f_db.artifact_id}, Title: {f_db.title}, Status: {f_db.status}"
                    )
                raise AssertionError(
                    f"Failed to create/retrieve the 3 mock features. Expected 3, got {len(mock_features_for_prioritization_input)}."
                )

            print(
                f"INFO: Passing {len(mock_features_for_prioritization_input)} mock features to prioritize_features via features_arg."
            )
            prioritized_features_result = await pm_agent.prioritize_features(
                project_id=TEST_PROJECT_ID,
                features_arg=mock_features_for_prioritization_input,  # Pass the ORM objects
                prioritization_criteria={"focus": "user_impact"},  # Example criteria
            )
            assert isinstance(
                prioritized_features_result, list
            ), "prioritize_features should return a list."

            print(
                f"DEBUG: prioritize_features returned {len(prioritized_features_result)} features."
            )
            for pf in prioritized_features_result:
                print(
                    f"DEBUG: - Prioritized: ID {pf.get('id')}, Title {pf.get('title')}, Rank {pf.get('extra_data', {}).get('prioritization', {}).get('rank')}"
                )

            assert len(prioritized_features_result) == len(
                mock_features_for_prioritization_input
            ), f"Mismatch in prioritized feature count. Expected {len(mock_features_for_prioritization_input)}, got {len(prioritized_features_result)}"
            if prioritized_features_result:
                assert "rank" in prioritized_features_result[0].get(
                    "extra_data", {}
                ).get("prioritization", {}), "Prioritized feature missing rank."
            logger.info(
                f"prioritize_features returned {len(prioritized_features_result)} prioritized features."
            )

            # Verify RequirementsArtifact (type="Feature") priorities and extra_data in DB
            # Ranks should be 1, 2, 3...
            for i, pf in enumerate(
                sorted(
                    prioritized_features_result,
                    key=lambda x: x.get("extra_data", {})
                    .get("prioritization", {})
                    .get("rank"),
                )
            ):
                feature_id = uuid.UUID(pf["id"])
                db_feature = await session.get(FeatureArtifact, feature_id)
                assert (
                    db_feature is not None
                ), f"Feature {feature_id} not found after prioritization."
                assert db_feature.priority == (
                    i + 1
                ), f"Feature {feature_id} DB priority incorrect after prioritization."
                assert (
                    "prioritization" in db_feature.extra_data
                ), "Prioritization details missing in DB extra_data."
            logger.info(
                f"Feature priorities and extra_data verified in DB for project {TEST_PROJECT_ID}."
            )

            # --- Test think method ---
            logger.info("Testing ProductManagerAgent.think()...")
            think_contexts = [
                {
                    "thought_type": "requirement_analysis",
                    "summary": "Analyze new mobile app idea",
                    "query": "mobile app requirements",
                },
                {
                    "thought_type": "user_story_creation",
                    "summary": "Create stories for login module",
                    "query": "user login stories",
                },
                {
                    "thought_type": "general_product_management",
                    "summary": "General PM reflection",
                    "query": "market trends",
                },
            ]
            for i, think_context in enumerate(think_contexts):
                logger.info(
                    f"Running think test case {i+1} ({think_context['thought_type']})..."
                )
                think_result = await pm_agent.think(context=think_context)
                assert isinstance(think_result, dict), "think() should return a dict."
                assert (
                    "thought_process" in think_result
                ), "Think result missing 'thought_process'."
                assert think_result["thought_process"].startswith(
                    "Product Management:"
                ), "Thought process prefix mismatch."
                logger.info(
                    f"think() for '{think_context['thought_type']}' returned: {think_result['decision']}"
                )

                # Verify think activity logs (simplified)
                think_activity_stmt = (
                    select(AgentActivity)
                    .where(
                        AgentActivity.agent_id == agent_id,
                        AgentActivity.activity_type
                        == f"pm_thinking_{think_context['thought_type']}_completed",
                    )
                    .order_by(AgentActivity.timestamp.desc())
                )  # Get the latest one

                think_log = (
                    (await session.execute(think_activity_stmt)).scalars().first()
                )
                assert think_log is not None, "Thinking activity log not found."
                assert (
                    think_log.input_data["thought_type"]
                    == think_context["thought_type"]
                ), f"Expected thought_type {think_context['thought_type']}, got {think_log.input_data.get('thought_type')}"
                assert (
                    think_log.input_data["decision"]
                    == "Plan generated for product management task"
                ), f"Expected decision 'Plan generated for product management task', got {think_log.input_data.get('decision')}"
                logger.info(
                    f"Think activity for '{think_context['thought_type']}' verified."
                )

            logger.info("All ProductManagerAgent verifications passed!")

    except Exception as e:
        logger.error(f"ProductManagerAgent verification failed: {e}", exc_info=True)
        raise  # Re-raise to fail the script run if an assertion or error occurs
    finally:
        if db_client:
            await cleanup_test_database(db_client)
        logger.info("ProductManagerAgent verification script finished.")


if __name__ == "__main__":
    # Note: Ensure PostgreSQL server is running and accessible via TEST_DATABASE_URL
    # and the database specified in TEST_DATABASE_URL exists.
    asyncio.run(verify_product_manager_agent_functionality())
