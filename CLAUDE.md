# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Obra** (Claude Code Orchestrator) is an AI orchestration platform combining local LLM reasoning (Qwen 2.5 Coder) with remote code generation (Claude Code CLI) for autonomous software development.

**Architecture**: Hybrid local-remote design with multi-stage validation pipeline and quality-based iterative improvement. See Architecture Principles below for core patterns (StateManager, validation order, fresh sessions, hybrid prompts).

**Terminology**: The **Orchestrator** (validation, quality scoring, prompt optimization) and **Implementer** (code generation) are the two LLM agents. Shorthand: **Orc** and **Imp** (for efficient communication in this file only - use formal terms in code/docs).

**Current Version**: **v1.7.2** (November 13, 2025)

**Status**: Production-ready - 815+ tests (88% coverage), 19 critical bugs fixed through real orchestration, validated performance (PHASE_6)

**Key Features Implemented**:
- ✅ Hybrid local-remote architecture (M0-M9)
- ✅ Multi-stage validation pipeline with quality-based iteration
- ✅ Unified Execution Architecture - All NL commands through orchestrator (v1.7.0 - ADR-017)
- ✅ Natural Language Command Interface (v1.3.0 - ADR-014, enhanced v1.6.0 - ADR-016)
- ✅ Agile/Scrum work hierarchy - Epics, Stories, Tasks, Subtasks, Milestones (v1.3.0 - ADR-013)
- ✅ Project Infrastructure Maintenance System (v1.4.0 - ADR-015)
- ✅ Interactive UX improvements - Natural language defaults to orchestrator (v1.5.0)
- ✅ LLM-First Prompt Engineering (PHASE_6) - 35% token efficiency, 100% parse success
- ✅ Retry logic, Task dependencies, Git integration, Configuration profiles (M9)

**Complete Details**: `docs/design/OBRA_SYSTEM_OVERVIEW.md` - Full system architecture, design principles, capabilities, and development guidelines.

## Quick Context Refresh

When starting a new session, read these documents in priority order:

### Essential Reading
1. **[CLAUDE.md](CLAUDE.md)** - This file
2. **[docs/design/OBRA_SYSTEM_OVERVIEW.md](docs/design/OBRA_SYSTEM_OVERVIEW.md)** - ⭐ Complete system overview
3. **[CHANGELOG.md](CHANGELOG.md)** - Recent changes and version history
4. **[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** - Technical architecture
5. **[docs/development/TEST_GUIDELINES.md](docs/development/TEST_GUIDELINES.md)** - ⚠️ CRITICAL: Prevents WSL2 crashes

### Key References
- **Documentation Index**: `docs/README.md` - Browse all docs
- **ADRs**: `docs/decisions/` - Architecture decisions (14 ADRs total)
- **Phase Reports**: `docs/development/phase-reports/` - Latest work summaries
- **Configuration**: `docs/guides/CONFIGURATION_PROFILES_GUIDE.md`
- **Interactive Mode**: `docs/development/INTERACTIVE_STREAMING_QUICKREF.md` - v1.5.0 UX improvements
- **Natural Language Interface**: `docs/guides/NL_COMMAND_GUIDE.md` - Natural language command guide
- **Agile Workflow**: `docs/guides/AGILE_WORKFLOW_GUIDE.md` - Epic/story/milestone workflows
- **Project Infrastructure**: `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md` - Automatic doc maintenance
- **Flexible LLM**: `docs/business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md` - Dual deployment model

## Architecture Principles

### 1. Plugin System (Foundation - M0)
- **AgentPlugin** and **LLMPlugin** are abstract base classes defining interfaces
- Agents (Claude Code, Aider) and LLM providers (Ollama, llama.cpp) are pluggable
- Decorator-based registration: `@register_agent('name')`
- Enables testing with mock plugins and runtime agent swapping

### 2. StateManager is Single Source of Truth (M1)
- **ALL** state access MUST go through StateManager - NO direct database access
- Prevents inconsistencies, enables atomic transactions, supports rollback
- Thread-safe with proper locking (RLock)
- **Rule**: Never bypass StateManager even for "quick reads"

### 3. Validation Order Matters (M2, M4)
- **Sequence**: ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine
- Validate completeness (format) BEFORE quality (correctness) BEFORE confidence
- Completeness check is fast, quality check is expensive (may use LLM)
- Different failure modes: incomplete = retry, low quality = review/breakpoint

### 4. No Cost Tracking
- Using Claude Code subscription (flat fee), not API (per-token)
- Track token usage for context management ONLY, not billing
- Rate limits detected reactively from Claude Code output
- Focus on quality, not cost optimization

### 5. Fail-Safe Defaults
- When uncertain, trigger breakpoint (pause for human input)
- Conservative confidence thresholds (prefer false positives)
- Checkpoint before risky operations
- Auto-save state frequently

### 6. Agent Architecture - Dual Communication Paths (M8)
- **Two separate systems**: Remote AI (Claude Code) and Local LLM (Qwen on Ollama)
- **Remote AI (Task Execution)**: subprocess in same environment (recommended)
- **Local LLM (Validation)**: Always on host machine via HTTP API
  - Handles validation, quality scoring, confidence calculation
  - Requires GPU (Qwen 2.5 Coder on RTX 5090)
  - Accessed at http://10.0.75.1:11434 (Host on vEthernet DevSwitch)

**Key Points**:
- Agent type controls WHERE Claude Code runs (local subprocess vs remote SSH)
- Local LLM location is INDEPENDENT (always on host for GPU access)
- Choose local agent for same-machine deployment (simpler, faster)
- Choose SSH agent only if Claude Code must run remotely

### 7. Headless Mode for Automation (M8)
- **Headless Mode**: Uses `claude --print` flag for non-interactive subprocess execution
- **Dangerous Mode**: Uses `--dangerously-skip-permissions` to bypass all permission prompts
- **Per-Iteration Sessions**: Each orchestration iteration uses a fresh Claude session
  - Eliminates session lock conflicts
  - Obra provides context continuity across sessions
  - 100% reliability, no PTY issues
- **PTY Not Used**: Claude Code has known issues with PTY/terminal emulation (no bugfix)
- **Why This Works**:
  - `subprocess.run()` with `--print` returns output directly
  - No terminal emulation needed (STDIN/STDOUT only)
  - Dangerous mode enables fully autonomous operation
- **Trade-off**: No persistent Claude session, but gains reliability and simplicity

### 8. Core Enhancements for Production (M9)
**Four key improvements for reliability, workflows, and usability:**

- **Retry Logic with Exponential Backoff** ✅:
  - Gracefully handle transient failures (rate limits, timeouts, network issues)
  - Exponential backoff: 1s → 2s → 4s → 8s → 16s (configurable)
  - Jitter prevents thundering herd problems
  - Differentiate retryable vs non-retryable errors

- **Task Dependency System** ✅:
  - Define dependencies: "Task B depends on Task A, C"
  - Topological sort for optimal execution order
  - Cycle detection prevents circular dependencies
  - Automatic blocking until dependencies complete

- **Git Auto-Integration** ✅:
  - Auto-commit after successful task completion
  - LLM-generated semantic commit messages
  - Branch per task: `obra/task-{id}-{slug}`
  - Optional PR creation via `gh` CLI
  - Configurable commit strategy (per-task, per-milestone, manual)

- **Configuration Profiles** ✅:
  - Pre-configured profiles for different project types
  - Profiles: `python_project`, `web_app`, `ml_project`, `microservice`, `minimal`, `production`
  - Override via CLI: `--profile python_project --set key=value`

### 9. LLM-First Prompt Engineering (PHASE_6)
**Validated performance optimization framework:**

- **Hybrid Prompt Format**:
  - JSON metadata for structured data (task context, constraints, dependencies)
  - Natural language for instructions (what Claude does best)
  - Rule-based validation with `PromptRuleEngine`
  - Schema-driven response parsing

- **Validated Improvements** (A/B Testing):
  - **35.2% token efficiency** (p < 0.001, statistically significant)
  - **22.6% faster responses** (p < 0.001, statistically significant)
  - **100% parsing success rate** (vs 87% baseline)
  - Maintained quality scores (no degradation)

- **Key Components**:
  - `StructuredPromptBuilder`: Generates hybrid prompts
  - `StructuredResponseParser`: Parses Claude responses
  - `PromptRuleEngine`: Validates prompts against rules
  - `ABTestingFramework`: Empirical validation
  - `TaskComplexityEstimator`: Complexity analysis

**See**: `docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md` for detailed design

### 10. Interactive Orchestration (v1.5.0 UX Improvement)
**Real-time command injection and natural language interface:**

- **UX Improvement (v1.5.0)**:
  - **Natural language (no slash) defaults to orchestrator** - Just type naturally to communicate with Obra
  - **ALL system commands require `/` prefix** - Including `/help`, `/status`, `/pause`, etc.
  - **Invalid slash commands rejected** - Helpful error messages guide users

- **Interactive Commands**:
  - **Natural text (no slash)** - Send message to orchestrator (DEFAULT)
  - `/help` - Show help message
  - `/status` - Show current task status, iteration, quality score
  - `/pause` / `/resume` - Pause/resume execution
  - `/stop` - Stop execution gracefully
  - `/to-impl <message>` - Send message to implementer (Claude Code)
  - `/override-decision <choice>` - Override orchestrator's decision

- **Interactive Checkpoints** (6 injection points):
  - Before agent execution, after agent response, before validation
  - After validation (low confidence), before decision execution, on error/exception

- **Key Components**:
  - `CommandProcessor`: Parses commands and routes natural language to orchestrator
  - `InputManager`: Non-blocking input with prompt_toolkit and tab completion
  - `TaskStoppedException`: Graceful shutdown signal

**See**: `docs/development/INTERACTIVE_STREAMING_QUICKREF.md` for v1.5.0 command reference

### 11. Session Management Architecture
**Per-iteration session model for maximum reliability:**

- **Architecture**: Fresh Claude session per orchestration iteration
- **Benefits**:
  - Eliminates session lock conflicts (PHASE_4 critical bug fix)
  - No stale state between iterations
  - Simpler error recovery (no session cleanup needed)
  - Works with `--dangerously-skip-permissions` for full autonomy

- **Context Continuity**: Obra maintains state across sessions
  - Task history in StateManager
  - File change tracking via FileWatcher
  - Metrics aggregated at task level (not session level)

- **Configuration**:
  - Context window limits: 200,000 tokens (Claude Pro)
  - Refresh thresholds: 70% warning, 80% refresh, 95% critical
  - Max turns: Task-type specific (5-20 turns)
  - Timeout: 7200s (2 hours) default

**See**: `docs/guides/SESSION_MANAGEMENT_GUIDE.md` for complete guide

### 12. Agile/Scrum Work Hierarchy (v1.3.0 - ADR-013)
**Industry-standard terminology for organizing work at scale:**

- **Work Item Hierarchy**:
  ```
  Product (Project)
    ↓
  Epic (Large feature, 3-15 sessions)
    ↓
  Story (User deliverable, 1 session)
    ↓
  Task (Technical work - default)
    ↓
  Subtask (via parent_task_id)

  Milestone → Checkpoint (zero-duration, when epics complete)
  ```

- **Key Components**:
  - **TaskType Enum**: EPIC, STORY, TASK, SUBTASK
  - **Epic Methods**: `create_epic()`, `get_epic_stories()`, `execute_epic()`
  - **Story Methods**: `create_story()`, `get_story_tasks()`
  - **Milestone Methods**: `create_milestone()`, `check_milestone_completion()`, `achieve_milestone()`

- **Usage Example**:
  ```python
  # Create epic (large feature)
  epic_id = state.create_epic(
      project_id=1,
      title="User Authentication System",
      description="Complete auth with OAuth, MFA, session management"
  )

  # Create stories (user deliverables)
  story1 = state.create_story(1, epic_id, "Email/password login", "As a user...")
  story2 = state.create_story(1, epic_id, "OAuth integration", "As a user...")
  story3 = state.create_story(1, epic_id, "Multi-factor auth", "As a user...")

  # Execute entire epic (runs all stories sequentially)
  orchestrator.execute_epic(project_id=1, epic_id=epic_id)

  # Create milestone (checkpoint)
  milestone = state.create_milestone(1, "Auth Complete", required_epic_ids=[epic_id])

  # Check and achieve milestone
  if state.check_milestone_completion(milestone):
      state.achieve_milestone(milestone)
  ```

- **Database Schema**:
  - Task model: Added `task_type`, `epic_id`, `story_id` fields
  - Milestone model: Separate table with `required_epic_ids` (JSON array)
  - Migration: `migrations/versions/003_agile_hierarchy.sql`

- **Backward Compatibility**:
  - Existing tasks default to `TaskType.TASK`
  - Task dependencies (M9) still work
  - Subtask hierarchy via `parent_task_id` preserved

- **CLI Commands**:
  - `obra epic create/list/show/execute` - Epic management
  - `obra story create/list/show` - Story management
  - `obra milestone create/check/achieve` - Milestone tracking

**See**: `docs/guides/AGILE_WORKFLOW_GUIDE.md` for complete workflow examples
**See**: `docs/decisions/ADR-013-adopt-agile-work-hierarchy.md` for rationale

### 13. Natural Language Command Interface (v1.3.0 - ADR-014)
**Conversational command execution with automatic intent detection:**

- **Unified NL Interface** (Stories 1-5):
  - **IntentClassifier**: Automatically detect COMMAND vs QUESTION intent (95%+ accuracy)
  - **EntityExtractor**: Schema-aware extraction (90%+ accuracy on Obra entities)
  - **CommandValidator**: Business rule validation before execution
  - **CommandExecutor**: StateManager integration with transaction safety
  - **ResponseFormatter**: Color-coded responses with contextual suggestions

- **Pipeline Architecture**:
  ```
  User Input
      ↓
  IntentClassifier (LLM) → COMMAND or QUESTION
      ↓
  ├─ COMMAND → EntityExtractor → CommandValidator → CommandExecutor
  └─ QUESTION → Informational Response
  ```

- **Natural Language Examples**:
  - "Create an epic for user authentication" → Creates epic
  - "Add a story for password reset to epic 5" → Creates story
  - "Show me all open tasks" → Lists tasks
  - "What's the status of milestone 3?" → Shows milestone status

- **Configuration**: `nl_commands` section with confidence thresholds, LLM provider, and master enable switch

- **Performance**: <3s end-to-end latency (P95), 95% intent accuracy, 90% entity extraction accuracy

**See**: `docs/guides/NL_COMMAND_GUIDE.md` for complete user guide
**See**: `docs/decisions/ADR-014-natural-language-command-interface.md` for architecture

### 14. Project Infrastructure Maintenance (v1.4.0 - ADR-015)
**Automatic documentation maintenance and freshness tracking:**

- **DocumentationManager Component**:
  - Freshness checking (30/60/90 day thresholds)
  - Automatic maintenance task creation with rich context
  - Implementation plan archiving
  - CHANGELOG update automation
  - ADR creation suggestions

- **Event-Driven Triggers**:
  - Epic completion hook: Creates maintenance task when `requires_adr=True` or `has_architectural_changes=True`
  - Milestone achievement hook: Creates comprehensive maintenance task with all epic context
  - Periodic freshness checks: Threading-based scheduler (configurable interval, default 7 days)

- **StateManager Integration**:
  - 4 new Task fields: `requires_adr`, `has_architectural_changes`, `changes_summary`, `documentation_status`
  - 1 new Milestone field: `version`
  - Database migration 004 with indexed fields

- **Configuration System**: New `documentation:` section with master enable/disable, per-trigger config, freshness thresholds

- **Test Coverage**: 50 tests (42 unit + 8 integration), 91% coverage

**See**: `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md` for complete user guide
**See**: `docs/decisions/ADR-015-project-infrastructure-maintenance-system.md` for architecture

### 15. Unified Execution Architecture (v1.7.0 - ADR-017)
**All NL commands route through orchestrator for consistent validation:**

- **Architecture**: Single entry point `execute_nl_command()` routes all NL commands through orchestrator
- **Components**:
  - `IntentToTaskConverter`: Converts OperationContext → Task objects
  - `NLQueryHelper`: Handles query-only operations (no task creation)
- **Pipeline**: NLCommandProcessor → ParsedIntent → Orchestrator → Validation Pipeline

- **Benefits**:
  - Consistent quality control for all NL commands
  - Unified validation and scoring
  - Single entry point for monitoring
  - Simplified testing (24 new tests, 100% passing)

- **Performance** (validated in Story 6):
  - P50 latency: < 2s
  - P95 latency: < 3s
  - Throughput: > 40 cmd/min
  - Overhead: < 500ms vs direct access

**See**: `docs/guides/ADR017_MIGRATION_GUIDE.md` for internal API changes
**See**: `docs/decisions/ADR-017-unified-execution-architecture.md` for architecture

## Code Standards

### Type Hints (Required)
```python
def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    pass
```

### Docstrings (Required - Google Style)
```python
def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    """Send a prompt to the agent and get response.

    Args:
        prompt: The text prompt to send
        context: Optional context dict with task info

    Returns:
        Agent's response as string

    Raises:
        AgentException: If agent communication fails
    """
    pass
```

### Exception Handling
```python
# Use custom exceptions with context
raise AgentException(
    "Cannot connect to agent",
    context={'host': host, 'port': port},
    recovery="Check network connectivity and agent process status"
)
```

### Configuration-Driven Design
```python
# Load agent from config, not hardcode
agent_type = config.get('agent.type')
agent = AgentRegistry.get(agent_type)()
agent.initialize(config.get('agent.config'))
```

## Testing Requirements

### ⚠️ CRITICAL: Read TEST_GUIDELINES.md First

**Before writing ANY tests, read [`docs/development/TEST_GUIDELINES.md`](docs/development/TEST_GUIDELINES.md)** to prevent WSL2 crashes.

**Key rules:**
- ⚠️ Max sleep per test: 0.5s (use `fast_time` fixture for longer)
- ⚠️ Max threads per test: 5 (with mandatory `timeout=` on join)
- ⚠️ Max memory allocation: 20KB per test
- ⚠️ Mark heavy tests: `@pytest.mark.slow`

**Why:** M2 testing caused multiple WSL2 crashes from:
- 75+ seconds of cumulative sleeps
- 25+ concurrent threads without timeouts
- 100KB+ memory allocations
- No cleanup of background threads

### Coverage Targets (All Met!)
- **Overall**: ≥85% coverage → **88% achieved** ✅
- **Critical modules**: ≥90% → **DecisionEngine 96%, QualityController 99%, ContextManager 92%** ✅
- **M0 (foundation)**: ≥95% → **95% achieved** ✅
- **M9 modules**: ≥90% → **RetryManager 91%, DependencyResolver 97%, GitManager 95%** ✅

### Test Structure
```python
# Use shared test_config fixture from conftest.py
def test_with_config(test_config):
    orchestrator = Orchestrator(config=test_config)
    assert orchestrator.config is not None

# Use fast_time fixture to avoid blocking sleeps
def test_completion_detection(fast_time):
    monitor.mark_complete()
    time.sleep(2.0)  # Instant! Mocked by fast_time
    assert monitor.is_complete()

# Threading with limits and timeouts
def test_concurrent_operations():
    errors = []
    threads = [threading.Thread(target=worker) for _ in range(3)]  # Max 5
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)  # MANDATORY timeout
    assert len(errors) == 0
```

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run automated setup
./setup.sh
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term

# Run specific module tests
pytest tests/test_plugins.py              # M0
pytest tests/test_state.py                # M1
pytest tests/test_orchestrator.py         # M6
pytest tests/test_integration_e2e.py      # Integration
pytest tests/test_retry_manager.py        # M9
pytest tests/test_command_processor.py    # Interactive
pytest tests/test_structured_prompts.py   # PHASE_6
```

### Code Quality
```bash
# Type checking
mypy src/

# Linting
pylint src/

# Format code
black src/ tests/
```

### Running Obra
```bash
# Initialize
python -m src.cli init

# Create project with profile
python -m src.cli project create "My Project" --profile python_project

# Create task with dependencies
python -m src.cli task create "Implement feature X" --project 1 --depends-on 5,6

# Execute task
python -m src.cli task execute 1

# Interactive mode (with command injection)
python -m src.cli interactive
```

### LLM Management

**Graceful Fallback**: Obra loads even if LLM service is unavailable, allowing you to configure and connect later.

```bash
# Check LLM connection status
python -m src.cli llm status

# List available LLM providers
python -m src.cli llm list

# Reconnect to current LLM (after service comes online)
python -m src.cli llm reconnect

# Switch to different LLM provider
python -m src.cli llm reconnect --type openai-codex --model gpt-5-codex
python -m src.cli llm reconnect --type ollama --endpoint http://localhost:11434

# Quick switch between providers
python -m src.cli llm switch ollama
python -m src.cli llm switch openai-codex --model gpt-5-codex
```

**Configuration Options**:
```yaml
# Option 1: Local LLM (Ollama/Qwen)
llm:
  type: ollama
  model: qwen2.5-coder:32b
  api_url: http://localhost:11434
  temperature: 0.7

# Option 2: Remote LLM (OpenAI Codex)
llm:
  type: openai-codex
  model: gpt-5-codex  # or codex-mini-latest, o3, o4-mini
  timeout: 120
```

**Environment Variables** (alternative to config file):
```bash
# Switch to OpenAI Codex via environment
export ORCHESTRATOR_LLM_TYPE=openai-codex
export ORCHESTRATOR_LLM_MODEL=gpt-5-codex

# Switch to Ollama via environment
export ORCHESTRATOR_LLM_TYPE=ollama
export ORCHESTRATOR_LLM_API_URL=http://localhost:11434
```

**Programmatic Reconnection**:
```python
# In Python/interactive mode
orchestrator.reconnect_llm()  # Reconnect to current config

# Switch LLM provider
orchestrator.reconnect_llm(
    llm_type='openai-codex',
    llm_config={'model': 'gpt-5-codex', 'timeout': 120}
)

# Check if LLM is available
if orchestrator.check_llm_available():
    orchestrator.execute_task(task_id=1)
else:
    print("LLM not available, reconnect first")
```

**Git Operations**: This repository uses SSH authentication (`git@github.com:Omar-Unpossible/claude_code_orchestrator.git`)

## Changelog Maintenance

**Update CHANGELOG.md for significant changes** (features, bug fixes, architectural changes, performance improvements, breaking changes).

**Format**: Use semantic versioning (MAJOR.MINOR.PATCH) and Keep a Changelog format. Add entries under `[Unreleased]` section before committing.

**See**: `CHANGELOG.md` for format examples and version history.

## Data Flow (High-Level)

```
User initiates task
    ↓
Orchestrator gets task from StateManager
    ↓
ContextManager builds context from history
    ↓
StructuredPromptBuilder creates optimized hybrid prompt (PHASE_6)
    ↓
[Interactive Checkpoint 1: Before agent execution]
    ↓
Agent (via plugin) executes task in fresh session
    ↓
[Interactive Checkpoint 2: After agent response]
    ↓
FileWatcher detects changes (optional)
    ↓
[Interactive Checkpoint 3: Before validation]
    ↓
ResponseValidator checks format/completeness
    ↓
QualityController validates correctness
    ↓
ConfidenceScorer rates confidence (heuristic + LLM ensemble)
    ↓
[Interactive Checkpoint 4: After validation (if low confidence)]
    ↓
DecisionEngine decides next action (proceed/retry/clarify/escalate)
    ↓
[Interactive Checkpoint 5: Before decision execution]
    ↓
StateManager persists everything (atomic transaction)
    ↓
GitManager commits changes (if enabled)
    ↓
Loop continues or breakpoint triggered
    ↓
[Interactive Checkpoint 6: On error/exception]
```

See `docs/architecture/data_flow.md` for detailed flow diagrams.

## Common Pitfalls to Avoid

### Core Architecture
- ❌ **Don't bypass StateManager**: All state goes through it, no direct DB access
- ❌ **Don't reverse validation order**: Always ResponseValidator → QualityController → ConfidenceScorer
- ❌ **Don't hardcode agents**: Use plugin system, load from config
- ❌ **Don't forget thread safety**: StateManager and Registry must be thread-safe

### Testing
- ❌ **Don't skip test guidelines**: WSL2 crashes are preventable! Read TEST_GUIDELINES.md
- ❌ **Don't exceed test resource limits**: Max 0.5s sleep, 5 threads, 20KB per test
- ❌ **Don't assume unit tests catch integration bugs**: 88% coverage missed 6 bugs in PHASE_4

### Configuration & APIs
- ❌ **Don't implement cost tracking**: This is subscription-based
- ❌ **Don't use Config() directly**: Always use `Config.load()`
- ❌ **Don't assume StateManager API**: Check method signatures - use named args
- ❌ **Don't use wrong model attributes**: Use `project_name` not `name`, `working_directory` not `working_dir`
- ❌ **Don't run setup.sh without OBRA_RUNTIME_DIR**: Set environment variable first
- ❌ **Don't assume profile exists** (M9): Always validate profile name before loading

### LLM Management
- ✅ **Obra loads without LLM**: Graceful fallback allows initialization even if LLM unavailable
- ✅ **Use `orchestrator.reconnect_llm()`**: Connect to LLM after Obra starts
- ✅ **Check LLM before tasks**: Use `orchestrator.check_llm_available()` before executing tasks
- ✅ **CLI commands available**: `obra llm status`, `obra llm reconnect`, `obra llm switch`
- ❌ **Don't panic if LLM down**: Obra will load and prompt you to reconnect

### M9 Features
- ❌ **Don't retry non-retryable errors**: Check error type before applying retry logic
- ❌ **Don't create circular dependencies**: DependencyResolver will reject cycles
- ❌ **Don't commit without checking git status**: GitManager checks for uncommitted changes first

### Session Management
- ❌ **Don't reuse sessions across iterations**: Use fresh session per iteration (PHASE_4 fix)
- ❌ **Don't aggregate metrics at session level**: Use task-level aggregation (session metrics are ephemeral)

### Documentation
- ❌ **Don't save docs in wrong locations**: Always use `docs/` subfolders, never project root or `/tmp`
  - Planning → `docs/development/` or `docs/design/`
  - Architecture → `docs/architecture/`
  - Decisions → `docs/decisions/`
  - Guides → `docs/guides/`
- ❌ **Don't create duplicate docs**: Check `docs/archive/README.md` first

## Hardware & Environment

**Target Deployment**:
- **Host**: Windows 11 Pro with Hyper-V
- **LLM**: Qwen 2.5 Coder 32B via Ollama on RTX 5090 (32GB VRAM)
- **VM**: Windows 11 Pro guest with WSL2 (Ubuntu 22.04)
- **Agent**: Claude Code CLI in VM WSL2 (isolated execution)
- **Database**: SQLite (simple) or PostgreSQL (production)

**Deployment**: Host runs Ollama+Qwen (GPU) → Hyper-V VM → WSL2 (Obra + Claude Code + Workspace)

See `docs/guides/COMPLETE_SETUP_WALKTHROUGH.md` for detailed setup instructions.

## External References

- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) - Local LLM interface
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code) - Agent documentation
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/) - Database layer
- [Click CLI](https://click.palletsprojects.com/) - CLI framework
- [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/) - Interactive input handling

## Working with This Codebase

### Starting a New Session

1. Read this file (CLAUDE.md) for overview
2. Read `docs/design/OBRA_SYSTEM_OVERVIEW.md` for complete system understanding
3. Review `CHANGELOG.md` for recent changes
4. Read `docs/architecture/ARCHITECTURE.md` for technical architecture
5. Read `docs/development/TEST_GUIDELINES.md` if writing tests

### Making Changes

- **Core implementation complete** - Focus on enhancements, optimization, and validation
- **Follow existing patterns** - Plugin system, StateManager access, validation order
- **Maintain test coverage** - Add tests for new features (≥85% coverage)
- **Update documentation** - Keep docs in sync with code changes
- **Test before committing** - Run `pytest --cov=src` to verify
- **Real-world validation** - Unit tests don't catch integration bugs; test with actual orchestration

### When Stuck

- **System overview**: Read `docs/design/OBRA_SYSTEM_OVERVIEW.md` for complete system understanding
- **Architecture decisions**: Check `docs/decisions/` for ADRs (14 total)
- **Latest changes**: Review `CHANGELOG.md` and `docs/development/phase-reports/`
- **Technical architecture**: Consult `docs/architecture/ARCHITECTURE.md`
- **Natural language interface**: See `docs/guides/NL_COMMAND_GUIDE.md` for conversational commands
- **Project maintenance**: See `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md` for auto-doc maintenance
- **Testing issues**: Check `docs/development/WSL2_TEST_CRASH_POSTMORTEM.md` for WSL2 crash prevention
- **Configuration**: See `docs/guides/CONFIGURATION_PROFILES_GUIDE.md` for profile setup
- **Historical context**: Browse `docs/archive/README.md` for archived milestones and analysis

## Future Development

**Note**: Obra v1.5.0 provides a production-ready foundation. Future enhancements focus on security, observability, and enterprise features based on user demand.

### Proposed Enhancement Areas

**Security Hardening**:
- Input sanitization (prompt injection detection)
- Output sanitization (PII/secret redaction)
- Git operation confirmation prompts
- Security audit trail
- Secrets management integration

**Template System**:
- Domain-specific prompt templates (Bug Fix, Refactoring, Frontend, API, IaC)
- Auto-detection via keywords
- 40% quality improvement for specialized domains
- Template registry pattern

**Observability**:
- Structured JSON logging
- Correlation IDs for task lifecycle tracing
- Approval gate timestamps
- Privacy-preserving log analysis
- Pre-commit hooks for quality checks

**Multi-Agent Orchestration**:
- ParallelAgentCoordinator maturation
- Hierarchical delegation (multi-agent epics)
- Standard message format for agents
- Summarization for completed phases
- Circuit breaker patterns

**Enterprise Features** (if demand validated):
- GDPR/HIPAA/SOC2 compliance frameworks
- Web UI dashboard (real-time monitoring)
- Distributed orchestration (multi-cloud)
- Advanced RAG integration

**See**: Enhancement proposals in `docs/design/enhancements/` for detailed specifications and rationale

---

**Last Updated**: November 13, 2025
**Version**: v1.7.2 (Testing Infrastructure Foundation - Story 0)
**Previous Versions**: v1.7.1 (Observability), v1.7.0 (Unified Execution), v1.5.0 (Interactive UX), v1.4.0 (Project Infrastructure)
**Test Coverage**: 88% overall (815+ tests, 72 test files)
**ADRs**: 17 architecture decision records
