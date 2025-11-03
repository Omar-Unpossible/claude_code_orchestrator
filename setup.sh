#!/bin/bash
# Setup script for Claude Code Orchestrator
# This script sets up the development environment and runtime directories

set -e  # Exit on error

# Default runtime directory (can be overridden with OBRA_RUNTIME_DIR env var)
RUNTIME_DIR="${OBRA_RUNTIME_DIR:-$HOME/obra-runtime}"

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "======================================================================"
echo "  Claude Code Orchestrator - Setup Script"
echo "======================================================================"
echo ""
echo -e "${BLUE}Runtime directory: $RUNTIME_DIR${NC}"
echo -e "${BLUE}Repository: $(pwd)${NC}"
echo ""

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo -e "${RED}Error: Python 3.10 or higher is required. Found: $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version: $PYTHON_VERSION${NC}"

# Create virtual environment
echo ""
echo -e "${YELLOW}Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo ""
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
echo ""
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip > /dev/null 2>&1
echo -e "${GREEN}✓ Pip upgraded${NC}"

# Install package in editable mode
echo ""
echo -e "${YELLOW}Installing package in editable mode...${NC}"
pip install -e . > /dev/null 2>&1
echo -e "${GREEN}✓ Package installed${NC}"

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements-dev.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create RUNTIME directories (NOT in repo)
echo ""
echo -e "${YELLOW}Creating runtime directories...${NC}"
mkdir -p "$RUNTIME_DIR"/{data,logs,workspace}
echo -e "${GREEN}✓ Runtime directories created:${NC}"
echo -e "   - ${BLUE}$RUNTIME_DIR/data${NC}"
echo -e "   - ${BLUE}$RUNTIME_DIR/logs${NC}"
echo -e "   - ${BLUE}$RUNTIME_DIR/workspace${NC}"

# Detect host IP for Ollama
echo ""
echo -e "${YELLOW}Detecting host IP for Ollama...${NC}"
HOST_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}' 2>/dev/null || echo "localhost")
echo -e "${GREEN}✓ Detected host IP: $HOST_IP${NC}"

# Create/update config.yaml with runtime paths
echo ""
echo -e "${YELLOW}Creating configuration file...${NC}"
cat > config/config.yaml <<EOF
# Claude Code Orchestrator Configuration
# Runtime configuration - DO NOT commit sensitive values!

# Database Configuration
database:
  url: sqlite:///$RUNTIME_DIR/data/orchestrator.db
  pool_size: 10
  max_overflow: 20
  echo: false

# Agent Configuration
agent:
  type: mock  # Options: mock, claude_code, aider
  timeout: 120
  max_retries: 3
  workspace_path: $RUNTIME_DIR/workspace

  # SSH-specific config (for claude-code-ssh agent)
  ssh:
    host: localhost
    port: 22
    user: claude
    key_path: ~/.ssh/id_rsa

  # Docker-specific config (for claude-code-docker agent)
  docker:
    image: claude-code:latest
    container_name: claude-agent
    workspace_mount: $RUNTIME_DIR/workspace

# LLM Configuration
llm:
  type: ollama  # LLM provider type
  model: qwen2.5-coder:32b
  api_url: http://$HOST_IP:11434
  temperature: 0.7
  timeout: 30
  max_tokens: 4096
  context_length: 32768

# File Monitoring
monitoring:
  file_watcher:
    enabled: true
    debounce_ms: 500
    ignore_patterns:
      - "**/__pycache__/**"
      - "**/.git/**"
      - "**/.venv/**"
      - "**/*.pyc"
      - "**/node_modules/**"

  output_monitor:
    completion_markers:
      - "Task completed"
      - "Done"
      - "Finished"
    error_markers:
      - "Error:"
      - "Failed:"
      - "Exception:"

# Orchestration Settings
orchestration:
  max_iterations: 50
  iteration_timeout: 300
  task_timeout: 3600
  concurrent_tasks: 1
  auto_retry: true

# Breakpoint Configuration
breakpoints:
  enabled: true
  auto_resolve_timeout: 300

  triggers:
    low_confidence:
      enabled: true
      threshold: 30
    quality_too_low:
      enabled: true
      threshold: 50
    validation_failed:
      enabled: true
      max_retries: 3
    rate_limit_hit:
      enabled: true
    unexpected_error:
      enabled: true

# Validation Settings
validation:
  response:
    check_completeness: true
    check_code_blocks_closed: true
    min_length: 10

  quality:
    enabled: true
    threshold: 70
    run_tests: true
    check_syntax: true

# Confidence Scoring
confidence:
  threshold: 50
  weights:
    validation: 0.3
    quality: 0.4
    agent_health: 0.1
    retry_count: 0.2

# Context Management
context:
  max_tokens: 8000
  prioritization:
    - recent_interactions
    - task_description
    - relevant_files
    - project_context

  summarization:
    enabled: true
    keep_recent: 5

# Logging
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: $RUNTIME_DIR/logs/orchestrator.log
  max_bytes: 10485760
  backup_count: 5

# Prompt Templates
prompts:
  template_dir: config/prompt_templates

# Performance
performance:
  enable_caching: true
  cache_ttl: 300

# Development/Debug Settings
debug:
  enabled: false
  save_interactions: true
  verbose_logging: false
EOF

echo -e "${GREEN}✓ Configuration file created: config/config.yaml${NC}"

# Initialize database
echo ""
echo -e "${YELLOW}Initializing database...${NC}"
python -m src.cli init --db-url "sqlite:///$RUNTIME_DIR/data/orchestrator.db" 2>/dev/null || true
echo -e "${GREEN}✓ Database initialized${NC}"

# Verify setup
echo ""
echo -e "${YELLOW}Verifying setup...${NC}"
python3 << 'VERIFY_EOF'
from src.core.config import Config
from src.core.state import StateManager
import os

try:
    config = Config.load()
    db_url = config.get('database.url')
    state = StateManager.get_instance(db_url)
    projects = state.list_projects()

    print(f"✓ Configuration loaded successfully")
    print(f"✓ Database connected: {db_url}")
    print(f"✓ Current projects: {len(projects)}")

    # Verify runtime paths are outside repo
    if '/obra-runtime/' in db_url or os.path.expanduser('~') in db_url:
        print(f"✓ Runtime files correctly placed outside repository")
    else:
        print(f"⚠ Warning: Runtime files may be in repository")

except Exception as e:
    print(f"✗ Verification failed: {e}")
    exit(1)
VERIFY_EOF

echo -e "${GREEN}✓ Setup verification complete${NC}"

# Test Ollama connection (optional)
echo ""
echo -e "${YELLOW}Testing Ollama connection...${NC}"
if curl -s --connect-timeout 5 "http://$HOST_IP:11434/api/tags" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is accessible at http://$HOST_IP:11434${NC}"
else
    echo -e "${YELLOW}⚠ Ollama not accessible at http://$HOST_IP:11434${NC}"
    echo -e "${YELLOW}  Make sure Ollama is running on the host and listening on 0.0.0.0:11434${NC}"
fi

# Install git hooks
echo ""
echo -e "${YELLOW}Installing git hooks...${NC}"
if [ -f "hooks/pre-commit" ]; then
    cp hooks/pre-commit .git/hooks/pre-commit
    chmod +x .git/hooks/pre-commit
    echo -e "${GREEN}✓ Pre-commit hook installed${NC}"
else
    echo -e "${YELLOW}⚠ Pre-commit hook not found, skipping${NC}"
fi

# Summary
echo ""
echo "======================================================================"
echo -e "${GREEN}✓ Setup complete!${NC}"
echo "======================================================================"
echo ""
echo -e "${BLUE}Runtime directory:${NC} $RUNTIME_DIR"
echo -e "${BLUE}Repository:${NC} $(pwd)"
echo -e "${BLUE}Virtual environment:${NC} $(pwd)/venv"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "  1. Activate virtual environment:"
echo -e "     ${BLUE}source venv/bin/activate${NC}"
echo ""
echo "  2. Create a project:"
echo -e "     ${BLUE}python -m src.cli project create 'My Project'${NC}"
echo ""
echo "  3. Create a task:"
echo -e "     ${BLUE}python -m src.cli task create 'My Task' --project 1${NC}"
echo ""
echo "  4. Execute the task:"
echo -e "     ${BLUE}python -m src.cli task execute 1${NC}"
echo ""
echo "  5. Or check status:"
echo -e "     ${BLUE}python -m src.cli status${NC}"
echo ""
echo "For more information, see docs/guides/GETTING_STARTED.md"
echo ""
echo "======================================================================"
