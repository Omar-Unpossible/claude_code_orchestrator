# ADR-019 Phase 3 Startup Prompt
# Previous Sessions: 2 | Phases Completed: Phase 1 & 2 (Core + Decision/Progress)
# Generated: 2025-11-15
# Branch: obra/adr-019-session-continuity

---

## ⚠️ FRESH CONTEXT - PHASE 3 IMPLEMENTATION

You are beginning **Phase 3** of ADR-019: Orchestrator Session Continuity Enhancements.

**Phases 1 & 2 are COMPLETE** - do not re-implement existing components!

This prompt provides everything needed to continue from where Session 2 left off.

---

## What's Already Done ✅

### Phase 1: Core Session Management (COMPLETE)
**Components** (100% functional, 93% coverage):
- ✅ `OrchestratorSessionManager` (96 lines, 99% coverage)
  - LLM lifecycle management
  - Self-handoff at >85% context
  - Exponential backoff retry logic
  - Thread-safe with RLock

- ✅ `CheckpointVerifier` (141 lines, 89% coverage)
  - Pre-checkpoint verification (git clean, tests pass)
  - Post-resume verification (files exist, branch match, age check)
  - Configurable checks (enable/disable individually)
  - Privacy-compliant (no raw reasoning)

**Integration Points** (DONE):
- `Orchestrator._initialize_session_continuity()` - initializes session manager
- `Orchestrator._check_and_handle_self_handoff()` - triggers handoff
- Called in: `execute_task()` and `execute_nl_command()`

**Tests** (61 tests, all passing):
- Unit tests: 47 (orchestrator_session_manager: 18, checkpoint_verifier: 29)
- Integration tests: 14 (test_session_continuity.py)

### Phase 2: Decision Records & Progress Reporting (COMPLETE)
**Components** (100% functional, 94% coverage):
- ✅ `DecisionRecordGenerator` (138 lines, 92% coverage)
  - Auto-generates ADR-format decision records
  - Significance detection (confidence ≥0.7)
  - Privacy-compliant (sanitizes reasoning, redacts secrets)
  - Markdown & JSON output

- ✅ `ProgressReporter` (93 lines, 100% coverage)
  - Structured JSON progress reports
  - Test status tracking
  - Context usage monitoring
  - Next steps prediction
  - ProductionLogger integration

**Tests** (53 tests, all passing):
- DecisionRecordGenerator: 29 tests
- ProgressReporter: 24 tests

### Summary of What Exists
- **Total Components**: 4 (all in `src/orchestration/session/`)
- **Total Tests**: 114 (all passing)
- **Coverage**: 94% overall
- **Code Quality**: Mypy 0 errors, Pylint 9.20/10

---

## Phase 3: Your Mission

Implement **SessionMetricsCollector** and integrate all Phase 1-3 components with Orchestrator.

### Story 3.1: SessionMetricsCollector (~150 lines)

**Purpose**: Track session patterns, handoff metrics, and context usage for analytics.

**File**: `src/orchestration/session/session_metrics_collector.py`

**Key Responsibilities**:
1. Track handoff frequency and patterns
2. Monitor context window usage over time
3. Collect decision confidence trends
4. Log session duration and operation counts
5. Generate session summary reports

**Metrics to Track**:
```python
{
    'session_id': str,
    'handoff_count': int,
    'total_operations': int,
    'avg_context_usage': float,
    'peak_context_usage': float,
    'operations_by_type': Dict[str, int],  # task_execution, nl_command, etc.
    'avg_confidence': float,
    'low_confidence_count': int,
    'session_duration_seconds': float,
    'context_zones_distribution': {  # green, yellow, red
        'green': int,
        'yellow': int,
        'red': int
    }
}
```

**Methods**:
- `__init__(config: Config)` - Initialize with config
- `record_operation(operation_type: str, context_mgr: Any, decision: Any)` - Track single operation
- `record_handoff(checkpoint_id: str, context_usage: float)` - Track handoff event
- `get_session_metrics() -> Dict[str, Any]` - Get current session metrics
- `generate_session_summary() -> str` - Generate markdown summary
- `reset_session()` - Reset for new session

**Configuration** (`config.yaml`):
```yaml
orchestrator:
  session_continuity:
    metrics:
      enabled: true
      track_context_zones: true
      track_confidence_trends: true
      summary_on_handoff: true
```

**Thread Safety**: Yes (use RLock for concurrent access)

**Integration Point**: Call from `Orchestrator` after each operation

---

## Story 3.2: Orchestrator Integration

**Purpose**: Wire all Phase 1-3 components into Orchestrator execution flow.

**Files to Modify**:
1. `src/orchestrator.py`
2. `src/orchestration/decision_engine.py`

### Integration Tasks

**Task A: Initialize Session Components** (`Orchestrator.__init__`)
```python
# Already done for Phase 1, add Phase 2-3:
self.decision_record_generator = DecisionRecordGenerator(
    config=self.config,
    state_manager=self.state_manager
)

self.progress_reporter = ProgressReporter(
    config=self.config,
    production_logger=self.production_logger  # if exists
)

self.session_metrics_collector = SessionMetricsCollector(
    config=self.config
)
```

**Task B: Record Decisions** (`DecisionEngine.decide_next_action`)
```python
def decide_next_action(self, context: Dict[str, Any]) -> Action:
    # ... existing decision logic ...

    action = Action(...)

    # NEW: Generate decision record if significant
    if self.decision_record_generator and self.decision_record_generator.is_significant(action):
        try:
            dr = self.decision_record_generator.generate_decision_record(action, context)
            self.decision_record_generator.save_decision_record(dr)
        except Exception as e:
            logger.warning("Failed to generate decision record: %s", e)

    return action
```

**Task C: Report Progress** (`Orchestrator.execute_task`, `execute_nl_command`)
```python
# After task/command execution
if self.progress_reporter:
    report = self.progress_reporter.generate_progress_report(
        session_id=self.session_manager.current_session_id,
        operation='task_execution',  # or 'nl_command'
        status='success',  # or 'failure'
        task=task,
        result=result,
        context_mgr=self.orchestrator_context_manager
    )
    self.progress_reporter.log_progress(report)
```

**Task D: Collect Metrics** (After each operation)
```python
if self.session_metrics_collector:
    self.session_metrics_collector.record_operation(
        operation_type='task_execution',
        context_mgr=self.orchestrator_context_manager,
        decision=action
    )
```

**Task E: Generate Summary on Handoff** (`OrchestratorSessionManager.restart_orchestrator_with_checkpoint`)
```python
# Before handoff
if self.session_metrics_collector:
    summary = self.session_metrics_collector.generate_session_summary()
    logger.info("Session summary before handoff:\n%s", summary)

    # Reset for new session
    self.session_metrics_collector.reset_session()
```

---

## Story 3.3: Testing Requirements

### Unit Tests for SessionMetricsCollector (~150 lines)
**File**: `tests/orchestration/session/test_session_metrics_collector.py`

**Test Coverage** (15-20 tests, target ≥90%):
1. Initialization and configuration
2. Record operation (various types)
3. Record handoff events
4. Get session metrics (structure validation)
5. Generate session summary (markdown format)
6. Reset session (clears metrics)
7. Context zone distribution tracking
8. Confidence trend tracking
9. Operation type counting
10. Thread safety (concurrent recording)

### Integration Tests (~100 lines)
**File**: `tests/integration/test_adr019_e2e.py`

**Scenarios** (8-10 tests):
1. Complete workflow: task execution with DR generation + progress reporting
2. Self-handoff with metrics collection
3. Multiple operations with metrics aggregation
4. Decision record saved to file (verify file contents)
5. Progress report logged to ProductionLogger
6. Session summary generated on handoff
7. Graceful degradation (components disabled)
8. Error handling (component failures don't break orchestration)

---

## Implementation Steps (Do in Order)

### Step 1: Implement SessionMetricsCollector
1. Create `src/orchestration/session/session_metrics_collector.py`
2. Follow patterns from Phase 1-2 components:
   - Type hints + Google docstrings
   - Thread-safe (RLock)
   - Configuration-driven
   - Exception handling with OrchestratorException
3. Update `src/orchestration/session/__init__.py` exports

### Step 2: Write Unit Tests
1. Create `tests/orchestration/session/test_session_metrics_collector.py`
2. Follow TEST_GUIDELINES.md (max 0.5s sleep, 5 threads, 20KB)
3. Target ≥90% coverage
4. Run: `pytest tests/orchestration/session/test_session_metrics_collector.py -v --cov=src/orchestration/session/session_metrics_collector.py`

### Step 3: Integrate with Orchestrator & DecisionEngine
1. Modify `src/orchestrator.py`:
   - Initialize all Phase 2-3 components
   - Add progress reporting after task/NL execution
   - Add metrics collection after operations
2. Modify `src/orchestration/decision_engine.py`:
   - Add decision record generation after decisions
3. DO NOT modify `OrchestratorSessionManager` (integration already done in Phase 1)

### Step 4: Write Integration Tests
1. Create `tests/integration/test_adr019_e2e.py`
2. Test complete workflows (task execution → decision → DR + progress + metrics)
3. Test self-handoff with all components working together

### Step 5: Verify All Gates Pass
Run complete test suite:
```bash
pytest tests/orchestration/session/ tests/integration/test_session_continuity.py tests/integration/test_adr019_e2e.py -v --cov=src/orchestration/session
```

**Verification Gate P3 Criteria**:
- [ ] SessionMetricsCollector implemented (≥90% coverage)
- [ ] All 4 components integrated with Orchestrator
- [ ] Decision records auto-generated and saved
- [ ] Progress reports logged to ProductionLogger
- [ ] Session metrics collected and summarized
- [ ] All tests pass (target: 140+ tests)
- [ ] Overall coverage ≥90%
- [ ] Mypy: 0 errors
- [ ] Pylint: ≥9.0

---

## Quick Start Commands

```bash
# Verify you're on correct branch
git branch --show-current  # Should be: obra/adr-019-session-continuity

# Verify existing components
ls -la src/orchestration/session/
# Should see: orchestrator_session_manager.py, checkpoint_verifier.py,
#             decision_record_generator.py, progress_reporter.py

# Run existing tests to verify everything works
pytest tests/orchestration/session/ tests/integration/test_session_continuity.py -v

# Should see: 114 tests passed

# Begin Phase 3
mkdir -p tests/integration  # Already exists
touch src/orchestration/session/session_metrics_collector.py
touch tests/orchestration/session/test_session_metrics_collector.py
touch tests/integration/test_adr019_e2e.py
```

---

## Critical Files to Read (In Order)

**Project Context**:
1. `CLAUDE.md` - Project guidelines, architecture rules
2. `docs/testing/TEST_GUIDELINES.md` - WSL2 crash prevention (CRITICAL!)
3. `docs/decisions/ADR-019-orchestrator-session-continuity.md` - Architecture decision

**Existing Implementations** (Reference for patterns):
4. `src/orchestration/session/orchestrator_session_manager.py` - Phase 1 example
5. `src/orchestration/session/decision_record_generator.py` - Phase 2 example
6. `src/orchestration/decision_engine.py` - Integration point for DRs

**Test Examples**:
7. `tests/orchestration/session/test_orchestrator_session_manager.py` - Unit test pattern
8. `tests/integration/test_session_continuity.py` - Integration test pattern

---

## Code Standards (MUST FOLLOW)

### Type Hints + Google Docstrings
```python
def record_operation(
    self,
    operation_type: str,
    context_mgr: Any,  # Type: OrchestratorContextManager
    decision: Any  # Type: Action
) -> None:
    """Record a single operation for metrics.

    Args:
        operation_type: Type of operation (task_execution, nl_command, etc.)
        context_mgr: Orchestrator context manager
        decision: Decision action from DecisionEngine

    Raises:
        OrchestratorException: If recording fails
    """
```

### Configuration-Driven
```python
# Load from config, never hardcode
self.enabled = config.get(
    'orchestrator.session_continuity.metrics.enabled', True
)
```

### Thread Safety
```python
from threading import RLock

class SessionMetricsCollector:
    def __init__(self, config):
        self._lock = RLock()
        self._metrics = {}

    def record_operation(self, ...):
        with self._lock:
            # Thread-safe operation
            self._metrics['total_operations'] += 1
```

### Exception Handling
```python
try:
    # Operation
    pass
except Exception as e:
    raise OrchestratorException(
        f"Failed to record metrics: {e}",
        context={'operation_type': operation_type},
        recovery="Check metrics collector configuration"
    ) from e
```

---

## Testing Constraints (WSL2 Survival)

**CRITICAL - Read `docs/testing/TEST_GUIDELINES.md`**:
- ⚠️ Max 0.5s sleep per test (use `fast_time` fixture)
- ⚠️ Max 5 threads per test (with timeout= on join)
- ⚠️ Max 20KB memory allocation per test
- ⚠️ Mark heavy tests with `@pytest.mark.slow`

**Fixtures to Use**:
- `test_config` - Mock Config object
- `fast_time` - Mock time.sleep() for instant execution
- `tmp_path` - Temporary directory (auto-cleanup)

---

## Performance Targets

- **Metrics Collection**: <10ms per operation
- **Session Summary Generation**: <100ms
- **Decision Record Generation**: <50ms per record
- **Progress Report Generation**: <20ms per report

---

## Expected Deliverables

### Code
1. `src/orchestration/session/session_metrics_collector.py` (~150 lines)
2. Modified `src/orchestrator.py` (+100 lines integration)
3. Modified `src/orchestration/decision_engine.py` (+20 lines)
4. Updated `src/orchestration/session/__init__.py` (exports)

### Tests
5. `tests/orchestration/session/test_session_metrics_collector.py` (~200 lines, 15-20 tests)
6. `tests/integration/test_adr019_e2e.py` (~150 lines, 8-10 tests)

### Total
- **Implementation**: ~270 lines
- **Tests**: ~350 lines
- **Total Tests**: 140+ (existing 114 + new 25-30)
- **Coverage Target**: ≥90%

---

## Git Workflow

```bash
# All work on existing branch
git branch  # Verify: obra/adr-019-session-continuity

# After implementation
git add src/orchestration/session/session_metrics_collector.py
git add tests/orchestration/session/test_session_metrics_collector.py

# After integration
git add src/orchestrator.py src/orchestration/decision_engine.py
git add tests/integration/test_adr019_e2e.py

# Commit Phase 3
git commit -m "feat(adr-019): Implement SessionMetricsCollector and complete integration (Phase 3)

SessionMetricsCollector (150 lines, ≥90% coverage):
- Track handoff frequency and patterns
- Monitor context usage trends
- Collect decision confidence metrics
- Generate session summaries
- Thread-safe metrics collection

Orchestrator Integration:
- Initialize all Phase 1-3 components
- Generate decision records after decisions
- Report progress after task/NL execution
- Collect metrics after operations
- Generate summary on handoff

Integration Tests (25-30 tests):
- E2E workflow validation
- Component interaction testing
- Error handling scenarios

Verification Gate P3: PASSED ✅
- All components integrated
- 140+ tests passing
- ≥90% coverage
- Mypy 0 errors
- Pylint ≥9.0

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
"
```

---

## Success Criteria (Gate P3)

**Must pass ALL**:
- ✅ SessionMetricsCollector implemented
- ✅ Integration complete (Orchestrator + DecisionEngine)
- ✅ Decision records auto-generated and saved
- ✅ Progress reports logged
- ✅ Session metrics collected
- ✅ Tests: 140+ passing
- ✅ Coverage: ≥90%
- ✅ Mypy: 0 errors
- ✅ Pylint: ≥9.0

---

## Context Window Management

**Monitor your context after each step**:
- After implementing SessionMetricsCollector: ~25%
- After unit tests: ~40%
- After integration: ~60%
- After integration tests: ~75%

**If context reaches 80%**: Generate continuation prompt and hand off.

---

## Estimated Timeline

- **SessionMetricsCollector**: 1-2 hours
- **Unit Tests**: 1-2 hours
- **Integration**: 1-2 hours
- **Integration Tests**: 1-2 hours
- **Total**: 4-8 hours (1 session)

---

## START HERE

```bash
# 1. Verify branch and existing work
git branch --show-current
pytest tests/orchestration/session/ -v

# 2. Read critical files (in order)
cat CLAUDE.md
cat docs/testing/TEST_GUIDELINES.md
cat src/orchestration/session/decision_record_generator.py  # Reference

# 3. Create SessionMetricsCollector
touch src/orchestration/session/session_metrics_collector.py
# Implement following DecisionRecordGenerator patterns

# 4. Write tests
touch tests/orchestration/session/test_session_metrics_collector.py
# Follow test_decision_record_generator.py patterns

# 5. Integrate and test
# Modify src/orchestrator.py
# Modify src/orchestration/decision_engine.py
# Create tests/integration/test_adr019_e2e.py
```

---

**REMEMBER**:
- Phase 1 & 2 are COMPLETE - don't re-implement!
- Focus on SessionMetricsCollector + Integration
- Follow existing patterns from Phase 1-2
- Test as you go (unit tests before integration)
- Monitor YOUR context window

**You have everything needed to complete Phase 3. Begin implementation now!** 🚀

---

**Session**: 3 of ~3-4
**Phases**: 1 ✅ 2 ✅ 3 ⏳
**Estimated**: 4-8 hours to complete ADR-019
