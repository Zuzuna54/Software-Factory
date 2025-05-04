# agents/tasks/celery_app.py

import os
from celery import Celery

# Configure Celery application
# The broker and backend URLs should ideally come from environment variables
# for flexibility and security.
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "agent_tasks",
    broker=redis_url,
    backend=redis_url,
    include=["agents.tasks.agent_tasks"],  # Auto-discover tasks in this module
)

# Load Celery configuration from settings object (optional, can configure directly)
# app.config_from_object('django.conf:settings', namespace='CELERY')

# Optional configuration settings
app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Accept JSON format
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,  # Track when tasks start execution
    task_time_limit=3600,  # Optional: Soft time limit (1 hour)
    worker_max_tasks_per_child=200,  # Prevent memory leaks
    worker_prefetch_multiplier=1,  # Ensure fair task distribution
    broker_connection_retry_on_startup=True,  # Retry connecting to broker on startup
)

# If you have tasks in other modules, add them to the 'include' list above.
# Example: include=['agents.tasks.agent_tasks', 'agents.tasks.other_tasks']

if __name__ == "__main__":
    # This allows running the worker directly using:
    # python -m agents.tasks.celery_app worker --loglevel=info
    app.start()
