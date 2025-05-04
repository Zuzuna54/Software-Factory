# Agent System Command-Line Interface (CLI) Usage Guide

This document explains how to use the `agent_cli.py` script to interact with the autonomous agent system for testing, debugging, and manual intervention.

## Overview

The CLI provides commands to:

- Create and list agents.
- Send messages between agents.
- View agent messages and activities.
- Search the knowledge base (vector search on messages).

**Important:** The CLI is primarily intended for low-level testing and debugging. It runs _inside_ the `backend` Docker container.

## Prerequisites

1.  **System Running:** Ensure all services are running via `docker-compose up --build -d`.
2.  **Environment Variables:** The `backend` container (where the CLI runs) needs access to environment variables defined in your root `.env` file. Key variables include:
    - `DATABASE_URL`: Connection string for the PostgreSQL database.
    - `REDIS_URL`: Connection string for Redis (used by underlying components).
    - `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID is required for the LLM provider (`VertexGeminiProvider`).
    - _(Potentially other API keys if added later)_

## Running Commands

All commands are executed using `docker-compose exec` targeting the `backend` service. The base structure is:

```bash
docker-compose exec backend python agents/cli/agent_cli.py <command> [subcommand] [options]
```

## Available Commands

### Agent Management (`agent`)

- **`agent create`**: Create a new agent instance.

  - `--type <type>`: Agent type (Currently only supports `base`, defaults to `base`). Future versions will support `ProductManager`, `Developer`, etc.
  - `--name <name>`: **(Required)** A descriptive name for the agent (e.g., `"Main PM"`, `"User Input"`).
  - `--capabilities '<json_string>'`: Optional. A JSON string defining the agent's capabilities (e.g., `'{"can_code": true}'`).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py agent create --name "Test User Agent" --type base
    ```
  - _Output:_ Prints the newly created agent's ID.

- **`agent list`**: List all agents registered in the database.

  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py agent list
    ```
  - _Output:_ A JSON list of registered agents with their ID, type, name, creation time, capabilities, and active status.

- **`agent activities`**: Show recent activities logged for an agent.
  - `--id <agent_id>`: **(Required)** The UUID of the agent.
  - `--type <activity_type>`: Optional. Filter by activity type (e.g., `CodeGeneration`, `Review`). Case-insensitive, partial matches allowed.
  - `--limit <number>`: Optional. Maximum number of activities to show (default: 10).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py agent activities --id <some_agent_uuid> --limit 5
    ```
  - _Output:_ A JSON list of the agent's recent activities.

### Messaging (`message`)

- **`message send`**: Send a message from one agent to another.

  - `--sender <sender_id>`: **(Required)** The UUID of the sending agent. **Limitation:** The sender agent must have been created _within the same `agent create` command execution_ in this specific CLI invocation. You cannot easily send messages _as_ an agent created in a previous run or automatically by the system using this command directly. A common workaround is to create a temporary 'User' agent first and send the message from its ID.
  - `--receiver <receiver_id>`: **(Required)** The UUID of the receiving agent.
  - `--content "<message_content>"`: **(Required)** The text content of the message.
  - `--type <message_type>`: Optional. The type/intent of the message (e.g., `INFORM`, `REQUEST`, `REQUIREMENT`, `PROPOSE`, `BUG_REPORT`). Case-insensitive. Defaults to `INFORM`.
  - `--conv_id <conversation_uuid>`: Optional. UUID to link messages in a conversation thread.
  - `--task_id <task_uuid>`: Optional. UUID of a related task.
  - `--metadata '<json_string>'`: Optional. Additional structured data as a JSON string.
  - **Example (assuming `USER_AGENT_ID` and `PM_AGENT_ID` were obtained):**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py message send --sender <USER_AGENT_ID> --receiver <PM_AGENT_ID> --type REQUIREMENT --content "Initial requirement: Build a simple task list application."
    ```
  - _Output:_ Prints the ID of the sent message if successful.

- **`message show`**: Show recent messages received by an agent.
  - `--id <agent_id>`: **(Required)** The UUID of the agent whose received messages you want to see.
  - `--limit <number>`: Optional. Maximum number of messages to show (default: 10).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py message show --id <some_agent_uuid> --limit 20
    ```
  - _Output:_ A JSON list of recently received messages for the specified agent.

### Knowledge Base (`knowledge`)

- **`knowledge search`**: Perform vector search on stored knowledge (currently messages).
  - `--query "<search_term>"`: **(Required)** The query string to search for.
  - `--limit <number>`: Optional. Maximum number of results to return (default: 5).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py knowledge search --query "database schema design"
    ```
  - _Output:_ A JSON list of messages most relevant to the query.

## Example Workflow: Initiating a Task

This workflow demonstrates how to manually kick off the process by sending a requirement to the Product Manager (PM) agent.

1.  **Identify the PM Agent:**

    - List existing agents to see if a PM agent was created automatically or in a previous run.
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py agent list
      ```
    - Look for an agent with type `ProductManager` (or similar, depending on future implementation). Note its `agent_id`.
    - If no PM agent exists, you might need to investigate the agent startup process or create one manually (though the CLI currently only supports `base` type). Let's assume a PM agent exists with ID `<PM_AGENT_ID>`.

2.  **Create a Temporary Sender Agent:**

    - Due to the `message send` limitation, create a temporary agent to act as the sender.
      ```bash
      # Execute the command and capture the output (which contains the agent ID)
      USER_AGENT_ID=$(docker-compose exec backend python agents/cli/agent_cli.py agent create --name "Manual Input Agent" --type base | grep 'Agent Created: ID =' | sed 's/Agent Created: ID = //')
      echo "Created User Agent with ID: $USER_AGENT_ID"
      ```
    - _(Note: The `grep | sed` part is a shell trick to extract the ID; adjust if the output format changes.)_

3.  **Send the Requirement Message:**

    - Use the obtained IDs to send the initial requirement.
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py message send --sender "$USER_AGENT_ID" --receiver "<PM_AGENT_ID>" --type REQUIREMENT --content "Please plan the development of a web application for managing personal tasks."
      ```
    - Replace `<PM_AGENT_ID>` with the actual ID found in step 1.

4.  **Monitor:**
    - Check the logs of the services:
      ```bash
      docker-compose logs -f backend celery_worker celery_beat
      ```
    - Check messages received by the PM or activities logged:
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py message show --id <PM_AGENT_ID>
      docker-compose exec backend python agents/cli/agent_cli.py agent activities --id <PM_AGENT_ID>
      ```
    - Check the dashboard at `http://localhost:3000` (if the frontend is fully functional).

## Extending the CLI

The CLI script is located at `agents/cli/agent_cli.py`. To add new commands or functionality:

1.  **Add Functions:** Implement new `async` methods within the `AgentCLI` class to encapsulate the desired logic. Use existing instance variables like `self.db_client`, `self.llm_provider`, `self.vector_memory` as needed.
2.  **Define Arguments:** Add new subparsers or arguments to the `argparse` setup within the `run_cli` async function.
3.  **Connect Logic:** In `run_cli`, check for your new command/arguments and call the corresponding `AgentCLI` method you created.
4.  **Agent Factory:** Note the TODO in the code regarding implementing an agent factory. Extending the CLI to create specialized agents (`ProductManager`, `Developer`, etc.) would require implementing this factory pattern first.
