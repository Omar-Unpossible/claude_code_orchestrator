#!/bin/bash
# Obra startup script - ensures correct environment

set -e

cd /home/omarwsl/projects/claude_code_orchestrator

# 1. Check venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements-dev.txt"
    exit 1
fi

# 2. Activate venv
source venv/bin/activate

# 3. Verify Python
if [[ "$VIRTUAL_ENV" != "/home/omarwsl/projects/claude_code_orchestrator/venv" ]]; then
    echo "❌ Wrong virtual environment!"
    echo "Expected: /home/omarwsl/projects/claude_code_orchestrator/venv"
    echo "Got: $VIRTUAL_ENV"
    exit 1
fi

echo "✓ Using: $(which python3)"

# 4. Verify Ollama
if curl -s --connect-timeout 2 http://10.0.75.1:11434/api/tags > /dev/null 2>&1; then
    echo "✓ Ollama reachable at http://10.0.75.1:11434"
else
    echo "⚠ Warning: Cannot reach Ollama at http://10.0.75.1:11434"
fi

# 5. Start Obra
echo ""
echo "Starting Obra Interactive Mode..."
echo "=================================="
echo ""

exec python3 -m src.cli interactive
