#!/bin/bash
# Quick start script for Obra
# Ensures virtual environment is activated before running

set -e

OBRA_DIR="/home/omarwsl/projects/claude_code_orchestrator"

cd "$OBRA_DIR"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found at venv/"
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements-dev.txt
    echo "✓ Dependencies installed"
else
    echo "✓ Virtual environment found"
fi

# Activate venv
echo "✓ Activating virtual environment..."
source venv/bin/activate

# Verify LLM is accessible
echo "✓ Checking LLM connection..."
if curl -s --connect-timeout 2 http://10.0.75.1:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama service is reachable at http://10.0.75.1:11434"
else
    echo "⚠ Warning: Cannot connect to Ollama at http://10.0.75.1:11434"
    echo "  Make sure Ollama is running on the host machine"
fi

echo ""
echo "=========================================="
echo "Starting Obra Interactive Mode"
echo "=========================================="
echo ""

# Run Obra in interactive mode
python -m src.cli interactive
