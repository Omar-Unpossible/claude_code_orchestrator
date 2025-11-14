# Workflow Test Fix - Implementation Plan

**Created**: 2025-11-13
**Priority**: CRITICAL
**Effort**: 4-22 hours (phased)
**Status**: Ready to implement

---

## Quick Summary

**Problem**: Basic user workflows broken - tests not validating real usage
**Scope**: 13 failing tests + 15 missing workflow tests
**Impact**: Users can't list projects, create epics/stories, or delete assets

---

## Phase 1: Fix Broken Tests (URGENT - 4 hours)

### 1.1 Fix Integration Tests (10 failing tests)

**File**: `tests/integration/test_orchestrator_nl_integration.py`

**Issue**: Tests use old API `entity_type=...` instead of `entity_types=[...]`

**Lines to Fix**: 113, 134, 159, 183, 240, 265, 294, 314, 363, 390

**Pattern**:
```python
# BEFORE (v1.7.4 API)
operation_context = OperationContext(
    operation=OperationType.CREATE,
    entity_type=EntityType.EPIC,  # ❌ OLD API
    identifier=None,
    ...
)

# AFTER (v1.7.5 API)
operation_context = OperationContext(
    operation=OperationType.CREATE,
    entity_types=[EntityType.EPIC],  # ✅ NEW API
    identifier=None,
    ...
)
```

**Affected Tests**:
1. `test_execute_nl_command_create_epic` (line 113)
2. `test_execute_nl_command_update_task` (line 134)
3. `test_execute_nl_command_delete_story` (line 159)
4. `test_execute_nl_command_query_tasks` (line 183)
5. `test_nl_command_validation_failure` (line 240)
6. `test_nl_command_quality_scoring` (line 265)
7. `test_nl_command_confidence_tracking` (line 294)
8. `test_cli_nl_process_command` (line 314)
9. `test_cli_interactive_nl_routing` (line 363)
10. `test_cli_nl_error_propagation` (line 390)

**Verification**:
```bash
pytest tests/integration/test_orchestrator_nl_integration.py -v
# Expected: 12/12 passing (currently 2/12)
```

---

### 1.2 Fix Smoke Tests (3 failing tests)

**File**: `tests/smoke/test_smoke_workflows.py`

#### Test 1: `test_create_epic_smoke` (MOST CRITICAL)

**Issue**: Returns `intent='QUESTION'` instead of `'COMMAND'`

**Error Message**:
```
AssertionError: assert 'QUESTION' == 'COMMAND'
Error: 'COMMAND intent requires operation_context'
```

**Root Cause**: NL pipeline not constructing `OperationContext` properly

**Debug Steps**:
1. Add logging to `NLCommandProcessor.process()` to see where pipeline fails
2. Check if `EntityTypeClassifier.classify()` returns tuple correctly
3. Verify `OperationContext` construction in `nl_command_processor.py`

**Possible Fix Location**: `src/nl/nl_command_processor.py` around line 200-250

#### Test 2: `test_confirmation_workflow_smoke`

**Needs Investigation** - Run test to see exact failure

#### Test 3: `test_error_recovery_smoke`

**Needs Investigation** - Run test to see exact failure

**Verification**:
```bash
pytest tests/smoke/test_smoke_workflows.py -v
# Expected: 10/10 passing (currently 7/10)
```

---

## Phase 2: Add Workflow Integration Tests (HIGH PRIORITY - 8 hours)

### 2.1 Create New Test File

**File**: `tests/integration/test_nl_workflows.py`

**Structure**:
```python
"""Integration tests for complete NL command workflows.

These tests validate entire workflows from user input to DB changes,
using real components with minimal mocking.
"""

import pytest
from src.nl.nl_command_processor import NLCommandProcessor
from src.core.state import StateManager
from src.nl.types import EntityType, OperationType

@pytest.fixture
def state_manager():
    """Real StateManager with in-memory database."""
    state = StateManager(database_url='sqlite:///:memory:')
    yield state
    state.close()

@pytest.fixture
def nl_processor(mock_llm_smart, state_manager):
    """Real NL processor with mocked LLM."""
    return NLCommandProcessor(
        llm_plugin=mock_llm_smart,
        state_manager=state_manager,
        config={'nl_commands': {'enabled': True}}
    )

class TestProjectWorkflows:
    """Test project-level workflows (US-NL-001, US-NL-002)."""

    def test_list_projects_workflow(self, nl_processor, state_manager):
        """Workflow: 'list all projects' → actual project list."""
        # Setup: Create 3 test projects
        proj1 = state_manager.create_project("Project A", "desc", "/tmp/a")
        proj2 = state_manager.create_project("Project B", "desc", "/tmp/b")
        proj3 = state_manager.create_project("Project C", "desc", "/tmp/c")

        # Mock LLM responses for query pipeline
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "QUERY", "confidence": 0.94}',
            '{"entity_types": ["PROJECT"], "confidence": 0.96}',
            '{"identifier": null, "confidence": 0.98}',
            '{"parameters": {}, "confidence": 0.90}'
        ]

        # Execute NL command
        response = nl_processor.process("list all projects")

        # Assertions
        assert response.success, f"Failed: {response.error_message}"
        assert response.intent_type == 'COMMAND'
        assert "Project A" in response.formatted_response
        assert "Project B" in response.formatted_response
        assert "Project C" in response.formatted_response

class TestEpicStoryTaskCreation:
    """Test work item creation workflows (US-NL-008)."""

    def test_create_epic_workflow(self, nl_processor, state_manager):
        """Workflow: 'create epic for user auth' → epic in DB."""
        # Setup: Create project
        project = state_manager.create_project("Test Project", "desc", "/tmp/test")

        # Mock LLM responses for CREATE pipeline
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "CREATE", "confidence": 0.94}',
            '{"entity_types": ["EPIC"], "confidence": 0.96}',
            '{"identifier": null, "confidence": 0.98}',
            '{"parameters": {"title": "User Authentication", "project_id": 1}, "confidence": 0.90}'
        ]

        # Execute NL command
        response = nl_processor.process("create epic for user authentication")

        # Assertions
        assert response.success
        assert response.intent_type == 'COMMAND'
        assert len(response.execution_result.created_ids) == 1

        # Verify epic in database
        epic_id = response.execution_result.created_ids[0]
        epic = state_manager.get_task(epic_id)
        assert epic is not None
        assert epic.task_type == TaskType.EPIC
        assert "authentication" in epic.title.lower()

    # ... Add 13 more workflow tests
```

---

### 2.2 Test Coverage Matrix

| Workflow | Test Name | User Story | Priority |
|----------|-----------|------------|----------|
| List projects | `test_list_projects_workflow` | US-NL-001 | P0 |
| Query project stats | `test_query_project_statistics_workflow` | US-NL-002 | P0 |
| Create epic | `test_create_epic_workflow` | US-NL-008 | P0 |
| Create story | `test_create_story_in_epic_workflow` | US-NL-008 | P0 |
| Create task | `test_create_task_workflow` | US-NL-008 | P0 |
| Update task status | `test_update_task_status_workflow` | US-NL-009 | P0 |
| Update epic title | `test_update_epic_title_workflow` | US-NL-009 | P1 |
| Delete single task | `test_delete_single_task_workflow` | US-NL-010 | P0 |
| Delete all tasks (bulk) | `test_delete_all_tasks_workflow` | US-NL-010 | P0 |
| Delete epic (cascade) | `test_delete_epic_cascade_workflow` | US-NL-010 | P1 |
| Query hierarchy | `test_query_epic_hierarchy_workflow` | US-NL-005 | P1 |
| Invalid entity type | `test_invalid_entity_type_workflow` | US-NL-016 | P1 |
| Missing context | `test_missing_context_workflow` | US-NL-017 | P1 |
| Bulk delete confirmation | `test_bulk_delete_with_confirmation_workflow` | US-NL-010 | P0 |
| Multi-entity query | `test_multi_entity_query_workflow` | Bulk Ops | P1 |

**Total**: 15 new workflow tests

---

## Execution Plan

### Session 1: Fix Integration Tests (2 hours)

**Goal**: Get 10 failing integration tests passing

1. Open `tests/integration/test_orchestrator_nl_integration.py`
2. Find/replace: `entity_type=EntityType.` → `entity_types=[EntityType.`
3. Add closing bracket `]` after each entity type
4. Run tests: `pytest tests/integration/test_orchestrator_nl_integration.py -v`
5. Fix any remaining issues
6. Verify: 12/12 passing

---

### Session 2: Fix Smoke Tests (2 hours)

**Goal**: Get 3 failing smoke tests passing

1. Debug `test_create_epic_smoke`:
   ```bash
   pytest tests/smoke/test_smoke_workflows.py::TestSmokeWorkflows::test_create_epic_smoke -vvs
   ```
2. Add debug logging to NL pipeline
3. Identify where `OperationContext` construction fails
4. Fix issue in `src/nl/nl_command_processor.py`
5. Verify: 10/10 smoke tests passing

---

### Session 3: Create Workflow Tests (8 hours)

**Goal**: Add 15 workflow integration tests

**Phase A** (2 hours): Create file and fixtures
- Create `tests/integration/test_nl_workflows.py`
- Add fixtures (`state_manager`, `nl_processor`, `mock_llm_smart`)
- Add test class structure

**Phase B** (3 hours): Implement P0 tests (9 tests)
- List projects
- Query project stats
- Create epic/story/task
- Update task status
- Delete single task
- Delete all tasks (bulk)
- Bulk delete confirmation

**Phase C** (2 hours): Implement P1 tests (6 tests)
- Update epic title
- Delete epic (cascade)
- Query hierarchy
- Invalid entity type
- Missing context
- Multi-entity query

**Phase D** (1 hour): Verification
- Run all new tests: `pytest tests/integration/test_nl_workflows.py -v`
- Verify: 15/15 passing
- Check coverage increase

---

## Success Criteria

### Phase 1 Complete ✅

- [ ] 12/12 integration tests passing
- [ ] 10/10 smoke tests passing
- [ ] 0 known broken workflows
- [ ] CI/CD passing

### Phase 2 Complete ✅

- [ ] 15 new workflow tests created
- [ ] All 20 user stories have integration tests
- [ ] Workflows validated end-to-end
- [ ] No mocks except LLM (realistic responses)

---

## Testing Commands

```bash
# Phase 1 Verification
pytest tests/integration/test_orchestrator_nl_integration.py -v
pytest tests/smoke/test_smoke_workflows.py -v

# Phase 2 Verification
pytest tests/integration/test_nl_workflows.py -v

# Full Regression
pytest tests/ -v --tb=short

# Coverage Check
pytest tests/integration tests/smoke --cov=src/nl --cov=src/orchestrator --cov-report=term
```

---

## Risk Mitigation

### Risk 1: Smoke Test Fixes Take Longer Than Expected

**Mitigation**: If `test_create_epic_smoke` is complex to fix:
1. Create new smoke test with corrected setup
2. Mark old test as `@pytest.mark.xfail` temporarily
3. Document issue for deeper investigation

### Risk 2: Workflow Tests Reveal More Issues

**Mitigation**: If workflow tests uncover new bugs:
1. Document each bug
2. Create minimal reproduction test
3. Fix bugs in separate session
4. Keep workflow tests as regression suite

### Risk 3: Mock LLM Responses Don't Match Real LLM

**Mitigation**: After Phase 2, run Phase 3:
1. Create `test_nl_workflows_real_llm.py`
2. Mark tests `@pytest.mark.requires_ollama`
3. Run with real Qwen 2.5 Coder
4. Adjust mock responses to match reality

---

## Next Steps

**Immediate** (Start Now):
1. Begin Phase 1, Session 1 (Fix integration tests)
2. Estimated time: 2 hours
3. Low risk, high impact

**After Phase 1**:
1. Verify all tests pass: `pytest tests/integration tests/smoke`
2. Commit with message: "fix: Update integration and smoke tests for v1.7.5 API"
3. Push to main
4. Begin Phase 2

---

**Status**: ✅ Ready to implement
**First Task**: Fix 10 integration tests (2 hours)
**Expected Outcome**: All basic workflows validated by tests
