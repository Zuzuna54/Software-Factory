# Software Factory CLI Testing Manual

## Overview

This manual provides comprehensive documentation for using the Software Factory CLI tool to test and validate all aspects of the system. The CLI tool has been fully refactored to use database-first operations, ensuring all data is persisted between commands and allowing for complete end-to-end testing of the autonomous multi-agent system.

## Key Features

- **Database-First Architecture**: All operations are persisted in the database
- **Complete Test Coverage**: Test every component of the system individually or together
- **Realistic Test Scenarios**: Create and run multi-agent interaction scenarios
- **Comprehensive Validation**: Verify all aspects of agent behavior and communication
- **Error Handling Testing**: Simulate and recover from various failure conditions

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
./agents/cli/agent_cli.sh db query --sql "SELECT version()"

# Execute a more complex query with parameters
./agents/cli/agent_cli.sh db query --sql "SELECT count(*) FROM agents WHERE status = $1" --params '["active"]'

# Explain a query execution plan
./agents/cli/agent_cli.sh db query --sql "SELECT * FROM agents" --explain true
```

#### Transaction Testing

```bash
# Test database transaction
./agents/cli/agent_cli.sh db transaction

# Test transaction isolation levels
./agents/cli/agent_cli.sh db transaction-isolation --isolation-level "READ COMMITTED" --test-type "read_phenomena"

# Test write conflicts
./agents/cli/agent_cli.sh db transaction-isolation --isolation-level "SERIALIZABLE" --test-type "write_conflict" --concurrency 3

# Test deadlock detection
./agents/cli/agent_cli.sh db transaction-isolation --test-type "deadlock"
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

# Show specific metrics
./agents/cli/agent_cli.sh db performance-stats --include-queries true --include-tables true --include-indexes true
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

# Create agent with capabilities
./agents/cli/agent_cli.sh agent create --name "Multi-skill Agent" --type "assistant" --capabilities '["coding", "planning", "research"]'
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

# Update agent system prompt
./agents/cli/agent_cli.sh agent update 550e8400-e29b-41d4-a716-446655440000 --system-prompt "You are a specialized research assistant focused on data analysis."
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
./agents/cli/agent_cli.sh agent create-base --name "Test Base Agent" --system-prompt "You are a test agent designed for debugging."
```

#### Test Agent Thinking

```bash
# Test agent thinking capability
./agents/cli/agent_cli.sh agent think 550e8400-e29b-41d4-a716-446655440000 --prompt "Analyze the following problem: How to optimize API response times?"
```

#### Manage Agent Capabilities

```bash
# Get agent capabilities
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000 --action get

# Set agent capabilities
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000 --action set --capabilities '["coding", "planning", "testing"]'

# Add a capability
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000 --action add --capabilities '["design"]'

# Remove a capability
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000 --action remove --capabilities '["testing"]'
```

#### Change Agent Status

```bash
# Change agent status
./agents/cli/agent_cli.sh agent status 550e8400-e29b-41d4-a716-446655440000 --status "busy"
```

#### Simulate Agent Errors

```bash
# Simulate agent error conditions
./agents/cli/agent_cli.sh agent error-sim 550e8400-e29b-41d4-a716-446655440000 --error-type "timeout" --recover true

# Simulate unrecoverable error
./agents/cli/agent_cli.sh agent error-sim 550e8400-e29b-41d4-a716-446655440000 --error-type "permission" --recover false
```

## Communication and Messages

### Conversation Management

#### Create Conversation

```bash
# Create a new conversation
./agents/cli/agent_cli.sh conversation create --topic "Test Planning Session"

# Create conversation with specific ID
./agents/cli/agent_cli.sh conversation create --id "123e4567-e89b-12d3-a456-426614174000" --topic "Architecture Discussion"

# Create conversation with metadata
./agents/cli/agent_cli.sh conversation create --topic "Feature Planning" --metadata '{"priority": "high", "deadline": "2023-06-30"}'
```

#### List Conversations

```bash
# List all conversations
./agents/cli/agent_cli.sh conversation list

# List including inactive conversations
./agents/cli/agent_cli.sh conversation list --include-inactive
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

#### Update Conversation

```bash
# Update conversation topic
./agents/cli/agent_cli.sh conversation update 123e4567-e89b-12d3-a456-426614174000 --topic "Updated Topic"

# Update conversation status
./agents/cli/agent_cli.sh conversation update 123e4567-e89b-12d3-a456-426614174000 --status "paused"

# Update conversation metadata
./agents/cli/agent_cli.sh conversation update 123e4567-e89b-12d3-a456-426614174000 --metadata '{"priority": "medium"}'
```

#### Delete Conversation

```bash
# Mark conversation as inactive (soft delete)
./agents/cli/agent_cli.sh conversation delete 123e4567-e89b-12d3-a456-426614174000
```

#### Advanced Conversation Operations

```bash
# Generate visualization of conversation in text format
./agents/cli/agent_cli.sh conversation visualize --id 123e4567-e89b-12d3-a456-426614174000 --format "text"

# Generate visualization in mermaid format
./agents/cli/agent_cli.sh conversation visualize --id 123e4567-e89b-12d3-a456-426614174000 --format "mermaid"

# Generate visualization in JSON format
./agents/cli/agent_cli.sh conversation visualize --id 123e4567-e89b-12d3-a456-426614174000 --format "json"

# Inject a message into conversation
./agents/cli/agent_cli.sh conversation inject --id 123e4567-e89b-12d3-a456-426614174000 --sender-id "550e8400-e29b-41d4-a716-446655440000" --recipient-id "123e4567-e89b-12d3-a456-426614174000" --message-type "ALERT" --content '{"type": "ALERT", "message": "Injected alert"}'

# Simulate conversation failure
./agents/cli/agent_cli.sh conversation simulate-failure --id 123e4567-e89b-12d3-a456-426614174000 --failure-type "timeout" --recover true

# Export conversation to JSON file
./agents/cli/agent_cli.sh conversation export --id 123e4567-e89b-12d3-a456-426614174000 --format "json" --output "conversation_export.json"

# Export conversation to markdown file
./agents/cli/agent_cli.sh conversation export --id 123e4567-e89b-12d3-a456-426614174000 --format "markdown"

# Export conversation to HTML file
./agents/cli/agent_cli.sh conversation export --id 123e4567-e89b-12d3-a456-426614174000 --format "html"

# Export conversation to CSV file
./agents/cli/agent_cli.sh conversation export --id 123e4567-e89b-12d3-a456-426614174000 --format "csv"
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

# List messages sent by an agent
./agents/cli/agent_cli.sh message list --agent "550e8400-e29b-41d4-a716-446655440000" --as-sender true --as-recipient false
```

## LLM Provider Testing

### Text Completion

```bash
# Generate text completion
./agents/cli/agent_cli.sh llm completion --prompt "What is artificial intelligence?"

# Generate completion with model and token specification
./agents/cli/agent_cli.sh llm completion --prompt "Explain quantum computing" --model "gemini-pro" --max-tokens 200
```

### Chat Completion

```bash
# Generate chat completion
./agents/cli/agent_cli.sh llm chat-completion --messages '[{"role": "system", "content": "You are a helpful assistant"},{"role": "user", "content": "What is the capital of France?"}]'

# Generate chat completion with temperature
./agents/cli/agent_cli.sh llm chat-completion --messages '[{"role": "system", "content": "You are a helpful assistant"},{"role": "user", "content": "Write a short poem about programming"}]' --temperature 0.9
```

### Text Embedding

```bash
# Generate text embedding
./agents/cli/agent_cli.sh llm embedding --text "This is a test sentence"

# With specific model
./agents/cli/agent_cli.sh llm embedding --text "This is a test sentence" --model "gemini-embedding"
```

### Function Calling

```bash
# Test function calling
./agents/cli/agent_cli.sh llm function-call --prompt "What's the weather in New York?" --functions '[{"name": "get_weather", "description": "Get weather for a location", "parameters": {"type": "object", "properties": {"location": {"type": "string"}}}}]'

# Test function calling with multiple functions
./agents/cli/agent_cli.sh llm function-call --prompt "Set a reminder for my meeting tomorrow" --functions '[{"name": "set_reminder", "description": "Set a reminder", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "time": {"type": "string"}}}}, {"name": "create_event", "description": "Create calendar event", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}}}}]'
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
./agents/cli/agent_cli.sh memory store --text "Important information to remember"
```

#### Search Memory

```bash
# Store and search vector memory
./agents/cli/agent_cli.sh memory search --text "New text to store" --query "information"
```

### Advanced Memory Operations

#### Context Window Management

```bash
# Test context window management with two items
./agents/cli/agent_cli.sh memory context --context-items '["First piece of context about machine learning", "Second piece of context about neural networks"]' --query "How do neural networks work?" --max-tokens 1000

# Test with more items
./agents/cli/agent_cli.sh memory context --context-items '["Context item 1", "Context item 2", "Context item 3", "Context item 4", "Context item 5"]' --query "test query" --max-tokens 500
```

#### Memory Indexing

```bash
# Add item to memory index
./agents/cli/agent_cli.sh memory index --operation "add" --content "This is content to remember" --metadata '{"source": "test", "importance": "high"}'

# Update item in memory index
./agents/cli/agent_cli.sh memory index --operation "update" --item-id "item-123" --content "Updated content"

# Get item from memory index
./agents/cli/agent_cli.sh memory index --operation "get" --item-id "item-123"

# Delete item from memory index
./agents/cli/agent_cli.sh memory index --operation "delete" --item-id "item-123"
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
# Test logging at all levels
./agents/cli/agent_cli.sh log levels --message "Test logging message"

# Test with context
./agents/cli/agent_cli.sh log levels --message "Test with context" --include-context true
```

#### List Logs

```bash
# List recent log entries
./agents/cli/agent_cli.sh log list --limit 20

# List logs by level
./agents/cli/agent_cli.sh log list --level "ERROR" --limit 10
```

#### Search Logs

```bash
# Search for specific log entries
./agents/cli/agent_cli.sh log search --agent-id "550e8400-e29b-41d4-a716-446655440000" --component "agent" --start-time "2023-06-01" --end-time "2023-06-30" --search-term "error"
```

#### Configure Logging

```bash
# Configure logging with default settings
./agents/cli/agent_cli.sh log configure --default-level "INFO"

# Configure file logging
./agents/cli/agent_cli.sh log configure --default-level "DEBUG" --log-to-file true --log-file "./logs/agent_cli.log"

# Configure component-specific logging
./agents/cli/agent_cli.sh log configure --default-level "INFO" --component-levels '{"agent": "DEBUG", "db": "WARNING"}'
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

# 7. Visualize the conversation as a sequence diagram
./agents/cli/agent_cli.sh conversation visualize --id "98765432-10ab-cdef-1234-567890abcdef" --format "mermaid"

# 8. Export the conversation for documentation
./agents/cli/agent_cli.sh conversation export --id "98765432-10ab-cdef-1234-567890abcdef" --format "markdown" --output "feature_planning.md"
```

### Testing Thinking and Reasoning

```bash
# 1. Create an agent with BaseAgent capabilities
./agents/cli/agent_cli.sh agent create-base --id "550e8400-e29b-41d4-a716-446655440000" --name "Reasoning Agent" --type "reasoner"

# 2. Set agent capabilities
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000 --action set --capabilities '["reasoning", "problem_solving"]'

# 3. Test thinking capability with a complex problem
./agents/cli/agent_cli.sh agent think 550e8400-e29b-41d4-a716-446655440000 --prompt "Design a system for high-throughput event processing that meets these constraints: latency < 100ms, scalable to 10k events/sec, 99.99% reliability"

# 4. View agent activity logs
./agents/cli/agent_cli.sh log list --agent-id "550e8400-e29b-41d4-a716-446655440000" --level "INFO"
```

### Testing Error Handling and Recovery

```bash
# 1. Create an agent and conversation
./agents/cli/agent_cli.sh agent create --id "550e8400-e29b-41d4-a716-446655440000" --name "Test Agent" --type "tester"
./agents/cli/agent_cli.sh conversation create --id "123e4567-e89b-12d3-a456-426614174000" --topic "Error Testing"

# 2. Simulate agent error
./agents/cli/agent_cli.sh agent error-sim 550e8400-e29b-41d4-a716-446655440000 --error-type "timeout" --recover true

# 3. Simulate conversation failure
./agents/cli/agent_cli.sh conversation simulate-failure --id "123e4567-e89b-12d3-a456-426614174000" --failure-type "protocol_error" --recover true

# 4. Verify recovery via logs
./agents/cli/agent_cli.sh log search --search-term "recovery" --level "INFO"
```

### Database Performance Testing

```bash
# 1. Check database connection and metrics
./agents/cli/agent_cli.sh db pool-status
./agents/cli/agent_cli.sh db metrics

# 2. Test query performance
./agents/cli/agent_cli.sh db query --sql "SELECT * FROM agents JOIN agent_messages ON agents.agent_id = agent_messages.sender_id LIMIT 100" --explain true

# 3. Test transaction isolation levels
./agents/cli/agent_cli.sh db transaction-isolation --isolation-level "READ COMMITTED" --test-type "read_phenomena"
./agents/cli/agent_cli.sh db transaction-isolation --isolation-level "SERIALIZABLE" --test-type "write_conflict" --concurrency 5

# 4. Check detailed performance statistics
./agents/cli/agent_cli.sh db performance-stats --include-queries true --min-calls 10
```

## Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check database connection
./agents/cli/agent_cli.sh db query --sql "SELECT 1"

# Check connection pool status
./agents/cli/agent_cli.sh db pool-status
```

#### UUID Format Issues

If you get UUID format errors, ensure you're using valid UUIDs in the format:
`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (8-4-4-4-12 pattern)

#### Memory/Embedding Issues

```bash
# Check vector extension
./agents/cli/agent_cli.sh db query --sql "SELECT * FROM pg_extension WHERE extname = 'vector'"
```

#### Logging Configuration Issues

```bash
# Reset logging configuration to defaults
./agents/cli/agent_cli.sh log configure --default-level "INFO" --log-to-file false
```

## Database-First Architecture

The CLI tool has been fully refactored to use database-first operations:

- **Persistent Storage**: All data is stored in PostgreSQL database tables
- **No In-Memory Storage**: Removed in-memory dictionaries for agents and conversations
- **UUID Handling**: Proper UUID formatting and validation for all IDs
- **Transaction Management**: Proper transaction handling for database operations
- **Error Handling**: Comprehensive error handling for database operations
- **Async Operations**: All database operations are performed asynchronously

This architecture ensures that:

1. All changes persist between CLI commands and sessions
2. Multiple CLI instances can interact with the same data
3. The CLI properly exercises the database functionality
4. Testing is more realistic and closer to production behavior

## Conclusion

This CLI tool provides comprehensive capabilities for testing and validating all aspects of the Software Factory system. By using these commands in various combinations, you can verify the functionality, performance, and reliability of all system components individually and as an integrated whole.
