"""Unit tests for CommandValidator (ADR-016 Story 5 Task 3.1).

Tests the updated CommandValidator with OperationContext API covering:
- Operation + entity type combination validation (3 tests)
- Operation requirements validation (3 tests)
- Parameter validation - status, priority, dependencies (4 tests)
- Entity exists check for UPDATE/DELETE (3 tests)
- Backward compatibility with validate_legacy() (2 tests)

Target: 90%+ code coverage for CommandValidator
"""

import pytest
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from src.nl.command_validator import CommandValidator, ValidationResult, ValidationException
from src.nl.types import OperationContext, OperationType, EntityType, QueryType
from core.state import StateManager


@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager for testing."""
    state = Mock(spec=StateManager)
    return state


@pytest.fixture
def validator(mock_state_manager):
    """Create CommandValidator with mock StateManager."""
    return CommandValidator(mock_state_manager)


class TestValidateOperationEntityCombination:
    """Test operation + entity type combination validation."""

    def test_valid_update_project(self, validator):
        """Test valid UPDATE + PROJECT combination."""
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.PROJECT],
            identifier="test project",
            parameters={"status": "INACTIVE"},
            confidence=0.95,
            raw_input="Mark test project as INACTIVE"
        )

        result = validator.validate(context)

        # Should pass operation+entity validation (may fail on existence check)
        errors = validator._validate_operation_entity_combination(context)
        assert len(errors) == 0

    def test_valid_create_epic(self, validator):
        """Test valid CREATE + EPIC combination."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_types=[EntityType.EPIC],
            identifier=None,
            parameters={"title": "User Authentication"},
            confidence=0.92,
            raw_input="Create epic for user authentication"
        )

        errors = validator._validate_operation_entity_combination(context)
        assert len(errors) == 0

    def test_valid_query_task(self, validator):
        """Test valid QUERY + TASK combination."""
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            identifier=None,
            parameters={},
            query_type=QueryType.SIMPLE,
            confidence=0.90,
            raw_input="Show all tasks"
        )

        errors = validator._validate_operation_entity_combination(context)
        assert len(errors) == 0


class TestValidateOperationRequirements:
    """Test operation-specific requirements validation."""

    def test_update_requires_identifier(self, validator):
        """Test UPDATE operation requires identifier (OperationContext validation)."""
        # OperationContext.__post_init__() already validates this
        # Test that constructing without identifier raises ValueError
        with pytest.raises(ValueError, match="update operation requires an identifier"):
            context = OperationContext(
                operation=OperationType.UPDATE,
                entity_types=[EntityType.PROJECT],
                identifier=None,  # Missing!
                parameters={"status": "INACTIVE"},
                confidence=0.85
            )

    def test_delete_requires_identifier(self, validator):
        """Test DELETE operation requires identifier (OperationContext validation)."""
        # OperationContext.__post_init__() already validates this
        # Test that constructing without identifier raises ValueError
        with pytest.raises(ValueError, match="delete operation requires an identifier"):
            context = OperationContext(
                operation=OperationType.DELETE,
                entity_types=[EntityType.TASK],
                identifier=None,  # Missing!
                parameters={},
                confidence=0.90
            )

    def test_query_allows_null_identifier(self, validator):
        """Test QUERY operation allows null identifier (show all)."""
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.PROJECT],
            identifier=None,  # Valid for "show all" queries
            parameters={},
            query_type=QueryType.SIMPLE,
            confidence=0.92
        )

        errors = validator._validate_operation_requirements(context)
        assert len(errors) == 0


class TestValidateOperationParameters:
    """Test parameter validation (status, priority, dependencies)."""

    def test_valid_status_parameter(self, validator):
        """Test valid status parameter for PROJECT."""
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.PROJECT],
            identifier="test project",
            parameters={"status": "INACTIVE"},
            confidence=0.95
        )

        errors = validator._validate_operation_parameters(context)
        assert len(errors) == 0

    def test_invalid_status_parameter(self, validator):
        """Test invalid status parameter for PROJECT."""
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.PROJECT],
            identifier="test project",
            parameters={"status": "INVALID_STATUS"},
            confidence=0.85
        )

        errors = validator._validate_operation_parameters(context)
        assert len(errors) > 0
        assert any("Invalid status" in err for err in errors)

    def test_valid_priority_parameter(self, validator):
        """Test valid priority parameter."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_types=[EntityType.TASK],
            identifier=None,
            parameters={"priority": "HIGH", "title": "Implement feature X"},
            confidence=0.90
        )

        errors = validator._validate_operation_parameters(context)
        assert len(errors) == 0

    def test_invalid_priority_parameter(self, validator):
        """Test invalid priority parameter."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_types=[EntityType.TASK],
            identifier=None,
            parameters={"priority": "URGENT", "title": "Implement feature X"},
            confidence=0.85
        )

        errors = validator._validate_operation_parameters(context)
        assert len(errors) > 0
        assert any("Invalid priority" in err for err in errors)

    def test_optional_parameters_with_none(self, validator):
        """Phase 4: None values for optional parameters should be valid.

        Tests that the parameter validator accepts None for optional fields
        (priority, status) without raising validation errors.

        Expected impact: -8% failure rate
        """
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_types=[EntityType.TASK],
            identifier=None,
            parameters={
                'title': 'Test Task',
                'priority': None,  # Extractor returned None
                'status': None,    # Extractor returned None
            },
            confidence=0.85
        )

        errors = validator._validate_operation_parameters(context)
        assert len(errors) == 0, f"Should accept None for optional fields, got errors: {errors}"


class TestValidateEntityExists:
    """Test entity exists check for UPDATE/DELETE operations."""

    def test_project_exists_by_id(self, validator, mock_state_manager):
        """Test UPDATE project with existing ID."""
        # Mock project found
        mock_project = Mock()
        mock_project.id = 1
        mock_project.project_name = "Test Project"
        mock_state_manager.get_project.return_value = mock_project

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.PROJECT],
            identifier=1,
            parameters={"status": "INACTIVE"},
            confidence=0.95
        )

        errors = validator._validate_entity_exists(context)
        assert len(errors) == 0
        mock_state_manager.get_project.assert_called_once_with(1)

    def test_task_not_found_by_id(self, validator, mock_state_manager):
        """Test UPDATE task with non-existent ID."""
        # Mock task not found
        mock_state_manager.get_task.return_value = None

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.TASK],
            identifier=999,
            parameters={"status": "COMPLETED"},
            confidence=0.90
        )

        errors = validator._validate_entity_exists(context)
        assert len(errors) > 0
        assert any("Task with ID 999 not found" in err for err in errors)

    def test_project_exists_by_name(self, validator, mock_state_manager):
        """Test UPDATE project with existing name."""
        # Mock project found by name
        mock_project1 = Mock()
        mock_project1.id = 1
        mock_project1.project_name = "Other Project"

        mock_project2 = Mock()
        mock_project2.id = 2
        mock_project2.project_name = "Test Project"

        # Add list_projects to mock
        mock_state_manager.list_projects = Mock(return_value=[mock_project1, mock_project2])

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.PROJECT],
            identifier="test project",  # Case-insensitive match
            parameters={"status": "INACTIVE"},
            confidence=0.92
        )

        errors = validator._validate_entity_exists(context)
        assert len(errors) == 0


class TestValidateDependencies:
    """Test dependency validation (circular dependencies, self-dependency)."""

    def test_self_dependency_rejected(self, validator):
        """Test task cannot depend on itself."""
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.TASK],
            identifier=5,
            parameters={"dependencies": [5]},  # Self-dependency!
            confidence=0.85
        )

        errors = validator._validate_dependencies_from_context(context)
        assert len(errors) > 0
        assert any("cannot depend on itself" in err for err in errors)

    def test_valid_dependencies(self, validator, mock_state_manager):
        """Test valid task dependencies."""
        # Mock dependency tasks exist
        mock_task1 = Mock()
        mock_task1.id = 1
        mock_task1.dependencies = []

        mock_task2 = Mock()
        mock_task2.id = 2
        mock_task2.dependencies = []

        mock_state_manager.get_task.side_effect = lambda tid: mock_task1 if tid == 1 else mock_task2

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.TASK],
            identifier=3,
            parameters={"dependencies": [1, 2]},
            confidence=0.92
        )

        errors = validator._validate_dependencies_from_context(context)
        assert len(errors) == 0


class TestValidateIntegration:
    """Test full validation pipeline integration."""

    def test_valid_update_project_full_validation(self, validator, mock_state_manager):
        """Test complete validation for valid UPDATE PROJECT command."""
        # Mock project exists
        mock_project = Mock()
        mock_project.id = 1
        mock_project.project_name = "Manual Tetris Test"
        mock_state_manager.get_project.return_value = mock_project

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.PROJECT],
            identifier=1,
            parameters={"status": "INACTIVE"},
            confidence=0.95,
            raw_input="Mark the manual tetris test as INACTIVE"
        )

        result = validator.validate(context)

        assert result.valid
        assert len(result.errors) == 0
        assert result.validated_command['operation'] == 'update'
        assert result.validated_command['entity_type'] == 'project'
        assert result.validated_command['identifier'] == 1
        assert result.validated_command['parameters']['status'] == 'INACTIVE'

    def test_invalid_update_missing_identifier(self, validator):
        """Test validation fails for UPDATE without identifier."""
        # OperationContext.__post_init__() validates this, so we test the ValueError
        with pytest.raises(ValueError, match="update operation requires an identifier"):
            context = OperationContext(
                operation=OperationType.UPDATE,
                entity_types=[EntityType.PROJECT],
                identifier=None,  # Missing!
                parameters={"status": "INACTIVE"},
                confidence=0.85
            )


class TestBackwardCompatibility:
    """Test backward compatibility with legacy ExtractedEntities API."""

    def test_validate_legacy_deprecation_warning(self, validator):
        """Test validate_legacy() emits deprecation warning."""
        # Mock ExtractedEntities
        @dataclass
        class MockExtractedEntities:
            entity_type: str = "task"
            entities: list = None
            confidence: float = 0.9

            def __post_init__(self):
                if self.entities is None:
                    self.entities = [{"title": "Test Task"}]

        entities = MockExtractedEntities()

        with pytest.warns(DeprecationWarning, match="validate_legacy.*deprecated"):
            result = validator.validate_legacy(entities)

        # Should still work
        assert isinstance(result, ValidationResult)

    def test_validate_legacy_functionality(self, validator):
        """Test validate_legacy() still works correctly."""
        # Mock ExtractedEntities
        @dataclass
        class MockExtractedEntities:
            entity_type: str = "task"
            entities: list = None
            confidence: float = 0.9

            def __post_init__(self):
                if self.entities is None:
                    self.entities = [{"title": "Test Task", "description": "Test"}]

        entities = MockExtractedEntities()

        with pytest.warns(DeprecationWarning):
            result = validator.validate_legacy(entities)

        assert result.valid
        assert len(result.errors) == 0
        assert result.validated_command['entity_type'] == 'task'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
