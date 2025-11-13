# Code Review Plan - Obra Project

**Review Date**: 2025-11-04
**Reviewer**: Claude Code
**Project**: Obra (Claude Code Orchestrator) v1.2+
**Codebase Size**: ~23,000 lines (54 production files, 61 test files)
**Test Coverage**: 88% overall, 695+ tests

---

## Codebase Overview

### Tech Stack
- **Language**: Python 3.x with type hints (required)
- **Database**: SQLAlchemy ORM (SQLite/PostgreSQL)
- **CLI**: Click framework
- **Testing**: pytest (695+ tests, 88% coverage)
- **LLM**: Ollama (Qwen 2.5 Coder 32B on RTX 5090)
- **Agent**: Claude Code CLI (isolated VM/WSL2)
- **Deployment**: Docker + docker-compose

### Architecture Layers

**M0 - Plugin System (Foundation)**:
- `src/plugins/` - AgentPlugin/LLMPlugin interfaces with decorator registration
- Abstract factory pattern + registry system
- Thread-safe decorator-based registration: `@register_agent`, `@register_llm`

**M1 - Core Infrastructure**:
- `src/core/` - StateManager (single source of truth), Config, models, exceptions
- StateManager: Atomic transactions, thread-safe (RLock), no direct DB access allowed
- SQLAlchemy models: Project, Task, Interaction, Checkpoint, SessionRecord
- Custom exception hierarchy with context and recovery suggestions

**M2 - LLM Integration**:
- `src/llm/` - Local LLM interface, validation, prompt generation
- ResponseValidator, QualityController, PromptGenerator
- PHASE_6: Structured prompts (hybrid JSON + natural language)
- Validation pipeline order: ResponseValidator → QualityController → ConfidenceScorer

**M2/M8 - Agent Implementations**:
- `src/agents/` - Claude Code local/SSH agents, output monitoring
- ClaudeCodeLocalAgent: subprocess with headless mode (`--print` flag)
- ClaudeCodeSSHAgent: remote SSH execution
- Per-iteration fresh sessions (eliminates lock conflicts)
- OutputMonitor: Streams and parses agent output

**M3 - File Monitoring**:
- `src/monitoring/` - FileWatcher for change detection
- Watchdog-based filesystem monitoring with event batching
- Thread cleanup requirements (WSL2 constraints)

**M4 - Orchestration Engine**:
- `src/orchestration/` - Scheduler, DecisionEngine, QualityController
- TaskScheduler: Priority-based with dependency resolution (PHASE_3)
- DecisionEngine: PROCEED/ESCALATE/CLARIFY/RETRY decisions
- BreakpointManager: Human intervention points
- Interactive commands (Phase 1-2): 8 commands, 6 checkpoints

**M5 - Utilities**:
- `src/utils/` - Token counting, context management, confidence scoring
- M9: RetryManager (exponential backoff), GitManager (auto-commits)
- Interactive: CommandProcessor, InputManager (non-blocking input)

**M6 - Integration**:
- `src/orchestrator.py` - Main integration loop (8 steps)
- `src/cli.py` - Click-based CLI commands
- `src/interactive.py` - REPL interface

**M7 - Testing**:
- `tests/` - 695+ comprehensive tests
- `tests/conftest.py` - Shared fixtures (test_config, fast_time)
- WSL2 resource limits: max 0.5s sleep, max 5 threads, max 20KB memory per test

### Critical Paths

1. **StateManager as Single Source of Truth**
   - ALL state access goes through StateManager
   - NO direct database access allowed
   - Atomic transactions, thread-safe with RLock
   - Rollback capability via checkpoints

2. **Validation Pipeline Order (STRICT)**
   - ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine
   - MUST NOT reverse this order
   - Different failure modes at each stage

3. **Per-Iteration Session Management**
   - Fresh Claude session per orchestration iteration
   - Eliminates session lock conflicts (PHASE_4 fix)
   - Task-level metrics aggregation
   - No session reuse across iterations

4. **Interactive Command Injection**
   - 6 checkpoints in orchestration loop
   - 8 commands: /pause, /resume, /to-claude, /to-obra, /override-decision, /status, /help, /stop
   - Non-blocking input with prompt_toolkit
   - TaskStoppedException for graceful shutdown

### Current State

**Milestones Completed**: All M0-M9 complete
**Recent Enhancements**:
- PHASE_3: Task Scheduler with dependency resolution
- PHASE_4: 6 critical bugs fixed (session management)
- PHASE_6: LLM-First Prompt Engineering (35.2% token efficiency improvement)
- Interactive Streaming Phase 1-2: Command injection (100/100 tests passing)

**Production Validation**:
- 16 critical bugs found and fixed through real-world testing
- 88% unit test coverage did NOT catch integration bugs
- Real orchestration testing revealed all 6 PHASE_4 bugs

---

## Risk Assessment

### High-Risk Areas (Obra-Specific)

#### ⚠️ CRITICAL: StateManager Integrity
**Risk Level**: CRITICAL
**Why**: Entire architecture depends on StateManager as single source of truth
**Check For**:
- Direct database access bypassing StateManager
- Missing StateManager calls for state reads/writes
- Improper transaction handling (not using atomic operations)
- Thread safety violations (missing locks)

#### ⚠️ CRITICAL: Plugin Registration Thread Safety
**Risk Level**: HIGH
**Why**: Decorator-based registration must be thread-safe
**Check For**:
- Race conditions in registry access
- Improper locking in AgentRegistry/LLMRegistry
- Plugin registration during multi-threaded execution

#### ⚠️ CRITICAL: Validation Pipeline Order
**Risk Level**: CRITICAL
**Why**: Reversing order leads to incorrect quality assessment
**Check For**:
- Code calling QualityController before ResponseValidator
- ConfidenceScorer called before validation
- DecisionEngine receiving unvalidated responses

#### ⚠️ CRITICAL: Thread Safety
**Risk Level**: HIGH
**Why**: StateManager, Registry, FileWatcher require proper locking
**Check For**:
- Missing RLock usage in StateManager operations
- Concurrent access without synchronization
- Deadlock potential in nested locks
- Race conditions in shared state

#### ⚠️ CRITICAL: Session Management
**Risk Level**: HIGH
**Why**: Per-iteration sessions critical for reliability (PHASE_4 fix)
**Check For**:
- Session reuse across iterations
- Missing session cleanup in finally blocks
- Incorrect session_id assignment
- Lock conflicts from stale sessions

#### ⚠️ CRITICAL: Agent Communication
**Risk Level**: HIGH
**Why**: Subprocess management critical for execution
**Check For**:
- Missing error handling in subprocess calls
- Improper output parsing
- Zombie processes from incomplete cleanup
- Timeout handling issues

#### ⚠️ CRITICAL: Test Resource Limits (WSL2)
**Risk Level**: CRITICAL
**Why**: Violations cause WSL2 crashes
**Check For**:
- `time.sleep()` > 0.5s per test
- Thread count > 5 per test
- Missing `timeout=` on thread.join()
- Memory allocations > 20KB per test
- Missing `@pytest.mark.slow` on heavy tests

#### ⚠️ HIGH: Interactive Command Processing
**Risk Level**: MEDIUM
**Why**: Command injection points need proper synchronization
**Check For**:
- Race conditions in InputManager
- Missing checkpoint integration
- TaskStoppedException not properly handled
- Command parsing vulnerabilities

#### ⚠️ HIGH: Configuration Loading
**Risk Level**: MEDIUM
**Why**: Common pitfall #8 - Config() vs Config.load()
**Check For**:
- Direct Config() instantiation (should use Config.load())
- Missing profile inheritance
- Hardcoded configuration values

#### ⚠️ HIGH: Git Operations
**Risk Level**: MEDIUM
**Why**: SSH authentication, auto-commit logic, branch management
**Check For**:
- Hardcoded SSH keys or credentials
- Missing error handling in git commands
- Branch conflicts from improper management
- Unsafe git operations (force push to main)

### Security-Sensitive Components

#### Command Injection Vulnerabilities
- Agent execution (subprocess with dangerous mode flag)
- Git operations (shell command construction)
- File system operations (path validation)

#### LLM Prompt Injection
- Structured prompts with validation (PHASE_6)
- User input sanitization
- Response parsing safety

#### Secrets Management
- API keys in configuration (should not be hardcoded)
- SSH keys for git operations
- Database credentials
- Log sanitization (no secrets in logs)

#### Subprocess Security
- `shell=True` usage (should ALWAYS be False)
- Command argument escaping
- Environment variable injection

#### File System Access
- FileWatcher path validation
- Git operations (proper path checking)
- Arbitrary file read/write prevention

#### Configuration Parsing
- YAML injection risks
- Profile loading validation
- Untrusted configuration sources

### Complex Business Logic

#### DecisionEngine
- Decision logic: PROCEED/RETRY/CLARIFY/ESCALATE
- Confidence threshold calculations
- Breakpoint trigger conditions
- Multi-factor decision making

#### DependencyResolver (M9)
- Topological sort implementation
- Cycle detection algorithm
- Cascading failure handling
- Dependency graph validation

#### RetryManager (M9)
- Exponential backoff with jitter
- Retryable vs non-retryable error classification
- Max retry limits
- Backoff calculation correctness

#### StructuredPromptBuilder (PHASE_6)
- Hybrid prompt generation (JSON + natural language)
- Schema validation
- Rule engine integration
- Template rendering

#### ConfidenceScorer
- Ensemble scoring (heuristic + LLM)
- Calibration tracking
- Multi-factor confidence assessment
- Threshold determination

### Known Issues (Fixed in PHASE_4)

✅ **Session lock conflicts** - Fixed via per-iteration sessions
✅ **Context window tracking** - Fixed with per-session token counts
✅ **Metrics race conditions** - Fixed with task-level aggregation
✅ **Stale session state** - Eliminated via fresh sessions
✅ **Error recovery** - Automatic cleanup with fresh sessions
✅ **Configuration inheritance** - Fixed profile loading logic

⚠️ **PTY compatibility** - Abandoned (Claude Code has known issues, using subprocess.run() directly)

---

## Review Chunks (Priority Order)

### Chunk 1: Core Infrastructure - Plugin System (M0)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/plugins/base.py
src/plugins/registry.py
src/plugins/exceptions.py
src/plugins/__init__.py
```

**Focus Areas**:
- Thread-safe registration with decorators (@register_agent, @register_llm)
- Abstract base classes (AgentPlugin, LLMPlugin) interface contracts
- Registry singleton pattern and thread safety
- Plugin lifecycle management
- Error handling in registration

**Estimated Complexity**: MEDIUM
**Priority**: CRITICAL
**Rationale**: Foundation for entire plugin system, thread safety critical

---

### Chunk 2: Core Infrastructure - State Management (M1)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/core/state.py         (~2,000+ lines, single source of truth)
src/core/models.py        (SQLAlchemy models)
```

**Focus Areas**:
- **CRITICAL**: No direct database access - ALL goes through StateManager
- Atomic transactions and rollback capability
- Thread safety with RLock
- Task-level metrics aggregation (PHASE_4 fix)
- Session management integration
- Checkpoint creation and rollback
- State consistency across concurrent operations

**Estimated Complexity**: HIGH
**Priority**: CRITICAL
**Rationale**: Most critical component, single source of truth, common pitfall #1

---

### Chunk 3: Core Infrastructure - Configuration & Exceptions (M1)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/core/config.py
src/core/exceptions.py
```

**Focus Areas**:
- Config.load() usage (NEVER Config() directly - pitfall #8)
- Profile inheritance logic (M9)
- Configuration validation
- Exception hierarchy with context and recovery
- Custom exception handling patterns

**Estimated Complexity**: LOW
**Priority**: HIGH
**Rationale**: Common pitfall (#8), M9 profile system critical for usability

---

### Chunk 4: LLM Integration - Validation Pipeline (M2)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/llm/response_validator.py
src/orchestration/quality_controller.py
src/utils/confidence_scorer.py
```

**Focus Areas**:
- **CRITICAL**: Validation order: ResponseValidator → QualityController → ConfidenceScorer
- NEVER reverse this order (pitfall #2)
- Interface consistency (send_prompt method - PHASE_4 BUG-003)
- Ensemble scoring in ConfidenceScorer
- Error propagation through pipeline
- Quality scoring with LLM integration

**Estimated Complexity**: HIGH
**Priority**: CRITICAL
**Rationale**: Strict ordering requirement, integration bug found in PHASE_4

---

### Chunk 5: LLM Integration - Structured Prompts (PHASE_6)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/llm/structured_prompt_builder.py
src/llm/structured_response_parser.py
src/llm/prompt_rule_engine.py
src/llm/code_validators.py
src/llm/prompt_rule.py
src/llm/rule_validation_result.py
```

**Focus Areas**:
- Hybrid prompt generation (JSON metadata + natural language)
- Schema validation and rule engine
- Response parsing robustness (100% parsing success rate target)
- LLM prompt injection prevention
- Template rendering safety
- Performance (35.2% token efficiency improvement)

**Estimated Complexity**: HIGH
**Priority**: HIGH
**Rationale**: Recent enhancement (PHASE_6), validated performance gains, security concerns

---

### Chunk 6: Agent Implementations (M2/M8)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/agents/claude_code_local.py
src/agents/claude_code_ssh.py
src/agents/output_monitor.py
src/agents/mock_agent.py
```

**Focus Areas**:
- Subprocess management in ClaudeCodeLocalAgent (headless mode)
- Per-iteration session implementation (PHASE_4 fix - pitfall #17)
- Session ID handling (PHASE_4 BUG-005)
- Output parsing and completion detection
- Dangerous mode flag usage (security concern)
- Error handling and process cleanup
- SSH authentication in ClaudeCodeSSHAgent
- OutputMonitor thread safety

**Estimated Complexity**: HIGH
**Priority**: CRITICAL
**Rationale**: Core execution, PHASE_4 bugs found here, subprocess security

---

### Chunk 7: Orchestration Engine - Core (M4)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/orchestration/decision_engine.py
src/orchestration/quality_controller.py (if not already reviewed in Chunk 4)
src/orchestration/breakpoint_manager.py
```

**Focus Areas**:
- DecisionEngine logic: PROCEED/RETRY/CLARIFY/ESCALATE
- Validation result type handling (PHASE_4 BUG-004)
- Confidence threshold calculations
- Breakpoint trigger conditions
- Quality control integration with LLM
- Multi-factor decision making

**Estimated Complexity**: HIGH
**Priority**: CRITICAL
**Rationale**: Core decision logic, PHASE_4 bug found (type mismatch)

---

### Chunk 8: Orchestration Engine - Interactive Commands (Phase 1-2)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/utils/command_processor.py     (376 lines)
src/utils/input_manager.py          (176 lines)
src/utils/streaming_handler.py
```

**Focus Areas**:
- Command parsing and execution (8 commands)
- Non-blocking input with prompt_toolkit
- Checkpoint integration (6 locations)
- TaskStoppedException handling
- Race conditions in InputManager
- Command injection security
- Graceful shutdown logic

**Estimated Complexity**: MEDIUM
**Priority**: HIGH
**Rationale**: Recent implementation (Phase 1-2), concurrency concerns, security

---

### Chunk 9: Orchestration Engine - Scheduling (PHASE_3)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/orchestration/task_scheduler.py
src/orchestration/dependency_resolver.py
src/orchestration/complexity_estimator.py
src/orchestration/max_turns_calculator.py
```

**Focus Areas**:
- Topological sort implementation in DependencyResolver
- Cycle detection algorithm
- Priority-based task selection
- Dependency graph validation
- Cascading failure handling
- Complexity estimation accuracy

**Estimated Complexity**: HIGH
**Priority**: MEDIUM
**Rationale**: Complex graph algorithms, M9 enhancement, tested but should verify

---

### Chunk 10: Utilities - Retry & Git (M9)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/utils/retry_manager.py
src/utils/git_manager.py
```

**Focus Areas**:
- Exponential backoff with jitter implementation
- Retryable vs non-retryable error classification
- Max retry limits and backoff calculation
- SSH authentication for git operations
- Auto-commit logic and message generation
- Branch management (obra/task-{id}-{slug})
- PR creation integration (gh CLI)
- Security: no hardcoded SSH keys, safe git commands

**Estimated Complexity**: MEDIUM
**Priority**: HIGH
**Rationale**: M9 core features, SSH security concerns, auto-commit safety

---

### Chunk 11: Utilities - Context & Token Management (M5)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/utils/context_manager.py
src/utils/token_counter.py
src/utils/json_extractor.py
```

**Focus Areas**:
- Context window tracking (per-session token counts - PHASE_4 fix)
- Token counting accuracy (model-specific encoders)
- Context building and prioritization
- Summarization logic
- Refresh thresholds (70% warning, 80% refresh, 95% critical)
- LRU caching implementation

**Estimated Complexity**: MEDIUM
**Priority**: MEDIUM
**Rationale**: PHASE_4 fix applied, performance-critical, context management

---

### Chunk 12: File Monitoring (M3)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/monitoring/file_watcher.py
src/monitoring/event_detector.py
```

**Focus Areas**:
- Thread cleanup (WSL2 constraints - pitfall #5)
- Event batching and debouncing
- Resource management (file handles)
- Watchdog integration safety
- Change tracking accuracy
- Background thread lifecycle

**Estimated Complexity**: MEDIUM
**Priority**: MEDIUM
**Rationale**: Thread safety critical for WSL2, background threads need cleanup

---

### Chunk 13: CLI & Integration (M6)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
src/cli.py
src/orchestrator.py        (~1,000+ lines, main integration loop)
src/interactive.py
```

**Focus Areas**:
- Orchestrator 8-step execution loop
- Interactive checkpoint integration (6 locations)
- Per-iteration session implementation (PHASE_4 fixes)
- CLI command parsing and profile loading
- Error handling and recovery
- Session lifecycle management
- Integration of all M0-M5 components

**Estimated Complexity**: HIGH
**Priority**: CRITICAL
**Rationale**: Main integration point, PHASE_4 fixes applied, complex orchestration logic

---

### Chunk 14: Testing Infrastructure (M7)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
tests/conftest.py
tests/test_*.py (61 files, 695+ tests)
```

**Focus Areas**:
- **CRITICAL**: WSL2 resource limit compliance (pitfall #7)
  - Max 0.5s sleep per test
  - Max 5 threads per test with mandatory timeout=
  - Max 20KB memory allocation per test
  - @pytest.mark.slow on heavy tests
- Shared fixtures (test_config, fast_time) usage
- Thread cleanup in fixtures
- Mock usage (proper mocking of Ollama, Claude Code)
- Test quality (assertions, edge cases, error paths)
- Coverage of critical paths (StateManager, validation pipeline, DecisionEngine)

**Estimated Complexity**: HIGH
**Priority**: CRITICAL
**Rationale**: WSL2 crash prevention critical, test quality validates entire system

---

### Chunk 15: Configuration & Profiles (M9)
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
config/default_config.yaml
config/profiles/python_project.yaml
config/profiles/web_app.yaml
config/profiles/ml_project.yaml
config/profiles/microservice.yaml
config/profiles/minimal.yaml
config/profiles/production.yaml
config/prompt_rules.yaml
config/response_schemas.yaml
config/hybrid_prompt_templates.yaml
```

**Focus Areas**:
- Profile inheritance from default config
- Validation rules for prompts (PHASE_6)
- Response schemas accuracy
- Prompt templates safety (no injection vulnerabilities)
- Configuration completeness for each profile
- No hardcoded secrets in configs

**Estimated Complexity**: LOW
**Priority**: MEDIUM
**Rationale**: M9 feature, user-facing, configuration correctness important

---

### Chunk 16: Documentation & Deployment
**Status**: [ ] Not Started | [ ] In Progress | [ ] Complete

**Files**:
```
docs/architecture/ARCHITECTURE.md
docs/development/TEST_GUIDELINES.md
docs/decisions/ADR-*.md (11 ADRs)
CLAUDE.md
README.md
CHANGELOG.md
Dockerfile
docker-compose.yml
setup.sh
requirements.txt
```

**Focus Areas**:
- Documentation accuracy (vs actual code implementation)
- CLAUDE.md reflects current architecture (updated Nov 4)
- TEST_GUIDELINES.md compliance in tests
- ADRs document actual decisions made
- CHANGELOG.md completeness (version history)
- Docker deployment readiness
- setup.sh automation correctness
- requirements.txt completeness (all dependencies listed)

**Estimated Complexity**: LOW
**Priority**: LOW
**Rationale**: Documentation review, validate accuracy, deployment verification

---

## Review Criteria Reference

### Correctness & Reliability
- Logic errors, edge cases, race conditions
- Error handling with custom exceptions (context + recovery)
- State management consistency (all through StateManager)
- None/Optional handling (proper type hints required)
- Validation pipeline order (ResponseValidator → QualityController → ConfidenceScorer)
- Per-iteration session management (no session reuse - pitfall #17)
- Thread safety with proper locking (RLock for StateManager/Registry)

### Security
- Command injection in subprocess calls (agent execution, git operations)
- SQL injection via SQLAlchemy (should use parameterized queries)
- LLM prompt injection (structured prompts with validation)
- Secrets management (API keys, SSH keys in config - should not be hardcoded)
- File system access (FileWatcher, git operations - proper path validation)
- Agent dangerous mode (--dangerously-skip-permissions flag usage)
- Configuration file parsing (YAML injection risks)
- Subprocess shell=True usage (should ALWAYS be False)
- Log sanitization (no secrets in logs)

### Code Quality & Maintainability
- **Type hints required** - All functions must have type hints (return type + parameters)
- **Docstrings required** - Google style docstrings for all public functions/classes
- Code clarity and readability (PEP 8 compliance)
- DRY violations and code duplication
- Function/class complexity (too long, too many responsibilities)
- Magic numbers and hardcoded values (should be in config)
- Inconsistent naming or patterns
- Dead code and unused imports
- TODO/FIXME/HACK stubs needing completion
- Config.load() usage (NEVER use Config() directly - pitfall #8)
- StateManager bypass checks (NEVER access database directly - pitfall #1)
- Proper exception hierarchy (use custom exceptions from src/core/exceptions.py)

### Architecture & Design
- **Plugin system integrity** - Decorator-based registration (@register_agent, @register_llm)
- **StateManager as single source of truth** - No direct database access (pitfall #1)
- **Validation pipeline order** - Must maintain sequence (never reverse - pitfall #2)
- Separation of concerns (plugins, core, orchestration, utils)
- Tight coupling or circular dependencies
- Design patterns used appropriately (Factory for plugins, Strategy for agents)
- Scalability considerations (thread safety, resource limits)
- Configuration-driven design (load from config, not hardcode)
- Per-iteration session model (fresh session each iteration - pitfall #17)
- Interactive checkpoint integration (6 locations in orchestration loop)

### Testing
- **Test coverage targets** - Overall ≥88%, Critical modules ≥90%
- **WSL2 resource limits (CRITICAL)** (pitfall #7):
  - Max 0.5s sleep per test (use fast_time fixture for longer)
  - Max 5 threads per test with mandatory timeout= on join()
  - Max 20KB memory allocation per test
  - Mark heavy tests with @pytest.mark.slow
- **Shared fixtures usage** - Use test_config, fast_time from conftest.py
- **Thread cleanup** - All background threads must be properly cleaned up
- Test quality (assertions, edge cases, error paths)
- Missing tests for critical paths (StateManager, validation pipeline, DecisionEngine)
- Flaky or brittle tests (timing issues, race conditions)
- Mock usage (proper mocking of external dependencies: Ollama, Claude Code)
- Integration tests (695+ tests total, comprehensive coverage)

### Performance
- N+1 queries and inefficient database access (SQLAlchemy query optimization)
- Unnecessary computations (especially in validation pipeline)
- Memory leaks or resource cleanup (thread cleanup, file handles)
- Token counting efficiency (PHASE_6: 35.2% improvement validated)
- Context window management (per-session tracking, refresh thresholds)
- Retry backoff efficiency (exponential with jitter)
- Large payloads or unoptimized queries
- LLM call optimization (batch when possible, structured prompts)
- Subprocess overhead (per-iteration sessions vs persistent)

### Documentation
- README.md completeness (project overview, current status)
- CLAUDE.md accuracy (architecture principles, development guide)
- CHANGELOG.md maintenance (version history, breaking changes)
- ADRs (Architecture Decision Records) in docs/decisions/
- API documentation (docstrings, type hints)
- Inline comments for complex logic (especially validation pipeline, DecisionEngine)
- Missing or outdated documentation (especially after PHASE_6, Interactive Streaming)
- Test documentation (TEST_GUIDELINES.md compliance)
- User guides (QUICK_START.md, session management, configuration profiles)

### DevOps & Operations
- Logging quality (levels, no sensitive data in logs)
- Monitoring and observability (metrics, task tracking)
- Error tracking setup (exception context, recovery suggestions)
- Environment configuration (Windows 11 + Hyper-V + WSL2, Ollama on host)
- Deployment considerations (Docker, docker-compose, automated setup.sh)
- SSH authentication for git operations (no HTTPS password prompts)
- Runtime directory isolation (OBRA_RUNTIME_DIR environment variable)

---

## Review Success Criteria

- [ ] All 16 chunks reviewed
- [ ] StateManager bypass checks passed (no direct DB access - pitfall #1)
- [ ] Validation pipeline order verified (ResponseValidator → QualityController → ConfidenceScorer - pitfall #2)
- [ ] WSL2 test compliance verified (TEST_GUIDELINES.md - pitfall #7)
- [ ] Type hints and docstrings completeness checked
- [ ] Configuration loading compliance (Config.load() usage - pitfall #8)
- [ ] Session management compliance (per-iteration sessions - pitfall #17)
- [ ] Thread safety verified (proper locking)
- [ ] Security vulnerabilities identified (command injection, secrets)
- [ ] Documentation accuracy validated (CLAUDE.md, ARCHITECTURE.md, ADRs)

---

## Estimated Effort

**Total Chunks**: 16
**Estimated Sessions**: 8-10 sessions (2 chunks per session average)
**Time per Chunk**: 30-60 minutes depending on complexity
**Total Estimated Time**: 12-20 hours

**Complexity Breakdown**:
- **CRITICAL** (6 chunks): Chunks 1, 2, 4, 6, 7, 13 - ~8-10 hours
- **HIGH** (5 chunks): Chunks 3, 5, 8, 10, 14 - ~4-6 hours
- **MEDIUM** (4 chunks): Chunks 9, 11, 12, 15 - ~2-3 hours
- **LOW** (1 chunk): Chunk 16 - ~1 hour

---

## Common Pitfalls to Watch For

Based on CLAUDE.md "Common Pitfalls to Avoid" (21 documented):

1. ❌ **StateManager bypass** - Direct database access (pitfall #1)
2. ❌ **Validation order reversal** - Wrong pipeline sequence (pitfall #2)
3. ❌ **Hardcoded agents** - Not using plugin system (pitfall #3)
4. ❌ **Test resource limit violations** - WSL2 crashes (pitfall #7)
5. ❌ **Config() direct usage** - Should use Config.load() (pitfall #8)
6. ❌ **Wrong model attributes** - Use project_name not name (pitfall #10)
7. ❌ **Circular dependencies** - DependencyResolver will reject (pitfall #14)
8. ❌ **Session reuse** - Use fresh session per iteration (pitfall #17)
9. ❌ **Session-level metrics** - Use task-level aggregation (pitfall #18)
10. ❌ **Documentation in wrong locations** - Use docs/ subdirectories (pitfall #16)

---

**Review Plan Created**: 2025-11-04
**Next Step**: Begin Chunk 1 (Plugin System) review
