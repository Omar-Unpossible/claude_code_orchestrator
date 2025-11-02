#!/bin/bash
# Setup script for Claude Code Orchestrator

set -e  # Exit on error

echo "======================================================================"
echo "  Claude Code Orchestrator - Setup Script"
echo "======================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

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

# Install dependencies
echo ""
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Install development dependencies (optional)
read -p "Install development dependencies (pytest, coverage, etc.)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install -r requirements-dev.txt > /dev/null 2>&1
    echo -e "${GREEN}✓ Development dependencies installed${NC}"
fi

# Create necessary directories
echo ""
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p config data logs
echo -e "${GREEN}✓ Directories created${NC}"

# Initialize orchestrator
echo ""
echo -e "${YELLOW}Initializing orchestrator...${NC}"
python -m src.cli init
echo -e "${GREEN}✓ Orchestrator initialized${NC}"

# Setup Ollama (optional)
echo ""
read -p "Do you want to setup Ollama for local LLM? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Checking if Ollama is installed...${NC}"
    if command -v ollama &> /dev/null; then
        echo -e "${GREEN}✓ Ollama is installed${NC}"

        echo ""
        read -p "Pull Qwen 2.5 Coder model? [y/N] " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Pulling qwen2.5-coder:32b (this may take a while)...${NC}"
            ollama pull qwen2.5-coder:32b
            echo -e "${GREEN}✓ Model downloaded${NC}"
        fi
    else
        echo -e "${YELLOW}Ollama not found. Install from: https://ollama.ai${NC}"
    fi
fi

# Run tests (optional)
echo ""
read -p "Run tests to verify installation? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Running tests...${NC}"
    python -m pytest tests/ -v --tb=short -x
    echo -e "${GREEN}✓ Tests passed${NC}"
fi

# Print next steps
echo ""
echo "======================================================================"
echo -e "${GREEN}✓ Setup complete!${NC}"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Create a project:"
echo "     python -m src.cli project create 'My Project'"
echo ""
echo "  3. Create a task:"
echo "     python -m src.cli task create 'My Task' --project 1"
echo ""
echo "  4. Execute the task:"
echo "     python -m src.cli task execute 1"
echo ""
echo "  5. Or use interactive mode:"
echo "     python -m src.cli interactive"
echo ""
echo "For more information, see docs/guides/GETTING_STARTED.md"
echo ""
echo "======================================================================"
