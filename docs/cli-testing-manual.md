# Software Factory CLI Testing Manual

## Overview

This manual provides comprehensive documentation for using the Software Factory CLI tool to test and validate all aspects of the system. The CLI tool has been fully refactored to use database-first operations, ensuring all data is persisted between commands and allowing for complete end-to-end testing of the autonomous multi-agent system.

## Prerequisites

Before using the CLI tool, ensure you have:

1. A running PostgreSQL database with the Software Factory schema
2. Environment variables set up (or use `.env` file):
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory
   ```
3. Python 3.12 or higher installed
4. All dependencies installed via `pip install -r requirements.txt`

## CLI Command Structure

All commands follow this general pattern:

```bash
./agents/cli/agent_cli.sh [command] [subcommand] [options]
```

## Database Testing Commands

### Basic Database Operations

#### Query Execution

```bash
# Execute a simple query
./agents/cli/agent_cli.sh component db query --sql "SELECT version()"

# Execute a more complex query
./agents/cli/agent_cli.sh component db query --sql "SELECT count(*) FROM agents WHERE status = 'active'"
```

#### Transaction Testing

```bash
# Test database transaction
./agents/cli/agent_cli.sh component db transaction
```

#### Connection Pool Status

```bash
# Show connection pool statistics
./agents/cli/agent_cli.sh db pool-status
```

#### Database Tables

```bash
# List all tables with record counts
./agents/cli/agent_cli.sh db tables
```

#### Database Metrics

```bash
# Show database performance metrics
./agents/cli/agent_cli.sh db metrics
```

### Database Schema Management

#### Schema Validation

```bash
# Validate database schema against models
./agents/cli/agent_cli.sh db validate
```

#### Run Migrations

```bash
# Run pending migrations
./agents/cli/agent_cli.sh db migrate
```

#### Rollback Migration

```bash
# Rollback to previous migration
./agents/cli/agent_cli.sh db rollback
```

#### Data Integrity Checking

```bash
# Check data integrity (foreign keys, etc.)
./agents/cli/agent_cli.sh db verify-integrity

# Check data constraints
./agents/cli/agent_cli.sh db check-constraints
```

## Agent Management

### Create and Manage Agents

#### Create Simple Agent

```bash
# Create agent with auto-generated ID
./agents/cli/agent_cli.sh agent create --name "Test Agent" --type "assistant"

# Create agent with specific UUID
./agents/cli/agent_cli.sh agent create --id "550e8400-e29b-41d4-a716-446655440000" --name "Research Bot" --type "researcher"
```

#### List Agents

```bash
# List all active agents
./agents/cli/agent_cli.sh agent list

# List all agents including inactive ones
./agents/cli/agent_cli.sh agent list --include-inactive
```

#### Show Agent Details

```bash
# Show details of specific agent
./agents/cli/agent_cli.sh agent show 550e8400-e29b-41d4-a716-446655440000
```

#### Update Agent

```bash
# Update agent properties
./agents/cli/agent_cli.sh agent update 550e8400-e29b-41d4-a716-446655440000 --name "Updated Name" --status "inactive"
```

#### Delete Agent

```bash
# Mark agent as inactive (soft delete)
./agents/cli/agent_cli.sh agent delete 550e8400-e29b-41d4-a716-446655440000
```

### Advanced Agent Operations

#### Create BaseAgent

```bash
# Create a full BaseAgent instance
./agents/cli/agent_cli.sh agent create-base --name "Test Base Agent" --type "test" --role "tester"
```

#### Test Agent Thinking

```bash
# Test agent thinking capability
./agents/cli/agent_cli.sh agent think 550e8400-e29b-41d4-a716-446655440000 --context '{"problem": "test problem", "constraints": ["time", "resources"]}'
```

#### Manage Agent Capabilities

```bash
# Set agent capabilities
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000 --set '["coding", "planning", "testing"]'

# Get agent capabilities
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000
```

#### Change Agent Status

```bash
# Change agent status
./agents/cli/agent_cli.sh agent status 550e8400-e29b-41d4-a716-446655440000 --status "busy"
```

#### Simulate Agent Errors

```bash
# Simulate agent error conditions
./agents/cli/agent_cli.sh agent error-sim 550e8400-e29b-41d4-a716-446655440000 --type "timeout"
```

## Communication and Messages

### Conversation Management

#### Create Conversation

```bash
# Create a new conversation
./agents/cli/agent_cli.sh conversation create --topic "Test Planning Session"

# Create conversation with specific ID
./agents/cli/agent_cli.sh conversation create --id "123e4567-e89b-12d3-a456-426614174000" --topic "Architecture Discussion"
```

#### List Conversations

```bash
# List all conversations
./agents/cli/agent_cli.sh conversation list
```

#### Select Conversation

```bash
# Select a conversation as current
./agents/cli/agent_cli.sh conversation select 123e4567-e89b-12d3-a456-426614174000
```

#### Show Conversation Details

```bash
# Show conversation details
./agents/cli/agent_cli.sh conversation show --id 123e4567-e89b-12d3-a456-426614174000

# Show conversation with messages
./agents/cli/agent_cli.sh conversation show --id 123e4567-e89b-12d3-a456-426614174000 --messages --limit 20
```

#### Advanced Conversation Operations

```bash
# Generate visualization of conversation
./agents/cli/agent_cli.sh conversation visualize --id 123e4567-e89b-12d3-a456-426614174000 --format "graph"

# Inject a message into conversation
./agents/cli/agent_cli.sh conversation inject --id 123e4567-e89b-12d3-a456-426614174000 --content '{"type": "ALERT", "message": "Injected alert"}'

# Simulate conversation failure
./agents/cli/agent_cli.sh conversation simulate-failure --id 123e4567-e89b-12d3-a456-426614174000 --error "network"

# Export conversation to file
./agents/cli/agent_cli.sh conversation export --id 123e4567-e89b-12d3-a456-426614174000 --format "json" --output "conversation_export.json"
```

### Message Operations

#### Send Generic Message

```bash
# Send a generic message
./agents/cli/agent_cli.sh message send --type "REQUEST" --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --content '{"action": "analyze", "data": "test.csv"}'
```

#### Send Request Message

```bash
# Send a request message
./agents/cli/agent_cli.sh message request --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --action "process_data" --parameters '{"file": "data.csv"}' --priority 2
```

#### Send Inform Message

```bash
# Send an inform message
./agents/cli/agent_cli.sh message inform --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --type "analysis_result" --data '{"accuracy": 0.95, "runtime": 120}'
```

#### Send Propose Message

```bash
# Send a propose message
./agents/cli/agent_cli.sh message send --type "PROPOSE" --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --content '{"proposal": "Use algorithm X", "reason": "Better performance"}'
```

#### Send Confirm Message

```bash
# Send a confirm message
./agents/cli/agent_cli.sh message send --type "CONFIRM" --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --content '{"confirmation": "Proposal accepted"}'
```

#### Send Alert Message

```bash
# Send an alert message
./agents/cli/agent_cli.sh message send --type "ALERT" --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --content '{"alert_type": "error", "message": "Process failed"}'
```

#### List Messages

```bash
# List messages for an agent
./agents/cli/agent_cli.sh message list --agent "550e8400-e29b-41d4-a716-446655440000" --limit 10
```

## LLM Provider Testing

### Text Completion

```bash
# Generate text completion
./agents/cli/agent_cli.sh component llm completion --prompt "What is artificial intelligence?"

# Generate completion with model and token specification
./agents/cli/agent_cli.sh component llm completion --prompt "Explain quantum computing" --model "gemini-pro" --max-tokens 200
```

### Chat Completion

```bash
# Generate chat completion
./agents/cli/agent_cli.sh llm chat-completion --messages '[{"role": "system", "content": "You are a helpful assistant"},{"role": "user", "content": "What is the capital of France?"}]'
```

### Text Embedding

```bash
# Generate text embedding
./agents/cli/agent_cli.sh component llm embedding --text "This is a test sentence"

# With specific model
./agents/cli/agent_cli.sh component llm embedding --text "This is a test sentence" --model "gemini-embedding"
```

### Function Calling

```bash
# Test function calling
./agents/cli/agent_cli.sh llm function-call --prompt "What's the weather in New York?" --functions '[{"name": "get_weather", "description": "Get weather for a location", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}}]'
```

### List Models

```bash
# List available LLM models
./agents/cli/agent_cli.sh llm models
```

## Vector Memory Testing

### Store and Search

#### Store Text

```bash
# Store text in vector memory
./agents/cli/agent_cli.sh component memory store --text "Important information to remember"
```

#### Search Memory

```bash
# Store and search vector memory
./agents/cli/agent_cli.sh component memory search --text "New text to store" --query "information"
```

### Advanced Memory Operations

#### Context Window Management

```bash
# Test context window management
./agents/cli/agent_cli.sh memory context --size 2048 --text "Long text to test context window..."
```

#### Memory Indexing

```bash
# Test memory indexing
./agents/cli/agent_cli.sh memory index --collection "test_collection" --operation "create"
```

#### Memory Statistics

```bash
# Show memory usage statistics
./agents/cli/agent_cli.sh memory stats
```

## Logging and Activity Tracking

### Log Operations

#### Test Logging System

```bash
# Test logging system for an agent
./agents/cli/agent_cli.sh component log --agent "550e8400-e29b-41d4-a716-446655440000"
```

#### List Logs

```bash
# List recent log entries
./agents/cli/agent_cli.sh log list --limit 20
```

#### Search Logs

```bash
# Search for specific log entries
./agents/cli/agent_cli.sh log search --agent-id "550e8400-e29b-41d4-a716-446655440000" --type "thinking" --start-time "2023-06-01" --end-time "2023-06-30"
```

#### Verify Logging

```bash
# Verify logging for a specific operation
./agents/cli/agent_cli.sh log verify --operation "agent_creation" --agent-id "550e8400-e29b-41d4-a716-446655440000"
```

#### Log Metrics

```bash
# Show logging metrics
./agents/cli/agent_cli.sh log metrics
```

#### Export Logs

```bash
# Export logs to file
./agents/cli/agent_cli.sh log export --agent-id "550e8400-e29b-41d4-a716-446655440000" --format "json" --output "agent_logs.json"
```

## Component Verification

### Run Component Verification Scripts

#### Agent Verification

```bash
# Verify base agent component
./agents/cli/agent_cli.sh component verify base-agent
```

#### Database Client Verification

```bash
# Verify database client component
./agents/cli/agent_cli.sh component verify db-client
```

#### LLM Provider Verification

```bash
# Verify LLM provider component
./agents/cli/agent_cli.sh component verify llm-provider
```

#### Vector Memory Verification

```bash
# Verify vector memory component
./agents/cli/agent_cli.sh component verify vector-memory
```

#### Communication Protocol Verification

```bash
# Verify communication protocol component
./agents/cli/agent_cli.sh component verify communication
```

#### Logging System Verification

```bash
# Verify logging system component
./agents/cli/agent_cli.sh component verify logging
```

#### CLI Tool Verification

```bash
# Verify CLI tool component
./agents/cli/agent_cli.sh component verify cli-tool
```

## Simulation Commands

### Run Predefined Simulations

#### Basic Simulation

```bash
# Run basic simulation
./agents/cli/agent_cli.sh simulation run basic
```

#### Planning Simulation

```bash
# Run planning simulation
./agents/cli/agent_cli.sh simulation run planning
```

#### Problem-Solving Simulation

```bash
# Run problem-solving simulation
./agents/cli/agent_cli.sh simulation run problem-solving
```

## End-to-End Testing Scenarios

### Basic Agent Communication Scenario

The following sequence tests a complete agent communication flow:

```bash
# 1. Create two agents
./agents/cli/agent_cli.sh agent create --id "550e8400-e29b-41d4-a716-446655440000" --name "Project Manager" --type "manager"
./agents/cli/agent_cli.sh agent create --id "123e4567-e89b-12d3-a456-426614174000" --name "Developer" --type "developer"

# 2. Create a conversation
./agents/cli/agent_cli.sh conversation create --id "98765432-10ab-cdef-1234-567890abcdef" --topic "Feature Planning"

# 3. Send a request from manager to developer
./agents/cli/agent_cli.sh message request --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --action "implement_feature" --parameters '{"feature": "login", "deadline": "2023-07-15"}' --conversation-id "98765432-10ab-cdef-1234-567890abcdef"

# 4. Send a proposal response from developer
./agents/cli/agent_cli.sh message send --type "PROPOSE" --sender "123e4567-e89b-12d3-a456-426614174000" --recipient "550e8400-e29b-41d4-a716-446655440000" --content '{"proposal": "Implementation plan", "timeline": "2 weeks", "resources": ["auth_lib"]}' --conversation-id "98765432-10ab-cdef-1234-567890abcdef"

# 5. Send confirmation from manager
./agents/cli/agent_cli.sh message send --type "CONFIRM" --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --content '{"confirmation": "Plan approved", "notes": "Proceed as proposed"}' --conversation-id "98765432-10ab-cdef-1234-567890abcdef"

# 6. View conversation with messages
./agents/cli/agent_cli.sh conversation show --id "98765432-10ab-cdef-1234-567890abcdef" --messages
```

### Testing Thinking and Reasoning

```bash
# 1. Create an agent with BaseAgent capabilities
./agents/cli/agent_cli.sh agent create-base --id "550e8400-e29b-41d4-a716-446655440000" --name "Reasoning Agent" --type "reasoner"

# 2. Test thinking capability with a complex problem
./agents/cli/agent_cli.sh agent think 550e8400-e29b-41d4-a716-446655440000 --context '{"problem": "Design a system for high-throughput event processing", "constraints": ["latency < 100ms", "scalable to 10k events/sec", "99.99% reliability"]}'

# 3. View agent activity logs
./agents/cli/agent_cli.sh log list --agent-id "550e8400-e29b-41d4-a716-446655440000" --type "thinking"
```

## Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check database connection
./agents/cli/agent_cli.sh component db query --sql "SELECT 1"

# Check connection pool status
./agents/cli/agent_cli.sh db pool-status
```

#### UUID Format Issues

If you get UUID format errors, ensure you're using valid UUIDs in the format:
`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (8-4-4-4-12 pattern)

#### Memory/Embedding Issues

```bash
# Check vector extension
./agents/cli/agent_cli.sh component db query --sql "SELECT * FROM pg_extension WHERE extname = 'vector'"
```

## Conclusion

This CLI tool provides comprehensive capabilities for testing and validating all aspects of the Software Factory system. By using these commands in various combinations, you can verify the functionality, performance, and reliability of all system components individually and as an integrated whole.
