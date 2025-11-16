# Obra (Claude Code Orchestrator)

## Overview

**Obra** is an AI orchestration platform that combines local LLM reasoning (Qwen 2.5 Coder) with remote code generation (Claude Code CLI) for autonomous software development. It provides a hybrid architecture with multi-stage validation pipeline and quality-based iterative improvement.

**Current Version**: v1.7.2
**Status**: Production-ready - 815+ tests (88% coverage), validated performance

## Quick Context Commands

```bash
# Get comprehensive project overview
tree -L 3 -I 'venv|__pycache__|*.pyc|.git|dist|build'
tokei
git status

# Search codebase
rg "StateManager" src/
fd test_ tests/

# View file with syntax highlighting
bat src/core/state_manager.py

# Run tests with coverage
pytest --cov=src --cov-report=term
```

## Architecture

### Core Principles

1. **StateManager is Single Source of Truth** - ALL state access through StateManager
2. **Validation Order Matters** - ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine
3. **Plugin System** - AgentPlugin and LLMPlugin for extensibility
4. **Per-Iteration Sessions** - Fresh Claude session per orchestration iteration
5. **LLM-First Prompt Engineering** - Hybrid JSON metadata + natural language instructions

### Key Components

```
src/
├── core/                   # Core orchestration engine
│   ├── orchestrator.py     # Main orchestration logic
│   ├── state_manager.py    # Single source of truth for state
│   └── decision_engine.py  # Iteration control logic
├── plugins/
│   ├── agents/            # Agent implementations (Claude Code, Aider)
│   └── llm/               # LLM providers (Ollama, OpenAI Codex)
├── validation/            # Multi-stage validation pipeline
├── quality/               # Quality scoring and metrics
├── context/               # Context management
└── cli/                   # Command-line interface
```

### Documentation Structure

**Essential Reading** (in order):
1. `CLAUDE.md` - This project's main guidance file
2. `docs/design/OBRA_SYSTEM_OVERVIEW.md` - Complete system architecture
3. `CHANGELOG.md` - Recent changes and version history
4. `docs/architecture/ARCHITECTURE.md` - Technical details
5. `docs/testing/TEST_GUIDELINES.md` - Critical for preventing WSL2 crashes

**Reference Documentation**:
- `docs/guides/` - User and developer guides
- `docs/decisions/` - Architecture Decision Records (17 ADRs)
- `docs/testing/` - Test guidelines and postmortems
- `docs/archive/` - Historical phase reports

## Development Tools

### LLM-Optimized Tools (Installed)

Modern CLI tools optimized for AI-assisted development.

**See Skill**: `development-tools` for complete tool reference

**Quick Reference**:
- `tokei` - Code statistics
- `rg "pattern"` - Fast code search (10-100x faster than grep)
- `fd filename` - Find files (faster than find)
- `bat file.py` - View with syntax highlighting
- `jq '.key' data.json` - Parse JSON
- `yq '.key' file.yaml` - Parse YAML

**Full Guide**: Invoke `development-tools` Skill when needed

## Environment Setup

### Prerequisites

```bash
# Python 3.11+ with virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run automated setup
./setup.sh
```

### LLM Configuration

**Option 1: Local LLM (Ollama/Qwen)** - Default
```yaml
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://10.0.75.1:11434  # Host on vEthernet DevSwitch
  temperature: 0.7
```

**Option 2: Remote LLM (OpenAI Codex)**
```yaml
llm:
  type: openai-codex
  model: gpt-5-codex
  timeout: 120
```

### Environment Variables

```bash
# LLM configuration (alternative to config file)
export ORCHESTRATOR_LLM_TYPE=ollama
export ORCHESTRATOR_LLM_MODEL=qwen2.5-coder:32b
export ORCHESTRATOR_LLM_API_URL=http://10.0.75.1:11434

# Runtime directory (required for setup.sh)
export OBRA_RUNTIME_DIR=/path/to/runtime

# Database (optional)
export DATABASE_URL=sqlite:///obra.db
```

## Common Tasks

### Running Obra

```bash
python -m src.cli init  # Initialize (first time)
python -m src.cli project create "My Project" --profile python_project
python -m src.cli task create "Implement feature X" --project 1
python -m src.cli task execute 1
python -m src.cli interactive  # Interactive mode

# MUST use helper script
./scripts/startup/obra.sh
```

### LLM Management

```bash
# Check LLM connection status
python -m src.cli llm status

# Reconnect to LLM
python -m src.cli llm reconnect

# Switch LLM provider
python -m src.cli llm switch ollama
python -m src.cli llm switch openai-codex --model gpt-5-codex
```

### Testing Workflows

**CRITICAL**: Read `docs/testing/TEST_GUIDELINES.md` before writing tests!

**Run tests**:
```bash
pytest                           # All tests
pytest --cov=src --cov-report=term  # With coverage
pytest -m "not slow"             # Fast tests only
pytest tests/test_state.py       # Specific module
```

**Detailed Patterns**: See `testing-guidelines` Skill

### Code Quality

```bash
# Type checking
mypy src/

# Linting
pylint src/

# Format code
black src/ tests/

# Check all
mypy src/ && pylint src/ && black --check src/ tests/
```

### Finding Implementation Patterns

```bash
# Find StateManager usage
rg "StateManager" src/ -t py

# Find validation pipeline components
rg "class.*Validator" src/ -t py

# Find agent implementations
rg "@register_agent" src/plugins/agents/ -t py

# Find test fixtures
rg "@pytest.fixture" tests/ -t py

# Find configuration examples
fd config src/ tests/ -e py -e yaml -e json
```

### Documentation Tasks

```bash
# Find architecture documentation
tree docs/architecture/

# Find ADRs (Architecture Decision Records)
fd ADR docs/decisions/ -e md

# Find guides
tree docs/guides/

# Search documentation
rg "StateManager" docs/ -t md
```

## Interactive Mode Commands (v1.5.0 UX)

**See Skill**: `interactive-commands` for complete command reference

**Usage**: `python -m src.cli interactive`

**Quick Reference**: Natural language (no `/`) goes to orchestrator. System commands use `/` prefix.

## Agile Workflow (v1.3.0)

Epic/Story/Milestone management for Agile/Scrum workflows.

**See Skill**: `agile-workflow` for complete command reference

**Quick Commands**:
```bash
python -m src.cli epic create "Title" --project 1
python -m src.cli story create "Title" --epic 1 --project 1
python -m src.cli milestone create "Title" --project 1
```

**Full Guide**: Invoke `agile-workflow` Skill

## Shell Enhancements for LLM-Led Development

WSL2 includes 35+ optimized commands for Claude Code workflows.

**See Skill**: `shell-enhancements` for complete command reference

**Quick Start**:
```bash
context              # Get project snapshot
recent 5             # Show recent files
todos                # Find TODO comments
gcom "msg"          # Stage all and commit
gnew branch         # Create and switch branch
```

**Full Documentation**: Invoke `shell-enhancements` Skill when needed

## Notes for Claude

### Critical Patterns to Follow

1. **Use StateManager for ALL state access** - Never bypass with direct DB access
2. **Follow validation order** - ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine
3. **Use plugin system** - Load agents and LLMs from config, never hardcode
4. **Fresh sessions per iteration** - Don't reuse Claude sessions across iterations
5. **Read TEST_GUIDELINES.md** - Critical for preventing WSL2 crashes when writing tests

**See `.claude/RULES.md`** for complete DO/DON'T quick reference.

### Quick Rules Reference

**DO**:
- ✅ Use `Config.load('config.yaml')`
- ✅ Access state via `orchestrator.state_manager`
- ✅ Use `fast_time` fixture for sleeps > 0.5s
- ✅ Add `timeout=` on all thread joins
- ✅ Check `orchestrator.check_llm_available()` before tasks

**DON'T**:
- ❌ Bypass StateManager
- ❌ Reverse validation order
- ❌ Hardcode agents/LLMs
- ❌ Reuse sessions across iterations
- ❌ Exceed test resource limits
- ❌ Save docs to project root or `/tmp`

### Model Attribute Names (Correct Usage)

```python
# Project model
project.project_name          # NOT project.name
project.working_directory     # NOT project.working_dir

# Task model
task.task_id                  # Primary key
task.title                    # Task title
task.task_type               # EPIC, STORY, TASK, SUBTASK
task.epic_id                 # Parent epic (if story/task)
task.story_id                # Parent story (if task)

# State fields
task.requires_adr            # Boolean
task.has_architectural_changes  # Boolean
task.documentation_status    # String
```

### Key Configuration Patterns

```python
# Config and StateManager access
config = Config.load('config.yaml')
orchestrator = Orchestrator(config=config)
state = orchestrator.state_manager
task = state.create_task(project_id=1, title="...", description="...")

# Profile validation
if profile_name in ProfileManager.list_profiles():
    profile = ProfileManager.load_profile(profile_name)
```

### Helper Scripts Location

All helper scripts organized in `scripts/` directory:

```bash
# Startup scripts
./scripts/startup/obra.sh              # Main startup script (USE THIS!)
./scripts/startup/start_obra.sh        # Alternative with auto-setup

# Testing scripts
python scripts/testing/test_exact_flow.py      # Test interactive flow
python scripts/testing/test_llm_*.py           # LLM integration tests

# Diagnostic scripts
./scripts/diagnostic/check_python_env.sh       # Check environment
python scripts/diagnostic/diagnose_llm_issue.py  # Debug LLM connection

# Example scripts
python scripts/examples/run_obra.py            # Simple orchestration example
```

See `scripts/README.md` for complete documentation.

### Codebase Patterns

**Decorators for Registration**:
```python
@register_agent('claude-code')
class ClaudeCodeAgent(AgentPlugin):
    pass

@register_llm('ollama')
class OllamaLLM(LLMPlugin):
    pass
```

**Exception Handling with Context**:
```python
raise AgentException(
    "Cannot connect to agent",
    context={'host': host, 'port': port},
    recovery="Check network connectivity and agent process status"
)
```

**Configuration-Driven Design**:
```python
agent_type = config.get('agent.type')
agent = AgentRegistry.get(agent_type)()
agent.initialize(config.get('agent.config'))
```

### Architecture References

For deep understanding, read in order:
1. `CLAUDE.md` - Overview and principles (this file's parent)
2. `docs/design/OBRA_SYSTEM_OVERVIEW.md` - Complete system design
3. `docs/architecture/ARCHITECTURE.md` - Technical architecture
4. `docs/decisions/` - 17 ADRs documenting key decisions

### Recent Enhancements

**v1.7.2** (Current):
- Testing Infrastructure Foundation (Story 0)
- 815+ tests, 88% coverage

**v1.7.1**:
- Observability improvements
- Structured logging

**v1.7.0**:
- Unified Execution Architecture (ADR-017)
- All NL commands route through orchestrator

**v1.5.0**:
- Interactive UX improvements
- Natural language defaults to orchestrator (no slash required)

**v1.4.0**:
- Project Infrastructure Maintenance System (ADR-015)
- Automatic documentation freshness tracking

**v1.3.0**:
- Agile/Scrum work hierarchy (ADR-013)
- Natural Language Command Interface (ADR-014)

See `CHANGELOG.md` for complete version history.

## Hardware & Deployment

**Target Environment**:
- Host: Windows 11 Pro with Hyper-V
- LLM: Qwen 2.5 Coder 32B via Ollama on RTX 5090 (32GB VRAM)
- VM: Windows 11 Pro guest with WSL2 (Ubuntu 22.04)
- Agent: Claude Code CLI in VM WSL2
- Database: SQLite (simple) or PostgreSQL (production)

**Network Setup**:
- LLM endpoint: `http://10.0.75.1:11434` (Host on vEthernet DevSwitch)
- MUST use local agent execution via subprocess
- Optional SSH agent for remote execution

## External References

- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) - Local LLM interface
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code) - Agent documentation
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/) - Database layer
- [Click CLI](https://click.palletsprojects.com/) - CLI framework
- [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/) - Interactive input

## Quick Reference

**Daily Commands**:
```bash
./scripts/startup/obra.sh          # Start Obra
python -m src.cli interactive      # Interactive mode
pytest --cov=src                   # Run tests with coverage
rg "StateManager" src/ -t py       # Search codebase
tree -L 3 -I 'venv|*.pyc'         # View structure
```

**When Claude Needs Context**:
```bash
tree -L 3 -I 'venv|__pycache__|*.pyc|.git'
tokei
git status
rg "class.*Manager" src/ -t py
```

**When Debugging**:
```bash
python -m src.cli llm status       # Check LLM connection
pytest tests/test_state.py -v     # Run specific tests
rg "ERROR" logs/                  # Search logs
bat src/core/orchestrator.py      # View file with highlighting
```

---

**Last Updated**: November 14, 2025
**Version**: v1.7.2
**Repository**: git@github.com:Omar-Unpossible/claude_code_orchestrator.git
