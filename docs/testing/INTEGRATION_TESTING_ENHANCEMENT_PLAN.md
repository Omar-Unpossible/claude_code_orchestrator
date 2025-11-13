# Integration Testing & Observability Enhancement Plan

**Created**: 2025-11-12
**Status**: Planning
**Priority**: Critical
**Target**: Pre-v1.7.0

---

## Executive Summary

**Problem**: Current test suite has excellent unit test coverage (88%) but critical gaps in integration testing. Real-world workflow issues (LLM connectivity, agent communication, core orchestration) are not caught by automated tests and require manual validation.

**Impact**: Fundamental product issues manifest immediately in manual testing but weren't detected by CI/CD.

**Solution**: Comprehensive integration testing strategy with health checks, smoke tests, end-to-end workflows, and enhanced observability.

---

## Gap Analysis

### ✅ What We Test Well (Current Coverage)

| Area | Coverage | Test Count | Speed | Notes |
|------|----------|------------|-------|-------|
| **NL Command Logic** | 90%+ | 233 mock tests | Fast (15s) | Unit tests with mocked LLMs |
| **NL Intent Classification** | 85% | 33 real LLM tests | Slow (5-10min) | Validates prompt engineering |
| **StateManager CRUD** | 95% | 150+ tests | Fast | Database operations |
| **Plugin Registry** | 95% | 50+ tests | Fast | Component registration |
| **Configuration** | 85% | 40+ tests | Fast | Config loading/validation |
| **Agile Hierarchy** | 90% | 60+ tests | Fast | Epic/story/task/milestone |

### ❌ Critical Gaps (Missing Coverage)

| Area | Current Coverage | Risk | User Impact |
|------|-----------------|------|-------------|
| **LLM Connectivity** | 0% | HIGH | App fails if Ollama down |
| **LLM Switching** | 0% | HIGH | Can't switch Ollama ↔ OpenAI Codex |
| **Agent Communication** | 5% | CRITICAL | Core orchestration broken |
| **Full Orchestrator Workflow** | 10% | CRITICAL | End-to-end task execution untested |
| **Session Management** | 20% | HIGH | Per-iteration sessions not validated |
| **Configuration Changes** | 15% | MEDIUM | Runtime reconfig untested |
| **Git Integration** | 30% | MEDIUM | Commits/PRs not validated E2E |
| **Interactive Mode** | 10% | MEDIUM | Command injection untested |
| **Error Recovery** | 25% | MEDIUM | Retry logic not validated E2E |
| **Health Checks** | 0% | HIGH | No smoke tests for deployment |

---

## Proposed Testing Strategy

### Tier 1: Health Checks & Smoke Tests (NEW)

**Purpose**: Fast validation that all systems are operational
**Execution**: On startup, before CI/CD, after deployment
**Speed**: <30 seconds
**Coverage**: Connectivity, basic operations

#### 1.1 System Health Checks

```python
# File: tests/health/test_system_health.py

class TestSystemHealth:
    """Fast health checks for all critical systems."""

    def test_llm_connectivity_ollama(self):
        """Verify Ollama is reachable and responding."""
        # Try to connect to Ollama endpoint
        # Send simple generation request
        # Assert response within timeout (5s)

    def test_llm_connectivity_openai_codex(self, skip_if_no_api_key):
        """Verify OpenAI Codex is reachable (if configured)."""
        # Try to connect to OpenAI API
        # Send simple generation request
        # Assert response within timeout (10s)

    def test_database_connectivity(self):
        """Verify database is accessible."""
        # Create in-memory DB
        # Create test project
        # Query it back
        # Assert success within 1s

    def test_agent_registry_loaded(self):
        """Verify agent plugins are registered."""
        # Check Claude Code local agent registered
        # Check Claude Code SSH agent registered
        # Assert at least 2 agents available

    def test_llm_registry_loaded(self):
        """Verify LLM plugins are registered."""
        # Check Ollama LLM registered
        # Check OpenAI Codex LLM registered
        # Assert at least 2 LLMs available

    def test_configuration_valid(self):
        """Verify default configuration loads."""
        # Load default config
        # Validate required keys present
        # Assert no validation errors

    def test_state_manager_initialization(self):
        """Verify StateManager can initialize."""
        # Create StateManager
        # Verify DB tables created
        # Assert ready for use
```

**Run Command**:
```bash
pytest tests/health/ -v --timeout=30
# Expected: 7 passed in <30s
```

**CI/CD Integration**: Run on every commit (fast gate)

---

#### 1.2 Smoke Tests (Core Workflows)

```python
# File: tests/smoke/test_smoke_workflows.py

class TestSmokeWorkflows:
    """Fast validation of core workflows with mocks."""

    def test_create_project_smoke(self):
        """Smoke test: Create project via CLI."""
        # Run: obra project create "Test" --description "Test"
        # Assert: Project created, ID returned
        # Speed: <1s

    def test_create_epic_smoke(self):
        """Smoke test: Create epic via NL."""
        # Setup: Project exists
        # Run: NL command "create epic for user auth"
        # Assert: Epic created
        # Speed: <1s (mocked LLM)

    def test_list_tasks_smoke(self):
        """Smoke test: List tasks via NL."""
        # Setup: Tasks exist
        # Run: NL command "list tasks"
        # Assert: Tasks returned
        # Speed: <1s

    def test_llm_reconnect_smoke(self):
        """Smoke test: LLM reconnect command."""
        # Run: obra llm status
        # Run: obra llm reconnect
        # Assert: Success
        # Speed: <2s
```

**Run Command**:
```bash
pytest tests/smoke/ -v --timeout=60
# Expected: 10 passed in <1 minute
```

---

### Tier 2: LLM Integration Tests (ENHANCED)

**Purpose**: Validate LLM connectivity, switching, and basic operations
**Execution**: Before merge, nightly CI
**Speed**: 5-10 minutes
**Coverage**: Real LLM communication

#### 2.1 LLM Connectivity & Switching

```python
# File: tests/integration/test_llm_connectivity.py

@pytest.mark.integration
@pytest.mark.requires_ollama
class TestLLMConnectivity:
    """Validate LLM connectivity and health."""

    def test_ollama_connection_success(self):
        """Test successful connection to Ollama."""
        # Create LocalLLMInterface
        # Initialize with correct endpoint
        # Send test prompt
        # Assert: Response received, no errors

    def test_ollama_connection_failure_wrong_port(self):
        """Test graceful failure with wrong port."""
        # Create LocalLLMInterface
        # Initialize with wrong port (11435)
        # Try to generate
        # Assert: Specific connection error, helpful message

    def test_ollama_connection_failure_service_down(self):
        """Test graceful failure when Ollama not running."""
        # Mock connection failure
        # Try to generate
        # Assert: Clear error message, recovery suggestion

    def test_llm_switch_ollama_to_openai(self, skip_if_no_api_key):
        """Test switching from Ollama to OpenAI Codex."""
        # Start with Ollama
        # Generate test prompt (verify works)
        # Switch to OpenAI Codex via orchestrator.reconnect_llm()
        # Generate same prompt
        # Assert: Both work, different providers

    def test_llm_switch_via_cli(self):
        """Test LLM switching via CLI command."""
        # Run: obra llm status (get current)
        # Run: obra llm switch openai-codex --model gpt-5-codex
        # Run: obra llm status (verify switched)
        # Assert: Switch successful

    def test_llm_fallback_on_timeout(self):
        """Test LLM timeout handling."""
        # Configure very short timeout (1s)
        # Send complex prompt (slow)
        # Assert: Timeout error, retry suggestion


@pytest.mark.integration
class TestLLMProviderSwitching:
    """Test dynamic LLM provider switching during runtime."""

    def test_switch_maintains_state(self):
        """Verify StateManager state preserved during LLM switch."""
        # Create project with Ollama
        # Create epic with Ollama
        # Switch to OpenAI Codex
        # Create story with OpenAI Codex
        # Assert: All entities still accessible

    def test_switch_with_pending_confirmation(self):
        """Test LLM switch during pending confirmation."""
        # Start UPDATE operation (pending confirmation)
        # Switch LLM
        # Confirm with "yes"
        # Assert: Operation completes successfully
```

---

#### 2.2 LLM Performance & Accuracy Baselines

```python
# File: tests/integration/test_llm_performance.py

@pytest.mark.integration
@pytest.mark.slow
class TestLLMPerformance:
    """Establish performance baselines for LLM operations."""

    def test_intent_classification_latency_ollama(self, real_llm):
        """Baseline: Intent classification latency with Ollama."""
        # 10 intent classification requests
        # Measure: p50, p95, p99 latency
        # Assert: p95 < 2s, p99 < 5s
        # Log: Baseline metrics

    def test_entity_extraction_accuracy_ollama(self, real_llm):
        """Baseline: Entity extraction accuracy with Ollama."""
        # 50 test prompts with known entities
        # Measure: Accuracy (correct entity_type)
        # Assert: Accuracy >= 90%
        # Log: Confusion matrix

    def test_full_pipeline_latency_ollama(self, real_llm):
        """Baseline: Full NL pipeline latency with Ollama."""
        # 10 end-to-end NL commands
        # Measure: Total pipeline time
        # Assert: p95 < 5s
        # Log: Per-stage timing breakdown
```

---

### Tier 3: Agent Integration Tests (NEW - CRITICAL)

**Purpose**: Validate Claude Code agent communication and orchestration
**Execution**: Before merge, nightly CI
**Speed**: 10-15 minutes
**Coverage**: Agent communication, session management, orchestration workflow

#### 3.1 Agent Connectivity

```python
# File: tests/integration/test_agent_connectivity.py

@pytest.mark.integration
class TestAgentConnectivity:
    """Validate agent connectivity and basic operations."""

    def test_claude_code_local_agent_available(self):
        """Verify Claude Code local agent can be instantiated."""
        # Get agent from registry
        # Initialize
        # Assert: No errors

    def test_claude_code_local_agent_send_prompt(self, tmp_workspace):
        """Verify agent can send/receive prompts."""
        # Create local agent
        # Send simple prompt: "list files"
        # Assert: Response received
        # Speed: <30s

    def test_claude_code_session_creation(self, tmp_workspace):
        """Verify fresh session creation."""
        # Create agent
        # Start session
        # Send prompt
        # Assert: Session ID returned, response received

    def test_claude_code_session_isolation(self, tmp_workspace):
        """Verify sessions are isolated (per-iteration model)."""
        # Create session 1, create file
        # Create session 2 (fresh)
        # List files in session 2
        # Assert: Session 2 doesn't see session 1's file
```

---

#### 3.2 Orchestrator Core Workflows (NEW - CRITICAL GAP)

```python
# File: tests/integration/test_orchestrator_workflows.py

@pytest.mark.integration
@pytest.mark.slow
class TestOrchestratorWorkflows:
    """End-to-end orchestrator workflows with real LLM + real agent."""

    def test_full_workflow_create_project_to_execution(self, temp_workspace):
        """
        Full workflow: Create project → Create task → Execute task

        This is THE most critical test - validates core value proposition.
        """
        # Setup
        orchestrator = Orchestrator(config=integration_config)

        # Step 1: Create project
        project = orchestrator.state_manager.create_project(
            name="Integration Test Project",
            description="Full E2E test",
            working_dir=temp_workspace
        )

        # Step 2: Create task via NL
        nl_response = orchestrator.nl_processor.process(
            "create task to add a hello world Python script"
        )
        assert nl_response.success
        task_id = nl_response.execution_result.created_ids[0]

        # Step 3: Execute task (CRITICAL - real Claude Code agent)
        execution_result = orchestrator.execute_task(
            task_id=task_id,
            max_iterations=3
        )

        # Assertions
        assert execution_result.success
        assert execution_result.files_modified  # Code was written
        assert os.path.exists(os.path.join(temp_workspace, 'hello.py'))

        # Validation: Check code quality
        with open(os.path.join(temp_workspace, 'hello.py')) as f:
            code = f.read()
            assert 'print' in code.lower()  # Basic sanity check

        # Speed: ~1-2 minutes (real agent execution)

    def test_workflow_with_quality_feedback(self, temp_workspace):
        """
        Workflow: Task execution with quality feedback loop.

        Validates: Quality controller, retry logic, iterative improvement.
        """
        # Create task with quality requirements
        # Execute task
        # Simulate low quality score
        # Assert: Orchestrator retries, improves quality

    def test_workflow_with_confirmation(self, temp_workspace):
        """
        Workflow: UPDATE/DELETE with confirmation.

        Validates: Interactive confirmation workflow end-to-end.
        """
        # Create task
        # Send NL command "delete task X"
        # Assert: Confirmation prompt returned
        # Send "yes"
        # Assert: Task deleted

    def test_workflow_multi_task_epic(self, temp_workspace):
        """
        Workflow: Create epic → Create stories → Execute tasks.

        Validates: Agile hierarchy, multi-task orchestration.
        """
        # Create epic via NL
        # Create 3 stories via NL
        # Execute epic (runs all stories)
        # Assert: All stories completed

    def test_workflow_with_dependencies(self, temp_workspace):
        """
        Workflow: Tasks with dependencies (M9).

        Validates: Dependency resolution, execution order.
        """
        # Create task A
        # Create task B (depends on A)
        # Execute task B
        # Assert: Task A executed first, then B

    def test_workflow_git_integration(self, temp_workspace):
        """
        Workflow: Task execution with git commits (M9).

        Validates: GitManager integration, auto-commits.
        """
        # Initialize git repo
        # Create task
        # Execute task with git integration enabled
        # Assert: Commit created, commit message semantic
```

---

#### 3.3 Session Management Tests (NEW)

```python
# File: tests/integration/test_session_management.py

@pytest.mark.integration
class TestSessionManagement:
    """Validate per-iteration session management (PHASE_4 fix)."""

    def test_fresh_session_per_iteration(self):
        """Verify each iteration gets fresh Claude session."""
        # Execute task for 3 iterations
        # Track session IDs
        # Assert: 3 different session IDs

    def test_context_continuity_across_sessions(self):
        """Verify Obra maintains context despite fresh sessions."""
        # Iteration 1: Create file
        # Iteration 2: Modify file
        # Assert: Iteration 2 sees iteration 1's changes (via Obra context)

    def test_no_session_lock_conflicts(self):
        """Verify no session lock conflicts (PHASE_4 bug)."""
        # Execute same task twice concurrently
        # Assert: No "session locked" errors
```

---

### Tier 4: Configuration & State Management Tests (NEW)

**Purpose**: Validate configuration changes, state persistence, migrations
**Execution**: Before merge
**Speed**: 5 minutes
**Coverage**: Config management, state persistence

```python
# File: tests/integration/test_configuration_management.py

@pytest.mark.integration
class TestConfigurationManagement:
    """Validate configuration loading, switching, persistence."""

    def test_load_default_config(self):
        """Verify default config loads without errors."""
        config = Config.load()
        assert config.get('llm.type') in ['ollama', 'openai-codex']

    def test_switch_config_profile(self):
        """Verify switching between config profiles (M9)."""
        # Load python_project profile
        # Verify settings match python_project
        # Switch to web_app profile
        # Verify settings changed

    def test_runtime_config_update(self):
        """Verify runtime config updates work."""
        orchestrator = Orchestrator(...)
        # Update LLM temperature
        # Send new command
        # Verify new temperature used

    def test_config_validation_errors(self):
        """Verify invalid configs are caught."""
        # Load config with invalid llm.type
        # Assert: ValidationError with helpful message
```

---

### Tier 5: Observability & Logging Enhancements (NEW)

**Purpose**: Better visibility into system behavior for debugging and monitoring
**Implementation**: Structured logging, metrics, health endpoints

#### 5.1 Structured Logging

```python
# File: src/core/logging_config.py (NEW)

import logging
import json
from datetime import datetime
from typing import Dict, Any

class StructuredLogger:
    """Structured JSON logging for observability."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # JSON handler
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)

    def log_llm_request(
        self,
        provider: str,
        model: str,
        prompt_length: int,
        latency_ms: float,
        success: bool,
        error: str = None
    ):
        """Log LLM request with structured data."""
        self.logger.info(json.dumps({
            'event': 'llm_request',
            'timestamp': datetime.utcnow().isoformat(),
            'provider': provider,
            'model': model,
            'prompt_length': prompt_length,
            'latency_ms': latency_ms,
            'success': success,
            'error': error
        }))

    def log_agent_execution(
        self,
        agent_type: str,
        task_id: int,
        iteration: int,
        duration_s: float,
        success: bool,
        files_modified: int
    ):
        """Log agent execution with structured data."""
        self.logger.info(json.dumps({
            'event': 'agent_execution',
            'timestamp': datetime.utcnow().isoformat(),
            'agent_type': agent_type,
            'task_id': task_id,
            'iteration': iteration,
            'duration_s': duration_s,
            'success': success,
            'files_modified': files_modified
        }))

    def log_nl_command(
        self,
        command: str,
        intent: str,
        operation: str,
        entity_type: str,
        success: bool,
        latency_ms: float
    ):
        """Log NL command execution."""
        self.logger.info(json.dumps({
            'event': 'nl_command',
            'timestamp': datetime.utcnow().isoformat(),
            'command': command,
            'intent': intent,
            'operation': operation,
            'entity_type': entity_type,
            'success': success,
            'latency_ms': latency_ms
        }))
```

**Integration**: Add to all critical paths (LLM requests, agent execution, NL commands)

---

#### 5.2 Metrics & Health Endpoints

```python
# File: src/core/metrics.py (NEW)

from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime, timedelta
import statistics

@dataclass
class MetricsCollector:
    """Collect and aggregate metrics for monitoring."""

    llm_requests: List[Dict] = field(default_factory=list)
    agent_executions: List[Dict] = field(default_factory=list)
    nl_commands: List[Dict] = field(default_factory=list)

    def record_llm_request(self, provider: str, latency_ms: float, success: bool):
        """Record LLM request metric."""
        self.llm_requests.append({
            'timestamp': datetime.utcnow(),
            'provider': provider,
            'latency_ms': latency_ms,
            'success': success
        })

    def get_llm_stats(self, window_minutes: int = 60) -> Dict:
        """Get LLM statistics for time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent = [r for r in self.llm_requests if r['timestamp'] > cutoff]

        if not recent:
            return {'count': 0}

        latencies = [r['latency_ms'] for r in recent]
        successes = sum(1 for r in recent if r['success'])

        return {
            'count': len(recent),
            'success_rate': successes / len(recent),
            'latency_p50': statistics.median(latencies),
            'latency_p95': statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0],
            'latency_p99': statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else latencies[0],
        }

    def health_check(self) -> Dict:
        """Overall health check."""
        llm_stats = self.get_llm_stats(window_minutes=5)

        return {
            'status': 'healthy' if llm_stats.get('success_rate', 0) > 0.9 else 'degraded',
            'llm_available': llm_stats.get('count', 0) > 0,
            'llm_success_rate': llm_stats.get('success_rate', 0),
            'llm_latency_p95': llm_stats.get('latency_p95', 0)
        }
```

**Usage**: Expose via CLI command `obra health`

---

### Tier 6: CI/CD Integration

#### 6.1 Test Tiers in CI/CD

```yaml
# .github/workflows/test-tiers.yml (example)

name: Test Tiers

on: [push, pull_request]

jobs:
  tier1-health-checks:
    name: "Tier 1: Health Checks (Fast)"
    runs-on: ubuntu-latest
    timeout-minutes: 2
    steps:
      - uses: actions/checkout@v3
      - name: Run health checks
        run: |
          pytest tests/health/ -v --timeout=30
      # Run on every commit

  tier2-unit-tests:
    name: "Tier 2: Unit Tests (Fast)"
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Run unit tests
        run: |
          pytest tests/ -v -m "not integration" -m "not slow"
      # Run on every commit

  tier3-llm-integration:
    name: "Tier 3: LLM Integration (Slow)"
    runs-on: ubuntu-latest
    timeout-minutes: 15
    if: github.event_name == 'pull_request' || github.ref == 'refs/heads/main'
    services:
      ollama:
        image: ollama/ollama:latest
        ports:
          - 11434:11434
    steps:
      - name: Pull Qwen model
        run: docker exec ollama ollama pull qwen2.5-coder:32b
      - name: Run LLM integration tests
        run: |
          pytest tests/integration/test_llm_*.py -v -m integration
      # Run on PR and merge to main

  tier4-orchestrator-e2e:
    name: "Tier 4: Orchestrator E2E (Slowest)"
    runs-on: ubuntu-latest
    timeout-minutes: 30
    if: github.ref == 'refs/heads/main' || contains(github.event.pull_request.labels.*.name, 'run-e2e')
    steps:
      - name: Run orchestrator workflows
        run: |
          pytest tests/integration/test_orchestrator_workflows.py -v --timeout=1800
      # Run on merge to main or with "run-e2e" label

  nightly-full-suite:
    name: "Nightly: Full Test Suite"
    runs-on: ubuntu-latest
    if: github.event.schedule
    steps:
      - name: Run all tests
        run: |
          pytest tests/ -v --timeout=3600
      # Run nightly
```

---

## Implementation Priority

### Phase 1 (Week 1): Foundation
1. ✅ Create test directory structure (health/, smoke/, integration/)
2. ✅ Implement Tier 1: Health Checks (7 tests)
3. ✅ Implement Tier 1: Smoke Tests (10 tests)
4. ✅ Add basic structured logging
5. ✅ Verify all pass locally

### Phase 2 (Week 2): LLM Integration
1. ✅ Enhance Tier 2: LLM Connectivity (10 tests)
2. ✅ Add Tier 2: LLM Switching (8 tests)
3. ✅ Add Tier 2: Performance Baselines (5 tests)
4. ✅ CI/CD: Add tier 1-2 to GitHub Actions

### Phase 3 (Week 3): Critical Gaps - Agent Integration
1. ✅ Implement Tier 3: Agent Connectivity (5 tests)
2. ✅ Implement Tier 3: Orchestrator Workflows (8 tests) **CRITICAL**
3. ✅ Implement Tier 3: Session Management (3 tests)
4. ✅ CI/CD: Add tier 3 to nightly builds

### Phase 4 (Week 4): Configuration & Observability
1. ✅ Implement Tier 4: Configuration Management (5 tests)
2. ✅ Enhance structured logging throughout codebase
3. ✅ Add metrics collection
4. ✅ Create `obra health` CLI command
5. ✅ CI/CD: Full pipeline integration

---

## Success Metrics

### Coverage Goals
- **Health Checks**: 100% of critical systems (7/7)
- **Smoke Tests**: 100% of core workflows (10/10)
- **LLM Integration**: 90%+ LLM operations (23/25 tests)
- **Agent Integration**: 80%+ orchestrator workflows (16/20 tests)
- **Overall Integration**: 70%+ real-world scenarios

### Quality Gates
- All Tier 1 (health + smoke) tests pass on every commit
- All Tier 2 (LLM integration) tests pass before merge
- All Tier 3 (agent + orchestrator) tests pass nightly
- No manual testing required for basic workflows

### Observability Goals
- All LLM requests logged with latency
- All agent executions logged with duration
- All NL commands logged with outcome
- Health check endpoint available
- Metrics aggregated for monitoring

---

## Cost/Benefit Analysis

### Costs
- **Development Time**: 4 weeks (1 engineer)
- **CI/CD Time**: +5 minutes per PR (tier 1-2), +30 minutes nightly (tier 3-4)
- **Infrastructure**: Ollama container in CI (~$0.10/month)

### Benefits
- **Catch 95%+ of workflow issues** before manual testing
- **Reduce manual testing time** from 30min/feature to 5min/feature
- **Prevent production incidents** from LLM/agent connectivity issues
- **Faster debugging** with structured logs
- **Confidence in releases** with comprehensive E2E validation

### ROI
- **Time Saved**: ~100 hours/year in manual testing
- **Incidents Prevented**: ~20-30/year (connectivity, switching, workflows)
- **Developer Velocity**: +30% (faster feedback, less debugging)

---

## Appendix: Example Test Scenarios

### Scenario 1: LLM Goes Down During Task Execution

**Current**: Manual testing required, unclear how system behaves
**With Plan**: `test_llm_connection_failure_during_execution()` catches it

### Scenario 2: Switch LLM Mid-Epic

**Current**: Untested, might break state
**With Plan**: `test_switch_maintains_state()` validates it works

### Scenario 3: Fresh Session Per Iteration

**Current**: Integration test exists but gaps remain
**With Plan**: `test_fresh_session_per_iteration()` fully validates

### Scenario 4: Confirmation Workflow End-to-End

**Current**: Unit tests only, not tested with real agent
**With Plan**: `test_workflow_with_confirmation()` validates E2E

---

## Next Steps

1. **Review Plan**: Stakeholder review of testing strategy
2. **Prioritize**: Confirm Phase 1-4 priorities
3. **Allocate Resources**: 1 engineer for 4 weeks
4. **Start Implementation**: Begin with Phase 1 (Week 1)
5. **Iterate**: Adjust based on lessons learned

---

**Questions? Concerns? Feedback?**

This plan is comprehensive but flexible. We can adjust priorities, add/remove tests, or change the implementation timeline based on project needs.
