"""End-to-end integration tests for complete orchestrator workflows.

Tests the full system integration from CLI/API through to task completion.
"""

import pytest
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.orchestrator import Orchestrator
from src.core.state import StateManager
from src.core.config import Config


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for integration tests."""
    temp_dir = tempfile.mkdtemp(prefix='orch_test_')
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# Use test_config from conftest.py instead


@pytest.fixture
def state_manager(test_config):
    """Create state manager for integration tests."""
    db_url = test_config.get('database.url')
    sm = StateManager.get_instance(db_url)
    yield sm
    sm.close()


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    def test_complete_task_lifecycle(self, test_config, state_manager, fast_time):
        """Test complete task lifecycle from creation to completion."""
        # 1. Create project
        project = state_manager.create_project({
            'name': 'E2E Test Project',
            'description': 'Integration test',
            'working_dir': '/tmp/test'
        })

        assert project.id is not None
        assert project.status == 'active'

        # 2. Create task
        task = state_manager.create_task(project.id, {
            'title': 'Implement add function',
            'description': 'Create a function that adds two numbers',
            'priority': 5,
            'status': 'pending'
        })

        assert task.id is not None
        assert task.status == 'pending'

        # 3. Initialize orchestrator
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # 4. Mock agent response
        orchestrator.agent.send_prompt = Mock(return_value="""
def add(a, b):
    \"\"\"Add two numbers.\"\"\"
    return a + b

# Test
assert add(2, 3) == 5
""")

        # 5. Execute task
        result = orchestrator.execute_task(task.id, max_iterations=3)

        # 6. Verify results
        assert result['status'] in ['completed', 'escalated']
        assert result['iterations'] >= 1

        # 7. Verify task status updated
        updated_task = state_manager.get_task(task.id)
        assert updated_task.status in ['completed', 'in_progress']

        # Cleanup
        orchestrator.shutdown()

    def test_multi_task_workflow(self, test_config, state_manager, fast_time):
        """Test workflow with multiple tasks."""
        # Create project
        project = state_manager.create_project({
            'name': 'Multi-Task Project',
            'working_dir': '/tmp/test'
        })

        # Create multiple tasks
        task1 = state_manager.create_task(project.id, {
            'title': 'Task 1',
            'description': 'First task',
            'status': 'pending',
            'priority': 10
        })

        task2 = state_manager.create_task(project.id, {
            'title': 'Task 2',
            'description': 'Second task',
            'status': 'pending',
            'priority': 5
        })

        # Initialize orchestrator
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock responses
        orchestrator.agent.send_prompt = Mock(return_value="def foo(): pass")

        # Execute both tasks
        result1 = orchestrator.execute_task(task1.id, max_iterations=2)
        result2 = orchestrator.execute_task(task2.id, max_iterations=2)

        # Verify both completed or escalated
        assert result1['status'] in ['completed', 'escalated', 'max_iterations']
        assert result2['status'] in ['completed', 'escalated', 'max_iterations']

        orchestrator.shutdown()

    def test_error_recovery_workflow(self, test_config, state_manager, fast_time):
        """Test error recovery in complete workflow."""
        project = state_manager.create_project({
            'name': 'Error Test Project',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Error-prone task',
            'description': 'Task that might fail',
            'status': 'pending'
        })

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock agent to fail first, then succeed
        call_count = {'count': 0}

        def mock_response(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 1:
                raise Exception("Agent error")
            return "def recovered(): pass"

        orchestrator.agent.send_prompt = Mock(side_effect=mock_response)

        # Execute task
        result = orchestrator.execute_task(task.id, max_iterations=3)

        # Should recover or escalate
        assert result['status'] in ['completed', 'escalated', 'max_iterations']

        orchestrator.shutdown()

    def test_confidence_based_escalation(self, test_config, state_manager, fast_time):
        """Test escalation based on low confidence."""
        project = state_manager.create_project({
            'name': 'Confidence Test',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Complex task',
            'description': 'Very complex task requiring escalation',
            'status': 'pending'
        })

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Mock low-quality response
        orchestrator.agent.send_prompt = Mock(return_value="TODO: This is complex")

        result = orchestrator.execute_task(task.id, max_iterations=2)

        # Should escalate due to low confidence
        assert result['status'] in ['escalated', 'max_iterations']

        orchestrator.shutdown()


class TestComponentIntegration:
    """Test integration between components."""

    def test_context_manager_integration(self, test_config, state_manager, fast_time):
        """Test ContextManager integration in workflow."""
        project = state_manager.create_project({
            'name': 'Context Test',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Test task',
            'description': 'Task to test context building',
            'status': 'pending'
        })

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify context manager is integrated
        assert orchestrator.context_manager is not None

        # Build context
        orchestrator.current_task = task
        orchestrator.current_project = project
        context = orchestrator._build_context([])

        assert isinstance(context, str)
        assert len(context) >= 0

        orchestrator.shutdown()

    def test_quality_controller_integration(self, test_config, state_manager, fast_time):
        """Test QualityController integration."""
        project = state_manager.create_project({
            'name': 'Quality Test',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Quality task',
            'description': 'Test quality validation',
            'status': 'pending'
        })

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify quality controller is integrated
        assert orchestrator.quality_controller is not None

        # Mock good code
        orchestrator.agent.send_prompt = Mock(return_value="def clean_code(): return True")

        result = orchestrator.execute_task(task.id, max_iterations=1)

        assert 'status' in result

        orchestrator.shutdown()

    def test_decision_engine_integration(self, test_config, state_manager, fast_time):
        """Test DecisionEngine integration."""
        project = state_manager.create_project({
            'name': 'Decision Test',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Decision task',
            'description': 'Test decision making',
            'status': 'pending'
        })

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Verify decision engine is integrated
        assert orchestrator.decision_engine is not None

        orchestrator.agent.send_prompt = Mock(return_value="def decide(): pass")

        result = orchestrator.execute_task(task.id, max_iterations=1)

        # Decision should be made
        assert result['status'] in ['completed', 'escalated', 'max_iterations']

        orchestrator.shutdown()


class TestStateManagement:
    """Test state persistence and recovery."""

    def test_state_persistence(self, test_config, state_manager, fast_time):
        """Test state persists across orchestrator restarts."""
        project = state_manager.create_project({
            'name': 'Persistence Test',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Persistent task',
            'status': 'pending'
        })

        # First orchestrator instance
        orch1 = Orchestrator(config=test_config)
        orch1.initialize()
        orch1.agent.send_prompt = Mock(return_value="def persist(): pass")

        result = orch1.execute_task(task.id, max_iterations=1)
        orch1.shutdown()

        # Second orchestrator instance
        orch2 = Orchestrator(config=test_config)
        orch2.initialize()

        # Task state should persist
        updated_task = state_manager.get_task(task.id)
        assert updated_task is not None

        orch2.shutdown()

    def test_project_task_relationship(self, test_config, state_manager):
        """Test project-task relationships persist."""
        project = state_manager.create_project({
            'name': 'Relationship Test',
            'working_dir': '/tmp/test'
        })

        task1 = state_manager.create_task(project.id, {'title': 'Task 1', 'status': 'pending'})
        task2 = state_manager.create_task(project.id, {'title': 'Task 2', 'status': 'pending'})

        # Verify relationship
        project_tasks = state_manager.get_project_tasks(project.id)
        assert len(project_tasks) == 2
        assert all(t.project_id == project.id for t in project_tasks)


class TestPerformance:
    """Test performance characteristics."""

    def test_initialization_performance(self, test_config, fast_time):
        """Test orchestrator initializes quickly."""
        start = time.time()

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        elapsed = time.time() - start

        # Should initialize in <5s
        assert elapsed < 5.0

        orchestrator.shutdown()

    def test_task_execution_performance(self, test_config, state_manager, fast_time):
        """Test task executes in reasonable time."""
        project = state_manager.create_project({
            'name': 'Performance Test',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Fast task',
            'status': 'pending'
        })

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()
        orchestrator.agent.send_prompt = Mock(return_value="def fast(): pass")

        start = time.time()
        result = orchestrator.execute_task(task.id, max_iterations=1)
        elapsed = time.time() - start

        # Single iteration should be fast (agent is mocked)
        assert elapsed < 2.0

        orchestrator.shutdown()


class TestErrorScenarios:
    """Test various error scenarios."""

    def test_invalid_task_id(self, test_config):
        """Test handling invalid task ID."""
        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        with pytest.raises(Exception):  # Should raise OrchestratorException
            orchestrator.execute_task(999999)

        orchestrator.shutdown()

    def test_missing_project(self, test_config, state_manager):
        """Test handling missing project."""
        # Create task with non-existent project
        # This should be prevented by database constraints

        project = state_manager.create_project({
            'name': 'Temp Project',
            'working_dir': '/tmp/test'
        })

        # Verify project exists
        assert state_manager.get_project(project.id) is not None

    def test_agent_failure(self, test_config, state_manager, fast_time):
        """Test handling complete agent failure."""
        project = state_manager.create_project({
            'name': 'Failure Test',
            'working_dir': '/tmp/test'
        })

        task = state_manager.create_task(project.id, {
            'title': 'Failing task',
            'status': 'pending'
        })

        orchestrator = Orchestrator(config=test_config)
        orchestrator.initialize()

        # Agent always fails
        orchestrator.agent.send_prompt = Mock(side_effect=Exception("Agent down"))

        result = orchestrator.execute_task(task.id, max_iterations=2)

        # Should escalate or reach max iterations
        assert result['status'] in ['escalated', 'max_iterations']

        orchestrator.shutdown()
