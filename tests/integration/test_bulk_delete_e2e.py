"""End-to-end tests for bulk delete operations."""

import pytest
from unittest.mock import patch, Mock
from src.nl.nl_command_processor import NLCommandProcessor
from src.core.state import StateManager
from src.core.models import TaskType


@pytest.fixture
def state_manager(tmp_path):
    """StateManager with test database."""
    StateManager.reset_instance()
    db_path = tmp_path / "test.db"
    sm = StateManager.get_instance(f"sqlite:///{db_path}", echo=False)
    yield sm
    StateManager.reset_instance()


@pytest.fixture
def mock_llm_interface():
    """Mock LLM interface for testing."""
    mock = Mock()
    mock.generate.return_value = '{"entity_type": "task", "confidence": 0.9}'
    mock.model = 'test-model'
    return mock


@pytest.fixture
def processor(mock_llm_interface, state_manager):
    """NLCommandProcessor instance."""
    return NLCommandProcessor(mock_llm_interface, state_manager)


@pytest.fixture
def test_project(state_manager):
    """Create test project."""
    return state_manager.create_project(
        name="Test Project",
        description="Test project for bulk delete e2e",
        working_dir="/tmp/test"
    )


@patch('builtins.input', return_value='yes')
@patch('builtins.print')  # Suppress output
def test_bulk_delete_all_tasks_e2e(mock_print, mock_input, processor, state_manager, test_project):
    """End-to-end: 'delete all tasks' command."""
    # Setup: Create 5 tasks
    for i in range(5):
        state_manager.create_task(
            test_project.id,
            {"title": f"Task {i}", "description": f"Description {i}"}
        )

    # Execute
    result = processor.process("delete all tasks", project_id=test_project.id)

    # Verify intent recognized
    assert result.intent_type.value == 'COMMAND'

    # Verify no remaining tasks
    remaining = state_manager.list_tasks(test_project.id, task_type=TaskType.TASK)
    assert len(remaining) == 0


@patch('builtins.input', return_value='yes')
@patch('builtins.print')
def test_bulk_delete_multi_entity_e2e(mock_print, mock_input, processor, state_manager, test_project):
    """End-to-end: 'delete all epics stories and tasks' command."""
    # Setup: Create epic → story → task
    epic_id = state_manager.create_epic(test_project.id, "Epic 1", "Desc")
    story_id = state_manager.create_story(test_project.id, epic_id, "Story 1", "Desc")
    task = state_manager.create_task(test_project.id, {"title": "Task 1", "description": "Desc", "story_id": story_id})
    task_id = task.id

    # Execute
    result = processor.process(
        "delete all epics stories and tasks",
        project_id=test_project.id
    )

    # Verify intent recognized
    assert result.intent_type.value == 'COMMAND'

    # Verify all deleted
    assert state_manager.get_task(epic_id) is None
    assert state_manager.get_task(story_id) is None
    assert state_manager.get_task(task_id) is None


@patch('builtins.input', return_value='no')
@patch('builtins.print')
def test_bulk_delete_cancelled_e2e(mock_print, mock_input, processor, state_manager, test_project):
    """End-to-end: User cancels bulk delete."""
    # Setup: Create 3 tasks
    for i in range(3):
        state_manager.create_task(test_project.id, {"title": f"Task {i}", "description": f"Desc {i}"})

    # Execute
    result = processor.process("delete all tasks", project_id=test_project.id)

    # Verify: Cancelled, tasks remain
    remaining = state_manager.list_tasks(test_project.id, task_type=TaskType.TASK)
    assert len(remaining) == 3


def test_bulk_delete_empty_project(processor, state_manager, test_project):
    """End-to-end: Bulk delete on empty project."""
    # No setup needed - project is empty

    # Execute (should not fail)
    result = processor.process("delete all tasks", project_id=test_project.id)

    # Verify intent recognized
    assert result.intent_type.value == 'COMMAND'


@patch('builtins.input', return_value='yes')
@patch('builtins.print')
def test_bulk_delete_cascade(mock_print, mock_input, state_manager, test_project):
    """Test epic deletion cascades to stories and tasks."""
    from src.nl.bulk_command_executor import BulkCommandExecutor
    from src.nl.types import EntityType

    # Setup: create epic → story → task
    epic_id = state_manager.create_epic(test_project.id, "Epic 1", "Desc")
    story_id = state_manager.create_story(test_project.id, epic_id, "Story 1", "Desc")
    task = state_manager.create_task(test_project.id, {"title": "Task 1", "description": "Desc", "story_id": story_id})
    task_id = task.id

    # Execute: delete all epics
    executor = BulkCommandExecutor(state_manager)
    result = executor.execute_bulk_delete(test_project.id, [EntityType.EPIC], require_confirmation=False)

    # Verify: epic, story, and task all deleted
    assert state_manager.get_task(epic_id) is None
    assert state_manager.get_task(story_id) is None
    assert state_manager.get_task(task_id) is None
    assert result['epic'] == 1
