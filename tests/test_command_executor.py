"""Unit tests for Command Executor.

Tests CommandExecutor execution logic including:
- Epic/story/task creation via StateManager
- Reference resolution (epic_reference → epic_id)
- Transaction safety and error handling
- Confirmation workflow for destructive operations

Coverage Target: 95%
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.nl.command_executor import CommandExecutor, ExecutionResult
from src.core.models import TaskType, Task


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_state_manager():
    """Create mock StateManager."""
    mock_state = Mock()
    mock_state.create_epic = Mock(return_value=5)
    mock_state.create_story = Mock(return_value=6)
    mock_state.create_task = Mock()
    mock_state.create_milestone = Mock(return_value=10)
    mock_state.list_tasks = Mock(return_value=[])
    mock_state.get_task = Mock()
    return mock_state


@pytest.fixture
def executor(mock_state_manager):
    """Create CommandExecutor with mock StateManager."""
    return CommandExecutor(mock_state_manager, default_project_id=1)


# ============================================================================
# Test: Epic Creation
# ============================================================================

def test_epic_creation_success(executor, mock_state_manager):
    """Test successful epic creation."""
    command = {
        'entity_type': 'epic',
        'entities': [{
            'title': 'User Authentication',
            'description': 'Complete auth system'
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    assert 5 in result.created_ids
    assert len(result.errors) == 0
    mock_state_manager.create_epic.assert_called_once()


def test_epic_creation_with_priority(executor, mock_state_manager):
    """Test epic creation with custom priority."""
    command = {
        'entity_type': 'epic',
        'entities': [{
            'title': 'Critical Feature',
            'description': 'High priority',
            'priority': 1
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    # Check priority was passed
    call_kwargs = mock_state_manager.create_epic.call_args[1]
    assert 'priority' in call_kwargs
    assert call_kwargs['priority'] == 1


# ============================================================================
# Test: Story Creation
# ============================================================================

def test_story_creation_success(executor, mock_state_manager):
    """Test successful story creation with epic_id."""
    command = {
        'entity_type': 'story',
        'entities': [{
            'title': 'User Login',
            'description': 'Login feature',
            'epic_id': 5
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    assert 6 in result.created_ids
    mock_state_manager.create_story.assert_called_once_with(
        project_id=1,
        epic_id=5,
        title='User Login',
        description='Login feature'
    )


def test_story_creation_missing_epic_id(executor):
    """Test story creation fails without epic_id."""
    command = {
        'entity_type': 'story',
        'entities': [{
            'title': 'Story',
            'description': 'Story without epic'
            # Missing epic_id
        }]
    }

    result = executor.execute(command)

    assert result.success is False
    assert any('epic_id' in err.lower() for err in result.errors)


# ============================================================================
# Test: Task Creation
# ============================================================================

def test_task_creation_success(executor, mock_state_manager):
    """Test successful task creation."""
    mock_task = Mock()
    mock_task.id = 7
    mock_task.title = 'Implement auth'
    mock_state_manager.create_task.return_value = mock_task

    command = {
        'entity_type': 'task',
        'entities': [{
            'title': 'Implement auth',
            'description': 'Auth implementation',
            'story_id': 6
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    assert 7 in result.created_ids
    mock_state_manager.create_task.assert_called_once()


def test_task_creation_with_dependencies(executor, mock_state_manager):
    """Test task creation with dependencies."""
    mock_task = Mock()
    mock_task.id = 8
    mock_state_manager.create_task.return_value = mock_task

    command = {
        'entity_type': 'task',
        'entities': [{
            'title': 'Integration tests',
            'description': 'Test suite',
            'dependencies': [5, 6, 7]
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    # Check dependencies were passed
    call_args = mock_state_manager.create_task.call_args[0]
    task_data = call_args[1]
    assert 'dependencies' in task_data
    assert task_data['dependencies'] == [5, 6, 7]


# ============================================================================
# Test: Subtask Creation
# ============================================================================

def test_subtask_creation_success(executor, mock_state_manager):
    """Test successful subtask creation."""
    mock_task = Mock()
    mock_task.id = 9
    mock_state_manager.create_task.return_value = mock_task

    command = {
        'entity_type': 'subtask',
        'entities': [{
            'title': 'Write unit tests',
            'description': 'Tests',
            'parent_task_id': 7
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    assert 9 in result.created_ids


def test_subtask_missing_parent_task_id(executor):
    """Test subtask creation fails without parent_task_id."""
    command = {
        'entity_type': 'subtask',
        'entities': [{
            'title': 'Subtask',
            'description': 'Without parent'
        }]
    }

    result = executor.execute(command)

    assert result.success is False
    assert any('parent_task_id' in err.lower() for err in result.errors)


# ============================================================================
# Test: Milestone Creation
# ============================================================================

def test_milestone_creation_success(executor, mock_state_manager):
    """Test successful milestone creation."""
    command = {
        'entity_type': 'milestone',
        'entities': [{
            'name': 'Auth Complete',
            'description': 'Authentication done',
            'required_epic_ids': [5, 6]
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    assert 10 in result.created_ids
    mock_state_manager.create_milestone.assert_called_once()


def test_milestone_missing_required_epic_ids(executor):
    """Test milestone creation fails without required_epic_ids."""
    command = {
        'entity_type': 'milestone',
        'entities': [{
            'name': 'Milestone',
            'description': 'Without epics'
        }]
    }

    result = executor.execute(command)

    assert result.success is False
    assert any('required_epic_ids' in err.lower() for err in result.errors)


# ============================================================================
# Test: Reference Resolution
# ============================================================================

def test_epic_reference_resolution(executor, mock_state_manager):
    """Test epic_reference resolved to epic_id."""
    # Mock search returns matching epic
    mock_epic = Mock()
    mock_epic.id = 5
    mock_epic.title = 'User Authentication System'
    mock_state_manager.list_tasks.return_value = [mock_epic]

    command = {
        'entity_type': 'story',
        'entities': [{
            'title': 'Login',
            'epic_reference': 'User Authentication'  # Name, not ID
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    # Should have resolved and called create_story with epic_id=5
    mock_state_manager.create_story.assert_called_once()
    call_kwargs = mock_state_manager.create_story.call_args[1]
    assert call_kwargs['epic_id'] == 5


def test_epic_reference_not_found(executor, mock_state_manager):
    """Test epic_reference fails if epic doesn't exist."""
    # Mock search returns no results
    mock_state_manager.list_tasks.return_value = []

    command = {
        'entity_type': 'story',
        'entities': [{
            'title': 'Story',
            'epic_reference': 'Nonexistent Epic'
        }]
    }

    result = executor.execute(command)

    assert result.success is False
    assert any('not found' in err.lower() for err in result.errors)


# ============================================================================
# Test: Multiple Entities
# ============================================================================

def test_multiple_entities_creation(executor, mock_state_manager):
    """Test creating multiple entities in one command."""
    mock_state_manager.create_epic.side_effect = [10, 11, 12]

    command = {
        'entity_type': 'epic',
        'entities': [
            {'title': 'Epic 1', 'description': 'First'},
            {'title': 'Epic 2', 'description': 'Second'},
            {'title': 'Epic 3', 'description': 'Third'}
        ]
    }

    result = executor.execute(command)

    assert result.success is True
    assert len(result.created_ids) == 3
    assert result.created_ids == [10, 11, 12]
    assert mock_state_manager.create_epic.call_count == 3


def test_partial_failure_stops_execution(executor, mock_state_manager):
    """Test execution stops on first error."""
    # First succeeds, second fails
    mock_state_manager.create_epic.side_effect = [
        10,  # Success
        Exception("Database error")  # Failure
    ]

    command = {
        'entity_type': 'epic',
        'entities': [
            {'title': 'Epic 1', 'description': 'First'},
            {'title': 'Epic 2', 'description': 'Second'},
            {'title': 'Epic 3', 'description': 'Third'}
        ]
    }

    result = executor.execute(command)

    assert result.success is False
    assert len(result.created_ids) == 1  # Only first succeeded
    assert 10 in result.created_ids
    assert len(result.errors) > 0
    assert mock_state_manager.create_epic.call_count == 2  # Stopped after error


# ============================================================================
# Test: Confirmation Workflow
# ============================================================================

def test_delete_requires_confirmation(executor):
    """Test delete operation requires confirmation."""
    command = {
        'entity_type': 'epic',
        'action': 'delete',  # Destructive operation
        'entities': [{'id': 5}]
    }

    result = executor.execute(command, confirmed=False)

    assert result.success is False
    assert result.confirmation_required is True
    assert any('confirmation' in err.lower() for err in result.errors)


def test_delete_with_confirmation(executor, mock_state_manager):
    """Test delete proceeds with confirmation."""
    command = {
        'entity_type': 'epic',
        'action': 'delete',
        'entities': [{'id': 5, 'title': 'Epic', 'description': 'To delete'}]
    }

    # Note: We'd need a delete method in StateManager for this to fully work
    # For now, test that confirmation flag allows execution
    result = executor.execute(command, confirmed=True)

    # With confirmed=True, should attempt execution (may fail if no delete method)
    # But won't fail on confirmation check
    assert result.confirmation_required is False


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_empty_command(executor):
    """Test empty command returns error."""
    result = executor.execute({})

    assert result.success is False
    assert len(result.errors) > 0


def test_no_entities(executor):
    """Test command with no entities returns error."""
    command = {
        'entity_type': 'epic',
        'entities': []
    }

    result = executor.execute(command)

    assert result.success is False
    assert any('no' in err.lower() and 'entities' in err.lower() for err in result.errors)


def test_unknown_entity_type(executor):
    """Test unknown entity type raises error."""
    command = {
        'entity_type': 'unknown_type',
        'entities': [{'title': 'Test'}]
    }

    result = executor.execute(command)

    assert result.success is False
    assert any('unknown' in err.lower() for err in result.errors)


# ============================================================================
# Test: Story Reference Resolution
# ============================================================================

def test_story_reference_resolution(executor, mock_state_manager):
    """Test story_reference resolved to story_id."""
    # Mock search returns matching story
    mock_story = Mock()
    mock_story.id = 10
    mock_story.title = 'User Login Story'
    mock_state_manager.list_tasks.return_value = [mock_story]

    mock_task = Mock()
    mock_task.id = 15
    mock_state_manager.create_task.return_value = mock_task

    command = {
        'entity_type': 'task',
        'entities': [{
            'title': 'Login API',
            'description': 'Create endpoint',
            'story_reference': 'User Login'  # Name, not ID
        }]
    }

    result = executor.execute(command)

    assert result.success is True
    # Should have resolved story_reference to story_id
    call_args = mock_state_manager.create_task.call_args[0]
    task_data = call_args[1]
    assert task_data['story_id'] == 10


def test_story_reference_not_found(executor, mock_state_manager):
    """Test story_reference fails if story doesn't exist."""
    mock_state_manager.list_tasks.return_value = []

    command = {
        'entity_type': 'task',
        'entities': [{
            'title': 'Task',
            'story_reference': 'Nonexistent Story'
        }]
    }

    result = executor.execute(command)

    assert result.success is False
    assert any('story' in err.lower() and 'not found' in err.lower() for err in result.errors)


# ============================================================================
# Test: Project ID Handling
# ============================================================================

def test_custom_project_id(executor, mock_state_manager):
    """Test execution with custom project_id."""
    command = {
        'entity_type': 'epic',
        'entities': [{'title': 'Epic', 'description': 'Desc'}]
    }

    result = executor.execute(command, project_id=5)

    assert result.success is True
    # Check project_id=5 was used
    call_kwargs = mock_state_manager.create_epic.call_args[1]
    assert call_kwargs['project_id'] == 5


# ============================================================================
# Test: ExecutionResult
# ============================================================================

def test_execution_result_creation():
    """Test ExecutionResult dataclass."""
    result = ExecutionResult(
        success=True,
        created_ids=[5, 6, 7],
        errors=[],
        results={'entity_type': 'epic', 'created_count': 3}
    )

    assert result.success is True
    assert len(result.created_ids) == 3
    assert result.results['created_count'] == 3


def test_execution_result_with_errors():
    """Test ExecutionResult with errors."""
    result = ExecutionResult(
        success=False,
        errors=['Epic not found', 'Database error']
    )

    assert result.success is False
    assert len(result.errors) == 2
    assert len(result.created_ids) == 0
