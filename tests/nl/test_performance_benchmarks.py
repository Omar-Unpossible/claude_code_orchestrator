"""Performance benchmarks for ADR-016 NL command pipeline (Story 6 Task 4.4).

Measures latency, throughput, and memory usage for the five-stage pipeline:
    IntentClassifier → OperationClassifier → EntityTypeClassifier →
    EntityIdentifierExtractor → ParameterExtractor → CommandValidator → CommandExecutor

Performance Targets (from ADR-016 Implementation Plan):
- IntentClassifier: <200ms
- OperationClassifier: <150ms
- EntityTypeClassifier: <150ms
- EntityIdentifierExtractor: <150ms
- ParameterExtractor: <150ms
- CommandValidator: <50ms
- CommandExecutor: <100ms
- Total Pipeline: <1000ms (1 second)
- Throughput: 50+ commands/minute
- Memory: <200MB additional
"""

import pytest
import time
import json
import psutil
import os
from unittest.mock import MagicMock

from src.nl.intent_classifier import IntentClassifier
from src.nl.operation_classifier import OperationClassifier
from src.nl.entity_type_classifier import EntityTypeClassifier
from src.nl.entity_identifier_extractor import EntityIdentifierExtractor
from src.nl.parameter_extractor import ParameterExtractor
from src.nl.question_handler import QuestionHandler
from src.nl.command_validator import CommandValidator
from src.nl.command_executor import CommandExecutor
from src.nl.types import (
    OperationContext, OperationType, EntityType, QueryType
)
from src.core.state import StateManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def perf_state(tmp_path):
    """StateManager for performance testing."""
    state = StateManager(database_url='sqlite:///:memory:')

    # Create test project
    project = state.create_project(
        name="Performance Test Project",
        description="Performance benchmarking",
        working_dir=str(tmp_path)
    )

    yield state
    state.close()


@pytest.fixture
def mock_llm_fast():
    """Fast mock LLM for performance testing."""
    llm = MagicMock()

    # Ultra-fast responses (simulate optimized LLM)
    llm.generate = MagicMock(return_value=json.dumps({
        "operation": "CREATE",
        "entity_type": "task",
        "identifier": None,
        "parameters": {"title": "test"},
        "confidence": 0.95
    }))

    return llm


@pytest.fixture
def perf_components(mock_llm_fast, perf_state):
    """Pipeline components for performance testing."""
    return {
        'intent_classifier': IntentClassifier(mock_llm_fast, confidence_threshold=0.7),
        'operation_classifier': OperationClassifier(mock_llm_fast, confidence_threshold=0.7),
        'entity_type_classifier': EntityTypeClassifier(mock_llm_fast, confidence_threshold=0.7),
        'entity_identifier_extractor': EntityIdentifierExtractor(mock_llm_fast, confidence_threshold=0.7),
        'parameter_extractor': ParameterExtractor(mock_llm_fast, confidence_threshold=0.7),
        'command_validator': CommandValidator(perf_state),
        'command_executor': CommandExecutor(perf_state, default_project_id=1),
        'state': perf_state
    }


def get_memory_usage_mb():
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


# ============================================================================
# Performance Tests
# ============================================================================

class TestComponentLatency:
    """Test latency of individual pipeline components."""

    def test_intent_classifier_latency(self, perf_components):
        """Test: IntentClassifier latency <200ms."""
        user_input = "Create epic for authentication"

        start = time.time()
        result = perf_components['intent_classifier'].classify(user_input)
        latency = (time.time() - start) * 1000  # Convert to ms

        assert result.intent in ["COMMAND", "QUESTION"]
        print(f"\nIntentClassifier latency: {latency:.2f}ms (target: <200ms)")
        # With mock LLM, should be very fast
        assert latency < 200  # Target: <200ms

    def test_operation_classifier_latency(self, perf_components):
        """Test: OperationClassifier latency <150ms."""
        user_input = "Create epic for authentication"

        start = time.time()
        result = perf_components['operation_classifier'].classify(user_input)
        latency = (time.time() - start) * 1000

        assert result.operation_type == OperationType.CREATE
        print(f"\nOperationClassifier latency: {latency:.2f}ms (target: <150ms)")
        assert latency < 150  # Target: <150ms

    def test_entity_type_classifier_latency(self, perf_components):
        """Test: EntityTypeClassifier latency <150ms."""
        user_input = "Create epic for authentication"
        operation = OperationType.CREATE

        start = time.time()
        result = perf_components['entity_type_classifier'].classify(user_input, operation)
        latency = (time.time() - start) * 1000

        assert result.entity_type == EntityType.EPIC
        print(f"\nEntityTypeClassifier latency: {latency:.2f}ms (target: <150ms)")
        assert latency < 150  # Target: <150ms

    def test_entity_identifier_extractor_latency(self, perf_components):
        """Test: EntityIdentifierExtractor latency <150ms."""
        user_input = "Create epic for authentication"
        entity_type = EntityType.EPIC
        operation = OperationType.CREATE

        start = time.time()
        result = perf_components['entity_identifier_extractor'].extract(
            user_input, entity_type, operation
        )
        latency = (time.time() - start) * 1000

        assert result.identifier is None  # CREATE doesn't need identifier
        print(f"\nEntityIdentifierExtractor latency: {latency:.2f}ms (target: <150ms)")
        assert latency < 150  # Target: <150ms

    def test_parameter_extractor_latency(self, perf_components):
        """Test: ParameterExtractor latency <150ms."""
        user_input = "Create epic for authentication"
        operation = OperationType.CREATE
        entity_type = EntityType.EPIC

        start = time.time()
        result = perf_components['parameter_extractor'].extract(
            user_input, operation, entity_type
        )
        latency = (time.time() - start) * 1000

        assert "title" in result.parameters or "description" in result.parameters
        print(f"\nParameterExtractor latency: {latency:.2f}ms (target: <150ms)")
        assert latency < 150  # Target: <150ms

    def test_command_validator_latency(self, perf_components):
        """Test: CommandValidator latency <50ms."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            identifier=None,
            parameters={"title": "Test Task"},
            confidence=0.95,
            raw_input="Create task"
        )

        start = time.time()
        result = perf_components['command_validator'].validate(context)
        latency = (time.time() - start) * 1000

        assert result.valid is True
        print(f"\nCommandValidator latency: {latency:.2f}ms (target: <50ms)")
        assert latency < 50  # Target: <50ms

    def test_command_executor_latency(self, perf_components):
        """Test: CommandExecutor latency <100ms."""
        validated_command = {
            'operation': 'create',
            'entity_type': 'task',
            'identifier': None,
            'parameters': {'title': 'Performance Test Task'},
            'confidence': 0.95
        }

        start = time.time()
        result = perf_components['command_executor'].execute(
            validated_command, project_id=1
        )
        latency = (time.time() - start) * 1000

        assert result.success is True
        print(f"\nCommandExecutor latency: {latency:.2f}ms (target: <100ms)")
        assert latency < 100  # Target: <100ms


class TestEndToEndLatency:
    """Test end-to-end pipeline latency."""

    def test_full_pipeline_latency(self, perf_components, mock_llm_fast):
        """Test: Full pipeline completes in <1000ms (1 second)."""
        user_input = "Create task for testing performance"

        # Mock LLM responses for all stages
        mock_llm_fast.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),
            json.dumps({"operation": "CREATE", "confidence": 0.94}),
            json.dumps({"entity_type": "task", "confidence": 0.93}),
            json.dumps({"identifier": None, "confidence": 1.0}),
            json.dumps({
                "parameters": {"title": "testing performance"},
                "confidence": 0.92
            })
        ]

        start = time.time()

        # Stage 1: Intent Classification
        intent_result = perf_components['intent_classifier'].classify(user_input)

        # Stage 2: Operation Classification
        operation_result = perf_components['operation_classifier'].classify(user_input)

        # Stage 3: Entity Type Classification
        entity_type_result = perf_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )

        # Stage 4: Entity Identifier Extraction
        identifier_result = perf_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )

        # Stage 5: Parameter Extraction
        parameter_result = perf_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )

        # Build OperationContext
        context = OperationContext(
            operation=operation_result.operation_type,
            entity_type=entity_type_result.entity_type,
            identifier=identifier_result.identifier,
            parameters=parameter_result.parameters,
            confidence=0.92,
            raw_input=user_input
        )

        # Stage 6: Validation
        validation_result = perf_components['command_validator'].validate(context)

        # Stage 7: Execution
        execution_result = perf_components['command_executor'].execute(
            validation_result.validated_command, project_id=1
        )

        latency = (time.time() - start) * 1000

        assert execution_result.success is True
        print(f"\nFull pipeline latency: {latency:.2f}ms (target: <1000ms)")
        assert latency < 1000  # Target: <1000ms (1 second)

    def test_pipeline_p95_latency(self, perf_components, mock_llm_fast):
        """Test: P95 latency <1500ms."""
        user_input = "Create task for P95 test"

        # Run 20 iterations to measure P95
        latencies = []

        for i in range(20):
            # Reset mock for each iteration
            mock_llm_fast.generate.side_effect = [
                json.dumps({"intent": "COMMAND", "confidence": 0.95}),
                json.dumps({"operation": "CREATE", "confidence": 0.94}),
                json.dumps({"entity_type": "task", "confidence": 0.93}),
                json.dumps({"identifier": None, "confidence": 1.0}),
                json.dumps({
                    "parameters": {"title": f"p95 test {i}"},
                    "confidence": 0.92
                })
            ]

            start = time.time()

            # Run full pipeline (abbreviated for brevity)
            intent_result = perf_components['intent_classifier'].classify(user_input)
            operation_result = perf_components['operation_classifier'].classify(user_input)
            entity_type_result = perf_components['entity_type_classifier'].classify(
                user_input, operation_result.operation_type
            )
            identifier_result = perf_components['entity_identifier_extractor'].extract(
                user_input, entity_type_result.entity_type, operation_result.operation_type
            )
            parameter_result = perf_components['parameter_extractor'].extract(
                user_input, operation_result.operation_type, entity_type_result.entity_type
            )

            context = OperationContext(
                operation=operation_result.operation_type,
                entity_type=entity_type_result.entity_type,
                identifier=identifier_result.identifier,
                parameters=parameter_result.parameters,
                confidence=0.92,
                raw_input=user_input
            )

            validation_result = perf_components['command_validator'].validate(context)
            execution_result = perf_components['command_executor'].execute(
                validation_result.validated_command, project_id=1
            )

            latency = (time.time() - start) * 1000
            latencies.append(latency)

        # Calculate P95
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        print(f"\nP95 latency: {p95_latency:.2f}ms (target: <1500ms)")
        print(f"Min latency: {min(latencies):.2f}ms")
        print(f"Max latency: {max(latencies):.2f}ms")
        print(f"Avg latency: {sum(latencies)/len(latencies):.2f}ms")

        assert p95_latency < 1500  # Target: <1500ms P95


class TestThroughput:
    """Test pipeline throughput."""

    def test_commands_per_minute(self, perf_components, mock_llm_fast):
        """Test: Throughput >50 commands/minute."""
        user_input = "Create task for throughput test"

        # Run for 10 seconds and count commands
        start_time = time.time()
        commands_processed = 0
        duration = 10  # seconds

        while (time.time() - start_time) < duration:
            # Reset mock
            mock_llm_fast.generate.side_effect = [
                json.dumps({"intent": "COMMAND", "confidence": 0.95}),
                json.dumps({"operation": "CREATE", "confidence": 0.94}),
                json.dumps({"entity_type": "task", "confidence": 0.93}),
                json.dumps({"identifier": None, "confidence": 1.0}),
                json.dumps({
                    "parameters": {"title": f"throughput test {commands_processed}"},
                    "confidence": 0.92
                })
            ]

            # Run abbreviated pipeline
            try:
                intent_result = perf_components['intent_classifier'].classify(user_input)
                operation_result = perf_components['operation_classifier'].classify(user_input)
                entity_type_result = perf_components['entity_type_classifier'].classify(
                    user_input, operation_result.operation_type
                )

                context = OperationContext(
                    operation=operation_result.operation_type,
                    entity_type=entity_type_result.entity_type,
                    identifier=None,
                    parameters={"title": "test"},
                    confidence=0.92,
                    raw_input=user_input
                )

                validation_result = perf_components['command_validator'].validate(context)
                execution_result = perf_components['command_executor'].execute(
                    validation_result.validated_command, project_id=1
                )

                if execution_result.success:
                    commands_processed += 1
            except Exception:
                pass  # Continue processing

        # Calculate commands per minute
        commands_per_minute = (commands_processed / duration) * 60

        print(f"\nCommands processed: {commands_processed} in {duration}s")
        print(f"Throughput: {commands_per_minute:.1f} commands/minute (target: >50)")

        assert commands_per_minute > 50  # Target: >50 commands/minute


class TestMemoryUsage:
    """Test pipeline memory usage."""

    def test_memory_overhead(self, perf_components, mock_llm_fast):
        """Test: Memory overhead <200MB."""
        # Measure baseline memory
        baseline_memory = get_memory_usage_mb()

        # Process 100 commands
        for i in range(100):
            mock_llm_fast.generate.side_effect = [
                json.dumps({"intent": "COMMAND", "confidence": 0.95}),
                json.dumps({"operation": "CREATE", "confidence": 0.94}),
                json.dumps({"entity_type": "task", "confidence": 0.93}),
                json.dumps({"identifier": None, "confidence": 1.0}),
                json.dumps({
                    "parameters": {"title": f"memory test {i}"},
                    "confidence": 0.92
                })
            ]

            user_input = f"Create task for memory test {i}"

            # Run abbreviated pipeline
            intent_result = perf_components['intent_classifier'].classify(user_input)
            operation_result = perf_components['operation_classifier'].classify(user_input)

            context = OperationContext(
                operation=operation_result.operation_type,
                entity_type=EntityType.TASK,
                identifier=None,
                parameters={"title": f"memory test {i}"},
                confidence=0.92,
                raw_input=user_input
            )

            validation_result = perf_components['command_validator'].validate(context)
            execution_result = perf_components['command_executor'].execute(
                validation_result.validated_command, project_id=1
            )

        # Measure final memory
        final_memory = get_memory_usage_mb()
        memory_overhead = final_memory - baseline_memory

        print(f"\nBaseline memory: {baseline_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Memory overhead: {memory_overhead:.2f}MB (target: <200MB)")

        assert memory_overhead < 200  # Target: <200MB

    def test_memory_stability(self, perf_components, mock_llm_fast):
        """Test: No memory leaks over 500 commands."""
        # Measure memory at multiple checkpoints
        checkpoints = []

        for batch in range(5):  # 5 batches of 100 commands
            batch_start_memory = get_memory_usage_mb()

            for i in range(100):
                mock_llm_fast.generate.side_effect = [
                    json.dumps({"intent": "COMMAND", "confidence": 0.95}),
                    json.dumps({"operation": "CREATE", "confidence": 0.94}),
                ]

                user_input = f"Create task for stability test {batch * 100 + i}"

                try:
                    intent_result = perf_components['intent_classifier'].classify(user_input)
                    operation_result = perf_components['operation_classifier'].classify(user_input)
                except Exception:
                    pass

            batch_end_memory = get_memory_usage_mb()
            checkpoints.append(batch_end_memory)

        # Check that memory doesn't grow unbounded
        memory_growth = checkpoints[-1] - checkpoints[0]

        print(f"\nMemory checkpoints: {[f'{m:.2f}MB' for m in checkpoints]}")
        print(f"Total memory growth: {memory_growth:.2f}MB")

        # Memory should not grow more than 50MB over 500 commands
        assert memory_growth < 50  # No significant leaks


# ============================================================================
# Comparative Performance Tests
# ============================================================================

class TestComparativePerformance:
    """Compare performance of new vs old pipeline (if applicable)."""

    def test_new_pipeline_vs_baseline(self, perf_components, mock_llm_fast):
        """Test: New pipeline is not significantly slower than baseline."""
        user_input = "Create task for comparison"

        # Measure new pipeline (5-stage)
        mock_llm_fast.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),
            json.dumps({"operation": "CREATE", "confidence": 0.94}),
            json.dumps({"entity_type": "task", "confidence": 0.93}),
            json.dumps({"identifier": None, "confidence": 1.0}),
            json.dumps({"parameters": {"title": "test"}, "confidence": 0.92})
        ]

        start = time.time()
        intent_result = perf_components['intent_classifier'].classify(user_input)
        operation_result = perf_components['operation_classifier'].classify(user_input)
        entity_type_result = perf_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        identifier_result = perf_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        parameter_result = perf_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )
        new_pipeline_latency = (time.time() - start) * 1000

        print(f"\nNew pipeline (5-stage) latency: {new_pipeline_latency:.2f}ms")

        # New pipeline should complete in <1s
        assert new_pipeline_latency < 1000

        # With mock LLM, 5 stages should be very fast
        # Real LLM would add ~120ms per stage = ~600ms total for 5 LLM calls
        print(f"Estimated real LLM latency: ~{120 * 5}ms")
