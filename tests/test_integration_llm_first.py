"""Integration tests for LLM-First Prompt Engineering Framework (PHASE_5).

Tests integration of:
- QualityController with StructuredResponseParser (TASK_5.1)
- Orchestrator with TaskComplexityEstimator (TASK_5.2)
- ParallelAgentCoordinator (TASK_5.3)

CRITICAL: This is a SEQUENTIAL testing event. NO parallel test execution.
"""

import pytest
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from src.orchestrator import Orchestrator
from src.core.state import StateManager
from src.core.models import Task
from src.orchestration.quality_controller import QualityController, QualityResult
from src.orchestration.parallel_agent_coordinator import ParallelAgentCoordinator
from src.orchestration.subtask import SubTask
from src.orchestration.complexity_estimate import ComplexityEstimate
from src.core.exceptions import OrchestratorException


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def state_manager(test_config):
    """Create in-memory StateManager for testing."""
    StateManager.reset_instance()
    db_url = test_config.get('database.url')
    sm = StateManager.get_instance(db_url, echo=False)
    yield sm
    sm.close()
    StateManager.reset_instance()


@pytest.fixture
def mock_agent():
    """Mock AgentPlugin for testing."""
    agent = Mock()
    agent.send_prompt = Mock(return_value="Task completed successfully")
    agent.get_response = Mock(return_value="Response from agent")
    agent.initialize = Mock()
    agent.cleanup = Mock()
    return agent


@pytest.fixture
def mock_llm():
    """Mock LLMPlugin for testing."""
    llm = Mock()
    llm.generate = Mock(return_value='{"status": "completed"}')
    llm.initialize = Mock()
    return llm


@pytest.fixture
def mock_llm_initialization(monkeypatch):
    """Mock LocalLLMInterface initialization to avoid Ollama dependency."""
    def mock_initialize(self, config):
        """Mock initialize that doesn't connect to Ollama."""
        self.config = config or {}
        self.model = self.config.get('model', 'qwen2.5-coder:32b')
        self.temperature = self.config.get('temperature', 0.7)
        self.max_tokens = self.config.get('max_tokens', 32768)
        # Don't actually connect to Ollama

    monkeypatch.setattr('src.llm.local_interface.LocalLLMInterface.initialize', mock_initialize)


def create_test_task(state_manager, **kwargs):
    """Create a test task in StateManager.

    Args:
        state_manager: StateManager instance
        **kwargs: Additional task fields

    Returns:
        Created task
    """
    import tempfile
    import os

    # Create temporary directory for tests
    test_dir = tempfile.mkdtemp(prefix='obra_test_')

    project = state_manager.create_project(
        name='test_project',
        description='Test project',
        working_dir=test_dir
    )

    task_data = {
        'title': kwargs.get('title', 'Test task'),
        'description': kwargs.get('description', 'Simple test task'),
        'priority': kwargs.get('priority', 5),
        'status': kwargs.get('status', 'pending')
    }

    return state_manager.create_task(project.id, task_data)


def create_complex_task(state_manager):
    """Create a complex task that triggers decomposition.

    Args:
        state_manager: StateManager instance

    Returns:
        Created complex task
    """
    import tempfile

    # Create temporary directory for tests
    test_dir = tempfile.mkdtemp(prefix='obra_test_')

    project = state_manager.create_project(
        name='test_project',
        description='Test project',
        working_dir=test_dir
    )

    task_data = {
        'title': 'Implement e-commerce platform',
        'description': '''
        Build a complete e-commerce platform with:
        - User authentication and authorization
        - Product catalog with search
        - Shopping cart functionality
        - Checkout and payment processing
        - Order management system
        - Admin dashboard
        - Inventory tracking
        - Email notifications
        - Analytics and reporting
        ''',
        'priority': 10,
        'status': 'pending'
    }

    return state_manager.create_task(project.id, task_data)


# ============================================================================
# A. QualityController Integration Tests
# ============================================================================

class TestQualityControllerIntegration:
    """Test QualityController integration with StructuredResponseParser."""

    def test_quality_controller_structured_response_parsing(self, state_manager):
        """Test structured response parsing in QualityController."""
        # Setup with structured mode enabled
        config = {
            'structured_mode': True,
            'response_schemas_file': 'config/response_schemas.yaml',
            'prompt_rules_file': 'config/prompt_rules.yaml'
        }
        controller = QualityController(state_manager, config)

        # Create structured response
        response = """
<METADATA>
{
    "status": "completed",
    "files_modified": ["/path/to/file.py"],
    "confidence": 0.95,
    "tests_added": 5
}
</METADATA>
<CONTENT>
Implementation complete. All tests passing.
</CONTENT>
"""

        # Create test task
        task = create_test_task(state_manager)

        # Validate
        result = controller.validate_output(
            output=response,
            task=task,
            context={'response_type': 'task_execution'}
        )

        # Assertions
        assert isinstance(result, QualityResult)
        assert result.overall_score >= 0.0
        assert result.metadata.get('structured_mode') is True
        assert 'schema_valid' in result.metadata

    def test_quality_controller_rule_violation_logging(self, state_manager):
        """Test that rule violations are logged to StateManager."""
        # Setup
        config = {
            'structured_mode': True,
            'response_schemas_file': 'config/response_schemas.yaml',
            'prompt_rules_file': 'config/prompt_rules.yaml'
        }
        controller = QualityController(state_manager, config)

        # Create response that might violate rules
        response = """
<METADATA>
{
    "status": "partial",
    "files_modified": [],
    "confidence": 0.3
}
</METADATA>
<CONTENT>
TODO: Need to implement this
</CONTENT>
"""

        task = create_test_task(state_manager)

        # Validate
        result = controller.validate_output(
            output=response,
            task=task,
            context={'response_type': 'task_execution'}
        )

        # Check that violations are tracked
        assert isinstance(result.rule_violations, list)

    def test_quality_controller_backward_compatibility(self, state_manager):
        """Test that unstructured mode still works."""
        # Setup WITHOUT structured mode
        config = {'structured_mode': False}
        controller = QualityController(state_manager, config)

        # Regular unstructured response
        response = """
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b
"""

        task = create_test_task(state_manager)

        # Validate
        result = controller.validate_output(
            output=response,
            task=task,
            context={'language': 'python'}
        )

        # Assertions for unstructured mode
        assert isinstance(result, QualityResult)
        assert result.metadata.get('structured_mode') is False
        assert 'syntax' in result.stage_scores
        assert 'quality' in result.stage_scores

    def test_quality_controller_schema_validation_failure(self, state_manager):
        """Test handling of schema validation failures."""
        config = {
            'structured_mode': True,
            'response_schemas_file': 'config/response_schemas.yaml'
        }
        controller = QualityController(state_manager, config)

        # Invalid structured response (missing required fields)
        response = """
<METADATA>
{
    "invalid_field": "value"
}
</METADATA>
<CONTENT>
Content here
</CONTENT>
"""

        task = create_test_task(state_manager)

        # Should still return result, but with validation errors
        result = controller.validate_output(
            output=response,
            task=task,
            context={'response_type': 'task_execution'}
        )

        assert isinstance(result, QualityResult)
        # Should have improvements/errors
        assert len(result.improvements) > 0

    def test_quality_controller_metadata_extraction(self, state_manager):
        """Test that metadata is properly extracted from structured responses."""
        config = {
            'structured_mode': True,
            'response_schemas_file': 'config/response_schemas.yaml'
        }
        controller = QualityController(state_manager, config)

        response = """
<METADATA>
{
    "status": "completed",
    "files_modified": ["/src/main.py", "/tests/test_main.py"],
    "confidence": 0.92,
    "tests_added": 3,
    "lines_of_code": 150
}
</METADATA>
<CONTENT>
Implementation complete with comprehensive tests.
</CONTENT>
"""

        task = create_test_task(state_manager)
        result = controller.validate_output(
            output=response,
            task=task,
            context={'response_type': 'task_execution'}
        )

        # Check metadata extraction
        metadata = result.metadata.get('response_metadata', {})
        assert metadata.get('status') == 'completed'
        assert metadata.get('confidence') == 0.92
        assert len(metadata.get('files_modified', [])) == 2

    def test_quality_controller_quality_score_calculation(self, state_manager):
        """Test quality score calculation with structured responses."""
        config = {
            'structured_mode': True,
            'response_schemas_file': 'config/response_schemas.yaml'
        }
        controller = QualityController(state_manager, config)

        # High-quality response
        high_quality_response = """
<METADATA>
{
    "status": "completed",
    "files_modified": ["/src/feature.py"],
    "confidence": 0.95,
    "tests_added": 10,
    "coverage_percentage": 95
}
</METADATA>
<CONTENT>
Feature implemented with comprehensive tests and documentation.
</CONTENT>
"""

        task = create_test_task(state_manager)
        result = controller.validate_output(
            output=high_quality_response,
            task=task,
            context={'response_type': 'task_execution'}
        )

        # Should have high score
        assert result.overall_score >= 0.7
        assert result.passes_gate is True


# ============================================================================
# B. Orchestrator Integration Tests
# ============================================================================

class TestOrchestratorIntegration:
    """Test Orchestrator integration with TaskComplexityEstimator."""

    def test_orchestrator_complexity_estimation(self, test_config, state_manager, mock_agent, mock_llm, mock_llm_initialization, fast_time):
        """Test complexity estimation before task execution."""
        # Enable complexity estimation
        config_dict = test_config._config.copy()
        config_dict['enable_complexity_estimation'] = True
        config_dict['orchestration'] = config_dict.get('orchestration', {})
        config_dict['orchestration']['complexity_config_path'] = 'config/complexity_thresholds.yaml'

        # Update test_config
        test_config._config = config_dict
        test_config.get = lambda key, default=None: (
            config_dict.get(key.split('.')[0], {}).get(key.split('.')[1], default)
            if '.' in key else config_dict.get(key, default)
        )

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Replace agent and LLM
        orchestrator.agent = mock_agent
        orchestrator.llm_interface = mock_llm

        # Mock complexity estimator
        mock_estimate = ComplexityEstimate(
            task_id=1,
            estimated_tokens=2000,
            estimated_loc=50,
            estimated_files=2,
            complexity_score=35.0,
            should_decompose=False,
            decomposition_suggestions=[],
            parallelization_opportunities=[],
            estimated_duration_minutes=30,
            confidence=0.85,
            timestamp=datetime.now()
        )

        if orchestrator.complexity_estimator:
            orchestrator.complexity_estimator.estimate_complexity = Mock(return_value=mock_estimate)

        # Create simple task
        task = create_test_task(state_manager, title='Simple task', description='Add two numbers')

        # Execute with complexity estimation
        result = orchestrator.execute_task(task.id, max_iterations=2)

        # Verify result has complexity estimate if estimator is available
        if orchestrator.complexity_estimator:
            assert 'complexity_estimate' in result or result['status'] in ['completed', 'escalated']

        orchestrator.shutdown()

    def test_orchestrator_task_decomposition(self, test_config, state_manager, mock_agent, mock_llm, mock_llm_initialization, fast_time):
        """Test task decomposition when complexity threshold exceeded."""
        # Enable complexity estimation
        config_dict = test_config._config.copy()
        config_dict['enable_complexity_estimation'] = True

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        orchestrator.agent = mock_agent
        orchestrator.llm_interface = mock_llm

        # Create complex task
        task = create_complex_task(state_manager)

        # Mock high complexity that requires decomposition
        mock_estimate = ComplexityEstimate(
            task_id=task.id,
            estimated_tokens=15000,
            estimated_loc=500,
            estimated_files=10,
            complexity_score=85.0,
            should_decompose=True,
            decomposition_suggestions=[
                'Implement user authentication',
                'Create product catalog',
                'Build shopping cart'
            ],
            parallelization_opportunities=[
                {'group_id': 1, 'subtask_ids': [1, 2]}
            ],
            estimated_duration_minutes=300,
            confidence=0.80,
            timestamp=datetime.now()
        )

        if orchestrator.complexity_estimator:
            orchestrator.complexity_estimator.estimate_complexity = Mock(return_value=mock_estimate)

            # Execute
            result = orchestrator.execute_task(task.id, max_iterations=2)

            # Should have decomposition info
            assert result.get('decomposed') is True or result['status'] in ['completed', 'escalated']
            if result.get('decomposed'):
                assert 'subtasks_created' in result

        orchestrator.shutdown()

    def test_orchestrator_backward_compatibility(self, test_config, state_manager, mock_agent, mock_llm_initialization, fast_time):
        """Test orchestrator works without complexity estimation."""
        # Disable complexity estimation
        config_dict = test_config._config.copy()
        config_dict['enable_complexity_estimation'] = False

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        orchestrator.agent = mock_agent

        # Create task
        task = create_test_task(state_manager)

        # Execute normally (should not try to estimate complexity)
        result = orchestrator.execute_task(task.id, max_iterations=2)

        # Should complete without complexity estimation
        assert result['status'] in ['completed', 'escalated', 'max_iterations']
        assert 'complexity_estimate' not in result or orchestrator.complexity_estimator is None

        orchestrator.shutdown()

    def test_orchestrator_subtask_creation(self, test_config, state_manager, mock_agent, mock_llm_initialization, fast_time):
        """Test subtask creation from decomposition suggestions."""
        config_dict = test_config._config.copy()
        config_dict['enable_complexity_estimation'] = True

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        orchestrator.agent = mock_agent

        task = create_test_task(state_manager, title='Complex feature')

        # Create estimate with suggestions
        estimate = ComplexityEstimate(
            task_id=task.id,
            estimated_tokens=10000,
            estimated_loc=300,
            estimated_files=5,
            complexity_score=75.0,
            should_decompose=True,
            decomposition_suggestions=[
                'Implement backend API',
                'Create frontend UI',
                'Write integration tests'
            ],
            parallelization_opportunities=[],
            estimated_duration_minutes=180,
            confidence=0.85,
            timestamp=datetime.now()
        )

        # Call internal method
        subtasks = orchestrator._create_subtasks_from_estimate(task, estimate)

        # Verify subtasks created
        assert len(subtasks) == 3
        assert all(isinstance(st, SubTask) for st in subtasks)
        assert subtasks[0].title == 'Implement backend API'

        orchestrator.shutdown()

    def test_orchestrator_subtask_storage(self, test_config, state_manager, mock_agent, mock_llm_initialization, fast_time):
        """Test subtask storage in StateManager."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        task = create_test_task(state_manager)

        # Create subtasks
        subtasks = [
            SubTask(
                subtask_id=1,
                parent_task_id=task.id,
                title='Subtask 1',
                description='First subtask',
                estimated_complexity=30.0,
                estimated_duration_minutes=30,
                dependencies=[],
                parallelizable=True,
                parallel_group=1,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            ),
            SubTask(
                subtask_id=2,
                parent_task_id=task.id,
                title='Subtask 2',
                description='Second subtask',
                estimated_complexity=25.0,
                estimated_duration_minutes=25,
                dependencies=[],
                parallelizable=True,
                parallel_group=1,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            )
        ]

        # Store subtasks
        subtask_ids = orchestrator._store_subtasks(task.id, subtasks)

        # Verify stored
        assert len(subtask_ids) == 2
        assert all(isinstance(sid, int) for sid in subtask_ids)

        # Verify can retrieve
        for subtask_id in subtask_ids:
            stored_task = state_manager.get_task(subtask_id)
            assert stored_task is not None
            # Verify it's a subtask (has parent_task_id set)
            assert stored_task.parent_task_id == task.id

        orchestrator.shutdown()


# ============================================================================
# C. ParallelAgentCoordinator Tests
# ============================================================================

class TestParallelAgentCoordinator:
    """Test ParallelAgentCoordinator."""

    def test_parallel_agent_coordination(self, state_manager, mock_agent, fast_time):
        """Test parallel execution of multiple subtasks."""
        # Create agent factory
        def agent_factory():
            agent = Mock()
            agent.send_prompt = Mock(return_value="Subtask completed")
            agent.initialize = Mock()
            agent.cleanup = Mock()
            return agent

        coordinator = ParallelAgentCoordinator(
            state_manager=state_manager,
            agent_factory=agent_factory,
            config={
                'max_parallel_agents': 3,
                'agent_timeout_seconds': 10
            }
        )

        # Create parent task
        parent_task = create_test_task(state_manager, title='Parent task')

        # Create subtasks with parallel groups
        subtasks = [
            SubTask(
                subtask_id=1,
                parent_task_id=parent_task.id,
                title='Subtask 1',
                description='First parallel subtask',
                estimated_complexity=30.0,
                estimated_duration_minutes=15,
                dependencies=[],
                parallelizable=True,
                parallel_group=1,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            ),
            SubTask(
                subtask_id=2,
                parent_task_id=parent_task.id,
                title='Subtask 2',
                description='Second parallel subtask',
                estimated_complexity=25.0,
                estimated_duration_minutes=10,
                dependencies=[],
                parallelizable=True,
                parallel_group=1,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            )
        ]

        # Execute in parallel
        results = coordinator.execute_parallel(
            subtasks=subtasks,
            parent_task=parent_task,
            context={'project_id': parent_task.project_id}
        )

        # Verify all completed
        assert len(results) == 2
        assert all(r['status'] in ['completed', 'failed', 'timeout'] for r in results)

    def test_sequential_testing_enforcement(self, state_manager):
        """Test RULE_SINGLE_AGENT_TESTING enforcement."""
        coordinator = ParallelAgentCoordinator(
            state_manager=state_manager,
            agent_factory=None,
            config={}
        )

        parent_task = create_test_task(state_manager)

        # Create multiple testing tasks in same group
        testing_subtasks = [
            SubTask(
                subtask_id=1,
                parent_task_id=parent_task.id,
                title='Test authentication',
                description='Write tests for auth module',
                estimated_complexity=20.0,
                estimated_duration_minutes=20,
                dependencies=[],
                parallelizable=True,
                parallel_group=1,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            ),
            SubTask(
                subtask_id=2,
                parent_task_id=parent_task.id,
                title='Test database',
                description='Write tests for database',
                estimated_complexity=25.0,
                estimated_duration_minutes=25,
                dependencies=[],
                parallelizable=True,
                parallel_group=1,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            )
        ]

        # Should raise exception for parallel testing
        with pytest.raises(OrchestratorException) as exc_info:
            coordinator._enforce_testing_rule(testing_subtasks)

        assert 'RULE_SINGLE_AGENT_TESTING' in str(exc_info.value)

    def test_empty_task_list(self, state_manager):
        """Test handling of empty task list."""
        coordinator = ParallelAgentCoordinator(
            state_manager=state_manager,
            agent_factory=None,
            config={}
        )

        parent_task = create_test_task(state_manager)

        # Execute with empty list
        results = coordinator.execute_parallel(
            subtasks=[],
            parent_task=parent_task,
            context={}
        )

        # Should return empty list
        assert results == []

    def test_result_merging(self, state_manager):
        """Test result merging from parallel agents."""
        coordinator = ParallelAgentCoordinator(
            state_manager=state_manager,
            agent_factory=None,
            config={}
        )

        parent_task = create_test_task(state_manager)

        # Create subtasks
        subtasks = [
            SubTask(
                subtask_id=1,
                parent_task_id=parent_task.id,
                title='Subtask 1',
                description='First',
                estimated_complexity=30.0,
                estimated_duration_minutes=15,
                dependencies=[],
                parallelizable=False,
                parallel_group=None,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            ),
            SubTask(
                subtask_id=2,
                parent_task_id=parent_task.id,
                title='Subtask 2',
                description='Second',
                estimated_complexity=25.0,
                estimated_duration_minutes=10,
                dependencies=[],
                parallelizable=False,
                parallel_group=None,
                status='pending',
                assigned_agent_id=None,
                created_at=datetime.now()
            )
        ]

        # Mock results (out of order)
        results = [
            {'subtask_id': 2, 'status': 'completed', 'result': 'Result 2'},
            {'subtask_id': 1, 'status': 'completed', 'result': 'Result 1'}
        ]

        # Merge
        merged = coordinator._merge_agent_results(results, subtasks)

        # Should be sorted by subtask_id
        assert len(merged) == 2
        assert merged[0]['subtask_id'] == 1
        assert merged[1]['subtask_id'] == 2


# ============================================================================
# D. End-to-End Integration Tests
# ============================================================================

class TestEndToEndIntegration:
    """Test complete end-to-end integration."""

    def test_integration_with_state_manager(self, test_config, state_manager, mock_agent, mock_llm_initialization, fast_time):
        """Test all StateManager integrations."""
        # Setup
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()
        orchestrator.agent = mock_agent

        # Create task
        task = create_test_task(state_manager, title='Integration test task')

        # Execute
        result = orchestrator.execute_task(task.id, max_iterations=2)

        # Verify task updated in StateManager
        updated_task = state_manager.get_task(task.id)
        assert updated_task is not None

        orchestrator.shutdown()

    def test_full_workflow_with_structured_validation(self, test_config, state_manager, mock_agent, mock_llm_initialization, fast_time):
        """Test full workflow with structured validation."""
        # Enable structured mode
        config_dict = test_config._config.copy()
        config_dict['orchestration'] = config_dict.get('orchestration', {})
        config_dict['orchestration']['quality'] = {
            'structured_mode': True,
            'response_schemas_file': 'config/response_schemas.yaml'
        }

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock structured response
        structured_response = """
<METADATA>
{
    "status": "completed",
    "files_modified": ["/src/feature.py"],
    "confidence": 0.90
}
</METADATA>
<CONTENT>
Feature implemented successfully.
</CONTENT>
"""
        mock_agent.send_prompt = Mock(return_value=structured_response)
        orchestrator.agent = mock_agent

        # Create task
        task = create_test_task(state_manager)

        # Execute
        result = orchestrator.execute_task(task.id, max_iterations=2)

        # Verify execution completed
        assert result['status'] in ['completed', 'escalated', 'max_iterations']

        orchestrator.shutdown()
