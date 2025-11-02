# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Claude Code orchestration system** where a local LLM (Qwen on RTX 5090) acts as an intelligent supervisor that:
- Monitors Claude Code CLI running in WSL2/VM
- Validates Claude Code's work using fast local inference
- Generates optimized follow-up prompts
- Detects when human intervention is needed (breakpoints)
- Tracks all changes and maintains project state

This enables semi-autonomous software development with Claude Code doing the heavy lifting and the local LLM providing oversight and continuity.

## Project Status

**Current Phase**: Pre-implementation (M0 not started)

The project is following a milestone-based implementation plan:
- **M0**: Architecture Foundation (plugin system) - NOT STARTED
- **M1**: Core Infrastructure (database, state) - NOT STARTED
- **M2**: LLM & Agent Interfaces - NOT STARTED
- **M3**: File Monitoring - NOT STARTED
- **M4**: Orchestration Engine - NOT STARTED
- **M5**: Utility Services - NOT STARTED
- **M6**: Integration & CLI - NOT STARTED
- **M7**: Testing & Deployment - NOT STARTED

**See**: `IMPLEMENTATION_PLAN.md` for detailed roadmap and `plans/*.json` for detailed specifications.

## Architecture Principles

### 1. Plugin System (Foundation)
- **AgentPlugin** and **LLMPlugin** are abstract base classes defining interfaces
- Agents (Claude Code, Aider, etc.) and LLM providers (Ollama, llama.cpp) are pluggable
- Decorator-based registration: `@register_agent('name')`
- Enables testing with mock plugins and runtime agent swapping
- **Rule**: Start with M0 - plugin interfaces must be defined before implementation

### 2. StateManager is Single Source of Truth
- **ALL** state access MUST go through StateManager - NO direct database access
- Prevents inconsistencies, enables atomic transactions, supports rollback
- Thread-safe with proper locking
- **Rule**: Never bypass StateManager even for "quick reads"

### 3. Validation Order Matters
- **Sequence**: ResponseValidator → QualityController
- Validate completeness (format, structure) BEFORE quality (correctness, requirements)
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

## Project Structure

```
claude_code_orchestrator/
├── src/
│   ├── plugins/         # M0: START HERE - AgentPlugin/LLMPlugin interfaces
│   ├── core/            # M1: State, config, models, exceptions
│   ├── llm/             # M2: Local LLM interface, validation
│   ├── agents/          # M2: Claude Code agent implementations
│   ├── monitoring/      # M3: File watching
│   ├── orchestration/   # M4: Task scheduling, decisions, breakpoints
│   └── utils/           # M5: Token counting, context management
├── plans/               # Detailed JSON specifications for each milestone
│   ├── 00_architecture_overview.json  # M0 details
│   ├── 01_foundation.json             # M1 details
│   ├── 02_interfaces.json             # M2 details
│   └── [03-07]_*.json                 # M3-M7 details
├── docs/
│   ├── architecture/    # System design, data flow diagrams
│   └── decisions/       # Architecture Decision Records (ADRs)
├── tests/
│   └── mocks/           # Mock plugins for testing
├── config/              # YAML configuration files
├── IMPLEMENTATION_PLAN.md   # High-level roadmap (READ FIRST)
└── GETTING_STARTED.md       # Seed prompt for implementation
```

## Implementation Workflow

### Before Starting Any Milestone

1. **Read the plan**: `plans/0X_*.json` for the milestone you're working on
2. **Check dependencies**: Ensure prerequisite milestones are complete
3. **Follow implementation order**: Some deliverables have dependencies within milestones
4. **Update progress**: Mark milestone status in `IMPLEMENTATION_PLAN.md` as you work

### For Milestone 0 (Architecture Foundation)

**Implementation Order**: 0.1 → 0.2 → 0.3

**Deliverables**:
- **0.1**: Plugin interfaces in `src/plugins/base.py` (AgentPlugin, LLMPlugin ABCs)
- **0.2**: Plugin registry in `src/plugins/registry.py` (decorator-based registration)
- **0.3**: Architecture documentation (design decisions, diagrams, ADRs)

**Acceptance Criteria**:
- Can instantiate different agent types via configuration
- Tests pass with ≥95% coverage
- Type checking passes (mypy)
- Linting score ≥9.0 (pylint)
- Mock plugins work (EchoAgent, MockAgent, ErrorAgent)

### For Milestone 1 (Core Infrastructure)

**Implementation Order**: 1.4 → 1.3 → 1.1 → 1.2 (exceptions first!)

**Why this order**:
- Exceptions are used everywhere (build first)
- Config is needed by StateManager
- Models define database schema
- StateManager uses all of the above

**Critical**: StateManager must be thread-safe with transaction support. This is the spine of the system.

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

**Before writing tests, read [`TEST_GUIDELINES.md`](./TEST_GUIDELINES.md)** to prevent WSL2 crashes.

**Key rules:**
- ⚠️ Max sleep per test: 0.5s (use `fast_time` fixture for longer)
- ⚠️ Max threads per test: 5 (with mandatory `timeout=` on join)
- ⚠️ Max memory allocation: 20KB per test
- ⚠️ Mark heavy tests: `@pytest.mark.slow`

**Why:** M2 testing caused multiple WSL2 crashes from:
- 75+ seconds of cumulative sleeps in test_output_monitor.py
- 25+ concurrent threads without timeouts
- 100KB+ memory allocations
- No cleanup of background threads

See `TEST_GUIDELINES.md` for complete rules and examples.

### Coverage Targets
- **Overall**: ≥85% coverage
- **Critical modules** (StateManager, DecisionEngine, TaskScheduler): ≥90%
- **M0 (foundation)**: ≥95%

### Test Structure
```python
# Create mock plugins for testing
@register_agent('mock')
class MockAgent(AgentPlugin):
    """Test double that returns configurable responses"""
    pass

# Test both success and failure paths
def test_agent_connection_success():
    pass

def test_agent_connection_failure():
    pass

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

### Performance Targets
- Local LLM response (p95): <10s
- State operation (p95): <100ms
- File change detection: <1s
- **Test file execution: <30s**
- **Full test suite: <2 minutes**

## Development Commands

**Note**: Project is pre-implementation. These commands will be relevant once code is written.

### Setup (Future)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies (once requirements.txt exists)
pip install -r requirements-dev.txt

# Verify environment
python scripts/validate_env.py
```

### Testing (Future)
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term

# Run specific milestone tests
pytest tests/test_plugins.py  # M0
pytest tests/test_state.py    # M1
```

### Code Quality (Future)
```bash
# Type checking
mypy src/

# Linting
pylint src/

# Format code
black src/ tests/
isort src/ tests/
```

## Key Files to Reference

### Planning Documents
- **`IMPLEMENTATION_PLAN.md`**: High-level roadmap, milestone overview, progress tracking
- **`GETTING_STARTED.md`**: Detailed seed prompt with step-by-step M0 instructions
- **`plans/00_architecture_overview.json`**: Complete M0 specification with acceptance criteria

### Architecture Decisions
All major architectural decisions are documented in `plans/00_architecture_overview.json` under `architectural_decisions`:
- **decision_001**: Why plugin system (not hardcoded)
- **decision_002**: Multiple deployment models (SSH/Docker/Local)
- **decision_003**: StateManager as single source of truth
- **decision_004**: Validation ordering (ResponseValidator before QualityController)
- **decision_005**: No cost tracking (subscription-based)

## Data Flow (High-Level)

```
User initiates task
    ↓
Orchestrator gets task from TaskScheduler
    ↓
PromptGenerator creates optimized prompt with context
    ↓
Agent (via plugin) executes task
    ↓
FileWatcher detects changes
    ↓
ResponseValidator checks completeness
    ↓
QualityController validates correctness
    ↓
DecisionEngine decides next action (proceed/retry/breakpoint)
    ↓
StateManager persists everything
    ↓
Loop continues or breakpoint triggered
```

## Common Pitfalls to Avoid

1. **Don't bypass StateManager**: All state goes through it, no direct DB access
2. **Don't reverse validation order**: Always ResponseValidator before QualityController
3. **Don't hardcode agents**: Use plugin system, load from config
4. **Don't implement M1 before M0**: Plugin interfaces are the foundation
5. **Don't skip tests**: Write tests alongside code, aim for coverage targets
6. **Don't forget thread safety**: StateManager and Registry must be thread-safe
7. **Don't implement cost tracking**: This is subscription-based (see decision_005)

## Progress Tracking

After completing each deliverable:
1. Update `IMPLEMENTATION_PLAN.md` progress table
2. Mark milestone status (🔴 → 🟡 → 🟢)
3. Commit with clear message: `"M0.1: Implement plugin interfaces"`
4. Update notes column with key decisions or issues
5. Run tests and verify coverage meets target

## Hardware & Environment

- **Target**: Windows 11 + WSL2 (primary), Docker (for distribution)
- **LLM**: Qwen2.5-Coder 32B via Ollama on RTX 5090 (32GB VRAM)
- **Agent**: Claude Code CLI in isolated VM (via SSH for safety)
- **Language**: Python 3.10+
- **Database**: SQLite (simple) or PostgreSQL (robust) - decision pending

## External References

- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) - Local LLM interface
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code) - Agent documentation
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/) - Database layer
- [Click CLI](https://click.palletsprojects.com/) - CLI framework (likely choice)

## Working with This Codebase

### Starting Implementation
1. Read `IMPLEMENTATION_PLAN.md` for context (10 minutes)
2. Read `plans/00_architecture_overview.json` for M0 details (20 minutes)
3. Create project structure: `mkdir -p src/plugins tests/mocks docs/{architecture,decisions} config`
4. Begin with deliverable 0.1: `src/plugins/base.py`
5. Write tests alongside code: `tests/test_plugins.py`
6. Update progress in `IMPLEMENTATION_PLAN.md` after each deliverable

### Making Changes
- **Follow milestone order**: M0 → M1 → M2 → ... (see dependency graph)
- **Read the JSON plan** for the milestone before starting
- **Check implementation_order** within milestone (some deliverables have dependencies)
- **Meet acceptance criteria** before considering deliverable done
- **Update documentation** as you implement (don't defer to later)

### When Stuck
- Check `architectural_decisions` in `plans/00_architecture_overview.json`
- Review `risks_and_mitigations` section in relevant plan
- Consult `implementation_notes` in deliverable specification
- Follow `testing_strategy` for guidance on test structure

## Definition of Done (Per Milestone)

- [ ] All deliverables implemented
- [ ] Tests pass with coverage ≥ target (M0: 95%, others: 85-90%)
- [ ] Type checking passes (mypy)
- [ ] Linting score ≥9.0 (pylint)
- [ ] Documentation complete (code + architecture)
- [ ] Progress tracked in `IMPLEMENTATION_PLAN.md`
- [ ] Acceptance criteria met (see `plans/*.json`)
- [ ] Code reviewed (for multi-person teams)

## Critical Success Factors

1. **Plugin system enables flexibility** - Multiple agents without core changes
2. **StateManager is single source of truth** - All state goes through it
3. **Validation before quality control** - Order matters for correctness
4. **File watching tracks changes** - Enables rollback capability
5. **Breakpoints enable oversight** - Human intervention at critical points
6. **Thread-safe operations** - Concurrent access properly locked
