# Global Iteration 1: CLI Enhancement and Persistence

## Overview

This plan outlines the necessary steps to make the `agents/cli/agent_cli.py` tool fully functional, persistent, and aligned with the capabilities developed up to Iteration 5 of the project plan. The current CLI serves as a basic testing tool but lacks proper database integration for creation, cannot instantiate specialized agents, and has limitations in message sending.

## Goals

1.  Enable the CLI to reliably create and register _any_ specialized agent type defined up to Iteration 5 (Base, ProductManager, ScrumMaster, BackendDeveloper, QAAgent) persistently in the database.
2.  Modify the CLI's message sending functionality to allow sending messages _as_ any valid agent ID registered in the database, removing the in-memory limitation.
3.  Ensure all relevant CLI actions interact correctly with the PostgreSQL database for persistence.
4.  Lay the groundwork for the CLI to potentially initiate workflows (e.g., sending the initial requirement message).

## Required Tasks

### Task 1: Implement Agent Factory

- **Description:** Create a factory pattern to handle the instantiation of different agent types.
- **Why:** The current CLI `agent create` only instantiates `BaseAgent`. A factory is needed to create specialized agents (`ProductManagerAgent`, `ScrumMasterAgent`, `BackendDeveloperAgent`, `QAAgent`) based on the `--type` argument.
- **Implementation:**
  - Create `agents/factory.py`.
  - Define an `AgentFactory` class or function.
  - The factory should take `agent_type`, `agent_name`, `capabilities`, and potentially other shared dependencies (`llm_provider`, `db_client`, `vector_memory`, `comm_protocol`) as input.
  - It should import the necessary specialized agent classes from `agents/specialized/`.
  - Based on `agent_type`, it should instantiate and return the correct agent class instance.
  - Include error handling for unknown agent types.
- **Files to Create/Modify:**
  - `agents/factory.py` (New)
  - `agents/cli/agent_cli.py` (Modify `create_agent` to use the factory)
  - Potentially `agents/specialized/__init__.py` to ensure classes are importable.

### Task 2: Ensure Persistent Agent Creation in CLI

- **Description:** Modify the `agent create` command in the CLI to ensure the agent is fully registered in the database before the command returns.
- **Why:** The current approach relies on the `BaseAgent.__init__` performing registration asynchronously. The CLI should explicitly handle the registration via the `db_client` within the `create_agent` method or reliably wait for the background registration to complete.
- **Implementation:**
  - In `AgentCLI.create_agent`:
    - After instantiating the agent using the factory (from Task 1), explicitly call a registration method or directly use `self.db_client.execute` to insert the agent record into the `agents` table.
    - Use the agent's generated `agent_id`, `agent_type`, `agent_name`, and `capabilities`.
    - Handle potential `UniqueViolationError` if an agent with the same ID somehow already exists.
    - Remove or modify the reliance on the agent's constructor doing the registration implicitly if opting for explicit registration.
- **Files to Modify:**
  - `agents/cli/agent_cli.py`
  - Potentially `agents/base_agent.py` (if modifying constructor registration logic).

### Task 3: Fix `message send` Functionality

- **Description:** Remove the limitation that the sender agent must be managed in the current CLI session's memory.
- **Why:** This is the most significant limitation, preventing the CLI from being used to interact _as_ existing agents or initiate workflows realistically.
- **Implementation:**
  - In `AgentCLI.send_message`:
    - Remove the check `sender_agent = self.agents.get(sender_id)` and the subsequent error if not found.
    - Instead, add a check to verify that the provided `sender_id` exists as an active agent in the `agents` database table using `self.db_client.fetch_one`.
    - If the sender ID is valid, proceed to create the `AgentMessage` object using `self.comm_protocol._create_message`.
    - Directly use `self.db_client.execute` to insert the created message into the `agent_messages` table (similar to the logic currently inside `BaseAgent.send_message`).
    - Ensure the vector embedding for the sent message is also generated and stored using `self.vector_memory.store_entity` (again, mirroring logic from `BaseAgent.send_message` but triggered directly from the CLI method after DB validation).
- **Files to Modify:**
  - `agents/cli/agent_cli.py`

### Task 4: Refine Database Interactions (If Needed)

- **Description:** Review the methods in `agents/db/postgres.py` and ensure they fully support the CLI's needs for creating agents and sending messages.
- **Why:** While the DB client seems robust, explicit checks ensure the required insert/query patterns are efficient and correct for the CLI use case.
- **Implementation:**
  - Verify that the `execute` method handles INSERTs correctly for `agents` and `agent_messages` tables.
  - Verify that the `fetch_one` method works for checking agent existence by ID.
  - No code changes expected unless specific issues are found during implementation of Tasks 2 & 3.
- **Files to Modify:**
  - `agents/db/postgres.py` (Potentially)

## Post-Implementation Verification

1.  Run `agent create` for `base`, `ProductManager`, `ScrumMaster`, `BackendDeveloper`, `QAAgent` types. Verify agents appear immediately in `agent list` and the database.
2.  Run `message send` using an `agent_id` obtained from `agent list` (not created in the same session). Verify the command succeeds and the message appears in the database and via `message show <receiver_id>`.
3.  Check database tables (`agents`, `agent_messages`, `enhanced_vector_storage`) directly to confirm persistence.
