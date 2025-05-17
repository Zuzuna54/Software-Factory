# Agent CLI Tool

This directory contains a Command Line Interface (CLI) tool for testing agent interactions.

## Module Structure

The CLI tool is organized into the following modules:

- `cli_core.py`: Core `AgentCLI` class with initialization and shared utilities
- `cli_agent_ops.py`: Functions for agent management (create, list, get, etc.)
- `cli_conversation_ops.py`: Functions for conversation management
- `cli_message_ops.py`: Functions for message operations (send, request, inform, etc.)
- `cli_simulation.py`: Functions for running predefined simulation scenarios
- `cli_component_ops.py`: Functions for testing individual system components
- `cli_app.py`: Main CLI application with command parsing and handling

## Entry Points

- `__main__.py`: Allows running the tool as a module with `python -m agents.cli`
- `agent_cli.sh`: Bash script wrapper to run the CLI tool

## Usage

```bash
# Using the script
./agents/cli/agent_cli.sh [command] [subcommand] [options]

# As a Python module
python -m agents.cli [command] [subcommand] [options]
```

## Commands

- `agent`: Agent management commands

  - `create`: Create a new agent
  - `list`: List all agents
  - `show`: Show agent details

- `conversation`: Conversation management commands

  - `create`: Create a new conversation
  - `list`: List all conversations
  - `select`: Select a conversation
  - `show`: Show conversation details

- `message`: Message commands

  - `send`: Send a generic message
  - `request`: Send a request message
  - `inform`: Send an inform message
  - `list`: List messages

- `simulation`: Simulation commands

  - `run`: Run a predefined simulation

- `component`: Component testing commands

  - `db`: Database client testing

    - `query`: Execute a database query
    - `transaction`: Test database transaction management

  - `llm`: LLM provider testing

    - `completion`: Generate text completion
    - `embedding`: Generate text embedding

  - `memory`: Vector memory testing

    - `store`: Store text in vector memory
    - `search`: Store text and search vector memory

  - `log`: Logging system testing

  - `verify`: Run component verification
    - Supported components: `base-agent`, `db-client`, `llm-provider`,
      `vector-memory`, `communication`, `logging`, `cli-tool`

## Examples

```bash
# AGENT COMMANDS

# Create a new agent with ID, name, and type
./agents/cli/agent_cli.sh agent create --id "agent-123" --name "Research Assistant" --type "research"

# Create a new agent with auto-generated ID
./agents/cli/agent_cli.sh agent create --name "Data Analyst" --type "analysis"

# List all registered agents
./agents/cli/agent_cli.sh agent list

# Show details of a specific agent
./agents/cli/agent_cli.sh agent show agent-123

# CONVERSATION COMMANDS

# Create a new conversation with a specific topic
./agents/cli/agent_cli.sh conversation create --topic "Project Planning"

# Create a conversation with a specific ID and topic
./agents/cli/agent_cli.sh conversation create --id "convo-456" --topic "Data Analysis"

# List all conversations
./agents/cli/agent_cli.sh conversation list

# Select a conversation as current
./agents/cli/agent_cli.sh conversation select convo-456

# Show details of the current conversation
./agents/cli/agent_cli.sh conversation show

# Show details of a specific conversation
./agents/cli/agent_cli.sh conversation show --id "convo-456"

# Show messages in a conversation with default limit (10)
./agents/cli/agent_cli.sh conversation show --id "convo-456" --messages

# Show messages in a conversation with custom limit
./agents/cli/agent_cli.sh conversation show --id "convo-456" --messages --limit 20

# MESSAGE COMMANDS

# Send a generic message
./agents/cli/agent_cli.sh message send --type "REQUEST" --sender "agent-123" --recipient "agent-456" --content '{"action": "analyze", "data": "sample.csv"}'

# Send a request message (specialized command)
./agents/cli/agent_cli.sh message request --sender "agent-123" --recipient "agent-456" --action "process_data" --parameters '{"file": "data.csv"}' --priority 2

# Send an inform message (specialized command)
./agents/cli/agent_cli.sh message inform --sender "agent-123" --recipient "agent-456" --type "analysis_result" --data '{"accuracy": 0.95, "runtime": 120}'

# Send a propose message
./agents/cli/agent_cli.sh message send --type "PROPOSE" --sender "agent-123" --recipient "agent-456" --content '{"proposal": "Let's use algorithm X", "reason": "Better performance"}'

# Send a confirm message
./agents/cli/agent_cli.sh message send --type "CONFIRM" --sender "agent-123" --recipient "agent-456" --content '{"confirmation": "Proposal accepted"}'

# Send an alert message
./agents/cli/agent_cli.sh message send --type "ALERT" --sender "agent-123" --recipient "agent-456" --content '{"alert_type": "error", "message": "Process failed"}'

# Send a message as a reply to another message
./agents/cli/agent_cli.sh message send --type "INFORM" --sender "agent-123" --recipient "agent-456" --content '{"status": "completed"}' --reply-to "msg-789"

# List messages for a specific agent
./agents/cli/agent_cli.sh message list --agent "agent-123"

# List messages with a limit
./agents/cli/agent_cli.sh message list --agent "agent-123" --limit 5

# SIMULATION COMMANDS

# Run a basic simulation
./agents/cli/agent_cli.sh simulation run basic

# Run a planning simulation
./agents/cli/agent_cli.sh simulation run planning

# Run a problem-solving simulation
./agents/cli/agent_cli.sh simulation run problem-solving

# COMPONENT TESTING COMMANDS

# Database client testing

# Execute a custom SQL query
./agents/cli/agent_cli.sh component db query --sql "SELECT version()"

# Test database transactions
./agents/cli/agent_cli.sh component db transaction

# LLM provider testing

# Generate text completion with default model
./agents/cli/agent_cli.sh component llm completion --prompt "What is artificial intelligence?"

# Generate text completion with custom model and token limit
./agents/cli/agent_cli.sh component llm completion --prompt "Explain quantum computing" --model "gemini-pro" --max-tokens 200

# Generate text embedding
./agents/cli/agent_cli.sh component llm embedding --text "This is a test sentence"

# Generate text embedding with custom model
./agents/cli/agent_cli.sh component llm embedding --text "This is a test sentence" --model "gemini-embedding"

# Vector memory testing

# Store text in vector memory
./agents/cli/agent_cli.sh component memory store --text "Important information to remember"

# Store and search vector memory
./agents/cli/agent_cli.sh component memory search --text "New text to store" --query "information"

# Logging system testing

# Test logging system for an agent
./agents/cli/agent_cli.sh component log --agent "agent-123"

# Component verification

# Verify base agent component
./agents/cli/agent_cli.sh component verify base-agent

# Verify database client component
./agents/cli/agent_cli.sh component verify db-client

# Verify LLM provider component
./agents/cli/agent_cli.sh component verify llm-provider

# Verify vector memory component
./agents/cli/agent_cli.sh component verify vector-memory

# Verify communication protocol component
./agents/cli/agent_cli.sh component verify communication

# Verify logging system component
./agents/cli/agent_cli.sh component verify logging

# Verify CLI tool component
./agents/cli/agent_cli.sh component verify cli-tool
```
