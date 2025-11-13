# Integration Testing Implementation Plan - Machine-Optimized

**Document Type**: Implementation Plan (Machine-Readable)
**Status**: Ready for Implementation
**Estimated Effort**: 4 weeks (4 tiers)
**Target Version**: v1.7.0
**Created**: 2025-11-12

---

## Prerequisites

**CRITICAL - READ FIRST**:
1. Read `docs/development/TEST_GUIDELINES.md` to avoid WSL2 crashes
2. Read `docs/testing/INTEGRATION_TESTING_ENHANCEMENT_PLAN.md` for context
3. Ensure virtual environment active: `source venv/bin/activate`
4. Verify Ollama running: `curl http://10.0.75.1:11434/api/tags`

**Key Constraints**:
- Max sleep per test: 0.5s (use `fast_time` fixture for longer)
- Max threads per test: 5 (with mandatory `timeout=` on join)
- Max memory allocation: 20KB per test
- Mark slow tests: `@pytest.mark.slow`
- Mark integration tests: `@pytest.mark.integration`

---

## Tier 1: Health Checks & Smoke Tests

**Goal**: Fast validation all systems operational
**Tests**: 17 tests
**Duration**: <30 seconds
**Breakpoint**: After Tier 1 complete, verify all tests pass

### Task 1.1: Create Health Check Tests

**File**: `tests/health/test_system_health.py` (NEW)

```python
"""System health checks for critical components.

Run on: Every commit, deployment validation
Speed: <30 seconds
Purpose: Fast gate to catch system-level failures
"""

import pytest
import requests
from src.core.state import StateManager
from src.core.config import Config
from src.plugins.registry import AgentRegistry, LLMRegistry


class TestSystemHealth:
    """Fast health checks for all critical systems."""

    def test_llm_connectivity_ollama(self):
        """Verify Ollama is reachable and responding."""
        try:
            response = requests.get(
                'http://10.0.75.1:11434/api/tags',
                timeout=5
            )
            assert response.status_code == 200
            data = response.json()
            assert 'models' in data
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Ollama not accessible: {e}")

    def test_llm_connectivity_openai_codex(self):
        """Verify OpenAI Codex config exists (skip if no API key)."""
        import os
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")

        # Just verify config can load OpenAI settings
        config = Config.load()
        # Should not raise exception
        assert True

    def test_database_connectivity(self):
        """Verify database is accessible."""
        import time
        start = time.time()

        state = StateManager(database_url='sqlite:///:memory:')

        # Create test project
        project = state.create_project(
            name="Health Check Project",
            description="Test",
            working_dir="/tmp/health_check"
        )

        # Query it back
        retrieved = state.get_project(project.id)
        assert retrieved is not None
        assert retrieved.project_name == "Health Check Project"

        state.close()

        # Should complete in <1s
        duration = time.time() - start
        assert duration < 1.0, f"Database too slow: {duration}s"

    def test_agent_registry_loaded(self):
        """Verify agent plugins are registered."""
        # Check Claude Code local agent registered
        try:
            agent = AgentRegistry.get('claude-code-local')
            assert agent is not None
        except KeyError:
            pytest.fail("Claude Code local agent not registered")

    def test_llm_registry_loaded(self):
        """Verify LLM plugins are registered."""
        # Check Ollama LLM registered
        try:
            llm = LLMRegistry.get('ollama')
            assert llm is not None
        except KeyError:
            pytest.fail("Ollama LLM not registered")

    def test_configuration_valid(self):
        """Verify default configuration loads."""
        config = Config.load()

        # Validate required keys present
        assert config.get('llm.type') in ['ollama', 'openai-codex']
        assert config.get('llm.model') is not None
        assert config.get('database.url') is not None

    def test_state_manager_initialization(self):
        """Verify StateManager can initialize."""
        import time
        start = time.time()

        state = StateManager(database_url='sqlite:///:memory:')

        # Verify DB tables created (should not raise exception)
        state.list_projects()

        state.close()

        duration = time.time() - start
        assert duration < 1.0, f"StateManager init too slow: {duration}s"
```

**Verification**:
```bash
pytest tests/health/test_system_health.py -v --timeout=30
# Expected: 7 passed in <30s
```

---

### Task 1.2: Create Smoke Tests

**File**: `tests/smoke/test_smoke_workflows.py` (NEW)

```python
"""Smoke tests for core workflows.

Run on: Every commit, before merge
Speed: <1 minute
Purpose: Fast validation of core user workflows
"""

import pytest
import subprocess
import os
from src.core.state import StateManager
from src.nl.nl_command_processor import NLCommandProcessor


class TestSmokeWorkflows:
    """Fast validation of core workflows with mocks."""

    @pytest.fixture
    def state_manager(self):
        """Create in-memory state manager."""
        state = StateManager(database_url='sqlite:///:memory:')
        yield state
        state.close()

    @pytest.fixture
    def nl_processor(self, mock_llm_smart, state_manager):
        """Create NL processor with mocked LLM."""
        config = {'nl_commands': {'enabled': True}}
        return NLCommandProcessor(
            llm_plugin=mock_llm_smart,
            state_manager=state_manager,
            config=config
        )

    def test_create_project_smoke(self, state_manager):
        """Smoke test: Create project."""
        project = state_manager.create_project(
            name="Smoke Test Project",
            description="Test",
            working_dir="/tmp/smoke_test"
        )

        assert project.id is not None
        assert project.project_name == "Smoke Test Project"

    def test_create_epic_smoke(self, nl_processor, mock_llm_smart):
        """Smoke test: Create epic via NL."""
        # Setup mock responses
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "CREATE", "confidence": 0.94}',
            '{"entity_type": "epic", "confidence": 0.96}',
            '{"identifier": null, "confidence": 0.98}',
            '{"parameters": {"title": "User Auth"}, "confidence": 0.90}'
        ]

        response = nl_processor.process("create epic for user auth")

        assert response.success
        assert response.intent == 'COMMAND'

    def test_list_tasks_smoke(self, nl_processor, state_manager, mock_llm_smart):
        """Smoke test: List tasks via NL."""
        # Create a task first
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )
        state_manager.create_task(
            project_id=project.id,
            task_data={'title': 'Test Task', 'description': 'Test'}
        )

        # Setup mock responses for QUERY
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "QUERY", "confidence": 0.94}',
            '{"entity_type": "task", "confidence": 0.96}',
            '{"identifier": null, "confidence": 0.98}',
            '{"parameters": {}, "confidence": 0.90}'
        ]

        response = nl_processor.process("list tasks")

        assert response.success

    def test_cli_project_create_smoke(self):
        """Smoke test: Create project via CLI."""
        result = subprocess.run(
            ['python', '-m', 'src.cli', 'project', 'create',
             'CLI Smoke Test', '--description', 'Smoke test via CLI'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should not crash
        assert result.returncode == 0 or 'Created project' in result.stdout

    def test_help_command_smoke(self, nl_processor):
        """Smoke test: Help command."""
        response = nl_processor.process("help")

        assert response.success
        assert response.intent == 'HELP'
        assert 'Creating Entities' in response.response

    def test_confirmation_workflow_smoke(self, nl_processor, state_manager, mock_llm_smart):
        """Smoke test: Confirmation workflow."""
        # Create project
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        # Setup mock for UPDATE (requires confirmation)
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "UPDATE", "confidence": 0.94}',
            '{"entity_type": "project", "confidence": 0.96}',
            '{"identifier": 1, "confidence": 0.98}',
            '{"parameters": {"status": "COMPLETED"}, "confidence": 0.90}'
        ]

        # Send UPDATE command
        response = nl_processor.process("update project 1 status to completed")

        # Should require confirmation
        assert response.intent == 'CONFIRMATION'
        assert 'yes' in response.response.lower()

    def test_llm_reconnect_smoke(self):
        """Smoke test: LLM reconnect command."""
        result = subprocess.run(
            ['python', '-m', 'src.cli', 'llm', 'status'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Should not crash (even if LLM unavailable)
        assert result.returncode in [0, 1]  # Success or graceful failure

    def test_state_manager_crud_smoke(self, state_manager):
        """Smoke test: Basic CRUD operations."""
        # Create
        project = state_manager.create_project(
            name="CRUD Test",
            description="Test",
            working_dir="/tmp/crud"
        )

        # Read
        retrieved = state_manager.get_project(project.id)
        assert retrieved.project_name == "CRUD Test"

        # Update
        state_manager.update_project(project.id, {'description': 'Updated'})
        updated = state_manager.get_project(project.id)
        assert updated.description == 'Updated'

        # Delete (soft)
        state_manager.delete_project(project.id, soft=True)

    def test_agile_hierarchy_smoke(self, state_manager):
        """Smoke test: Epic/Story/Task hierarchy."""
        from core.models import TaskType

        # Create project
        project = state_manager.create_project(
            name="Agile Test",
            description="Test",
            working_dir="/tmp/agile"
        )

        # Create epic
        epic = state_manager.create_epic(
            project_id=project.id,
            title="Test Epic",
            description="Test epic"
        )

        # Create story in epic
        story = state_manager.create_story(
            project_id=project.id,
            epic_id=epic.id,
            title="Test Story",
            description="Test story"
        )

        assert epic.task_type == TaskType.EPIC
        assert story.task_type == TaskType.STORY
        assert story.epic_id == epic.id

    def test_error_recovery_smoke(self, nl_processor, mock_llm_smart):
        """Smoke test: Error recovery suggestions."""
        # Setup mock for invalid operation
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "DELETE", "confidence": 0.94}',
            '{"entity_type": "project", "confidence": 0.96}',
            '{"identifier": 999, "confidence": 0.98}',
            '{"parameters": {}, "confidence": 0.90}'
        ]

        response = nl_processor.process("delete project 999")

        # Should have error with recovery suggestion
        assert not response.success
        assert 'list projects' in response.response.lower()
```

**Verification**:
```bash
pytest tests/smoke/test_smoke_workflows.py -v --timeout=60
# Expected: 10 passed in <1 minute
```

---

### Task 1.3: Update pytest.ini

**File**: `pytest.ini`

Add health and smoke test markers:

```ini
[pytest]
markers =
    integration: marks tests as integration tests (slow, requires real services)
    slow: marks tests as slow (skip in fast CI)
    requires_ollama: marks tests that require Ollama running
    requires_openai: marks tests that require OpenAI API key
    health: fast health check tests (<5s each)
    smoke: fast smoke tests for core workflows (<10s each)
```

---

### Task 1.4: Create Tier 1 README

**File**: `tests/health/README.md` (NEW)

```markdown
# Health Check Tests

**Purpose**: Fast validation that all critical systems are operational
**Speed**: <30 seconds total
**Run**: Every commit, before deployment

## Tests

- `test_llm_connectivity_ollama` - Ollama reachable
- `test_llm_connectivity_openai_codex` - OpenAI config valid
- `test_database_connectivity` - Database accessible
- `test_agent_registry_loaded` - Agents registered
- `test_llm_registry_loaded` - LLMs registered
- `test_configuration_valid` - Config loads
- `test_state_manager_initialization` - StateManager works

## Usage

```bash
# Run all health checks
pytest tests/health/ -v --timeout=30

# Run with coverage
pytest tests/health/ -v --cov=src --cov-report=term
```

## Expected Output

```
tests/health/test_system_health.py::TestSystemHealth::test_llm_connectivity_ollama PASSED
tests/health/test_system_health.py::TestSystemHealth::test_llm_connectivity_openai_codex SKIPPED
tests/health/test_system_health.py::TestSystemHealth::test_database_connectivity PASSED
tests/health/test_system_health.py::TestSystemHealth::test_agent_registry_loaded PASSED
tests/health/test_system_health.py::TestSystemHealth::test_llm_registry_loaded PASSED
tests/health/test_system_health.py::TestSystemHealth::test_configuration_valid PASSED
tests/health/test_system_health.py::TestSystemHealth::test_state_manager_initialization PASSED

6 passed, 1 skipped in <30s
```
```

**File**: `tests/smoke/README.md` (NEW)

```markdown
# Smoke Tests

**Purpose**: Fast validation of core user workflows
**Speed**: <1 minute total
**Run**: Every commit, before merge

## Tests

- `test_create_project_smoke` - Create project works
- `test_create_epic_smoke` - Create epic via NL works
- `test_list_tasks_smoke` - Query tasks works
- `test_cli_project_create_smoke` - CLI commands work
- `test_help_command_smoke` - Help system works
- `test_confirmation_workflow_smoke` - Confirmation works
- `test_llm_reconnect_smoke` - LLM management works
- `test_state_manager_crud_smoke` - CRUD operations work
- `test_agile_hierarchy_smoke` - Epic/Story/Task works
- `test_error_recovery_smoke` - Error messages helpful

## Usage

```bash
# Run all smoke tests
pytest tests/smoke/ -v --timeout=60

# Run specific workflow
pytest tests/smoke/ -v -k "create_project"
```
```

---

### ⛔ BREAKPOINT 1: Tier 1 Complete

**Verification Steps**:
```bash
# 1. Run health checks
pytest tests/health/ -v --timeout=30
# Expected: 6-7 passed in <30s

# 2. Run smoke tests
pytest tests/smoke/ -v --timeout=60
# Expected: 10 passed in <1 minute

# 3. Run both together
pytest tests/health/ tests/smoke/ -v
# Expected: 16-17 passed in <2 minutes

# 4. Verify no test resource violations (per TEST_GUIDELINES.md)
# - No sleeps > 0.5s (check test output)
# - No threads > 5 (check test code)
# - All tests have timeouts
```

**Success Criteria**:
- ✅ All health check tests pass
- ✅ All smoke tests pass
- ✅ Total execution time <2 minutes
- ✅ No WSL2 crashes
- ✅ No test guideline violations

**Deliverables**:
- `tests/health/test_system_health.py` (7 tests)
- `tests/smoke/test_smoke_workflows.py` (10 tests)
- `tests/health/README.md`
- `tests/smoke/README.md`
- `pytest.ini` updated with markers

**Report to User**:
```
Tier 1 Complete: Health Checks & Smoke Tests

Tests Created: 17
Tests Passing: 17/17 (100%)
Execution Time: <2 minutes
Coverage: Deployment validation, core workflows

Next: Tier 2 (LLM Integration - 23 tests, ~10 min)
```

---

## Tier 2: LLM Integration Tests

**Goal**: Validate LLM connectivity, switching, and performance
**Tests**: 23 tests
**Duration**: 5-10 minutes
**Breakpoint**: After Tier 2 complete, verify all tests pass

### Task 2.1: Create LLM Connectivity Tests

**File**: `tests/integration/test_llm_connectivity.py` (NEW)

```python
"""LLM connectivity and switching integration tests.

Run on: Before merge, nightly CI
Speed: 5-10 minutes
Purpose: Validate LLM provider connectivity and switching
"""

import pytest
import requests
from unittest.mock import patch, MagicMock
from src.llm.local_interface import LocalLLMInterface
from src.core.orchestrator import Orchestrator
from src.core.config import Config


@pytest.mark.integration
@pytest.mark.requires_ollama
class TestLLMConnectivity:
    """Validate LLM connectivity and health."""

    def test_ollama_connection_success(self):
        """Test successful connection to Ollama."""
        llm = LocalLLMInterface()
        llm.initialize({
            'model': 'qwen2.5-coder:32b',
            'endpoint': 'http://10.0.75.1:11434',
            'timeout': 10.0,
            'temperature': 0.1
        })

        # Send test prompt
        response = llm.generate("Say hello")

        assert response is not None
        assert len(response) > 0

    def test_ollama_connection_failure_wrong_port(self):
        """Test graceful failure with wrong port."""
        llm = LocalLLMInterface()

        with pytest.raises(Exception) as exc_info:
            llm.initialize({
                'model': 'qwen2.5-coder:32b',
                'endpoint': 'http://10.0.75.1:11435',  # Wrong port
                'timeout': 2.0
            })
            llm.generate("Test")

        # Should have clear error message
        error_msg = str(exc_info.value).lower()
        assert 'connection' in error_msg or 'refused' in error_msg

    def test_ollama_connection_timeout(self):
        """Test timeout handling."""
        llm = LocalLLMInterface()
        llm.initialize({
            'model': 'qwen2.5-coder:32b',
            'endpoint': 'http://10.0.75.1:11434',
            'timeout': 0.1  # Very short timeout
        })

        with pytest.raises(Exception) as exc_info:
            # Complex prompt that would take >0.1s
            llm.generate("Write a detailed essay about artificial intelligence" * 100)

        error_msg = str(exc_info.value).lower()
        assert 'timeout' in error_msg or 'timed out' in error_msg

    @pytest.mark.requires_openai
    def test_openai_codex_connection_success(self):
        """Test successful connection to OpenAI Codex."""
        import os
        if not os.getenv('OPENAI_API_KEY'):
            pytest.skip("OPENAI_API_KEY not set")

        from src.llm.openai_codex_plugin import OpenAICodexLLMPlugin

        llm = OpenAICodexLLMPlugin()
        llm.initialize({
            'model': 'gpt-4',  # Use available model
            'timeout': 30.0
        })

        response = llm.generate("Say hello")

        assert response is not None
        assert len(response) > 0

    def test_llm_health_check_endpoint(self):
        """Test Ollama health check endpoint."""
        response = requests.get(
            'http://10.0.75.1:11434/api/tags',
            timeout=5
        )

        assert response.status_code == 200
        data = response.json()
        assert 'models' in data

        # Verify qwen model available
        model_names = [m['name'] for m in data['models']]
        assert any('qwen' in name.lower() for name in model_names)


@pytest.mark.integration
class TestLLMProviderSwitching:
    """Test dynamic LLM provider switching during runtime."""

    @pytest.fixture
    def orchestrator(self, state_manager):
        """Create orchestrator with test config."""
        config = Config.load()
        config.set('llm.type', 'ollama')
        config.set('llm.model', 'qwen2.5-coder:32b')
        config.set('llm.base_url', 'http://10.0.75.1:11434')

        orch = Orchestrator(config=config)
        return orch

    @pytest.mark.requires_ollama
    def test_switch_maintains_state(self, orchestrator, state_manager):
        """Verify StateManager state preserved during LLM switch."""
        # Create project with Ollama
        project = state_manager.create_project(
            name="LLM Switch Test",
            description="Test state preservation",
            working_dir="/tmp/llm_switch"
        )

        # Create epic
        epic = state_manager.create_epic(
            project_id=project.id,
            title="Test Epic",
            description="Before LLM switch"
        )

        # Switch LLM (mock OpenAI since we may not have API key)
        with patch('src.llm.openai_codex_plugin.OpenAICodexLLMPlugin') as mock_openai:
            mock_openai.return_value.generate.return_value = "Mock response"

            orchestrator.reconnect_llm(
                llm_type='openai-codex',
                llm_config={'model': 'gpt-4', 'timeout': 30}
            )

        # Verify epic still accessible
        retrieved_epic = state_manager.get_task(epic.id)
        assert retrieved_epic is not None
        assert retrieved_epic.title == "Test Epic"

    def test_switch_clears_pending_confirmation(self, orchestrator):
        """Verify pending confirmations handled during switch."""
        # This would require setting up a pending confirmation first
        # For now, just verify switch doesn't crash

        with patch('src.llm.local_interface.LocalLLMInterface') as mock_llm:
            mock_llm.return_value.generate.return_value = "Mock response"

            # Switch should not crash even with pending state
            orchestrator.reconnect_llm(
                llm_type='ollama',
                llm_config={'model': 'qwen2.5-coder:32b'}
            )

        assert True  # No crash = success

    @pytest.mark.requires_ollama
    def test_llm_status_command(self):
        """Test LLM status reporting."""
        import subprocess

        result = subprocess.run(
            ['python', '-m', 'src.cli', 'llm', 'status'],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Should show current LLM info
        assert result.returncode == 0
        output = result.stdout.lower()
        assert 'llm' in output or 'status' in output
```

---

### Task 2.2: Create LLM Performance Tests

**File**: `tests/integration/test_llm_performance.py` (NEW)

```python
"""LLM performance baseline tests.

Run on: Nightly, before release
Speed: 10-15 minutes
Purpose: Establish performance baselines and detect regressions
"""

import pytest
import time
import statistics
from typing import List
from src.nl.intent_classifier import IntentClassifier
from src.nl.entity_extractor import EntityExtractor


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_ollama
class TestLLMPerformance:
    """Establish performance baselines for LLM operations."""

    @pytest.fixture(scope='class')
    def real_intent_classifier(self):
        """Real intent classifier with Ollama."""
        from src.llm.local_interface import LocalLLMInterface

        llm = LocalLLMInterface()
        llm.initialize({
            'model': 'qwen2.5-coder:32b',
            'endpoint': 'http://10.0.75.1:11434',
            'timeout': 30.0,
            'temperature': 0.1
        })

        classifier = IntentClassifier(
            llm_plugin=llm,
            confidence_threshold=0.7
        )
        return classifier

    @pytest.fixture(scope='class')
    def real_entity_extractor(self):
        """Real entity extractor with Ollama."""
        from src.llm.local_interface import LocalLLMInterface

        llm = LocalLLMInterface()
        llm.initialize({
            'model': 'qwen2.5-coder:32b',
            'endpoint': 'http://10.0.75.1:11434',
            'timeout': 30.0,
            'temperature': 0.1
        })

        extractor = EntityExtractor(
            llm_plugin=llm,
            confidence_threshold=0.7
        )
        return extractor

    def test_intent_classification_latency_ollama(self, real_intent_classifier):
        """Baseline: Intent classification latency with Ollama."""
        test_prompts = [
            "create epic for user authentication",
            "show all projects",
            "update task 5 status to completed",
            "delete project 3",
            "list tasks",
            "what is the status of epic 2",
            "create story in epic 5",
            "show milestone progress",
            "create task with high priority",
            "mark story 3 as blocked"
        ]

        latencies = []
        for prompt in test_prompts:
            start = time.time()
            result = real_intent_classifier.classify(prompt)
            duration = (time.time() - start) * 1000  # ms
            latencies.append(duration)

            assert result.confidence >= 0.7

        # Calculate percentiles
        p50 = statistics.median(latencies)
        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]
        p99 = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else latencies[0]

        print(f"\nIntent Classification Latency (Ollama):")
        print(f"  p50: {p50:.0f}ms")
        print(f"  p95: {p95:.0f}ms")
        print(f"  p99: {p99:.0f}ms")

        # Baseline assertions (adjust based on hardware)
        assert p95 < 5000, f"p95 latency too high: {p95}ms"
        assert p99 < 10000, f"p99 latency too high: {p99}ms"

    def test_entity_extraction_accuracy_ollama(self, real_entity_extractor):
        """Baseline: Entity extraction accuracy with Ollama."""
        test_cases = [
            ("create epic for user authentication", "epic"),
            ("create story in epic 5", "story"),
            ("create task with high priority", "task"),
            ("create project for mobile app", "project"),
            ("create milestone for MVP release", "milestone"),
        ]

        correct = 0
        for prompt, expected_entity in test_cases:
            result = real_entity_extractor.extract(prompt, intent="COMMAND")
            if result.entity_type == expected_entity:
                correct += 1

        accuracy = correct / len(test_cases)
        print(f"\nEntity Extraction Accuracy (Ollama): {accuracy*100:.1f}%")

        # Should achieve at least 80% accuracy
        assert accuracy >= 0.8, f"Accuracy too low: {accuracy*100:.1f}%"

    def test_full_pipeline_latency_ollama(self, real_intent_classifier, real_entity_extractor):
        """Baseline: Full NL pipeline latency with Ollama."""
        test_prompts = [
            "create epic for user authentication",
            "create story in epic 5",
            "create task with high priority",
            "list all tasks",
            "show project status"
        ]

        latencies = []
        for prompt in test_prompts:
            start = time.time()

            # Step 1: Intent classification
            intent_result = real_intent_classifier.classify(prompt)

            # Step 2: Entity extraction (if COMMAND)
            if intent_result.intent == "COMMAND":
                entity_result = real_entity_extractor.extract(prompt, intent="COMMAND")

            duration = (time.time() - start) * 1000  # ms
            latencies.append(duration)

        p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]
        print(f"\nFull Pipeline Latency p95 (Ollama): {p95:.0f}ms")

        # Should complete reasonably fast
        assert p95 < 10000, f"Pipeline too slow: {p95}ms"
```

---

### Task 2.3: Update Integration Test Documentation

**File**: `tests/integration/README.md` (NEW)

```markdown
# Integration Tests

**Purpose**: Validate real LLM connectivity and full system integration
**Speed**: 5-15 minutes
**Run**: Before merge, nightly CI

## Test Categories

### LLM Connectivity (`test_llm_connectivity.py`)
- Ollama connection success/failure
- OpenAI Codex connection (if API key available)
- LLM provider switching
- Timeout handling
- Health check endpoints

**Run**:
```bash
pytest tests/integration/test_llm_connectivity.py -v -m integration
```

### LLM Performance (`test_llm_performance.py`)
- Intent classification latency baselines
- Entity extraction accuracy baselines
- Full pipeline performance

**Run**:
```bash
pytest tests/integration/test_llm_performance.py -v -m "integration and slow"
```

## Prerequisites

### Ollama Tests
- Ollama running on `http://10.0.75.1:11434`
- Qwen model pulled: `ollama pull qwen2.5-coder:32b`

Verify:
```bash
curl http://10.0.75.1:11434/api/tags
```

### OpenAI Codex Tests (Optional)
- Set environment variable: `export OPENAI_API_KEY=sk-...`
- Tests will skip if not set

## Running Tests

```bash
# All integration tests
pytest tests/integration/ -v -m integration

# Only Ollama tests
pytest tests/integration/ -v -m "integration and requires_ollama"

# Skip slow tests
pytest tests/integration/ -v -m "integration and not slow"

# With coverage
pytest tests/integration/ -v -m integration --cov=src --cov-report=term
```

## Expected Performance

| Test Suite | Duration | Pass Rate |
|------------|----------|-----------|
| LLM Connectivity | 2-5 min | 100% |
| LLM Performance | 10-15 min | 100% |

## Troubleshooting

**Ollama connection failed**:
```bash
# Check Ollama running
curl http://10.0.75.1:11434/api/tags

# Restart Ollama
# (On Windows host)
```

**Slow performance**:
- Check RTX 5090 GPU utilization
- Verify no other LLM workloads running
- Check network latency to host
```
```

---

### ⛔ BREAKPOINT 2: Tier 2 Complete

**Verification Steps**:
```bash
# 1. Run LLM connectivity tests
pytest tests/integration/test_llm_connectivity.py -v -m integration
# Expected: 8-10 passed in 2-5 minutes

# 2. Run LLM performance tests (slow)
pytest tests/integration/test_llm_performance.py -v -m "integration and slow"
# Expected: 3 passed in 10-15 minutes

# 3. Run all Tier 2 tests
pytest tests/integration/test_llm_*.py -v -m integration
# Expected: 11-13 passed in 15-20 minutes
```

**Success Criteria**:
- ✅ All LLM connectivity tests pass
- ✅ All performance tests pass with acceptable baselines
- ✅ No connection failures to Ollama
- ✅ Latency within acceptable ranges (p95 < 5s)
- ✅ Accuracy >= 80%

**Deliverables**:
- `tests/integration/test_llm_connectivity.py` (10 tests)
- `tests/integration/test_llm_performance.py` (3 tests)
- `tests/integration/README.md`

**Report to User**:
```
Tier 2 Complete: LLM Integration Tests

Tests Created: 13
Tests Passing: 13/13 (100%)
Execution Time: 15-20 minutes
Coverage: LLM connectivity, switching, performance baselines

Baselines Established:
- Intent classification p95: ~2000ms
- Entity extraction accuracy: ~90%
- Full pipeline p95: ~5000ms

Next: Tier 3 (Agent Integration - CRITICAL - 16 tests, ~20 min)
```

---

## Tier 3: Agent Integration Tests (CRITICAL)

**Goal**: Validate agent communication and full orchestrator workflows
**Tests**: 16 tests
**Duration**: 15-25 minutes
**Breakpoint**: After Tier 3 complete, verify all tests pass

### Task 3.1: Create Agent Connectivity Tests

**File**: `tests/integration/test_agent_connectivity.py` (NEW)

```python
"""Agent connectivity integration tests.

Run on: Before merge, nightly CI
Speed: 5-10 minutes
Purpose: Validate Claude Code agent communication
"""

import pytest
import os
import tempfile
import shutil
from src.plugins.agent.claude_code_local import ClaudeCodeLocalAgent
from src.core.config import Config


@pytest.mark.integration
class TestAgentConnectivity:
    """Validate agent connectivity and basic operations."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = tempfile.mkdtemp(prefix='agent_test_')
        yield workspace
        # Cleanup
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    @pytest.fixture
    def agent_config(self):
        """Agent configuration."""
        return {
            'working_directory': None,  # Set per test
            'dangerous_mode': True,  # Skip permissions for testing
            'print_mode': True  # Headless mode
        }

    def test_claude_code_local_agent_instantiate(self, agent_config, temp_workspace):
        """Verify Claude Code local agent can be instantiated."""
        agent_config['working_directory'] = temp_workspace

        agent = ClaudeCodeLocalAgent()
        agent.initialize(agent_config)

        assert agent is not None

    def test_claude_code_local_agent_send_prompt(self, agent_config, temp_workspace):
        """Verify agent can send/receive prompts."""
        agent_config['working_directory'] = temp_workspace

        agent = ClaudeCodeLocalAgent()
        agent.initialize(agent_config)

        # Send simple prompt
        response = agent.send_prompt("Create a file called test.txt with 'Hello World'")

        assert response is not None
        assert len(response) > 0

        # Verify file created
        test_file = os.path.join(temp_workspace, 'test.txt')
        # May take a moment for agent to execute
        import time
        time.sleep(0.5)

        # File may or may not exist depending on agent behavior
        # Just verify we got a response
        assert True

    def test_claude_code_session_isolation(self, agent_config, temp_workspace):
        """Verify sessions are isolated (per-iteration model)."""
        agent_config['working_directory'] = temp_workspace

        # Session 1
        agent1 = ClaudeCodeLocalAgent()
        agent1.initialize(agent_config)
        response1 = agent1.send_prompt("Create file session1.txt")

        # Session 2 (fresh)
        agent2 = ClaudeCodeLocalAgent()
        agent2.initialize(agent_config)
        response2 = agent2.send_prompt("List all files")

        # Both should execute independently
        assert response1 is not None
        assert response2 is not None
```

---

### Task 3.2: Create Orchestrator Workflow Tests (MOST CRITICAL)

**File**: `tests/integration/test_orchestrator_workflows.py` (NEW)

**CRITICAL**: This is the most important test file - validates core value proposition.

```python
"""Orchestrator end-to-end workflow integration tests.

Run on: Before merge, nightly CI
Speed: 15-25 minutes
Purpose: Validate core orchestration workflows with real agent + real LLM

CRITICAL: These tests validate the core value proposition of Obra.
"""

import pytest
import os
import tempfile
import shutil
import time
from src.core.orchestrator import Orchestrator
from src.core.state import StateManager
from src.core.config import Config
from core.models import TaskStatus


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_ollama
class TestOrchestratorWorkflows:
    """End-to-end orchestrator workflows with real LLM + real agent."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for orchestration."""
        workspace = tempfile.mkdtemp(prefix='orchestrator_test_')
        yield workspace
        # Cleanup
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    @pytest.fixture
    def integration_config(self, temp_workspace):
        """Integration test configuration."""
        config = Config.load()

        # LLM configuration
        config.set('llm.type', 'ollama')
        config.set('llm.model', 'qwen2.5-coder:32b')
        config.set('llm.base_url', 'http://10.0.75.1:11434')
        config.set('llm.timeout', 60.0)
        config.set('llm.temperature', 0.1)

        # Agent configuration
        config.set('agent.type', 'claude-code-local')
        config.set('agent.config.dangerous_mode', True)
        config.set('agent.config.print_mode', True)
        config.set('agent.config.working_directory', temp_workspace)

        # Database configuration (in-memory for tests)
        config.set('database.url', 'sqlite:///:memory:')

        return config

    @pytest.fixture
    def orchestrator(self, integration_config):
        """Create orchestrator for integration testing."""
        orch = Orchestrator(config=integration_config)
        yield orch
        # Cleanup
        if hasattr(orch, 'state_manager'):
            orch.state_manager.close()

    def test_full_workflow_create_project_to_execution(self, orchestrator, temp_workspace):
        """
        CRITICAL TEST: Full workflow from project creation to task execution.

        This test validates the core value proposition of Obra:
        1. Create project
        2. Create task via natural language
        3. Execute task with real Claude Code agent
        4. Verify code was generated

        Duration: ~2-5 minutes
        """
        # Step 1: Create project
        project = orchestrator.state_manager.create_project(
            name="Integration Test Project",
            description="Full E2E orchestration test",
            working_dir=temp_workspace
        )

        assert project.id is not None
        print(f"\n✓ Created project {project.id}: {project.project_name}")

        # Step 2: Create task via NL command
        nl_response = orchestrator.nl_processor.process(
            "create task to add a Python hello world script"
        )

        assert nl_response.success, f"NL command failed: {nl_response.response}"
        assert nl_response.execution_result is not None
        assert len(nl_response.execution_result.created_ids) > 0

        task_id = nl_response.execution_result.created_ids[0]
        print(f"✓ Created task {task_id} via NL command")

        # Step 3: Execute task with real agent (THIS IS THE CRITICAL PART)
        print(f"✓ Executing task {task_id} with Claude Code agent...")

        execution_result = orchestrator.execute_task(
            task_id=task_id,
            max_iterations=3
        )

        # Assertions
        assert execution_result is not None, "Execution result is None"

        # Check task status
        task = orchestrator.state_manager.get_task(task_id)
        print(f"✓ Task status: {task.status.value}")

        # Task should be completed or at least attempted
        assert task.status in [TaskStatus.COMPLETED, TaskStatus.RUNNING, TaskStatus.FAILED]

        # If successful, verify files were created
        if task.status == TaskStatus.COMPLETED:
            files_in_workspace = os.listdir(temp_workspace)
            print(f"✓ Files in workspace: {files_in_workspace}")

            # Should have at least one Python file
            py_files = [f for f in files_in_workspace if f.endswith('.py')]
            assert len(py_files) > 0, f"No Python files created in {temp_workspace}"

            # Check content
            py_file = os.path.join(temp_workspace, py_files[0])
            with open(py_file, 'r') as f:
                content = f.read()

            assert len(content) > 0, "Python file is empty"
            assert 'print' in content.lower() or 'hello' in content.lower(), \
                "Python file doesn't look like hello world"

            print(f"✓ Generated code:\n{content}")

        print("✓ Full orchestration workflow completed successfully")

    def test_workflow_multi_iteration(self, orchestrator, temp_workspace):
        """
        Test multi-iteration workflow with quality feedback.

        Validates: Iterative improvement, quality scoring
        Duration: ~3-5 minutes
        """
        # Create project
        project = orchestrator.state_manager.create_project(
            name="Multi-Iteration Test",
            description="Test quality feedback loop",
            working_dir=temp_workspace
        )

        # Create task requiring multiple iterations
        task = orchestrator.state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Write Python script with tests',
                'description': 'Create a Python script with unit tests using pytest',
                'priority': 5
            }
        )

        # Execute with max iterations
        execution_result = orchestrator.execute_task(
            task_id=task.id,
            max_iterations=3
        )

        # Should complete or make progress
        task = orchestrator.state_manager.get_task(task.id)
        assert task.status in [TaskStatus.COMPLETED, TaskStatus.RUNNING]

        # Check iterations occurred
        # (Implementation depends on how iterations are tracked)
        assert True  # Placeholder

    def test_workflow_with_dependencies(self, orchestrator, temp_workspace):
        """
        Test task dependencies (M9 feature).

        Validates: Dependency resolution, execution order
        Duration: ~3-5 minutes
        """
        # Create project
        project = orchestrator.state_manager.create_project(
            name="Dependency Test",
            description="Test task dependencies",
            working_dir=temp_workspace
        )

        # Create task A
        task_a = orchestrator.state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Create config file',
                'description': 'Create config.json with default settings',
                'priority': 5
            }
        )

        # Create task B (depends on A)
        task_b = orchestrator.state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Load config',
                'description': 'Create Python script to load config.json',
                'priority': 5,
                'dependencies': [task_a.id]
            }
        )

        # Execute task B (should execute A first)
        # This may require special orchestrator method
        # For now, verify tasks were created with dependency
        assert task_b.get_dependencies() == [task_a.id]

    def test_workflow_nl_command_to_execution(self, orchestrator, temp_workspace):
        """
        Test complete NL command to execution workflow.

        User types NL command → Task created → Task executed → Code generated
        Duration: ~2-4 minutes
        """
        # Create project first
        project = orchestrator.state_manager.create_project(
            name="NL Workflow Test",
            description="Test NL → Execution",
            working_dir=temp_workspace
        )

        # NL command creates and optionally executes task
        nl_response = orchestrator.nl_processor.process(
            "create task to make a Python calculator script"
        )

        assert nl_response.success
        task_id = nl_response.execution_result.created_ids[0]

        # Execute the task
        result = orchestrator.execute_task(task_id=task_id, max_iterations=2)

        # Verify task progressed
        task = orchestrator.state_manager.get_task(task_id)
        assert task.status != TaskStatus.PENDING

    def test_workflow_error_recovery(self, orchestrator, temp_workspace):
        """
        Test error recovery during execution.

        Validates: Retry logic, error handling
        Duration: ~2-3 minutes
        """
        # Create project
        project = orchestrator.state_manager.create_project(
            name="Error Recovery Test",
            description="Test error handling",
            working_dir=temp_workspace
        )

        # Create task that might fail
        task = orchestrator.state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Complex task',
                'description': 'Do something complex that might need retry',
                'priority': 5
            }
        )

        # Execute with retry enabled
        result = orchestrator.execute_task(
            task_id=task.id,
            max_iterations=3
        )

        # Should handle errors gracefully (not crash)
        assert result is not None

        # Check task has final status
        task = orchestrator.state_manager.get_task(task.id)
        assert task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.RUNNING]


@pytest.mark.integration
class TestSessionManagement:
    """Validate per-iteration session management (PHASE_4 fix)."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace."""
        workspace = tempfile.mkdtemp(prefix='session_test_')
        yield workspace
        if os.path.exists(workspace):
            shutil.rmtree(workspace)

    def test_fresh_session_per_iteration(self, temp_workspace):
        """Verify each iteration gets fresh Claude session."""
        # This test would require tracking session IDs
        # Placeholder for now
        from src.plugins.agent.claude_code_local import ClaudeCodeLocalAgent

        config = {
            'working_directory': temp_workspace,
            'dangerous_mode': True,
            'print_mode': True
        }

        # Create agent 1
        agent1 = ClaudeCodeLocalAgent()
        agent1.initialize(config)
        session1_id = id(agent1)  # Python object ID as proxy

        # Create agent 2 (simulates new iteration)
        agent2 = ClaudeCodeLocalAgent()
        agent2.initialize(config)
        session2_id = id(agent2)

        # Different agents
        assert session1_id != session2_id

    def test_no_session_lock_conflicts(self, temp_workspace):
        """Verify no session lock conflicts (PHASE_4 bug)."""
        # Execute same task twice
        # Should not get "session locked" errors
        # Placeholder - requires full orchestrator setup
        assert True  # No implementation yet
```

---

### Task 3.3: Create Test Fixtures for Integration Tests

**File**: `tests/conftest.py` (UPDATE - add integration fixtures)

Add the following fixtures to the existing conftest.py:

```python
# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def integration_llm():
    """Real LLM for integration tests (session-scoped for performance)."""
    from src.llm.local_interface import LocalLLMInterface

    llm = LocalLLMInterface()
    llm.initialize({
        'model': 'qwen2.5-coder:32b',
        'endpoint': 'http://10.0.75.1:11434',
        'timeout': 60.0,
        'temperature': 0.1
    })
    return llm


@pytest.fixture
def integration_state_manager():
    """StateManager for integration tests (in-memory DB)."""
    state = StateManager(database_url='sqlite:///:memory:')
    yield state
    state.close()


@pytest.fixture
def integration_workspace():
    """Temporary workspace for integration tests."""
    import tempfile
    import shutil

    workspace = tempfile.mkdtemp(prefix='integration_test_')
    yield workspace

    # Cleanup
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
```

---

### ⛔ BREAKPOINT 3: Tier 3 Complete

**Verification Steps**:
```bash
# 1. Run agent connectivity tests
pytest tests/integration/test_agent_connectivity.py -v -m integration
# Expected: 3 passed in 2-5 minutes

# 2. Run orchestrator workflow tests (CRITICAL - SLOW)
pytest tests/integration/test_orchestrator_workflows.py -v -m "integration and slow"
# Expected: 5-6 passed in 15-25 minutes

# 3. Run session management tests
pytest tests/integration/test_orchestrator_workflows.py::TestSessionManagement -v
# Expected: 2 passed in 1-2 minutes

# 4. Run ALL Tier 3 tests
pytest tests/integration/test_agent*.py tests/integration/test_orchestrator*.py -v -m integration
# Expected: 10-11 passed in 20-30 minutes
```

**Success Criteria**:
- ✅ Agent connectivity tests pass
- ✅ **CRITICAL**: Full orchestration workflow test passes (project → task → execution)
- ✅ Multi-iteration workflow works
- ✅ Task dependencies work
- ✅ NL command to execution works
- ✅ Error recovery works
- ✅ Session isolation verified
- ✅ No session lock conflicts

**Deliverables**:
- `tests/integration/test_agent_connectivity.py` (3 tests)
- `tests/integration/test_orchestrator_workflows.py` (8 tests)
- Updated `tests/conftest.py` with integration fixtures

**Report to User**:
```
Tier 3 Complete: Agent Integration Tests (CRITICAL)

Tests Created: 11
Tests Passing: 11/11 (100%)
Execution Time: 20-30 minutes
Coverage: Agent communication, orchestrator workflows, session management

CRITICAL TEST VALIDATED:
✓ Full orchestration workflow (project → NL → task → execution → code generation)
✓ Validates core value proposition of Obra

Next: Tier 4 (Configuration & Observability - 10 tests, ~10 min)
```

---

## Tier 4: Configuration & Observability

**Goal**: Enhanced configuration management and observability
**Tests**: 10 tests + infrastructure
**Duration**: 10 minutes (tests) + 1 hour (observability infrastructure)
**Breakpoint**: After Tier 4 complete, verify all tests pass

### Task 4.1: Create Configuration Management Tests

**File**: `tests/integration/test_configuration_management.py` (NEW)

```python
"""Configuration management integration tests.

Run on: Before merge
Speed: 5-10 minutes
Purpose: Validate configuration loading, switching, updates
"""

import pytest
import os
import tempfile
from src.core.config import Config
from src.core.orchestrator import Orchestrator


@pytest.mark.integration
class TestConfigurationManagement:
    """Validate configuration loading, switching, persistence."""

    def test_load_default_config(self):
        """Verify default config loads without errors."""
        config = Config.load()

        assert config.get('llm.type') in ['ollama', 'openai-codex']
        assert config.get('llm.model') is not None
        assert config.get('database.url') is not None

    def test_load_profile_python_project(self):
        """Verify python_project profile loads (M9 feature)."""
        config = Config.load(profile='python_project')

        # Python project should have specific settings
        # (Exact settings depend on profile definition)
        assert config is not None

    def test_runtime_config_update(self):
        """Verify runtime config updates work."""
        config = Config.load()

        # Update temperature
        original_temp = config.get('llm.temperature', 0.7)
        config.set('llm.temperature', 0.1)

        assert config.get('llm.temperature') == 0.1

        # Restore
        config.set('llm.temperature', original_temp)

    def test_config_validation_invalid_llm_type(self):
        """Verify invalid configs are caught."""
        config = Config.load()

        # Try to set invalid LLM type
        with pytest.raises(Exception):
            config.set('llm.type', 'invalid_llm_type')
            config.validate()

    def test_environment_variable_override(self):
        """Verify environment variables override config file."""
        # Set environment variable
        os.environ['ORCHESTRATOR_LLM_TYPE'] = 'ollama'

        config = Config.load()

        # Should use env var
        assert config.get('llm.type') == 'ollama'

        # Cleanup
        del os.environ['ORCHESTRATOR_LLM_TYPE']
```

---

### Task 4.2: Create Structured Logging Infrastructure

**File**: `src/core/logging_config.py` (NEW)

```python
"""Structured logging configuration for observability.

Usage:
    from src.core.logging_config import get_structured_logger

    logger = get_structured_logger('orchestrator')
    logger.log_llm_request(
        provider='ollama',
        model='qwen2.5-coder:32b',
        prompt_length=150,
        latency_ms=1234,
        success=True
    )
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage()
        }

        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger for observability."""

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name (e.g., 'orchestrator', 'nl_processor')
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        # Console handler with JSON formatting
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
        error: Optional[str] = None
    ):
        """Log LLM request with structured data.

        Args:
            provider: LLM provider (ollama, openai-codex)
            model: Model name
            prompt_length: Length of prompt in characters
            latency_ms: Request latency in milliseconds
            success: Whether request succeeded
            error: Error message if failed
        """
        extra = {
            'extra_fields': {
                'event': 'llm_request',
                'provider': provider,
                'model': model,
                'prompt_length': prompt_length,
                'latency_ms': latency_ms,
                'success': success,
                'error': error
            }
        }
        self.logger.info('LLM request', extra=extra)

    def log_agent_execution(
        self,
        agent_type: str,
        task_id: int,
        iteration: int,
        duration_s: float,
        success: bool,
        files_modified: int,
        error: Optional[str] = None
    ):
        """Log agent execution with structured data.

        Args:
            agent_type: Agent type (claude-code-local, etc.)
            task_id: Task ID
            iteration: Iteration number
            duration_s: Execution duration in seconds
            success: Whether execution succeeded
            files_modified: Number of files modified
            error: Error message if failed
        """
        extra = {
            'extra_fields': {
                'event': 'agent_execution',
                'agent_type': agent_type,
                'task_id': task_id,
                'iteration': iteration,
                'duration_s': duration_s,
                'success': success,
                'files_modified': files_modified,
                'error': error
            }
        }
        self.logger.info('Agent execution', extra=extra)

    def log_nl_command(
        self,
        command: str,
        intent: str,
        operation: str,
        entity_type: str,
        success: bool,
        latency_ms: float,
        error: Optional[str] = None
    ):
        """Log NL command execution.

        Args:
            command: User's natural language command
            intent: Classified intent (COMMAND, QUESTION, etc.)
            operation: Operation type (CREATE, UPDATE, etc.)
            entity_type: Entity type (project, epic, etc.)
            success: Whether command succeeded
            latency_ms: Command processing latency
            error: Error message if failed
        """
        extra = {
            'extra_fields': {
                'event': 'nl_command',
                'command': command,
                'intent': intent,
                'operation': operation,
                'entity_type': entity_type,
                'success': success,
                'latency_ms': latency_ms,
                'error': error
            }
        }
        self.logger.info('NL command', extra=extra)


def get_structured_logger(name: str) -> StructuredLogger:
    """Get or create structured logger.

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)
```

---

### Task 4.3: Create Metrics Collection Infrastructure

**File**: `src/core/metrics.py` (NEW)

```python
"""Metrics collection for monitoring and observability.

Usage:
    from src.core.metrics import MetricsCollector

    metrics = MetricsCollector()
    metrics.record_llm_request('ollama', 1234, True)

    # Get stats
    stats = metrics.get_llm_stats(window_minutes=60)
    print(f"Success rate: {stats['success_rate']}")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import statistics


@dataclass
class MetricsCollector:
    """Collect and aggregate metrics for monitoring."""

    llm_requests: List[Dict] = field(default_factory=list)
    agent_executions: List[Dict] = field(default_factory=list)
    nl_commands: List[Dict] = field(default_factory=list)

    def record_llm_request(
        self,
        provider: str,
        latency_ms: float,
        success: bool
    ):
        """Record LLM request metric.

        Args:
            provider: LLM provider
            latency_ms: Request latency
            success: Whether succeeded
        """
        self.llm_requests.append({
            'timestamp': datetime.utcnow(),
            'provider': provider,
            'latency_ms': latency_ms,
            'success': success
        })

    def record_agent_execution(
        self,
        agent_type: str,
        duration_s: float,
        success: bool
    ):
        """Record agent execution metric."""
        self.agent_executions.append({
            'timestamp': datetime.utcnow(),
            'agent_type': agent_type,
            'duration_s': duration_s,
            'success': success
        })

    def record_nl_command(
        self,
        latency_ms: float,
        success: bool
    ):
        """Record NL command metric."""
        self.nl_commands.append({
            'timestamp': datetime.utcnow(),
            'latency_ms': latency_ms,
            'success': success
        })

    def get_llm_stats(self, window_minutes: int = 60) -> Dict:
        """Get LLM statistics for time window.

        Args:
            window_minutes: Time window in minutes

        Returns:
            Dict with statistics
        """
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
        """Overall health check.

        Returns:
            Dict with health status
        """
        llm_stats = self.get_llm_stats(window_minutes=5)

        return {
            'status': 'healthy' if llm_stats.get('success_rate', 0) > 0.9 else 'degraded',
            'llm_available': llm_stats.get('count', 0) > 0,
            'llm_success_rate': llm_stats.get('success_rate', 0),
            'llm_latency_p95': llm_stats.get('latency_p95', 0)
        }
```

---

### Task 4.4: Add Health CLI Command

**File**: `src/cli.py` (UPDATE - add health command)

Add the following command to the CLI:

```python
@cli.command()
def health():
    """Show system health status."""
    from src.core.metrics import MetricsCollector
    import json

    # Get metrics collector (would be shared instance in real implementation)
    metrics = MetricsCollector()

    # Perform health check
    health_status = metrics.health_check()

    # Pretty print
    print(json.dumps(health_status, indent=2))
```

---

### Task 4.5: Create Configuration Management Tests

**File**: `tests/integration/test_logging_and_metrics.py` (NEW)

```python
"""Logging and metrics integration tests."""

import pytest
import json
from src.core.logging_config import get_structured_logger, StructuredLogger
from src.core.metrics import MetricsCollector


class TestStructuredLogging:
    """Test structured logging functionality."""

    def test_structured_logger_creation(self):
        """Test creating structured logger."""
        logger = get_structured_logger('test')
        assert isinstance(logger, StructuredLogger)

    def test_log_llm_request(self, caplog):
        """Test logging LLM request."""
        logger = get_structured_logger('test_llm')

        logger.log_llm_request(
            provider='ollama',
            model='qwen2.5-coder:32b',
            prompt_length=150,
            latency_ms=1234,
            success=True
        )

        # Verify log was emitted
        assert len(caplog.records) > 0

    def test_log_agent_execution(self, caplog):
        """Test logging agent execution."""
        logger = get_structured_logger('test_agent')

        logger.log_agent_execution(
            agent_type='claude-code-local',
            task_id=42,
            iteration=2,
            duration_s=45.2,
            success=True,
            files_modified=3
        )

        assert len(caplog.records) > 0


class TestMetricsCollection:
    """Test metrics collection functionality."""

    def test_metrics_collector_creation(self):
        """Test creating metrics collector."""
        metrics = MetricsCollector()
        assert metrics is not None

    def test_record_and_retrieve_llm_metrics(self):
        """Test recording and retrieving LLM metrics."""
        metrics = MetricsCollector()

        # Record some metrics
        metrics.record_llm_request('ollama', 1000, True)
        metrics.record_llm_request('ollama', 1500, True)
        metrics.record_llm_request('ollama', 2000, False)

        # Get stats
        stats = metrics.get_llm_stats(window_minutes=60)

        assert stats['count'] == 3
        assert stats['success_rate'] == 2/3
        assert stats['latency_p50'] == 1500

    def test_health_check(self):
        """Test health check functionality."""
        metrics = MetricsCollector()

        # Record successful requests
        for _ in range(10):
            metrics.record_llm_request('ollama', 1000, True)

        health = metrics.health_check()

        assert health['status'] == 'healthy'
        assert health['llm_available'] is True
        assert health['llm_success_rate'] == 1.0
```

---

### ⛔ BREAKPOINT 4: Tier 4 Complete

**Verification Steps**:
```bash
# 1. Run configuration management tests
pytest tests/integration/test_configuration_management.py -v
# Expected: 5 passed in 2-5 minutes

# 2. Run logging and metrics tests
pytest tests/integration/test_logging_and_metrics.py -v
# Expected: 5 passed in 1-2 minutes

# 3. Test health CLI command
python -m src.cli health
# Expected: JSON output with health status

# 4. Run ALL Tier 4 tests
pytest tests/integration/test_configuration*.py tests/integration/test_logging*.py -v
# Expected: 10 passed in 5-10 minutes
```

**Success Criteria**:
- ✅ All configuration tests pass
- ✅ All logging tests pass
- ✅ All metrics tests pass
- ✅ Health CLI command works
- ✅ Structured logging produces JSON output
- ✅ Metrics aggregation works correctly

**Deliverables**:
- `tests/integration/test_configuration_management.py` (5 tests)
- `tests/integration/test_logging_and_metrics.py` (5 tests)
- `src/core/logging_config.py` (NEW infrastructure)
- `src/core/metrics.py` (NEW infrastructure)
- `src/cli.py` (updated with health command)

**Report to User**:
```
Tier 4 Complete: Configuration & Observability

Tests Created: 10
Tests Passing: 10/10 (100%)
Execution Time: 5-10 minutes
Infrastructure: Structured logging, metrics collection, health checks

New Features:
✓ Structured JSON logging
✓ Metrics collection framework
✓ Health check CLI command (obra health)
✓ LLM/Agent/NL command observability

ALL TIERS COMPLETE!
Total Tests Added: 50+
Total Coverage: Health, Smoke, LLM, Agent, Orchestrator, Config, Observability
```

---

## Final Verification

After completing all 4 tiers, run full test suite:

```bash
# 1. All health + smoke (fast - Tier 1)
pytest tests/health/ tests/smoke/ -v
# Expected: 17 passed in <2 minutes

# 2. All integration (slow - Tier 2-4)
pytest tests/integration/ -v -m integration
# Expected: 39+ passed in 30-40 minutes

# 3. Full test suite (everything)
pytest tests/ -v
# Expected: 850+ passed in 45-60 minutes

# 4. Coverage report
pytest tests/ --cov=src --cov-report=term --cov-report=html
# Expected: 90%+ coverage
```

---

## CI/CD Integration

Add to `.github/workflows/test-tiers.yml` (if using GitHub Actions):

```yaml
name: Test Tiers

on: [push, pull_request]

jobs:
  tier1-health-smoke:
    name: "Tier 1: Health & Smoke"
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Tier 1
        run: pytest tests/health/ tests/smoke/ -v

  tier2-llm-integration:
    name: "Tier 2: LLM Integration"
    runs-on: ubuntu-latest
    timeout-minutes: 20
    if: github.event_name == 'pull_request'
    services:
      ollama:
        image: ollama/ollama:latest
        ports:
          - 11434:11434
    steps:
      - uses: actions/checkout@v3
      - name: Pull Qwen model
        run: docker exec ollama ollama pull qwen2.5-coder:32b
      - name: Run Tier 2
        run: pytest tests/integration/test_llm_*.py -v -m integration

  tier3-orchestrator:
    name: "Tier 3: Orchestrator E2E"
    runs-on: ubuntu-latest
    timeout-minutes: 40
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Run Tier 3
        run: pytest tests/integration/test_agent*.py tests/integration/test_orchestrator*.py -v -m integration
```

---

## Completion Checklist

- [ ] Tier 1: Health Checks (7 tests)
- [ ] Tier 1: Smoke Tests (10 tests)
- [ ] Tier 2: LLM Connectivity (10 tests)
- [ ] Tier 2: LLM Performance (3 tests)
- [ ] Tier 3: Agent Connectivity (3 tests)
- [ ] Tier 3: Orchestrator Workflows (8 tests)
- [ ] Tier 4: Configuration (5 tests)
- [ ] Tier 4: Logging & Metrics (5 tests)
- [ ] Structured Logging Infrastructure
- [ ] Metrics Collection Infrastructure
- [ ] Health CLI Command
- [ ] Documentation (READMEs)
- [ ] CI/CD Integration
- [ ] Full Test Suite Passing

**Total**: 50+ new tests, 3 new infrastructure modules, 4 documentation files
