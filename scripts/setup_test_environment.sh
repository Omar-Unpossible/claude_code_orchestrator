#!/bin/bash
# Setup Test Environment for Obra Real-World Testing
# This script prepares the environment for running end-to-end tests

set -e  # Exit on error

echo "========================================================================"
echo "Obra Test Environment Setup"
echo "========================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "setup.sh" ]; then
    echo -e "${RED}✗ Error: Must run from project root directory${NC}"
    exit 1
fi

echo "1. Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

if [ "$python_major" -ge 3 ] && [ "$python_minor" -ge 12 ]; then
    echo -e "   ${GREEN}✓ Python $python_version${NC}"
else
    echo -e "   ${RED}✗ Python 3.12+ required, found $python_version${NC}"
    exit 1
fi

echo ""
echo "2. Checking virtual environment..."
if [ -d "venv" ]; then
    echo -e "   ${GREEN}✓ Virtual environment exists${NC}"

    # Activate venv
    source venv/bin/activate
    echo -e "   ${GREEN}✓ Activated virtual environment${NC}"
else
    echo -e "   ${YELLOW}⚠ Virtual environment not found, creating...${NC}"
    python -m venv venv
    source venv/bin/activate
    echo -e "   ${GREEN}✓ Created and activated virtual environment${NC}"
fi

echo ""
echo "3. Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "   ${GREEN}✓ Dependencies installed${NC}"

echo ""
echo "4. Checking directories..."
mkdir -p data logs config /tmp/obra_test_run/workspace
echo -e "   ${GREEN}✓ Created: data/${NC}"
echo -e "   ${GREEN}✓ Created: logs/${NC}"
echo -e "   ${GREEN}✓ Created: config/${NC}"
echo -e "   ${GREEN}✓ Created: /tmp/obra_test_run/workspace/${NC}"

echo ""
echo "5. Checking external dependencies..."

# Check Claude Code CLI
if command -v claude &> /dev/null; then
    claude_version=$(claude --version 2>&1 || echo "unknown")
    echo -e "   ${GREEN}✓ Claude Code CLI: $claude_version${NC}"
else
    echo -e "   ${YELLOW}⚠ Claude Code CLI not found (tests will use mock)${NC}"
    echo "     Install with: npm install -g @anthropics/claude-code"
fi

# Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "   ${GREEN}✓ Ollama is running${NC}"

    # Check for Qwen model
    if curl -s http://localhost:11434/api/tags | grep -q "qwen"; then
        echo -e "   ${GREEN}✓ Qwen model available${NC}"
    else
        echo -e "   ${YELLOW}⚠ Qwen model not found${NC}"
        echo "     Install with: ollama pull qwen2.5-coder:32b"
    fi
else
    echo -e "   ${YELLOW}⚠ Ollama not running (LLM validation will be skipped)${NC}"
    echo "     Start with: systemctl start ollama"
fi

# Check API key
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo -e "   ${GREEN}✓ ANTHROPIC_API_KEY is set${NC}"
else
    echo -e "   ${YELLOW}⚠ ANTHROPIC_API_KEY not set (required for real agent)${NC}"
    echo "     Set with: export ANTHROPIC_API_KEY=your_key_here"
fi

echo ""
echo "6. Creating test configuration..."
cat > config/test_config.yaml << 'EOF'
# Test Configuration for Real-World Runthrough
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434
  temperature: 0.7
  timeout: 30
  max_tokens: 4096

agent:
  type: mock  # Change to 'claude_code_local' for real agent testing
  timeout: 120
  max_retries: 3

  local:
    command: claude
    workspace_dir: /tmp/obra_test_run/workspace
    timeout_ready: 30
    timeout_response: 120

database:
  url: sqlite:///data/orchestrator_test.db
  pool_size: 5
  echo: false

monitoring:
  file_watcher:
    enabled: true
    debounce_ms: 500

orchestration:
  max_iterations: 10
  iteration_timeout: 300
  task_timeout: 1800

breakpoints:
  enabled: true
  triggers:
    low_confidence:
      enabled: true
      threshold: 30
    quality_too_low:
      enabled: true
      threshold: 50

validation:
  quality:
    enabled: true
    threshold: 70

confidence:
  threshold: 50

logging:
  level: INFO
  file: logs/test_runthrough.log
EOF

echo -e "   ${GREEN}✓ Test configuration created: config/test_config.yaml${NC}"

echo ""
echo "7. Running quick validation..."

# Try importing main modules
python -c "
import sys
sys.path.insert(0, '.')
from src.core.config import Config
from src.core.state import StateManager
from src.agents.claude_code_local import ClaudeCodeLocalAgent
print('   ✓ All modules import successfully')
" || {
    echo -e "   ${RED}✗ Module import failed${NC}"
    exit 1
}

echo ""
echo "========================================================================"
echo "Setup Complete!"
echo "========================================================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Run quick test (2 minutes):"
echo "     python tests/test_runthrough.py --scenario 1"
echo ""
echo "  2. Run all tests (15 minutes):"
echo "     python tests/test_runthrough.py --all"
echo ""
echo "  3. View test plan:"
echo "     cat docs/development/REAL_WORLD_TEST_PLAN.md"
echo ""
echo "  4. View quick start guide:"
echo "     cat docs/development/QUICK_START_TESTING.md"
echo ""
echo "Optional: Enable real agent testing:"
echo "  1. Edit config/test_config.yaml"
echo "  2. Change agent.type from 'mock' to 'claude_code_local'"
echo "  3. Ensure ANTHROPIC_API_KEY is set"
echo ""
echo "========================================================================"
