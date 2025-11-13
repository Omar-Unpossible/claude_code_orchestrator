# ADR-017 Story 5 Startup Prompt

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 0-4 are complete. Now implement Story 5.

---

## What You're Building

**Story 5**: Implement Unified Orchestrator Routing (12 hours)

**Purpose**: Update orchestrator to accept ParsedIntent from NLCommandProcessor and route to IntentToTaskConverter for execution, completing the unified execution architecture.

**Key Changes**:
- Add `orchestrator.execute_nl_command(parsed_intent)` method
- Route CREATE/UPDATE/DELETE through IntentToTaskConverter → execute_task()
- Route QUERY through NLQueryHelper (read-only operations)
- Update CLI to use new routing (`ParsedIntent` → orchestrator)
- Update interactive mode to use new routing
- Apply full validation pipeline to NL commands

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

### Story 4: NLCommandProcessor Routing ✅
- **Changes**: `NLCommandProcessor.process()` now returns `ParsedIntent` (not NLResponse)
- **New Type**: `ParsedIntent` dataclass with `intent_type`, `operation_context`, `requires_execution`
- **Tests**: 18 new tests for ParsedIntent structure and routing
- **Backward Compatibility**: `process_and_execute()` method (deprecated)

---

## The Problem

Currently, NL commands have two execution paths:
1. **NL Path**: User → NLCommandProcessor → CommandExecutor → StateManager (bypasses orchestrator!)
2. **CLI Path**: User → CLI → Orchestrator → Agent → StateManager (full validation)

This creates inconsistency:
- NL commands skip orchestrator validation
- No quality scoring for NL commands
- No confidence tracking for NL commands
- Different error handling paths

---

## The Solution

**Unified Execution Architecture**:
```
User Input (NL or CLI)
    ↓
NLCommandProcessor.process() → ParsedIntent
    ↓
Orchestrator.execute_nl_command(parsed_intent)
    ↓
├─ COMMAND → IntentToTaskConverter → Task → execute_task() → Full Pipeline
└─ QUESTION → Return answer (no execution needed)
```

**Benefits**:
- ALL commands go through orchestrator
- Consistent validation for NL and CLI
- Quality scoring for NL commands
- Unified error handling
- Confidence tracking for NL commands

---

## Implementation Plan

### Step 1: Add execute_nl_command() Method to Orchestrator

**File**: `src/orchestrator.py`

```python
def execute_nl_command(
    self,
    parsed_intent: ParsedIntent,
    project_id: int,
    interactive: bool = False
) -> Dict[str, Any]:
    """Execute natural language command through unified pipeline (ADR-017).

    This method routes ParsedIntent from NLCommandProcessor through the
    orchestrator's validation pipeline, ensuring consistent quality control
    for all commands (NL and CLI).

    Args:
        parsed_intent: ParsedIntent from NLCommandProcessor.process()
        project_id: Project ID for command execution
        interactive: True if running in interactive mode

    Returns:
        Dict with execution results:
        {
            'success': bool,
            'message': str,
            'task_id': Optional[int],  # For COMMAND intents
            'answer': Optional[str],   # For QUESTION intents
            'confidence': float,
            'validation_passed': bool
        }

    Raises:
        ValueError: If ParsedIntent is invalid
        OrchestratorException: If execution fails

    Example:
        >>> parsed_intent = nl_processor.process("create epic for auth")
        >>> result = orchestrator.execute_nl_command(parsed_intent, project_id=1)
        >>> print(result['message'])
        ✓ Created Epic #5: User Authentication
    """
    # 1. Validate ParsedIntent structure
    if not isinstance(parsed_intent, ParsedIntent):
        raise ValueError("Expected ParsedIntent, got {}".format(type(parsed_intent)))

    # 2. Handle QUESTION intents (no execution needed)
    if parsed_intent.is_question():
        return {
            'success': True,
            'message': parsed_intent.question_context.get('answer', 'No answer available'),
            'answer': parsed_intent.question_context.get('answer'),
            'confidence': parsed_intent.confidence,
            'task_id': None
        }

    # 3. Handle COMMAND intents (need execution)
    if parsed_intent.is_command():
        # Check if validation failed during NL processing
        if parsed_intent.metadata.get('validation_failed'):
            errors = parsed_intent.metadata.get('validation_errors', ['Validation failed'])
            return {
                'success': False,
                'message': '\n'.join(errors),
                'validation_passed': False,
                'confidence': parsed_intent.confidence,
                'task_id': None
            }

        # Check if already executed (confirmation workflow)
        if parsed_intent.metadata.get('executed'):
            return {
                'success': parsed_intent.metadata.get('execution_success', True),
                'message': parsed_intent.metadata.get('execution_response', 'Operation completed'),
                'task_id': None,  # Already executed, no new task
                'confidence': parsed_intent.confidence
            }

        # 4. Route through IntentToTaskConverter
        operation_context = parsed_intent.operation_context

        # Handle QUERY operations (read-only)
        if operation_context.operation == OperationType.QUERY:
            try:
                query_result = self.nl_query_helper.execute(
                    operation_context,
                    project_id=project_id
                )
                return {
                    'success': query_result.success,
                    'message': query_result.formatted_output,
                    'data': query_result.data,
                    'confidence': parsed_intent.confidence,
                    'task_id': None
                }
            except Exception as e:
                logger.exception(f"Query execution failed: {e}")
                return {
                    'success': False,
                    'message': f"Query failed: {str(e)}",
                    'confidence': 0.0,
                    'task_id': None
                }

        # Handle CREATE/UPDATE/DELETE operations (write operations)
        try:
            # Convert OperationContext → Task
            task = self.intent_to_task_converter.convert(
                operation_context=operation_context,
                project_id=project_id,
                original_message=parsed_intent.original_message,
                confidence=parsed_intent.confidence
            )

            # Execute task through full orchestration pipeline
            logger.info(f"Executing NL command via orchestrator: task_id={task.id}")
            execution_result = self.execute_task(task.id, interactive=interactive)

            # Format response
            return {
                'success': execution_result.get('success', False),
                'message': execution_result.get('message', 'Task execution completed'),
                'task_id': task.id,
                'confidence': parsed_intent.confidence,
                'validation_passed': True,
                'quality_score': execution_result.get('quality_score'),
                'iterations': execution_result.get('iterations', 0)
            }

        except Exception as e:
            logger.exception(f"NL command execution failed: {e}")
            return {
                'success': False,
                'message': f"Execution failed: {str(e)}",
                'confidence': 0.0,
                'task_id': None
            }

    # Fallback (should never reach here)
    return {
        'success': False,
        'message': "Unknown intent type",
        'confidence': 0.0,
        'task_id': None
    }
```

### Step 2: Update CLI to Use New Routing

**File**: `src/cli.py`

**Current Code** (processes NL directly):
```python
@nl.command()
@click.argument('message', required=True)
@click.option('--project-id', type=int, help='Project ID')
def process(message: str, project_id: Optional[int]):
    """Process natural language message."""
    # OLD: Direct execution via NLCommandProcessor
    response = nl_processor.process_and_execute(message, project_id=project_id)
    click.echo(response.response)
```

**NEW Code** (routes through orchestrator):
```python
@nl.command()
@click.argument('message', required=True)
@click.option('--project-id', type=int, help='Project ID')
def process(message: str, project_id: Optional[int]):
    """Process natural language message through orchestrator (ADR-017)."""
    try:
        # NEW: Get ParsedIntent (does not execute)
        parsed_intent = nl_processor.process(message, project_id=project_id)

        # Route through orchestrator for unified execution
        result = orchestrator.execute_nl_command(
            parsed_intent=parsed_intent,
            project_id=project_id or 1,
            interactive=False
        )

        # Display result
        if result['success']:
            click.secho(result['message'], fg='green')
            if result.get('task_id'):
                click.echo(f"Task ID: {result['task_id']}")
        else:
            click.secho(result['message'], fg='red')

    except Exception as e:
        click.secho(f"Error: {str(e)}", fg='red', err=True)
        sys.exit(1)
```

### Step 3: Update Interactive Mode to Use New Routing

**File**: `src/cli.py` (interactive command handler)

**Current Code** (direct execution):
```python
def handle_nl_message(message: str, context: dict):
    """Handle natural language message in interactive mode."""
    response = nl_processor.process_and_execute(message, context=context)
    return response.response
```

**NEW Code** (orchestrator routing):
```python
def handle_nl_message(message: str, context: dict, project_id: int):
    """Handle natural language message through orchestrator (ADR-017)."""
    try:
        # Parse intent (no execution)
        parsed_intent = nl_processor.process(message, context=context)

        # Route through orchestrator
        result = orchestrator.execute_nl_command(
            parsed_intent=parsed_intent,
            project_id=project_id,
            interactive=True
        )

        # Format and return response
        if result['success']:
            return f"{Fore.GREEN}{result['message']}{Style.RESET_ALL}"
        else:
            return f"{Fore.RED}{result['message']}{Style.RESET_ALL}"

    except Exception as e:
        logger.exception(f"Interactive NL handling failed: {e}")
        return f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}"
```

### Step 4: Add NLQueryHelper to Orchestrator

**File**: `src/orchestrator.py`

```python
def __init__(self, config: Config):
    """Initialize Orchestrator with NL components (ADR-017)."""
    self.config = config
    self.state_manager = StateManager(...)
    self.llm_plugin = LLMRegistry.get(...)()

    # ADR-017: Add NL components
    self.intent_to_task_converter = IntentToTaskConverter(
        state_manager=self.state_manager
    )
    self.nl_query_helper = NLQueryHelper(
        state_manager=self.state_manager,
        llm_plugin=self.llm_plugin
    )

    # ... rest of initialization
```

---

## Integration Points

### Files to Update

1. **`src/orchestrator.py`**: Add `execute_nl_command()` method
2. **`src/cli.py`**: Update NL command and interactive handlers
3. **`tests/integration/test_orchestrator_nl_integration.py`**: New integration tests

### Files NOT Updated

These remain unchanged:
- **`src/nl/nl_command_processor.py`**: Already returns ParsedIntent (Story 4)
- **`src/orchestration/intent_to_task_converter.py`**: Already converts OperationContext → Task (Story 2)
- **`src/nl/nl_query_helper.py`**: Already handles queries (Story 3)

---

## Test Plan

### New Integration Tests (12 tests)

**File**: `tests/integration/test_orchestrator_nl_integration.py`

**Category 1: Orchestrator NL Routing** (5 tests):
- `test_execute_nl_command_create_epic`
- `test_execute_nl_command_update_task`
- `test_execute_nl_command_delete_story`
- `test_execute_nl_command_query_tasks`
- `test_execute_nl_command_question_intent`

**Category 2: Validation Pipeline** (4 tests):
- `test_nl_command_validation_failure`
- `test_nl_command_quality_scoring`
- `test_nl_command_confidence_tracking`
- `test_nl_command_error_handling`

**Category 3: CLI Integration** (3 tests):
- `test_cli_nl_process_command`
- `test_cli_interactive_nl_routing`
- `test_cli_nl_error_propagation`

### Update Existing Tests

**File**: `tests/integration/test_orchestrator_e2e.py`

Update `test_full_workflow_create_project_to_execution` to include NL path:
```python
def test_full_workflow_create_project_to_execution(self, orchestrator, nl_processor):
    """Test complete workflow: NL command → Task creation → Execution."""
    # 1. Create project via NL
    parsed_intent = nl_processor.process("create project Test Project")
    result = orchestrator.execute_nl_command(parsed_intent, project_id=1)
    assert result['success'] is True

    # 2. Create epic via NL
    parsed_intent = nl_processor.process("create epic for user auth")
    result = orchestrator.execute_nl_command(parsed_intent, project_id=1)
    assert result['success'] is True
    assert result['task_id'] is not None

    # 3. Execute task through orchestrator
    task_result = orchestrator.execute_task(result['task_id'])
    assert task_result['success'] is True
```

---

## Acceptance Criteria

✅ **Implementation**:
- [ ] `orchestrator.execute_nl_command()` method implemented
- [ ] COMMAND intents route through IntentToTaskConverter
- [ ] QUERY intents route through NLQueryHelper
- [ ] QUESTION intents return answer directly
- [ ] Validation failures handled gracefully
- [ ] Quality scoring applied to NL commands
- [ ] Confidence tracking maintained

✅ **CLI Integration**:
- [ ] `obra nl process` uses new routing
- [ ] Interactive mode uses new routing
- [ ] Error messages properly formatted
- [ ] User feedback includes task IDs

✅ **Tests**:
- [ ] 12 new integration tests passing
- [ ] `test_full_workflow_create_project_to_execution` updated and passing
- [ ] All existing tests still pass
- [ ] Code coverage ≥90%

✅ **Validation**:
- [ ] NL commands go through full orchestrator pipeline
- [ ] Quality scores generated for NL commands
- [ ] Confidence tracked from NL to execution
- [ ] No regressions in existing functionality

---

## Validation Commands

**After Story 5 complete**:
```bash
# Run orchestrator NL integration tests
pytest tests/integration/test_orchestrator_nl_integration.py -v

# Run E2E test with NL path
pytest tests/integration/test_orchestrator_e2e.py::TestOrchestratorE2E::test_full_workflow_create_project_to_execution -v

# Run all smoke tests
pytest tests/smoke/ -v

# Verify no regressions
pytest tests/ -v --cov=src
```

**Expected Results**:
- All integration tests passing (12/12)
- E2E test passing with NL path
- All smoke tests passing (10/10)
- Coverage ≥90% on orchestrator

---

## Key Design Decisions

### Decision 1: Why execute_nl_command() Instead of Modifying execute_task()?

**Options**:
1. Add `parsed_intent` parameter to `execute_task()`
2. Create new `execute_nl_command()` method

**Choice**: Option 2

**Rationale**:
- Separation of concerns: NL-specific logic in dedicated method
- Easier to test NL path independently
- Doesn't complicate existing `execute_task()` API
- Clear migration path (can deprecate later if needed)

### Decision 2: How to Handle QUERY Operations?

**Options**:
1. Convert QUERY → Task → Execute (full pipeline)
2. Route QUERY directly to NLQueryHelper (lightweight)

**Choice**: Option 2

**Rationale**:
- Queries are read-only (no state changes)
- Don't need full orchestration pipeline
- Faster response time
- Lower resource usage

### Decision 3: What About Confirmation Workflow?

**Current State**: Story 4 confirmation handlers still execute via CommandExecutor

**Future State**: Story 5 will handle confirmations differently:
- Store pending ParsedIntent in orchestrator state
- User confirms → execute via `execute_nl_command()`
- Cleaner separation of parsing vs execution

**Implementation**:
- Add `pending_nl_commands` dict to orchestrator
- Store ParsedIntent with timestamp and project_id
- On confirmation, retrieve and execute

---

## Example Usage

### Before ADR-017 (Story 4)

```python
# OLD: Direct execution (bypasses orchestrator)
nl_processor = NLCommandProcessor(...)
response = nl_processor.process_and_execute("create epic for auth")
print(response.response)  # ✓ Created Epic #5
```

### After ADR-017 (Story 5)

```python
# NEW: Unified execution through orchestrator
nl_processor = NLCommandProcessor(...)
orchestrator = Orchestrator(...)

# Step 1: Parse intent (no execution)
parsed_intent = nl_processor.process("create epic for auth")

# Step 2: Execute through orchestrator (full validation)
result = orchestrator.execute_nl_command(
    parsed_intent=parsed_intent,
    project_id=1
)

print(result['message'])  # ✓ Created Epic #5 (quality_score=0.85, iterations=1)
```

---

## Common Pitfalls to Avoid

1. ❌ **Don't execute in NLCommandProcessor**: It should only parse and return ParsedIntent
2. ❌ **Don't skip orchestrator validation**: All COMMAND intents must go through full pipeline
3. ❌ **Don't forget error handling**: NL commands can fail at any stage
4. ❌ **Don't break backward compatibility**: `process_and_execute()` should still work (deprecated)
5. ❌ **Don't forget confidence tracking**: Pass confidence from ParsedIntent through to results

---

## References

**Key Files**:
- `src/orchestrator.py` - Main file to modify
- `src/cli.py` - CLI integration
- `src/orchestration/intent_to_task_converter.py` - For CREATE/UPDATE/DELETE routing
- `src/nl/nl_query_helper.py` - For QUERY routing

**Documentation**:
- `docs/development/ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml` - Full plan
- `docs/development/ADR017_STORY2_STARTUP_PROMPT.md` - IntentToTaskConverter reference
- `docs/development/ADR017_STORY3_STARTUP_PROMPT.md` - NLQueryHelper reference
- `docs/development/ADR017_STORY4_STARTUP_PROMPT.md` - ParsedIntent reference

**Tests**:
- `tests/nl/test_parsed_intent.py` - ParsedIntent structure tests (Story 4)
- `tests/integration/test_orchestrator_e2e.py` - E2E workflow test
- `tests/smoke/test_smoke_workflows.py` - Smoke tests

---

## Upon Completion of Story 5

**Status**: ADR-017 implementation COMPLETE!

After Story 5, you will have:
- ✅ Unified execution architecture for ALL commands (NL and CLI)
- ✅ Consistent validation pipeline
- ✅ Quality scoring for NL commands
- ✅ Confidence tracking end-to-end
- ✅ Full integration testing

**Next Steps** (optional enhancements):
- Performance optimization (caching, batching)
- Advanced NL features (multi-turn clarification, context resolution)
- Enhanced error recovery
- User feedback loop

---

**Ready to start? Implement Story 5: Unified Orchestrator Routing.**

Remember:
- Route ALL COMMAND intents through orchestrator
- Handle QUESTION intents inline (no execution)
- Update CLI and interactive mode
- Write comprehensive integration tests
- Verify E2E workflow passes!
