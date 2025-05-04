# Agent System Command-Line Interface (CLI) Usage Guide

This document explains how to use the `agent_cli.py` script to interact with the autonomous agent system for testing, debugging, and manual intervention.

## Overview

The CLI provides commands to:

- Create and list agents persistently in the database.
- Send messages between any registered agents.
- View agent messages and activities from the database.
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

- **`agent create`**: Create a new agent instance and register it persistently in the database.

  - `--type <type>`: **(Required)** The type of agent to create. Known types based on current implementation: `base`, `product_manager`, `scrum_master`, `backend_developer`, `qa`. See `agents/factory.py` for the definitive list.
  - `--name <name>`: **(Required)** A descriptive name for the agent (e.g., `"Main PM"`, `"Backend Dev 1"`).
  - `--capabilities '<json_string>'`: Optional. A JSON string defining agent-specific capabilities (e.g., `'{"language": "python"}'`).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py agent create --type product_manager --name "Main Product Manager"
    ```
  - _Output:_ Prints the newly created agent's ID.

- **`agent list`**: List all agents registered in the database.

  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py agent list
    ```
  - _Output:_ A JSON list of registered agents with their ID, type, name, creation time, capabilities, and active status.

- **`agent activities`**: Show recent activities logged for an agent from the database.
  - `--id <agent_id>`: **(Required)** The UUID of the agent.
  - `--type <activity_type>`: Optional. Filter by activity type (e.g., `CodeGeneration`, `RequirementAnalysis`). Case-insensitive, partial matches allowed.
  - `--limit <number>`: Optional. Maximum number of activities to show (default: 10).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py agent activities --id <some_agent_uuid> --limit 5 --type CodeGeneration
    ```
  - _Output:_ A JSON list of the agent's recent activities.

### Messaging (`message`)

- **`message send`**: Send a message from one agent to another (logs directly to DB).

  - `--sender <sender_id>`: **(Required)** The UUID of the sending agent (must exist in the database).
  - `--receiver <receiver_id>`: **(Required)** The UUID of the receiving agent (must exist in the database).
  - `--content "<message_content>"`: **(Required)** The text content of the message.
  - `--type <message_type>`: Optional. The type/intent of the message (e.g., `INFORM`, `REQUEST`, `REQUIREMENT`, `PROPOSE`, `BUG_REPORT`). Case-insensitive. Defaults to `INFORM`. See `agents.communication.protocol.MessageType` for all valid types.
  - `--conv_id <conversation_uuid>`: Optional. UUID to link messages in a conversation thread.
  - `--task_id <task_uuid>`: Optional. UUID of a related task.
  - `--metadata '<json_string>'`: Optional. Additional structured data as a JSON string (e.g., `'{"priority": "high"}'`).
  - **Example (assuming PM and ScrumMaster agents exist):**
    ```bash
    # List agents to get IDs
    docker-compose exec backend python agents/cli/agent_cli.py agent list
    # Assume PM_ID and SM_ID are obtained
    docker-compose exec backend python agents/cli/agent_cli.py message send \
      --sender <PM_ID> \
      --receiver <SM_ID> \
      --type REQUEST \
      --content "Please start planning sprint 1 based on the approved features."
    ```
  - _Output:_ Prints the ID of the logged message if successful.

- **`message show`**: Show recent messages received by an agent from the database.
  - `--id <agent_id>`: **(Required)** The UUID of the agent whose received messages you want to see.
  - `--limit <number>`: Optional. Maximum number of messages to show (default: 10).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py message show --id <some_agent_uuid> --limit 20
    ```
  - _Output:_ A JSON list of recently received messages for the specified agent.

### Knowledge Base (`knowledge`)

- **`knowledge search`**: Perform vector search on stored knowledge (currently messages) via vector similarity.
  - `--query "<search_term>"`: **(Required)** The query string to search for.
  - `--limit <number>`: Optional. Maximum number of results to return (default: 5).
  - **Example:**
    ```bash
    docker-compose exec backend python agents/cli/agent_cli.py knowledge search --query "API endpoint implementation patterns"
    ```
  - _Output:_ A JSON list of messages most relevant to the query, including their metadata and similarity score.

## Example Workflow: Initiating a Task

This workflow demonstrates how to manually kick off the process by sending a requirement to the Product Manager (PM) agent using the updated CLI.

1.  **Ensure PM Agent Exists:**

    - List existing agents.
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py agent list
      ```
    - Look for an agent with type `product_manager`. Note its `agent_id` (`<PM_AGENT_ID>`).
    - If no PM agent exists, create one:
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py agent create --type product_manager --name "Main PM"
      # Re-run list to get the new ID if needed
      ```

2.  **(Optional) Create a 'User' Agent for Sending:**

    - While you can now send as any agent, you might want a dedicated agent ID to represent manual input.
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py agent create --type base --name "Manual Input"
      # Note the returned <USER_AGENT_ID>
      ```

3.  **Send the Requirement Message:**

    - Use the appropriate sender ID (e.g., the User Agent ID from step 2, or even the PM sending to itself if that fits the workflow) and the PM Agent ID.
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py message send \
        --sender "<USER_AGENT_ID_OR_OTHER_SENDER>" \
        --receiver "<PM_AGENT_ID>" \
        --type REQUIREMENT \
        --content "Please plan the development of a web application for managing personal tasks."
      ```

4.  **Monitor:**
    - Check the logs of the services (especially `celery_worker` and `backend` to see if the PM agent reacts to the message):
      ```bash
      docker-compose logs -f backend celery_worker celery_beat
      ```
    - Check messages received by the PM or its activities logged:
      ```bash
      docker-compose exec backend python agents/cli/agent_cli.py message show --id <PM_AGENT_ID>
      docker-compose exec backend python agents/cli/agent_cli.py agent activities --id <PM_AGENT_ID>
      ```
    - Check the dashboard at `http://localhost:3000`.

## Extending the CLI

The CLI script is located at `agents/cli/agent_cli.py`. To add new commands or functionality:

1.  **Add Agent Types:** If you create new specialized agents, add them to the `AGENT_TYPE_MAP` in `agents/factory.py`.
2.  **Add CLI Functions:** Implement new `async` methods within the `AgentCLI` class for the core logic.
3.  **Define Arguments:** Add new subparsers or arguments to the `argparse` setup within the `run_cli` async function.
4.  **Connect Logic:** In `run_cli`, check for your new command/arguments and call the corresponding `AgentCLI` method.
