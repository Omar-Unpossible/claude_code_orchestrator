# Story 0 + Enhancements Implementation Plan

**Date**: November 13, 2025
**Version**: 1.0
**Status**: Ready for Implementation
**Total Effort**: 25-27 hours (3-4 days)
**Target Release**: v1.7.2

---

## Executive Summary

This plan completes the remaining work from ADR-017 evaluation:

1. **Story 0 (Testing Infrastructure Foundation)**: Complete the missing 27/44 tests
2. **Test Execution & Validation**: Run all tests and validate the system
3. **Enhancement 3**: Add NL Command Completion Tests (if feature exists)
4. **Enhancement 4**: Consolidate Test Documentation
5. **Enhancement 5**: Extract Common Test Fixtures

**Benefits**:
- ✅ Comprehensive integration test coverage (0% → 100% for LLM/agent)
- ✅ THE CRITICAL TEST validates entire system E2E
- ✅ Clean, maintainable test infrastructure
- ✅ Reduced documentation clutter
- ✅ DRY principle for test fixtures

---

## Phase 1: Complete Story 0 Testing Infrastructure

**Duration**: 16 hours (2 days)
**Priority**: P0 - Foundation

### Part A: LLM Integration Tests (15 tests, 5-8 minutes runtime)

**File**: `tests/integration/test_llm_connectivity.py`

#### Test Class 1: LLM Connectivity Tests (6 tests)

```python
class TestLLMConnectivity:
    """Validate LLM connectivity across providers."""

    def test_ollama_connection_success(self):
        """Test successful connection to Ollama."""
        # Given: Ollama is running
        # When: Connect to Ollama
        # Then: Connection succeeds, model list returned

    def test_ollama_connection_failure_wrong_port(self):
        """Test graceful handling of wrong port."""
        # Given: Ollama configured with wrong port
        # When: Attempt connection
        # Then: ConnectionError raised with helpful message

    def test_ollama_connection_failure_service_down(self):
        """Test graceful handling when Ollama service down."""
        # Given: Ollama service not running
        # When: Attempt connection
        # Then: ConnectionError raised, fallback message shown

    def test_openai_codex_connection_success(self):
        """Test OpenAI Codex connection (if configured)."""
        # Given: OpenAI API key configured
        # When: Connect to OpenAI Codex
        # Then: Connection succeeds, models available
        # Skip if: No API key configured

    def test_llm_timeout_handling(self):
        """Test LLM request timeout handling."""
        # Given: LLM configured with short timeout (1s)
        # When: Send request that exceeds timeout
        # Then: TimeoutError raised, retry suggested

    def test_llm_retry_on_transient_failure(self):
        """Test retry logic for transient failures."""
        # Given: Mock LLM that fails once, succeeds second time
        # When: Send request
        # Then: Retry succeeds, no error to user
```

**Implementation Details**:
- Use `pytest.mark.integration` for slow tests
- Use `pytest.mark.requires_ollama` for Ollama-dependent tests
- Use `pytest.mark.skipif` for optional provider tests (OpenAI Codex)
- Mock network failures for timeout/retry tests
- Real Ollama connection for success tests

---

#### Test Class 2: LLM Switching Tests (4 tests)

```python
class TestLLMSwitching:
    """Validate LLM provider switching."""

    def test_switch_ollama_to_openai_codex(self):
        """Test switching from Ollama to OpenAI Codex."""
        # Given: Orchestrator using Ollama
        # When: Switch to OpenAI Codex via reconnect_llm()
        # Then: Provider switched, new requests use OpenAI Codex

    def test_switch_openai_codex_to_ollama(self):
        """Test switching from OpenAI Codex to Ollama."""
        # Given: Orchestrator using OpenAI Codex
        # When: Switch to Ollama via reconnect_llm()
        # Then: Provider switched, new requests use Ollama

    def test_switch_maintains_state_manager_state(self):
        """Test switching preserves StateManager state."""
        # Given: Project and tasks exist in StateManager
        # When: Switch LLM provider
        # Then: StateManager state unchanged, entities still accessible

    def test_switch_during_pending_operation(self):
        """Test switching while operation in progress."""
        # Given: Long-running LLM request in progress
        # When: Attempt to switch provider
        # Then: Switch deferred until operation completes OR error raised
```

**Implementation Details**:
- Use `orchestrator.reconnect_llm()` for switching
- Verify `orchestrator.llm` attribute changes
- Check StateManager entities before/after switch
- Test concurrent access with threading (max 2 threads, timeout 10s)

---

#### Test Class 3: LLM Performance Baselines (5 tests)

```python
class TestLLMPerformance:
    """Establish performance baselines for LLM operations."""

    def test_intent_classification_latency_baseline(self):
        """Measure intent classification latency baseline."""
        # Given: 10 sample NL commands
        # When: Classify each command (COMMAND vs QUESTION)
        # Then: P50 < 500ms, P95 < 1000ms, P99 < 1500ms

    def test_entity_extraction_latency_baseline(self):
        """Measure entity extraction latency baseline."""
        # Given: 10 sample commands with entities
        # When: Extract entities from each
        # Then: P50 < 800ms, P95 < 1500ms, P99 < 2000ms

    def test_full_nl_pipeline_latency_baseline(self):
        """Measure full NL pipeline latency (5 stages)."""
        # Given: 20 sample NL commands
        # When: Process through full pipeline (intent → params)
        # Then: P50 < 1.5s, P95 < 3s, P99 < 4s

    def test_intent_classification_accuracy_baseline(self):
        """Measure intent classification accuracy."""
        # Given: 50 labeled commands (25 COMMAND, 25 QUESTION)
        # When: Classify all commands
        # Then: Accuracy ≥ 95%, precision ≥ 95%, recall ≥ 95%

    def test_entity_extraction_accuracy_baseline(self):
        """Measure entity extraction accuracy."""
        # Given: 50 labeled commands with ground truth entities
        # When: Extract entities from all commands
        # Then: Accuracy ≥ 90% (entity type + identifier correct)
```

**Implementation Details**:
- Use `time.perf_counter()` for latency measurements
- Collect P50/P95/P99 percentiles using `numpy.percentile()`
- Store baselines in test output for regression detection
- Use labeled test dataset from `tests/fixtures/nl_test_dataset.json`
- Calculate accuracy metrics: (true_positives + true_negatives) / total

---

### Part B: Agent Integration Tests (12 tests, 10-15 minutes runtime)

**File**: `tests/integration/test_agent_connectivity.py`

#### Test Class 1: Agent Connectivity Tests (4 tests)

```python
class TestAgentConnectivity:
    """Validate Claude Code agent connectivity."""

    def test_claude_code_local_agent_available(self):
        """Test Claude Code local agent is available."""
        # Given: Claude Code CLI installed
        # When: Check agent availability
        # Then: Agent responds, version returned

    def test_agent_send_receive_prompts(self):
        """Test agent can send and receive prompts."""
        # Given: Agent available
        # When: Send simple prompt "print hello world in Python"
        # Then: Agent returns valid response with code

    def test_fresh_session_creation_per_iteration(self):
        """Test fresh session created for each iteration."""
        # Given: Orchestrator with session model
        # When: Execute 2 tasks sequentially
        # Then: Each gets new session, session IDs different

    def test_session_isolation_verified(self):
        """Test sessions are isolated from each other."""
        # Given: Task 1 creates file 'test1.py'
        # When: Task 2 executes in new session
        # Then: Task 2 doesn't see Task 1's context (clean slate)
```

**Implementation Details**:
- Use real Claude Code agent (not mocked)
- Test with `--print` flag for subprocess execution
- Verify session isolation via workspace file inspection
- Use `temp_workspace` fixture for clean testing

---

#### Test Class 2: Orchestrator Workflow Tests (8 tests)

```python
class TestOrchestratorWorkflows:
    """Validate end-to-end orchestrator workflows."""

    def test_full_workflow_create_project_to_execution(self):
        """THE CRITICAL TEST - Full E2E workflow validation.

        This is the single most important test. It validates:
        - LLM connectivity works
        - NL command parsing works
        - Task creation works
        - Orchestrator execution works
        - Agent communication works
        - File operations work
        - Quality validation works

        If this test fails, core product is broken.
        """
        # Given: Empty workspace
        # When:
        #   1. Create project via StateManager
        #   2. Create task via NL command: "Create a Python hello world script"
        #   3. Execute task through orchestrator (REAL agent)
        # Then:
        #   1. File created: hello_world.py
        #   2. File contains valid Python code
        #   3. Code quality acceptable (>= 70%)
        #   4. Metrics tracked correctly
        #   5. Task marked as completed

    def test_workflow_with_quality_feedback_loop(self):
        """Test workflow with iterative improvement."""
        # Given: Mock agent returns low-quality code first iteration
        # When: Execute task through orchestrator
        # Then: DecisionEngine triggers RETRY, second iteration succeeds

    def test_workflow_with_confirmation_update_delete(self):
        """Test workflow with confirmation for UPDATE/DELETE."""
        # Given: NL command "Delete task 5"
        # When: Execute through orchestrator (non-interactive mode)
        # Then: Safety breakpoint triggered, operation aborted

    def test_multi_task_epic_execution(self):
        """Test multi-task epic execution."""
        # Given: Epic with 3 stories
        # When: Execute epic via orchestrator.execute_epic()
        # Then: All 3 stories executed sequentially, sessions isolated

    def test_task_dependencies_m9(self):
        """Test task dependency resolution (M9 feature)."""
        # Given: Task B depends on Task A
        # When: Execute Task B
        # Then: Task A executed first, Task B executes after

    def test_git_integration_e2e_m9(self):
        """Test Git integration end-to-end (M9 feature)."""
        # Given: Git enabled in config
        # When: Execute task that modifies files
        # Then: Commit created, commit message accurate

    def test_session_management_per_iteration(self):
        """Test per-iteration session model."""
        # Given: Task with max_iterations=3
        # When: Execute task (fails twice, succeeds third)
        # Then: 3 separate sessions created, context preserved via StateManager

    def test_context_continuity_across_sessions(self):
        """Test context continuity across fresh sessions."""
        # Given: Task 1 creates entity 'User' in database
        # When: Task 2 executes (new session)
        # Then: Task 2 can access 'User' via StateManager (context preserved)
```

**Implementation Details**:
- Use real agent for THE CRITICAL TEST
- Mock agent for quality feedback test (control quality scores)
- Use `pytest.mark.slow` for multi-task tests (>30s)
- Verify Git commits with `git log --oneline`
- Check session IDs in orchestrator logs

---

### Part C: Structured Logging & Metrics Foundation

**Files**:
- `src/core/logging_config.py` (enhance existing or create)
- `src/core/metrics.py` (enhance existing or create)

#### Structured Logging Enhancement

```python
# src/core/logging_config.py

import logging
import json
from datetime import datetime
from typing import Any, Dict

class StructuredLogger:
    """Structured JSON logging for Obra."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        self.logger.addHandler(handler)

    def log_event(self, event: str, **kwargs):
        """Log structured event with metadata."""
        self.logger.info(json.dumps({
            'timestamp': datetime.now().isoformat(),
            'event': event,
            **kwargs
        }))

class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, 'event'):
            log_data['event'] = record.event

        return json.dumps(log_data)
```

**Integration Points**:
1. `src/llm/local_llm_interface.py` - Log LLM requests
2. `src/agents/claude_code_local_agent.py` - Log agent executions
3. `src/nl/nl_command_processor.py` - Log NL command processing
4. `src/orchestrator.py` - Log orchestration steps

**Events to Log**:
- `llm_request`: provider, model, latency_ms, success, error
- `agent_execution`: agent_type, task_id, iteration, duration_s, files_modified
- `nl_command`: command, intent, operation, entity_type, success
- `orchestrator_step`: step, task_id, duration_ms, success

---

#### Metrics Collection Enhancement

```python
# src/core/metrics.py

from typing import Dict, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics

@dataclass
class MetricPoint:
    """Single metric measurement."""
    timestamp: datetime
    value: float
    metadata: Dict = field(default_factory=dict)

class MetricsCollector:
    """Collect and aggregate metrics."""

    def __init__(self):
        self.metrics: Dict[str, List[MetricPoint]] = {}

    def record(self, metric_name: str, value: float, **metadata):
        """Record a metric value."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        self.metrics[metric_name].append(
            MetricPoint(datetime.now(), value, metadata)
        )

    def get_aggregates(self, metric_name: str, window_minutes: int = 5) -> Dict:
        """Get aggregates for metric over time window."""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        recent = [m for m in self.metrics.get(metric_name, []) if m.timestamp > cutoff]

        if not recent:
            return {}

        values = [m.value for m in recent]
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'p95': self._percentile(values, 0.95),
            'p99': self._percentile(values, 0.99),
        }

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile."""
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]

# Global metrics collector
metrics = MetricsCollector()
```

**Metrics to Collect**:
- `llm_request_latency_ms`: Latency of LLM requests
- `agent_execution_duration_s`: Duration of agent executions
- `nl_command_latency_ms`: Latency of NL command processing
- `task_execution_duration_s`: Duration of task executions

---

#### CLI Health Command

**File**: `src/cli.py` (add command)

```python
@click.command('health')
def health():
    """Display system health status."""
    from src.core.metrics import metrics
    from src.llm.llm_registry import LLMRegistry
    from src.state.state_manager import StateManager
    from src.config import Config

    config = Config.load()

    # Check LLM availability
    llm_available = False
    llm_name = "Unknown"
    try:
        llm_plugin = LLMRegistry.get(config.get('llm.type'))()
        llm_plugin.initialize(config.get('llm'))
        llm_available = llm_plugin.is_available()
        llm_name = f"{config.get('llm.type')} ({config.get('llm.model', 'default')})"
    except Exception as e:
        pass

    # Check database availability
    db_available = False
    try:
        state = StateManager(config)
        db_available = True
    except Exception:
        pass

    # Get LLM metrics
    llm_metrics = metrics.get_aggregates('llm_request_latency_ms', window_minutes=5)

    # Display health status
    status = "HEALTHY" if (llm_available and db_available) else "DEGRADED"
    status_color = click.style(status, fg='green' if status == "HEALTHY" else 'yellow')

    click.echo(f"Status: {status_color}")
    click.echo(f"\nLLM: {llm_name}")
    click.echo(f"  - Available: {'Yes' if llm_available else 'No'}")

    if llm_metrics:
        success_rate = llm_metrics.get('success_rate', 0) * 100
        click.echo(f"  - Success Rate: {success_rate:.1f}% (last 5 min)")
        click.echo(f"  - Latency P95: {llm_metrics.get('p95', 0):.0f}ms")

    click.echo(f"\nDatabase: {'Available' if db_available else 'Unavailable'}")
```

**Usage**:
```bash
$ obra health
Status: HEALTHY ✅
LLM: ollama (qwen2.5-coder:32b)
  - Available: Yes
  - Success Rate: 98.2% (last 5 min)
  - Latency P95: 1234ms
Database: Available
```

---

### Part D: Story 0 Acceptance Criteria

**Before marking Story 0 as complete, verify**:

- ✅ **Tier 1 health checks** (7 tests) implemented and passing
- ✅ **Tier 1 smoke tests** (10 tests) implemented and passing
- ✅ **Tier 2 LLM integration tests** (15 tests) implemented and passing
- ✅ **Tier 3 agent integration tests** (12 tests) implemented and passing
- ✅ **THE CRITICAL TEST** passing (test_full_workflow_create_project_to_execution)
- ✅ **Structured logging** integrated at all critical paths
- ✅ **Metrics collection** functional
- ✅ **obra health command** working
- ✅ **CI/CD**: Tier 1 tests run on every commit (<2 min)
- ✅ **Documentation**: Testing strategy documented

---

## Phase 2: Test Execution & Validation

**Duration**: 2 hours
**Priority**: P0 - Quality Gate

### Test Execution Plan

**Step 1: Run Tier 1 Tests (Fast Gate)**
```bash
# Health checks + smoke tests (17 tests, <2 minutes)
pytest tests/health tests/smoke -v --timeout=120

# Expected output:
# ====== 17 passed in 1.XX minutes ======
```

**Success Criteria**:
- All 17 tests passing
- Total time < 2 minutes
- No warnings or errors

---

**Step 2: Run Tier 2 LLM Integration Tests**
```bash
# LLM connectivity tests (15 tests, 5-8 minutes)
pytest tests/integration/test_llm_connectivity.py -v -m integration --timeout=600

# Expected output:
# ====== 15 passed in X.XX minutes ======
```

**Success Criteria**:
- All 15 tests passing
- Total time 5-8 minutes
- Performance baselines documented (P50/P95/P99 latencies)

---

**Step 3: Run Tier 3 Agent Integration Tests**
```bash
# Agent connectivity tests (12 tests, 10-15 minutes)
pytest tests/integration/test_agent_connectivity.py -v -m integration --timeout=1800

# Expected output:
# ====== 12 passed in X.XX minutes ======
```

**Success Criteria**:
- All 12 tests passing
- Total time 10-15 minutes
- THE CRITICAL TEST passing (most important validation)

---

**Step 4: Run THE CRITICAL TEST Standalone**
```bash
# THE CRITICAL TEST (1 test, 1-2 minutes)
pytest tests/integration/test_agent_connectivity.py::TestOrchestratorWorkflows::test_full_workflow_create_project_to_execution -v

# Expected output:
# ====== 1 passed in X.XX minutes ======
```

**Success Criteria**:
- Test passes in <2 minutes
- File created by agent exists
- Code quality >= 70%
- Metrics tracked correctly

**Failure Handling**:
- If this test fails, **DO NOT PROCEED**
- This test validates core product functionality
- Debug and fix before continuing

---

**Step 5: Run All Tests (Regression Validation)**
```bash
# Full test suite (800+ tests, ~30 minutes)
pytest tests/ -v --timeout=3600 --cov=src --cov-report=term

# Expected output:
# ====== 8XX passed in XX.XX minutes ======
# Coverage: 88% or higher
```

**Success Criteria**:
- All 800+ tests passing (100% pass rate)
- Coverage >= 88%
- No new test failures introduced
- No coverage regressions

---

**Step 6: Performance Validation**
```bash
# Run performance benchmarks
pytest tests/integration/test_adr017_performance.py -v

# Expected output:
# test_nl_command_latency_p95 PASSED (P95: X.XXs < 3s ✓)
# test_throughput PASSED (XX cmd/min > 40 ✓)
```

**Success Criteria**:
- P95 latency < 3s
- Throughput > 40 cmd/min
- No performance regressions from v1.7.1

---

### Test Validation Checklist

```markdown
## Story 0 Test Validation

- [ ] Tier 1 (17 tests): All passing in <2 min
- [ ] Tier 2 (15 tests): All passing in 5-8 min
- [ ] Tier 3 (12 tests): All passing in 10-15 min
- [ ] THE CRITICAL TEST: Passing in <2 min ⭐
- [ ] Full suite (800+ tests): All passing in ~30 min
- [ ] Coverage: >= 88%
- [ ] Performance: P95 < 3s, throughput > 40 cmd/min
- [ ] obra health: Command works, shows correct status
- [ ] Structured logging: Events logged at critical paths
- [ ] Metrics: Collected and aggregated correctly

## Ready for Phase 3?
- [ ] All checkboxes above are checked
- [ ] No test failures
- [ ] No coverage regressions
- [ ] Performance targets met
```

---

## Phase 3: Enhancement 3 - NL Command Completion Tests

**Duration**: 4 hours
**Priority**: P2 - Nice-to-Have

### Step 1: Discovery (1 hour)

**Check if NL Command Completion feature exists**:

```bash
# Search for completion-related files
find . -name "*completion*" -type f | grep -v node_modules | grep -v .git

# Search for completion in code
grep -r "completion\|autocomplete\|tab_complete" src/ --include="*.py" | head -20

# Check git history
git log --all --oneline --grep="completion" | head -10

# Check documentation
ls -la docs/development/ | grep -i completion
```

**Outcomes**:

**A) Feature EXISTS** → Proceed to Step 2
**B) Feature DOES NOT EXIST** → Skip to Step 4 (document as future enhancement)

---

### Step 2: Understand Feature (1 hour)

If feature exists, analyze:

1. **Read implementation**:
   - Locate completion code (likely in `src/cli.py` or `src/interactive.py`)
   - Understand completion algorithm (static list? LLM-based? Fuzzy matching?)
   - Identify completion triggers (TAB key? double-TAB? other?)

2. **Check existing tests**:
   ```bash
   grep -r "completion\|autocomplete" tests/ --include="*.py"
   ```

3. **Identify test gaps**:
   - Are there ANY tests for completion?
   - What scenarios are covered?
   - What's missing?

---

### Step 3: Implement Tests (2 hours)

**File**: `tests/test_nl_command_completion.py`

```python
import pytest
from src.cli import get_completions  # Example - adjust based on actual API

class TestNLCommandCompletion:
    """Test natural language command completion."""

    def test_command_completion_basic(self):
        """Test basic command completion."""
        # Given: User types "create e"
        # When: Request completions
        # Then: Suggestions include ["epic", "entity"]

    def test_command_completion_entity_types(self):
        """Test entity type completion."""
        # Given: User types "create epic for "
        # When: Request completions
        # Then: Suggestions include common entity names or "..."

    def test_command_completion_operations(self):
        """Test operation completion."""
        # Given: User types "mar"
        # When: Request completions
        # Then: Suggestions include ["mark"]

    def test_command_completion_fuzzy_matching(self):
        """Test fuzzy matching in completion."""
        # Given: User types "crt"
        # When: Request completions
        # Then: Suggestions include ["create"] (fuzzy match)

    def test_command_completion_context_aware(self):
        """Test context-aware completion."""
        # Given: User types "update task " with project 1 active
        # When: Request completions
        # Then: Suggestions include task IDs from project 1

    def test_command_completion_no_suggestions(self):
        """Test no suggestions for invalid input."""
        # Given: User types "asdfghjkl"
        # When: Request completions
        # Then: No suggestions returned
```

**Test Count**: 10-15 tests depending on feature complexity

---

### Step 4: Document Findings

**If feature EXISTS**:

Create `docs/guides/NL_COMMAND_COMPLETION_GUIDE.md`:
```markdown
# Natural Language Command Completion Guide

## Overview
Obra supports intelligent command completion for natural language input.

## Usage
[Instructions on how to use completion]

## Examples
[Completion examples]

## Implementation
[Technical details for developers]

## Tests
- 15 tests in `tests/test_nl_command_completion.py`
- Coverage: X%
```

**If feature DOES NOT EXIST**:

Add to `docs/design/enhancements/NL_COMMAND_COMPLETION_PROPOSAL.md`:
```markdown
# Proposal: Natural Language Command Completion

## Motivation
Improve UX by providing intelligent suggestions as users type NL commands.

## Design
[Proposed design]

## Effort
Estimated 8-12 hours implementation.
```

---

### Enhancement 3 Acceptance Criteria

- [ ] Discovery complete: Feature exists or documented as future enhancement
- [ ] If exists: Implementation understood, test gaps identified
- [ ] If exists: 10-15 tests implemented and passing
- [ ] If exists: User guide created
- [ ] If not exists: Proposal document created
- [ ] Documentation updated

---

## Phase 4: Enhancement 4 - Consolidate Test Documentation

**Duration**: 2 hours
**Priority**: P3 - Cleanup

### Step 1: Audit Documentation (30 minutes)

**Inventory ADR017 documentation files**:

```bash
# Find all ADR017 files
find docs/ -name "*ADR017*" -o -name "*adr017*" | sort

# Expected files (14+):
# - ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml
# - ADR017_ENHANCED_WITH_TESTING.yaml
# - ADR017_EPIC_BREAKDOWN.md
# - ADR017_TESTING_ENHANCEMENT_SUMMARY.md
# - ADR017_COMPLETE_PLAN_SUMMARY.md
# - ADR017_STARTUP_PROMPT_V2.md
# - ADR017_STORY2_STARTUP_PROMPT.md
# - ADR017_STORY3_STARTUP_PROMPT.md
# - ADR017_STORY4_STARTUP_PROMPT.md
# - ADR017_STORY5_STARTUP_PROMPT.md
# - ADR017_STORY6_STARTUP_PROMPT.md
# - ADR017_STORY7_STARTUP_PROMPT.md
# - ADR017_STORY8_STARTUP_PROMPT.md
# - ADR017_STORY9_STARTUP_PROMPT.md
# - ADR017_IMPLEMENTATION_EVALUATION_REPORT.md (NEW - from this evaluation)
```

**Categorize files**:
- **Keep (Active)**: 3 files
- **Archive (Historical)**: 11+ files

---

### Step 2: Archive Historical Files (30 minutes)

**Create archive directory**:
```bash
mkdir -p docs/archive/adr017_planning
mkdir -p docs/archive/adr017_startup_prompts
```

**Move files to archive**:

```bash
# Archive planning documents (keep enhanced plan and summary)
mv docs/development/ADR017_COMPLETE_PLAN_SUMMARY.md \
   docs/archive/adr017_planning/

# Archive startup prompts (all 8 story prompts)
mv docs/development/ADR017_STORY2_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/
mv docs/development/ADR017_STORY3_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/
mv docs/development/ADR017_STORY4_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/
mv docs/development/ADR017_STORY5_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/
mv docs/development/ADR017_STORY6_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/
mv docs/development/ADR017_STORY7_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/
mv docs/development/ADR017_STORY8_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/
mv docs/development/ADR017_STORY9_STARTUP_PROMPT.md \
   docs/archive/adr017_startup_prompts/

# Archive original startup prompt
mv docs/development/ADR017_STARTUP_PROMPT_V2.md \
   docs/archive/adr017_planning/
```

**Keep in active docs**:
- `ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml` (original plan)
- `ADR017_ENHANCED_WITH_TESTING.yaml` (enhanced plan with Story 0/10)
- `ADR017_IMPLEMENTATION_EVALUATION_REPORT.md` (evaluation results)

---

### Step 3: Create Archive README (15 minutes)

**File**: `docs/archive/adr017_planning/README.md`

```markdown
# ADR-017 Planning Archive

This directory contains historical planning documents for ADR-017 (Unified Execution Architecture).

## Active Documents (See docs/development/)
- `ADR017_UNIFIED_EXECUTION_IMPLEMENTATION_PLAN.yaml` - Original 9-story plan
- `ADR017_ENHANCED_WITH_TESTING.yaml` - Enhanced 11-story plan with testing
- `ADR017_IMPLEMENTATION_EVALUATION_REPORT.md` - Post-implementation evaluation

## Archived Planning Documents
- `ADR017_COMPLETE_PLAN_SUMMARY.md` - Planning summary (superseded by evaluation)
- `ADR017_STARTUP_PROMPT_V2.md` - Original startup prompt

## Archived Startup Prompts
See `docs/archive/adr017_startup_prompts/` for per-story execution prompts.

## Implementation Timeline
- **Planning**: November 12, 2025
- **Implementation**: November 13, 2025 (Stories 1-9)
- **Releases**: v1.7.0 (Stories 1-7), v1.7.1 (Stories 8-9)
- **Evaluation**: November 13, 2025

## Key Outcomes
- ✅ 9/11 stories completed (82%)
- ✅ 794+ tests passing (100% pass rate)
- ✅ Unified execution architecture operational
- ⚠️ Story 0: Partial (17/44 tests)
- ❌ Story 10: Deferred to v1.7.2+
```

---

### Step 4: Create Implementation Summary (45 minutes)

**File**: `docs/development/ADR017_IMPLEMENTATION_SUMMARY.md`

```markdown
# ADR-017 Implementation Summary

**Epic**: Unified Execution Architecture
**Status**: ✅ COMPLETE (9/11 stories)
**Release**: v1.7.0 (November 13, 2025), v1.7.1 (November 13, 2025)
**Next Steps**: Story 0 completion (v1.7.2), Story 10 observability (v1.8.0)

---

## What Was Implemented

### Core Architecture (Stories 1-7) - v1.7.0
- ✅ **Unified execution path** - All NL commands route through orchestrator
- ✅ **IntentToTaskConverter** - Converts NL intents to Task objects (504 lines)
- ✅ **NLQueryHelper** - Read-only query operations (479 lines)
- ✅ **24 integration tests** - NL routing, regression, performance validation

### Safety Enhancements (Stories 8-9) - v1.7.1
- ✅ **Confirmation workflow** - Human-in-the-loop for destructive operations
- ✅ **Rich UI** - Color-coded prompts with dry-run simulation (24 tests)

### Test Coverage
- ✅ **794+ tests passing** (100% pass rate)
- ✅ **88% code coverage** maintained
- ✅ **Performance validated** - P95 < 3s, throughput > 40 cmd/min

---

## What Was Deferred

### Story 0: Testing Infrastructure (Partial)
**Completed**: Health checks (7), smoke tests (10)
**Deferred**: LLM integration (15), agent integration (12), THE CRITICAL TEST
**Status**: Planned for v1.7.2 (16 hours)

### Story 10: Observability Enhancements
**Deferred**: Correlation IDs, enhanced logging, metrics v2, CLI commands
**Status**: Planned for v1.8.0 (8 hours)

---

## Key Files

### Implementation
- `src/orchestration/intent_to_task_converter.py` (Story 2)
- `src/nl/nl_query_helper.py` (Story 3)
- `src/orchestrator.py` (Story 5 - execute_nl_command method)
- `tests/integration/test_orchestrator_nl_integration.py` (Story 6)

### Documentation
- `docs/decisions/ADR-017-unified-execution-architecture.md` (ADR)
- `docs/guides/ADR017_MIGRATION_GUIDE.md` (Migration guide)
- `docs/guides/NL_COMMAND_GUIDE.md` (User guide - updated)
- `docs/development/ADR017_IMPLEMENTATION_EVALUATION_REPORT.md` (Evaluation)

### Planning (Archive)
- `docs/archive/adr017_planning/` - Historical planning documents
- `docs/archive/adr017_startup_prompts/` - Per-story execution prompts

---

## Lessons Learned

### Successes
1. **Test-first approach worked** - Even partial Story 0 provided confidence
2. **Incremental implementation** - Per-story execution enabled fast iteration
3. **Real-world validation** - 100% test pass rate, no production issues
4. **Documentation quality** - Comprehensive migration guide eased adoption

### Challenges
1. **Story 0 deferred** - Test-first approach partially abandoned (time pressure)
2. **Story 10 deferred** - Observability not critical for single-user deployment
3. **API changes** - Breaking changes to internal APIs (mitigated by migration guide)

### Improvements for Next Epic
1. **Commit to test-first** - Don't defer testing infrastructure
2. **Prioritize observability** - Build monitoring from day 1
3. **Smaller stories** - 16-hour stories are too large (split into 8-hour chunks)

---

## Next Steps

### v1.7.2 (Recommended)
- Complete Story 0 (16 hours) - See `STORY0_AND_ENHANCEMENTS_IMPLEMENTATION_PLAN.md`
- Consolidate documentation (2 hours)
- Extract test fixtures (3 hours)

### v1.8.0 (Optional)
- Implement Story 10 (8 hours) - Production observability
- Add NL command completion tests (4 hours)

---

**Last Updated**: November 13, 2025
**Maintainer**: Claude Code (Sonnet 4.5)
```

---

### Enhancement 4 Acceptance Criteria

- [ ] Documentation audit complete (14+ files inventoried)
- [ ] Archive directories created (`adr017_planning/`, `adr017_startup_prompts/`)
- [ ] 11+ files moved to archive
- [ ] 3 active files remain in `docs/development/`
- [ ] Archive README created with navigation
- [ ] Implementation summary created with lessons learned
- [ ] All links verified (no broken references)

---

## Phase 5: Enhancement 5 - Extract Common Test Fixtures

**Duration**: 3 hours
**Priority**: P3 - Code Quality

### Step 1: Audit Test Fixtures (1 hour)

**Identify duplicate fixtures across test files**:

```bash
# Search for common fixture patterns
grep -r "def.*fixture\|@pytest.fixture" tests/ --include="*.py" | wc -l

# Find tests that create similar objects
grep -r "OperationContext\|ParsedIntent\|Task\|Project" tests/ --include="*.py" \
  | grep "=" | head -20
```

**Files to review**:
- `tests/test_intent_to_task_converter.py` (33 tests)
- `tests/integration/test_orchestrator_nl_integration.py` (12 tests)
- `tests/integration/test_adr017_regression.py` (10 tests)
- `tests/integration/test_adr017_performance.py` (7 tests)
- `tests/test_story9_confirmation_ui.py` (24 tests)

**Common patterns to extract**:
1. `mock_parsed_intent()` - Standard ParsedIntent factory
2. `mock_operation_context()` - Standard OperationContext factory
3. `test_project_with_tasks()` - Pre-populated project for tests
4. `mock_llm_plugin()` - Mock LLM with standard responses
5. `temp_workspace()` - Temporary workspace with cleanup

---

### Step 2: Extract to conftest.py (1.5 hours)

**File**: `tests/conftest.py` (enhance existing)

```python
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from src.nl.types import ParsedIntent, OperationContext
from src.state.models import Project, Task, TaskType
from src.state.state_manager import StateManager
from src.config import Config

# ============================================================
# FIXTURE 1: Mock ParsedIntent Factory
# ============================================================

@pytest.fixture
def mock_parsed_intent():
    """Factory for creating ParsedIntent objects."""

    def _make_intent(
        intent_type: str = "COMMAND",
        operation: str = "CREATE",
        entity_type: str = "task",
        identifier: str = None,
        parameters: Dict[str, Any] = None,
        confidence: float = 0.95,
        original_message: str = "create a task"
    ) -> ParsedIntent:
        """Create a ParsedIntent with defaults."""
        op_context = OperationContext(
            operation=operation,
            entity_type=entity_type,
            identifier=identifier,
            parameters=parameters or {},
            confidence=confidence
        )

        return ParsedIntent(
            intent_type=intent_type,
            operation_context=op_context,
            original_message=original_message,
            confidence=confidence,
            requires_execution=(intent_type == "COMMAND")
        )

    return _make_intent


# ============================================================
# FIXTURE 2: Mock OperationContext Factory
# ============================================================

@pytest.fixture
def mock_operation_context():
    """Factory for creating OperationContext objects."""

    def _make_context(
        operation: str = "CREATE",
        entity_type: str = "task",
        identifier: str = None,
        parameters: Dict[str, Any] = None,
        confidence: float = 0.95
    ) -> OperationContext:
        """Create an OperationContext with defaults."""
        return OperationContext(
            operation=operation,
            entity_type=entity_type,
            identifier=identifier,
            parameters=parameters or {},
            confidence=confidence
        )

    return _make_context


# ============================================================
# FIXTURE 3: Test Project with Tasks
# ============================================================

@pytest.fixture
def test_project_with_tasks(state_manager):
    """Create a test project with sample tasks."""

    # Create project
    project = state_manager.create_project(
        project_name="Test Project",
        working_directory="/tmp/test_project"
    )

    # Create epic
    epic = state_manager.create_epic(
        project_id=project.id,
        title="Test Epic",
        description="Epic for testing"
    )

    # Create story
    story = state_manager.create_story(
        project_id=project.id,
        epic_id=epic.id,
        title="Test Story",
        description="Story for testing"
    )

    # Create tasks
    task1 = state_manager.create_task(
        project_id=project.id,
        title="Task 1",
        description="First test task",
        story_id=story.id
    )

    task2 = state_manager.create_task(
        project_id=project.id,
        title="Task 2",
        description="Second test task",
        story_id=story.id
    )

    return {
        'project': project,
        'epic': epic,
        'story': story,
        'tasks': [task1, task2]
    }


# ============================================================
# FIXTURE 4: Mock LLM Plugin
# ============================================================

@pytest.fixture
def mock_llm_plugin(mocker):
    """Create a mock LLM plugin with standard responses."""

    mock_llm = mocker.Mock()
    mock_llm.is_available.return_value = True
    mock_llm.generate.return_value = {
        'operation': 'CREATE',
        'entity_type': 'task',
        'confidence': 0.95
    }

    return mock_llm


# ============================================================
# FIXTURE 5: Enhanced Temp Workspace
# ============================================================

@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with automatic cleanup."""

    # Create temp directory
    workspace = tempfile.mkdtemp(prefix="obra_test_")
    workspace_path = Path(workspace)

    # Create standard subdirectories
    (workspace_path / "src").mkdir()
    (workspace_path / "tests").mkdir()
    (workspace_path / "docs").mkdir()

    # Initialize git repository (if needed)
    # subprocess.run(['git', 'init'], cwd=workspace, check=True)

    yield workspace_path

    # Cleanup
    shutil.rmtree(workspace, ignore_errors=True)


# ============================================================
# FIXTURE 6: Standard Test Config
# ============================================================

@pytest.fixture
def test_config():
    """Create a standard test configuration."""

    config_dict = {
        'llm': {
            'type': 'ollama',
            'model': 'qwen2.5-coder:32b',
            'api_url': 'http://localhost:11434',
            'timeout': 30
        },
        'agent': {
            'type': 'claude_code_local',
            'max_context': 200000
        },
        'orchestrator': {
            'max_iterations': 3,
            'quality_threshold': 0.7
        },
        'nl_commands': {
            'enabled': True,
            'confidence_threshold': 0.7
        }
    }

    return Config.from_dict(config_dict)
```

---

### Step 3: Update Tests to Use Shared Fixtures (30 minutes)

**Example transformation**:

**Before** (duplicated in each test file):
```python
# tests/test_intent_to_task_converter.py

def test_convert_create_operation():
    # Create operation context (duplicated)
    op_context = OperationContext(
        operation="CREATE",
        entity_type="task",
        identifier=None,
        parameters={'title': 'Test Task'},
        confidence=0.95
    )

    # Test logic...
```

**After** (using shared fixture):
```python
# tests/test_intent_to_task_converter.py

def test_convert_create_operation(mock_operation_context):
    # Use fixture factory
    op_context = mock_operation_context(
        operation="CREATE",
        entity_type="task",
        parameters={'title': 'Test Task'}
    )

    # Test logic... (unchanged)
```

**Files to update**:
- `tests/test_intent_to_task_converter.py` (33 tests)
- `tests/integration/test_orchestrator_nl_integration.py` (12 tests)
- `tests/integration/test_adr017_regression.py` (10 tests)
- `tests/integration/test_adr017_performance.py` (7 tests)
- `tests/test_story9_confirmation_ui.py` (24 tests)

**Estimated changes**: 50-70 test functions

---

### Enhancement 5 Acceptance Criteria

- [ ] Fixture audit complete (5+ common patterns identified)
- [ ] 6 shared fixtures extracted to `tests/conftest.py`
- [ ] 50-70 test functions updated to use shared fixtures
- [ ] All tests still passing (100% pass rate)
- [ ] No functionality changes (only refactoring)
- [ ] Documentation: Add docstrings to each fixture
- [ ] Benefits validated: Reduced LOC, easier maintenance

**Benefits Metrics**:
- Lines of code reduced: ~200-300 lines
- Maintenance burden: ~40% reduction (update 1 fixture vs 5+ copies)
- Test readability: Improved (less boilerplate)

---

## Phase 6: Documentation & Release

**Duration**: 1 hour
**Priority**: P1 - Required

### Step 1: Update CHANGELOG.md

**File**: `CHANGELOG.md`

```markdown
## [1.7.2] - 2025-11-XX

### Added
- **Story 0 Testing Infrastructure (Complete)**: Comprehensive integration test suite
  - 15 LLM integration tests (connectivity, switching, performance baselines)
  - 12 agent integration tests (connectivity, E2E workflows)
  - **THE CRITICAL TEST**: Full workflow validation (create → execute → validate)
  - Structured logging at all critical paths (llm_request, agent_execution, nl_command)
  - Metrics collection with aggregates (P50/P95/P99 latencies)
  - `obra health` CLI command for system health checks

### Changed
- **Test fixtures consolidated**: Extracted 6 common fixtures to `tests/conftest.py`
  - `mock_parsed_intent()` - Standard ParsedIntent factory
  - `mock_operation_context()` - Standard OperationContext factory
  - `test_project_with_tasks()` - Pre-populated project for tests
  - `mock_llm_plugin()` - Mock LLM with standard responses
  - `temp_workspace()` - Enhanced temporary workspace with cleanup
  - `test_config()` - Standard test configuration
- **Reduced test LOC by 200-300 lines** (DRY principle)

### Documentation
- **Consolidated ADR-017 documentation**: Archived 11+ historical files
  - Moved startup prompts to `docs/archive/adr017_startup_prompts/`
  - Moved planning documents to `docs/archive/adr017_planning/`
  - Created implementation summary: `docs/development/ADR017_IMPLEMENTATION_SUMMARY.md`
- **Enhanced**: Added archive README with navigation

### Tests
- **Total tests**: 844+ (800 existing + 44 new from Story 0)
- **Test pass rate**: 100%
- **Coverage**: 88% (maintained)
- **Performance**: P95 < 3s latency, throughput > 40 cmd/min ✓

### Performance Baselines (NEW)
- **LLM Intent Classification**: P50 < 500ms, P95 < 1000ms
- **LLM Entity Extraction**: P50 < 800ms, P95 < 1500ms
- **Full NL Pipeline**: P50 < 1.5s, P95 < 3s
- **Accuracy**: Intent 95%+, Entity extraction 90%+

[1.7.2]: https://github.com/Omar-Unpossible/claude_code_orchestrator/compare/v1.7.1...v1.7.2
```

---

### Step 2: Update CLAUDE.md

**File**: `CLAUDE.md`

Update version and Story 0 status:

```markdown
**Current Version**: **v1.7.2** (November XX, 2025)

**Status**: Production-ready - 844+ tests (88% coverage), Story 0 testing infrastructure complete
```

Update "Testing Requirements" section:

```markdown
### Test Tiers (Story 0 - Complete)

**Tier 1: Fast Gate** (17 tests, <2 min)
- Health checks (7): LLM, database, agent, config
- Smoke tests (10): Core workflows with mocks
- Run: Every commit

**Tier 2: LLM Integration** (15 tests, 5-8 min)
- Connectivity (6): Ollama/OpenAI success/failure modes
- Switching (4): Provider switching with state preservation
- Performance (5): Latency and accuracy baselines
- Run: Before merge, nightly

**Tier 3: Agent Integration** (12 tests, 10-15 min)
- Connectivity (4): Agent availability, session creation
- Workflows (8): E2E orchestration, dependencies, git
- **THE CRITICAL TEST**: Full create → execute → validate
- Run: Before merge (with label), nightly

**Execution**:
```bash
# Fast gate (every commit)
pytest tests/health tests/smoke -v

# Integration (before merge)
pytest tests/integration/test_llm_*.py tests/integration/test_agent_*.py -v

# THE CRITICAL TEST (before release)
pytest tests/integration/test_agent_connectivity.py::TestOrchestratorWorkflows::test_full_workflow_create_project_to_execution -v
```
```

---

### Step 3: Create v1.7.2 Release Notes

**File**: `docs/release_notes/RELEASE_v1.7.2.md`

```markdown
# Release Notes: v1.7.2

**Release Date**: November XX, 2025
**Focus**: Testing Infrastructure & Code Quality
**Effort**: 25 hours (3 days)

---

## Highlights

### ✅ Story 0 Testing Infrastructure (Complete)

**THE CRITICAL TEST** is now implemented and passing - the single most important test that validates Obra's core value proposition works end-to-end.

**Test Coverage**:
- 844+ total tests (100% pass rate)
- 44 new integration tests (15 LLM + 12 agent + 17 health/smoke)
- 88% code coverage (maintained)

**Test Tiers**:
- Tier 1 (17 tests): Fast gate (<2 min) - Run every commit
- Tier 2 (15 tests): LLM integration (5-8 min) - Run before merge
- Tier 3 (12 tests): Agent integration (10-15 min) - Run before release

**Benefits**:
- Early detection of integration issues
- Faster debugging with comprehensive test coverage
- Baseline metrics for performance regression detection
- Confidence in production deployments

---

### ✅ Code Quality Improvements

**Test Fixture Consolidation**:
- 6 common fixtures extracted to `tests/conftest.py`
- 200-300 lines of duplicate code removed
- 40% reduction in test maintenance burden
- Improved test readability

**Documentation Cleanup**:
- 11+ historical files archived
- Clear navigation with archive README
- Implementation summary with lessons learned

---

## New Features

### obra health Command

```bash
$ obra health
Status: HEALTHY ✅
LLM: ollama (qwen2.5-coder:32b)
  - Available: Yes
  - Success Rate: 98.2% (last 5 min)
  - Latency P95: 1234ms
Database: Available
```

### Structured Logging

All critical paths now log structured events:
- `llm_request`: provider, model, latency_ms, success
- `agent_execution`: agent_type, task_id, duration_s, files_modified
- `nl_command`: command, intent, operation, success
- `orchestrator_step`: step, task_id, duration_ms

---

## Performance Baselines

**LLM Operations** (established empirically):
- Intent classification: P50 < 500ms, P95 < 1000ms
- Entity extraction: P50 < 800ms, P95 < 1500ms
- Full NL pipeline: P50 < 1.5s, P95 < 3s

**Accuracy**:
- Intent classification: 95%+
- Entity extraction: 90%+

---

## Breaking Changes

**None** - This release is fully backward compatible.

---

## Upgrade Guide

```bash
# Pull latest code
git pull origin main

# Install any new dependencies
pip install -r requirements-dev.txt

# Run tests to validate
pytest tests/health tests/smoke -v
pytest tests/integration/ -v -m integration
```

---

## What's Next

**v1.8.0 (Future)**:
- Story 10: Observability enhancements (correlation IDs, metrics v2, CLI commands)
- NL command completion tests (if feature implemented)
- Additional performance optimizations

---

## Contributors

- Claude Code (Sonnet 4.5) - Implementation
- Omar (Project Owner) - Direction and validation

**Thank you for using Obra!**
```

---

### Phase 6 Acceptance Criteria

- [ ] CHANGELOG.md updated with v1.7.2 entry
- [ ] CLAUDE.md version updated to v1.7.2
- [ ] Release notes created (`RELEASE_v1.7.2.md`)
- [ ] All documentation links verified
- [ ] Git tags created: `git tag -a v1.7.2 -m "Release v1.7.2"`

---

## Implementation Execution Plan

### Week 1: Story 0 Foundation

**Day 1-2** (16 hours):
- Part A: LLM integration tests (15 tests)
- Part B: Agent integration tests (12 tests)
- Part C: Structured logging & metrics
- Part D: `obra health` command

**Day 3** (2 hours):
- Run all tests, validate results
- Debug any failures
- Document performance baselines

### Week 2: Enhancements & Cleanup

**Day 4** (4 hours):
- Enhancement 3: NL command completion tests
  - Discovery (1h)
  - Understanding (1h)
  - Implementation (2h)

**Day 5** (2 hours):
- Enhancement 4: Consolidate documentation
  - Audit (30min)
  - Archive (30min)
  - Create summaries (1h)

**Day 6** (3 hours):
- Enhancement 5: Extract test fixtures
  - Audit (1h)
  - Extract to conftest.py (1.5h)
  - Update tests (30min)

**Day 7** (1 hour):
- Documentation & release
  - Update CHANGELOG, CLAUDE.md
  - Create release notes
  - Git tag for v1.7.2

---

## Success Metrics

### Test Coverage
- [ ] **844+ tests passing** (100% pass rate)
- [ ] **88% code coverage** (maintained)
- [ ] **THE CRITICAL TEST passing** (most important)

### Performance
- [ ] **P95 latency < 3s** for NL commands
- [ ] **Throughput > 40 cmd/min**
- [ ] **Baselines documented** (P50/P95/P99 for LLM operations)

### Code Quality
- [ ] **200-300 LOC reduced** (fixture consolidation)
- [ ] **6 shared fixtures** in conftest.py
- [ ] **11+ files archived** (documentation cleanup)

### Documentation
- [ ] **Implementation summary** created
- [ ] **Archive README** with navigation
- [ ] **Release notes** for v1.7.2
- [ ] **CHANGELOG** updated

---

## Validation Checklist

Before marking this plan as complete:

### Story 0
- [ ] All 44 tests implemented and passing
- [ ] THE CRITICAL TEST passing (<2 min)
- [ ] obra health command working
- [ ] Structured logging at critical paths
- [ ] Metrics collection functional
- [ ] Performance baselines documented

### Enhancement 3
- [ ] Discovery complete
- [ ] Tests implemented (if feature exists) OR proposal documented

### Enhancement 4
- [ ] 11+ files archived
- [ ] 3 active files remain
- [ ] Archive README created
- [ ] Implementation summary created

### Enhancement 5
- [ ] 6 fixtures extracted to conftest.py
- [ ] 50-70 tests updated
- [ ] All tests still passing
- [ ] Benefits validated (LOC reduction)

### Release
- [ ] CHANGELOG.md updated
- [ ] CLAUDE.md version updated
- [ ] Release notes created
- [ ] Git tag created: v1.7.2
- [ ] All tests passing before release

---

## Risk Mitigation

### Risk 1: THE CRITICAL TEST Fails
**Impact**: HIGH - Blocks release
**Mitigation**:
- Debug immediately, don't proceed
- Check LLM connectivity, agent availability
- Review orchestrator logs for errors
- Test with simpler task first

### Risk 2: Performance Baselines Not Met
**Impact**: MEDIUM - May need optimization
**Mitigation**:
- Document actual baselines (even if slower)
- Identify bottlenecks with profiling
- Optimize hot paths if needed
- Adjust targets if hardware-limited

### Risk 3: Test Fixture Consolidation Breaks Tests
**Impact**: MEDIUM - Rework required
**Mitigation**:
- Run tests after each fixture extraction
- Update incrementally (one fixture at a time)
- Keep backup of original tests
- Rollback if >5% tests fail

### Risk 4: Documentation Cleanup Breaks Links
**Impact**: LOW - Annoying but fixable
**Mitigation**:
- Verify all links before archiving
- Use relative paths (not absolute)
- Test documentation build
- Fix broken links immediately

---

## Rollback Plan

If critical issues arise:

**Scenario A: Tests fail after Story 0**
```bash
# Revert to v1.7.1
git checkout v1.7.1

# Investigate failures
pytest tests/ -v --tb=short

# Fix and retry
```

**Scenario B: Performance degrades**
- Document actual baselines (don't block release)
- Create optimization tasks for v1.7.3
- Release v1.7.2 with notes about performance

**Scenario C: Fixture consolidation breaks tests**
```bash
# Revert conftest.py changes
git checkout HEAD~1 tests/conftest.py

# Revert test updates
git checkout HEAD~1 tests/test_*.py

# Investigate and fix incrementally
```

---

## Next Actions

1. **Review this plan** with Omar for approval
2. **Create Story 0 startup prompt** for Claude Code execution
3. **Begin implementation** (Week 1, Day 1)
4. **Track progress** using TodoWrite tool
5. **Validate at each phase** before proceeding

---

**Plan Status**: ✅ Ready for Implementation
**Estimated Effort**: 25-27 hours (3-4 days)
**Target Release**: v1.7.2
**Success Probability**: HIGH (clear plan, well-defined scope)

**Last Updated**: November 13, 2025
**Author**: Claude Code (Sonnet 4.5)
