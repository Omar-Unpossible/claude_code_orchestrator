#!/bin/bash
# Check which Python environment is being used

echo "=== Python Environment Check ==="
echo

echo "Current Python:"
which python3
python3 --version
echo

echo "Virtual Environment Python:"
ls -la /home/omarwsl/projects/claude_code_orchestrator/venv/bin/python3
echo

echo "Virtual Environment Status:"
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "❌ Virtual environment NOT activated"
    echo "   You are using system Python"
    echo
    echo "To fix:"
    echo "   source venv/bin/activate"
else
    echo "✓ Virtual environment IS activated"
    echo "   VIRTUAL_ENV=$VIRTUAL_ENV"
fi
echo

echo "Testing LLM plugin import:"
python3 -c "
import sys
sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')
try:
    import src.llm
    from src.plugins.registry import LLMRegistry
    providers = LLMRegistry.list()
    print(f'✓ LLM plugins registered: {providers}')
    if 'ollama' in providers:
        print('✓ ollama plugin available')
    else:
        print('✗ ollama plugin NOT available')
except Exception as e:
    print(f'✗ Error importing LLM modules: {e}')
"
