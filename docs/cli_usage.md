# Agent System Command-Line Interface (CLI) Usage Guide

This document explains how to use the `agent_cli.py` script to interact with the autonomous agent system for testing, debugging, and manual intervention.

## Overview

The CLI provides commands to:

- Create and list agents persistently in the database.
- Send messages between any registered agents.
- View agent messages and activities from the database.
- Search the knowledge base (vector search on messages).
- Dispatch background tasks handled by Celery workers.

**Important:** The CLI is primarily intended for low-level testing and debugging. It runs _inside_ the `backend` Docker container or directly within the activated virtual environment if run locally.

## Prerequisites

1.  **System Running:** Ensure all services are running via `docker-compose up --build -d` if using Docker, or that the database, Redis, and Celery worker are running if operating locally.
2.  **Environment Variables:** The environment (container or local shell) where the CLI runs needs access to environment variables defined in your root `.env` file. Key variables include:
    - `DATABASE_URL`: Connection string for the PostgreSQL database.
    - `REDIS_URL`: Connection string for Redis (used by underlying components like Celery).
    - `GEMINI_API_KEY`: Your API Key for Google Gemini (required by `GeminiApiProvider`).
    - _(Potentially other API keys if added later)_
3.  **Python Environment:** If running locally (outside Docker), ensure you have activated the virtual environment (`source .venv/bin/activate`).

## Running Commands

Commands can be executed either via `docker-compose exec` or directly using `python` if running locally.

**Via Docker:**

```bash
docker-compose exec backend python agents/cli/agent_cli.py <command> [subcommand] [options]
```

**Locally (in project root with venv activated):**

```bash
python agents/cli/agent_cli.py <command> [subcommand] [options]
```

## Available Commands

### Agent Management (`agent`)

- **`agent create`**: Create a new agent instance and register it persistently in the database.

  - `--type <type>`: **(Required)** The type of agent to create. Known types based on current implementation: `base`, `product_manager`, `scrum_master`, `backend_developer`, `qa`. See `agents/factory.py` for the definitive list (`AGENT_TYPE_MAP`).
  - `--name <name>`: **(Required)** A descriptive name for the agent (e.g., `"Main PM"`, `"Backend Dev 1"`).
  - `--capabilities '<json_string>'`: Optional. A JSON string defining agent-specific capabilities (e.g., `'{"language": "python"}'`).
  - **Example (Docker):**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py agent create --type product_manager --name "Main Product Manager"
    ```
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py agent create --type backend_developer --name "CLI Test Developer"
    ```
  - _Output:_ Prints the newly created agent's ID.

- **`agent list`**: List all agents registered in the database.

  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py agent list
    ```
  - _Output:_ A JSON list of registered agents with their ID, type, name, creation time, capabilities, and active status.

- **`agent activities`**: Show recent activities logged for an agent from the database.

  - `--id <agent_id>`: **(Required)** The UUID of the agent.
  - `--type <activity_type>`: Optional. Filter by activity type (e.g., `CodeGeneration`, `RequirementAnalysis`). Case-insensitive, partial matches allowed.
  - `--limit <number>`: Optional. Maximum number of activities to show (default: 10).
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py agent activities --id <some_agent_uuid> --limit 5 --type CodeGeneration
    ```
  - _Output:_ A JSON list of the agent's recent activities.

- **`agent analyze-requirements`**: Invoke the `analyze_requirements` method directly on a Product Manager agent.

  - `--id <agent_id>`: **(Required)** The UUID of the Product Manager agent.
  - `--description "<project_description>"`: **(Required)** High-level project description.
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py agent analyze-requirements --id <pm_agent_uuid> --description "Develop a weather widget for the dashboard"
    ```
  - _Output:_ JSON result from the agent method.

- **`agent run-tests`**: Invoke the `run_tests` method directly on a QA agent.
  - `--id <agent_id>`: **(Required)** The UUID of the QA agent.
  - `--paths [path1 path2 ...]`: Optional. List of specific test paths/files to run.
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py agent run-tests --id <qa_agent_uuid> --paths tests/test_api.py
    ```
  - _Output:_ JSON result from the agent method.

### Messaging (`message`)

- **`message send`**: Send a message from one agent to another (logs directly to DB).

  - `--sender <sender_id>`: **(Required)** The UUID of the sending agent (must exist in the database).
  - `--receiver <receiver_id>`: **(Required)** The UUID of the receiving agent (must exist in the database).
  - `--content "<message_content>"`: **(Required)** The text content of the message.
  - `--type <message_type>`: Optional. The type/intent of the message (e.g., `INFORM`, `REQUEST`, `PROPOSE`, `TASK_ASSIGNMENT`). Case-insensitive. Defaults to `INFORM`. See `agents.communication.protocol.MessageType` for all valid types.
  - `--conv_id <conversation_uuid>`: Optional. UUID to link messages in a conversation thread.
  - `--task_id <task_uuid>`: Optional. UUID of a related task.
  - `--metadata '<json_string>'`: Optional. Additional structured data as a JSON string (e.g., `'{"priority": "high"}'`).
  - **Example (Local, assuming PM and ScrumMaster agents exist):**
    ```bash
    # List agents to get IDs
    python agents/cli/agent_cli.py agent list
    # Assume PM_ID and SM_ID are obtained
    python agents/cli/agent_cli.py message send \
      --sender <PM_ID> \
      --receiver <SM_ID> \
      --type REQUEST \
      --content "Please start planning sprint 1 based on the approved features."
    ```
  - _Output:_ Prints the ID of the logged message if successful.

- **`message show`**: Show recent messages received by an agent from the database.
  - `--id <agent_id>`: **(Required)** The UUID of the agent whose received messages you want to see.
  - `--limit <number>`: Optional. Maximum number of messages to show (default: 10).
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py message show --id <some_agent_uuid> --limit 20
    ```
  - _Output:_ A JSON list of recently received messages for the specified agent.

### Knowledge Base (`knowledge`)

- **`knowledge search`**: Perform vector search on stored knowledge (currently messages) via vector similarity.
  - `--query "<search_term>"`: **(Required)** The query string to search for.
  - `--limit <number>`: Optional. Maximum number of results to return (default: 5).
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py knowledge search --query "API endpoint implementation patterns"
    ```
  - _Output:_ A JSON list of messages most relevant to the query, including their metadata and similarity score.

### Task Dispatching (`task dispatch`)

These commands send tasks to the Celery workers for background processing.

- **`task dispatch analyze_requirements`**: Dispatch task for a Product Manager agent to analyze requirements.

  - `--project_description "<description>"`: **(Required)** The high-level project description.
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py task dispatch analyze_requirements --project_description "Develop a new user authentication service"
    ```
  - _Output:_ Prints the Celery task ID.

- **`task dispatch plan_sprint`**: Dispatch task for a Scrum Master agent to plan a sprint.

  - `--project_id <project_id>`: **(Required)** The ID of the project for which to plan the sprint (e.g., the ID generated by `analyze_requirements`).
  - `--sprint_duration_days <days>`: Optional. Duration of the sprint in days (default: 14).
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py task dispatch plan_sprint --project_id "user-authentication-service" --sprint_duration_days 10
    ```
  - _Output:_ Prints the Celery task ID.

- **`task dispatch assign_task`**: Dispatch task for a Scrum Master agent to assign a task.

  - `--task_id <task_uuid>`: **(Required)** The UUID of the task to assign.
  - `--agent_id <agent_uuid>`: **(Required)** The UUID of the agent to assign the task to.
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py task dispatch assign_task --task_id <task_uuid_from_plan_sprint> --agent_id <developer_agent_uuid>
    ```
  - _Output:_ Prints the Celery task ID.

- **`task dispatch update_task_status`**: Dispatch task for a Scrum Master agent to update a task's status.
  - `--task_id <task_uuid>`: **(Required)** The UUID of the task to update.
  - `--status <NEW_STATUS>`: **(Required)** The new status (e.g., `BACKLOG`, `ASSIGNED`, `IN_PROGRESS`, `REVIEW`, `DONE`). Case-sensitive, must match database expectations.
  - `--agent_id <updater_agent_uuid>`: Optional. UUID of the agent performing the update (can be useful for logging/context).
  - **Example (Local):**
    ```bash
    python agents/cli/agent_cli.py task dispatch update_task_status --task_id <some_task_uuid> --status IN_PROGRESS
    ```
  - _Output:_ Prints the Celery task ID.

## Example Workflow: Initiating a Task via Celery

This workflow uses the background task dispatch mechanism.

1.  **Dispatch Requirement Analysis:**

    ```bash
    python agents/cli/agent_cli.py task dispatch analyze_requirements --project_description "E2E Test Run 3 - Celery Workflow"
    # Note the Celery Task ID from output
    ```

2.  **Monitor Celery Worker & Check Project:**

    - Watch Celery logs (`docker-compose logs -f celery_worker` or local logs).
    - Once the task succeeds, find the `project_id` created (e.g., `e2e-test-run-3:-celery-workflow`) from the logs ("Ensured project exists: ID=...")
    - Verify project creation in DB:
      ```bash
      python agents/cli/agent_cli.py agent list # (Optional: To see agent created by task)
      psql -h localhost -d agent_team -U agent_user -c "SELECT project_id FROM projects WHERE project_id = '<actual_project_id>';" # Use PGPASSWORD env var
      ```

3.  **Dispatch Sprint Planning:**

    ```bash
    python agents/cli/agent_cli.py task dispatch plan_sprint --project_id "<actual_project_id>" --sprint_duration_days 7
    # Note the Celery Task ID
    ```

4.  **Monitor Celery & Check Sprint/Tasks:**

    - Watch Celery logs.
    - Once the task succeeds, find the `sprint_id` created from the logs or DB.
    - Verify sprint and task creation in DB:
      ```bash
      psql -h localhost -d agent_team -U agent_user -c "SELECT sprint_id, status FROM sprints WHERE project_id = '<actual_project_id>' ORDER BY created_at DESC LIMIT 1;"
      psql -h localhost -d agent_team -U agent_user -c "SELECT task_id, title, status FROM tasks WHERE sprint_id = '<new_sprint_id>';" # Use PGPASSWORD env var
      ```

5.  **Create Agent & Dispatch Task Assignment:**

    ```bash
    python agents/cli/agent_cli.py agent create --name "E2E Worker Agent 3" --type backend_developer
    # Note the <worker_agent_id>
    python agents/cli/agent_cli.py task dispatch assign_task --task_id "<task_id_from_step_4>" --agent_id "<worker_agent_id>"
    # Note the Celery Task ID
    ```

6.  **Monitor Celery & Check Task Assignment:**

    - Watch Celery logs.
    - Verify task status and assignment in DB:
      ```bash
      psql -h localhost -d agent_team -U agent_user -c "SELECT status, assigned_to FROM tasks WHERE task_id = '<task_id_from_step_4>';" # Use PGPASSWORD env var
      ```

7.  **Dispatch Status Updates & Verify:**
    ```bash
    python agents/cli/agent_cli.py task dispatch update_task_status --task_id "<task_id_from_step_4>" --status IN_PROGRESS
    # Monitor & Verify DB
    python agents/cli/agent_cli.py task dispatch update_task_status --task_id "<task_id_from_step_4>" --status DONE
    # Monitor & Verify DB
    ```

## Extending the CLI

The CLI script is located at `agents/cli/agent_cli.py`. To add new commands or functionality:

1.  **Add Agent Types:** If you create new specialized agents, add them to the `AGENT_TYPE_MAP` in `agents/factory.py`.
2.  **Add Celery Tasks:** Define new `@shared_task` functions in `agents/tasks/agent_tasks.py`.
3.  **Add CLI Functions:** Implement new `async` methods within the `AgentCLI` class for any direct agent interaction logic (if needed).
4.  **Define Arguments:** Add new subparsers or arguments to the `argparse` setup within the `run_cli` async function. Specifically, add new subparsers under `task dispatch` for new Celery tasks.
5.  **Connect Logic:** In `run_cli`, check for your new command/arguments and call the corresponding `AgentCLI` method or the `cli.dispatch_celery_task` method, ensuring necessary arguments are collected for `task_kwargs`.
