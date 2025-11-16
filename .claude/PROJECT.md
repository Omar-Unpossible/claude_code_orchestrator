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

These tools are optimized for AI-assisted development and provide cleaner output than traditional Unix tools:

```bash
# Code analysis
tokei                              # Code statistics (fast, accurate)
tree -L 2 -I 'venv|*.pyc'         # Directory structure visualization
rg "pattern" -t py                 # Search code (ripgrep - 10-100x faster than grep)
fd filename -e py                  # Find files (faster than find)

# File operations
bat file.py                        # View with syntax highlighting
ll                                 # Directory listing (if aliased to eza/exa)

# Data processing
cat data.json | jq '.key'          # Parse JSON
yq '.key' config.yaml              # Parse YAML

# Automation
watchexec -e py pytest             # Auto-run tests on file changes
hyperfine 'pytest tests/'          # Benchmark commands

# API testing
http GET localhost:8000/health     # HTTP requests (httpie)

# Git workflow
lazygit                            # Git TUI (visual interface)
git diff                           # Uses delta for better diffs
```

### Tool Selection Guidelines

| Task | Instead of | Use | Why |
|------|-----------|-----|-----|
| Search code | `grep` | `rg` (ripgrep) | 10-100x faster, respects .gitignore |
| Find files | `find` | `fd` | Faster, better syntax, respects .gitignore |
| View files | `cat` | `bat` | Syntax highlighting, line numbers |
| Parse JSON | `grep`/`sed` | `jq` | Proper JSON parsing |
| Parse YAML | `grep`/`sed` | `yq` | Proper YAML parsing |
| Watch files | Manual loops | `watchexec` | Efficient, debounced file watching |
| HTTP requests | `curl` | `http` (httpie) | More readable syntax |
| Benchmark | `time` | `hyperfine` | Statistical analysis, warmup runs |
| Git operations | Manual git | `lazygit` | Visual interface, faster workflows |

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
# Initialize (first time only)
python -m src.cli init

# Create project
python -m src.cli project create "My Project" --profile python_project

# Create and execute task
python -m src.cli task create "Implement feature X" --project 1
python -m src.cli task execute 1

# Interactive mode with command injection
python -m src.cli interactive

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

**CRITICAL**: Read `docs/testing/TEST_GUIDELINES.md` before writing tests to prevent WSL2 crashes!

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term

# Run specific module tests
pytest tests/test_state.py              # StateManager (M1)
pytest tests/test_orchestrator.py       # Core orchestration (M6)
pytest tests/test_integration_e2e.py    # Integration tests

# Auto-run tests on file changes
watchexec -e py pytest

# Run only fast tests (exclude slow tests)
pytest -m "not slow"
```

**Test Resource Limits** (Critical for WSL2 stability):
- Max sleep per test: 0.5s (use `fast_time` fixture for longer)
- Max threads per test: 5 (with mandatory `timeout=` on join)
- Max memory allocation: 20KB per test
- Mark heavy tests: `@pytest.mark.slow`

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

When running `python -m src.cli interactive`:

```bash
# Natural language (no slash) - defaults to orchestrator
"Create a new feature for user authentication"
"What's the current task status?"

# System commands (require / prefix)
/help                           # Show help message
/status                         # Show current task status
/pause                          # Pause execution
/resume                         # Resume execution
/stop                           # Stop gracefully
/to-impl <message>             # Send message to implementer (Claude Code)
/override-decision <choice>    # Override orchestrator's decision
```

## Agile Workflow (v1.3.0)

```bash
# Epic management (large features)
python -m src.cli epic create "User Authentication System" --project 1
python -m src.cli epic list --project 1
python -m src.cli epic execute 1

# Story management (user deliverables)
python -m src.cli story create "Email/password login" --epic 1 --project 1
python -m src.cli story list --epic 1

# Milestone tracking
python -m src.cli milestone create "Auth Complete" --project 1
python -m src.cli milestone check 1
python -m src.cli milestone achieve 1
```

## Shell Enhancements for LLM-Led Development

The WSL2 environment includes 35+ commands optimized for Claude Code workflows.

### Before Starting Claude Code Sessions

**Get Complete Context**:
```bash
context              # Complete project snapshot (location, git, files, stats)
recent 5             # Show 5 recently modified files
todos                # All TODO/FIXME/XXX comments
docs                 # List documentation files
root                 # Jump to project root
```

**MUST Follow Pre-Session Workflow**:
```bash
z obra               # Navigate to project (or use 'obra' alias)
context              # Get comprehensive overview
recent 5             # Check recent activity
todos                # Review pending TODOs
gs                   # Git status
```

### Git Workflow (Fast Iteration)

```bash
gcom <msg>           # Stage all changes and commit
gamend               # Amend last commit with current changes
gs                   # Short git status
gundo                # Undo last commit (keep changes in working dir)
gnew <branch>        # Create and switch to new branch
glog [N]             # Show last N commits in compact format
gdiff [opts]         # Pretty git diff (with delta if installed)
```

### Code Navigation

```bash
ff                   # Fuzzy file finder with preview
search <pattern>     # Grep with context and colors
es <pattern>         # Edit files containing pattern
```

### Testing & Validation (Auto-detects Project Type)

```bash
test [opts]          # Run tests (Python/Node/Rust/Go auto-detected)
lint [opts]          # Run linter (auto-detected)
fmt [opts]           # Format code (auto-detected)
check-all            # Run format + lint + test in sequence
```

**Python Projects** (auto-detected):
- Tests: `pytest` → `python -m pytest`
- Lint: `ruff check` → `pylint` → `flake8`
- Format: `ruff format` → `black`

**Node.js Projects**: `npm test`, `npm run lint`, `npm run format`
**Rust Projects**: `cargo test`, `cargo clippy`, `cargo fmt`
**Go Projects**: `go test ./...`, `go fmt ./...`

### Session Management

```bash
save-context [file]  # Save work context (git status, recent files, diff)
load-context [file]  # View saved context
diagnose             # Environment diagnostics (versions, git, disk, processes)
```

**Example**:
```bash
# End of session
save-context ~/work-context-$(date +%Y%m%d).md

# Next session
load-context ~/work-context-20251115.md
```

### Quick Reference

```bash
claude-help          # Show all commands with descriptions
ch                   # Alias for claude-help
```

**Performance**:
- Startup overhead: < 50ms
- `context` command: ~500ms
- `recent` command: ~100ms
- All commands use native tools (no Python/Node overhead)

**Full Documentation**: `~/CLAUDE_ENHANCEMENTS_README.md`

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
# CORRECT: Load config from file
config = Config.load('config.yaml')

# CORRECT: Access StateManager through dependency injection
orchestrator = Orchestrator(config=config)
state = orchestrator.state_manager

# CORRECT: Use named arguments for StateManager methods
task = state.create_task(
    project_id=1,
    title="Implement feature",
    description="Detailed description"
)

# CORRECT: Check profile before loading (M9)
available_profiles = ProfileManager.list_profiles()
if profile_name in available_profiles:
    profile = ProfileManager.load_profile(profile_name)
```

### Testing Patterns

```python
# Use shared test_config fixture
def test_orchestrator(test_config):
    orchestrator = Orchestrator(config=test_config)
    assert orchestrator.config is not None

# Use fast_time fixture to avoid blocking sleeps
def test_completion(fast_time):
    monitor.mark_complete()
    time.sleep(2.0)  # Instant with fast_time mock
    assert monitor.is_complete()

# Threading with limits and mandatory timeouts
def test_concurrent(test_config):
    threads = [threading.Thread(target=worker) for _ in range(3)]  # Max 5
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)  # MANDATORY timeout
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
