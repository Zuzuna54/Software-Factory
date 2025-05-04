# Database Schema Documentation

This document provides details on the PostgreSQL database schema used by the Autonomous AI Development Team.

**Schema Source:** The authoritative SQL schema is defined in `infra/database/schema.sql` and applied initially via `infra/docker/postgres/init.sql`. Future changes should be managed via Alembic migrations.

**Extensions Used:**

- `uuid-ossp`: For generating UUID primary keys.
- `pgvector`: For storing and searching vector embeddings.

## Tables

### `agents`

Stores information about each registered AI agent.

| Column         | Type         | Constraints                   | Description                             |
| -------------- | ------------ | ----------------------------- | --------------------------------------- |
| `agent_id`     | UUID         | PRIMARY KEY, DEFAULT gen_uuid | Unique identifier for the agent         |
| `agent_type`   | VARCHAR(50)  | NOT NULL                      | Role type (e.g., PM, ScrumMaster)       |
| `agent_name`   | VARCHAR(100) | NOT NULL                      | Human-readable name of the agent        |
| `created_at`   | TIMESTAMP    | NOT NULL, DEFAULT NOW()       | Timestamp when the agent was registered |
| `capabilities` | JSONB        |                               | Agent-specific skills/tools             |
| `active`       | BOOLEAN      | NOT NULL, DEFAULT TRUE        | Whether the agent is currently active   |

### `agent_messages`

Records all structured messages exchanged between agents.

| Column              | Type         | Constraints                           | Description                                    |
| ------------------- | ------------ | ------------------------------------- | ---------------------------------------------- |
| `message_id`        | UUID         | PRIMARY KEY, DEFAULT gen_uuid         | Unique identifier for the message              |
| `timestamp`         | TIMESTAMP    | NOT NULL, DEFAULT NOW()               | Time the message was sent/recorded             |
| `sender_id`         | UUID         | REFERENCES agents(agent_id)           | ID of the sending agent                        |
| `receiver_id`       | UUID         | REFERENCES agents(agent_id)           | ID of the receiving agent                      |
| `message_type`      | VARCHAR(50)  | NOT NULL                              | Type of message (REQUEST, INFORM, ALERT, etc.) |
| `content`           | TEXT         | NOT NULL                              | The main content/payload of the message        |
| `related_task_id`   | UUID         |                                       | Optional reference to a related task ID        |
| `metadata`          | JSONB        |                                       | Additional structured data (e.g., severity)    |
| `parent_message_id` | UUID         | REFERENCES agent_messages(message_id) | Reference to a parent message for threading    |
| `context_vector`    | VECTOR(1536) |                                       | Vector embedding for semantic search           |

### `agent_activities`

Logs significant actions performed by agents.

| Column              | Type         | Constraints                   | Description                                         |
| ------------------- | ------------ | ----------------------------- | --------------------------------------------------- |
| `activity_id`       | UUID         | PRIMARY KEY, DEFAULT gen_uuid | Unique identifier for the activity log              |
| `agent_id`          | UUID         | REFERENCES agents(agent_id)   | ID of the agent performing the activity             |
| `timestamp`         | TIMESTAMP    | NOT NULL, DEFAULT NOW()       | Time the activity occurred                          |
| `activity_type`     | VARCHAR(100) | NOT NULL                      | Type of activity (CodeGeneration, Review, etc.)     |
| `description`       | TEXT         | NOT NULL                      | Human-readable description of the activity          |
| `thought_process`   | TEXT         |                               | Agent's internal reasoning/chain-of-thought         |
| `input_data`        | JSONB        |                               | Structured input data used for the activity         |
| `output_data`       | JSONB        |                               | Structured output data produced by the activity     |
| `related_files`     | TEXT[]       |                               | List of file paths relevant to the activity         |
| `decisions_made`    | JSONB        |                               | Structured record of decisions made during activity |
| `execution_time_ms` | INTEGER      |                               | Time taken for the activity in milliseconds         |

### `artifacts`

Stores various project artifacts generated or managed by agents.

| Column             | Type         | Constraints                       | Description                                         |
| ------------------ | ------------ | --------------------------------- | --------------------------------------------------- |
| `artifact_id`      | UUID         | PRIMARY KEY, DEFAULT gen_uuid     | Unique identifier for the artifact                  |
| `artifact_type`    | VARCHAR(50)  | NOT NULL                          | Type (Requirement, UserStory, Design, Code, Test)   |
| `title`            | VARCHAR(255) | NOT NULL                          | Title or name of the artifact                       |
| `content`          | TEXT         |                                   | Main content (e.g., code, description, design spec) |
| `created_at`       | TIMESTAMP    | NOT NULL, DEFAULT NOW()           | Timestamp when the artifact was created             |
| `created_by`       | UUID         | REFERENCES agents(agent_id)       | Agent ID that created the artifact                  |
| `last_modified_at` | TIMESTAMP    |                                   | Timestamp of the last modification                  |
| `last_modified_by` | UUID         | REFERENCES agents(agent_id)       | Agent ID that last modified the artifact            |
| `parent_id`        | UUID         | REFERENCES artifacts(artifact_id) | Optional parent artifact ID (for hierarchy)         |
| `status`           | VARCHAR(50)  | NOT NULL                          | Current status (Draft, Review, Approved, etc.)      |
| `metadata`         | JSONB        |                                   | Additional properties (e.g., language, priority)    |
| `version`          | INTEGER      | NOT NULL, DEFAULT 1               | Version number of the artifact                      |
| `content_vector`   | VECTOR(1536) |                                   | Vector embedding for semantic search                |

### `tasks`

Tracks development tasks assigned to agents.

| Column              | Type         | Constraints                   | Description                                        |
| ------------------- | ------------ | ----------------------------- | -------------------------------------------------- |
| `task_id`           | UUID         | PRIMARY KEY, DEFAULT gen_uuid | Unique identifier for the task                     |
| `title`             | VARCHAR(255) | NOT NULL                      | Task title                                         |
| `description`       | TEXT         | NOT NULL                      | Detailed description of the task                   |
| `created_at`        | TIMESTAMP    | NOT NULL, DEFAULT NOW()       | Timestamp when the task was created                |
| `created_by`        | UUID         | REFERENCES agents(agent_id)   | Agent ID that created the task                     |
| `assigned_to`       | UUID         | REFERENCES agents(agent_id)   | Agent ID assigned to the task                      |
| `sprint_id`         | UUID         | REFERENCES sprints(sprint_id) | Optional reference to the sprint ID                |
| `priority`          | INTEGER      | NOT NULL                      | Task priority level                                |
| `status`            | VARCHAR(50)  | NOT NULL                      | Current status (Backlog, InProgress, Review, Done) |
| `estimated_effort`  | FLOAT        |                               | Estimated effort (e.g., story points, hours)       |
| `actual_effort`     | FLOAT        |                               | Actual effort spent                                |
| `dependencies`      | UUID[]       |                               | List of task IDs this task depends on              |
| `metadata`          | JSONB        |                               | Additional task data (e.g., related feature)       |
| `related_artifacts` | UUID[]       |                               | List of artifact IDs related to this task          |

### `meetings`

Stores records of scheduled or completed agent meetings.

| Column         | Type        | Constraints                   | Description                                                    |
| -------------- | ----------- | ----------------------------- | -------------------------------------------------------------- |
| `meeting_id`   | UUID        | PRIMARY KEY, DEFAULT gen_uuid | Unique identifier for the meeting                              |
| `meeting_type` | VARCHAR(50) | NOT NULL                      | Type (Planning, StandUp, Review, Retrospective, Brainstorming) |
| `start_time`   | TIMESTAMP   | NOT NULL, DEFAULT NOW()       | Scheduled or actual start time                                 |
| `end_time`     | TIMESTAMP   |                               | Actual end time                                                |
| `participants` | UUID[]      |                               | List of participant agent IDs (FK handled in app logic)        |
| `summary`      | TEXT        |                               | Text summary of the meeting                                    |
| `decisions`    | JSONB       |                               | Structured record of decisions made                            |
| `action_items` | JSONB       |                               | Structured list of action items assigned                       |

### `meeting_conversations`

Logs the transcript of messages within a meeting.

| Column            | Type        | Constraints                     | Description                                       |
| ----------------- | ----------- | ------------------------------- | ------------------------------------------------- |
| `conversation_id` | UUID        | PRIMARY KEY, DEFAULT gen_uuid   | Unique identifier for the message log             |
| `meeting_id`      | UUID        | REFERENCES meetings(meeting_id) | ID of the meeting this message belongs to         |
| `sequence_number` | INTEGER     | NOT NULL                        | Order of the message within the meeting           |
| `timestamp`       | TIMESTAMP   | NOT NULL, DEFAULT NOW()         | Time the message was sent                         |
| `speaker_id`      | UUID        |                                 | Agent ID of the speaker (FK handled in app logic) |
| `message`         | TEXT        | NOT NULL                        | Content of the message                            |
| `message_type`    | VARCHAR(50) |                                 | Optional classification (Question, Answer, etc.)  |
| `context`         | JSONB       |                                 | Optional context related to the message           |

### `sprints`

Tracks development sprints.

| Column        | Type         | Constraints                   | Description                                             |
| ------------- | ------------ | ----------------------------- | ------------------------------------------------------- |
| `sprint_id`   | UUID         | PRIMARY KEY, DEFAULT gen_uuid | Unique identifier for the sprint                        |
| `sprint_name` | VARCHAR(255) | NOT NULL                      | Name of the sprint (e.g., "Sprint 2024-07-15")          |
| `start_date`  | TIMESTAMP    | NOT NULL                      | Start date of the sprint                                |
| `end_date`    | TIMESTAMP    | NOT NULL                      | End date of the sprint                                  |
| `goal`        | TEXT         |                               | The primary goal of the sprint                          |
| `created_by`  | UUID         | REFERENCES agents(agent_id)   | Agent ID that created the sprint (usually Scrum Master) |
| `status`      | VARCHAR(50)  | NOT NULL                      | Status (PLANNING, IN_PROGRESS, COMPLETED)               |

### `project_vision`

Stores the high-level vision and goals for a project.

| Column             | Type         | Constraints                 | Description                                       |
| ------------------ | ------------ | --------------------------- | ------------------------------------------------- |
| `vision_id`        | UUID         | PRIMARY KEY                 | Unique identifier for the vision document         |
| `project_id`       | UUID         | NOT NULL                    | Identifier for the project this vision belongs to |
| `title`            | VARCHAR(255) | NOT NULL                    | Title of the project vision                       |
| `vision_statement` | TEXT         | NOT NULL                    | The core vision statement                         |
| `target_audience`  | TEXT         |                             | Description of the target users/audience          |
| `key_goals`        | JSONB        |                             | List of key goals for the project                 |
| `success_metrics`  | JSONB        |                             | How success will be measured                      |
| `constraints`      | JSONB        |                             | Known constraints or limitations                  |
| `created_by`       | UUID         | REFERENCES agents(agent_id) | Agent ID that created the vision (usually PM)     |
| `created_at`       | TIMESTAMP    | NOT NULL, DEFAULT NOW()     | Creation timestamp                                |
| `last_modified_at` | TIMESTAMP    |                             | Last modification timestamp                       |
| `status`           | VARCHAR(50)  | NOT NULL                    | Status (e.g., DRAFT, ACTIVE, ARCHIVED)            |

## Indexes

Various indexes are created on foreign keys and frequently queried columns (like timestamps, status, type) to optimize query performance. See `infra/database/schema.sql` for the full list.
