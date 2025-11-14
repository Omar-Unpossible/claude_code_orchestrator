"""Tests for BulkCommandExecutor."""

import pytest
from unittest.mock import Mock, patch
from src.nl.bulk_command_executor import BulkCommandExecutor, BulkOperationException
from src.nl.types import EntityType


@pytest.fixture
def mock_state_manager():
    """Mock StateManager."""
    mock = Mock()
    mock.delete_all_tasks.return_value = 10
    mock.delete_all_stories.return_value = 5
    mock.delete_all_epics.return_value = 2
    mock.delete_all_subtasks.return_value = 3
    mock.list_tasks.return_value = [Mock() for _ in range(10)]
    mock.list_epics.return_value = [Mock() for _ in range(2)]
    return mock


@pytest.fixture
def executor(mock_state_manager):
    """BulkCommandExecutor instance."""
    return BulkCommandExecutor(mock_state_manager)


def test_dependency_ordering(executor):
    """Test entities ordered by dependency (children first)."""
    entity_types = [EntityType.EPIC, EntityType.TASK, EntityType.STORY, EntityType.SUBTASK]
    ordered = executor._order_by_dependencies(entity_types)

    expected = [EntityType.SUBTASK, EntityType.TASK, EntityType.STORY, EntityType.EPIC]
    assert ordered == expected


def test_get_entity_counts(executor, mock_state_manager):
    """Test entity count retrieval."""
    counts = executor._get_entity_counts(1, [EntityType.TASK, EntityType.EPIC])

    assert counts['tasks'] == 10
    assert counts['epics'] == 2


@patch('builtins.input', return_value='yes')
def test_bulk_delete_with_confirmation(mock_input, executor, mock_state_manager):
    """Test bulk delete executes when user confirms."""
    result = executor.execute_bulk_delete(
        project_id=1,
        entity_types=[EntityType.TASK, EntityType.EPIC],
        require_confirmation=True
    )

    assert 'task' in result
    assert result['task'] == 10
    assert 'epic' in result
    assert result['epic'] == 2

    mock_state_manager.delete_all_tasks.assert_called_once_with(1)
    mock_state_manager.delete_all_epics.assert_called_once_with(1)


@patch('builtins.input', return_value='no')
def test_bulk_delete_cancelled(mock_input, executor, mock_state_manager):
    """Test bulk delete cancelled by user."""
    result = executor.execute_bulk_delete(
        project_id=1,
        entity_types=[EntityType.TASK],
        require_confirmation=True
    )

    assert result['cancelled'] is True
    mock_state_manager.delete_all_tasks.assert_not_called()


def test_bulk_delete_without_confirmation(executor, mock_state_manager):
    """Test bulk delete skips confirmation when disabled."""
    result = executor.execute_bulk_delete(
        project_id=1,
        entity_types=[EntityType.TASK],
        require_confirmation=False
    )

    assert result['task'] == 10
    mock_state_manager.delete_all_tasks.assert_called_once_with(1)


def test_bulk_delete_handles_exception(executor, mock_state_manager):
    """Test bulk delete raises exception with partial results."""
    mock_state_manager.delete_all_tasks.return_value = 5
    mock_state_manager.delete_all_stories.side_effect = Exception("DB error")

    with pytest.raises(BulkOperationException) as exc_info:
        executor.execute_bulk_delete(
            project_id=1,
            entity_types=[EntityType.TASK, EntityType.STORY],
            require_confirmation=False
        )

    assert exc_info.value.partial_results['task'] == 5
    assert 'story' not in exc_info.value.partial_results
