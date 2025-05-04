# Frontend Iteration 1: Dashboard Implementation

## Overview

This document outlines the frontend development tasks required to build the user interface for the Autonomous AI Team Dashboard, based on the backend infrastructure and APIs established up to Iteration 5. The goal is to create a functional, real-time monitoring and observability tool.

## Key Technologies

- Next.js (App Router)
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Redux Toolkit (for state management)
- Socket.IO Client (for real-time updates)

## Implementation Tasks

### 1. Global Setup (Layout, State, Real-time)

- **File:** `dashboard/src/app/layout.tsx`
- **Tasks:**
  - [ ] **Integrate Redux Toolkit:**
    - Set up the Redux store (`dashboard/src/lib/store.ts` or similar).
    - Define initial slices (e.g., `agentsSlice`, `tasksSlice`, `logsSlice`, `notificationsSlice`).
    - Wrap the root layout's children with the Redux `<Provider>`.
  - [ ] **Implement Core Layout:**
    - Create persistent layout components (e.g., `Sidebar`, `Header`) using shadcn/ui.
    - Include navigation links to different dashboard pages (Overview, Agents, Tasks, Logs, Metrics, Settings).
    - Integrate the layout components into `RootLayout`.
  - [ ] **Integrate Socket.IO Client:**
    - Create a Socket.IO client instance, connecting to the backend's `/ws` endpoint (likely in a global context or effect within the layout).
    - Handle connection/disconnection events.
    - Set up listeners for backend events (`agent_registered`, `message_sent`, `activity_logged`, `error_occurred`, etc.).
    - Dispatch Redux actions based on received Socket.IO events to update the relevant state slices.
  - [ ] **Implement Notifications:**
    - Add shadcn `Toaster` component to the root layout.
    - Create a mechanism (e.g., a Redux middleware or slice) to trigger toasts based on specific Socket.IO events or application actions (e.g., errors).

### 2. Dashboard Overview Page (`/`)

- **File:** `dashboard/src/app/page.tsx`
- **Tasks:**
  - [ ] **Fetch Summary Data:**
    - Define necessary backend API endpoint(s) to provide aggregated summary data (e.g., agent count, active tasks, recent errors).
    - Fetch this data using standard React/Next.js data fetching patterns (e.g., `useEffect`, Server Components, or a client-side fetching library).
  - [ ] **Display Summary:**
    - Create reusable `StatCard` components (using shadcn `Card`).
    - Display key metrics fetched from the API.
  - [ ] **Activity Feed:**
    - Create an `ActivityFeed` component.
    - Subscribe to relevant Redux state (updated by Socket.IO listeners) or directly listen to Socket.IO events to display a stream of recent activities (e.g., agents registered, tasks started/completed, errors).
  - [ ] **Loading/Error States:** Implement appropriate UI feedback for data loading and potential API errors.

### 3. Agents List Page (`/agents`)

- **File:** `dashboard/src/app/agents/page.tsx`
- **Tasks:**
  - [ ] **Fetch Agent List:** Fetch data from `/api/v1/dashboard/agents`.
  - [ ] **Display List:** Use shadcn `Table` or a card grid to display agent ID, name, type, status (active/inactive), and creation time.
  - [ ] **Navigation:** Link each agent row/card to its corresponding detail page (`/agents/[agentId]`).
  - [ ] **Real-time Updates:** Update the list dynamically when `agent_registered` events are received via Socket.IO (or via Redux state updates).
  - [ ] **Loading/Error States:** Implement UI feedback.

### 4. Agent Detail Page (`/agents/[agentId]`)

- **File:** `dashboard/src/app/agents/[agentId]/page.tsx`
- **Tasks:**
  - [ ] **Fetch Agent Details:** Fetch data from `/api/v1/dashboard/agents/{agentId}` using the `agentId` from route parameters.
  - [ ] **Display Details:** Show agent ID, name, type, status, capabilities, and creation time.
  - [ ] **Display Activities:** Use a table or list to show the `recent_activities` data.
  - [ ] **Display Messages:** Use a table or list to show the `recent_messages` data (sender, receiver, type, preview).
  - [ ] **Layout:** Consider using shadcn `Tabs` to organize details, activities, and messages.
  - [ ] **Real-time Updates:** Potentially refresh activity/message lists based on Socket.IO events or implement polling.
  - [ ] **Loading/Error States:** Implement UI feedback.

### 5. Tasks Page (`/tasks`)

- **File:** `dashboard/src/app/tasks/page.tsx`
- **Tasks:**
  - [ ] **Define Task API:** Create a backend endpoint (e.g., `/api/v1/dashboard/tasks`) to fetch tasks, potentially with filtering/sorting options.
  - [ ] **Fetch Task Data:** Fetch tasks from the new API endpoint.
  - [ ] **Display Tasks:** Implement a shadcn `DataTable` (table with sorting, filtering, pagination) or a Kanban-style board to display tasks. Show relevant fields like ID, title, status, assignee, priority, sprint ID.
  - [ ] **Real-time Updates:** Update task statuses or list based on relevant Socket.IO events (requires corresponding backend event emissions).
  - [ ] **Loading/Error States:** Implement UI feedback.

### 6. Logs Page (`/logs`)

- **File:** `dashboard/src/app/logs/page.tsx`
- **Tasks:**
  - [ ] **Implement Log View:** Use shadcn `Table` or a dedicated log viewer component.
  - [ ] **Implement Filtering:** Add UI controls (e.g., dropdowns, input fields) to filter logs by `agent_id` and `activity_type`.
  - [ ] **Implement Pagination:** Add controls to fetch logs page by page using `limit` and `offset` parameters.
  - [ ] **Fetch Log Data:** Fetch data from `/api/v1/dashboard/logs` using the filter and pagination parameters.
  - [ ] **Display Logs:** Show timestamp, agent ID, activity type, description, and potentially allow viewing detailed input/output data (e.g., in a modal).
  - [ ] **Real-time Updates:** Optionally append new logs received via the `activity_logged` Socket.IO event.
  - [ ] **Loading/Error States:** Implement UI feedback.

### 7. Metrics Page (`/metrics`)

- **File:** `dashboard/src/app/metrics/page.tsx`
- **Tasks:**
  - [ ] **Fetch Metrics Data:** Fetch data periodically or on demand from the `/metrics` endpoint.
  - [ ] **Install Charting Library:** Add a charting library like `recharts` or `nivo` (`pnpm add recharts`).
  - [ ] **Visualize Metrics:** Create chart components (line charts, bar charts, gauges) to display key metrics:
    - Counters (e.g., `agent_messages_sent_total`, `agent_think_requests_total`)
    - Gauges (if implemented in backend)
    - Timers (e.g., average `agent_think_duration_seconds`).
  - [ ] **Loading/Error States:** Implement UI feedback.

### 8. Settings Page (`/settings`)

- **File:** `dashboard/src/app/settings/page.tsx`
- **Tasks:**
  - [ ] **Implement Forms:** Add placeholder form elements using shadcn components for potential future settings (e.g., API keys, model configurations). (Functionality depends on future backend support).

## Verification

- All pages should render correctly and fetch data from the backend APIs.
- Real-time updates via Socket.IO should be reflected in the UI (activity feeds, notifications).
- Filtering and pagination should work as expected on the Logs page.
- Metrics charts should display data fetched from the `/metrics` endpoint.
- The UI should be responsive and adhere to the styling provided by Tailwind and shadcn/ui.
