"""Unit tests for Command Validator.

Tests CommandValidator validation logic including:
- Required fields validation
- Epic/story/task reference validation
- Circular dependency detection
- Business rule enforcement

Coverage Target: 95%
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.nl.command_validator import CommandValidator, ValidationResult
from src.nl.entity_extractor import ExtractedEntities
from src.core.models import TaskType


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_state_manager():
    """Create mock StateManager."""
    mock_state = Mock()
    mock_state.get_task = Mock()
    mock_state.list_tasks = Mock(return_value=[])
    return mock_state


@pytest.fixture
def validator(mock_state_manager):
    """Create CommandValidator with mock StateManager."""
    return CommandValidator(mock_state_manager)


# ============================================================================
# Test: Valid Entity Creation
# ============================================================================

def test_valid_epic_creation(validator):
    """Test validation passes for valid epic."""
    entities = ExtractedEntities(
        entity_type='epic',
        entities=[{
            'title': 'User Authentication',
            'description': 'Complete auth system'
        }],
        confidence=0.95
    )

    result = validator.validate(entities)

    assert result.valid is True
    assert len(result.errors) == 0
    assert result.validated_command['entity_type'] == 'epic'


def test_valid_story_with_epic_id(validator, mock_state_manager):
    """Test validation passes for story with valid epic_id."""
    # Mock epic exists
    mock_epic = Mock()
    mock_epic.task_type = TaskType.EPIC
    mock_state_manager.get_task.return_value = mock_epic

    entities = ExtractedEntities(
        entity_type='story',
        entities=[{
            'title': 'User Login',
            'description': 'Login feature',
            'epic_id': 5
        }],
        confidence=0.92
    )

    result = validator.validate(entities)

    assert result.valid is True
    assert len(result.errors) == 0


# ============================================================================
# Test: Required Fields Validation
# ============================================================================

def test_epic_missing_title(validator):
    """Test validation fails when epic missing title."""
    entities = ExtractedEntities(
        entity_type='epic',
        entities=[{
            'description': 'Auth system'
            # Missing 'title'
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any('title' in err.lower() for err in result.errors)


def test_subtask_missing_parent_task_id(validator):
    """Test validation fails when subtask missing parent_task_id."""
    entities = ExtractedEntities(
        entity_type='subtask',
        entities=[{
            'title': 'Write tests'
            # Missing 'parent_task_id'
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any('parent_task_id' in err.lower() for err in result.errors)


# ============================================================================
# Test: Reference Validation
# ============================================================================

def test_invalid_epic_reference(validator, mock_state_manager):
    """Test validation fails when epic_id doesn't exist."""
    # Mock epic doesn't exist
    mock_state_manager.get_task.return_value = None

    entities = ExtractedEntities(
        entity_type='story',
        entities=[{
            'title': 'Login Story',
            'epic_id': 9999  # Doesn't exist
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any('9999' in err and 'not found' in err.lower() for err in result.errors)


def test_epic_id_not_epic_type(validator, mock_state_manager):
    """Test validation fails when epic_id points to non-epic task."""
    # Mock task exists but is not epic
    mock_task = Mock()
    mock_task.task_type = TaskType.TASK  # Not epic!
    mock_state_manager.get_task.return_value = mock_task

    entities = ExtractedEntities(
        entity_type='story',
        entities=[{
            'title': 'Story',
            'epic_id': 5
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any('not an epic' in err.lower() for err in result.errors)


def test_invalid_parent_task_reference(validator, mock_state_manager):
    """Test validation fails when parent_task_id doesn't exist."""
    mock_state_manager.get_task.return_value = None

    entities = ExtractedEntities(
        entity_type='subtask',
        entities=[{
            'title': 'Subtask',
            'parent_task_id': 9999
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any('parent task' in err.lower() and 'not found' in err.lower() for err in result.errors)


# ============================================================================
# Test: Circular Dependency Detection
# ============================================================================

def test_task_self_dependency(validator):
    """Test validation catches task depending on itself."""
    entities = ExtractedEntities(
        entity_type='task',
        entities=[{
            'id': 5,
            'title': 'Task',
            'dependencies': [5]  # Depends on itself!
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert any('cannot depend on itself' in err.lower() for err in result.errors)


def test_no_circular_dependency_for_new_task(validator):
    """Test no circular check for new task (no ID)."""
    entities = ExtractedEntities(
        entity_type='task',
        entities=[{
            'title': 'New Task',
            'dependencies': [1, 2, 3]
            # No 'id' field - new task
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    # Should be valid (no circular check without task ID)
    assert result.valid is True


# ============================================================================
# Test: Multiple Entities
# ============================================================================

def test_multiple_valid_entities(validator, mock_state_manager):
    """Test validation with multiple valid entities."""
    mock_epic = Mock()
    mock_epic.task_type = TaskType.EPIC
    mock_state_manager.get_task.return_value = mock_epic

    entities = ExtractedEntities(
        entity_type='story',
        entities=[
            {'title': 'Login', 'epic_id': 5},
            {'title': 'Signup', 'epic_id': 5},
            {'title': 'MFA', 'epic_id': 5}
        ],
        confidence=0.92
    )

    result = validator.validate(entities)

    assert result.valid is True
    assert len(result.errors) == 0


def test_multiple_entities_with_errors(validator, mock_state_manager):
    """Test validation fails if any entity invalid."""
    mock_state_manager.get_task.return_value = None  # Epic doesn't exist

    entities = ExtractedEntities(
        entity_type='story',
        entities=[
            {'title': 'Login', 'epic_id': 5},  # Invalid
            {'title': 'Signup'},  # Missing epic_id - but that's OK for story
            {'title': 'MFA', 'epic_id': 9999}  # Invalid
        ],
        confidence=0.9
    )

    result = validator.validate(entities)

    assert result.valid is False
    assert len(result.errors) >= 2  # At least 2 errors


# ============================================================================
# Test: Transitive Dependency Checking
# ============================================================================

def test_transitive_circular_dependency(validator, mock_state_manager):
    """Test detection of transitive circular dependency."""
    # Setup: Task 1 -> Task 2 -> Task 3 -> Task 1 (cycle)
    task1 = Mock()
    task1.dependencies = [2]
    task2 = Mock()
    task2.dependencies = [3]
    task3 = Mock()
    task3.dependencies = [1]  # Back to task 1!

    def get_task_mock(task_id):
        if task_id == 1:
            return task1
        elif task_id == 2:
            return task2
        elif task_id == 3:
            return task3
        return None

    mock_state_manager.get_task.side_effect = get_task_mock

    entities = ExtractedEntities(
        entity_type='task',
        entities=[{
            'id': 1,
            'title': 'Task 1',
            'dependencies': [2]
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    # Should detect circular dependency
    assert result.valid is False
    assert any('circular' in err.lower() for err in result.errors)


def test_get_all_dependencies_no_circular(validator, mock_state_manager):
    """Test _get_all_dependencies with valid tree."""
    # Task 2 depends on task 5
    task2 = Mock()
    task2.dependencies = [5]
    task5 = Mock()
    task5.dependencies = []

    def get_task_mock(task_id):
        if task_id == 2:
            return task2
        elif task_id == 5:
            return task5
        return None

    mock_state_manager.get_task.side_effect = get_task_mock

    # Get all dependencies of [2]
    all_deps = validator._get_all_dependencies([2])

    assert 2 in all_deps
    assert 5 in all_deps


def test_dependency_validation_with_exception(validator, mock_state_manager):
    """Test dependency validation handles exceptions gracefully."""
    # Mock get_task raises exception
    mock_state_manager.get_task.side_effect = Exception("DB error")

    entities = ExtractedEntities(
        entity_type='task',
        entities=[{
            'id': 1,
            'title': 'Task',
            'dependencies': [2, 3]
        }],
        confidence=0.9
    )

    # Should not fail completely - just log warning
    result = validator.validate(entities)

    # Should still be valid (validation continues despite DB error)
    assert result.valid is True


# ============================================================================
# Test: Reference Validation Edge Cases
# ============================================================================

def test_story_id_validation_exception(validator, mock_state_manager):
    """Test story_id validation handles exceptions."""
    mock_state_manager.get_task.side_effect = Exception("DB error")

    entities = ExtractedEntities(
        entity_type='task',
        entities=[{
            'title': 'Task',
            'story_id': 5
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    # Should have error about story check failure
    assert result.valid is False
    assert any('story' in err.lower() for err in result.errors)


def test_multiple_reference_types(validator, mock_state_manager):
    """Test entity with multiple reference types."""
    mock_epic = Mock()
    mock_epic.task_type = TaskType.EPIC
    mock_story = Mock()
    mock_story.task_type = TaskType.STORY
    mock_parent = Mock()

    def get_task_mock(task_id):
        if task_id == 5:
            return mock_epic
        elif task_id == 10:
            return mock_story
        elif task_id == 15:
            return mock_parent
        return None

    mock_state_manager.get_task.side_effect = get_task_mock

    entities = ExtractedEntities(
        entity_type='task',
        entities=[{
            'title': 'Complex Task',
            'epic_id': 5,
            'story_id': 10,
            'parent_task_id': 15
        }],
        confidence=0.9
    )

    result = validator.validate(entities)

    # Should validate all references
    assert result.valid is True


# ============================================================================
# Test: ValidationResult
# ============================================================================

def test_validation_result_creation():
    """Test ValidationResult dataclass."""
    result = ValidationResult(
        valid=True,
        errors=[],
        warnings=['Minor issue'],
        validated_command={'entity_type': 'epic'}
    )

    assert result.valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 1


def test_validation_result_with_errors():
    """Test ValidationResult with errors."""
    result = ValidationResult(
        valid=False,
        errors=['Epic not found', 'Invalid field'],
        warnings=[]
    )

    assert result.valid is False
    assert len(result.errors) == 2
