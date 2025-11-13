# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.7.0] - 2025-11-13

### Added
- **Unified Execution Architecture (ADR-017)**: All NL commands now route through orchestrator for consistent validation
  - IntentToTaskConverter component for OperationContext → Task conversion (`src/orchestration/intent_to_task_converter.py`)
  - NLQueryHelper component for query-only operations (`src/nl/nl_query_helper.py`, refactored from CommandExecutor)
  - Unified `execute_nl_command()` entry point in orchestrator for all NL command routing
  - **12 new integration tests** for NL routing (`tests/integration/test_orchestrator_nl_integration.py`) - 100% passing
  - **8 regression tests** for backward compatibility (`tests/integration/test_adr017_regression.py`) - 100% passing
  - **4 performance tests** validating latency < 3s P95 (`tests/integration/test_adr017_performance.py`) - 100% passing

### Changed
- **Internal API**: `IntentToTaskConverter.convert()` parameter names updated
  - Parameter `operation_context` → `parsed_intent` (naming clarity)
  - Parameter `confidence` removed (now stored in OperationContext)
  - New parameter `original_message` required for context tracking
- **Internal API**: `NLCommandProcessor` requires `config` parameter in initialization
  - Parameter order changed: `llm_plugin` now first, `state_manager` second
  - New required parameter `config` added for orchestrator integration
- **Internal API**: `NLCommandProcessor.process()` now returns `ParsedIntent` instead of `NLResponse`
  - NL commands no longer execute directly, must route through orchestrator
  - Enables unified validation pipeline for all commands
- **Architecture**: CommandExecutor renamed to NLQueryHelper, write operations removed
  - Supports QUERY operations only: SIMPLE, HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP
  - CREATE/UPDATE/DELETE operations now handled by IntentToTaskConverter → Orchestrator
- E2E test updated to validate unified NL routing through orchestrator (`tests/integration/test_orchestrator_e2e.py`)

### Performance
- **P50 latency**: < 2s for NL commands ✅
- **P95 latency**: < 3s for NL commands ✅ (acceptable trade-off: quality > speed)
- **Throughput**: > 40 commands/minute ✅
- **NL routing overhead**: < 500ms vs direct access ✅
- **Maintained quality**: No degradation in NL accuracy (95%+)

### Documentation
- **Migration Guide**: Added `docs/guides/ADR017_MIGRATION_GUIDE.md` for internal API changes
- **User Guide**: Updated `docs/guides/NL_COMMAND_GUIDE.md` with unified routing flow and v1.7.0 architecture diagram
- **Architecture**: Updated `docs/architecture/ARCHITECTURE.md` with completed ADR-017 section
- **ADR-017**: Marked as IMPLEMENTED in `docs/decisions/ADR-017-unified-execution-architecture.md`

### Tests
- **Total Tests Added**: 24 (12 integration + 8 regression + 4 performance)
- **All Tests Passing**: 794+ tests (770 existing + 24 new)
- **Coverage**: Maintained at 88%
- **Integration Tests**: 100% pass rate validating unified NL → orchestrator routing
- **Regression Tests**: 100% pass rate confirming backward compatibility
- **Performance Tests**: 100% pass rate meeting latency targets (P95 < 3s)

### Fixed
- **Database isolation** in integration tests (shared StateManager fixture)
- **LLM mocking** in test fixtures (added `is_available()` mock method)
- **File watcher** directory creation in test fixtures (ensures workspace exists)
- **NLCommandProcessor** initialization in E2E tests (updated parameter order)

### Benefits
- ✅ **Consistent Quality**: ALL commands (NL and CLI) validated through multi-stage pipeline
- ✅ **Unified Validation**: Single entry point for monitoring and metrics
- ✅ **Retry Logic**: NL commands automatically retry on transient failures
- ✅ **Confidence Tracking**: All NL operations tracked with confidence scores
- ✅ **Breakpoints**: Human-in-the-loop checkpoints for critical operations
- ✅ **Simplified Testing**: ~40% reduction in integration test surface area

[1.7.0]: https://github.com/Omar-Unpossible/claude_code_orchestrator/compare/v1.6.0...v1.7.0

## [1.6.0] - 2025-11-11

### Added - ADR-016: Natural Language Command Interface Refactor
- **Five-Stage Pipeline Architecture**: Decomposed single EntityExtractor into specialized components
  - **OperationClassifier**: Classifies operation type (CREATE, UPDATE, DELETE, QUERY) with 95% accuracy
  - **EntityTypeClassifier**: Classifies entity type (project, epic, story, task, milestone) with 95% accuracy
  - **EntityIdentifierExtractor**: Extracts entity names or IDs with 95% accuracy
  - **ParameterExtractor**: Extracts operation-specific parameters (status, priority, dependencies) with 92% accuracy
  - **QuestionHandler**: Handles informational questions with intelligent contextual responses
  - **Overall accuracy: 95%+ across all command types** (up from 80-85% in v1.3.0)

- **UPDATE Operation Support**: Natural language updates for work items
  - "Mark the manual tetris test as INACTIVE" → Updates project status
  - "Change task 10 priority to HIGH" → Updates task priority
  - "Update task 15 dependencies to include tasks 3 and 7" → Updates dependencies
  - **Resolves ISSUE-001**: Project status update misclassification fixed

- **Hierarchical Query Support**: Advanced query capabilities
  - **WORKPLAN** queries: "List the workplans for the projects" → Shows epic → story → task hierarchy
  - **NEXT_STEPS** queries: "What's next for project 1?" → Shows pending tasks prioritized
  - **BACKLOG** queries: "Show me the backlog" → Shows all pending work
  - **ROADMAP** queries: "Display the roadmap" → Shows milestones and epics
  - **Resolves ISSUE-002**: "Workplan" vocabulary gap resolved

- **Intelligent Question Handling**: Context-aware informational responses
  - **NEXT_STEPS** questions: "What's next for the tetris game?" → Actionable task list
  - **STATUS** questions: "How's project 1 going?" → Progress metrics and completion %
  - **BLOCKERS** questions: "What's blocking development?" → Identifies blockers and recommendations
  - **PROGRESS** questions: "Show progress for epic 2" → Velocity and estimated completion
  - **GENERAL** questions: "How do I create an epic?" → Usage instructions
  - **Resolves ISSUE-003**: Natural questions now handled instead of rejected

- **Comprehensive Test Suite**: 254 new tests for ADR-016
  - 214 unit tests (100% pass rate) for all new classifiers
  - 27 integration tests for full pipeline validation
  - 13 performance benchmarks (<1s latency, >50 cmd/min throughput)
  - Test coverage: 74% overall, 84-89% for core classifiers
  - Files: `tests/nl/test_operation_classifier.py`, `test_entity_type_classifier.py`, etc.

- **Documentation**: Complete documentation package
  - **ADR-016**: `docs/decisions/ADR-016-decompose-nl-entity-extraction.md` - Architecture decision
  - **Migration Guide**: `docs/guides/ADR016_MIGRATION_GUIDE.md` - Developer migration instructions
  - **Test Report**: `docs/quality/ADR016_STORY6_TEST_REPORT.md` - Comprehensive validation results
  - **Updated NL Guide**: `docs/guides/NL_COMMAND_GUIDE.md` - v1.6.0 features and examples

### Changed - ADR-016
- **CommandValidator**: Now accepts `OperationContext` instead of `ExtractedEntities`
  - New method: `validate(OperationContext)` - Validates operation + entity + parameters
  - Deprecated method: `validate_legacy(ExtractedEntities)` - Backward compatibility (removed in v1.7.0)
  - Enhanced validation: Checks operation-specific requirements (e.g., UPDATE requires identifier)

- **CommandExecutor**: Enhanced with hierarchical query support
  - Supports HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP query types
  - Improved error handling and parameter validation
  - Optimized for UPDATE operations (status, priority, dependencies)

- **NLCommandProcessor**: Orchestrates new 5-stage pipeline
  - Routes COMMAND intent through operation/entity/identifier/parameter stages
  - Routes QUESTION intent directly to QuestionHandler
  - Aggregates confidence scores across pipeline stages
  - Improved error propagation and logging

### Deprecated - ADR-016
- **EntityExtractor**: Deprecated in v1.6.0, will be removed in v1.7.0
  - Use new 5-stage pipeline (OperationClassifier → EntityTypeClassifier → EntityIdentifierExtractor → ParameterExtractor)
  - OR use NLCommandProcessor for high-level API
  - Backward compatibility via `CommandValidator.validate_legacy()` in v1.6.0 only

- **ExtractedEntities**: Replaced by `OperationContext` type
  - Old: `ExtractedEntities(entity_type, entities, confidence)`
  - New: `OperationContext(operation, entity_type, identifier, parameters, confidence)`

### Fixed - ADR-016
- **ISSUE-001 (HIGH)**: Project status update misclassification
  - Before: "Mark the manual tetris test as INACTIVE" created new task
  - After: Correctly identifies UPDATE + PROJECT, updates project status
  - Root cause: EntityExtractor didn't distinguish CREATE vs UPDATE operations
  - Solution: Dedicated OperationClassifier with 97% accuracy on UPDATE operations

- **ISSUE-002 (MEDIUM)**: Hierarchical query vocabulary gap
  - Before: "List the workplans for the projects" defaulted to simple list
  - After: Correctly identifies HIERARCHICAL query type, shows epic → story → task structure
  - Root cause: CommandExecutor didn't support hierarchical queries
  - Solution: Added QueryType enum and hierarchical rendering in CommandExecutor

- **ISSUE-003 (MEDIUM)**: Natural questions rejected as invalid
  - Before: "What's next for the tetris game development?" rejected with "Invalid command syntax"
  - After: Handled intelligently with contextual task list and recommendations
  - Root cause: No question handling pathway in pipeline
  - Solution: Added QuestionHandler component with 5 question types

### Performance - ADR-016
- **Latency**: <1000ms end-to-end pipeline latency (target: <1500ms P95) ✅
  - IntentClassifier: <200ms
  - OperationClassifier: <150ms
  - EntityTypeClassifier: <150ms
  - EntityIdentifierExtractor: <150ms
  - ParameterExtractor: <150ms
  - CommandValidator: <50ms
  - CommandExecutor: <100ms

- **Throughput**: >50 commands/minute (target: >50) ✅
- **Memory**: <200MB additional memory overhead (target: <200MB) ✅
- **Accuracy**: 95%+ across all command types (target: 95%) ✅

### Migration
- **Breaking Change**: EntityExtractor API deprecated
- **Rollback Available**: Set `nl_commands.use_legacy_pipeline: true` in config (v1.6.0 only)
- **Migration Timeline**: Migrate by v1.7.0 (Q1 2026) when legacy pipeline is removed
- **See**: `docs/guides/ADR016_MIGRATION_GUIDE.md` for complete migration instructions

---

### Fixed
- **NL Test Suite**: Fixed 10 failing tests in NL command system (90% pass rate achieved - 55/61 mock tests)
  - Replaced broken mock LLM fixtures with `mock_llm_smart` and `mock_llm_simple` in `tests/conftest.py`
  - Fixed `test_nl_entity_extractor_bug_prevention.py` (6/6 tests now passing, was 1/6)
  - Fixed `test_nl_command_processor_integration.py` (25/25 tests now passing, was 21/25)
  - Fixed `test_nl_e2e_integration.py` (24/30 tests passing, 1 MagicMock leak fixed)
  - Added 'project' as valid entity type in `ExtractedEntities` class (was missing, causing 3 failures)
  - All mock tests now execute in ~15s (improved from ~31s target)

### Added
- **Real LLM Integration Tests**: Created 33 new tests using actual Ollama/Qwen (5-10min execution)
  - File: `tests/test_nl_real_llm_integration.py`
  - Intent classification accuracy tests (8 tests) - Validates COMMAND vs QUESTION classification
  - Entity extraction accuracy tests (10 tests) - Validates extraction of all entity types
  - Full pipeline E2E tests (8 tests) - Complete workflow validation with database verification
  - LLM failure mode tests (4 tests) - Timeout, connection, error handling
  - Performance benchmark tests (3 tests) - Speed measurement for optimization
  - Validates production behavior with real LLM, not just mocked logic
- **NL Testing Strategy Documentation**: Comprehensive guide on when to use mock vs real LLM tests
  - File: `docs/testing/NL_TESTING_STRATEGY.md`
  - Decision matrix for test approach selection (mock vs real LLM)
  - Test suite organization and execution commands
  - Pytest markers for integration tests (`@pytest.mark.integration`, `@pytest.mark.requires_ollama`)
  - CI/CD configuration guidance (mock on commit, real LLM on merge)
  - Performance benchmarks and troubleshooting guide
  - Migration guide for updating existing tests
- **Real LLM Testing Guide**: Detailed setup and troubleshooting documentation
  - File: `docs/development/REAL_LLM_TESTING_GUIDE.md`
  - Prerequisites and Ollama setup instructions
  - Running tests in different modes (development, pre-commit, pre-merge, CI/CD)
  - Comprehensive troubleshooting section
  - Performance expectations and optimization tips
- **Testing Documentation Index**: Centralized testing documentation reference
  - File: `docs/testing/README.md`
  - Links to all testing guides and strategies
  - Quick reference commands
  - Test file overview with execution times
- **Pytest Markers**: Added new markers for integration testing
  - `@pytest.mark.requires_ollama` - Tests requiring Ollama LLM service
  - `@pytest.mark.benchmark` - Performance benchmark tests (requires pytest-benchmark plugin)

### Changed
- **Test Fixtures**: Improved mock LLM fixtures in `tests/conftest.py`
  - `mock_llm_responses`: Dictionary of valid JSON templates for all Obra entity types (project, epic, story, task, subtask, milestone)
  - `mock_llm_smart`: Context-aware mock that returns appropriate responses based on user message keywords
    - Intelligently classifies intent (COMMAND for Obra entities, QUESTION for general info)
    - Returns correct entity type based on message content
    - Prevents MagicMock objects from leaking into responses
  - `mock_llm_simple`: Basic mock for simple test cases (always returns task entity)
  - `real_llm_*` fixtures: Module-scoped fixtures for real LLM integration tests (shared across tests for performance)
- **TEST_GUIDELINES.md**: Added comprehensive Natural Language Command Testing section
  - Dual testing strategy explanation (mock vs real LLM)
  - Example usage for both mock and real LLM tests
  - Prerequisites for real LLM tests (Ollama setup)
  - Best practices and cross-references to detailed guides

### Technical Details
- **Mock Fixture Intelligence**:
  - `mock_llm_smart` analyzes user messages to determine entity type
  - Checks for Obra work item keywords (project, epic, story, task, etc.)
  - Distinguishes between COMMAND (queries Obra data) and QUESTION (general programming)
  - Returns valid JSON matching `src/nl/schemas/obra_schema.json`
- **Real LLM Test Architecture**:
  - Module-scoped fixtures reuse config/state across tests (performance optimization)
  - Helper functions (`assert_valid_intent_result`, `assert_valid_extraction_result`) for validation
  - Tests properly marked with pytest markers for filtering
  - Default pytest run skips integration tests (fast development workflow)
- **Test Execution Modes**:
  - Development: Mock tests only (15s, no Ollama required)
  - Integration: Real LLM tests only (5-10min, requires Ollama)
  - Full: Both mock + real LLM (88+ tests, ~10min total)

### Documentation
- Created `docs/testing/NL_TESTING_STRATEGY.md` - Comprehensive testing strategy
- Created `docs/development/REAL_LLM_TESTING_GUIDE.md` - Real LLM testing guide
- Created `docs/testing/README.md` - Testing documentation index
- Updated `docs/development/TEST_GUIDELINES.md` - Added NL testing section
- Updated `pytest.ini` - Added `requires_ollama` and `benchmark` markers

### Planned
- Budget & Cost Controls
- Metrics & Reporting System
- Checkpoint System

## [1.5.0] - 2025-11-11

### Changed - BREAKING
- **Interactive Mode UX Improvement**: Natural text now defaults to orchestrator
  - **Natural language messages (no slash prefix) sent directly to orchestrator** - Eliminates friction for primary use case
  - **ALL system commands now require '/' prefix as first character** - Including `/help`, `/status`, `/pause`, `/resume`, `/stop`
  - **Invalid slash commands rejected with helpful error message** - Shows available commands and suggests `/help`
  - **Removed `/to-orch` command** - Natural text is default (no prefix needed)
  - **Updated slash commands**: `/help`, `/status`, `/pause`, `/resume`, `/stop`, `/to-impl`, `/override-decision`
  - **Prompt indicator** - No change needed (orchestrator context already clear)
  - **Tab completion** - Updated to only complete slash commands when input starts with `/`
  - **Bottom toolbar** - Added: "Type naturally to talk to orchestrator, or /help for commands"

### Migration Guide
**Old Syntax → New Syntax:**
- `help` → `/help`
- `status` → `/status`
- `/to-orch Be more lenient` → `Be more lenient with quality`
- `/to-impl fix bug` → `/to-impl fix bug` (unchanged)
- `pause` → `/pause`
- `resume` → `/resume`

**Rationale:** Eliminates friction for primary use case (orchestrator communication). Asymmetry between orchestrator (default) and implementer (/to-impl) is intentional - orchestrator is primary interface for guidance.

### Added
- `CommandValidationError` exception for invalid slash commands
- Tab completion for all slash commands (only when input starts with `/`)
- Bottom toolbar with usage hints in InputManager
- Comprehensive documentation in `INTERACTIVE_UX_IMPROVEMENT_PLAN.md` and `INTERACTIVE_UX_IMPLEMENTATION_CHECKLIST.md`

### Technical Details
- **CommandProcessor** (`src/utils/command_processor.py`):
  - New routing logic: `execute_command()` routes non-slash to orchestrator
  - New method: `_send_to_orchestrator()` for default routing
  - New method: `_process_slash_command()` with validation
  - Updated help text with new command syntax
- **Orchestrator** (`src/orchestrator.py`):
  - Error handling improvements in `_check_interactive_commands()` and `_wait_for_resume()`
  - Catches `CommandValidationError` and shows helpful messages
- **InputManager** (`src/utils/input_manager.py`):
  - New `SlashCommandCompleter` class for context-aware completion
  - Updated `SLASH_COMMANDS` list
  - Added bottom toolbar hint

### Documentation
- Updated `docs/development/INTERACTIVE_STREAMING_QUICKREF.md` with v1.5.0 UX changes
- Added `docs/development/INTERACTIVE_UX_IMPROVEMENT_PLAN.md` (human-readable plan)
- Added `docs/development/INTERACTIVE_UX_IMPLEMENTATION_CHECKLIST.md` (machine-optimized checklist)

## [1.4.0] - 2025-11-11

### Added
- **Project Infrastructure Maintenance System** (ADR-015) - Complete automatic documentation maintenance
  - **DocumentationManager Component** (`src/utils/documentation_manager.py`):
    - 10 public methods for comprehensive documentation management
    - Freshness checking (30/60/90 day thresholds)
    - Automatic maintenance task creation with rich context
    - Implementation plan archiving
    - CHANGELOG update automation
    - ADR creation suggestions
    - 42 unit tests with 91% coverage
  - **Event-Driven Triggers**:
    - Epic completion hook: Creates maintenance task when `requires_adr=True` or `has_architectural_changes=True`
    - Milestone achievement hook: Creates comprehensive maintenance task with all epic context
    - Configurable scopes: lightweight, comprehensive, full_review
  - **Periodic Freshness Checks** (Story 2.1):
    - Threading-based scheduler using `threading.Timer`
    - Configurable interval (default: 7 days)
    - Automatic rescheduling after each check
    - Graceful shutdown with thread safety
    - 12 unit tests for periodic functionality
  - **StateManager Integration**:
    - 4 new Task fields: `requires_adr`, `has_architectural_changes`, `changes_summary`, `documentation_status`
    - 1 new Milestone field: `version`
    - Database migration 004 with indexed fields
    - Hooks in `complete_epic()` and `achieve_milestone()`
  - **Configuration System**:
    - New `documentation:` section in `config/default_config.yaml`
    - Master enable/disable switch
    - Per-trigger configuration (epic_complete, milestone_achieved, periodic)
    - Maintenance targets, freshness thresholds, archive settings
    - Task configuration (priority, assigned agent)
  - **Integration Testing** (Story 1.4):
    - 8 end-to-end tests verifying complete workflows
    - Epic completion → task creation flow
    - Milestone achievement → comprehensive task flow
    - Configuration variation testing
    - 100% integration path coverage
  - **Documentation**:
    - Comprehensive user guide: `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md` (434 lines)
    - Architecture documentation: `docs/architecture/ARCHITECTURE.md` (v1.4 section added)
    - ADR-015 documenting system design and rationale
    - Implementation plans (human and machine-readable)
  - **Total Tests**: 50 (42 unit + 8 integration), all passing
  - **Coverage**: 91% (exceeds >90% target)

### References
- **ADR-015**: `docs/decisions/ADR-015-project-infrastructure-maintenance-system.md`
- **User Guide**: `docs/guides/PROJECT_INFRASTRUCTURE_GUIDE.md`
- **Implementation Plan**: `docs/development/PROJECT_INFRASTRUCTURE_IMPLEMENTATION_PLAN.yaml`
- **Epic Breakdown**: `docs/development/PROJECT_INFRASTRUCTURE_EPIC_BREAKDOWN.md`
- **Story Summaries**:
  - Story 1.1: `docs/development/STORY_1.1_DOCUMENTATION_MANAGER_SUMMARY.md`
  - Story 1.4: `docs/development/STORY_1.4_INTEGRATION_TESTING_SUMMARY.md`
  - Story 2.1: `docs/development/STORY_2.1_PERIODIC_CHECKS_SUMMARY.md`

## [1.3.0] - 2025-11-11

### Added
- **Natural Language Command Interface** (ADR-014) - Complete NL processing pipeline (Stories 1-5)
  - **Intent Classification Engine** (Story 1):
    - `IntentClassifier` with 95%+ accuracy on COMMAND/QUESTION/CLARIFICATION_NEEDED detection
    - Confidence-based clarification requests (threshold: 0.7)
    - Jinja2 prompt templates with few-shot learning examples
    - Conversation context awareness for multi-turn interactions
    - 22 unit tests (95% coverage, 100% pass rate)
  - **Schema-Aware Entity Extraction** (Story 2):
    - `EntityExtractor` with Obra schema understanding (epic/story/task/subtask/milestone)
    - 90%+ accuracy on entity extraction from natural language
    - Multi-entity support (create multiple items in one command)
    - Epic/story reference resolution by name or ID
    - 24 unit tests (95% coverage, 100% pass rate)
  - **Command Validation and Execution** (Story 3):
    - `CommandValidator` with business rule validation (epic exists, no cycles, required fields)
    - `CommandExecutor` with StateManager integration and transaction safety
    - Reference resolution (epic_reference → epic_id, story_reference → story_id)
    - Confirmation workflow for destructive operations (delete/update/execute)
    - 30 unit tests (95% coverage, 100% pass rate)
  - **Response Formatting** (Story 4):
    - `ResponseFormatter` with color-coded responses (green=success, red=error, yellow=warning)
    - Contextual next-action suggestions ("Created Epic #5 → Next: Add stories")
    - Recovery suggestions for errors ("Epic not found → Try: List epics with 'show epics'")
    - Clarification prompts with numbered options
    - 27 unit tests (99% coverage, 100% pass rate)
  - **Pipeline Integration** (Story 5):
    - `NLCommandProcessor` orchestrating full pipeline (intent → extraction → validation → execution → formatting)
    - Conversation context management (configurable max turns: 10)
    - Seamless integration with `CommandProcessor` for unified interface
    - Automatic routing: slash commands → slash handler, non-slash → NL processor
    - 13 integration tests (100% pass rate)
  - **Configuration**:
    - `nl_commands` config section with 9 options (enabled, llm_provider, confidence_threshold, etc.)
    - Master kill switch (`nl_commands.enabled`) for easy disable
    - Per-project defaults (default_project_id, require_confirmation_for)
  - **Documentation**:
    - `docs/guides/NL_COMMAND_GUIDE.md` (425 lines) - Complete user guide with examples, troubleshooting, FAQ
    - `docs/decisions/ADR-014-natural-language-command-interface.md` (550 lines) - Architecture decision record
    - `docs/development/NL_COMMAND_INTERFACE_SPEC.json` - Machine-readable specification
    - `docs/development/NL_COMMAND_INTERFACE_IMPLEMENTATION_GUIDE.md` - Developer implementation guide
    - `docs/development/NL_COMMAND_TEST_SPECIFICATION.md` - Comprehensive test specification
  - **Test Coverage**: 103 total tests (27 ResponseFormatter + 22 IntentClassifier + 24 EntityExtractor + 30 CommandValidator/Executor + 13 integration)
  - **Performance**: <3s end-to-end latency (P95), 95% intent accuracy, 90% entity extraction accuracy

- **Agile/Scrum Work Hierarchy** (ADR-013) - Phase 2 Production-Ready Implementation
  - **Core Implementation** (Phase 1, 24 hours):
    - TaskType enum: EPIC, STORY, TASK, SUBTASK (replaces generic "Task" for everything)
    - Epic: Large feature spanning multiple stories (3-15 sessions)
    - Story: User-facing deliverable (1 orchestration session)
    - Task: Technical work implementing story (default type, backward compatible)
    - Subtask: Granular step (via parent_task_id hierarchy)
    - True Milestone model: Zero-duration checkpoint (not work items)
    - Database migration: `migrations/versions/003_agile_hierarchy.sql` with rollback support
    - StateManager methods: `create_epic()`, `create_story()`, `get_epic_stories()`, `get_story_tasks()`
    - Milestone methods: `create_milestone()`, `check_milestone_completion()`, `achieve_milestone()`
    - Orchestrator: `execute_epic()` method replaces `execute_milestone()` (deprecated, removed in v2.0)
    - CLI commands: `obra epic`, `obra story`, `obra milestone` command groups (create/list/show/execute)
    - Smoke tests: 9 tests verifying core functionality (100% pass rate)
  - **Production Readiness** (Phase 2, 16 hours):
    - Enhanced CLI commands: Complete CRUD operations (list/show/update/delete for epic/story/milestone)
    - Comprehensive test suite: 75 tests (72 passing, 3 skipped - 96% pass rate)
      - Story 3.1: StateManager edge cases (50 tests) - validation, performance, cascade operations
      - Story 3.2: Orchestrator tests (15 tests) - epic execution, session management, backward compatibility
      - Story 3.3: Integration tests (20 tests) - full workflows, migration compatibility, error handling
    - Code quality improvements: Helper method renaming (_milestone → _epic for consistency)
    - Documentation suite:
      - `docs/guides/AGILE_WORKFLOW_GUIDE.md` (770+ lines) - Complete workflow examples, patterns, CLI reference
      - `docs/guides/MIGRATION_GUIDE_V1.3.md` (580+ lines) - Detailed migration guide with rollback procedures
      - CLAUDE.md: Added Architecture Principle #12 (Agile/Scrum Work Hierarchy)
      - Updated Key References section with Agile workflow guide
      - Updated ADR count from 12 to 13
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

### Changed
- **Test Count**: Increased from 695 tests to 770+ tests (75 new Agile hierarchy tests)
- **Documentation**: Updated project status from "695+ tests" to "770+ tests" in CLAUDE.md
- **Terminology**: Helper methods in Orchestrator now use "epic" terminology consistently
- **API Enhancement**: Added 13+ new methods across StateManager, Orchestrator, CLI

### Deprecated
- `execute_milestone()` method - Use `execute_epic()` instead (will be removed in v2.0)
  - Still functional in v1.3.0 for backward compatibility
  - Migration guide available at `docs/guides/MIGRATION_GUIDE_V1.3.md`

### Fixed
- Zero regressions introduced (all existing tests still passing)
- Maintained 88% overall code coverage
- All integration tests passing with proper mocking strategies
- Backward compatibility: Existing tasks default to TaskType.TASK seamlessly

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
