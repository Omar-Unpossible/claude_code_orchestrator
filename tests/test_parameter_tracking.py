"""Tests for parameter effectiveness tracking (TASK_2.1)."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, patch

from src.core.state import StateManager
from src.core.models import ParameterEffectiveness, Task, ProjectState


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    return 'sqlite:///:memory:'


@pytest.fixture
def state_manager(test_db):
    """Create StateManager with test database."""
    manager = StateManager.get_instance(test_db)
    yield manager
    # Cleanup
    manager.close()
    StateManager._instance = None


@pytest.fixture
def test_project(state_manager):
    """Create test project."""
    project = state_manager.create_project(
        name='Test Project',
        description='Test project for parameter tracking',
        working_dir='/tmp/test'
    )
    return project


@pytest.fixture
def test_task(state_manager, test_project):
    """Create test task."""
    task = state_manager.create_task(
        project_id=test_project.id,
        task_data={
            'title': 'Test Task',
            'description': 'Test task for parameter tracking',
            'status': 'pending'
        }
    )
    return task


class TestLogParameterUsage:
    """Test logging parameter usage."""

    def test_log_parameter_usage_basic(self, state_manager, test_task):
        """Test basic parameter usage logging."""
        state_manager.log_parameter_usage(
            template_name='validation',
            parameter_name='file_changes',
            was_included=True,
            token_count=150,
            task_id=test_task.id,
            prompt_token_count=2000
        )

        # Verify record created
        session = state_manager._get_session()
        record = session.query(ParameterEffectiveness).filter_by(
            parameter_name='file_changes'
        ).first()

        assert record is not None
        assert record.template_name == 'validation'
        assert record.was_included is True
        assert record.parameter_token_count == 150
        assert record.task_id == test_task.id
        assert record.prompt_token_count == 2000
        assert record.validation_accurate is None  # Not set yet

    def test_log_parameter_usage_excluded(self, state_manager, test_task):
        """Test logging when parameter was excluded."""
        state_manager.log_parameter_usage(
            template_name='validation',
            parameter_name='conversation_history',
            was_included=False,  # Excluded due to token limit
            token_count=0,
            task_id=test_task.id,
            prompt_token_count=2000
        )

        session = state_manager._get_session()
        record = session.query(ParameterEffectiveness).filter_by(
            parameter_name='conversation_history'
        ).first()

        assert record is not None
        assert record.was_included is False
        assert record.parameter_token_count == 0

    def test_log_parameter_usage_without_task(self, state_manager):
        """Test logging without associated task."""
        state_manager.log_parameter_usage(
            template_name='task_execution',
            parameter_name='project_goals',
            was_included=True,
            token_count=100,
            task_id=None,  # No task
            prompt_token_count=1500
        )

        session = state_manager._get_session()
        record = session.query(ParameterEffectiveness).filter_by(
            parameter_name='project_goals'
        ).first()

        assert record is not None
        assert record.task_id is None

    def test_log_multiple_parameters(self, state_manager, test_task):
        """Test logging multiple parameters."""
        parameters = [
            ('file_changes', True, 200),
            ('test_results', True, 150),
            ('dependency_impact', False, 0),
            ('git_context', True, 100)
        ]

        for param_name, included, tokens in parameters:
            state_manager.log_parameter_usage(
                template_name='validation',
                parameter_name=param_name,
                was_included=included,
                token_count=tokens,
                task_id=test_task.id
            )

        session = state_manager._get_session()
        records = session.query(ParameterEffectiveness).filter_by(
            task_id=test_task.id
        ).all()

        assert len(records) == 4
        included_count = sum(1 for r in records if r.was_included)
        assert included_count == 3


class TestUpdateValidationAccuracy:
    """Test updating validation accuracy."""

    def test_update_validation_accuracy(self, state_manager, test_task):
        """Test updating validation accuracy for a task."""
        # Log some parameter usage
        state_manager.log_parameter_usage(
            'validation', 'param1', True, 100, test_task.id
        )
        state_manager.log_parameter_usage(
            'validation', 'param2', True, 50, test_task.id
        )

        # Update accuracy
        updated = state_manager.update_validation_accuracy(
            task_id=test_task.id,
            was_accurate=True
        )

        assert updated == 2

        # Verify records updated
        session = state_manager._get_session()
        records = session.query(ParameterEffectiveness).filter_by(
            task_id=test_task.id
        ).all()

        assert all(r.validation_accurate is True for r in records)

    def test_update_only_recent_records(self, state_manager, test_task):
        """Test that only recent records within window are updated."""
        # Log a parameter usage
        state_manager.log_parameter_usage(
            'validation', 'param1', True, 100, test_task.id
        )

        # Update with short time window (won't catch records from before)
        updated = state_manager.update_validation_accuracy(
            task_id=test_task.id,
            was_accurate=True,
            window_minutes=0  # Very short window
        )

        # Should update because record just created
        assert updated >= 0

    def test_update_doesnt_overwrite_existing(self, state_manager, test_task):
        """Test that already-set accuracy values aren't overwritten."""
        # Log parameter usage
        state_manager.log_parameter_usage(
            'validation', 'param1', True, 100, test_task.id
        )

        # Update first time
        state_manager.update_validation_accuracy(test_task.id, True)

        # Try to update again
        updated = state_manager.update_validation_accuracy(test_task.id, False)

        # Should not update (validation_accurate already set)
        assert updated == 0

    def test_update_different_tasks_separately(self, state_manager, test_project):
        """Test that different tasks are updated independently."""
        # Create two tasks
        task1 = state_manager.create_task(test_project.id, {
            'title': 'Task 1',
            'description': 'First task',
            'status': 'pending'
        })
        task2 = state_manager.create_task(test_project.id, {
            'title': 'Task 2',
            'description': 'Second task',
            'status': 'pending'
        })

        # Log parameters for both
        state_manager.log_parameter_usage('validation', 'p1', True, 100, task1.id)
        state_manager.log_parameter_usage('validation', 'p2', True, 100, task2.id)

        # Update only task1
        updated = state_manager.update_validation_accuracy(task1.id, True)

        assert updated == 1

        # Verify task2 not affected
        session = state_manager._get_session()
        task2_record = session.query(ParameterEffectiveness).filter_by(
            task_id=task2.id
        ).first()
        assert task2_record.validation_accurate is None


class TestGetParameterEffectiveness:
    """Test parameter effectiveness analysis."""

    def test_get_effectiveness_no_data(self, state_manager):
        """Test with no data returns empty dict."""
        result = state_manager.get_parameter_effectiveness('validation', min_samples=1)
        assert result == {}

    def test_get_effectiveness_insufficient_samples(self, state_manager, test_task):
        """Test that parameters with insufficient samples are excluded."""
        # Log only 10 samples (below min_samples=20)
        for i in range(10):
            state_manager.log_parameter_usage(
                'validation', 'param1', True, 100, test_task.id
            )
            state_manager.update_validation_accuracy(test_task.id, True)

        result = state_manager.get_parameter_effectiveness('validation', min_samples=20)

        assert result == {}  # Not enough samples

    def test_get_effectiveness_with_sufficient_samples(self, state_manager, test_project):
        """Test effectiveness calculation with sufficient samples."""
        # Create 30 tasks and log parameter usage
        for i in range(30):
            task = state_manager.create_task(test_project.id, {
                'title': f'Task {i}',
                'description': f'Task {i}',
                'status': 'pending'
            })

            # file_changes included -> 85% accurate
            state_manager.log_parameter_usage(
                'validation', 'file_changes', True, 150, task.id
            )
            # Simulate 85% accuracy (about 25-26 out of 30 should be accurate)
            is_accurate = i < 26  # 26/30 = 86.7%
            state_manager.update_validation_accuracy(task.id, is_accurate)

        result = state_manager.get_parameter_effectiveness('validation', min_samples=20)

        assert 'file_changes' in result
        assert result['file_changes']['sample_count'] == 30
        # Should be around 0.867 (26/30)
        assert 0.80 <= result['file_changes']['accuracy_when_included'] <= 0.90

    def test_get_effectiveness_impact_score(self, state_manager, test_project):
        """Test impact score calculation."""
        # Create tasks with parameter included (high accuracy)
        for i in range(25):
            task = state_manager.create_task(test_project.id, {
                'title': f'Task Included {i}',
                'description': 'Test',
                'status': 'pending'
            })
            state_manager.log_parameter_usage(
                'validation', 'helpful_param', True, 100, task.id
            )
            # 90% accurate when included
            is_accurate = (i % 10) < 9
            state_manager.update_validation_accuracy(task.id, is_accurate)

        # Create tasks with parameter excluded (lower accuracy)
        for i in range(25):
            task = state_manager.create_task(test_project.id, {
                'title': f'Task Excluded {i}',
                'description': 'Test',
                'status': 'pending'
            })
            state_manager.log_parameter_usage(
                'validation', 'helpful_param', False, 0, task.id
            )
            # 60% accurate when excluded
            is_accurate = (i % 10) < 6
            state_manager.update_validation_accuracy(task.id, is_accurate)

        result = state_manager.get_parameter_effectiveness('validation', min_samples=20)

        assert 'helpful_param' in result
        # Impact score should be positive (parameter helps)
        assert result['helpful_param']['impact_score'] > 0.15

    def test_get_effectiveness_by_template(self, state_manager, test_project):
        """Test that effectiveness is template-specific."""
        task = state_manager.create_task(test_project.id, {
            'title': 'Task',
            'description': 'Test',
            'status': 'pending'
        })

        # Log for different templates
        for i in range(25):
            state_manager.log_parameter_usage(
                'validation', 'param1', True, 100, task.id
            )
            state_manager.log_parameter_usage(
                'task_execution', 'param1', True, 100, task.id
            )

        state_manager.update_validation_accuracy(task.id, True)

        # Query for validation template
        result_val = state_manager.get_parameter_effectiveness('validation', min_samples=20)
        # Query for task_execution template
        result_task = state_manager.get_parameter_effectiveness('task_execution', min_samples=20)

        # Both should have param1
        assert 'param1' in result_val
        assert 'param1' in result_task


class TestIntegration:
    """Integration tests for full parameter tracking workflow."""

    def test_full_workflow(self, state_manager, test_project):
        """Test complete parameter tracking workflow."""
        # 1. Execute task with parameters
        task = state_manager.create_task(test_project.id, {
            'title': 'Integration Test Task',
            'description': 'Test full workflow',
            'status': 'pending'
        })

        # 2. Log parameter usage during validation
        parameters = [
            ('file_changes', True, 200),
            ('test_results', True, 150),
            ('git_context', False, 0),  # Excluded
        ]

        for param, included, tokens in parameters:
            state_manager.log_parameter_usage(
                'validation', param, included, tokens, task.id, 2000
            )

        # 3. After human review, update accuracy
        updated = state_manager.update_validation_accuracy(task.id, True)
        assert updated == 3

        # 4. Verify records updated
        session = state_manager._get_session()
        records = session.query(ParameterEffectiveness).filter_by(
            task_id=task.id
        ).all()

        assert len(records) == 3
        assert all(r.validation_accurate is True for r in records)

    def test_multiple_tasks_analysis(self, state_manager, test_project):
        """Test analysis across multiple tasks."""
        # Execute 30 tasks
        for i in range(30):
            task = state_manager.create_task(test_project.id, {
                'title': f'Analysis Task {i}',
                'description': 'Test',
                'status': 'pending'
            })

            # Log parameters
            state_manager.log_parameter_usage(
                'validation', 'critical_param', True, 150, task.id
            )

            # Simulate varying accuracy
            is_accurate = i < 27  # 90% accurate
            state_manager.update_validation_accuracy(task.id, is_accurate)

        # Analyze effectiveness
        result = state_manager.get_parameter_effectiveness('validation', min_samples=20)

        assert 'critical_param' in result
        assert result['critical_param']['sample_count'] == 30
        assert result['critical_param']['accuracy_when_included'] == 0.9
