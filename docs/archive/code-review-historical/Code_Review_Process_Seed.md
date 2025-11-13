# Obra Code Review Process

This document defines the code review process specifically tailored for the **Obra (Claude Code Orchestrator)** project - an intelligent supervision system for semi-autonomous software development.

## Project Context

**Tech Stack:**
- Python 3.x with type hints (required)
- SQLAlchemy ORM (SQLite/PostgreSQL)
- Click CLI framework
- pytest (695+ tests, 88% coverage target)
- Ollama (local LLM - Qwen 2.5 Coder on RTX 5090)
- Claude Code CLI (agent in isolated VM/WSL2)

**Architecture:** Plugin-based system with StateManager as single source of truth, comprehensive validation pipeline, and per-iteration session management.

**Project Status:** Real-World Validation & Refinement (v1.2+) - All M0-M9 milestones complete, Interactive Streaming Phase 1-2 complete, 16 critical bugs fixed through production testing.

This review will span multiple sessions with persistent documentation to track progress.

## Setup Phase: Create Review Infrastructure

First, create these files to track our review:

1. **`REVIEW_PLAN.md`** - The master review plan (checklist format)
2. **`REVIEW_FINDINGS.md`** - Documented issues as we find them
3. **`REVIEW_PROGRESS.md`** - Session log and current status

## Phase 1: Discovery & Planning

Explore the codebase and create a comprehensive review plan. Document your findings in `REVIEW_PLAN.md` with this structure:

### Codebase Overview
- **Tech Stack:** Python 3.x, SQLAlchemy, Click, pytest, Ollama, Claude Code
- **Architecture Layers:**
  - Plugins (M0): AgentPlugin/LLMPlugin interfaces with decorator registration
  - Core (M1): StateManager, Config, models, exceptions
  - LLM (M2): Local LLM interface, validation, structured prompts (PHASE_6)
  - Agents (M2/M8): Claude Code implementations (local/SSH), output monitoring
  - Monitoring (M3): FileWatcher for change detection
  - Orchestration (M4): Scheduler, DecisionEngine, QualityController, interactive commands
  - Utils (M5): Token counting, context management, retry logic (M9), git integration (M9)
  - Integration (M6): CLI, orchestrator loop with 6 interactive checkpoints
- **Critical Paths:**
  - StateManager (single source of truth - NEVER bypass)
  - Validation pipeline order: ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine
  - Per-iteration session management (fresh Claude session each iteration)
  - Interactive command injection (8 commands, 6 checkpoint locations)
- **Current State:**
  - 695+ tests (88% coverage achieved)
  - ~23,000 lines of code (production + tests + docs)
  - All M0-M9 milestones complete
  - PHASE_6 validated: 35.2% token efficiency improvement
  - 16 critical bugs fixed through real-world testing

### Risk Assessment

**High-Risk Areas (Obra-Specific):**
- [ ] **StateManager integrity** - All state access must go through StateManager (no direct DB access)
- [ ] **Plugin registration system** - Decorator-based registration must be thread-safe
- [ ] **Validation pipeline order** - Must maintain ResponseValidator → QualityController → ConfidenceScorer sequence
- [ ] **Thread safety** - StateManager, Registry, FileWatcher with proper locking (RLock)
- [ ] **Session management** - Per-iteration sessions, no session reuse (critical for reliability)
- [ ] **Agent communication** - Subprocess management, output parsing, error handling
- [ ] **Test resource limits** - WSL2 crash prevention (max 0.5s sleep, 5 threads, 20KB memory per test)
- [ ] **Interactive command processing** - Command injection points, race conditions in InputManager
- [ ] **Configuration loading** - Must use Config.load(), not Config() directly
- [ ] **Git operations** - SSH authentication, auto-commit logic, branch management

**Security-Sensitive Components:**
- [ ] Agent execution (subprocess with dangerous mode flag)
- [ ] LLM prompt injection (structured prompts with validation)
- [ ] File system operations (FileWatcher, git integration)
- [ ] Configuration secrets (API keys, SSH keys)
- [ ] Command injection vulnerabilities (subprocess calls)

**Complex Business Logic:**
- [ ] DecisionEngine logic (proceed/retry/clarify/escalate)
- [ ] DependencyResolver topological sort and cycle detection
- [ ] RetryManager exponential backoff with jitter
- [ ] StructuredPromptBuilder hybrid prompt generation
- [ ] ConfidenceScorer ensemble scoring (heuristic + LLM)

**Areas with Known Issues:**
- [ ] Session lock conflicts (fixed in PHASE_4 via per-iteration sessions)
- [ ] Context window tracking (fixed - per-session token counts)
- [ ] Metrics race conditions (fixed - task-level aggregation)
- [ ] PTY compatibility (abandoned - using subprocess.run() directly)

### Review Chunks (in priority order)

For each chunk, use this format:
Chunk N: [Name] - [ ] Not Started | [ ] In Progress | [ ] Complete
Files:

path/to/file1.ts
path/to/file2.ts

Focus Areas:

Specific concerns for this chunk

Estimated Complexity: Low | Medium | High
Priority: Critical | High | Medium | Low

**Obra-Specific Review Chunks (Priority Order):**

1. **Core Infrastructure - Plugin System (M0)**
   - `src/plugins/agent_plugin.py`
   - `src/plugins/llm_plugin.py`
   - `src/plugins/registry.py`
   - Focus: Thread-safe registration, interface contracts, decorator patterns

2. **Core Infrastructure - State Management (M1)**
   - `src/core/state_manager.py`
   - `src/core/database.py`
   - `src/core/models.py`
   - Focus: Single source of truth, atomic transactions, thread safety, no bypass

3. **Core Infrastructure - Configuration & Exceptions (M1)**
   - `src/core/config.py`
   - `src/core/exceptions.py`
   - Focus: Config.load() usage, profile inheritance, exception context

4. **LLM Integration - Validation Pipeline (M2)**
   - `src/llm/response_validator.py`
   - `src/llm/quality_controller.py`
   - `src/utils/confidence_scorer.py`
   - Focus: Validation order, ensemble scoring, error propagation

5. **LLM Integration - Structured Prompts (PHASE_6)**
   - `src/llm/structured_prompt_builder.py`
   - `src/llm/structured_response_parser.py`
   - `src/llm/prompt_rule_engine.py`
   - Focus: Hybrid prompt generation, schema validation, parsing robustness

6. **Agent Implementations (M2/M8)**
   - `src/agents/claude_code_local.py`
   - `src/agents/claude_code_ssh.py`
   - `src/agents/output_monitor.py`
   - Focus: Subprocess management, output parsing, headless mode, per-iteration sessions

7. **Orchestration Engine - Core (M4)**
   - `src/orchestration/decision_engine.py`
   - `src/orchestration/orchestrator_loop.py`
   - `src/orchestration/quality_control.py`
   - Focus: Decision logic, validation order, breakpoint triggers

8. **Orchestration Engine - Interactive Commands (Phase 1-2)**
   - `src/orchestration/command_processor.py`
   - `src/orchestration/input_manager.py`
   - Focus: Command parsing, non-blocking input, checkpoint integration, TaskStoppedException

9. **Orchestration Engine - Scheduling (PHASE_3)**
   - `src/orchestration/task_scheduler.py`
   - `src/orchestration/dependency_resolver.py`
   - Focus: Topological sort, cycle detection, dependency tracking

10. **Utilities - Retry & Git (M9)**
    - `src/utils/retry_manager.py`
    - `src/utils/git_manager.py`
    - Focus: Exponential backoff, jitter, retryable error classification, SSH auth, auto-commits

11. **Utilities - Context & Token Management (M5)**
    - `src/utils/context_manager.py`
    - `src/utils/token_counter.py`
    - Focus: Context window tracking, per-session token counts, refresh thresholds

12. **File Monitoring (M3)**
    - `src/monitoring/file_watcher.py`
    - Focus: Thread cleanup, event handling, resource management

13. **CLI & Integration (M6)**
    - `src/cli.py`
    - `src/orchestrator.py`
    - `src/interactive.py`
    - Focus: Command parsing, profile loading, orchestration loop with checkpoints

14. **Testing Infrastructure (M7)**
    - `tests/conftest.py`
    - `tests/test_*.py` (695+ tests)
    - Focus: Shared fixtures, test resource limits, WSL2 crash prevention, fast_time usage

15. **Configuration & Profiles (M9)**
    - `config/default_config.yaml`
    - `config/profiles/*.yaml`
    - `config/prompt_rules.yaml`
    - Focus: Profile inheritance, validation rules, response schemas

16. **Documentation & Deployment**
    - `docs/` structure
    - `Dockerfile`, `docker-compose.yml`
    - `setup.sh`, `requirements.txt`
    - Focus: Documentation accuracy, deployment readiness

### Review Criteria Reference

Evaluate each chunk against these criteria (Obra-customized):

**Correctness & Reliability**
- Logic errors, edge cases, race conditions
- Error handling with custom exceptions (context + recovery)
- State management consistency (all through StateManager)
- None/Optional handling (proper type hints required)
- Validation pipeline order (ResponseValidator → QualityController → ConfidenceScorer)
- Per-iteration session management (no session reuse)
- Thread safety with proper locking (RLock for StateManager/Registry)

**Security**
- Command injection in subprocess calls (agent execution, git operations)
- SQL injection via SQLAlchemy (should use parameterized queries)
- LLM prompt injection (structured prompts with validation)
- Secrets management (API keys, SSH keys in config - should not be hardcoded)
- File system access (FileWatcher, git operations - proper path validation)
- Agent dangerous mode (--dangerously-skip-permissions flag usage)
- Configuration file parsing (YAML injection risks)
- Subprocess shell=True usage (should always be False)
- Log sanitization (no secrets in logs)

**Code Quality & Maintainability (Python-Specific)**
- **Type hints required** - All functions must have type hints (return type + parameters)
- **Docstrings required** - Google style docstrings for all public functions/classes
- Code clarity and readability (PEP 8 compliance)
- DRY violations and code duplication
- Function/class complexity (too long, too many responsibilities)
- Magic numbers and hardcoded values (should be in config)
- Inconsistent naming or patterns
- Dead code and unused imports
- TODO/FIXME/HACK stubs needing completion
- Config.load() usage (NEVER use Config() directly)
- StateManager bypass checks (NEVER access database directly)
- Proper exception hierarchy (use custom exceptions from src/core/exceptions.py)

**Architecture & Design (Obra-Specific)**
- **Plugin system integrity** - Decorator-based registration (@register_agent, @register_llm)
- **StateManager as single source of truth** - No direct database access
- **Validation pipeline order** - Must maintain sequence (never reverse)
- Separation of concerns (plugins, core, orchestration, utils)
- Tight coupling or circular dependencies
- Design patterns used appropriately (Factory for plugins, Strategy for agents)
- Scalability considerations (thread safety, resource limits)
- Configuration-driven design (load from config, not hardcode)
- Per-iteration session model (fresh session each iteration)
- Interactive checkpoint integration (6 locations in orchestration loop)

**Testing (⚠️ CRITICAL - WSL2 Crash Prevention)**
- **Test coverage targets** - Overall ≥88%, Critical modules ≥90%
- **WSL2 resource limits (CRITICAL)**:
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

**Performance**
- N+1 queries and inefficient database access (SQLAlchemy query optimization)
- Unnecessary computations (especially in validation pipeline)
- Memory leaks or resource cleanup (thread cleanup, file handles)
- Token counting efficiency (PHASE_6: 35.2% improvement validated)
- Context window management (per-session tracking, refresh thresholds)
- Retry backoff efficiency (exponential with jitter)
- Large payloads or unoptimized queries
- LLM call optimization (batch when possible, structured prompts)
- Subprocess overhead (per-iteration sessions vs persistent)

**Documentation**
- README.md completeness (project overview, current status)
- CLAUDE.md accuracy (architecture principles, development guide)
- CHANGELOG.md maintenance (version history, breaking changes)
- ADRs (Architecture Decision Records) in docs/decisions/
- API documentation (docstrings, type hints)
- Inline comments for complex logic (especially validation pipeline, DecisionEngine)
- Missing or outdated documentation (especially after PHASE_6, Interactive Streaming)
- Test documentation (TEST_GUIDELINES.md compliance)
- User guides (QUICK_START.md, session management, configuration profiles)

**DevOps & Operations**
- Logging quality (levels, no sensitive data in logs)
- Monitoring and observability (metrics, task tracking)
- Error tracking setup (exception context, recovery suggestions)
- Environment configuration (Windows 11 + Hyper-V + WSL2, Ollama on host)
- Deployment considerations (Docker, docker-compose, automated setup.sh)
- SSH authentication for git operations (no HTTPS password prompts)
- Runtime directory isolation (OBRA_RUNTIME_DIR environment variable)

---

## Phase 2: Findings Documentation Template

Create `REVIEW_FINDINGS.md` with this structure:
````markdown
# Code Review Findings

Last Updated: [Date]
Current Chunk: [Chunk Name]

## Summary Statistics
- Total Issues: 0
- Critical: 0 | High: 0 | Medium: 0 | Low: 0
- Bugs: 0 | Security: 0 | Quality: 0 | Performance: 0 | Testing: 0 | Docs: 0

## Critical Issues (Fix Immediately)
[Empty until we start finding issues]

## High Priority Issues
[Empty until we start finding issues]

## Medium Priority Issues
[Empty until we start finding issues]

## Low Priority Issues
[Empty until we start finding issues]

## Completed Fixes
[Issues we've already addressed]

---

## Issue Template (for reference)
**[SEVERITY] [CATEGORY] Issue Title**
- **Location:** `file.ts:123`
- **Description:** What's wrong and why it matters
- **Impact:** How this affects the system
- **Recommendation:** Specific fix
- **Status:** Open | In Progress | Fixed | Deferred
````

---

## Phase 3: Session Management Template

Create `REVIEW_PROGRESS.md`:
````markdown
# Code Review Progress Log

## Current Session
- **Date:** [Today's date]
- **Current Chunk:** Not started
- **Session Goal:** Complete discovery and planning

## Completed Chunks
[None yet]

## Session History
### Session 1 - [Date]
- Created review infrastructure
- Completed discovery and planning
- **Next:** Start Chunk 1

---

## How to Resume in a New Session

1. Read `REVIEW_PROGRESS.md` to see current status
2. Read `REVIEW_PLAN.md` to find next uncompleted chunk
3. Review any recent findings in `REVIEW_FINDINGS.md`
4. Continue with next chunk
5. Update all three documents as you go

## Quick Commands for Context Restoration
When starting a new session, run:
```bash
cat REVIEW_PROGRESS.md REVIEW_PLAN.md
```
This shows you exactly where we left off.
````

---

## Workflow for Each Review Chunk

When reviewing each chunk:

1. **Load context:** Read the chunk details from REVIEW_PLAN.md
2. **Review the code:** Analyze files against all criteria
3. **Document findings:** Add issues to REVIEW_FINDINGS.md with severity/category
4. **Update plan:** Mark chunk as complete in REVIEW_PLAN.md
5. **Update progress:** Log session work in REVIEW_PROGRESS.md
6. **Commit changes:** Git commit review docs + any fixes made

## Additional Best Practices (Obra-Specific)

- **Branch management:** Use `code-review-[date]` branch for fixes (SSH git operations, no password prompts)
- **Batch similar issues:** If you find repeated patterns, note them once with multiple locations
- **Quick wins:** Fix obvious issues immediately; document complex ones for discussion
- **False positives:** If I identify something that's actually correct, note it to avoid re-flagging
- **Reference CLAUDE.md:** Check "Common Pitfalls to Avoid" section for known issues
- **Reference phase reports:** See docs/development/phase-reports/ for historical bug fixes
- **WSL2 testing:** ALWAYS check TEST_GUIDELINES.md before writing tests (critical!)
- **StateManager compliance:** Verify no direct database access in reviewed code
- **Validation order:** Ensure ResponseValidator → QualityController → ConfidenceScorer sequence
- **Session management:** Verify per-iteration sessions (no session reuse)
- **Type hints:** All functions must have complete type hints
- **Docstrings:** All public functions/classes must have Google-style docstrings
- **Configuration:** Verify Config.load() usage (never Config() directly)
- **Known fixed bugs:** Check docs/development/phase-reports/PHASE4_SESSION_COMPLETE_SUMMARY.md for 6 critical bugs already fixed

---

## Start Here

Begin Phase 1: Explore the Obra codebase and create the three review documents (REVIEW_PLAN.md, REVIEW_FINDINGS.md, REVIEW_PROGRESS.md) with the discovery findings and proposed review strategy.

### Pre-Review Context Loading

Before starting discovery, read these essential documents:
1. **CLAUDE.md** - Architecture principles, common pitfalls (21 pitfalls documented!)
2. **docs/architecture/ARCHITECTURE.md** - Complete M0-M9 system architecture
3. **docs/development/TEST_GUIDELINES.md** - WSL2 crash prevention (CRITICAL!)
4. **docs/development/phase-reports/PHASE4_SESSION_COMPLETE_SUMMARY.md** - 6 critical bugs already fixed
5. **CHANGELOG.md** - Recent changes and version history

### What to Expect in Obra

**Strengths:**
- Comprehensive test coverage (695+ tests, 88%)
- Well-documented architecture (16 ADRs, detailed phase reports)
- Plugin-based design with clear interfaces
- Production-validated (16 critical bugs found and fixed)
- Performance-optimized (PHASE_6: 35.2% token efficiency improvement)

**Known Challenges:**
- Complex state management (StateManager must be respected)
- Thread safety requirements (proper locking patterns)
- WSL2 testing limitations (strict resource limits)
- Session management complexity (per-iteration model)
- Validation pipeline ordering (strict sequence required)

**Critical Areas for Review:**
- StateManager bypass checks (most common pitfall #1)
- Validation pipeline order violations (pitfall #2)
- Config() direct instantiation (pitfall #8)
- Test resource limit violations (pitfall #7)
- Thread cleanup issues (pitfall #5)

### After Creating Review Documents

Show me:
1. **Codebase summary** - Confirmed tech stack, architecture validation against CLAUDE.md
2. **Proposed review order** - 16 chunks with rationale (align with milestone structure M0-M9)
3. **Estimated effort** - Number of chunks, sessions, and approximate time per chunk
4. **High-priority concerns** - Any immediate red flags or architectural violations spotted
5. **Quick wins** - Low-hanging fruit that can be fixed immediately

Then we'll proceed chunk by chunk in subsequent sessions.

### Review Success Criteria

- [ ] All 16 chunks reviewed
- [ ] StateManager bypass checks passed (no direct DB access)
- [ ] Validation pipeline order verified
- [ ] WSL2 test compliance verified (TEST_GUIDELINES.md)
- [ ] Type hints and docstrings completeness checked
- [ ] Configuration loading compliance (Config.load() usage)
- [ ] Session management compliance (per-iteration sessions)
- [ ] Thread safety verified (proper locking)
- [ ] Security vulnerabilities identified (command injection, secrets)
- [ ] Documentation accuracy validated (CLAUDE.md, ARCHITECTURE.md, ADRs)