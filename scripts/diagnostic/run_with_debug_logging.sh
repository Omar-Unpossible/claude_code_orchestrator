#!/bin/bash
# Run Obra with full debug logging

cd /home/omarwsl/projects/claude_code_orchestrator
source venv/bin/activate

# Set Python to show all logs
export PYTHONUNBUFFERED=1

# Run with debug logging
python -m src.cli interactive --verbose 2>&1 | tee debug_interactive_output.log
