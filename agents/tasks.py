"""
Celery tasks configuration for the Autonomous AI Development Team
"""

import os
from celery import Celery

# Get Redis URL from environment variable or use default
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "autonomous_ai_dev",
    broker=redis_url,
    backend=redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)


@celery_app.task(name="example_task")
def example_task(name: str) -> str:
    """Example task to demonstrate Celery functionality"""
    return f"Hello, {name}! This is a Celery task."


# Add more tasks below
