#!/bin/bash

# Script to run the agent CLI tool

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." &> /dev/null && pwd )"

# Activate Python environment if it exists
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
  source "$PROJECT_ROOT/venv/bin/activate"
elif [ -f "$PROJECT_ROOT/.venv/bin/activate" ]; then
  source "$PROJECT_ROOT/.venv/bin/activate"
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# Run the agent CLI tool
python -m agents.cli.agent_cli "$@" 