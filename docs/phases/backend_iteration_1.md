# Backend Iteration 1: Supporting the Dashboard

## Overview

This document outlines the backend development tasks required to support the frontend implementation described in `frontend-iteration_1.md`. The focus is on providing the necessary API endpoints and real-time event emissions for the dashboard's core functionality.

## Why This Phase Matters

The backend must provide the data and real-time updates the dashboard needs to function effectively. Implementing these supporting features enables the crucial observability layer planned in Iteration 5.

## Expected Outcomes

After completing this phase, the backend will provide:

1.  An API endpoint serving aggregated system summary data.
2.  API endpoints for retrieving and filtering task information.
3.  Real-time Socket.IO events related to task lifecycle changes.

## Implementation Tasks

### Task 1: Dashboard Summary API Endpoint

- **What needs to be done:** Create a new API endpoint that aggregates key system statistics for the dashboard overview page.
- **Why this task is necessary:** The frontend overview page needs a single source for high-level statistics like agent counts, task status distribution, etc.
- **Files to be created/updated:**
  - `app/api/endpoints/dashboard.py`: Add a new route (e.g., `/summary`).
- **Implementation guidelines:**
  - Define a Pydantic model for the summary response (e.g., `DashboardSummaryResponse`).
  - The endpoint should query:
    - `agents` table for total/active agent counts.
    - `tasks` table for counts by status (BACKLOG, ASSIGNED, IN_PROGRESS, REVIEW, DONE).
    - Optionally, `agent_activities` for recent error counts (e.g., `activity_type` LIKE '%Error').
  - Return the aggregated data in the defined response model.
  - Add the new route to the `dashboard.router`.

### Task 2: Task API Endpoints

- **What needs to be done:** Create API endpoints for listing and potentially retrieving details about tasks.
- **Why this task is necessary:** The dashboard's Tasks page needs to fetch and display task information, including filtering and pagination.
- **Files to be created/updated:**
  - `app/api/endpoints/dashboard.py`: Add new routes (e.g., `/tasks`, potentially `/tasks/{task_id}`).
- **Implementation guidelines:**
  - Define a route `GET /tasks` in `dashboard.router`.
  - Accept query parameters for filtering (e.g., `status`, `agent_id`, `sprint_id`) and pagination (`limit`, `offset`).
  - Construct a dynamic SQL query based on the provided filters to fetch data from the `tasks` table.
  - Return a list of tasks (consider creating a Pydantic model `TaskResponse`).
  - Optionally, add a `GET /tasks/{task_id}` endpoint if detailed task views are anticipated.

### Task 3: Task-Related Event Emission

- **What needs to be done:** Modify existing backend logic to emit Socket.IO events when tasks are created, assigned, or their status changes.
- **Why this task is necessary:** To enable real-time updates on the dashboard's Tasks page without requiring constant polling.
- **Files to be created/updated:**
  - `agents/specialized/scrum_master.py` (specifically `_create_sprint_tasks`, `assign_task`, `update_task_status` methods).
  - OR `agents/tasks/agent_tasks.py` (if task logic is primarily handled async via Celery, modify the relevant task wrappers).
  - `app/main.py` (ensure `emit_event` function is available).
- **Implementation guidelines:**
  - Import the `emit_event` function from `app.main` into the relevant agent or task file.
  - **Task Creation:** After successfully inserting tasks in `_create_sprint_tasks` (or its Celery wrapper), call `await emit_event("task_created", {task_data})` for each new task.
  - **Task Assignment:** After successfully updating the task assignee in `assign_task` (or its Celery wrapper), call `await emit_event("task_assigned", {"task_id": ..., "agent_id": ...})`.
  - **Task Status Update:** After successfully updating the task status in `update_task_status` (or its Celery wrapper), call `await emit_event("task_status_updated", {"task_id": ..., "status": ...})`.
  - Ensure the event data includes necessary information for the frontend to update its state.

## Verification

- Test the new `/summary` endpoint returns correct aggregated data.
- Test the new `/tasks` endpoint with various filters and pagination parameters.
- Use a simple Socket.IO client or the dashboard frontend (once developed) to verify that `task_created`, `task_assigned`, and `task_status_updated` events are emitted correctly when corresponding actions occur in the backend.
