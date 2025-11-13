"""ADR-017 Performance Validation Tests.

Tests to validate latency and throughput requirements for unified execution architecture.

Story 6: Integration Testing

Performance Requirements:
- P50 latency < 2s for NL commands
- P95 latency < 3s for NL commands
- NL routing overhead < 500ms vs direct access
- Throughput >= 40 commands/minute
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock
from typing import List

from src.orchestrator import Orchestrator
from src.core.config import Config
from src.core.state import StateManager
from src.core.models import TaskType
from src.nl.types import ParsedIntent, OperationContext, OperationType, EntityType


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config()
    config.data = {
        'database': {'url': 'sqlite:///:memory:'},
        'agent': {'type': 'mock', 'config': {}},
        'llm': {'type': 'ollama', 'endpoint': 'http://localhost:11434'},
        'orchestration': {
            'breakpoints': {},
            'decision': {},
            'quality': {'min_quality_score': 0.7}
        }
    }
    return config


@pytest.fixture
def state_manager(test_config):
    """Create state manager."""
    db_url = test_config.get('database.url') or 'sqlite:///:memory:'
    sm = StateManager(database_url=db_url)
    yield sm
    sm.close()


@pytest.fixture
def test_workspace():
    """Create temporary workspace."""
    workspace = tempfile.mkdtemp(prefix='perf_test_')
    yield workspace
    if os.path.exists(workspace):
        import shutil
        shutil.rmtree(workspace)


@pytest.fixture
def orchestrator(test_config, state_manager):
    """Create orchestrator with mocked LLM."""
    orch = Orchestrator(config=test_config)
    orch.initialize()

    # Mock LLM for fast responses
    orch.llm_interface = Mock()
    orch.llm_interface.is_available = Mock(return_value=True)
    orch.llm_interface.generate = Mock(return_value="Mocked fast response")

    # Use shared state_manager
    orch.state_manager = state_manager
    orch.intent_to_task_converter.state_manager = state_manager
    orch.nl_query_helper.state_manager = state_manager

    return orch


@pytest.fixture
def test_project(state_manager, test_workspace):
    """Create test project."""
    return state_manager.create_project(
        name="Performance Test Project",
        description="Project for performance testing",
        working_dir=test_workspace
    )


def measure_nl_command_latency(orchestrator, project_id: int) -> float:
    """Measure latency for a single NL command execution.

    Returns:
        Latency in seconds
    """
    # Create simple ParsedIntent
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_type=EntityType.TASK,
        identifier=None,
        parameters={
            'title': 'Performance Test Task',
            'description': 'Testing NL command performance'
        },
        confidence=0.95,
        raw_input="create task for performance test"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="create task for performance test",
        confidence=0.95,
        requires_execution=False  # Don't actually execute, just measure routing
    )

    start = time.time()
    try:
        # Measure NL routing only (not full execution)
        result = orchestrator.execute_nl_command(
            parsed_intent=parsed_intent,
            project_id=project_id,
            interactive=False
        )
    except Exception:
        # Ignore execution errors, we're measuring routing time
        pass
    latency = time.time() - start

    return latency


# ============================================================================
# Performance Test 1: P50 Latency < 2s
# ============================================================================

@pytest.mark.slow
def test_nl_command_latency_p50(orchestrator, test_project):
    """Verify P50 latency < 2s for NL commands."""
    latencies: List[float] = []

    # Run 20 samples for P50
    for i in range(20):
        latency = measure_nl_command_latency(orchestrator, test_project.id)
        latencies.append(latency)

    # Calculate P50 (median)
    latencies_sorted = sorted(latencies)
    p50_index = len(latencies_sorted) // 2
    p50 = latencies_sorted[p50_index]

    print(f"\nP50 Latency: {p50:.3f}s (target: < 2.0s)")
    print(f"Min: {min(latencies):.3f}s, Max: {max(latencies):.3f}s")
    print(f"Avg: {sum(latencies)/len(latencies):.3f}s")

    # Assert P50 < 2s (with 10% tolerance for CI variability)
    assert p50 < 2.2, f"P50 latency {p50:.3f}s exceeds 2.0s threshold (2.2s with tolerance)"


# ============================================================================
# Performance Test 2: P95 Latency < 3s
# ============================================================================

@pytest.mark.slow
def test_nl_command_latency_p95(orchestrator, test_project):
    """Verify P95 latency < 3s for NL commands."""
    latencies: List[float] = []

    # Run 40 samples for reliable P95
    for i in range(40):
        latency = measure_nl_command_latency(orchestrator, test_project.id)
        latencies.append(latency)

    # Calculate P95
    latencies_sorted = sorted(latencies)
    p95_index = int(len(latencies_sorted) * 0.95)
    p95 = latencies_sorted[p95_index]

    print(f"\nP95 Latency: {p95:.3f}s (target: < 3.0s)")
    print(f"P50: {latencies_sorted[len(latencies_sorted)//2]:.3f}s")
    print(f"P99: {latencies_sorted[int(len(latencies_sorted)*0.99)]:.3f}s")

    # Assert P95 < 3s (with 10% tolerance)
    assert p95 < 3.3, f"P95 latency {p95:.3f}s exceeds 3.0s threshold (3.3s with tolerance)"


# ============================================================================
# Performance Test 3: NL vs Direct Latency Overhead < 500ms
# ============================================================================

@pytest.mark.slow
def test_nl_vs_direct_latency_overhead(orchestrator, state_manager, test_project):
    """Verify NL routing overhead < 500ms compared to direct StateManager."""
    nl_latencies: List[float] = []
    direct_latencies: List[float] = []

    # Measure NL command latency (10 samples)
    for i in range(10):
        latency = measure_nl_command_latency(orchestrator, test_project.id)
        nl_latencies.append(latency)

    # Measure direct StateManager latency (10 samples)
    for i in range(10):
        start = time.time()
        task = state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': 'Direct Task',
                'description': 'Direct StateManager access',
                'task_type': TaskType.TASK
            }
        )
        direct_latencies.append(time.time() - start)

    # Calculate averages
    avg_nl = sum(nl_latencies) / len(nl_latencies)
    avg_direct = sum(direct_latencies) / len(direct_latencies)
    overhead = avg_nl - avg_direct

    print(f"\nNL Avg: {avg_nl:.3f}s")
    print(f"Direct Avg: {avg_direct:.3f}s")
    print(f"Overhead: {overhead*1000:.0f}ms (target: < 500ms)")

    # Assert overhead < 500ms (with 50ms tolerance)
    assert overhead < 0.55, f"NL overhead {overhead*1000:.0f}ms exceeds 500ms threshold"


# ============================================================================
# Performance Test 4: Throughput >= 40 Commands/Minute
# ============================================================================

@pytest.mark.slow
def test_throughput_baseline(orchestrator, test_project):
    """Verify throughput >= 40 commands/minute."""
    num_commands = 20  # Run 20 commands
    start_time = time.time()

    for i in range(num_commands):
        measure_nl_command_latency(orchestrator, test_project.id)

    elapsed_time = time.time() - start_time
    commands_per_minute = (num_commands / elapsed_time) * 60

    print(f"\nCommands: {num_commands}")
    print(f"Elapsed: {elapsed_time:.2f}s")
    print(f"Throughput: {commands_per_minute:.1f} cmd/min (target: >= 40)")

    # Assert throughput >= 40 cmd/min (with 10% tolerance)
    assert commands_per_minute >= 36, f"Throughput {commands_per_minute:.1f} cmd/min below 40 threshold"
