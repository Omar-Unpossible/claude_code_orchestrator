"""Tests for StateManager task update and delete operations."""

import pytest
from src.core.state import StateManager
from core.models import TaskStatus, TaskType


class TestTaskUpdate:
    """Test StateManager.update_task() method."""

    @pytest.fixture
    def state_with_task(self, state_manager):
        """Create state manager with a test task."""
        # Create project
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        # Create task
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Original Title',
                'description': 'Original Description',
                'priority': 5,
                'task_type': TaskType.TASK
            }
        )

        return state_manager, task.id

    def test_update_task_title(self, state_with_task):
        """Test updating task title."""
        state, task_id = state_with_task

        updated = state.update_task(task_id, {'title': 'New Title'})

        assert updated.title == 'New Title'
        assert updated.description == 'Original Description'  # Unchanged

    def test_update_task_priority(self, state_with_task):
        """Test updating task priority."""
        state, task_id = state_with_task

        updated = state.update_task(task_id, {'priority': 1})

        assert updated.priority == 1

    def test_update_task_status(self, state_with_task):
        """Test updating task status."""
        state, task_id = state_with_task

        updated = state.update_task(task_id, {'status': TaskStatus.RUNNING})

        assert updated.status == TaskStatus.RUNNING

    def test_update_multiple_fields(self, state_with_task):
        """Test updating multiple task fields."""
        state, task_id = state_with_task

        updates = {
            'title': 'Updated Title',
            'priority': 3,
            'status': TaskStatus.COMPLETED
        }
        updated = state.update_task(task_id, updates)

        assert updated.title == 'Updated Title'
        assert updated.priority == 3
        assert updated.status == TaskStatus.COMPLETED

    def test_update_nonexistent_task(self, state_manager):
        """Test that updating nonexistent task raises exception."""
        from src.core.exceptions import TransactionException

        with pytest.raises(TransactionException) as exc_info:
            state_manager.update_task(999, {'title': 'New'})

        assert 'not found' in str(exc_info.value).lower()

    def test_update_ignores_invalid_fields(self, state_with_task):
        """Test that invalid fields are ignored."""
        state, task_id = state_with_task

        # Should not raise exception
        updated = state.update_task(task_id, {
            'title': 'Valid',
            'invalid_field': 'Should be ignored'
        })

        assert updated.title == 'Valid'
        assert not hasattr(updated, 'invalid_field')


class TestTaskDelete:
    """Test StateManager.delete_task() method."""

    @pytest.fixture
    def state_with_task(self, state_manager):
        """Create state manager with a test task."""
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test Task',
                'description': 'Test Description',
                'task_type': TaskType.TASK
            }
        )
        return state_manager, task.id

    def test_soft_delete_task(self, state_with_task):
        """Test soft deleting a task."""
        state, task_id = state_with_task

        state.delete_task(task_id, soft=True)

        # Task still exists in database but marked as deleted
        # Note: get_task() filters out soft-deleted tasks, so we query directly
        from core.models import Task
        session = state._get_session()
        task = session.query(Task).filter(Task.id == task_id).first()

        assert task is not None
        assert task.is_deleted is True

    def test_hard_delete_task(self, state_with_task):
        """Test hard deleting a task."""
        state, task_id = state_with_task

        state.delete_task(task_id, soft=False)

        # Task should not exist
        task = state.get_task(task_id)
        assert task is None

    def test_delete_nonexistent_task(self, state_manager):
        """Test that deleting nonexistent task raises exception."""
        from src.core.exceptions import TransactionException

        with pytest.raises(TransactionException) as exc_info:
            state_manager.delete_task(999)

        assert 'not found' in str(exc_info.value).lower()

    def test_soft_deleted_not_in_list(self, state_with_task):
        """Test that soft deleted tasks don't appear in list_tasks()."""
        state, task_id = state_with_task

        # Before delete
        tasks_before = state.list_tasks()
        assert any(t.id == task_id for t in tasks_before)

        # Soft delete
        state.delete_task(task_id, soft=True)

        # After delete - should not appear
        # Note: list_tasks() filters by is_deleted=False
        tasks_after = state.list_tasks()
        assert not any(t.id == task_id for t in tasks_after)
