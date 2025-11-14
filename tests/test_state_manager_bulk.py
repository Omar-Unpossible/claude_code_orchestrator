"""Tests for StateManager bulk delete methods."""

import pytest
from src.core.state import StateManager
from src.core.models import ProjectState, Task, TaskType, TaskStatus


@pytest.fixture
def state_manager(tmp_path):
    """StateManager with test database."""
    StateManager.reset_instance()
    db_path = tmp_path / "test.db"
    sm = StateManager.get_instance(f"sqlite:///{db_path}", echo=False)
    yield sm
    StateManager.reset_instance()


@pytest.fixture
def test_project(state_manager):
    """Create test project."""
    project = state_manager.create_project(
        name="Test Project",
        description="Test project for bulk operations",
        working_dir="/tmp/test"
    )
    return project


def test_delete_all_tasks(state_manager, test_project):
    """Test deleting all tasks in project."""
    # Create 5 regular tasks
    task_ids = []
    for i in range(5):
        task = state_manager.create_task(
            project_id=test_project.id,
            task_data={"title": f"Task {i}", "description": f"Description {i}"}
        )
        task_ids.append(task.id)

    # Delete all
    count = state_manager.delete_all_tasks(test_project.id)

    # Verify
    assert count == 5
    remaining = state_manager.list_tasks(test_project.id, task_type=TaskType.TASK)
    assert len(remaining) == 0


def test_delete_all_stories_cascade(state_manager, test_project):
    """Test deleting stories cascades to child tasks."""
    # Create epic → story → task
    epic_id = state_manager.create_epic(test_project.id, "Epic 1", "Epic description")

    story_id = state_manager.create_story(test_project.id, epic_id, "Story 1", "Story description")

    task = state_manager.create_task(
        test_project.id,
        {"title": "Task 1", "description": "Task description", "story_id": story_id}
    )
    task_id = task.id

    # Delete all stories
    count = state_manager.delete_all_stories(test_project.id)

    # Verify: story and task deleted, epic remains
    assert count == 1
    assert state_manager.get_task(story_id) is None
    assert state_manager.get_task(task_id) is None
    assert state_manager.get_task(epic_id) is not None


def test_delete_all_epics_cascade(state_manager, test_project):
    """Test deleting epics cascades to stories and tasks."""
    # Create epic → story → task
    epic_id = state_manager.create_epic(test_project.id, "Epic 1", "Epic description")

    story_id = state_manager.create_story(test_project.id, epic_id, "Story 1", "Story description")

    task = state_manager.create_task(
        test_project.id,
        {"title": "Task 1", "description": "Task description", "story_id": story_id}
    )
    task_id = task.id

    # Delete all epics
    count = state_manager.delete_all_epics(test_project.id)

    # Verify: epic, story, and task all deleted
    assert count == 1
    assert state_manager.get_task(epic_id) is None
    assert state_manager.get_task(story_id) is None
    assert state_manager.get_task(task_id) is None


def test_delete_all_subtasks(state_manager, test_project):
    """Test deleting all subtasks."""
    # Create task with 3 subtasks
    parent = state_manager.create_task(
        test_project.id,
        {"title": "Parent Task", "description": "Parent"}
    )
    parent_id = parent.id

    subtask_ids = []
    for i in range(3):
        subtask = state_manager.create_task(
            test_project.id,
            {"title": f"Subtask {i}", "description": f"Subtask {i}", "parent_task_id": parent_id}
        )
        subtask_ids.append(subtask.id)

    # Delete all subtasks
    count = state_manager.delete_all_subtasks(test_project.id)

    # Verify: subtasks deleted, parent remains
    assert count == 3
    parent = state_manager.get_task(parent_id)
    assert parent is not None
    for subtask_id in subtask_ids:
        assert state_manager.get_task(subtask_id) is None


def test_delete_all_tasks_empty_project(state_manager, test_project):
    """Test bulk delete on empty project returns 0."""
    count = state_manager.delete_all_tasks(test_project.id)
    assert count == 0


def test_delete_all_tasks_only_deletes_tasks_type(state_manager, test_project):
    """Test delete_all_tasks doesn't delete epics or stories."""
    # Create epic, story, task
    epic_id = state_manager.create_epic(test_project.id, "Epic 1", "Desc")
    story_id = state_manager.create_story(test_project.id, epic_id, "Story 1", "Desc")
    task = state_manager.create_task(test_project.id, {"title": "Task 1", "description": "Desc"})
    task_id = task.id

    # Delete all tasks
    count = state_manager.delete_all_tasks(test_project.id)

    # Verify: only regular task deleted
    assert count == 1
    assert state_manager.get_task(task_id) is None
    assert state_manager.get_task(epic_id) is not None
    assert state_manager.get_task(story_id) is not None
