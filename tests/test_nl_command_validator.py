"""Comprehensive tests for NL command validation (Phase 2).

Test coverage for src/nl/command_validator.py targeting 90% coverage.
Covers US-NL-008, US-NL-009, US-NL-010, US-NL-017.

Total test count: 30 tests
"""

import pytest
from unittest.mock import MagicMock

from src.nl.command_validator import CommandValidator, ValidationResult, ValidationException
from src.nl.entity_extractor import ExtractedEntities
from src.core.state import StateManager
from src.core.models import Task, TaskType, TaskStatus


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_state():
    """In-memory StateManager with test data."""
    state = StateManager(database_url='sqlite:///:memory:')

    # Create test project
    project = state.create_project(
        name="Test Project",
        description="Test project",
        working_dir="/tmp/test"
    )

    # Create test epic (returns epic_id)
    epic_id = state.create_epic(
        project_id=project.id,
        title="Test Epic",
        description="Test epic"
    )

    # Create test story (returns story_id)
    story_id = state.create_story(
        project_id=project.id,
        epic_id=epic_id,
        title="Test Story",
        description="Test story"
    )

    # Create test task using create_task (returns Task object)
    task = state.create_task(
        project_id=project.id,
        task_data={
            "title": "Test Task",
            "description": "Test task"
        }
    )

    yield state
    state.close()


@pytest.fixture
def validator(test_state):
    """CommandValidator with test StateManager."""
    return CommandValidator(test_state)


# ============================================================================
# Test Class 1: Required Fields Validation (US-NL-008) - 10 tests
# ============================================================================

class TestRequiredFieldsValidation:
    """Test required field validation for different entity types."""

    def test_epic_with_title_valid(self, validator):
        """Epic with title should be valid."""
        entities = ExtractedEntities(
            entity_type="epic",
            entities=[{"title": "New Epic", "description": "Test"}],
            confidence=0.95
        )

        result = validator.validate(entities)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_epic_missing_title_invalid(self, validator):
        """Epic without title should be invalid."""
        entities = ExtractedEntities(
            entity_type="epic",
            entities=[{"description": "Test"}],  # Missing title
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("title" in error.lower() for error in result.errors)

    def test_story_with_title_valid(self, validator):
        """Story with title should be valid."""
        entities = ExtractedEntities(
            entity_type="story",
            entities=[{"title": "New Story"}],
            confidence=0.92
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_task_missing_title_invalid(self, validator):
        """Task without title should be invalid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"description": "No title"}],
            confidence=0.8
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("title" in error.lower() for error in result.errors)

    def test_subtask_with_both_required_fields_valid(self, validator):
        """Subtask with title and parent_task_id should be valid."""
        entities = ExtractedEntities(
            entity_type="subtask",
            entities=[{"title": "Subtask", "parent_task_id": 3}],
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_subtask_missing_parent_task_id_invalid(self, validator):
        """Subtask without parent_task_id should be invalid."""
        entities = ExtractedEntities(
            entity_type="subtask",
            entities=[{"title": "Orphan Subtask"}],  # Missing parent_task_id
            confidence=0.85
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("parent_task_id" in error.lower() for error in result.errors)

    def test_milestone_with_required_fields_valid(self, validator):
        """Milestone with name and required_epic_ids should be valid."""
        entities = ExtractedEntities(
            entity_type="milestone",
            entities=[{"name": "Alpha Release", "required_epic_ids": [1]}],
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_milestone_missing_name_invalid(self, validator):
        """Milestone without name should be invalid."""
        entities = ExtractedEntities(
            entity_type="milestone",
            entities=[{"required_epic_ids": [1]}],  # Missing name
            confidence=0.8
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("name" in error.lower() for error in result.errors)

    def test_milestone_missing_required_epics_invalid(self, validator):
        """Milestone without required_epic_ids should be invalid."""
        entities = ExtractedEntities(
            entity_type="milestone",
            entities=[{"name": "Beta Release"}],  # Missing required_epic_ids
            confidence=0.85
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("required_epic_ids" in error.lower() for error in result.errors)

    def test_empty_title_invalid(self, validator):
        """Empty string for title should be invalid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"title": ""}],  # Empty string
            confidence=0.7
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("title" in error.lower() for error in result.errors)


# ============================================================================
# Test Class 2: Reference Validation (US-NL-009) - 10 tests
# ============================================================================

class TestReferenceValidation:
    """Test validation of entity references (epic_id, story_id, parent_task_id)."""

    def test_valid_epic_id_reference(self, validator):
        """Story with valid epic_id should be valid."""
        entities = ExtractedEntities(
            entity_type="story",
            entities=[{"title": "New Story", "epic_id": 1}],  # Epic ID=1 exists
            confidence=0.95
        )

        result = validator.validate(entities)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_invalid_epic_id_reference(self, validator):
        """Story with non-existent epic_id should be invalid."""
        entities = ExtractedEntities(
            entity_type="story",
            entities=[{"title": "Orphan Story", "epic_id": 999}],  # Epic 999 doesn't exist
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("999" in error for error in result.errors)
        assert any("not found" in error.lower() for error in result.errors)

    def test_epic_id_points_to_wrong_type(self, validator):
        """epic_id pointing to a task (not epic) should be invalid."""
        entities = ExtractedEntities(
            entity_type="story",
            entities=[{"title": "Story", "epic_id": 3}],  # ID=3 is a task, not epic
            confidence=0.85
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("not an epic" in error.lower() for error in result.errors)

    def test_valid_story_id_reference(self, validator):
        """Task with valid story_id should be valid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"title": "New Task", "story_id": 2}],  # Story ID=2 exists
            confidence=0.93
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_invalid_story_id_reference(self, validator):
        """Task with non-existent story_id should be invalid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"title": "Task", "story_id": 888}],  # Story 888 doesn't exist
            confidence=0.88
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("888" in error for error in result.errors)

    def test_story_id_points_to_wrong_type(self, validator):
        """story_id pointing to an epic (not story) should be invalid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"title": "Task", "story_id": 1}],  # ID=1 is epic, not story
            confidence=0.8
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("not a story" in error.lower() for error in result.errors)

    def test_valid_parent_task_id_reference(self, validator):
        """Subtask with valid parent_task_id should be valid."""
        entities = ExtractedEntities(
            entity_type="subtask",
            entities=[{"title": "Subtask", "parent_task_id": 3}],  # Task ID=3 exists
            confidence=0.92
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_invalid_parent_task_id_reference(self, validator):
        """Subtask with non-existent parent_task_id should be invalid."""
        entities = ExtractedEntities(
            entity_type="subtask",
            entities=[{"title": "Subtask", "parent_task_id": 777}],  # Task 777 doesn't exist
            confidence=0.85
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("777" in error for error in result.errors)

    def test_multiple_invalid_references(self, validator):
        """Entity with multiple invalid references should report all errors."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "title": "Task",
                "epic_id": 111,   # Doesn't exist
                "story_id": 222   # Doesn't exist
            }],
            confidence=0.7
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert len(result.errors) >= 2  # At least 2 errors

    def test_optional_references_allowed(self, validator):
        """Entity without optional references should be valid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"title": "Independent Task"}],  # No epic_id or story_id
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is True


# ============================================================================
# Test Class 3: Circular Dependency Validation (US-NL-010) - 10 tests
# ============================================================================

class TestCircularDependencyValidation:
    """Test circular dependency detection in task dependencies."""

    def test_task_without_dependencies_valid(self, validator):
        """Task without dependencies should be valid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"title": "Independent Task"}],
            confidence=0.95
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_task_with_valid_dependencies(self, validator, test_state):
        """Task with valid (non-circular) dependencies should be valid."""
        # Create task 4 that can depend on task 3
        task4 = test_state.create_task(
            project_id=1,
            task_data={
                "title": "Task 4",
                "description": "Test"
            }
        )

        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "id": task4.id,
                "title": "Task 4",
                "dependencies": [3]  # Depends on task 3
            }],
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_direct_self_dependency_invalid(self, validator):
        """Task depending on itself should be invalid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "id": 3,
                "title": "Task",
                "dependencies": [3]  # Self-dependency!
            }],
            confidence=0.8
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("itself" in error.lower() for error in result.errors)

    def test_new_task_with_dependencies_valid(self, validator):
        """New task (no ID) with dependencies should be valid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "title": "New Task",
                "dependencies": [1, 2]  # No ID, so can't be circular
            }],
            confidence=0.85
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_circular_dependency_a_depends_on_b_depends_on_a(self, validator, test_state):
        """A→B→A circular dependency should be invalid."""
        # Create task A (ID=4)
        task_a = test_state.create_task(

            project_id=1,

            task_data={

                "title": "Task A",

                "description": "Test"

            }

        )

        # Create task B (ID=5) that depends on A
        task_b = test_state.create_task(

            project_id=1,

            task_data={

                "title": "Task B",

                "description": "Test",

                "dependencies": [task_a.id]

            }

        )

        # Now try to make A depend on B (circular!)
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "id": task_a.id,
                "title": "Task A",
                "dependencies": [task_b.id]
            }],
            confidence=0.7
        )

        result = validator.validate(entities)
        # Should detect circular dependency
        assert result.valid is False
        assert any("circular" in error.lower() for error in result.errors)

    def test_empty_dependencies_list_valid(self, validator):
        """Task with empty dependencies list should be valid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "id": 3,
                "title": "Task",
                "dependencies": []  # Empty list
            }],
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_none_dependencies_valid(self, validator):
        """Task with None dependencies should be valid."""
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "id": 3,
                "title": "Task",
                "dependencies": None
            }],
            confidence=0.9
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_transitive_circular_dependency(self, validator, test_state):
        """A→B→C→A transitive circular dependency should be invalid."""
        # Create chain: A → B
        task_a = test_state.create_task(

            project_id=1,

            task_data={

                "title": "Task A",

                "description": "Test"

            }

        )

        task_b = test_state.create_task(


            project_id=1,


            task_data={


                "title": "Task B",


                "description": "Test",


                "dependencies": [task_a.id]


            }


        )

        task_c = test_state.create_task(


            project_id=1,


            task_data={


                "title": "Task C",


                "description": "Test",


                "dependencies": [task_b.id]


            }


        )

        # Now try A → C (which creates A→B→C→A cycle)
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "id": task_a.id,
                "title": "Task A",
                "dependencies": [task_c.id]
            }],
            confidence=0.6
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("circular" in error.lower() for error in result.errors)

    def test_multiple_dependencies_no_cycle_valid(self, validator, test_state):
        """Task with multiple dependencies (no cycle) should be valid."""
        task4 = test_state.create_task(

            project_id=1,

            task_data={

                "title": "Task 4",

                "description": "Test"

            }

        )

        task5 = test_state.create_task(


            project_id=1,


            task_data={


                "title": "Task 5",


                "description": "Test"


            }


        )

        entities = ExtractedEntities(
            entity_type="task",
            entities=[{
                "id": task5.id,
                "title": "Task 5",
                "dependencies": [task4.id, 3]  # Depends on task 4 and 3
            }],
            confidence=0.88
        )

        result = validator.validate(entities)
        assert result.valid is True

    def test_non_task_entity_types_ignore_dependencies(self, validator):
        """Non-task entities should not check dependencies."""
        # Epic with dependencies field (should be ignored)
        entities = ExtractedEntities(
            entity_type="epic",
            entities=[{
                "title": "Epic",
                "dependencies": [999]  # Ignored for epics
            }],
            confidence=0.9
        )

        result = validator.validate(entities)
        # Should be valid (dependencies ignored for non-tasks)
        assert result.valid is True


# Run with: pytest tests/test_nl_command_validator.py -v --cov=src/nl/command_validator
