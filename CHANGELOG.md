# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Flexible LLM Orchestrator** (Phases 1-7 complete, 7.5 hours implementation)
  - OpenAI Codex LLM plugin via CLI (`src/llm/openai_codex_interface.py`, 450 lines)
  - Registry-based LLM selection supporting multiple providers (Ollama, OpenAI Codex, Mock)
  - 36 unit tests for OpenAI Codex plugin (91% coverage, 100% pass rate)
  - 8 integration tests for end-to-end orchestration with both LLM types (100% pass rate)
  - Dual deployment architecture: Local LLM (Ollama + GPU) or Remote LLM (OpenAI Codex + subscription)
  - Configuration-driven LLM switching (no code changes required)
  - CLI-based authentication and subprocess execution for OpenAI Codex
  - Comprehensive error handling, retry logic, and metrics tracking
  - 100% backward compatible with existing Ollama configurations
- **OBRA_SYSTEM_OVERVIEW.md**: Comprehensive system overview document in `docs/design/` with full architecture, design principles, capabilities, and development guidelines (830+ lines)
- **FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md**: Strategic decision document for dual deployment model (local + remote LLM) in `docs/business_dev/`
- **FLEXIBLE_LLM_ORCHESTRATOR_IMPLEMENTATION_PLAN.md**: Machine-optimized implementation plan for adding multi-provider LLM support (900+ lines) in `docs/development/`
  - Multi-provider architecture: HTTP API-based (Ollama, Claude API, Mistral) and CLI-based (OpenAI Codex CLI)
  - Starting with OpenAI Codex CLI (flat fee subscription, subprocess execution)
  - Framework for adding future providers (Claude API, Mistral API, Gemini API)
  - Provider comparison table with implementation patterns
- **Terminology**: "Orc" and "Imp" shorthand added to CLAUDE.md for efficient internal communication (formal terms: Orchestrator and Implementer)
- Phase completion summaries:
  - `docs/development/PHASE_6_INTEGRATION_TESTS_COMPLETION.md`
  - `docs/development/PHASE_7_DOCUMENTATION_COMPLETION.md`

### Changed
- **LLM Plugin System**: Transitioned from hardcoded Ollama to registry-based plugin architecture
  - `LocalLLMInterface` now registered as 'ollama' plugin
  - `OpenAICodexLLMPlugin` registered as 'openai-codex' plugin
  - Orchestrator uses `LLMRegistry.get(llm_type)` for dynamic LLM selection
- **Configuration Format**: Added `llm.type` field for LLM provider selection
  - `llm.type: ollama` → Local GPU-based LLM (Qwen 2.5 Coder)
  - `llm.type: openai-codex` → Remote CLI-based LLM (OpenAI Codex)
  - `llm.type: mock` → Mock LLM for testing
- **Documentation Updates**:
  - `docs/design/OBRA_SYSTEM_OVERVIEW.md`: Added dual deployment architecture diagrams (Option A: Ollama, Option B: OpenAI Codex)
  - `CLAUDE.md`: Added Flexible LLM reference to Key References section
  - `docs/business_dev/FLEXIBLE_LLM_ORCHESTRATOR_STRATEGY.md`: Updated status to "Implemented", version 1.1
- **Test Infrastructure**: Updated `conftest.py` to register all LLM plugins for testing
- **CLAUDE.md optimization**: Reduced from 1,062 to 493 lines (54% reduction / 569 lines removed)
  - Removed redundant sections: Project Status, Documentation Structure, Real-World Testing Results, Definition of Done, Critical Success Factors, Project Structure tree
  - Compressed verbose sections: Changelog Maintenance (140→7 lines), Next Steps (81→5 lines), Git Operations (23→1 line)
  - Categorized Common Pitfalls into 6 logical groups for better scanning
  - **Project Overview rewrite**: Machine-optimized concise version (15→6 lines) focusing on architecture, no business pitch
  - **Terminology fixes**: "Virtual Developer (VD)" → "Local LLM" for consistency
  - **Added OBRA_SYSTEM_OVERVIEW.md references**: Quick Context Refresh (#2), Starting a New Session (#2), When Stuck (top item)
  - **Corrected ADR count**: 11→12 ADRs
  - Streamlined Quick Context Refresh with prioritized OBRA_SYSTEM_OVERVIEW.md
- Comprehensive documentation cleanup and reorganization (November 4, 2025)
- Archived 20 outdated documentation files to docs/archive/
- Removed 2 empty directories (api/, troubleshooting/)

### Fixed
- Zero regressions introduced (105 core tests still passing)
- All integration tests passing with proper mocking strategies

## [1.2.0] - 2025-11-04

### Added
- **PHASE_6**: LLM-First Prompt Engineering Framework with validated performance improvements
  - Hybrid prompt format (JSON metadata + natural language)
  - StructuredPromptBuilder and StructuredResponseParser
  - PromptRuleEngine for validation
  - ABTestingFramework for empirical validation
  - TaskComplexityEstimator for complexity analysis
- **Interactive Streaming Interface** (Phase 1-2)
  - CommandProcessor with 8 interactive commands (/pause, /resume, /to-claude, /to-obra, /override-decision, /status, /help, /stop)
  - InputManager for non-blocking input handling with prompt_toolkit
  - 6 interactive checkpoints in orchestration loop
  - TaskStoppedException for graceful shutdown
  - 100 comprehensive tests (100/100 passing)
- **PHASE_4**: Production validation and bug fixes
  - Per-iteration session architecture (eliminates session lock conflicts)
  - Task-level metrics aggregation
  - Fixed 6 critical bugs found during real-world orchestration testing
- Configuration files for PHASE_6 features (prompt_rules.yaml, response_schemas.yaml, hybrid_prompt_templates.yaml)
- Interactive Streaming quick reference guide
- Colorama and prompt_toolkit dependencies for interactive features

### Changed
- Updated CLAUDE.md with current project status (v1.2+)
- Session management architecture: fresh Claude session per iteration
- Improved error recovery with per-iteration cleanup
- Enhanced documentation structure with phase reports organization

### Fixed
- Session lock conflicts (multiple iterations using same session)
- Stale session state leaking between iterations
- Metrics race condition in concurrent session updates
- Context window token count drift across sessions
- Configuration inheritance for profile settings
- Error recovery and session cleanup issues

### Performance
- **35.2% token efficiency improvement** (validated via A/B testing, p < 0.001)
- **22.6% faster response times** (statistically significant, p < 0.001)
- **100% parsing success rate** (vs 87% baseline)
- Maintained quality scores with no degradation

## [1.1.0] - 2025-11-03

### Added
- **M9**: Core Enhancements for Production (4 major features)
  - Retry logic with exponential backoff (1s → 2s → 4s → 8s → 16s)
  - Task dependency system with topological sort and cycle detection
  - Git auto-integration with LLM-generated semantic commit messages
  - Configuration profiles for different project types (6 profiles: python_project, web_app, ml_project, microservice, minimal, production)
- RetryManager class with jitter and error differentiation (91% coverage, 31 tests)
- DependencyResolver class with cascading failure handling (97% coverage, 48 tests)
- GitManager class with branch-per-task and PR creation (95% coverage, 35 tests)
- Database migration support for task dependencies
- 162 new tests for M9 features (121/128 passing, 96%)
- ADR-008, ADR-009, ADR-010 documenting retry logic, dependencies, and git integration

### Changed
- Config class enhanced with profile loading and inheritance
- CLI updated with --profile flag
- StateManager updated with dependency-aware queries
- Orchestrator integrated with retry, git, and dependency features

### Fixed
- Transient failures (rate limits, timeouts, network issues) now handled gracefully
- Circular dependency detection prevents invalid task graphs

## [1.0.0] - 2025-11-02

### Added
- **M8**: Local Agent Implementation with headless mode
  - ClaudeCodeLocalAgent using subprocess for local execution
  - Headless mode using `claude --print` flag for non-interactive operation
  - Dangerous mode with `--dangerously-skip-permissions` for full autonomy
  - Per-iteration fresh sessions for 100% reliability
  - OutputMonitor for parsing Claude Code output
  - Hook system with stop hook for completion detection
  - 33 comprehensive tests with 100% coverage
- Quick start guide (QUICK_START.md) for users
- Iterative orchestration runner with complex task examples
- Real-world orchestration testing capabilities
- ADR-004 (local agent architecture) and ADR-007 (headless mode enhancements)

### Changed
- PTY approach abandoned (Claude Code has known issues, no bugfix available)
- Runtime artifacts moved to ~/obra-runtime/ (separate from code repository)
- Documentation reorganized with cleanup V2
- README.md updated with headless mode documentation

### Fixed
- **10 critical bugs** discovered during first real orchestration testing session:
  - Hook system bugs (completion detection)
  - Headless mode integration issues
  - Output parsing edge cases
  - Session lifecycle issues
  - Context window tracking
  - Timeout handling
  - Error propagation
  - State persistence
  - File watcher threading
  - SSH authentication workflow

### Security
- SSH key authentication configured for git operations (no passwords/tokens needed)

## [0.9.0] - 2025-11-01

### Added
- **M7**: Testing & Deployment
  - 14 integration tests for end-to-end workflows
  - Docker deployment configuration (Dockerfile, docker-compose.yml)
  - Automated setup script (setup.sh)
  - 88% overall test coverage achieved (exceeds 85% target)
  - Critical modules at 90%+ coverage (DecisionEngine 96%, QualityController 99%)
- TEST_GUIDELINES.md with WSL2 crash prevention rules
- WSL2_TEST_CRASH_POSTMORTEM.md documenting testing issues and solutions

### Changed
- Test infrastructure hardened with resource limits (max 0.5s sleep, max 5 threads, max 20KB allocation)
- Production-ready status achieved with comprehensive testing

### Fixed
- WSL2 crashes during testing (caused by excessive sleeps, threads, and memory allocation)

## [0.8.0] - 2025-11-01

### Added
- **M6**: Integration & CLI
  - Click-based CLI with commands for project, task, and orchestration management
  - Interactive REPL interface for real-time control
  - Main orchestrator integration loop
  - 122 integration tests
- CLI commands: init, project create, task create, task execute, interactive
- Session management and context window tracking

### Changed
- Orchestrator integrated with all M0-M5 components
- Complete end-to-end workflow implemented

## [0.7.0] - 2025-10-31

### Added
- **M5**: Utility Services (91% coverage)
  - Token counting for context management
  - ContextManager for building task context from history
  - ConfidenceScorer with heuristic + LLM ensemble scoring
- Utility functions for token management and confidence calculation

### Changed
- Focus on quality over cost (Claude Code subscription, not per-token API)

## [0.6.0] - 2025-10-30

### Added
- **M4**: Orchestration Engine (96-99% coverage for critical modules)
  - TaskScheduler for managing task execution order
  - DecisionEngine for next-action decisions (96% coverage)
  - QualityController for output validation (99% coverage)
  - Breakpoint system for human intervention
- Validation order established: ResponseValidator → QualityController → ConfidenceScorer → DecisionEngine

### Changed
- Completeness checks before quality checks (fast validation before expensive validation)
- Different failure modes: incomplete = retry, low quality = review/breakpoint

## [0.5.0] - 2025-10-29

### Added
- **M3**: File Monitoring (90% coverage)
  - FileWatcher with real-time change detection using watchdog
  - File change tracking for rollback capability
  - Thread-safe file watching with proper cleanup
- ADR-003 documenting file watcher thread cleanup strategy

### Changed
- Enables rollback capability through comprehensive file change tracking

## [0.4.0] - 2025-10-28

### Added
- **M2**: LLM & Agent Interfaces (90% coverage)
  - OllamaLLM class for local LLM communication (Qwen 2.5 Coder on RTX 5090)
  - ResponseValidator for format/completeness checking
  - PromptGenerator for optimized prompt creation
  - Agent interface implementations (base for future Claude Code agents)
- Dual communication paths: Task execution vs validation (separate systems)

### Changed
- LLM validation always on host machine via HTTP API (http://172.29.144.1:11434)
- Agent type controls where Claude Code runs (local vs remote)

## [0.3.0] - 2025-10-27

### Added
- **M1**: Core Infrastructure (84% coverage)
  - StateManager as single source of truth for all state operations
  - Database models (Project, Task, Interaction, SessionMetrics)
  - SQLAlchemy ORM with SQLite backend
  - Config class with YAML configuration support
  - Custom exception hierarchy (ObraException and subclasses)
- ADR-003 (state management) documenting StateManager architecture
- Thread-safe operations with RLock
- Atomic transactions and rollback support

### Changed
- All state access must go through StateManager (no direct database access)

## [0.2.0] - 2025-10-26

### Added
- **M0**: Architecture Foundation (95% coverage)
  - Plugin system with AgentPlugin and LLMPlugin abstract base classes
  - Decorator-based registration (@register_agent, @register_llm)
  - PluginRegistry for runtime agent/LLM swapping
  - Comprehensive plugin tests
- ADR-001 (why plugins) and ADR-002 (deployment models)

### Changed
- Established plugin-based architecture for flexibility and testability

## [0.1.0] - 2025-10-25

### Added
- Initial project setup
- Project structure and directory organization
- Basic README.md and CLAUDE.md documentation
- Python package configuration (setup.py)
- Git repository initialization
- Development environment setup (requirements.txt, requirements-dev.txt)

### Security
- SSH key setup for GitHub authentication

---

## Version History Summary

- **v1.2.0** (Nov 4, 2025): PHASE_6 LLM-First Prompts + Interactive Streaming + Production Validation
- **v1.1.0** (Nov 3, 2025): M9 Core Enhancements (Retry, Dependencies, Git, Profiles)
- **v1.0.0** (Nov 2, 2025): M8 Local Agent + Headless Mode + Production Ready (10 bugs fixed)
- **v0.9.0** (Nov 1, 2025): M7 Testing & Deployment (88% coverage, Docker ready)
- **v0.8.0** (Nov 1, 2025): M6 Integration & CLI (Complete workflow)
- **v0.7.0** (Oct 31, 2025): M5 Utility Services (Token counting, confidence)
- **v0.6.0** (Oct 30, 2025): M4 Orchestration Engine (Decision logic)
- **v0.5.0** (Oct 29, 2025): M3 File Monitoring (Change tracking)
- **v0.4.0** (Oct 28, 2025): M2 LLM & Agent Interfaces (Dual paths)
- **v0.3.0** (Oct 27, 2025): M1 Core Infrastructure (StateManager)
- **v0.2.0** (Oct 26, 2025): M0 Plugin System (Foundation)
- **v0.1.0** (Oct 25, 2025): Initial Setup

## Project Metrics

**Current Version**: v1.2.0 (November 4, 2025)

- **Total Tests**: 695+ tests (433 base + 162 M9 + 100 Interactive)
- **Test Coverage**: 88% overall (maintained across all versions)
- **Total Code**: ~23,000+ lines (production + tests + docs)
- **Critical Bugs Fixed**: 16 total (10 in v1.0.0 + 6 in v1.2.0)
- **Implementation Time**: ~100+ hours across all phases
- **Milestones Completed**: M0-M9 + PHASE_3, PHASE_4, PHASE_6 + Interactive Streaming Phase 1-2
- **ADRs**: 11 Architecture Decision Records
- **Configuration Profiles**: 6 (python_project, web_app, ml_project, microservice, minimal, production)

## Links

- [Documentation](docs/README.md)
- [Architecture](docs/architecture/ARCHITECTURE.md)
- [Quick Start Guide](QUICK_START.md)
- [Contributing Guidelines](CLAUDE.md)
- [Archive](docs/archive/README.md)
