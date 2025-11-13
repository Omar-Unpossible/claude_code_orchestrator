# ADR-017 Story 2 Startup Prompt

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra, a Claude Code orchestration system. Story 0 (testing infrastructure) and Story 1 (documentation) are complete. Now implement Story 2.

---

## What You're Building

**Story 2**: Create `IntentToTaskConverter` component (12 hours)

**Purpose**: Convert parsed NL intents → Task objects for orchestrator execution

**Location**: `src/orchestration/intent_to_task_converter.py`

---

## Quick Context

**The Problem**: Obra v1.6.0 has two execution paths:
- CLI tasks → Full orchestration (8-step validation)
- NL commands → Direct CRUD (bypasses validation)

**The Solution**: Route ALL commands through `orchestrator.execute_task()` for consistent quality.

**Story 2's Role**: Bridge NL parsing → orchestrator by converting `OperationContext` (from NL parser) → `Task` objects (for orchestrator).

---

## Implementation Requirements

### 1. Core Class: `IntentToTaskConverter`

```python
class IntentToTaskConverter:
    """Converts parsed NL intents to Task objects for orchestrator execution."""

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def convert(
        self,
        parsed_intent: OperationContext,
        project_id: int,
        original_message: str
    ) -> Task:
        """Convert parsed intent to executable task.

        Args:
            parsed_intent: OperationContext from NL parsing pipeline
            project_id: Project ID for task creation
            original_message: Original NL message (for context)

        Returns:
            Task object enriched with NL metadata
        """
        # 1. Map operation type to task title/description
        # 2. Extract parameters from parsed_intent
        # 3. Create task via state_manager
        # 4. Enrich with NL context
        # 5. Return task
```

### 2. Operation Mapping

**CREATE**:
- Title: "Create {entity_type}: {title}"
- Description: Parameters as instructions
- Task type: Map entity_type (epic→EPIC, story→STORY, etc.)

**UPDATE**:
- Title: "Update {entity_type} {identifier}: {field}"
- Description: Update instructions with old/new values
- Requires confirmation: True

**DELETE**:
- Title: "Delete {entity_type} {identifier}"
- Description: Safety context (what will be deleted)
- Requires confirmation: True

**QUERY**:
- Option 1: Return query context (no task needed)
- Option 2: Create informational task for complex queries

### 3. NL Context Enrichment

Add metadata to task:
```python
task.nl_context = {
    'source': 'natural_language',
    'original_message': original_message,
    'intent_confidence': parsed_intent.confidence,
    'operation_type': parsed_intent.operation_type,
    'entity_type': parsed_intent.entity_type,
    'parsed_at': datetime.utcnow().isoformat()
}
```

---

## Testing Requirements

**Target**: 25+ tests, ≥90% coverage

**Test Categories**:
1. **Operation Mapping** (8 tests): CREATE/UPDATE/DELETE/QUERY for each entity type
2. **Parameter Extraction** (5 tests): Correct mapping of parsed params → task data
3. **NL Context Enrichment** (4 tests): Metadata attached correctly
4. **Error Handling** (4 tests): Missing params, invalid entity types
5. **Integration** (4 tests): End-to-end with real OperationContext

**Test File**: `tests/test_intent_to_task_converter.py`

---

## Key Files to Reference

**Read These First**:
1. `docs/decisions/ADR-017-unified-execution-architecture.md` - Full architecture
2. `docs/development/ADR017_ENHANCED_WITH_TESTING.yaml` - Story 2 detailed spec
3. `src/nl/schemas/obra_schema.json` - NL parsing schema
4. `src/nl/entity_extractor.py` - See OperationContext structure
5. `src/core/state.py` - StateManager methods for task creation

**Related Components**:
- `src/nl/nl_command_processor.py` - Produces OperationContext
- `src/orchestrator.py` - Consumes Task objects
- `core/models.py` - Task model, TaskType enum

---

## Acceptance Criteria

✅ **Code**:
- [ ] `IntentToTaskConverter` class implemented
- [ ] `convert()` method handles all 4 operation types
- [ ] Parameter mapping correct for all entity types
- [ ] NL context enrichment working
- [ ] Error handling for edge cases

✅ **Tests**:
- [ ] 25+ unit tests written
- [ ] ≥90% code coverage
- [ ] All tests passing (`pytest tests/test_intent_to_task_converter.py -v`)

✅ **Integration**:
- [ ] Works with NLCommandProcessor output (OperationContext)
- [ ] Creates valid Task objects (accepted by orchestrator)
- [ ] Edge cases handled (missing params, invalid types)

---

## Development Approach

**Step 1**: Create class skeleton with core methods
**Step 2**: Implement CREATE operation (simplest)
**Step 3**: Add tests for CREATE (TDD for remaining operations)
**Step 4**: Implement UPDATE/DELETE/QUERY
**Step 5**: Add NL context enrichment
**Step 6**: Error handling and edge cases
**Step 7**: Integration testing with real OperationContext

---

## Example Usage (Target)

```python
from src.orchestration.intent_to_task_converter import IntentToTaskConverter

# NL parsing produces OperationContext
parsed_intent = nl_processor.process("create epic for user authentication")

# Convert to Task
converter = IntentToTaskConverter(state_manager)
task = converter.convert(
    parsed_intent=parsed_intent.operation_context,
    project_id=1,
    original_message="create epic for user authentication"
)

# Task ready for orchestrator
assert task.title == "Create epic: User Authentication"
assert task.nl_context['source'] == 'natural_language'
assert task.nl_context['operation_type'] == 'CREATE'

# Execute through orchestrator (Story 5)
orchestrator.execute_task(task_id=task.id)
```

---

## Critical Notes

1. **Do NOT execute tasks** - IntentToTaskConverter creates Task objects, orchestrator executes them
2. **StateManager for task creation** - Use `state_manager.create_task()`, NOT direct DB access
3. **Preserve parsed confidence** - Include in NL context for orchestrator decision-making
4. **Follow TEST_GUIDELINES.md** - Max 0.5s sleep, 5 threads, 20KB per test (WSL2 stability)

---

## Status Check

**Before starting**:
```bash
# Verify Story 0 tests passing
pytest tests/health tests/smoke -v  # Should: 17 passed in <3s

# Verify Story 1 docs exist
ls docs/decisions/ADR-017-unified-execution-architecture.md
ls docs/guides/ADR017_MIGRATION_GUIDE.md
```

**After Story 2**:
```bash
# Your tests should pass
pytest tests/test_intent_to_task_converter.py -v --cov=src/orchestration/intent_to_task_converter

# Target: 25+ tests, ≥90% coverage, <10s runtime
```

---

## Questions to Ask if Stuck

1. "Show me the OperationContext structure from entity_extractor.py"
2. "What parameters does state_manager.create_task() accept?"
3. "How does TaskType enum map to entity types?"
4. "What's the format of NL context metadata?"

---

**Ready to start? Implement Story 2: IntentToTaskConverter component. Begin with reading the referenced files, then create the class skeleton.**
