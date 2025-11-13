# ADR-017 Story 6 Startup Prompt

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 0-5 are complete. Now implement Story 6.

---

## What You're Building

**Story 6**: Integration Testing (16 hours)

**Purpose**: Comprehensive integration testing to validate the unified execution architecture works end-to-end with real LLM and real agent integration.

**Key Objectives**:
- Fix StateManager API mismatches in test fixtures
- Validate all 12 NL routing tests pass
- Ensure E2E test (THE CRITICAL TEST) passes with new NL routing
- Add regression tests for backward compatibility
- Validate performance (latency, throughput)
- Real LLM + Real Agent testing

---

## What's Already Complete

### Story 0: Testing Infrastructure ✅
- Health checks, smoke tests, integration tests framework
- THE CRITICAL TEST baseline established

### Story 1: Architecture Documentation ✅
- ADR-017 written and approved
- Architecture diagrams completed

### Story 2: IntentToTaskConverter ✅
- **Component**: `src/orchestration/intent_to_task_converter.py`
- **Function**: Converts `OperationContext` → `Task` objects
- **Tests**: 32 tests, 93% coverage

### Story 3: NLQueryHelper ✅
- **Component**: `src/nl/nl_query_helper.py`
- **Function**: Query-only operations (read-only)
- **Tests**: 17 tests, 97% coverage

### Story 4: NLCommandProcessor Routing ✅
- **Changes**: Returns `ParsedIntent` instead of `NLResponse`
- **New Type**: `ParsedIntent` dataclass
- **Tests**: 18 tests for ParsedIntent structure

### Story 5: Unified Orchestrator Routing ✅
- **Component**: `src/orchestrator.py::execute_nl_command()`
- **Integration**: Routes ALL NL commands through orchestrator
- **Components**: IntentToTaskConverter and NLQueryHelper initialized
- **Tests**: 12 new integration tests (need API fixes), E2E test updated

---

## The Problem

Story 5 implementation is complete but integration tests have API mismatches:
1. **StateManager.create_task()** - Tests use wrong parameter names (`task_type` vs correct API)
2. **StateManager.create_epic()/create_story()** - Parameter name mismatches
3. **Test fixtures** - Need alignment with actual StateManager API
4. **Real LLM/Agent testing** - Tests not yet run with actual Ollama + Claude Code

Additionally:
- Need to validate latency meets <3s P95 requirement
- Need to validate no regressions in existing 770+ tests
- Need backward compatibility tests for deprecated methods
- Need performance benchmarking

---

## The Solution

**Integration Testing Strategy**:
```
1. Fix Test API Mismatches
   ↓
2. Run NL Integration Tests (12 tests)
   ↓
3. Run E2E Test with Real LLM + Real Agent
   ↓
4. Add Regression Tests
   ↓
5. Performance Validation
   ↓
6. All 770+ Tests Pass
```

---

## Implementation Plan

### Step 1: Fix StateManager API Mismatches in Test Fixtures

**File**: `tests/integration/test_orchestrator_nl_integration.py`

**Current Errors**:
```python
# ERROR: StateManager.create_task() got unexpected keyword argument 'task_type'
state_manager.create_task(
    project_id=test_project.id,
    task_type=TaskType.TASK,  # WRONG
    description="Test task"
)
```

**Fix**: Check actual StateManager API and align parameters:
```python
# Step 1: Find correct API
grep -A 10 "def create_task" src/core/state.py

# Step 2: Update test fixtures to match
# Example (adjust based on actual API):
state_manager.create_task(
    project_id=test_project.id,
    task_data={'description': 'Test task', ...}
)
```

**Similar Fixes Needed**:
- `create_epic()` - Check parameter names
- `create_story()` - Check parameter names
- `create_milestone()` - Check parameter names

### Step 2: Run and Fix All 12 NL Integration Tests

**File**: `tests/integration/test_orchestrator_nl_integration.py`

**Run Tests**:
```bash
pytest tests/integration/test_orchestrator_nl_integration.py -v --tb=short
```

**Expected Results**:
- All 12 tests passing
- Category 1 (Orchestrator NL Routing): 5/5 ✅
- Category 2 (Validation Pipeline): 4/4 ✅
- Category 3 (CLI Integration): 3/3 ✅

**If Failures**: Debug and fix systematically:
1. Read error message carefully
2. Check StateManager API vs test usage
3. Fix parameter names/types
4. Re-run test
5. Repeat until all pass

### Step 3: Run E2E Test with Real LLM + Real Agent

**File**: `tests/integration/test_orchestrator_e2e.py`

**THE CRITICAL TEST** (updated in Story 5):
```bash
# Requires: Ollama running on http://10.0.75.1:11434
# Requires: Qwen 2.5 Coder model available
pytest tests/integration/test_orchestrator_e2e.py::TestOrchestratorE2E::test_full_workflow_create_project_to_execution -v --tb=short -m "" --timeout=180
```

**Expected Flow**:
1. ✅ Create project via StateManager
2. ✅ Parse NL intent: "create task to generate Python hello world script"
3. ✅ Route through `orchestrator.execute_nl_command()`
4. ✅ Task created via IntentToTaskConverter
5. ✅ Execute task with Real Claude Code agent
6. ✅ Validate file created (`hello.py`)
7. ✅ Validate code quality
8. ✅ Validate metrics tracked

**If Test Fails**:
- Check Ollama connectivity
- Check Claude Code CLI available
- Review logs for execution errors
- Debug specific step that failed

### Step 4: Add Regression Tests for Backward Compatibility

**New File**: `tests/integration/test_adr017_regression.py`

**Purpose**: Ensure existing functionality still works

**Tests to Add** (8 tests):
```python
# 1. Legacy process_and_execute() still works (deprecated but functional)
def test_legacy_process_and_execute_deprecated():
    """Verify deprecated method still works with warnings."""
    # Should work but emit deprecation warning
    pass

# 2. Direct StateManager CRUD still works
def test_direct_state_manager_create_task():
    """Verify direct StateManager access unchanged."""
    pass

# 3. CLI task execute still works
def test_cli_task_execute_unchanged():
    """Verify CLI task execution unchanged."""
    pass

# 4. Epic execution still works
def test_epic_execution_unchanged():
    """Verify epic execution flow unchanged."""
    pass

# 5. Quality scoring still applies
def test_quality_scoring_applied():
    """Verify quality scoring unchanged."""
    pass

# 6. Confidence tracking still works
def test_confidence_tracking_preserved():
    """Verify confidence scoring unchanged."""
    pass

# 7. Breakpoints still trigger
def test_breakpoints_still_work():
    """Verify breakpoint system unchanged."""
    pass

# 8. File watching still works
def test_file_watcher_unchanged():
    """Verify file watching unchanged."""
    pass
```

**Acceptance**: All 8 regression tests pass

### Step 5: Performance Validation

**New File**: `tests/integration/test_adr017_performance.py`

**Purpose**: Validate latency requirements met

**Performance Tests** (4 tests):
```python
import time

def test_nl_command_latency_p50():
    """Verify P50 latency < 2s for NL commands."""
    latencies = []
    for i in range(10):
        start = time.time()
        result = orchestrator.execute_nl_command(...)
        latencies.append(time.time() - start)

    p50 = sorted(latencies)[len(latencies) // 2]
    assert p50 < 2.0, f"P50 latency {p50:.2f}s exceeds 2s"

def test_nl_command_latency_p95():
    """Verify P95 latency < 3s for NL commands."""
    latencies = []
    for i in range(20):
        start = time.time()
        result = orchestrator.execute_nl_command(...)
        latencies.append(time.time() - start)

    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 3.0, f"P95 latency {p95:.2f}s exceeds 3s"

def test_nl_vs_direct_latency_overhead():
    """Verify NL routing overhead < 500ms."""
    # Compare NL path vs direct StateManager
    pass

def test_throughput_baseline():
    """Verify throughput >= 40 cmd/min."""
    pass
```

**Acceptance**: All latency requirements met

### Step 6: Run Full Test Suite (No Regressions)

**Command**:
```bash
# Run ALL tests
pytest tests/ -v --cov=src --cov-report=term

# Expected:
# - 770+ tests passing (existing)
# - 12 new NL integration tests passing
# - 8 regression tests passing
# - 4 performance tests passing
# Total: ~794 tests, all passing
```

**Coverage Target**: ≥88% (maintain current level)

**If Failures**:
- Identify failing test
- Check if ADR-017 changes caused regression
- Fix or document as expected behavior change
- Update tests if behavior intentionally changed

---

## Acceptance Criteria

✅ **Test Fixtures Fixed**:
- [ ] All StateManager API calls use correct parameters
- [ ] All 12 NL integration tests have proper fixtures
- [ ] No more `TypeError: unexpected keyword argument` errors

✅ **NL Integration Tests**:
- [ ] Category 1 (Orchestrator NL Routing): 5/5 passing
- [ ] Category 2 (Validation Pipeline): 4/4 passing
- [ ] Category 3 (CLI Integration): 3/3 passing
- [ ] Total: 12/12 passing

✅ **E2E Test**:
- [ ] THE CRITICAL TEST passes with new NL routing
- [ ] All 6 steps complete successfully
- [ ] Real LLM + Real Agent integration validated
- [ ] File created and validated

✅ **Regression Tests**:
- [ ] 8 new regression tests created
- [ ] All regression tests passing
- [ ] No existing functionality broken

✅ **Performance**:
- [ ] P50 latency < 2s
- [ ] P95 latency < 3s
- [ ] Overhead < 500ms vs direct access
- [ ] Throughput ≥ 40 cmd/min

✅ **Full Test Suite**:
- [ ] All 770+ existing tests passing
- [ ] All 12 new NL tests passing
- [ ] All 8 regression tests passing
- [ ] All 4 performance tests passing
- [ ] Code coverage ≥88%

---

## Validation Commands

**Step-by-step validation**:
```bash
# Step 1: Fix and run NL integration tests
pytest tests/integration/test_orchestrator_nl_integration.py -v

# Step 2: Run E2E test
pytest tests/integration/test_orchestrator_e2e.py::TestOrchestratorE2E::test_full_workflow_create_project_to_execution -v --timeout=180

# Step 3: Run regression tests
pytest tests/integration/test_adr017_regression.py -v

# Step 4: Run performance tests
pytest tests/integration/test_adr017_performance.py -v

# Step 5: Run all tests
pytest tests/ -v --cov=src --cov-report=term

# Step 6: Run smoke tests
pytest tests/smoke/ -v
```

**Expected Results**:
- ✅ All integration tests passing
- ✅ THE CRITICAL TEST passing
- ✅ All regression tests passing
- ✅ All performance tests passing
- ✅ Full test suite passing (794+ tests)
- ✅ Coverage ≥88%

---

## Key Design Decisions

### Decision 1: Should We Mock LLM for Integration Tests?

**Options**:
1. Mock LLM for all integration tests (fast, reliable)
2. Use real LLM for all integration tests (slow, realistic)
3. Hybrid: Mock for most, real for E2E only

**Choice**: Option 3 (Hybrid)

**Rationale**:
- Fast feedback loop for most tests (mock LLM)
- Real integration validation for critical path (E2E)
- Balance between speed and realism

### Decision 2: How to Handle Performance Test Variability?

**Problem**: Latency varies based on system load, LLM response time

**Solution**:
- Run performance tests multiple times (20+ samples)
- Use percentiles (P50, P95) not averages
- Allow 10% tolerance for CI variability
- Mark as `@pytest.mark.slow` for optional skipping

### Decision 3: Should Integration Tests Use In-Memory DB?

**Options**:
1. In-memory SQLite (fast, isolated)
2. Real SQLite file (realistic, persistent)
3. PostgreSQL (production-like, complex)

**Choice**: Option 1 (In-memory SQLite)

**Rationale**:
- Fast test execution
- Isolated tests (no cross-contamination)
- Easy cleanup
- Good enough for integration validation

---

## Common Pitfalls to Avoid

1. ❌ **Don't skip fixing API mismatches**: Tests must use correct StateManager API
2. ❌ **Don't skip THE CRITICAL TEST**: This validates core value proposition
3. ❌ **Don't skip performance tests**: Latency requirements are in ADR-017 success metrics
4. ❌ **Don't skip regression tests**: Must ensure no existing functionality broken
5. ❌ **Don't commit failing tests**: All tests must pass before Story 6 complete
6. ❌ **Don't reduce coverage**: Must maintain ≥88% coverage
7. ❌ **Don't skip real LLM testing**: At least run E2E with real Ollama once

---

## References

**Key Files**:
- `tests/integration/test_orchestrator_nl_integration.py` - 12 NL integration tests (need fixes)
- `tests/integration/test_orchestrator_e2e.py` - THE CRITICAL TEST (updated Story 5)
- `src/core/state.py` - StateManager API reference
- `src/orchestrator.py` - execute_nl_command() implementation

**Documentation**:
- `docs/decisions/ADR-017-unified-execution-architecture.md` - Architecture
- `docs/development/ADR017_STORY5_STARTUP_PROMPT.md` - Previous story
- `docs/development/TEST_GUIDELINES.md` - Test best practices

**Related Files**:
- `src/orchestration/intent_to_task_converter.py` - Story 2
- `src/nl/nl_query_helper.py` - Story 3
- `src/nl/nl_command_processor.py` - Story 4

---

## Upon Completion of Story 6

**Status**: ADR-017 integration VALIDATED!

After Story 6, you will have:
- ✅ All 12 NL integration tests passing
- ✅ THE CRITICAL TEST passing with unified routing
- ✅ No regressions in 770+ existing tests
- ✅ Performance validated (<3s P95 latency)
- ✅ Code coverage ≥88%
- ✅ Production-ready unified execution architecture

**Next Steps**: Story 7 - Documentation Updates (8 hours)
- Update user guides with new unified architecture
- Update API documentation
- Update CHANGELOG.md for v1.7.0
- Create migration guide for internal API changes
- Update architecture diagrams

---

## IMPORTANT: Generate Story 7 Startup Prompt

**When Story 6 is complete**, generate the startup prompt for Story 7 using this durable pattern:

1. **Create file**: `docs/development/ADR017_STORY7_STARTUP_PROMPT.md`
2. **Use this template structure**:
   - Context (Stories 0-6 complete)
   - What You're Building (Story 7: Documentation Updates)
   - What's Already Complete (Stories 0-6 summaries)
   - The Problem
   - The Solution
   - Implementation Plan (detailed steps)
   - Acceptance Criteria
   - Validation Commands
   - Key Design Decisions
   - Common Pitfalls
   - References
   - Upon Completion
   - **IMPORTANT: Generate Story 8 Startup Prompt** (durable pattern)

3. **Story 7 Focus**:
   - Update all user-facing documentation
   - Update API documentation
   - Update CHANGELOG.md for v1.7.0
   - Create migration guide
   - Update architecture diagrams
   - Document breaking changes
   - Update README if needed

4. **Include instructions for Story 8**: At the end of Story 7 prompt, add section telling Claude to generate Story 8 startup prompt when Story 7 is complete. Story 8 is "Destructive Operation Breakpoints (10 hours) - v1.7.1".

5. **Make pattern self-sustaining**: Each story prompt generates the next, ensuring smooth handoffs between sessions.

---

**Ready to start? Implement Story 6: Integration Testing.**

Remember:
- Fix StateManager API mismatches first
- Validate all 12 NL integration tests pass
- Run THE CRITICAL TEST with real LLM + real agent
- Add regression tests (8 tests)
- Add performance tests (4 tests)
- Ensure all 794+ tests pass
- **Generate Story 7 startup prompt when complete!**
