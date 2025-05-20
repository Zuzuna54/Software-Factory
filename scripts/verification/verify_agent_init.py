#!/usr/bin/env python
"""
Verification test for BaseAgent initialization and basic operations.
"""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from agents.base_agent import BaseAgent
from infra.db.models import Agent, AgentActivity


async def test_base_agent():
    """Test BaseAgent initialization and basic operations."""
    print("\n----- Testing BaseAgent Initialization and Operations -----")

    # Create database connection
    database_url = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory"
    )
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    test_id = uuid.uuid4()
    test_start_time = datetime.utcnow()

    try:
        async with async_session() as db_session:
            # 1. Test agent initialization
            print("Testing agent initialization...")
            agent = BaseAgent(
                agent_id=test_id,
                agent_type="test_agent",
                agent_name="Test Agent",
                agent_role="verification",
                capabilities=["testing", "verification"],
                db_session=db_session,
            )

            print(f"Agent created: {agent.agent_name} (ID: {agent.agent_id})")

            # 2. Test database initialization
            print("Testing database initialization...")
            await agent.initialize_db()

            # Verify the agent exists in database
            query = text(f"SELECT * FROM agents WHERE agent_id = '{agent.agent_id}'")
            result = await db_session.execute(query)
            agent_record = result.first()

            if agent_record:
                print(f"✅ Agent successfully stored in database")
            else:
                print(f"❌ Failed to store agent in database")
                return False

            # 3. Test thinking capability
            print("Testing thinking capability...")
            context = {
                "summary": "Test thinking operation",
                "type": "verification",
                "data": {"test_key": "test_value"},
            }

            result = await agent.think(context)

            if result and "thought_process" in result:
                print(f"✅ Agent thinking produced result")
            else:
                print(f"❌ Agent thinking failed to produce result")
                return False

            # 4. Test activity logging
            print("Testing agent activity logging...")
            activity_id = await agent.log_activity(
                activity_type="test_activity",
                description="Testing the log_activity method",
                input_data={"test": True, "timestamp": datetime.utcnow().isoformat()},
            )

            if activity_id:
                print(f"✅ Activity logged with ID: {activity_id}")
            else:
                print(f"❌ Failed to log activity")
                return False

            # 5. Clean up the test data
            print("Cleaning up test data...")
            await db_session.execute(
                text(
                    f"DELETE FROM agent_activities WHERE agent_id = '{agent.agent_id}'"
                )
            )
            await db_session.execute(
                text(f"DELETE FROM agents WHERE agent_id = '{agent.agent_id}'")
            )
            await db_session.commit()

            print("Test cleanup completed")

            test_end_time = datetime.utcnow()
            duration = (test_end_time - test_start_time).total_seconds()
            print(
                f"\n✅ All BaseAgent tests passed successfully in {duration:.2f} seconds!"
            )
            return True

    except Exception as e:
        print(f"❌ Error during BaseAgent testing: {str(e)}")
        return False
    finally:
        # Close the engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_base_agent())
