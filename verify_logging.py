#!/usr/bin/env python
"""
Verification test for comprehensive logging system.
"""

import asyncio
import uuid
import time
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from agents.logging import ActivityLogger, ActivityCategory, ActivityLevel


async def test_logging_system():
    """Test the comprehensive logging system."""
    print("\n----- Testing Comprehensive Logging System -----")

    # Create database connection
    database_url = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory"
    )
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    test_start_time = datetime.utcnow()
    test_id = uuid.uuid4()

    try:
        async with async_session() as db_session:
            # Initialize the logger
            print("Initializing activity logger...")
            logger = ActivityLogger(
                agent_id=test_id,
                agent_name="Test Agent",
                db_session=db_session,
                min_level=ActivityLevel.DEBUG,
            )

            # 1. Test basic activity logging
            print("\nTesting basic activity logging...")

            basic_start = time.time()
            activity_id = await logger.log_activity(
                activity_type="test_activity",
                description="Testing basic activity logging",
                category=ActivityCategory.SYSTEM,
                level=ActivityLevel.INFO,
                details={"test": True, "timestamp": datetime.utcnow().isoformat()},
            )
            basic_duration = time.time() - basic_start

            if activity_id:
                print(f"✅ Basic activity logging successful ({basic_duration:.2f}s)")
                print(f"Activity ID: {activity_id}")
            else:
                print(f"❌ Basic activity logging failed")
                return False

            # 2. Test decision logging
            print("\nTesting decision logging...")

            decision_start = time.time()
            decision_id = await logger.log_decision(
                decision_type="test_decision",
                description="Testing decision logging",
                options=[
                    {
                        "id": "option1",
                        "name": "Option 1",
                        "pros": ["Fast"],
                        "cons": ["Expensive"],
                    },
                    {
                        "id": "option2",
                        "name": "Option 2",
                        "pros": ["Cheap"],
                        "cons": ["Slow"],
                    },
                ],
                chosen_option={"id": "option1", "name": "Option 1"},
                reasoning="Option 1 was chosen because speed is more important than cost",
                confidence=0.85,
            )
            decision_duration = time.time() - decision_start

            if decision_id:
                print(f"✅ Decision logging successful ({decision_duration:.2f}s)")
                print(f"Decision Activity ID: {decision_id}")
            else:
                print(f"❌ Decision logging failed")
                return False

            # 3. Test error logging
            print("\nTesting error logging...")

            error_start = time.time()
            try:
                # Generate an exception deliberately
                raise ValueError("Test error for logging verification")
            except Exception as e:
                error_id = await logger.log_error(
                    error_type="test_error",
                    description="Testing error logging with exception",
                    exception=e,
                    severity=ActivityLevel.ERROR,
                    context={"operation": "verification_test"},
                    recovery_action="Continuing with tests",
                )
            error_duration = time.time() - error_start

            if error_id:
                print(f"✅ Error logging successful ({error_duration:.2f}s)")
                print(f"Error Activity ID: {error_id}")
            else:
                print(f"❌ Error logging failed")
                return False

            # 4. Test performance timing
            print("\nTesting performance timing...")

            # Start a timer
            logger.start_timer("test_operation")

            # Simulate work
            await asyncio.sleep(0.1)

            # Stop the timer
            timing_start = time.time()
            duration = await logger.stop_timer("test_operation", success=True)
            timing_duration = time.time() - timing_start

            if duration > 0:
                print(f"✅ Performance timing successful ({timing_duration:.2f}s)")
                print(f"Measured operation duration: {duration:.2f}s")
            else:
                print(f"❌ Performance timing failed")
                return False

            # 5. Test communication logging
            print("\nTesting communication logging...")

            comm_start = time.time()
            comm_id = await logger.log_communication(
                message_type="request",
                sender_id=test_id,
                recipient_id=uuid.uuid4(),
                content_summary="Test request for verification",
                message_id=uuid.uuid4(),
                full_content="This is a detailed test request for the verification process",
                metadata={"priority": "high"},
            )
            comm_duration = time.time() - comm_start

            if comm_id:
                print(f"✅ Communication logging successful ({comm_duration:.2f}s)")
                print(f"Communication Activity ID: {comm_id}")
            else:
                print(f"❌ Communication logging failed")
                return False

            # 6. Test thinking process logging
            print("\nTesting thinking process logging...")

            thinking_start = time.time()
            thinking_id = await logger.log_thinking_process(
                thought_type="problem_solving",
                description="Analyzing test verification approach",
                reasoning="Comprehensive testing requires validation of all logging system features",
                input_context={"task": "logging_verification", "priority": "high"},
                conclusion="All logging features should be tested systematically",
                intermediate_steps=[
                    {"step": 1, "action": "Define test cases"},
                    {"step": 2, "action": "Execute tests"},
                    {"step": 3, "action": "Verify results"},
                ],
            )
            thinking_duration = time.time() - thinking_start

            if thinking_id:
                print(
                    f"✅ Thinking process logging successful ({thinking_duration:.2f}s)"
                )
                print(f"Thinking Process Activity ID: {thinking_id}")
            else:
                print(f"❌ Thinking process logging failed")
                return False

            # 7. Test retrieval of recent activities
            print("\nTesting retrieval of recent activities...")

            retrieval_start = time.time()
            activities = await logger.get_recent_activities(
                limit=10, time_window=timedelta(minutes=5)
            )
            retrieval_duration = time.time() - retrieval_start

            if activities and len(activities) > 0:
                print(f"✅ Activity retrieval successful ({retrieval_duration:.2f}s)")
                print(f"Retrieved {len(activities)} recent activities")
            else:
                print(f"❌ Activity retrieval failed")
                return False

            # 8. Test performance metrics retrieval
            print("\nTesting performance metrics retrieval...")

            metrics_start = time.time()
            metrics = await logger.get_agent_performance_metrics()
            metrics_duration = time.time() - metrics_start

            if metrics:
                print(
                    f"✅ Performance metrics retrieval successful ({metrics_duration:.2f}s)"
                )
                metric_count = len(metrics)
                print(f"Retrieved metrics for {metric_count} operation type(s)")
            else:
                print(f"⚠️ No performance metrics available yet")

            # 9. Test decision history retrieval
            print("\nTesting decision history retrieval...")

            decision_history = logger.get_decision_history()

            if decision_history and len(decision_history) > 0:
                print(f"✅ Decision history retrieval successful")
                print(f"Retrieved {len(decision_history)} decisions")
            else:
                print(f"❌ Decision history retrieval failed")
                return False

            # 10. Clean up test data
            print("\nCleaning up test data...")
            await db_session.execute(
                f"DELETE FROM agent_activities WHERE agent_id = '{test_id}'"
            )
            await db_session.commit()

            # All tests passed!
            test_end_time = datetime.utcnow()
            duration = (test_end_time - test_start_time).total_seconds()
            print(
                f"\n✅ All logging system tests passed successfully in {duration:.2f} seconds!"
            )
            return True

    except Exception as e:
        print(f"❌ Error during logging system testing: {str(e)}")
        return False
    finally:
        # Close the engine
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_logging_system())
