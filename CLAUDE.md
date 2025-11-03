# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Obra** (Claude Code Orchestrator) is an intelligent supervision system where a local LLM (Qwen 2.5 Coder on RTX 5090) acts as an oversight layer that:
- Monitors Claude Code CLI running in isolated VM/WSL2
- Validates Claude Code's work using fast local inference
- Generates optimized follow-up prompts
- Detects when human intervention is needed (breakpoints)
- Tracks all changes and maintains project state

This enables semi-autonomous software development with Claude Code doing the heavy lifting and the local LLM providing oversight and continuity.

## Project Status

**Current Phase**: ✅ **PRODUCTION-READY (v1.1)** - All milestones complete including M8!

**Implementation complete**:
- ✅ **M0**: Architecture Foundation (plugin system) - 95% coverage
- ✅ **M1**: Core Infrastructure (database, state) - 84% coverage
- ✅ **M2**: LLM & Agent Interfaces - 90% coverage
- ✅ **M3**: File Monitoring - 90% coverage
- ✅ **M4**: Orchestration Engine - 96-99% coverage (critical modules)
- ✅ **M5**: Utility Services - 91% coverage
- ✅ **M6**: Integration & CLI - Complete with 122 tests
- ✅ **M7**: Testing & Deployment - 88% overall coverage
- ✅ **M8**: Local Agent Implementation - 100% coverage (33 tests)

**Key Metrics**:
- **Overall Coverage**: 88% (exceeds 85% target)
- **Total Tests**: 433+ (400+ from M0-M7, 33 from M8)
- **Total Code**: ~15,600 lines (8,900 production + 4,700 tests + 2,000 docs)

**Current Status**:
- ✅ Setup complete on WSL2
- ✅ 6 critical bugs fixed (Config loading, StateManager API, CLI bugs)
- ✅ 14 integration tests added
- ✅ **M8 - Local Agent** - Complete with 33 tests, 100% coverage
- ⏳ **Real-world validation** with Claude Code CLI (next step)

See `docs/development/milestones/M7_COMPLETION_SUMMARY.md` for detailed M0-M7 status.
See `docs/development/milestones/M8_COMPLETION_SUMMARY.md` for M8 local agent implementation.
See `docs/development/CLAUDE_CODE_LOCAL_AGENT_PLAN.md` for M8 implementation plan (historical).

## Documentation Structure

All documentation has been organized into logical directories:

```
docs/
├── README.md                         # Documentation index
├── guides/                           # User-facing guides
│   ├── COMPLETE_SETUP_WALKTHROUGH.md # Windows 11 + Hyper-V setup
│   └── GETTING_STARTED.md            # Quick start guide
├── architecture/                     # System architecture
│   ├── ARCHITECTURE.md               # Complete M0-M6 design
│   ├── plugin_system.md
│   ├── data_flow.md
│   └── system_design.md
├── decisions/                        # Architecture Decision Records
│   ├── 001_why_plugins.md
│   ├── 002_deployment_models.md
│   ├── 003_state_management.md
│   ├── ADR-003-file-watcher-thread-cleanup.md
│   └── ADR-004-local-agent-architecture.md  # Local agent design
├── design/                                         # Design docs and diagrams
│   └── design_future.md                            # Planned backlog features
│   └── obra-technical-design.md                    # Technical backlog
│   └── obra-technical-design-enhanced.md           # Technical backlog (enhanced)
├── development/                      # Development docs
│   ├── IMPLEMENTATION_PLAN.md        # M0-M7 roadmap
│   ├── CLAUDE_CODE_LOCAL_AGENT_PLAN.md  # M8 local agent plan ⚠️
│   ├── TEST_GUIDELINES.md            # Testing best practices ⚠️
│   ├── STATUS_REPORT.md
│   ├── WSL2_TEST_CRASH_POSTMORTEM.md
│   └── milestones/                   # Milestone summaries
│       ├── M1_PROGRESS.md
│       ├── M2_COMPLETION_SUMMARY.md
│       ├── M4_COMPLETION_SUMMARY.md
│       ├── M5_COMPLETION_SUMMARY.md
│       ├── M6_COMPLETION_SUMMARY.md
│       ├── M7_COMPLETION_SUMMARY.md
│       └── M8_COMPLETION_SUMMARY.md  # Local agent implementation
└── archive/                          # Historical documents
```

## Quick Context Refresh

When starting a new session, read these documents in order:

1. **[README.md](README.md)** - Project overview (371 lines)
2. **[docs/development/milestones/M8_COMPLETION_SUMMARY.md](docs/development/milestones/M8_COMPLETION_SUMMARY.md)** - Latest status (M8 local agent)
3. **[docs/development/milestones/M7_COMPLETION_SUMMARY.md](docs/development/milestones/M7_COMPLETION_SUMMARY.md)** - M0-M7 status
4. **[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** - System design (591 lines)
5. **[docs/development/IMPLEMENTATION_PLAN.md](docs/development/IMPLEMENTATION_PLAN.md)** - Complete roadmap
6. **[docs/development/TEST_GUIDELINES.md](docs/development/TEST_GUIDELINES.md)** - ⚠️ Critical for testing!

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
- **Two separate systems**: Agent (Claude Code) and LLM (Ollama)
- **Agent (Task Execution)**:
  - **Local Agent** (recommended): subprocess in same environment
  - **SSH Agent**: network connection to remote VM
  - Handles code generation and task execution
- **LLM (Validation)**: Always on host machine via HTTP API
  - Handles validation, quality scoring, confidence calculation
  - Requires GPU (Qwen 2.5 Coder on RTX 5090)
  - Accessed at http://172.29.144.1:11434

**Architecture Diagram**:
```
┌─────────────────────────────────────────────────────────────┐
│ HOST MACHINE (Windows 11 Pro)                               │
│  Ollama + Qwen (RTX 5090, GPU) ← HTTP API                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Hyper-V VM → WSL2                                     │  │
│  │   Obra ─┬─→ subprocess → Claude Code (Local)         │  │
│  │         └─→ SSH → Remote Claude Code (Optional)      │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key Points**:
- Agent type controls WHERE Claude Code runs (local vs remote)
- LLM location is INDEPENDENT (always on host for GPU access)
- Choose local agent for same-machine deployment (simpler, faster)
- Choose SSH agent only if Claude Code must run remotely

## Project Structure

```
obra/  (claude_code_orchestrator/)
├── src/
│   ├── plugins/         # M0: AgentPlugin/LLMPlugin interfaces
│   ├── core/            # M1: State, config, models, exceptions
│   ├── llm/             # M2: Local LLM interface, validation, prompts
│   ├── agents/          # M2/M8: Agent implementations
│   │   ├── claude_code_ssh.py      # SSH agent (remote)
│   │   ├── claude_code_local.py    # Local agent (M8 - planned)
│   │   └── output_monitor.py       # Output parsing
│   ├── monitoring/      # M3: File watching
│   ├── orchestration/   # M4: Scheduling, decisions, breakpoints, quality
│   ├── utils/           # M5: Token counting, context, confidence
│   ├── orchestrator.py  # M6: Main integration loop
│   ├── cli.py           # M6: Click-based CLI
│   └── interactive.py   # M6: REPL interface
├── tests/               # 400+ comprehensive tests
│   ├── conftest.py      # Shared fixtures (test_config, fast_time)
│   ├── test_*.py        # Module tests
│   └── test_integration_e2e.py  # 14 integration tests
├── docs/                # Organized documentation (see structure above)
├── config/              # YAML configuration files
├── data/                # SQLite database (runtime)
├── logs/                # Application logs (runtime)
├── Dockerfile           # Docker deployment
├── docker-compose.yml   # Multi-service deployment
├── setup.sh             # Automated setup script
├── requirements.txt     # Python dependencies
└── README.md            # Project overview
```

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

# Run specific milestone tests
pytest tests/test_plugins.py        # M0
pytest tests/test_state.py          # M1
pytest tests/test_orchestrator.py   # M6
pytest tests/test_integration_e2e.py  # M7 integration
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

# Create project
python -m src.cli project create "My Project"

# Create task
python -m src.cli task create "Implement feature X" --project 1

# Execute task
python -m src.cli task execute 1

# Interactive mode
python -m src.cli interactive
```

### Git Operations

**⚠️ IMPORTANT: This repository uses SSH for git operations**

The repository is configured to use SSH (not HTTPS) for authentication:
- **Remote URL**: `git@github.com:Omar-Unpossible/claude_code_orchestrator.git`
- **Authentication**: SSH keys (no passwords/tokens needed)
- **Benefit**: No GPG passphrase prompts, seamless push/pull

```bash
# Verify SSH is configured
git remote -v
# Should show: git@github.com:Omar-Unpossible/...

# Test SSH authentication
ssh -T git@github.com
# Should show: Hi Omar-Unpossible! You've successfully authenticated

# Git operations work seamlessly
git pull origin main    # No prompts
git push origin main    # No prompts
git fetch origin        # Automatic
```

**If you need to switch from HTTPS to SSH:**
```bash
# Check current remote
git remote -v

# If using HTTPS, switch to SSH
git remote set-url origin git@github.com:Omar-Unpossible/claude_code_orchestrator.git

# Remove credential helper (not needed for SSH)
git config --local --unset credential.helper
```

**SSH Key Setup** (if needed):
```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t ed25519 -C "omar@unpossiblecreations.com"

# Add to SSH agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Copy public key and add to GitHub
cat ~/.ssh/id_ed25519.pub
# Add at: https://github.com/settings/keys
```

## Data Flow (High-Level)

```
User initiates task
    ↓
Orchestrator gets task from StateManager
    ↓
ContextManager builds context from history
    ↓
PromptGenerator creates optimized prompt
    ↓
Agent (via plugin) executes task in isolated environment
    ↓
FileWatcher detects changes (optional)
    ↓
ResponseValidator checks format/completeness
    ↓
QualityController validates correctness
    ↓
ConfidenceScorer rates confidence (heuristic + LLM ensemble)
    ↓
DecisionEngine decides next action (proceed/retry/clarify/escalate)
    ↓
StateManager persists everything (atomic transaction)
    ↓
Loop continues or breakpoint triggered
```

See `docs/architecture/data_flow.md` for detailed flow diagrams.

## Common Pitfalls to Avoid

1. ❌ **Don't bypass StateManager**: All state goes through it, no direct DB access
2. ❌ **Don't reverse validation order**: Always ResponseValidator → QualityController → ConfidenceScorer
3. ❌ **Don't hardcode agents**: Use plugin system, load from config
4. ❌ **Don't skip test guidelines**: WSL2 crashes are preventable!
5. ❌ **Don't forget thread safety**: StateManager and Registry must be thread-safe
6. ❌ **Don't implement cost tracking**: This is subscription-based
7. ❌ **Don't exceed test resource limits**: Read TEST_GUIDELINES.md!
8. ❌ **Don't use Config() directly**: Always use `Config.load()` to load configuration
9. ❌ **Don't assume StateManager API**: Check method signatures - use named args
10. ❌ **Don't use wrong model attributes**: Use `project_name` not `name`, `working_directory` not `working_dir`
11. ❌ **Don't run setup.sh without OBRA_RUNTIME_DIR**: Set environment variable to avoid runtime files in repo

## Hardware & Environment

**Target Deployment**:
- **Host**: Windows 11 Pro with Hyper-V
- **LLM**: Qwen 2.5 Coder 32B via Ollama on RTX 5090 (32GB VRAM)
- **VM**: Windows 11 Pro guest with WSL2 (Ubuntu 22.04)
- **Agent**: Claude Code CLI in VM WSL2 (isolated execution)
- **Database**: SQLite (simple) or PostgreSQL (production)

**Architecture**:
```
Host (Windows 11 Pro)
├─ Ollama + Qwen (GPU-accelerated)
└─ Hyper-V
    └─ VM (Windows 11 Pro)
        └─ WSL2 (Ubuntu)
            ├─ Obra Orchestrator
            ├─ Claude Code CLI
            └─ Workspace
```

See `docs/guides/COMPLETE_SETUP_WALKTHROUGH.md` for detailed setup instructions.

## External References

- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) - Local LLM interface
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code) - Agent documentation
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/) - Database layer
- [Click CLI](https://click.palletsprojects.com/) - CLI framework

## Working with This Codebase

### Starting a New Session

1. Read this file (CLAUDE.md) for overview
2. Read `docs/development/milestones/M7_COMPLETION_SUMMARY.md` for latest status
3. Read `docs/architecture/ARCHITECTURE.md` for system design
4. Read `docs/development/TEST_GUIDELINES.md` if writing tests
5. Check `README.md` for quick reference

### Making Changes

- **All milestones complete** - Focus on bug fixes, optimization, and real-world testing
- **Follow existing patterns** - Plugin system, StateManager access, validation order
- **Maintain test coverage** - Add tests for new features (≥85% coverage)
- **Update documentation** - Keep docs in sync with code changes
- **Test before committing** - Run `pytest --cov=src` to verify

### When Stuck

- Check `docs/decisions/` for architectural decisions (ADRs)
- Review `docs/development/IMPLEMENTATION_PLAN.md` for context
- Consult `docs/architecture/ARCHITECTURE.md` for design details
- Read milestone summaries in `docs/development/milestones/`
- Check `docs/development/WSL2_TEST_CRASH_POSTMORTEM.md` for testing issues

## Definition of Done (Milestones)

All M0-M7 milestones have been completed with the following criteria met:

- ✅ All deliverables implemented
- ✅ Tests pass with coverage ≥ target (88% overall, exceeds 85%)
- ✅ Type checking passes (mypy)
- ✅ Linting score ≥9.0 (pylint)
- ✅ Documentation complete (code + architecture)
- ✅ Acceptance criteria met
- ✅ Docker deployment ready
- ✅ Setup automation complete

## Critical Success Factors

1. ✅ **Plugin system enables flexibility** - Multiple agents without core changes
2. ✅ **StateManager is single source of truth** - All state goes through it
3. ✅ **Validation before quality control** - Order matters for correctness
4. ✅ **File watching tracks changes** - Enables rollback capability
5. ✅ **Breakpoints enable oversight** - Human intervention at critical points
6. ✅ **Thread-safe operations** - Concurrent access properly locked
7. ✅ **Comprehensive testing** - 400+ tests, 88% coverage
8. ✅ **Production-ready deployment** - Docker + automated setup

## Next Steps

### Immediate (Real-World Validation)

**Status**: ✅ M8 Complete, ⏳ Ready for real-world testing

1. **Real-world validation with Claude Code CLI**:
   - Execute actual development tasks with local agent
   - Monitor confidence scores and quality metrics
   - Tune thresholds based on real usage
   - Validate breakpoint system with human intervention
   - Performance benchmarking (local vs SSH agent)

2. **Configuration and deployment**:
   - Create example configurations for local agent
   - Test end-to-end orchestration workflow
   - Document best practices and common patterns
   - Production deployment guide

3. **Documentation updates**:
   - Update README.md with M8 completion
   - Add local agent usage examples
   - Update architecture diagrams
   - Create troubleshooting guide

### v1.2 (Enhancements)

- [ ] Web UI dashboard (real-time monitoring)
- [ ] WebSocket updates for live status
- [ ] Multi-project orchestration
- [ ] Pattern learning from successful tasks
- [ ] Grafana/Prometheus monitoring integration
- [ ] API reference documentation (auto-generated)

### v2.0 (Future)

- [ ] Distributed architecture (multiple hosts)
- [ ] Horizontal scaling
- [ ] Advanced ML-based pattern learning
- [ ] Git integration (automatic commits)
- [ ] Multi-agent collaboration

---

**Project Status**: ✅ Production-ready (v1.1) - M8 complete, ready for real-world testing!

**Last Updated**: 2025-11-02
**Total Implementation Time**: ~58 hours (50h M0-M7 + 8h M8)
**Total Code**: ~15,600 lines (8,900 production + 4,700 tests + 2,000 docs)
**Test Coverage**: 88% overall (433+ tests, including 33 M8 local agent tests at 100% coverage)
