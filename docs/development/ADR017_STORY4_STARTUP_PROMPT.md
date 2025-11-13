# ADR-017 Story 4 Startup Prompt

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 0-3 are complete. Now implement Story 4.

---

## What You're Building

**Story 4**: Update NLCommandProcessor Routing (10 hours)

**Purpose**: Update NLCommandProcessor to route write operations through IntentToTaskConverter and query operations through NLQueryHelper, preparing for unified orchestrator execution.

**Key Changes**:
- Update `NLCommandProcessor.process()` to return `ParsedIntent` instead of executing directly
- Route CREATE/UPDATE/DELETE to `IntentToTaskConverter` (Story 2)
- Route QUERY to `NLQueryHelper` (Story 3)
- Add new `ParsedIntent` dataclass
- Maintain backward compatibility for existing callers

---

## What's Already Complete

### Story 0: Testing Infrastructure ✅
- Health checks, smoke tests, integration tests
- THE CRITICAL TEST: `test_full_workflow_create_project_to_execution`

### Story 1: Architecture Documentation ✅
- ADR-017 written and approved
- Architecture diagrams and design documents

### Story 2: IntentToTaskConverter ✅
- **Component**: `src/orchestration/intent_to_task_converter.py`
- **Function**: Converts `OperationContext` → `Task` objects
- **Tests**: 32 tests, 93% coverage
- **Operations**: CREATE, UPDATE, DELETE (QUERY raises exception)

### Story 3: NLQueryHelper ✅
- **Component**: `src/nl/nl_query_helper.py`
- **Function**: Query-only operations (SIMPLE/HIERARCHICAL/NEXT_STEPS/BACKLOG/ROADMAP)
- **Tests**: 17 tests, 97% coverage
- **Write protection**: Rejects CREATE/UPDATE/DELETE operations

---

## The Problem

Currently, `NLCommandProcessor.process()`:
1. Parses NL input → `OperationContext`
2. **Immediately executes** via `CommandExecutor.execute()`
3. Returns `NLResponse` with results

This bypasses orchestrator's validation pipeline for NL commands!

---

## The Solution

Update `NLCommandProcessor.process()` to:
1. Parse NL input → `OperationContext`
2. **Return ParsedIntent** (does NOT execute)
3. Caller (CLI/interactive) routes to appropriate handler:
   - **COMMAND** intent → Use `IntentToTaskConverter` + `orchestrator.execute_task()`
   - **QUESTION** intent → Handle inline (no change)

---

## Implementation Plan

### Step 1: Create ParsedIntent Dataclass

**File**: `src/nl/types.py` (add to existing file)

```python
@dataclass
class ParsedIntent:
    """Parsed intent from NL command processor (ADR-017).

    After ADR-017, NLCommandProcessor returns ParsedIntent instead of
    executing commands. This enables routing through orchestrator for
    validation and quality control.

    Attributes:
        intent_type: "COMMAND" or "QUESTION"
        operation_context: OperationContext for COMMAND intents
        original_message: User's original NL input
        confidence: Aggregate confidence from pipeline stages
        requires_execution: True for COMMAND, False for QUESTION
        question_context: Context for QUESTION intents
        metadata: Additional metadata (classification scores, etc.)
    """
    intent_type: str  # "COMMAND" or "QUESTION"
    operation_context: Optional[OperationContext]
    original_message: str
    confidence: float
    requires_execution: bool
    question_context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_command(self) -> bool:
        """Check if this is a COMMAND intent."""
        return self.intent_type == "COMMAND"

    def is_question(self) -> bool:
        """Check if this is a QUESTION intent."""
        return self.intent_type == "QUESTION"
```

### Step 2: Update NLCommandProcessor.process() Signature

**File**: `src/nl/nl_command_processor.py`

**OLD Signature**:
```python
def process(self, message: str, context: Dict[str, Any]) -> NLResponse:
    """Process NL message and return response."""
    # 5-stage pipeline → execute → return NLResponse
```

**NEW Signature**:
```python
def process(self, message: str, context: Dict[str, Any]) -> ParsedIntent:
    """Process NL message and return parsed intent (ADR-017).

    After ADR-017, this method returns ParsedIntent instead of executing.
    Caller routes to orchestrator for execution.

    Args:
        message: User's natural language message
        context: Context dict (project_id, user_id, etc.)

    Returns:
        ParsedIntent with operation_context for COMMAND or question_context for QUESTION
    """
    # 5-stage pipeline → validation → return ParsedIntent (NO EXECUTION)
```

### Step 3: Refactor NLCommandProcessor Internals

**Current Flow** (executes inline):
```python
def process(self, message: str, context: Dict[str, Any]) -> NLResponse:
    # Stage 1: Intent classification
    intent_result = self.intent_classifier.classify(message)

    if intent_result.intent == "QUESTION":
        return self._handle_question(message)

    # Stage 2-5: Entity extraction, validation
    operation_context = self._extract_and_validate(message)

    # EXECUTE (this is the problem!)
    execution_result = self.command_executor.execute(operation_context)

    # Format response
    return self.response_formatter.format(execution_result)
```

**NEW Flow** (returns ParsedIntent):
```python
def process(self, message: str, context: Dict[str, Any]) -> ParsedIntent:
    # Stage 1: Intent classification
    intent_result = self.intent_classifier.classify(message)

    if intent_result.intent == "QUESTION":
        return ParsedIntent(
            intent_type="QUESTION",
            operation_context=None,
            original_message=message,
            confidence=intent_result.confidence,
            requires_execution=False,
            question_context=self._build_question_context(message)
        )

    # Stage 2-5: Entity extraction, validation
    operation_context = self._extract_and_validate(message)

    # Return ParsedIntent (NO EXECUTION!)
    return ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message=message,
        confidence=operation_context.confidence,
        requires_execution=True,
        metadata={
            'intent_confidence': intent_result.confidence,
            'entity_confidence': operation_context.confidence,
            'operation': str(operation_context.operation),
            'entity_type': str(operation_context.entity_type)
        }
    )
```

### Step 4: Add Helper Method for Question Context

```python
def _build_question_context(self, message: str) -> Dict[str, Any]:
    """Build context for QUESTION intents.

    Args:
        message: User's question

    Returns:
        Dict with question context (type, keywords, etc.)
    """
    return {
        'question': message,
        'question_type': 'informational',  # Could classify further
        'requires_query': False,
        'suggested_response': self._generate_question_response(message)
    }
```

### Step 5: Maintain Backward Compatibility

Add a **deprecated** method for existing callers:

```python
@deprecated(version='1.8.0', reason="Use process() which returns ParsedIntent")
def process_and_execute(
    self,
    message: str,
    context: Dict[str, Any]
) -> NLResponse:
    """Process and execute NL message (DEPRECATED).

    This method maintains backward compatibility with pre-ADR-017 code.
    New code should use process() and route through orchestrator.

    Args:
        message: Natural language message
        context: Context dict

    Returns:
        NLResponse with execution results
    """
    warnings.warn(
        "process_and_execute() is deprecated. Use process() and route to orchestrator.",
        DeprecationWarning,
        stacklevel=2
    )

    # Parse intent
    parsed_intent = self.process(message, context)

    if parsed_intent.is_question():
        # Handle question inline
        return NLResponse(
            success=True,
            message=parsed_intent.question_context['suggested_response'],
            data={}
        )

    # Execute command (old way)
    if parsed_intent.operation_context.operation == OperationType.QUERY:
        # Use NLQueryHelper
        result = self.query_helper.execute(
            parsed_intent.operation_context,
            project_id=context.get('project_id', 1)
        )
    else:
        # Use CommandExecutor (old way - will be deprecated)
        result = self.command_executor.execute(
            parsed_intent.operation_context,
            project_id=context.get('project_id', 1)
        )

    # Format and return
    return self.response_formatter.format(result)
```

---

## Test Updates

### Update Existing Tests

**File**: `tests/nl/test_nl_command_processor_integration.py`

**Update ~40 tests** to expect `ParsedIntent` instead of `NLResponse`:

**OLD Test**:
```python
def test_create_epic_command(self, processor):
    """Test CREATE epic via NL."""
    response = processor.process("create epic for user auth")

    assert response.success is True
    assert response.data['entity_type'] == 'epic'
    assert 'created_ids' in response.data
```

**NEW Test**:
```python
def test_create_epic_command(self, processor):
    """Test CREATE epic NL parsing (returns ParsedIntent)."""
    parsed_intent = processor.process("create epic for user auth")

    # Verify ParsedIntent structure
    assert parsed_intent.is_command()
    assert parsed_intent.requires_execution is True
    assert parsed_intent.operation_context is not None
    assert parsed_intent.operation_context.operation == OperationType.CREATE
    assert parsed_intent.operation_context.entity_type == EntityType.EPIC
    assert parsed_intent.confidence > 0.8

    # NOTE: Execution happens elsewhere (orchestrator), not here!
```

### Add New Tests

**Category 1**: ParsedIntent Structure (8 tests)
- `test_parsed_intent_command_structure`
- `test_parsed_intent_question_structure`
- `test_parsed_intent_is_command_helper`
- `test_parsed_intent_is_question_helper`
- `test_parsed_intent_confidence_included`
- `test_parsed_intent_metadata_included`
- `test_parsed_intent_original_message_preserved`
- `test_parsed_intent_operation_context_complete`

**Category 2**: Routing Logic (6 tests)
- `test_command_intent_returns_operation_context`
- `test_question_intent_returns_question_context`
- `test_query_command_includes_query_type`
- `test_create_command_includes_parameters`
- `test_update_command_includes_identifier`
- `test_delete_command_includes_identifier`

**Category 3**: Backward Compatibility (4 tests)
- `test_process_and_execute_deprecation_warning`
- `test_process_and_execute_still_works`
- `test_process_and_execute_handles_questions`
- `test_process_and_execute_handles_queries`

**Total new tests**: 18
**Total updated tests**: ~40
**Total tests**: ~58

---

## Integration Points

### Files to Update

1. **`src/nl/types.py`**: Add `ParsedIntent` dataclass
2. **`src/nl/nl_command_processor.py`**: Update `process()` signature and logic
3. **`tests/nl/test_nl_command_processor_integration.py`**: Update ~40 tests
4. **`src/nl/__init__.py`**: Export `ParsedIntent`

### Files NOT Updated (Yet)

These will be updated in Story 5:
- **`src/cli.py`**: Will route ParsedIntent to orchestrator
- **`src/orchestrator.py`**: Will accept ParsedIntent and route to IntentToTaskConverter
- **Interactive mode handlers**: Will use new routing

---

## Acceptance Criteria

✅ **Implementation**:
- [ ] `ParsedIntent` dataclass created in `src/nl/types.py`
- [ ] `NLCommandProcessor.process()` returns `ParsedIntent` (not `NLResponse`)
- [ ] COMMAND intents include `OperationContext`
- [ ] QUESTION intents include `question_context`
- [ ] `requires_execution` flag set correctly
- [ ] Confidence scores tracked in metadata

✅ **Backward Compatibility**:
- [ ] `process_and_execute()` method added with deprecation warning
- [ ] Existing callers can still use old API (with warning)
- [ ] No breaking changes in v1.7.0

✅ **Tests**:
- [ ] ~40 existing tests updated for new API
- [ ] 18+ new tests for ParsedIntent structure and routing
- [ ] ~58 total tests passing
- [ ] Code coverage ≥90%

✅ **Integration**:
- [ ] `ParsedIntent` exported from `src.nl` module
- [ ] No smoke test failures
- [ ] LLM integration tests passing

---

## Validation Commands

**After Story 4 complete**:
```bash
# Run NL command processor tests
pytest tests/nl/test_nl_command_processor_integration.py -v

# Run all NL smoke tests
pytest tests/smoke/ -v -k "nl_"

# Run LLM integration tests
pytest tests/integration/test_llm_connectivity.py -v

# Verify no regressions
pytest tests/nl/ -v --cov=src/nl
```

**Expected Results**:
- All NL tests passing (~58 tests)
- All smoke tests passing (10/10)
- Coverage ≥90% on `nl_command_processor.py`

---

## Key Design Decisions

### Decision 1: Why Return ParsedIntent?

**Before ADR-017** (direct execution):
```
User → NLCommandProcessor → CommandExecutor → StateManager → Response
```
❌ Bypasses orchestrator validation!

**After ADR-017** (unified execution):
```
User → NLCommandProcessor → ParsedIntent → Orchestrator → Validation → Agent → Response
```
✅ All commands go through orchestrator!

### Decision 2: Why Keep process_and_execute()?

- **Backward compatibility**: Existing code still works
- **Gradual migration**: Can migrate callers incrementally
- **Deprecation path**: Will remove in v1.8.0 (6 months)

### Decision 3: How to Handle Questions?

Questions continue to be handled inline (no orchestrator needed):
- Informational queries don't need validation
- Fast response time (no orchestration overhead)
- Simple implementation

---

## Example Usage

### Before ADR-017 (Story 4)
```python
# OLD: Direct execution
processor = NLCommandProcessor(state_manager, ...)
response = processor.process("create epic for user auth")

if response.success:
    print(f"Created epic {response.data['entity_id']}")
```

### After ADR-017 (Story 4)
```python
# NEW: Returns ParsedIntent
processor = NLCommandProcessor(state_manager, ...)
parsed_intent = processor.process("create epic for user auth")

if parsed_intent.is_command():
    # Route to orchestrator (Story 5)
    task = intent_to_task_converter.convert(
        parsed_intent.operation_context,
        project_id=1,
        original_message=parsed_intent.original_message
    )

    # Execute via orchestrator
    orchestrator.execute_task(task.id)
```

---

## Common Pitfalls to Avoid

1. ❌ **Don't execute in process()**: Return ParsedIntent, don't execute!
2. ❌ **Don't break existing callers**: Add `process_and_execute()` for compatibility
3. ❌ **Don't forget confidence scores**: Track in ParsedIntent.metadata
4. ❌ **Don't skip question handling**: Questions still work inline
5. ❌ **Don't forget tests**: Update all ~40 existing tests

---

## References

**Key Files**:
- `src/nl/nl_command_processor.py` - Main file to modify
- `src/nl/types.py` - Add ParsedIntent here
- `src/orchestration/intent_to_task_converter.py` - Will consume ParsedIntent (Story 5)
- `src/nl/nl_query_helper.py` - For query operations

**Documentation**:
- `docs/development/ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml` - Full plan
- `docs/development/ADR017_STORY2_STARTUP_PROMPT.md` - IntentToTaskConverter reference
- `docs/development/ADR017_STORY3_STARTUP_PROMPT.md` - NLQueryHelper reference

**Tests**:
- `tests/nl/test_nl_command_processor_integration.py` - Tests to update
- `tests/smoke/test_smoke_workflows.py` - Smoke tests to verify

---

## Upon Completion of Story 4

**IMPORTANT**: When you finish Story 4, you MUST generate the startup prompt for Story 5.

Create the file: `docs/development/ADR017_STORY5_STARTUP_PROMPT.md`

**Story 5 Summary**:
- **Name**: Implement Unified Orchestrator Routing
- **Duration**: 12 hours
- **Dependencies**: Stories 0, 2, 3, 4
- **Purpose**: Update orchestrator to accept ParsedIntent and route to IntentToTaskConverter

**Story 5 Key Changes**:
- Add `orchestrator.execute_nl_command(parsed_intent)` method
- Route CREATE/UPDATE/DELETE through IntentToTaskConverter
- Apply full validation pipeline to NL commands
- Update CLI to use new routing
- Update interactive mode to use new routing

**Include in Story 5 Prompt**:
1. Complete context (Stories 0-4 summary)
2. Implementation plan for orchestrator routing
3. CLI integration changes
4. Interactive mode changes
5. Test plan (integration tests)
6. Validation commands
7. Acceptance criteria

---

**Ready to start? Implement Story 4: Update NLCommandProcessor Routing.**

Remember:
- Parse intent → Return ParsedIntent (NO execution!)
- Maintain backward compatibility
- Update all tests
- Generate Story 5 prompt when done!
