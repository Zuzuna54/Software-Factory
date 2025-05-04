# infra/docker/postgres/init.sql

-- This script will be executed when the PostgreSQL container starts for the first time.
-- It applies the main schema to the database.

-- Note: Ensure the database name (agent_team) and user (agent_user) match docker-compose.yml

\c agent_team agent_user

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Agent Metadata
CREATE TABLE agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    capabilities JSONB,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Inter-Agent Messages
CREATE TABLE agent_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    sender_id UUID REFERENCES agents(agent_id),
    receiver_id UUID REFERENCES agents(agent_id),
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    related_task_id UUID,
    metadata JSONB,
    parent_message_id UUID REFERENCES agent_messages(message_id),
    context_vector VECTOR(1536)
);

-- Agent Activities and Decisions
CREATE TABLE agent_activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(agent_id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    activity_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    thought_process TEXT,
    input_data JSONB,
    output_data JSONB,
    related_files TEXT[],
    decisions_made JSONB,
    execution_time_ms INTEGER
);

-- Project Artifacts
CREATE TABLE artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    artifact_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES agents(agent_id),
    last_modified_at TIMESTAMP,
    last_modified_by UUID REFERENCES agents(agent_id),
    parent_id UUID REFERENCES artifacts(artifact_id),
    status VARCHAR(50) NOT NULL,
    metadata JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    content_vector VECTOR(1536)
);

-- Tasks and Assignments
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES agents(agent_id),
    assigned_to UUID REFERENCES agents(agent_id),
    sprint_id UUID,
    priority INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL,
    estimated_effort FLOAT,
    actual_effort FLOAT,
    dependencies UUID[],
    metadata JSONB,
    related_artifacts UUID[]
);

-- Meetings and Conversations
CREATE TABLE meetings (
    meeting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_type VARCHAR(50) NOT NULL,
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    participants UUID[],
    summary TEXT,
    decisions JSONB,
    action_items JSONB
);

CREATE TABLE meeting_conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(meeting_id),
    sequence_number INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    speaker_id UUID,
    message TEXT NOT NULL,
    message_type VARCHAR(50),
    context JSONB
);

-- Sprints Table (if needed, based on iteration 2)
CREATE TABLE sprints (
    sprint_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sprint_name VARCHAR(255) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    goal TEXT,
    created_by UUID REFERENCES agents(agent_id),
    status VARCHAR(50) NOT NULL -- e.g., PLANNING, IN_PROGRESS, COMPLETED
);

-- Project Vision Table (based on iteration 2)
CREATE TABLE project_vision (
    vision_id UUID PRIMARY KEY,
    project_id UUID NOT NULL, -- Add project reference
    title VARCHAR(255) NOT NULL,
    vision_statement TEXT NOT NULL,
    target_audience TEXT,
    key_goals JSONB,
    success_metrics JSONB,
    constraints JSONB,
    created_by UUID REFERENCES agents(agent_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_modified_at TIMESTAMP,
    status VARCHAR(50) NOT NULL
);

-- Indexes (Copied from schema.sql, adjust as needed)
CREATE INDEX idx_agent_messages_sender ON agent_messages(sender_id);
CREATE INDEX idx_agent_messages_receiver ON agent_messages(receiver_id);
CREATE INDEX idx_agent_activities_agent ON agent_activities(agent_id);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX idx_artifacts_creator ON artifacts(created_by);
CREATE INDEX idx_agent_messages_timestamp ON agent_messages(timestamp DESC);
CREATE INDEX idx_agent_activities_timestamp ON agent_activities(timestamp DESC);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_meeting_conversations_meeting_id ON meeting_conversations(meeting_id, sequence_number);

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE agent_team TO agent_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO agent_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO agent_user; 