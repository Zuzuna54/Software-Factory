-- infra/database/schema.sql

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Agent Metadata
CREATE TABLE agents (
    agent_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type VARCHAR(50) NOT NULL, -- PM, ScrumMaster, FrontendLead, etc.
    agent_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    capabilities JSONB, -- Specialized capabilities based on role
    active BOOLEAN NOT NULL DEFAULT TRUE
);

-- Inter-Agent Messages
CREATE TABLE agent_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    sender_id UUID REFERENCES agents(agent_id),
    receiver_id UUID REFERENCES agents(agent_id),
    message_type VARCHAR(50) NOT NULL, -- REQUEST, INFORM, PROPOSE, etc.
    content TEXT NOT NULL,
    related_task_id UUID, -- Optional reference to task
    metadata JSONB, -- Additional structured data
    parent_message_id UUID REFERENCES agent_messages(message_id), -- For threading
    context_vector VECTOR(1536) -- For semantic search of message content
);

-- Agent Activities and Decisions
CREATE TABLE agent_activities (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents(agent_id),
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    activity_type VARCHAR(100) NOT NULL, -- CodeGeneration, Review, Testing, etc.
    description TEXT NOT NULL,
    thought_process TEXT, -- Internal reasoning of agent
    input_data JSONB, -- What the agent worked with
    output_data JSONB, -- What the agent produced
    related_files TEXT[], -- File paths affected
    decisions_made JSONB, -- Structured record of decisions
    execution_time_ms INTEGER -- Performance tracking
);

-- Project Artifacts
CREATE TABLE artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    artifact_type VARCHAR(50) NOT NULL, -- Requirement, UserStory, Design, Code, Test, etc.
    title VARCHAR(255) NOT NULL,
    content TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES agents(agent_id),
    last_modified_at TIMESTAMP,
    last_modified_by UUID REFERENCES agents(agent_id),
    parent_id UUID REFERENCES artifacts(artifact_id), -- For hierarchical artifacts
    status VARCHAR(50) NOT NULL,
    metadata JSONB, -- Additional properties
    version INTEGER NOT NULL DEFAULT 1,
    content_vector VECTOR(1536) -- For semantic search
);

-- Tasks and Assignments
CREATE TABLE tasks (
    task_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by UUID REFERENCES agents(agent_id),
    assigned_to UUID REFERENCES agents(agent_id),
    sprint_id UUID, -- Reference to sprint
    priority INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL, -- Backlog, InProgress, Review, Done, etc.
    estimated_effort FLOAT,
    actual_effort FLOAT,
    dependencies UUID[], -- Array of tasks this depends on
    metadata JSONB, -- Additional task data
    related_artifacts UUID[] -- References to requirements, designs, etc.
);

-- Meetings and Conversations
CREATE TABLE meetings (
    meeting_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_type VARCHAR(50) NOT NULL, -- Planning, StandUp, Review, Retrospective, Brainstorming
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP,
    participants UUID[], -- This should reference agents(agent_id) but array foreign keys are complex, handle in application logic or triggers
    summary TEXT,
    decisions JSONB,
    action_items JSONB
);

CREATE TABLE meeting_conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id UUID REFERENCES meetings(meeting_id),
    sequence_number INTEGER NOT NULL, -- Order in conversation
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    speaker_id UUID, -- This should reference agents(agent_id)
    message TEXT NOT NULL,
    message_type VARCHAR(50), -- Question, Answer, Proposal, etc.
    context JSONB -- Reference to what is being discussed
);

-- Create indexes for performance
CREATE INDEX idx_agent_messages_sender ON agent_messages(sender_id);
CREATE INDEX idx_agent_messages_receiver ON agent_messages(receiver_id);
CREATE INDEX idx_agent_activities_agent ON agent_activities(agent_id);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_artifacts_type ON artifacts(artifact_type);
CREATE INDEX idx_artifacts_creator ON artifacts(created_by);

-- Additional helpful indexes
CREATE INDEX idx_agent_messages_timestamp ON agent_messages(timestamp DESC);
CREATE INDEX idx_agent_activities_timestamp ON agent_activities(timestamp DESC);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_meeting_conversations_meeting_id ON meeting_conversations(meeting_id, sequence_number); 