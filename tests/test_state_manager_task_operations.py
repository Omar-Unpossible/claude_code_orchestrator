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


class TestTaskTypeFiltering:
    """Test StateManager.list_tasks() filtering by task_type parameter.

    This fixes the bug where NLQueryHelper calls list_tasks(task_type=...)
    but the parameter was missing from the method signature.
    """

    @pytest.fixture
    def state_with_mixed_tasks(self, state_manager):
        """Create state manager with tasks of different types."""
        # Create project
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        # Create epic
        epic = state_manager.create_epic(
            project_id=project.id,
            title="Test Epic",
            description="Epic description"
        )

        # Create story under epic
        story = state_manager.create_story(
            project_id=project.id,
            epic_id=epic,
            title="Test Story",
            description="Story description"
        )

        # Create regular task
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test Task',
                'description': 'Task description',
                'task_type': TaskType.TASK
            }
        )

        # Create subtask under task
        subtask = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test Subtask',
                'description': 'Subtask description',
                'task_type': TaskType.SUBTASK,
                'parent_task_id': task.id
            }
        )

        return state_manager, {
            'project_id': project.id,
            'epic_id': epic,
            'story_id': story,
            'task_id': task.id,
            'subtask_id': subtask.id
        }

    def test_filter_by_epic(self, state_with_mixed_tasks):
        """Test filtering tasks by EPIC task_type."""
        state, ids = state_with_mixed_tasks

        epics = state.list_tasks(task_type=TaskType.EPIC)

        assert len(epics) >= 1
        assert all(t.task_type == TaskType.EPIC for t in epics)
        assert any(t.id == ids['epic_id'] for t in epics)

    def test_filter_by_story(self, state_with_mixed_tasks):
        """Test filtering tasks by STORY task_type."""
        state, ids = state_with_mixed_tasks

        stories = state.list_tasks(task_type=TaskType.STORY)

        assert len(stories) >= 1
        assert all(t.task_type == TaskType.STORY for t in stories)
        assert any(t.id == ids['story_id'] for t in stories)

    def test_filter_by_task(self, state_with_mixed_tasks):
        """Test filtering tasks by TASK task_type."""
        state, ids = state_with_mixed_tasks

        tasks = state.list_tasks(task_type=TaskType.TASK)

        assert len(tasks) >= 1
        assert all(t.task_type == TaskType.TASK for t in tasks)
        assert any(t.id == ids['task_id'] for t in tasks)

    def test_filter_by_subtask(self, state_with_mixed_tasks):
        """Test filtering tasks by SUBTASK task_type."""
        state, ids = state_with_mixed_tasks

        subtasks = state.list_tasks(task_type=TaskType.SUBTASK)

        assert len(subtasks) >= 1
        assert all(t.task_type == TaskType.SUBTASK for t in subtasks)
        assert any(t.id == ids['subtask_id'] for t in subtasks)

    def test_no_filter_returns_all_types(self, state_with_mixed_tasks):
        """Test that omitting task_type returns all task types."""
        state, ids = state_with_mixed_tasks

        all_tasks = state.list_tasks()

        # Should contain all task types
        task_types = {t.task_type for t in all_tasks}
        assert TaskType.EPIC in task_types
        assert TaskType.STORY in task_types
        assert TaskType.TASK in task_types
        assert TaskType.SUBTASK in task_types

        # Should contain all our created tasks
        task_ids = {t.id for t in all_tasks}
        assert ids['epic_id'] in task_ids
        assert ids['story_id'] in task_ids
        assert ids['task_id'] in task_ids
        assert ids['subtask_id'] in task_ids

    def test_filter_with_limit(self, state_with_mixed_tasks):
        """Test combining task_type filter with limit."""
        state, ids = state_with_mixed_tasks

        # Create multiple epics to test limit
        for i in range(3):
            state.create_epic(
                project_id=ids['project_id'],
                title=f"Extra Epic {i}",
                description=f"Extra epic {i}"
            )

        epics = state.list_tasks(task_type=TaskType.EPIC, limit=2)

        assert len(epics) == 2
        assert all(t.task_type == TaskType.EPIC for t in epics)

    def test_filter_with_status(self, state_with_mixed_tasks):
        """Test combining task_type filter with status filter."""
        state, ids = state_with_mixed_tasks

        # Update epic status to COMPLETED
        state.update_task(ids['epic_id'], {'status': TaskStatus.COMPLETED})

        # Filter by EPIC and COMPLETED
        completed_epics = state.list_tasks(
            task_type=TaskType.EPIC,
            status=TaskStatus.COMPLETED
        )

        assert len(completed_epics) >= 1
        assert all(t.task_type == TaskType.EPIC for t in completed_epics)
        assert all(t.status == TaskStatus.COMPLETED for t in completed_epics)
        assert any(t.id == ids['epic_id'] for t in completed_epics)
