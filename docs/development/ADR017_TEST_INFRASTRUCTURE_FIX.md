# ADR-017 Test Infrastructure Fix - Implementation Plan

**Date**: 2025-11-13
**Priority**: 🟡 HIGH (Blocks Phase 3 validation)
**Status**: Ready for Implementation
**Estimated Effort**: 120-180 minutes
**Depends On**: Phase 3 urgent fixes (branch: `fix/phase3-urgent-fixes`)

---

## Executive Summary

Phase 3 testing revealed that the test infrastructure is incompatible with the current ADR-017 architecture. The tests were written for a pre-ADR-017 system where the NL processor executed commands directly. The current architecture separates parsing and execution:

- **NL Processor**: Parses commands → returns `ParsedIntent`
- **Orchestrator**: Executes `ParsedIntent` → returns `ExecutionResult`

**Current State**:
- ✅ **Phase 3 urgent fixes working** (confidence 0.7, parameter filtering, synonyms)
- ❌ **Test infrastructure outdated** (expects direct execution from NL processor)
- ❌ **Tests fail with `AttributeError: 'ParsedIntent' object has no attribute 'execution_result'`**

**Goal**: Update test fixtures and helper functions to properly use the ADR-017 orchestrator-based architecture.

---

## Problem Analysis

### Root Cause

Tests use `NLCommandProcessor.process()` which returns `ParsedIntent` (parsing only), but tests expect execution results with entity IDs. This architectural mismatch prevents validation of the Phase 3 urgent fixes.

### Evidence

```python
# Current test code (BROKEN)
r1 = real_nl_processor_with_llm.process("create epic for user authentication", context=ctx)
epic_id = r1.execution_result.created_ids[0]  # ❌ AttributeError: ParsedIntent has no attribute execution_result
```

**Expected**: `r1` should have `execution_result` with `created_ids`
**Actual**: `r1` is a `ParsedIntent` (parsing only, no execution)

### Architectural Flow (ADR-017)

```
User Command
    ↓
NLCommandProcessor.process()  ← Tests call this
    ↓
ParsedIntent (parsing only)  ← Tests receive this
    ↓
Orchestrator.execute_nl_command()  ← Tests SHOULD call this
    ↓
ExecutionResult (with created_ids)  ← Tests NEED this
```

---

## Solution Design

### Option 1: Add Orchestrator Fixture (RECOMMENDED)

Create a new fixture that wraps both NL processor and orchestrator, providing a unified interface for tests.

**Pros**:
- Clean separation of concerns
- Tests exercise the full ADR-017 pipeline
- Easy to maintain and understand
- Validates the actual production flow

**Cons**:
- Requires new fixture
- Tests need minor updates to use new fixture

### Option 2: Modify NL Processor to Execute (NOT RECOMMENDED)

Make `NLCommandProcessor.process()` execute commands directly.

**Pros**:
- No test changes needed
- Quick fix

**Cons**:
- ❌ **Violates ADR-017 architecture**
- ❌ **Breaks separation of concerns**
- ❌ **Creates technical debt**
- ❌ **Tests won't validate production flow**

### Decision: Option 1 (Orchestrator Fixture)

We'll create a new `real_nl_orchestrator` fixture that properly executes commands through the ADR-017 pipeline.

---

## Implementation Plan

### Step 1: Create Orchestrator Fixture (20 minutes)

**File**: `tests/conftest.py`

**Add new fixture**:

```python
@pytest.fixture
def real_nl_orchestrator(real_state_manager, real_llm, test_config):
    """REAL NL orchestrator with REAL LLM - for end-to-end testing.

    This fixture provides the complete ADR-017 pipeline:
    - NLCommandProcessor: Parses commands → ParsedIntent
    - Orchestrator: Executes ParsedIntent → ExecutionResult

    Use this for tests that need command execution results (entity IDs, etc.).
    """
    from src.core.orchestrator import Orchestrator
    from src.nl.nl_command_processor import NLCommandProcessor

    # Create orchestrator with NL processor
    orchestrator = Orchestrator(
        config=test_config,
        state_manager=real_state_manager,
        llm_plugin=real_llm
    )

    # Add convenience method for tests
    def execute_nl(command: str, context: dict = None):
        """Execute NL command and return result with execution_result.

        Returns:
            Object with:
                - confidence: float
                - operation_context: OperationContext
                - execution_result: ExecutionResult (with created_ids)
        """
        # Parse command
        parsed_intent = orchestrator.nl_processor.process(command, context=context or {})

        # Execute via orchestrator
        if parsed_intent.requires_execution:
            exec_result = orchestrator.command_executor.execute(
                parsed_intent.operation_context,
                project_id=context.get('project_id') if context else None
            )
        else:
            exec_result = None

        # Return unified result object
        class NLResult:
            def __init__(self, parsed_intent, execution_result):
                self.confidence = parsed_intent.confidence
                self.operation_context = parsed_intent.operation_context
                self.execution_result = execution_result
                self.intent = parsed_intent.intent_type
                self.success = execution_result.success if execution_result else False

        return NLResult(parsed_intent, exec_result)

    orchestrator.execute_nl = execute_nl
    return orchestrator
```

### Step 2: Update Test Files to Use New Fixture (60 minutes)

**Files to update**:
- `tests/integration/test_demo_scenarios.py` (8 tests)
- `tests/integration/test_obra_workflows.py` (8 tests)

**Changes required**:

```python
# BEFORE (using old fixture)
def test_basic_project_setup_demo(
    self,
    real_nl_processor_with_llm,  # ❌ Old fixture
    real_state_manager
):
    r1 = real_nl_processor_with_llm.process(
        "create epic for user authentication",
        context={'project_id': 1}
    )

# AFTER (using new fixture)
def test_basic_project_setup_demo(
    self,
    real_nl_orchestrator,  # ✅ New fixture
    real_state_manager
):
    r1 = real_nl_orchestrator.execute_nl(
        "create epic for user authentication",
        context={'project_id': 1}
    )
```

**Replacement pattern**:
1. Replace fixture parameter: `real_nl_processor_with_llm` → `real_nl_orchestrator`
2. Replace method call: `.process()` → `.execute_nl()`
3. Keep all other code the same (confidence checks, entity ID extraction, etc.)

**Automation script**:

```python
import re

def update_test_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replace fixture parameter
    content = re.sub(
        r'real_nl_processor_with_llm',
        r'real_nl_orchestrator',
        content
    )

    # Replace method calls
    content = re.sub(
        r'\.process\(',
        r'.execute_nl(',
        content
    )

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"✓ Updated {filepath}")

# Update both test files
update_test_file('tests/integration/test_demo_scenarios.py')
update_test_file('tests/integration/test_obra_workflows.py')
```

### Step 3: Verify Fixture Works (20 minutes)

**Test the new fixture**:

```bash
# Run single test to verify fixture works
pytest tests/integration/test_demo_scenarios.py::TestProductionDemoFlows::test_basic_project_setup_demo -v -m "real_llm" --timeout=0

# Expected output:
# - Confidence: 0.75 (passes 0.7 threshold) ✅
# - execution_result.created_ids: [1] ✅
# - Test: PASSED ✅
```

### Step 4: Run Full Test Suite (60 minutes)

**Run all demo and workflow tests**:

```bash
# Demo scenarios (8 tests, ~3-5 min)
pytest tests/integration/test_demo_scenarios.py -v -m "real_llm and demo_scenario" --timeout=0

# Obra workflows (8 tests, ~5-7 min)
pytest tests/integration/test_obra_workflows.py -v -m "real_llm and workflow" --timeout=0
```

**Expected outcomes**:
- Demo pass rate: **75-87.5%** (6-7/8 tests)
- Workflow pass rate: **67-80%** (10-12/14 tests)
- Confidence threshold: **All 0.7+ scores pass**
- Parameter validation: **No None errors**
- Synonym recognition: **High confidence on synonyms**

### Step 5: Commit and Merge (10 minutes)

```bash
# Commit fixture and test updates
git add tests/conftest.py tests/integration/test_demo_scenarios.py tests/integration/test_obra_workflows.py
git commit -m "fix: Update test infrastructure for ADR-017 architecture

- Add real_nl_orchestrator fixture for end-to-end testing
- Update 16 tests to use new fixture (demo + workflow)
- Tests now properly exercise NL processor → orchestrator → execution pipeline
- Validates Phase 3 urgent fixes (confidence, parameters, synonyms)

Related: ADR-017, Phase 3 urgent fixes"

git push origin fix/phase3-urgent-fixes
```

---

## Testing Strategy

### Phase 1: Smoke Test (5 minutes)

```bash
# Test single scenario to verify fixture works
pytest tests/integration/test_demo_scenarios.py::TestProductionDemoFlows::test_basic_project_setup_demo -v -m "real_llm" --timeout=0
```

**Success criteria**:
- Test completes without AttributeError
- Epic created with ID
- Confidence ≥ 0.7

### Phase 2: Demo Scenarios (10 minutes)

```bash
pytest tests/integration/test_demo_scenarios.py -v -m "real_llm and demo_scenario" --timeout=0
```

**Success criteria**:
- ≥ 6/8 tests pass (75% pass rate)
- No AttributeError exceptions
- Entity IDs extracted correctly

### Phase 3: Workflow Tests (15 minutes)

```bash
pytest tests/integration/test_obra_workflows.py -v -m "real_llm and workflow" --timeout=0
```

**Success criteria**:
- ≥ 10/14 tests pass (67% pass rate)
- Chained operations work (create epic → add story → add task)
- State dependencies validated

### Phase 4: Variation Tests (60 minutes - OPTIONAL)

```bash
pytest tests/integration/test_nl_variations.py -v -m "real_llm and stress_test" --timeout=0
```

**Success criteria**:
- ≥ 90% pass rate on variations
- Synonym operations recognized
- No parameter validation errors

---

## Success Criteria

### Minimum Requirements (MUST PASS)

- [x] Phase 3 urgent fixes committed and pushed
- [ ] `real_nl_orchestrator` fixture created
- [ ] 16 tests updated to use new fixture
- [ ] Smoke test passes (1 test)
- [ ] Demo scenarios ≥ 50% pass rate
- [ ] No AttributeError exceptions
- [ ] Changes committed to git

### Stretch Goals (NICE TO HAVE)

- [ ] Demo scenarios ≥ 75% pass rate
- [ ] Workflow tests ≥ 67% pass rate
- [ ] Variation tests ≥ 90% pass rate
- [ ] Full test suite run for clean baseline
- [ ] Before/after comparison report

---

## Risk Assessment

### Low Risk

**Fixture creation**:
- ✅ Well-defined interface
- ✅ Wraps existing components
- ✅ Easy to test in isolation

**Test updates**:
- ✅ Mechanical replacement (fixture name + method call)
- ✅ Can automate with script
- ✅ Easy to verify (smoke test)

### Medium Risk

**Orchestrator initialization**:
- ⚠️ May require additional config
- ⚠️ LLM connection must be stable
- **Mitigation**: Test fixture in isolation first

**Test timing**:
- ⚠️ Full suite takes 60-120 minutes
- ⚠️ LLM calls add latency
- **Mitigation**: Use timeout=0, add time buffers

### Rollback Plan

If new fixture causes issues:

```bash
# Revert to previous fixture
git diff HEAD~1 tests/conftest.py
git checkout HEAD~1 tests/conftest.py

# Or revert entire commit
git reset --hard HEAD~1
```

**Alternative**: Keep both fixtures, update tests incrementally

---

## Dependencies

### Code Dependencies

- ✅ `Orchestrator` class (src/core/orchestrator.py)
- ✅ `NLCommandProcessor` class (src/nl/nl_command_processor.py)
- ✅ `CommandExecutor` class (src/nl/command_executor.py)
- ✅ `StateManager` instance (real_state_manager fixture)
- ✅ `LLMPlugin` instance (real_llm fixture)

### Test Dependencies

- ✅ Phase 3 urgent fixes (branch: `fix/phase3-urgent-fixes`)
- ✅ Real LLM connection (Codex CLI)
- ✅ Test database (real_state_manager)
- ✅ pytest markers (real_llm, demo_scenario, workflow)

---

## Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| **Setup** | 5 min | Review this document, verify branch |
| **Fixture** | 20 min | Create `real_nl_orchestrator` fixture |
| **Test Updates** | 60 min | Update 16 tests to use new fixture |
| **Smoke Test** | 5 min | Verify fixture works (1 test) |
| **Demo Tests** | 10 min | Run demo scenarios (8 tests) |
| **Workflow Tests** | 15 min | Run workflow tests (8 tests) |
| **Commit** | 10 min | Git commit and push |
| **SUBTOTAL** | **125 min** | **Implementation + validation** |
| **Optional: Full Suite** | 60 min | Run variation tests (optional) |
| **TOTAL** | **185 min (3h)** | **Complete cycle** |

---

## Post-Implementation Checklist

After implementing all changes:

- [ ] `real_nl_orchestrator` fixture created
- [ ] Smoke test passes
- [ ] 16 tests updated (demo + workflow)
- [ ] Demo scenarios run successfully
- [ ] Workflow tests run successfully
- [ ] Changes committed to git
- [ ] Branch pushed to origin
- [ ] (Optional) Full test suite run
- [ ] (Optional) Comparison report generated

---

## Validation Evidence

### Before Fixes (Baseline)

```
Demo scenario pass rate: 12.5% (1/8)
Workflow pass rate: 0% (0/14)
Variation pass rate: ~82%

Confidence threshold: 0.8
Confidence scores: 0.45-0.79 (most fail)
Parameter errors: ~30% (None values)
Synonym recognition: ~50% (not explicitly supported)
```

### After Phase 3 Urgent Fixes (Current)

```
NL parsing validation:
✅ Confidence: 0.75 (passes 0.7 threshold)
✅ Operation classification: CREATE (confidence 0.91)
✅ Synonym expansion: Working (prompt includes 60+ synonyms)
✅ Parameter filtering: No None errors
✅ Entity extraction: "user authentication" (confidence 0.73)

Test infrastructure:
❌ AttributeError: 'ParsedIntent' object has no attribute 'execution_result'
❌ Tests fail due to architectural mismatch (pre-ADR-017 tests)
```

### Expected After Test Infrastructure Fix

```
Demo scenario pass rate: 75-87.5% (6-7/8)
Workflow pass rate: 67-80% (10-12/14)
Variation pass rate: ~90%

Confidence threshold: 0.7
Confidence scores: 0.70-0.95 (most pass)
Parameter errors: 0% (None values filtered)
Synonym recognition: 90%+ (explicit synonym support)
```

---

## Related Documents

- **ADR-017**: Unified Execution Architecture
- **Phase 3 Urgent Fixes**: `URGENT_FIXES_IMPLEMENTATION_PLAN.md`
- **Phase 3 Status**: `docs/testing/PHASE3_COMPREHENSIVE_STATUS.md`
- **NL Command Guide**: `docs/guides/NL_COMMAND_GUIDE.md`

---

## Notes

### Why Not Just Fix the Tests Directly?

The tests weren't "broken" - they were written for a different architecture (pre-ADR-017). The current ADR-017 architecture intentionally separates parsing from execution:

- **Parsing**: NL processor extracts intent
- **Execution**: Orchestrator validates and executes

This separation provides:
- Better testability (can test parsing without execution)
- Clear separation of concerns
- Orchestrator quality control
- Unified validation pipeline

The fixture approach respects this architecture while providing a convenient test interface.

### Why Create a New Fixture?

We could modify the existing `real_nl_processor_with_llm` fixture, but creating a new `real_nl_orchestrator` fixture:

1. Makes the architectural change explicit
2. Allows gradual migration (keep old fixture for compatibility)
3. Clearly signals "this fixture executes commands"
4. Follows ADR-017 design principles

### What About Backward Compatibility?

We'll keep the old `real_nl_processor_with_llm` fixture for any tests that only need parsing (no execution). Tests that need execution results will migrate to `real_nl_orchestrator`.

---

**Status**: Ready for implementation
**Owner**: Development Team
**Priority**: 🟡 HIGH (Blocks Phase 3 validation)
**Next Action**: Create `real_nl_orchestrator` fixture in `tests/conftest.py`
