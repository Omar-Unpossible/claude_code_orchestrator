#!/bin/bash
# Verification script to check if the fix works

echo "=== Verifying Dependency Installation ==="
echo

echo "1. Checking SQLAlchemy..."
python3 -c "import sqlalchemy; print(f'✓ SQLAlchemy {sqlalchemy.__version__} installed')" 2>&1 || echo "✗ SQLAlchemy not installed"

echo

echo "2. Checking LLM Registry..."
python3 -c "
import sys
sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')
import src.llm  # Trigger registration
from src.plugins.registry import LLMRegistry
providers = LLMRegistry.list()
print(f'✓ Registered LLM providers: {providers}')
if 'ollama' in providers:
    print('✓ ollama provider registered')
if 'openai-codex' in providers:
    print('✓ openai-codex provider registered')
" 2>&1

echo

echo "3. Testing Ollama Connection..."
python3 test_llm_config.py 2>&1 | head -30

echo
echo "=== Next Steps ==="
echo "If all checks pass, try running Obra again:"
echo "  python -m src.cli interactive"
