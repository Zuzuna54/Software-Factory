# Database Schema

This document describes the database schema used by the Autonomous AI Development Team.

## Overview

Our system uses PostgreSQL with the pgvector extension for storing and retrieving all agent data, including:

- Agent metadata and capabilities
- Inter-agent messages
- Agent activities and decisions
- Project artifacts
- Tasks and assignments
- Meeting records and conversations

## Tables

### agents

Stores information about each agent in the system.

| Column       | Type         | Description                               |
| ------------ | ------------ | ----------------------------------------- |
| agent_id     | UUID         | Primary key                               |
| agent_type   | VARCHAR(50)  | Role of the agent (PM, ScrumMaster, etc.) |
| agent_name   | VARCHAR(100) | Name of the agent                         |
| created_at   | TIMESTAMP    | When the agent was created                |
| capabilities | JSONB        | Agent-specific capabilities               |
| active       | BOOLEAN      | Whether the agent is active               |

### agent_messages

Records all messages sent between agents.

| Column            | Type         | Description                             |
| ----------------- | ------------ | --------------------------------------- |
| message_id        | UUID         | Primary key                             |
| timestamp         | TIMESTAMP    | When the message was sent               |
| sender_id         | UUID         | ID of the sending agent                 |
| receiver_id       | UUID         | ID of the receiving agent               |
| message_type      | VARCHAR(50)  | Type of message (REQUEST, INFORM, etc.) |
| content           | TEXT         | Content of the message                  |
| related_task_id   | UUID         | Optional task reference                 |
| metadata          | JSONB        | Additional structured data              |
| parent_message_id | UUID         | For threaded conversations              |
| context_vector    | VECTOR(1536) | Vector embedding for semantic search    |

### agent_activities

Tracks agent activities and the decisions they make.

| Column            | Type         | Description                 |
| ----------------- | ------------ | --------------------------- |
| activity_id       | UUID         | Primary key                 |
| agent_id          | UUID         | ID of the agent             |
| timestamp         | TIMESTAMP    | When the activity occurred  |
| activity_type     | VARCHAR(100) | Type of activity            |
| description       | TEXT         | Description of the activity |
| thought_process   | TEXT         | Internal reasoning          |
| input_data        | JSONB        | Input for the activity      |
| output_data       | JSONB        | Output from the activity    |
| related_files     | TEXT[]       | Files involved              |
| decisions_made    | JSONB        | Decisions made              |
| execution_time_ms | INTEGER      | Performance tracking        |

### artifacts

Stores project artifacts produced by agents.

| Column           | Type         | Description                           |
| ---------------- | ------------ | ------------------------------------- |
| artifact_id      | UUID         | Primary key                           |
| artifact_type    | VARCHAR(50)  | Type of artifact                      |
| title            | VARCHAR(255) | Title of the artifact                 |
| content          | TEXT         | Content of the artifact               |
| created_at       | TIMESTAMP    | When the artifact was created         |
| created_by       | UUID         | Agent that created the artifact       |
| last_modified_at | TIMESTAMP    | When the artifact was last modified   |
| last_modified_by | UUID         | Agent that last modified the artifact |
| parent_id        | UUID         | Parent artifact ID                    |
| status           | VARCHAR(50)  | Status of the artifact                |
| metadata         | JSONB        | Additional properties                 |
| version          | INTEGER      | Version number                        |
| content_vector   | VECTOR(1536) | Vector embedding for semantic search  |

### tasks

Tracks tasks and their assignments.

| Column            | Type         | Description                 |
| ----------------- | ------------ | --------------------------- |
| task_id           | UUID         | Primary key                 |
| title             | VARCHAR(255) | Task title                  |
| description       | TEXT         | Task description            |
| created_at        | TIMESTAMP    | When the task was created   |
| created_by        | UUID         | Agent that created the task |
| assigned_to       | UUID         | Agent assigned to the task  |
| sprint_id         | UUID         | Sprint containing the task  |
| priority          | INTEGER      | Task priority               |
| status            | VARCHAR(50)  | Task status                 |
| estimated_effort  | FLOAT        | Estimated effort            |
| actual_effort     | FLOAT        | Actual effort               |
| dependencies      | UUID[]       | Tasks this depends on       |
| metadata          | JSONB        | Additional task data        |
| related_artifacts | UUID[]       | Related artifacts           |

### meetings

Records meetings between agents.

| Column       | Type        | Description                   |
| ------------ | ----------- | ----------------------------- |
| meeting_id   | UUID        | Primary key                   |
| meeting_type | VARCHAR(50) | Type of meeting               |
| start_time   | TIMESTAMP   | When the meeting started      |
| end_time     | TIMESTAMP   | When the meeting ended        |
| participants | UUID[]      | Participating agents          |
| summary      | TEXT        | Meeting summary               |
| decisions    | JSONB       | Decisions made                |
| action_items | JSONB       | Action items from the meeting |

### meeting_conversations

Records conversations during meetings.

| Column          | Type        | Description               |
| --------------- | ----------- | ------------------------- |
| conversation_id | UUID        | Primary key               |
| meeting_id      | UUID        | Meeting ID                |
| sequence_number | INTEGER     | Order in the conversation |
| timestamp       | TIMESTAMP   | When the message was sent |
| speaker_id      | UUID        | Agent speaking            |
| message         | TEXT        | Message content           |
| message_type    | VARCHAR(50) | Type of message           |
| context         | JSONB       | Context for the message   |
