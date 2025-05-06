# Action Plan for Iteration 2 & 3 Missing Features

This document provides a detailed, actionable plan to implement the features identified as missing in the analysis document `docs/phases/missing_iteration_1.md`. Its goal is to bridge the gap between the current implementation and the planned capabilities for Iterations 2 and 3.

## Iteration 2: Implementing Orchestration & Task Handling

### 1. Task Triggering Mechanism

**Goal:** Establish methods to initiate the core agent workflows currently defined as Celery tasks (`analyze_requirements_task`, `plan_sprint_task`, `assign_task_to_agent_task`, `update_task_status_task`).

**Chosen Approach:** Add CLI commands for simplicity in initial testing and API endpoints for future integration.

**Actionable Steps:**

1.  **Add CLI Commands for Task Dispatch:**

    - **File:** `agents/cli/agent_cli.py`
    - **Logic:**

      - Add a new subcommand group: `task` (e.g., `parser.add_subparsers(dest="command").add_parser("task", ...)`).
      - Add subcommands under `task`, like `dispatch`.
      - For `dispatch`, add arguments to specify the task name (e.g., `--task-name analyze_requirements`) and necessary parameters (e.g., `--description "..."`, `--backlog-items '[{...}]'`, `--task-id X --agent-id Y`, etc.).
      - Implement a new method in `AgentCLI`, like `async def dispatch_celery_task(self, task_name: str, task_args: list, task_kwargs: dict):`.
      - Inside `dispatch_celery_task`, import the specific Celery task function from `agents.tasks.agent_tasks` based on `task_name`.
      - Use the `.delay()` or `.apply_async()` method to dispatch the task with the provided arguments. Example:

        ```python
        # Inside AgentCLI.dispatch_celery_task
        from agents.tasks.agent_tasks import analyze_requirements_task, plan_sprint_task # ... etc

        task_map = {
            "analyze_requirements": analyze_requirements_task,
            "plan_sprint": plan_sprint_task,
            "assign_task": assign_task_to_agent_task,
            "update_task_status": update_task_status_task
        }

        if task_name in task_map:
            task_func = task_map[task_name]
            task_func.apply_async(args=task_args, kwargs=task_kwargs)
            print(f"Dispatched task: {task_name}")
        else:
            print(f"Error: Unknown task name '{task_name}'")
        ```

      - Update the main `run_cli` function to handle the new `task dispatch` command.

2.  **Add API Endpoints for Task Dispatch:**

    - **File(s):**
      - Create `app/api/endpoints/tasks.py` (or similar).
      - Update `app/main.py` (if it exists, otherwise create it) to include the router from `tasks.py`.
    - **Logic:**
      - Use FastAPI (`APIRouter`).
      - Define POST endpoints like `/tasks/dispatch/analyze-requirements`, `/tasks/dispatch/plan-sprint`, etc.
      - Use Pydantic models to define request bodies for task parameters.
      - In the endpoint implementation, import the relevant Celery task function from `agents.tasks.agent_tasks`.
      - Call `.delay()` or `.apply_async()` to dispatch the task.
      - Return a response indicating task dispatch (e.g., `{ "message": "Task dispatched", "task_name": "..." }`).
    - **Example (`app/api/endpoints/tasks.py`):**

      ```python
      from fastapi import APIRouter, HTTPException
      from pydantic import BaseModel
      from agents.tasks.agent_tasks import analyze_requirements_task # ... import others

      router = APIRouter()

      class AnalyzeRequirementsPayload(BaseModel):
          project_description: str

      @router.post("/dispatch/analyze-requirements")
      async def dispatch_analyze_requirements(payload: AnalyzeRequirementsPayload):
          try:
              # Note: Celery's .delay/.apply_async are synchronous calls to queue the task
              analyze_requirements_task.delay(project_description=payload.project_description)
              return {"message": "Analyze requirements task dispatched"}
          except Exception as e:
              raise HTTPException(status_code=500, detail=str(e))

      # Add endpoints for other tasks...
      ```

### 2. Agent Task Consumption/Notification

**Goal:** Enable agents to become aware of and act upon tasks assigned to them.

**Chosen Approach:** Combine DB polling/checking with message-based notification.

**Actionable Steps:**

1.  **Modify Task Assignment to Notify Agent:**

    - **File:** `agents/specialized/scrum_master.py` (within `assign_task` method).
    - **File:** `agents/tasks/agent_tasks.py` (within `assign_task_to_agent_task`).
    - **Logic:**
      - After successfully updating the task status in the DB to 'ASSIGNED' (or similar) and setting the `assigned_to` field, the `ScrumMasterAgent` (or its Celery task wrapper) should create and send an `AgentMessage`.
      - Instantiate `AgentMessage` with:
        - `sender`: Scrum Master's agent ID.
        - `receiver`: The `agent_id` the task was assigned to.
        - `message_type`: `MessageType.TASK_ASSIGNMENT`.
        - `content`: A brief message like f"You have been assigned task {task_id}".
        - `related_task`: The `task_id`.
        - `metadata`: Optional, e.g., `{ "task_title": "...", "priority": "..." }`.
      - Call `self.send_message(assignment_message)` within the agent or use the comm protocol instance within the Celery task.

2.  **Implement Agent Core Processing Loop:**

    - **File:** `agents/base_agent.py` (or potentially add to specialized agents if behavior differs significantly).
    - **Logic:**
      - Add a new async method `async def run_processing_loop(self):`. This loop will be the agent's main "heartbeat".
      - Inside the loop:
        - Call `await self.check_for_new_tasks()` (implement this method, see next step).
        - Call `await self.process_incoming_messages()` (implement this method, see step after next).
        - Include `await asyncio.sleep(interval)` (e.g., 5-10 seconds) to prevent busy-waiting.
        - Add error handling (try/except) around method calls.
      - This loop needs to be started when an agent is "activated" (requires defining agent lifecycle management beyond simple creation). For now, it could be invoked manually via the CLI for testing.

3.  **Implement `check_for_new_tasks`:**

    - **File:** `agents/base_agent.py`
    - **Logic:**
      - Query the `tasks` table for tasks where `assigned_to == self.agent_id` and `status == 'BACKLOG'` (or 'ASSIGNED').
      - For each new task found:
        - Log the discovery.
        - Update the task status to 'IN_PROGRESS' (via `ScrumMasterAgent.update_task_status` or directly via DB call/Celery task `update_task_status_task`).
        - Call a new method `await self.handle_task(task_details)` (pass the fetched task data).

4.  **Implement `process_incoming_messages`:**

    - **File:** `agents/base_agent.py`
    - **Logic:**
      - Call `messages = await self.receive_messages(limit=10)` (fetches recent messages from DB).
      - Iterate through messages:
        - Check if the message has already been processed (requires adding a `processed_at` timestamp or status to `agent_messages` table, or tracking processed IDs in agent memory).
        - If not processed:
          - Based on `message.message_type`, call specific handlers (e.g., `if message.message_type == MessageType.TASK_ASSIGNMENT: await self.handle_task_assignment_message(message)`).
          - Mark message as processed.

5.  **Implement `handle_task` / `handle_task_assignment_message`:**
    - **File:** `agents/base_agent.py` (or override in specialized agents).
    - **Logic:**
      - These methods contain the core logic for _acting_ on a task.
      - Extract necessary details (task ID, description, related artifacts) from the task data or message.
      - Based on the agent's type and the task details, invoke the appropriate specialized method (e.g., a `BackendDeveloperAgent` would call `self.implement_api_endpoint` if the task is for API implementation).
      - This is where the agent's specific capabilities are executed.

### 3. Project Kickoff Mechanism

**Goal:** Define a clear entry point to start analyzing requirements for a new project.

**Chosen Approach:** Implement both CLI command and API endpoint.

**Actionable Steps:**

1.  **Add CLI Kickoff Command:**

    - **File:** `agents/cli/agent_cli.py`
    - **Logic:**
      - Add a new command, e.g., `project kickoff`.
      - Add argument `--description` (required).
      - In the handler for this command, call the `dispatch_celery_task` method (created in step 1.1) to trigger `analyze_requirements_task` with the provided description.
      - Example command structure: `python agent_cli.py project kickoff --description "Build a simple todo app"`

2.  **Add API Kickoff Endpoint:**
    - **File:** `app/api/endpoints/projects.py` (create this file).
    - **File:** `app/main.py` (update to include the new router).
    - **Logic:**
      - Create a POST endpoint like `/projects/kickoff`.
      - Define a Pydantic model for the request body containing `project_description: str`.
      - In the endpoint implementation, call the Celery task `analyze_requirements_task.delay(project_description=payload.project_description)`.
      - Return a confirmation response.

### 4. Celery Beat Usage

**Goal:** Enable scheduled tasks if required by the system's logic.

**Actionable Steps:**

1.  **Identify Need for Scheduled Tasks:**
    - Review agent logic (especially `ScrumMasterAgent` methods like `schedule_ceremonies`, `facilitate_standup`). Do any need to run periodically (e.g., daily standup trigger at a specific time)?
2.  **Define Scheduled Tasks (If Needed):**
    - **File:** `agents/tasks/celery_app.py`
    - **Logic:** Use Celery's beat schedule configuration within `app.conf.beat_schedule`.
    - Example:
      ```python
      app.conf.beat_schedule = {
          'trigger-daily-standup-check': {
              'task': 'agents.tasks.agent_tasks.trigger_standup_task', # Needs to be created
              'schedule': crontab(hour=9, minute=0), # Run daily at 9:00 AM UTC
          },
      }
      app.conf.timezone = 'UTC'
      ```
    - Create the actual Celery task (e.g., `trigger_standup_task`) in `agents/tasks/agent_tasks.py`. This task might query active sprints and notify the Scrum Master or directly trigger the standup facilitation logic.
    - Ensure the `celery_beat` service in `docker-compose.yml` is correctly configured to use a persistent scheduler (like `django_celery_beat.schedulers:DatabaseScheduler` if DB persistence is desired, requires adding Django dependencies) or Celery's default persistent scheduler.

## Iteration 3: Implementing the Development & QA Loop

### 1. Autonomous Dev Loop Triggering

**Goal:** Connect task assignment to developer action, and code commit to QA action.

**Actionable Steps:**

1.  **Developer Task Trigger:**
    - Implement **Iteration 2, Missing Feature #2 (Agent Task Consumption/Notification)** as described above. This ensures the Developer agent receives and acts on `TASK_ASSIGNMENT` messages/tasks.
2.  **QA Trigger after Commit:**
    - **Option A (Agent Message):**
      - **File:** `agents/specialized/backend_developer.py` (in `implement_api_endpoint` or `fix_code_issue`).
      - **Logic:** After a successful `self.git_client.commit_changes`, create and send an `AgentMessage` to the `QAAgent` (requires knowing the QA agent's ID, possibly via task context or a lookup).
        - `message_type`: `MessageType.CODE_COMMITTED`.
        - `content`: f"Code committed for task {related_task_id}. Commit hash: {commit_hash}".
        - `related_task`: `related_task_id`.
        - `metadata`: `{ "commit_hash": commit_hash, "files_changed": created_files }`.
      - The `QAAgent` needs to implement handling for `CODE_COMMITTED` messages in its `process_incoming_messages` loop (see Iteration 2, Action 2.4), which should then trigger `self.run_tests`.
    - **Option B (CI Trigger - Preferred):** Rely on the CI system (GitHub Actions) to trigger QA. See **Missing Feature #2 (CI/Webhook Integration)** below. This decouples the Dev agent from directly triggering QA.

### 2. CI/Webhook Integration

**Goal:** Automatically run QA tests when code is committed/pushed.

**Chosen Approach:** GitHub Actions workflow triggers a Celery task.

**Actionable Steps:**

1.  **Define GitHub Actions Workflow:**

    - **File:** `.github/workflows/ci.yml` (create or modify).
    - **Logic:**
      - Trigger on `push` to main/develop branches (or relevant branches).
      - Job 1: Checkout code, setup Python, install dependencies, run linters (`ruff`, `black --check`), run `pytest`.
      - **(Optional but Recommended) Job 2 (Trigger QA Agent):**
        - If Job 1 passes, make an authenticated API call to a new endpoint in the FastAPI app (e.g., POST `/ci/trigger-qa`).
        - Pass context like commit hash, branch name, triggering user/event.
        - Use GitHub secrets for API authentication keys.

2.  **Create API Endpoint for CI Trigger:**

    - **File:** `app/api/endpoints/ci.py` (create).
    - **File:** `app/main.py` (add router).
    - **Logic:**
      - Define POST `/ci/trigger-qa`.
      - Implement authentication (e.g., check for a secret token passed from GitHub Actions).
      - Define a Pydantic model for the payload (commit hash, etc.).
      - Dispatch a new Celery task `run_qa_tests_task(commit_hash=..., ...)`.

3.  **Create `run_qa_tests_task` Celery Task:**
    - **File:** `agents/tasks/agent_tasks.py`.
    - **Logic:**
      - This task initializes components (DB, LLM, etc.).
      - It needs to instantiate or locate the relevant `QAAgent` instance. (How to get the agent ID? Maybe have a designated QA agent ID in config, or query DB for active QA agents).
      - Invoke `qa_agent.run_tests()`.
      - Process the results: If tests fail, trigger the bug reporting flow (see next section). If tests pass, update the related task status (e.g., to 'QA_PASSED' or 'READY_FOR_DEPLOY').

### 3. Bug Reporting -> Fixing Loop

**Goal:** Enable QA to report bugs that trigger the Developer agent to fix them.

**Actionable Steps:**

1.  **Enhance QA Bug Reporting:**

    - **File:** `agents/specialized/qa_agent.py` (within `run_tests` result handling and/or `report_bug` method).
    - **Logic:**
      - When `run_tests` fails and `_analyze_test_failures` provides analysis:
        - **Option A (Create Bug Task):**
          - Call a `ScrumMasterAgent` method (or dispatch a Celery task) to create a new task in the DB.
          - Task details: type='BUG', title based on failed test, description contains failure analysis/logs, link to original task, potentially assign back to the original developer ID (if available from the task context).
        - **Option B (Send Bug Message):**
          - Send an `AgentMessage` (type `BUG_REPORT`) directly to the relevant `BackendDeveloperAgent` (or Scrum Master if dev unknown). Include analysis, logs, related task ID, commit hash.

2.  **Implement Developer Bug Handling:**
    - **File:** `agents/base_agent.py` / `agents/specialized/backend_developer.py` (within the agent's processing loop/message handling logic from Iteration 2, Action 2).
    - **Logic:**
      - The agent's loop needs to recognize BUG tasks (if fetched via `check_for_new_tasks`) or `BUG_REPORT` messages (if received via `process_incoming_messages`).
      - When a bug is identified:
        - Extract relevant details (file path, issue description, test failure info).
        - Call `self.fix_code_issue(file_path=..., issue_description=..., test_failure=...)`.
        - The `fix_code_issue` method (already partially defined) should use the LLM to generate the fix, write the file, and commit the changes using `GitClient`.
        - After committing the fix, the loop triggers again (Dev -> Commit -> CI -> QA).

### 4. Enhanced Codebase Analysis

**Goal:** Improve the Developer agent's ability to understand existing code before generating new code or fixes.

**Actionable Steps:**

1.  **Refactor `_analyze_codebase`:**

    - **File:** `agents/specialized/backend_developer.py`.
    - **Logic:**
      - Remove the current basic DB query.
      - Ensure `self.memory_search` is initialized (requires DB, VectorMemory, LLMProvider passed during agent creation).
      - Take the current task description or implementation goal as input.
      - Generate an embedding for the input description using `self.llm_provider.generate_embeddings`.
      - Call `results = await self.memory_search.search_entities(query_embedding=..., entity_types=['Code', 'Artifact'], limit=5, ...)`. Filter potentially by language ('python') using metadata filters if implemented in `search_entities`. (Note: Assumes code is stored as 'Code' entities in vector memory - requires a separate process to index the codebase).
      - Process `results`: Extract relevant file paths or content snippets from the search results metadata.
      - Format this retrieved context into a string to be included in the prompt sent to the LLM during `implement_api_endpoint` or `fix_code_issue`. Example context: "Found relevant existing code: /path/to/similar_module.py (implements ...), /path/to/utils.py (contains helper function ...)."

2.  **Code Indexing (Prerequisite):**
    - **Missing:** A process to actually populate the `EnhancedVectorMemory` with embeddings of the existing codebase files (`entity_type='Code'`).
    - **Task (Separate):** Implement a codebase indexing mechanism:
      - This could be a standalone script or a Celery task.
      - It should recursively scan project directories (respecting `.gitignore`).
      - For each source file (`.py`, `.js`, etc.):
        - Read the content.
        - Generate an embedding using the LLM provider.
        - Store it in vector memory using `vector_memory.store_entity` with `entity_type='Code'`, `entity_id=file_path`, content, embedding, and relevant metadata (language, module path).
      - This indexing should run initially and potentially be re-run after significant changes.

### 5. Developer Task Status Updates

**Goal:** Ensure Developer agents report their progress by updating task statuses.

**Actionable Steps:**

1.  **Integrate Status Updates into Workflow:**
    - **File:** `agents/specialized/backend_developer.py`.
    - **Logic:**
      - At the beginning of methods like `implement_api_endpoint` or `fix_code_issue` (after receiving the task), dispatch the `update_task_status_task` Celery task (or call SM method) to set the status to `IN_PROGRESS`. Pass the `related_task_id`.
      - After successfully committing code via `git_client.commit_changes`, dispatch `update_task_status_task` to set the status to `IN_REVIEW` or `PENDING_QA`.
      - If the implementation/fix fails, potentially update status to `BLOCKED` or `FAILED`.
      - Ensure the `related_task_id` is passed through these methods.

```

```
