# Software Factory CLI Tool

## Overview

The Software Factory CLI tool provides a command-line interface for interacting with and testing all components of the autonomous multi-agent system. It has been refactored to use a database-first architecture, ensuring all data persists between commands and enabling comprehensive testing capabilities.

## Key Features

- **Database-First Operations**: All operations use PostgreSQL for persistent storage
- **Agent Management**: Create, list, update, and delete agents
- **Conversation Management**: Create and manage multi-agent conversations
- **Message Operations**: Send and receive various message types between agents
- **Component Testing**: Test individual components (LLM, database, memory, etc.)
- **Simulation Scenarios**: Run predefined multi-agent interaction scenarios

## Installation

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 16 with vector extension
- Required Python packages (see `requirements.txt`)

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/your-org/software-factory.git
   cd software-factory
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (or create a `.env` file):
   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/software_factory
   ```

## Command Structure

The CLI commands are organized by functionality:

```bash
./agents/cli/agent_cli.sh [command] [subcommand] [options]
```

Where `command` can be one of:

- `agent`: Agent management operations
- `conversation`: Conversation management operations
- `message`: Message operations
- `db`: Database operations
- `llm`: LLM provider operations
- `memory`: Vector memory operations
- `log`: Logging operations
- `simulation`: Pre-defined simulation scenarios
- `component`: Component verification

## Command Documentation

### Agent Commands

#### Create and Manage Agents

```bash
# Create a new agent
./agents/cli/agent_cli.sh agent create --name "Test Agent" --type "assistant"

# List all agents
./agents/cli/agent_cli.sh agent list

# Show details of a specific agent
./agents/cli/agent_cli.sh agent show 550e8400-e29b-41d4-a716-446655440000

# Update an agent
./agents/cli/agent_cli.sh agent update 550e8400-e29b-41d4-a716-446655440000 --name "Updated Name" --status "inactive"

# Delete an agent (soft delete)
./agents/cli/agent_cli.sh agent delete 550e8400-e29b-41d4-a716-446655440000
```

#### Advanced Agent Operations

```bash
# Create a BaseAgent
./agents/cli/agent_cli.sh agent create-base --name "Base Agent" --system-prompt "You are a test agent."

# Test agent thinking
./agents/cli/agent_cli.sh agent think 550e8400-e29b-41d4-a716-446655440000 --prompt "Analyze this problem"

# Manage agent capabilities
./agents/cli/agent_cli.sh agent capabilities 550e8400-e29b-41d4-a716-446655440000 --action set --capabilities '["coding", "planning"]'

# Update agent status
./agents/cli/agent_cli.sh agent status 550e8400-e29b-41d4-a716-446655440000 --status "busy"

# Simulate agent errors
./agents/cli/agent_cli.sh agent error-sim 550e8400-e29b-41d4-a716-446655440000 --error-type "timeout" --recover true
```

### Conversation Commands

#### Manage Conversations

```bash
# Create a new conversation
./agents/cli/agent_cli.sh conversation create --topic "Test Conversation"

# List all conversations
./agents/cli/agent_cli.sh conversation list

# Select a conversation
./agents/cli/agent_cli.sh conversation select 123e4567-e89b-12d3-a456-426614174000

# Show conversation details
./agents/cli/agent_cli.sh conversation show --id 123e4567-e89b-12d3-a456-426614174000 --messages

# Update a conversation
./agents/cli/agent_cli.sh conversation update 123e4567-e89b-12d3-a456-426614174000 --topic "Updated Topic"

# Delete a conversation
./agents/cli/agent_cli.sh conversation delete 123e4567-e89b-12d3-a456-426614174000
```

#### Advanced Conversation Operations

```bash
# Visualize a conversation
./agents/cli/agent_cli.sh conversation visualize --id 123e4567-e89b-12d3-a456-426614174000 --format "mermaid"

# Inject a message into a conversation
./agents/cli/agent_cli.sh conversation inject --id 123e4567-e89b-12d3-a456-426614174000 --sender-id "550e8400-e29b-41d4-a716-446655440000" --recipient-id "123e4567-e89b-12d3-a456-426614174000" --message-type "ALERT" --content '{...}'

# Simulate conversation failure
./agents/cli/agent_cli.sh conversation simulate-failure --id 123e4567-e89b-12d3-a456-426614174000 --failure-type "timeout" --recover true

# Export a conversation
./agents/cli/agent_cli.sh conversation export --id 123e4567-e89b-12d3-a456-426614174000 --format "markdown"
```

### Message Commands

```bash
# Send a message
./agents/cli/agent_cli.sh message send --type "REQUEST" --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --content '{...}'

# Send a request message
./agents/cli/agent_cli.sh message request --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --action "process_data" --parameters '{...}'

# Send an inform message
./agents/cli/agent_cli.sh message inform --sender "550e8400-e29b-41d4-a716-446655440000" --recipient "123e4567-e89b-12d3-a456-426614174000" --type "analysis_result" --data '{...}'

# List messages
./agents/cli/agent_cli.sh message list --agent "550e8400-e29b-41d4-a716-446655440000" --limit 10
```

### Database Commands

```bash
# Execute a query
./agents/cli/agent_cli.sh db query --sql "SELECT version()"

# Test transaction isolation
./agents/cli/agent_cli.sh db transaction-isolation --isolation-level "READ COMMITTED" --test-type "read_phenomena"

# Show performance statistics
./agents/cli/agent_cli.sh db performance-stats --include-queries true --include-tables true
```

### LLM Commands

```bash
# Test chat completion
./agents/cli/agent_cli.sh llm chat-completion --messages '[{"role": "system", "content": "You are a helpful assistant"},{"role": "user", "content": "What is the capital of France?"}]'

# Test function calling
./agents/cli/agent_cli.sh llm function-call --prompt "What's the weather in New York?" --functions '[...]'

# List available models
./agents/cli/agent_cli.sh llm models
```

### Memory Commands

```bash
# Test context window
./agents/cli/agent_cli.sh memory context --context-items '[...]' --query "How do neural networks work?" --max-tokens 1000

# Test memory index
./agents/cli/agent_cli.sh memory index --operation "add" --content "Content to remember" --metadata '{...}'

# Get memory stats
./agents/cli/agent_cli.sh memory stats
```

### Logging Commands

```bash
# Test log levels
./agents/cli/agent_cli.sh log levels --message "Test message"

# Get log entries
./agents/cli/agent_cli.sh log list --level "ERROR" --limit 10

# Configure logging
./agents/cli/agent_cli.sh log configure --default-level "INFO" --component-levels '{"agent": "DEBUG"}'
```

### Component Verification

```bash
# Verify base agent
./agents/cli/agent_cli.sh component verify base-agent

# Verify database client
./agents/cli/agent_cli.sh component verify db-client

# Verify LLM provider
./agents/cli/agent_cli.sh component verify llm-provider
```

## Database-First Architecture

The CLI tool has been refactored to use PostgreSQL for persistent storage:

- All agent and conversation state is stored in the database
- Operations use proper database transactions
- All IDs are validated as proper UUIDs
- Soft deletion is used for data integrity
- Transaction isolation levels can be configured and tested

This approach ensures that:

1. Data persists between CLI commands and sessions
2. Multiple CLI instances can work with the same data
3. Tests reflect realistic production behavior

## Testing

For comprehensive testing guidance, see [CLI Testing Manual](cli-testing-manual.md).

## Development

### Adding New Commands

To add a new command:

1. Add a new function in the appropriate file in `agents/cli/`
2. Register the command in `agents/cli/agent_cli.py`
3. Update the documentation in this README and the testing manual

### Coding Standards

All CLI code should follow these standards:

- Use async functions with proper error handling
- Validate all inputs before processing
- Use proper transaction management for database operations
- Return structured responses as dictionaries
