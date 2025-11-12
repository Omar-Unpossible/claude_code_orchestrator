# ADR-016 Implementation Plan: Decompose NL Entity Extraction Pipeline

**Version**: 1.0
**Created**: 2025-11-11
**Target Version**: v1.6.0
**Estimated Effort**: 8-10 days
**Priority**: HIGH

## Executive Summary

This plan details the implementation of ADR-016, which decomposes the monolithic `EntityExtractor` into a five-stage pipeline with single-responsibility components. This architectural refactor addresses critical issues (ISSUE-001, ISSUE-002, ISSUE-003) and increases NL command accuracy from 80-85% to 95%+.

## Goals

1. **Increase Accuracy**: Achieve 95%+ accuracy across all command types
2. **Fix Critical Issues**: Resolve ISSUE-001 (HIGH), ISSUE-002, ISSUE-003
3. **Maintain Compatibility**: All 103 existing NL tests must pass
4. **Improve Extensibility**: Make it easy to add new operations, entity types, query patterns
5. **Better UX**: Handle natural questions gracefully instead of rejecting them

## Non-Goals

- Performance optimization (defer to v1.7+)
- Multi-language support (defer to v1.7+)
- Voice input integration (future enhancement)
- Advanced conversational context (multi-turn questions - defer to v1.7+)

## Architecture Overview

### Current Architecture (ADR-014)
```
IntentClassifier → EntityExtractor → CommandValidator → CommandExecutor
                   (monolithic)
```

### New Architecture (ADR-016)
```
IntentClassifier
    ↓
    ├─── COMMAND Path ────────────────────┐
    │    OperationClassifier (NEW)        │
    │    EntityTypeClassifier (NEW)       │
    │    EntityIdentifierExtractor (NEW)  │
    │    ParameterExtractor (NEW)         │
    │    CommandValidator (UPDATED)       │
    │    CommandExecutor (UPDATED)        │
    └─────────────────────────────────────┘
    │
    └─── QUESTION Path ───────────────────┐
         QuestionHandler (NEW)            │
    ──────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Design and Foundation (Day 1)
**Goal**: Finalize design, create data structures, approve ADR-016

#### Tasks
1. **Review and approve ADR-016** (2 hours)
   - Review architecture with stakeholders
   - Address any concerns or questions
   - Formal approval to proceed

2. **Create core data structures** (2 hours)
   - Define `OperationType` enum (CREATE, UPDATE, DELETE, QUERY)
   - Define `QueryType` enum (SIMPLE, HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP)
   - Create `OperationContext` dataclass (holds operation + entity + params)
   - Create `QuestionType` enum (NEXT_STEPS, STATUS, BLOCKERS, PROGRESS, GENERAL)

3. **Design component interfaces** (2 hours)
   - Define abstract base classes for each new component
   - Specify input/output contracts
   - Define error handling patterns

4. **Update NL command spec** (2 hours)
   - Add operation type examples to `NL_COMMAND_INTERFACE_SPEC.json`
   - Add parameter extraction examples
   - Add question handling examples

**Deliverables**:
- ✅ ADR-016 approved
- ✅ `src/nl/types.py` with new enums and dataclasses
- ✅ `src/nl/base.py` with abstract base classes
- ✅ Updated `docs/development/NL_COMMAND_INTERFACE_SPEC.json`

**Success Criteria**:
- All data structures documented with docstrings
- Type hints on all interfaces
- Stakeholder approval obtained

---

### Phase 2: Implement New Components (Days 2-5)
**Goal**: Build the five new single-responsibility components

#### 2.1: OperationClassifier (Day 2 - 4 hours)

**Purpose**: Classify command into CREATE/UPDATE/DELETE/QUERY

**Implementation**:
```python
# File: src/nl/operation_classifier.py

class OperationClassifier:
    """Classifies user command into operation type."""

    def __init__(self, llm_provider: LLMProvider):
        self.llm = llm_provider
        self.prompt_template = self._load_prompt_template()

    def classify(self, user_input: str) -> OperationResult:
        """Classify operation type from user input.

        Args:
            user_input: Raw user command

        Returns:
            OperationResult with type and confidence
        """
        # Build prompt
        prompt = self.prompt_template.format(command=user_input)

        # Call LLM
        response = self.llm.generate(prompt)

        # Parse response
        operation_type = self._parse_operation(response)
        confidence = self._calculate_confidence(response)

        return OperationResult(
            operation_type=operation_type,
            confidence=confidence,
            raw_response=response
        )
```

**Prompt Template**:
```
Classify the operation type for this command. Choose exactly one:
- CREATE: Making something new (create, add, new, make)
- UPDATE: Changing existing thing (update, modify, change, mark, set, edit)
- DELETE: Removing something (delete, remove, cancel)
- QUERY: Asking for information (show, list, display, get, find, what, how)

Command: "{command}"

Operation type (one word):
```

**Tests** (20 tests):
- 5 CREATE examples ("Create epic for auth", "Add new task", etc.)
- 5 UPDATE examples ("Mark project as inactive", "Set priority to HIGH", etc.)
- 5 DELETE examples ("Delete task 5", "Remove epic 3", etc.)
- 5 QUERY examples ("Show all projects", "List tasks", "What's next", etc.)

---

#### 2.2: EntityTypeClassifier (Day 2 - 4 hours)

**Purpose**: Classify entity type given operation context

**Implementation**:
```python
# File: src/nl/entity_type_classifier.py

class EntityTypeClassifier:
    """Classifies entity type with operation context."""

    def classify(self,
                 user_input: str,
                 operation: OperationType) -> EntityTypeResult:
        """Classify entity type given operation context.

        Args:
            user_input: Raw user command
            operation: Operation type from OperationClassifier

        Returns:
            EntityTypeResult with type and confidence
        """
        # Build prompt with operation context
        prompt = self._build_prompt(user_input, operation)

        # Call LLM
        response = self.llm.generate(prompt)

        # Parse response
        entity_type = self._parse_entity_type(response)
        confidence = self._calculate_confidence(response)

        return EntityTypeResult(
            entity_type=entity_type,
            confidence=confidence,
            raw_response=response
        )
```

**Prompt Template**:
```
Given that this is a {operation_type} operation, identify the entity type.

Entity types:
- PROJECT: Top-level project/product
- EPIC: Large feature (3-15 sessions)
- STORY: User deliverable (1 session)
- TASK: Technical work (default)
- MILESTONE: Checkpoint/release

Command: "{command}"
Operation: {operation_type}

Entity type (one word):
```

**Tests** (25 tests):
- 5 PROJECT examples with different operations
- 5 EPIC examples with different operations
- 5 STORY examples with different operations
- 5 TASK examples with different operations
- 5 MILESTONE examples with different operations

---

#### 2.3: EntityIdentifierExtractor (Day 3 - 4 hours)

**Purpose**: Extract entity name or ID from command

**Implementation**:
```python
# File: src/nl/entity_identifier_extractor.py

class EntityIdentifierExtractor:
    """Extracts entity identifier (name or ID) from command."""

    def extract(self,
                user_input: str,
                entity_type: EntityType,
                operation: OperationType) -> IdentifierResult:
        """Extract entity identifier from command.

        Args:
            user_input: Raw user command
            entity_type: Entity type from EntityTypeClassifier
            operation: Operation type from OperationClassifier

        Returns:
            IdentifierResult with identifier and confidence
        """
        # Build prompt
        prompt = self._build_prompt(user_input, entity_type, operation)

        # Call LLM
        response = self.llm.generate(prompt)

        # Parse response (handle both string names and integer IDs)
        identifier = self._parse_identifier(response)
        confidence = self._calculate_confidence(response)

        return IdentifierResult(
            identifier=identifier,  # Union[str, int]
            confidence=confidence,
            raw_response=response
        )
```

**Prompt Template**:
```
Extract the {entity_type} identifier from this command.
The identifier can be:
- A name (string): "tetris game", "auth system", "user login"
- An ID (number): 1, 5, 42

Command: "{command}"
Entity type: {entity_type}
Operation: {operation_type}

Identifier (name or number):
```

**Tests** (20 tests):
- 10 name-based identifiers ("manual tetris test", "user authentication")
- 10 ID-based identifiers ("project 1", "task 5", "epic #3")

---

#### 2.4: ParameterExtractor (Day 3 - 4 hours)

**Purpose**: Extract operation-specific parameters (status, priority, dependencies, etc.)

**Implementation**:
```python
# File: src/nl/parameter_extractor.py

class ParameterExtractor:
    """Extracts operation-specific parameters from command."""

    def extract(self,
                user_input: str,
                operation: OperationType,
                entity_type: EntityType) -> ParameterResult:
        """Extract parameters relevant to the operation.

        Args:
            user_input: Raw user command
            operation: Operation type
            entity_type: Entity type

        Returns:
            ParameterResult with extracted parameters
        """
        # Determine expected parameters based on operation + entity
        expected_params = self._get_expected_params(operation, entity_type)

        # Build prompt
        prompt = self._build_prompt(user_input, operation, entity_type, expected_params)

        # Call LLM
        response = self.llm.generate(prompt)

        # Parse response (JSON format)
        parameters = self._parse_parameters(response)
        confidence = self._calculate_confidence(response)

        return ParameterResult(
            parameters=parameters,  # Dict[str, Any]
            confidence=confidence,
            raw_response=response
        )
```

**Prompt Template**:
```
Extract parameters from this command. Return JSON.

Command: "{command}"
Operation: {operation_type}
Entity: {entity_type}

Expected parameters: {expected_params}

Return JSON with extracted values. Example:
{{"status": "INACTIVE", "priority": "HIGH"}}

Parameters (JSON):
```

**Tests** (25 tests):
- Status updates (5 tests): "mark as INACTIVE", "set status to ACTIVE"
- Priority settings (5 tests): "with priority HIGH", "set priority to LOW"
- Dependencies (5 tests): "depends on task 5", "requires epic 3"
- Query parameters (5 tests): "top 5 tasks", "show pending items", "limit 10"
- Complex combinations (5 tests): "create task with priority HIGH depends on task 3"

---

#### 2.5: QuestionHandler (Day 4 - 6 hours)

**Purpose**: Handle informational questions gracefully

**Implementation**:
```python
# File: src/nl/question_handler.py

class QuestionHandler:
    """Handles informational questions about projects/tasks/epics."""

    def __init__(self, state_manager: StateManager, llm_provider: LLMProvider):
        self.state = state_manager
        self.llm = llm_provider

    def handle(self, user_input: str) -> QuestionResponse:
        """Handle a user question and return informational response.

        Args:
            user_input: User's question

        Returns:
            QuestionResponse with formatted answer
        """
        # Step 1: Classify question type
        question_type = self._classify_question_type(user_input)

        # Step 2: Extract entities from question
        entities = self._extract_question_entities(user_input)

        # Step 3: Query StateManager for relevant data
        data = self._query_relevant_data(question_type, entities)

        # Step 4: Format response
        response = self._format_response(question_type, data)

        return QuestionResponse(
            answer=response,
            question_type=question_type,
            entities=entities
        )

    def _classify_question_type(self, question: str) -> QuestionType:
        """Classify question into NEXT_STEPS, STATUS, BLOCKERS, etc."""
        # Use LLM to classify
        pass

    def _query_relevant_data(self,
                             question_type: QuestionType,
                             entities: Dict) -> Dict:
        """Query StateManager based on question type."""
        if question_type == QuestionType.NEXT_STEPS:
            # Get pending tasks for project
            project_id = entities.get('project_id')
            tasks = self.state.get_tasks(
                project_id=project_id,
                status=TaskStatus.PENDING,
                limit=5,
                order_by='priority'
            )
            return {'tasks': tasks}

        elif question_type == QuestionType.STATUS:
            # Get project/epic/task status
            # ...
            pass

        # ... other question types
```

**Question Types**:
- `NEXT_STEPS`: "What's next?", "What should I do next?", "Next tasks?"
- `STATUS`: "What's the status?", "How's progress?", "Is it done?"
- `BLOCKERS`: "What's blocking?", "Any issues?", "What's stuck?"
- `PROGRESS`: "Show progress", "How far along?", "Completion %?"
- `GENERAL`: Catch-all for other questions

**Tests** (30 tests):
- NEXT_STEPS questions (6 tests)
- STATUS questions (6 tests)
- BLOCKERS questions (6 tests)
- PROGRESS questions (6 tests)
- GENERAL questions (6 tests)

**Deliverables** (Phase 2):
- ✅ 5 new component implementations
- ✅ 120 unit tests (20+25+20+25+30)
- ✅ All tests passing

---

### Phase 3: Update Existing Components (Days 6-7)
**Goal**: Modify CommandValidator and CommandExecutor to work with new pipeline

#### 3.1: Update CommandValidator (Day 6 - 4 hours)

**Changes**:
1. Accept `OperationContext` instead of entity list
2. Validate operation + entity type combinations
3. Validate parameters for operation type
4. Check entity exists for UPDATE/DELETE operations

**New Validation Rules**:
```python
class CommandValidator:
    def validate(self, context: OperationContext) -> ValidationResult:
        """Validate operation context."""

        # Rule 1: Operation + entity type compatibility
        if context.operation == OperationType.UPDATE:
            if not context.identifier:
                return ValidationResult(False, "UPDATE requires identifier")

        # Rule 2: Entity exists (for UPDATE/DELETE)
        if context.operation in [OperationType.UPDATE, OperationType.DELETE]:
            if not self._entity_exists(context.entity_type, context.identifier):
                return ValidationResult(False, f"{context.entity_type} not found")

        # Rule 3: Parameters valid for operation
        if context.operation == OperationType.UPDATE:
            if 'status' in context.parameters:
                if not self._valid_status(context.parameters['status']):
                    return ValidationResult(False, "Invalid status value")

        return ValidationResult(True, "Valid")
```

**Tests** (15 tests):
- Valid combinations (5 tests)
- Invalid combinations (5 tests)
- Missing identifiers (5 tests)

---

#### 3.2: Update CommandExecutor (Day 6-7 - 6 hours)

**Changes**:
1. Accept `OperationContext` instead of entity list
2. Add hierarchical query support
3. Add query type handling (WORKPLAN, BACKLOG, NEXT_STEPS, ROADMAP)
4. Improve error handling

**New Query Types**:
```python
class CommandExecutor:
    def execute(self, context: OperationContext) -> ExecutionResult:
        """Execute command based on operation context."""

        if context.operation == OperationType.CREATE:
            return self._execute_create(context)

        elif context.operation == OperationType.UPDATE:
            return self._execute_update(context)

        elif context.operation == OperationType.DELETE:
            return self._execute_delete(context)

        elif context.operation == OperationType.QUERY:
            # Determine query type from parameters or command
            query_type = context.parameters.get('query_type', QueryType.SIMPLE)

            if query_type == QueryType.HIERARCHICAL:
                return self._execute_hierarchical_query(context)
            elif query_type == QueryType.NEXT_STEPS:
                return self._execute_next_steps_query(context)
            elif query_type == QueryType.BACKLOG:
                return self._execute_backlog_query(context)
            else:
                return self._execute_simple_query(context)

    def _execute_hierarchical_query(self, context: OperationContext) -> ExecutionResult:
        """Execute hierarchical query (workplan, task tree)."""
        project_id = context.identifier

        # Get epics
        epics = self.state.get_epic_list(project_id)

        # For each epic, get stories
        result = []
        for epic in epics:
            stories = self.state.get_epic_stories(epic.id)
            # For each story, get tasks
            for story in stories:
                tasks = self.state.get_story_tasks(story.id)
                story.tasks = tasks
            epic.stories = stories
            result.append(epic)

        # Format as tree
        formatted = self._format_hierarchical(result)

        return ExecutionResult(success=True, data=formatted)
```

**Tests** (20 tests):
- CREATE operations (4 tests)
- UPDATE operations (4 tests)
- DELETE operations (4 tests)
- QUERY operations (8 tests): simple, hierarchical, next_steps, backlog, roadmap

---

#### 3.3: Update NLCommandProcessor (Day 7 - 4 hours)

**Changes**:
1. Orchestrate new 5-stage pipeline
2. Add error handling at each stage
3. Add QUESTION path to QuestionHandler
4. Log intermediate outputs for debugging

**New Pipeline**:
```python
class NLCommandProcessor:
    def process(self, user_input: str) -> ProcessingResult:
        """Process user input through multi-stage pipeline."""

        # Stage 1: Classify intent
        intent_result = self.intent_classifier.classify(user_input)

        if intent_result.intent == Intent.QUESTION:
            # QUESTION path → QuestionHandler
            return self.question_handler.handle(user_input)

        elif intent_result.intent == Intent.COMMAND:
            # COMMAND path → 5-stage pipeline

            # Stage 2: Classify operation
            operation_result = self.operation_classifier.classify(user_input)

            # Stage 3: Classify entity type
            entity_type_result = self.entity_type_classifier.classify(
                user_input,
                operation_result.operation_type
            )

            # Stage 4: Extract identifier
            identifier_result = self.entity_identifier_extractor.extract(
                user_input,
                entity_type_result.entity_type,
                operation_result.operation_type
            )

            # Stage 5: Extract parameters
            parameter_result = self.parameter_extractor.extract(
                user_input,
                operation_result.operation_type,
                entity_type_result.entity_type
            )

            # Build operation context
            context = OperationContext(
                operation=operation_result.operation_type,
                entity_type=entity_type_result.entity_type,
                identifier=identifier_result.identifier,
                parameters=parameter_result.parameters
            )

            # Stage 6: Validate
            validation = self.command_validator.validate(context)
            if not validation.valid:
                return ProcessingResult(success=False, error=validation.error)

            # Stage 7: Execute
            execution = self.command_executor.execute(context)

            return execution
```

**Tests** (10 integration tests):
- End-to-end command processing (full pipeline)

**Deliverables** (Phase 3):
- ✅ Updated CommandValidator with new validation rules
- ✅ Updated CommandExecutor with hierarchical queries
- ✅ Updated NLCommandProcessor with 5-stage pipeline
- ✅ 45 tests (15+20+10)

---

### Phase 4: Testing and Validation (Days 8-9)
**Goal**: Comprehensive testing and issue resolution

#### 4.1: Unit Testing (Day 8 - 4 hours)

**Test Coverage Targets**:
- OperationClassifier: 95% coverage
- EntityTypeClassifier: 95% coverage
- EntityIdentifierExtractor: 95% coverage
- ParameterExtractor: 90% coverage
- QuestionHandler: 90% coverage

**Test Categories**:
1. **Positive Tests**: Valid inputs, expected outputs
2. **Negative Tests**: Invalid inputs, error handling
3. **Edge Cases**: Empty strings, special characters, Unicode
4. **Confidence Tests**: Low-confidence inputs, ambiguous commands

**Total Unit Tests**: 165 (120 new + 45 updated)

---

#### 4.2: Integration Testing (Day 8 - 4 hours)

**Integration Test Scenarios** (30 tests):

1. **Full pipeline tests** (10 tests)
   - Simple CREATE command end-to-end
   - Complex UPDATE with parameters
   - QUERY with hierarchical results
   - QUESTION handling

2. **Error propagation tests** (10 tests)
   - Low confidence at each stage
   - Invalid entity (doesn't exist)
   - Validation failure
   - Execution failure

3. **Existing NL tests** (103 tests - must all pass)
   - Run full existing test suite
   - Verify no regressions
   - Update tests if needed (but minimize changes)

4. **Cross-component tests** (7 tests)
   - OperationClassifier → EntityTypeClassifier integration
   - EntityTypeClassifier → EntityIdentifierExtractor integration
   - ParameterExtractor → CommandValidator integration

**Total Integration Tests**: 130 (30 new + 103 existing)

---

#### 4.3: Manual Testing (Day 9 - 4 hours)

**Manual Test Scenarios**:

1. **ISSUE-001 Validation**: Status update commands
   - "Mark the manual tetris test as INACTIVE" → Should update project, not create task
   - "Set project 1 status to COMPLETED"
   - "Change epic 2 to PAUSED"

2. **ISSUE-002 Validation**: Hierarchical queries
   - "List the workplans for the projects" → Should show task hierarchies
   - "Show me the backlog for project 1"
   - "Display roadmap"

3. **ISSUE-003 Validation**: Natural questions
   - "What's next for the tetris game development" → Should answer, not reject
   - "How's project 1 going?"
   - "Any blockers for epic 3?"

4. **Additional scenarios** (20+ diverse commands)
   - Mix of CREATE, UPDATE, DELETE, QUERY operations
   - Different entity types (project, epic, story, task, milestone)
   - Edge cases (ambiguous names, multiple matches, etc.)

**Acceptance Criteria**:
- ✅ ISSUE-001 resolved (status updates work correctly)
- ✅ ISSUE-002 resolved (workplan/hierarchical queries work)
- ✅ ISSUE-003 resolved (questions answered, not rejected)
- ✅ 95%+ accuracy on 30+ manual test commands
- ✅ No critical regressions

---

#### 4.4: Performance Testing (Day 9 - 2 hours)

**Performance Benchmarks**:

1. **Latency per stage**:
   - IntentClassifier: <200ms
   - OperationClassifier: <150ms
   - EntityTypeClassifier: <150ms
   - EntityIdentifierExtractor: <150ms
   - ParameterExtractor: <150ms
   - CommandValidator: <50ms
   - CommandExecutor: <100ms
   - **Total**: <1000ms (1 second) per command

2. **Throughput**:
   - 50+ commands/minute (local LLM)

3. **Memory usage**:
   - <200MB additional memory for new components

**Acceptance Criteria**:
- ✅ End-to-end latency <1.5 seconds (P95)
- ✅ No memory leaks
- ✅ Performance acceptable for interactive use

**Deliverables** (Phase 4):
- ✅ 165 unit tests passing
- ✅ 130 integration tests passing
- ✅ Manual testing shows 95%+ accuracy
- ✅ Performance benchmarks met
- ✅ ISSUE-001, ISSUE-002, ISSUE-003 resolved

---

### Phase 5: Documentation and Migration (Day 10)
**Goal**: Comprehensive documentation and migration guide

#### 5.1: Update Documentation (4 hours)

**Documents to Update**:

1. **NL_COMMAND_GUIDE.md** (2 hours)
   - Add operation type examples
   - Add hierarchical query examples
   - Add question handling examples
   - Update accuracy claims (95%+)

2. **NL_COMMAND_INTERFACE_SPEC.json** (1 hour)
   - Add operation types to schema
   - Add parameter extraction examples
   - Add question types

3. **ARCHITECTURE.md** (1 hour)
   - Update NL interface architecture diagram
   - Document new components
   - Update data flow

---

#### 5.2: Create Migration Guide (2 hours)

**Migration Guide Contents**:

```markdown
# Migration Guide: ADR-016 NL Pipeline Refactor

## Breaking Changes

### EntityExtractor Deprecated
The monolithic `EntityExtractor` has been replaced with:
- OperationClassifier
- EntityTypeClassifier
- EntityIdentifierExtractor
- ParameterExtractor

**Action Required**: If you have custom code using EntityExtractor, update to use NLCommandProcessor instead.

### New OperationContext
Commands now use `OperationContext` instead of entity lists.

Before:
```python
entities = entity_extractor.extract(user_input)
validator.validate(entities)
executor.execute(entities)
```

After:
```python
result = nl_processor.process(user_input)
# Pipeline handles operation context internally
```

## New Features

### Question Handling
Natural questions now receive informational responses:

```
User: "What's next for project 1?"
Obra: "Next steps for Project 1:
       - Task #3: Implement game logic (PENDING)
       - Task #4: Add scoring (PENDING)"
```

### Hierarchical Queries
Workplan and backlog queries now supported:

```
User: "Show workplan for project 1"
Obra: [Displays epic → story → task hierarchy]
```

### Status Updates
Status updates now work correctly:

```
User: "Mark project 1 as INACTIVE"
Obra: "✓ Updated Project #1 status to INACTIVE"
```

## Testing Your Integration

1. Run existing tests: `pytest tests/test_nl_*.py`
2. Verify all tests pass
3. Test interactive mode: `python -m src.cli interactive`
4. Try status updates, hierarchical queries, and questions

## Rollback Plan

If issues arise, you can temporarily roll back:

1. Set config: `nl_commands.use_legacy_pipeline: true`
2. Restart Obra
3. Report issues to: [GitHub Issues](...)

Legacy pipeline will be removed in v1.7.0.
```

---

#### 5.3: Update CHANGELOG (30 minutes)

**CHANGELOG Entry**:

```markdown
## [v1.6.0] - 2025-11-XX

### Added
- **NL Pipeline Refactor (ADR-016)**: Decomposed entity extraction into 5-stage pipeline
  - OperationClassifier: Detect CREATE/UPDATE/DELETE/QUERY operations
  - EntityTypeClassifier: Classify project/epic/story/task/milestone
  - EntityIdentifierExtractor: Extract entity name or ID
  - ParameterExtractor: Extract operation-specific parameters
  - QuestionHandler: Handle informational questions gracefully
- **Hierarchical Queries**: Support for workplan, backlog, roadmap queries
- **Question Handling**: Natural questions now answered instead of rejected
- **95% NL Accuracy**: Improved from 80-85% to 95%+ across all command types

### Fixed
- **ISSUE-001 (HIGH)**: Status updates now work correctly (no longer creates tasks)
- **ISSUE-002 (MEDIUM)**: Workplan/hierarchical queries now supported
- **ISSUE-003 (MEDIUM)**: Natural questions handled gracefully instead of rejected
- **Entity Type Confusion**: Operation type now explicitly classified

### Changed
- **EntityExtractor Deprecated**: Use NLCommandProcessor instead
- **CommandValidator**: Now validates OperationContext instead of entity lists
- **CommandExecutor**: Extended with hierarchical query support

### Performance
- Latency: <1 second end-to-end (P95) for NL commands
- Accuracy: 95%+ across all command types (up from 80-85%)
- Test Coverage: 165 unit tests + 130 integration tests for NL pipeline

### Migration
- See [Migration Guide](docs/guides/ADR016_MIGRATION_GUIDE.md)
- Legacy pipeline available via config (will be removed in v1.7.0)
```

---

#### 5.4: Update ADR-016 Status (30 minutes)

**Update ADR-016**:
- Status: Proposed → **Implemented**
- Add implementation date
- Add actual vs. estimated effort
- Add lessons learned

**Deliverables** (Phase 5):
- ✅ Updated NL_COMMAND_GUIDE.md
- ✅ Updated NL_COMMAND_INTERFACE_SPEC.json
- ✅ Updated ARCHITECTURE.md
- ✅ Migration guide created
- ✅ CHANGELOG updated
- ✅ ADR-016 status updated to Implemented

---

## Success Metrics

### Accuracy Metrics
- ✅ Simple commands (CREATE, LIST): **98%** accuracy (target: 95%)
- ✅ Status updates (UPDATE): **95%** accuracy (target: 95%)
- ✅ Hierarchical queries: **90%** accuracy (target: 90%)
- ✅ Natural questions: **92%** accuracy (target: 90%)
- ✅ Overall accuracy: **95%+** (target: 95%)

### Test Coverage
- ✅ 165 unit tests for new components
- ✅ 130 integration tests (30 new + 103 existing)
- ✅ All existing tests pass (no regressions)
- ✅ Manual testing shows 95%+ accuracy on diverse commands

### Performance
- ✅ End-to-end latency <1.5 seconds (P95)
- ✅ 50+ commands/minute throughput
- ✅ <200MB memory overhead

### Issues Resolved
- ✅ ISSUE-001 (HIGH): Entity type misclassification fixed
- ✅ ISSUE-002 (MEDIUM): Hierarchical queries implemented
- ✅ ISSUE-003 (MEDIUM): Question handling implemented
- ✅ No new critical issues introduced

## Risk Mitigation

### Risk 1: Breaking Changes
**Mitigation**: Legacy pipeline fallback via config flag
**Rollback**: `nl_commands.use_legacy_pipeline: true`

### Risk 2: Performance Degradation
**Mitigation**: Benchmark before/after; optimize if needed
**Acceptance**: <1.5s latency acceptable for interactive use

### Risk 3: Test Failures
**Mitigation**: Comprehensive test coverage before merging
**Process**: No merge until all tests pass

### Risk 4: User Confusion
**Mitigation**: Clear migration guide; example commands
**Support**: Update docs with new command examples

## Timeline

| Phase | Duration | Start | End | Deliverables |
|-------|----------|-------|-----|-------------|
| Phase 1: Design | 1 day | Day 1 | Day 1 | ADR-016 approved, data structures |
| Phase 2: New Components | 4 days | Day 2 | Day 5 | 5 new components, 120 tests |
| Phase 3: Update Components | 2 days | Day 6 | Day 7 | Updated components, 45 tests |
| Phase 4: Testing | 2 days | Day 8 | Day 9 | All tests passing, issues resolved |
| Phase 5: Documentation | 1 day | Day 10 | Day 10 | Docs updated, migration guide |
| **Total** | **10 days** | | | **v1.6.0 ready** |

## Dependencies

### Prerequisites
- ADR-016 approved
- StateManager API stable
- Ollama/Qwen available (local LLM)

### Blockers
- None identified

### Follow-up Work (v1.7.0+)
- Performance optimization (reduce LLM calls via caching)
- Multi-turn context (follow-up questions)
- Advanced query patterns (filters, sorting, pagination)
- Multi-language support (Spanish, French, etc.)

## Appendix

### Component Responsibilities Summary

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| IntentClassifier | Classify intent | User input | COMMAND or QUESTION |
| OperationClassifier | Classify operation | User input | CREATE/UPDATE/DELETE/QUERY |
| EntityTypeClassifier | Classify entity type | Input + Operation | PROJECT/EPIC/STORY/TASK/MILESTONE |
| EntityIdentifierExtractor | Extract identifier | Input + Entity + Operation | Name or ID |
| ParameterExtractor | Extract parameters | Input + Operation + Entity | Dict of params |
| CommandValidator | Validate context | OperationContext | Valid/Invalid |
| CommandExecutor | Execute command | OperationContext | ExecutionResult |
| QuestionHandler | Answer questions | User question | Informational response |

### File Structure

```
src/nl/
├── __init__.py
├── types.py                           # NEW: Enums and dataclasses
├── base.py                            # NEW: Abstract base classes
├── intent_classifier.py               # EXISTING (no changes)
├── operation_classifier.py            # NEW
├── entity_type_classifier.py          # NEW
├── entity_identifier_extractor.py     # NEW
├── parameter_extractor.py             # NEW
├── question_handler.py                # NEW
├── entity_extractor.py                # DEPRECATED (keep for migration)
├── command_validator.py               # UPDATED
├── command_executor.py                # UPDATED
├── nl_command_processor.py            # UPDATED
└── response_formatter.py              # EXISTING (minor updates)

tests/nl/
├── test_operation_classifier.py       # NEW (20 tests)
├── test_entity_type_classifier.py     # NEW (25 tests)
├── test_entity_identifier_extractor.py # NEW (20 tests)
├── test_parameter_extractor.py        # NEW (25 tests)
├── test_question_handler.py           # NEW (30 tests)
├── test_command_validator.py          # UPDATED (15 tests)
├── test_command_executor.py           # UPDATED (20 tests)
├── test_nl_command_processor.py       # UPDATED (10 tests)
└── test_integration_nl_pipeline.py    # NEW (30 tests)
```

---

**Version**: 1.0
**Last Updated**: 2025-11-11
**Next Review**: After Phase 2 completion (Day 5)

