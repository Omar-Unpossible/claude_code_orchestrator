# ADR-016 Epic Breakdown: NL Pipeline Decomposition

**Version**: 1.0
**Created**: 2025-11-11
**Target Version**: v1.6.0

## Epic Overview

**Epic Name**: Decompose NL Entity Extraction Pipeline (ADR-016)

**Epic Description**: Refactor the monolithic EntityExtractor into a five-stage pipeline with single-responsibility components to increase NL command accuracy from 80-85% to 95%+.

**Business Value**:
- Critical issues blocking production deployment are resolved (ISSUE-001, ISSUE-002, ISSUE-003)
- 95%+ accuracy makes NL interface production-ready
- Better extensibility for future NL features

**Estimated Effort**: 8-10 days

---

## Story Hierarchy

### Story 1: Foundation and Design (1 day)
**Goal**: Establish architectural foundation and approve ADR-016

#### Tasks:
1. **Review and Approve ADR-016** (2 hours)
   - Review architecture with stakeholders
   - Address concerns and questions
   - Obtain formal approval
   - **Acceptance**: ADR-016 status = Approved

2. **Create Core Data Structures** (2 hours)
   - File: `src/nl/types.py`
   - Define `OperationType` enum: CREATE, UPDATE, DELETE, QUERY
   - Define `QueryType` enum: SIMPLE, HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP
   - Define `OperationContext` dataclass: operation + entity_type + identifier + parameters
   - Define `QuestionType` enum: NEXT_STEPS, STATUS, BLOCKERS, PROGRESS, GENERAL
   - **Acceptance**: All types documented with docstrings and type hints

3. **Design Component Interfaces** (2 hours)
   - File: `src/nl/base.py`
   - Create abstract base classes for each new component
   - Specify input/output contracts
   - Define error handling patterns
   - **Acceptance**: Clear interfaces for 5 new components

4. **Update NL Command Spec** (2 hours)
   - File: `docs/development/NL_COMMAND_INTERFACE_SPEC.json`
   - Add operation type examples (CREATE, UPDATE, DELETE, QUERY)
   - Add parameter extraction examples (status, priority, dependencies)
   - Add question handling examples (NEXT_STEPS, STATUS, etc.)
   - **Acceptance**: Spec includes all new patterns

**Story Acceptance Criteria**:
- ✅ ADR-016 approved by stakeholders
- ✅ `src/nl/types.py` created with 4 new enums/dataclasses
- ✅ `src/nl/base.py` created with abstract base classes
- ✅ NL_COMMAND_INTERFACE_SPEC.json updated with new patterns
- ✅ All code documented and type-hinted

---

### Story 2: Single-Purpose Classifiers (2 days)
**Goal**: Implement OperationClassifier and EntityTypeClassifier

#### Tasks:
1. **Implement OperationClassifier** (4 hours, Day 2)
   - File: `src/nl/operation_classifier.py`
   - **Purpose**: Classify command into CREATE/UPDATE/DELETE/QUERY
   - **Prompt Template**: "Classify the operation type for this command. Choose exactly one: CREATE (making new), UPDATE (changing existing), DELETE (removing), QUERY (asking for info)..."
   - **Implementation**:
     - `classify(user_input: str) -> OperationResult`
     - Call LLM with operation classification prompt
     - Parse response into OperationType
     - Calculate confidence score
   - **Tests**: `tests/nl/test_operation_classifier.py` (20 tests)
     - 5 CREATE examples: "Create epic for auth", "Add new task", etc.
     - 5 UPDATE examples: "Mark project as inactive", "Set priority to HIGH", etc.
     - 5 DELETE examples: "Delete task 5", "Remove epic 3", etc.
     - 5 QUERY examples: "Show all projects", "List tasks", "What's next", etc.
   - **Acceptance**: 20 tests passing, 95%+ accuracy on test cases

2. **Implement EntityTypeClassifier** (4 hours, Day 2)
   - File: `src/nl/entity_type_classifier.py`
   - **Purpose**: Classify entity type given operation context
   - **Prompt Template**: "Given that this is a {operation_type} operation, identify the entity type. Entity types: PROJECT (top-level), EPIC (large feature), STORY (user deliverable), TASK (technical work), MILESTONE (checkpoint)..."
   - **Implementation**:
     - `classify(user_input: str, operation: OperationType) -> EntityTypeResult`
     - Build prompt with operation context
     - Call LLM with entity type classification prompt
     - Parse response into EntityType
     - Calculate confidence score
   - **Tests**: `tests/nl/test_entity_type_classifier.py` (25 tests)
     - 5 PROJECT examples with different operations
     - 5 EPIC examples with different operations
     - 5 STORY examples with different operations
     - 5 TASK examples with different operations
     - 5 MILESTONE examples with different operations
   - **Acceptance**: 25 tests passing, 95%+ accuracy on test cases

**Story Acceptance Criteria**:
- ✅ `src/nl/operation_classifier.py` implemented and tested (20 tests)
- ✅ `src/nl/entity_type_classifier.py` implemented and tested (25 tests)
- ✅ 45 tests passing (100% pass rate)
- ✅ 95%+ classification accuracy on diverse examples
- ✅ Code coverage ≥95% for both components

---

### Story 3: Entity and Parameter Extraction (2 days)
**Goal**: Implement EntityIdentifierExtractor and ParameterExtractor

#### Tasks:
1. **Implement EntityIdentifierExtractor** (4 hours, Day 3)
   - File: `src/nl/entity_identifier_extractor.py`
   - **Purpose**: Extract entity name or ID from command
   - **Prompt Template**: "Extract the {entity_type} identifier from this command. The identifier can be a name (string) or an ID (number)..."
   - **Implementation**:
     - `extract(user_input: str, entity_type: EntityType, operation: OperationType) -> IdentifierResult`
     - Build prompt with entity type and operation context
     - Call LLM with identifier extraction prompt
     - Parse response (handle both string names and integer IDs)
     - Calculate confidence score
   - **Tests**: `tests/nl/test_entity_identifier_extractor.py` (20 tests)
     - 10 name-based identifiers: "manual tetris test", "user authentication", etc.
     - 10 ID-based identifiers: "project 1", "task 5", "epic #3", etc.
   - **Acceptance**: 20 tests passing, 90%+ extraction accuracy

2. **Implement ParameterExtractor** (4 hours, Day 3)
   - File: `src/nl/parameter_extractor.py`
   - **Purpose**: Extract operation-specific parameters (status, priority, dependencies)
   - **Prompt Template**: "Extract parameters from this command. Return JSON. Expected parameters: {expected_params}. Example: {\"status\": \"INACTIVE\", \"priority\": \"HIGH\"}..."
   - **Implementation**:
     - `extract(user_input: str, operation: OperationType, entity_type: EntityType) -> ParameterResult`
     - Determine expected parameters based on operation + entity type
     - Build prompt with expected parameters
     - Call LLM with parameter extraction prompt (JSON format)
     - Parse JSON response into Dict[str, Any]
     - Calculate confidence score
   - **Tests**: `tests/nl/test_parameter_extractor.py` (25 tests)
     - 5 status updates: "mark as INACTIVE", "set status to ACTIVE"
     - 5 priority settings: "with priority HIGH", "set priority to LOW"
     - 5 dependencies: "depends on task 5", "requires epic 3"
     - 5 query parameters: "top 5 tasks", "show pending items", "limit 10"
     - 5 complex combinations: "create task with priority HIGH depends on task 3"
   - **Acceptance**: 25 tests passing, 90%+ extraction accuracy

**Story Acceptance Criteria**:
- ✅ `src/nl/entity_identifier_extractor.py` implemented and tested (20 tests)
- ✅ `src/nl/parameter_extractor.py` implemented and tested (25 tests)
- ✅ 45 tests passing (100% pass rate)
- ✅ 90%+ extraction accuracy on diverse examples
- ✅ Handles both string names and integer IDs
- ✅ JSON parsing for parameters works correctly

---

### Story 4: Question Handling (1 day)
**Goal**: Implement QuestionHandler for informational queries

#### Tasks:
1. **Implement QuestionHandler Core** (4 hours, Day 4)
   - File: `src/nl/question_handler.py`
   - **Purpose**: Handle informational questions gracefully
   - **Question Types**: NEXT_STEPS, STATUS, BLOCKERS, PROGRESS, GENERAL
   - **Implementation**:
     - `handle(user_input: str) -> QuestionResponse`
     - Step 1: Classify question type using LLM
     - Step 2: Extract entities from question (project name, etc.)
     - Step 3: Query StateManager for relevant data
     - Step 4: Format helpful response
   - **Question Type Logic**:
     - NEXT_STEPS: Query pending tasks for project (limit 5, ordered by priority)
     - STATUS: Query project/epic/task status and completion %
     - BLOCKERS: Query tasks with BLOCKED status or missing dependencies
     - PROGRESS: Query completion metrics for project/epic
     - GENERAL: Fallback with help message
   - **Acceptance**: Core handler logic implemented

2. **Test QuestionHandler** (2 hours, Day 4)
   - File: `tests/nl/test_question_handler.py`
   - **Tests** (30 tests):
     - 6 NEXT_STEPS questions: "What's next?", "Next tasks for project 1?", etc.
     - 6 STATUS questions: "What's the status?", "How's progress?", "Is it done?"
     - 6 BLOCKERS questions: "What's blocking?", "Any issues?", "What's stuck?"
     - 6 PROGRESS questions: "Show progress", "How far along?", "Completion %?"
     - 6 GENERAL questions: "Help?", "What can you do?", "Explain epic 3"
   - **Acceptance**: 30 tests passing, helpful responses for all question types

**Story Acceptance Criteria**:
- ✅ `src/nl/question_handler.py` implemented and tested (30 tests)
- ✅ All 5 question types supported (NEXT_STEPS, STATUS, BLOCKERS, PROGRESS, GENERAL)
- ✅ 30 tests passing (100% pass rate)
- ✅ Helpful responses for all question types
- ✅ StateManager integration works correctly
- ✅ ISSUE-003 resolved (questions no longer rejected)

---

### Story 5: Update Core Components (2 days)
**Goal**: Update CommandValidator, CommandExecutor, and NLCommandProcessor

#### Tasks:
1. **Update CommandValidator** (4 hours, Day 6)
   - File: `src/nl/command_validator.py`
   - **Changes**:
     - Accept `OperationContext` instead of entity list
     - Add validation rule: UPDATE requires identifier
     - Add validation rule: Entity exists for UPDATE/DELETE operations
     - Add validation rule: Parameters valid for operation (e.g., valid status values)
   - **New Validation Logic**:
     ```python
     def validate(self, context: OperationContext) -> ValidationResult:
         # Rule 1: Operation + entity type compatibility
         # Rule 2: Entity exists (for UPDATE/DELETE)
         # Rule 3: Parameters valid for operation
     ```
   - **Tests**: `tests/nl/test_command_validator.py` (15 tests)
     - 5 valid combinations
     - 5 invalid combinations
     - 5 missing identifiers
   - **Acceptance**: 15 tests passing, proper validation for OperationContext

2. **Update CommandExecutor** (6 hours, Day 6-7)
   - File: `src/nl/command_executor.py`
   - **Changes**:
     - Accept `OperationContext` instead of entity list
     - Add hierarchical query support (HIERARCHICAL query type)
     - Add query type handling: NEXT_STEPS, BACKLOG, ROADMAP
     - Improve error handling
   - **New Query Types Implementation**:
     - HIERARCHICAL: Get epics → stories → tasks hierarchy
     - NEXT_STEPS: Get pending tasks for project (limit 5, ordered by priority)
     - BACKLOG: Get all pending tasks
     - ROADMAP: Get milestones and associated epics
   - **Tests**: `tests/nl/test_command_executor.py` (20 tests)
     - 4 CREATE operations
     - 4 UPDATE operations
     - 4 DELETE operations
     - 8 QUERY operations (simple, hierarchical, next_steps, backlog, roadmap)
   - **Acceptance**: 20 tests passing, hierarchical queries work, ISSUE-002 resolved

3. **Update NLCommandProcessor** (4 hours, Day 7)
   - File: `src/nl/nl_command_processor.py`
   - **Changes**:
     - Orchestrate new 5-stage pipeline (Operation → EntityType → Identifier → Parameters → Validate → Execute)
     - Add error handling at each stage
     - Add QUESTION path to QuestionHandler
     - Log intermediate outputs for debugging
   - **New Pipeline Logic**:
     ```python
     def process(self, user_input: str) -> ProcessingResult:
         # Stage 1: Classify intent (COMMAND vs QUESTION)
         # If QUESTION: → QuestionHandler
         # If COMMAND:
         #   Stage 2: Classify operation (CREATE/UPDATE/DELETE/QUERY)
         #   Stage 3: Classify entity type (PROJECT/EPIC/STORY/TASK/MILESTONE)
         #   Stage 4: Extract identifier (name or ID)
         #   Stage 5: Extract parameters (status, priority, etc.)
         #   Stage 6: Validate (OperationContext)
         #   Stage 7: Execute (CommandExecutor)
     ```
   - **Tests**: `tests/nl/test_nl_command_processor.py` (10 integration tests)
     - 3 CREATE commands end-to-end
     - 2 UPDATE commands end-to-end
     - 2 QUERY commands end-to-end
     - 3 QUESTION commands end-to-end
   - **Acceptance**: 10 tests passing, full pipeline works, ISSUE-001 resolved

**Story Acceptance Criteria**:
- ✅ `src/nl/command_validator.py` updated and tested (15 tests)
- ✅ `src/nl/command_executor.py` updated and tested (20 tests)
- ✅ `src/nl/nl_command_processor.py` updated and tested (10 tests)
- ✅ 45 tests passing (100% pass rate)
- ✅ Full pipeline works end-to-end
- ✅ ISSUE-001 resolved (status updates work correctly)
- ✅ ISSUE-002 resolved (hierarchical queries work)

---

### Story 6: Comprehensive Testing (2 days)
**Goal**: Validate entire system with unit, integration, and manual tests

#### Tasks:
1. **Run Unit Test Suite** (2 hours, Day 8)
   - Run all 165 unit tests for new components
   - Verify test coverage targets:
     - OperationClassifier: 95%
     - EntityTypeClassifier: 95%
     - EntityIdentifierExtractor: 95%
     - ParameterExtractor: 90%
     - QuestionHandler: 90%
   - **Acceptance**: All 165 unit tests passing, coverage targets met

2. **Run Integration Test Suite** (2 hours, Day 8)
   - Run 30 new integration tests (full pipeline, error propagation, cross-component)
   - Run 103 existing NL tests (regression check)
   - **Test Scenarios**:
     - 10 full pipeline tests (CREATE, UPDATE, QUERY, QUESTION end-to-end)
     - 10 error propagation tests (low confidence, validation failures)
     - 103 existing NL tests (must all pass)
     - 7 cross-component tests
   - **Acceptance**: All 130 integration tests passing, no regressions

3. **Manual Testing - Issue Validation** (4 hours, Day 9)
   - **ISSUE-001 Validation** (status updates):
     - Test: "Mark the manual tetris test as INACTIVE"
     - Expected: Update project #2 status to INACTIVE (not create task)
     - Test: "Set project 1 status to COMPLETED"
     - Test: "Change epic 2 to PAUSED"
   - **ISSUE-002 Validation** (hierarchical queries):
     - Test: "List the workplans for the projects"
     - Expected: Show epic → story → task hierarchies
     - Test: "Show me the backlog for project 1"
     - Test: "Display roadmap"
   - **ISSUE-003 Validation** (natural questions):
     - Test: "What's next for the tetris game development"
     - Expected: Informational response with next tasks (not "Invalid command")
     - Test: "How's project 1 going?"
     - Test: "Any blockers for epic 3?"
   - **Additional scenarios** (20+ diverse commands):
     - Mix of CREATE, UPDATE, DELETE, QUERY operations
     - Different entity types (project, epic, story, task, milestone)
     - Edge cases (ambiguous names, multiple matches)
   - **Acceptance**: 95%+ accuracy on 30+ manual commands, all 3 issues resolved

4. **Performance Testing** (2 hours, Day 9)
   - Measure latency per stage:
     - IntentClassifier: <200ms
     - OperationClassifier: <150ms
     - EntityTypeClassifier: <150ms
     - EntityIdentifierExtractor: <150ms
     - ParameterExtractor: <150ms
     - CommandValidator: <50ms
     - CommandExecutor: <100ms
     - Total: <1000ms (1 second) per command
   - Measure throughput: 50+ commands/minute
   - Measure memory usage: <200MB additional
   - **Acceptance**: End-to-end latency <1.5 seconds (P95), no performance regressions

**Story Acceptance Criteria**:
- ✅ 165 unit tests passing (100% pass rate)
- ✅ 130 integration tests passing (100% pass rate)
- ✅ All 103 existing NL tests pass (no regressions)
- ✅ 95%+ accuracy on 30+ manual test commands
- ✅ ISSUE-001, ISSUE-002, ISSUE-003 all resolved and verified
- ✅ Performance benchmarks met (latency <1.5s P95)
- ✅ No critical issues discovered

---

### Story 7: Documentation and Migration (1 day)
**Goal**: Complete documentation and create migration guide

#### Tasks:
1. **Update NL Command Guide** (2 hours, Day 10)
   - File: `docs/guides/NL_COMMAND_GUIDE.md`
   - Add operation type examples (CREATE, UPDATE, DELETE, QUERY)
   - Add hierarchical query examples (workplan, backlog, roadmap)
   - Add question handling examples (what's next, how's progress)
   - Update accuracy claims (95%+)
   - **Acceptance**: Guide includes all new patterns and examples

2. **Update NL Command Spec** (1 hour, Day 10)
   - File: `docs/development/NL_COMMAND_INTERFACE_SPEC.json`
   - Add operation types to schema
   - Add parameter extraction examples
   - Add question types
   - **Acceptance**: Spec is machine-readable and comprehensive

3. **Update Architecture Documentation** (1 hour, Day 10)
   - File: `docs/architecture/ARCHITECTURE.md`
   - Update NL interface architecture diagram (show 5-stage pipeline)
   - Document new components (OperationClassifier, EntityTypeClassifier, etc.)
   - Update data flow section
   - **Acceptance**: Architecture docs reflect new design

4. **Create Migration Guide** (2 hours, Day 10)
   - File: `docs/guides/ADR016_MIGRATION_GUIDE.md`
   - Document breaking changes (EntityExtractor deprecated)
   - Document new features (question handling, hierarchical queries)
   - Provide testing instructions
   - Document rollback plan (legacy pipeline via config)
   - **Acceptance**: Clear migration path for existing users

5. **Update CHANGELOG** (30 minutes, Day 10)
   - File: `CHANGELOG.md`
   - Add v1.6.0 entry with:
     - Added: NL pipeline refactor, hierarchical queries, question handling
     - Fixed: ISSUE-001, ISSUE-002, ISSUE-003
     - Changed: EntityExtractor deprecated, updated validators/executors
     - Performance: <1s latency, 95% accuracy
   - **Acceptance**: CHANGELOG entry complete and accurate

6. **Update ADR-016 Status** (30 minutes, Day 10)
   - File: `docs/decisions/ADR-016-decompose-nl-entity-extraction.md`
   - Change status: Proposed → Implemented
   - Add implementation date
   - Add actual vs. estimated effort
   - Add lessons learned
   - **Acceptance**: ADR-016 reflects implementation reality

**Story Acceptance Criteria**:
- ✅ `docs/guides/NL_COMMAND_GUIDE.md` updated with new patterns
- ✅ `docs/development/NL_COMMAND_INTERFACE_SPEC.json` updated
- ✅ `docs/architecture/ARCHITECTURE.md` updated with new architecture
- ✅ `docs/guides/ADR016_MIGRATION_GUIDE.md` created
- ✅ `CHANGELOG.md` updated for v1.6.0
- ✅ `docs/decisions/ADR-016-decompose-nl-entity-extraction.md` status = Implemented
- ✅ All documentation accurate and comprehensive

---

## Epic Acceptance Criteria

### Functional Requirements
- ✅ All 5 new components implemented (OperationClassifier, EntityTypeClassifier, EntityIdentifierExtractor, ParameterExtractor, QuestionHandler)
- ✅ All 3 existing components updated (CommandValidator, CommandExecutor, NLCommandProcessor)
- ✅ Full 5-stage pipeline works end-to-end for COMMAND path
- ✅ QUESTION path works end-to-end via QuestionHandler
- ✅ Hierarchical queries supported (WORKPLAN, BACKLOG, ROADMAP)

### Quality Requirements
- ✅ 165 unit tests passing (100% pass rate)
- ✅ 130 integration tests passing (100% pass rate)
- ✅ All 103 existing NL tests pass (no regressions)
- ✅ 95%+ accuracy on diverse manual test commands
- ✅ Test coverage ≥90% for all new components

### Issue Resolution
- ✅ ISSUE-001 (HIGH) resolved: Status updates work correctly (no longer creates tasks)
- ✅ ISSUE-002 (MEDIUM) resolved: Hierarchical queries work (workplan/backlog/roadmap)
- ✅ ISSUE-003 (MEDIUM) resolved: Questions answered gracefully (not rejected)

### Performance Requirements
- ✅ End-to-end latency <1.5 seconds (P95)
- ✅ Throughput ≥50 commands/minute
- ✅ Memory overhead <200MB
- ✅ No performance regressions vs. baseline

### Documentation Requirements
- ✅ ADR-016 status updated to Implemented
- ✅ NL_COMMAND_GUIDE.md updated with new patterns
- ✅ ARCHITECTURE.md updated with new architecture
- ✅ Migration guide created (ADR016_MIGRATION_GUIDE.md)
- ✅ CHANGELOG.md updated for v1.6.0
- ✅ All new code documented with docstrings and type hints

---

## Dependencies

**Prerequisites**:
- ADR-016 approved
- StateManager API stable
- Ollama/Qwen available (local LLM)

**Blockers**: None identified

**Follow-up Work** (v1.7.0+):
- Performance optimization (reduce LLM calls via caching)
- Multi-turn context (follow-up questions)
- Advanced query patterns (filters, sorting, pagination)
- Multi-language support (Spanish, French, etc.)

---

## Timeline Summary

| Story | Duration | Days | Deliverables |
|-------|----------|------|-------------|
| Story 1: Foundation | 1 day | Day 1 | ADR-016 approved, data structures, interfaces |
| Story 2: Classifiers | 2 days | Day 2-3 | OperationClassifier, EntityTypeClassifier + 45 tests |
| Story 3: Extraction | 2 days | Day 3-4 | EntityIdentifierExtractor, ParameterExtractor + 45 tests |
| Story 4: Questions | 1 day | Day 4 | QuestionHandler + 30 tests |
| Story 5: Core Updates | 2 days | Day 6-7 | Updated Validator/Executor/Processor + 45 tests |
| Story 6: Testing | 2 days | Day 8-9 | All tests passing, issues resolved |
| Story 7: Documentation | 1 day | Day 10 | All docs updated, migration guide |
| **Total** | **10 days** | | **v1.6.0 ready** |

---

**Version**: 1.0
**Last Updated**: 2025-11-11
**Status**: Proposed (awaiting approval)
