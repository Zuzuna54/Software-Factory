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
    context_vector HALFVEC(3072) -- Use HALFVEC for >2000 dims
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
    content_vector HALFVEC(3072) -- Use HALFVEC for >2000 dims
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

-- Sprints Table (Added based on ScrumMasterAgent usage)
CREATE TABLE sprints (
    sprint_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sprint_name VARCHAR(255) NOT NULL,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    goal TEXT,
    created_by UUID REFERENCES agents(agent_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL -- e.g., PLANNING, ACTIVE, COMPLETED
);

-- Project Vision Table (Added based on ProductManagerAgent usage)
CREATE TABLE project_vision (
    vision_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id VARCHAR(100) NOT NULL DEFAULT 'default-project', -- Assuming a default or passed project ID
    title VARCHAR(255) NOT NULL,
    vision_statement TEXT,
    target_audience TEXT,
    key_goals JSONB,
    success_metrics JSONB,
    constraints JSONB,
    created_by UUID REFERENCES agents(agent_id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL -- e.g., DRAFT, ACTIVE, ARCHIVED
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

-- Enhanced Vector Storage (Iteration 4)
CREATE TABLE IF NOT EXISTS enhanced_vector_storage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(), -- Changed from SERIAL to UUID
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    embedding HALFVEC(3072) NOT NULL, -- Use HALFVEC for >2000 dims
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    tags TEXT[],
    UNIQUE(entity_type, entity_id)
);

-- Vector Relationships (Iteration 4)
CREATE TABLE IF NOT EXISTS vector_relationships (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_entity_type VARCHAR(50) NOT NULL,
    source_entity_id VARCHAR(255) NOT NULL,
    target_entity_type VARCHAR(50) NOT NULL,
    target_entity_id VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(50) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(source_entity_type, source_entity_id, target_entity_type, target_entity_id, relationship_type)
);

-- Thought Processes Table (Iteration 4)
CREATE TABLE IF NOT EXISTS thought_processes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(agent_id), -- Added FK constraint
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    context TEXT,
    thought_steps JSONB NOT NULL,
    reasoning_path TEXT NOT NULL,
    conclusion TEXT,
    related_task_id UUID REFERENCES tasks(task_id), -- Added FK constraint
    related_files TEXT[],
    metadata JSONB,
    tags TEXT[]
);

-- Indexes for Enhanced Vector Storage (Iteration 4)
CREATE INDEX IF NOT EXISTS idx_enhanced_vector_entity_type
ON enhanced_vector_storage(entity_type);

CREATE INDEX IF NOT EXISTS idx_enhanced_vector_tags
ON enhanced_vector_storage USING GIN(tags);

-- Use HNSW index type and halfvec operator class for high-dimensional halfvec
CREATE INDEX IF NOT EXISTS idx_enhanced_vector_embedding
ON enhanced_vector_storage USING hnsw (embedding halfvec_cosine_ops);

-- Indexes for Vector Relationships (Iteration 4)
CREATE INDEX IF NOT EXISTS idx_vector_relationships_source
ON vector_relationships(source_entity_type, source_entity_id);

CREATE INDEX IF NOT EXISTS idx_vector_relationships_target
ON vector_relationships(target_entity_type, target_entity_id);

-- Indexes for Thought Processes (Iteration 4)
CREATE INDEX IF NOT EXISTS idx_thought_processes_agent_id ON thought_processes(agent_id);
CREATE INDEX IF NOT EXISTS idx_thought_processes_task_id ON thought_processes(related_task_id);
CREATE INDEX IF NOT EXISTS idx_thought_processes_tags ON thought_processes USING GIN(tags); 