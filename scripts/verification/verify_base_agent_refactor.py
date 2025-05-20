import asyncio
import uuid
import logging
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from agents.base_agent import BaseAgent
from agents.llm.vertex_gemini_provider import VertexGeminiProvider
from agents.memory.vector_memory import MemoryItem
from agents.db.postgres import PostgresClient
from agents.communication.message import MessageType

from infra.db.models import (
    Agent,
    AgentActivity,
    AgentMessage,
    Project as DBProject,  # Alias to avoid conflict if Project is used elsewhere
)  # For verification queries

# Configure basic logging for the script
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration ---
# Replace with your actual database URL or load from environment
TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost/software_factory"
# Note: For a real test, ensure this user/password/db exists or use a disposable one.


# --- Database Setup and Teardown ---
async def setup_test_database(db_url: str) -> PostgresClient:
    """Sets up a test database client and ensures tables exist."""
    logger.info(f"Setting up test database client for: {db_url}")
    db = PostgresClient(database_url=db_url)

    async with db.engine.connect() as conn:
        logger.info("Ensuring all tables from metadata exist (checkfirst=True)...")
        # Create tables if they don't exist, without dropping anything.
        await conn.run_sync(Agent.metadata.create_all, checkfirst=True)
        await conn.commit()

    logger.info("Database client set up, tables ensured.")
    return db


async def cleanup_test_database(db: PostgresClient):
    """Cleans up the test database client by disposing the engine."""
    logger.info("Cleaning up test database client (disposing engine)...")
    if db and db.engine:
        await db.engine.dispose()
    logger.info("Test database cleaned up.")


# --- Main Verification Logic ---
async def verify_base_agent():
    logger.info("Starting BaseAgent refactor verification...")

    db_client: Optional[PostgresClient] = None
    try:
        # 1. Initialize DB Client
        db_client = await setup_test_database(TEST_DATABASE_URL)

        async with db_client.session() as session:  # This is the AsyncSession
            logger.info("Database session obtained.")

            # 2. Initialize DummyLLMProvider
            llm_provider = VertexGeminiProvider()
            logger.info("DummyLLMProvider initialized.")

            # 3. Create a dummy Project for context if it doesn't exist
            dummy_project_id = uuid.uuid4()
            dummy_project_name = f"TestProject-{dummy_project_id}"
            # Define a fixed system/test agent ID for creating the project
            test_system_agent_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

            # Ensure the system agent exists, or create a placeholder one if necessary for FK constraint
            system_agent = await session.get(Agent, test_system_agent_id)
            if not system_agent:
                logger.info(
                    f"Creating placeholder system agent {test_system_agent_id} for project creation."
                )
                placeholder_agent = Agent(
                    agent_id=test_system_agent_id,
                    agent_name="SystemTestAgent",
                    agent_type="system",
                    agent_role="system utility agent for tests",
                    status="active",
                )
                session.add(placeholder_agent)
                # We will commit this along with the project, or rely on agent1.initialize() to create it if it is the same ID.
                # For safety, committing it here if it's a dedicated system agent ID.
                try:
                    await session.commit()  # Commit system agent first
                except Exception as e_sys_agent:
                    logger.error(
                        f"Failed to commit placeholder system agent: {e_sys_agent}"
                    )
                    await session.rollback()
                    raise

            existing_project = await session.get(DBProject, dummy_project_id)
            if not existing_project:
                # Check if a project with that name exists to avoid unique constraint errors if re-running
                project_by_name_stmt = select(DBProject).where(
                    DBProject.name == dummy_project_name
                )
                res_project_by_name = await session.execute(project_by_name_stmt)
                existing_project_by_name = res_project_by_name.scalar_one_or_none()

                if existing_project_by_name:
                    dummy_project_id = existing_project_by_name.project_id
                    logger.info(
                        f"Using existing Project '{dummy_project_name}' with ID: {dummy_project_id}"
                    )
                else:
                    logger.info(
                        f"Creating dummy Project '{dummy_project_name}' with ID: {dummy_project_id}"
                    )
                    new_project = DBProject(
                        project_id=dummy_project_id,
                        name=dummy_project_name,
                        description="Temporary project for verification script.",
                        created_by=test_system_agent_id,  # Use the defined system/test agent ID
                    )
                    session.add(new_project)
                    try:
                        await session.commit()
                        logger.info(
                            f"Dummy Project {dummy_project_id} created and committed."
                        )
                    except Exception as e_proj:
                        logger.error(f"Failed to commit dummy project: {e_proj}")
                        await session.rollback()  # Rollback if project creation failed
                        raise  # Re-raise to signal a setup problem
            else:
                logger.info(f"Dummy Project {dummy_project_id} already exists.")

            # 4. Initialize BaseAgent
            agent1_id = uuid.uuid4()
            agent1_name = "TestAgentAlpha"
            agent1 = BaseAgent(
                agent_id=agent1_id,
                agent_name=agent1_name,
                agent_type="verifier",
                agent_role="Performs verification tasks",
                capabilities=["test", "verify"],
                system_prompt="You are a helpful verification agent.",
                db_session=session,  # Pass the AsyncSession
                db_client=db_client,  # Pass the PostgresClient instance
                llm_provider=llm_provider,
            )
            await agent1.initialize()
            logger.info(
                f"BaseAgent '{agent1.agent_name}' initialized and registered with ID: {agent1.agent_id}"
            )
            assert (
                agent1.vector_memory is not None
            ), "VectorMemory was not initialized in BaseAgent"
            logger.info("VectorMemory successfully initialized within BaseAgent.")

            # Verify agent creation in DB
            db_agent = await session.get(Agent, agent1_id)
            assert (
                db_agent is not None
            ), f"Agent {agent1_id} not found in DB after async initialize()"
            assert db_agent.agent_name == agent1_name, "Agent name mismatch in DB"
            logger.info(f"Agent {agent1_id} successfully created/verified in database.")

            # Verify agent_initialized_and_registered activity log
            activity_log_stmt = select(AgentActivity).where(
                AgentActivity.agent_id == agent1_id,
                AgentActivity.activity_type == "agent_initialized_and_registered",
            )
            activity_log_res = await session.execute(activity_log_stmt)
            agent_init_log = activity_log_res.scalar_one_or_none()
            assert (
                agent_init_log is not None
            ), "'agent_initialized_and_registered' activity not logged."
            logger.info(
                "'agent_initialized_and_registered' activity successfully logged."
            )

            # 5. Test VectorMemory integration (store and retrieve)
            logger.info("Testing VectorMemory integration (store and retrieve)...")
            test_memory_content = "This is a test memory item for verification."
            memory_item = MemoryItem(
                content=test_memory_content,
                category="test_category",
                tags=["verify", "refactor"],
                importance=0.8,
                metadata={
                    "project_id": dummy_project_id
                },  # Pass project_id in metadata
            )
            stored_ids = await agent1.store_memory_item(memory_item)
            assert (
                stored_ids is not None and len(stored_ids) > 0
            ), "Failed to store memory item."
            logger.info(f"MemoryItem stored with ID(s): {stored_ids}")

            retrieved_memories = await agent1.retrieve_memories(
                query_text="test memory"
            )
            assert isinstance(
                retrieved_memories, list
            ), "retrieve_memories should return a list."
            # Exact match depends on dummy LLM and similarity; here we check if the call works
            # and if the stored item might be among those retrieved (VectorMemory might return other items too)
            if retrieved_memories:
                logger.info(
                    f"Retrieved {len(retrieved_memories)} memories. First one: {retrieved_memories[0].content[:50]}..."
                )
            else:
                logger.info(
                    "No memories retrieved for 'test memory' (might be OK with dummy embeddings)."
                )
            logger.info("VectorMemory store/retrieve methods called successfully.")

            # 6. Test think()
            logger.info("Testing agent.think()...")
            think_context = {
                "summary": "Test thinking context",
                "type": "verification_think",
            }
            think_result = await agent1.think(context=think_context)
            assert isinstance(think_result, dict), "agent.think() should return a dict."
            assert (
                think_result.get("decision") == "No decision made"
            ), "Default think decision incorrect."
            logger.info(
                f"agent.think() completed. Result: {think_result.get('decision')}"
            )

            # Verify thinking_started and thinking_completed logs
            thinking_started_stmt = select(AgentActivity).where(
                AgentActivity.agent_id == agent1_id,
                AgentActivity.activity_type == "thinking_generic_think_start",
            )
            thinking_started_log = (
                await session.execute(thinking_started_stmt)
            ).scalar_one_or_none()
            assert (
                thinking_started_log is not None
            ), "'thinking_generic_think_start' activity not logged."
            assert (
                thinking_started_log.thought_process
                == "Agent is about to execute its think method."
            ), "Logged thought_process mismatch"

            thinking_completed_stmt = select(AgentActivity).where(
                AgentActivity.agent_id == agent1_id,
                AgentActivity.activity_type == "thinking_completed",
            )
            thinking_completed_log = (
                await session.execute(thinking_completed_stmt)
            ).scalar_one_or_none()
            assert (
                thinking_completed_log is not None
            ), "'thinking_completed' activity not logged."
            logger.info("Thinking process activities logged successfully.")

            # 7. Test Communication (send_message, receive_message)
            logger.info("Testing communication (send_message, receive_message)...")
            # Setup a second agent for receiving messages
            agent2_id = uuid.uuid4()
            agent2 = BaseAgent(
                agent_id=agent2_id,
                agent_name="TestAgentBeta",
                db_session=session,  # Pass the AsyncSession
                db_client=db_client,  # Pass the PostgresClient instance
                llm_provider=llm_provider,
            )
            await agent2.initialize()
            logger.info(
                f"Initialized and registered TestAgentBeta (ID: {agent2_id}) for communication tests."
            )

            test_message_content = "Hello from TestAgentAlpha to TestAgentBeta!"
            message_id = await agent1.send_message(
                receiver_id=agent2_id,
                content=test_message_content,
                message_type="REQUEST",  # Using a string, BaseAgent converts to Enum
                extra_data={"test_key": "test_value"},
            )
            assert message_id is not None, "send_message did not return a message_id."
            logger.info(f"Message sent from agent1 with ID: {message_id}")

            # Verify message in DB (via Protocol's storage)
            db_message = await session.get(AgentMessage, message_id)
            assert db_message is not None, f"Message {message_id} not found in DB."
            assert (
                db_message.content == test_message_content
            ), "Message content mismatch in DB."
            assert db_message.sender_id == agent1_id, "Message sender_id mismatch."
            assert (
                db_message.message_type == MessageType.REQUEST.value
            ), "Message type mismatch in DB."
            logger.info(f"Message {message_id} verified in database.")

            # Verify message_sent activity log
            msg_sent_log_stmt = select(AgentActivity).where(
                AgentActivity.agent_id == agent1_id,
                AgentActivity.input_data["message_id"].astext == str(message_id),
            )  # Check based on metadata in log_communication
            msg_sent_log = (
                await session.execute(msg_sent_log_stmt)
            ).scalar_one_or_none()
            # The actual activity_type will be 'communication'
            # The message_type in input_data for log_communication will be the specific type like "REQUEST"
            assert (
                msg_sent_log is not None
            ), "'message_sent' (communication) activity not logged."
            assert msg_sent_log.input_data["message_type"] == MessageType.REQUEST.value
            logger.info("'message_sent' activity logged successfully.")

            # Test receive_message on agent2
            logger.info(
                f"Agent2 attempting to receive message ID: {message_id} (type: {type(message_id)})"
            )
            received_message_obj = await agent2.receive_message(message_id)
            assert (
                received_message_obj is not None
            ), "agent2.receive_message did not return a message object."

            logger.info(
                f"Original sent message ID: {message_id} (type: {type(message_id)})"
            )
            logger.info(
                f"Received message object ID: {received_message_obj.message_id} (type: {type(received_message_obj.message_id)})"
            )

            assert (
                received_message_obj.message_id
                == message_id  # message_id should now be a string
            ), "Received message ID mismatch."
            assert (
                received_message_obj.content == test_message_content
            ), "Received message content mismatch."
            logger.info(
                f"Agent2 successfully received message: {received_message_obj.message_id}"
            )

            # Verify message_received activity log for agent2
            msg_received_log_stmt = select(AgentActivity).where(
                AgentActivity.agent_id == agent2_id,
                AgentActivity.input_data["message_id"].astext == str(message_id),
                AgentActivity.input_data["message_type"].astext
                == f"RECEIVED_{MessageType.REQUEST.value}",
            )
            msg_received_log = (
                await session.execute(msg_received_log_stmt)
            ).scalar_one_or_none()
            assert (
                msg_received_log is not None
            ), "'message_received' (communication) activity not logged for agent2."
            logger.info("'message_received' activity logged successfully for agent2.")

            # 8. Test _with_retry (simplified conceptual test)
            logger.info("Testing _with_retry (conceptual)...")

            class RetryTester:
                def __init__(self):
                    self.attempts = 0

                async def op_that_fails_then_succeeds(self, fail_times: int):
                    self.attempts += 1
                    if self.attempts <= fail_times:
                        logger.info(
                            f"RetryTester.op_that_fails_then_succeeds: Failing (attempt {self.attempts})"
                        )
                        raise ValueError(
                            f"Simulated failure on attempt {self.attempts}"
                        )
                    logger.info(
                        f"RetryTester.op_that_fails_then_succeeds: Succeeded on attempt {self.attempts}"
                    )
                    return "Success"

            retry_tester = RetryTester()
            agent1.max_retries = 3  # Ensure it's set for the test
            agent1.retry_delay = 0.1  # Speed up test

            result = await agent1._with_retry(
                retry_tester.op_that_fails_then_succeeds, fail_times=2
            )
            assert (
                result == "Success"
            ), "_with_retry did not return success after retries."
            assert (
                retry_tester.attempts == 3
            ), "Retry mechanism did not attempt the correct number of times."
            logger.info(
                "_with_retry successfully executed an operation after simulated failures."
            )

            logger.info("All BaseAgent refactor verifications passed!")

    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
    finally:
        if db_client:
            await cleanup_test_database(db_client)
        logger.info("Verification script finished.")


if __name__ == "__main__":
    # Note: Ensure PostgreSQL server is running and accessible via TEST_DATABASE_URL
    # and the database specified in TEST_DATABASE_URL exists.
    # The script will attempt to drop and create tables within that database.
    # Example: `createdb test_agent_db` if using default URL.

    # For CI or automated tests, you might use a library like `testing.postgresql`
    # to spin up a temporary PostgreSQL instance.

    asyncio.run(verify_base_agent())
