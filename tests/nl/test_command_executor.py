"""Unit tests for CommandExecutor (ADR-016 Story 5 Task 3.2).

Tests the updated CommandExecutor with OperationContext API covering:
- CREATE operations for different entity types (5 tests)
- UPDATE operations with identifier resolution (4 tests)
- DELETE operations (2 tests)
- QUERY operations: SIMPLE, HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP (5 tests)
- Helper methods (identifier resolution, entity updates) (3 tests)
- Backward compatibility with execute_legacy() (1 test)

Target: 90%+ code coverage for CommandExecutor
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

from src.nl.command_executor import (
    CommandExecutor,
    ExecutionResult,
    ExecutionException
)
from src.nl.types import OperationContext, OperationType, EntityType, QueryType
from core.state import StateManager
from core.models import TaskType, TaskStatus


@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager for testing."""
    state = Mock()  # Don't use spec to allow any attribute
    state.db = Mock()
    state.db.commit = Mock()
    return state


@pytest.fixture
def executor(mock_state_manager):
    """Create CommandExecutor with mock StateManager."""
    return CommandExecutor(mock_state_manager, default_project_id=1)


class TestExecuteCreate:
    """Test CREATE operation execution."""

    def test_create_project(self, executor, mock_state_manager):
        """Test CREATE PROJECT operation."""
        mock_state_manager.create_project.return_value = 5

        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.PROJECT,
            parameters={"title": "New Project", "description": "Test project"},
            confidence=0.95
        )

        result = executor.execute(context)

        assert result.success
        assert result.created_ids == [5]
        assert result.results['operation'] == 'create'
        assert result.results['entity_type'] == 'project'
        mock_state_manager.create_project.assert_called_once()

    def test_create_epic(self, executor, mock_state_manager):
        """Test CREATE EPIC operation."""
        mock_state_manager.create_epic.return_value = 10

        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.EPIC,
            parameters={"title": "User Authentication", "description": "OAuth + MFA"},
            confidence=0.92
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.created_ids == [10]
        assert result.results['entity_id'] == 10
        mock_state_manager.create_epic.assert_called_once()

    def test_create_story(self, executor, mock_state_manager):
        """Test CREATE STORY operation."""
        mock_state_manager.create_story.return_value = 15

        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.STORY,
            parameters={"title": "Login Page", "epic_id": 10, "description": "Implement login"},
            confidence=0.90
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.created_ids == [15]
        mock_state_manager.create_story.assert_called_once_with(
            project_id=1,
            epic_id=10,
            title="Login Page",
            description="Implement login"
        )

    def test_create_task(self, executor, mock_state_manager):
        """Test CREATE TASK operation."""
        mock_task = Mock()
        mock_task.id = 20
        mock_task.title = "Implement password validation"
        mock_state_manager.create_task.return_value = mock_task

        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={"title": "Implement password validation", "priority": 5},
            confidence=0.88
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.created_ids == [20]

    def test_create_milestone(self, executor, mock_state_manager):
        """Test CREATE MILESTONE operation."""
        mock_state_manager.create_milestone.return_value = 25

        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.MILESTONE,
            parameters={
                "title": "v1.0 Release",
                "description": "First release",
                "required_epic_ids": [10, 11, 12]
            },
            confidence=0.93
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.created_ids == [25]
        mock_state_manager.create_milestone.assert_called_once()


class TestExecuteUpdate:
    """Test UPDATE operation execution."""

    def test_update_project_by_id(self, executor, mock_state_manager):
        """Test UPDATE PROJECT by ID."""
        mock_project = Mock()
        mock_project.id = 1
        mock_project.project_name = "Test Project"
        mock_project.status = TaskStatus.RUNNING
        mock_state_manager.get_project.return_value = mock_project

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT,
            identifier=1,
            parameters={"status": "INACTIVE"},
            confidence=0.95
        )

        result = executor.execute(context, confirmed=True)

        assert result.success
        assert result.results['operation'] == 'update'
        assert result.results['entity_id'] == 1
        assert 'status' in result.results['updated_fields']
        assert mock_project.status == TaskStatus.CANCELLED  # INACTIVE maps to CANCELLED

    def test_update_project_by_name(self, executor, mock_state_manager):
        """Test UPDATE PROJECT by name."""
        mock_project1 = Mock()
        mock_project1.id = 1
        mock_project1.project_name = "Other Project"

        mock_project2 = Mock()
        mock_project2.id = 2
        mock_project2.project_name = "Manual Tetris Test"
        mock_project2.status = TaskStatus.RUNNING

        mock_state_manager.get_all_projects.return_value = [mock_project1, mock_project2]
        mock_state_manager.get_project.return_value = mock_project2

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT,
            identifier="manual tetris test",  # Case-insensitive
            parameters={"status": "INACTIVE"},
            confidence=0.92
        )

        result = executor.execute(context, confirmed=True)

        assert result.success
        assert result.results['entity_id'] == 2
        assert mock_project2.status == TaskStatus.CANCELLED  # INACTIVE maps to CANCELLED

    def test_update_task_by_id(self, executor, mock_state_manager):
        """Test UPDATE TASK by ID."""
        mock_task = Mock()
        mock_task.id = 10
        mock_task.title = "Old Title"
        mock_task.status = TaskStatus.RUNNING
        mock_state_manager.get_task.return_value = mock_task

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier=10,
            parameters={"status": "COMPLETED", "title": "New Title"},
            confidence=0.90
        )

        result = executor.execute(context, confirmed=True)

        assert result.success
        assert mock_task.status == TaskStatus.COMPLETED
        assert mock_task.title == "New Title"

    def test_update_entity_not_found(self, executor, mock_state_manager):
        """Test UPDATE fails when entity not found."""
        mock_state_manager.get_task.return_value = None

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier=999,  # Non-existent
            parameters={"status": "COMPLETED"},
            confidence=0.85
        )

        result = executor.execute(context, confirmed=True)

        assert not result.success
        assert "not found" in result.errors[0].lower()


class TestExecuteDelete:
    """Test DELETE operation execution."""

    def test_delete_task_by_id(self, executor, mock_state_manager):
        """Test DELETE TASK by ID."""
        context = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.TASK,
            identifier=10,
            parameters={},
            confidence=0.92
        )

        # Mock database query/delete
        mock_query = Mock()
        mock_state_manager.db.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.delete.return_value = 1

        result = executor.execute(context, confirmed=True)

        assert result.success
        assert result.results['operation'] == 'delete'
        assert result.results['entity_id'] == 10

    def test_delete_requires_confirmation(self, executor):
        """Test DELETE requires confirmation."""
        context = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.TASK,
            identifier=10,
            parameters={},
            confidence=0.90
        )

        result = executor.execute(context, confirmed=False)

        assert not result.success
        assert result.confirmation_required
        assert "requires confirmation" in result.errors[0]


class TestExecuteQuery:
    """Test QUERY operation execution with different query types."""

    def test_query_simple_projects(self, executor, mock_state_manager):
        """Test SIMPLE QUERY for projects."""
        mock_project1 = Mock()
        mock_project1.id = 1
        mock_project1.project_name = "Project A"
        mock_project1.description = "Description A"

        mock_project2 = Mock()
        mock_project2.id = 2
        mock_project2.project_name = "Project B"
        mock_project2.description = "Description B"

        mock_state_manager.get_all_projects.return_value = [mock_project1, mock_project2]

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT,
            query_type=QueryType.SIMPLE,
            confidence=0.95
        )

        result = executor.execute(context)

        assert result.success
        assert result.results['query_type'] == 'simple'
        assert result.results['count'] == 2
        assert len(result.results['entities']) == 2

    def test_query_simple_tasks(self, executor, mock_state_manager):
        """Test SIMPLE QUERY for tasks."""
        mock_task1 = Mock()
        mock_task1.id = 10
        mock_task1.title = "Task 1"
        mock_task1.description = "Desc 1"
        mock_task1.status = TaskStatus.RUNNING

        mock_task2 = Mock()
        mock_task2.id = 11
        mock_task2.title = "Task 2"
        mock_task2.description = "Desc 2"
        mock_task2.status = TaskStatus.COMPLETED

        mock_state_manager.list_tasks.return_value = [mock_task1, mock_task2]

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK,
            query_type=QueryType.SIMPLE,
            confidence=0.92
        )

        result = executor.execute(context)

        assert result.success
        assert result.results['entity_type'] == 'task'
        assert result.results['count'] == 2

    def test_query_hierarchical(self, executor, mock_state_manager):
        """Test HIERARCHICAL/WORKPLAN query."""
        # Mock epic
        mock_epic = Mock()
        mock_epic.id = 5
        mock_epic.title = "User Auth Epic"
        mock_epic.status = TaskStatus.RUNNING

        # Mock stories
        mock_story1 = Mock()
        mock_story1.id = 10
        mock_story1.title = "Login Story"
        mock_story1.status = TaskStatus.RUNNING

        # Mock tasks
        mock_task1 = Mock()
        mock_task1.id = 20
        mock_task1.title = "Task 1"
        mock_task1.status = TaskStatus.RUNNING

        mock_state_manager.list_tasks.return_value = [mock_epic]
        mock_state_manager.get_epic_stories.return_value = [mock_story1]
        mock_state_manager.get_story_tasks.return_value = [mock_task1]

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK,
            query_type=QueryType.HIERARCHICAL,
            confidence=0.90
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.results['query_type'] == 'hierarchical'
        assert result.results['epic_count'] == 1
        assert len(result.results['hierarchy']) == 1
        assert result.results['hierarchy'][0]['epic_id'] == 5

    def test_query_workplan_maps_to_hierarchical(self, executor, mock_state_manager):
        """Test WORKPLAN query type maps to HIERARCHICAL."""
        mock_state_manager.list_tasks.return_value = []
        mock_state_manager.get_epic_stories.return_value = []

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK,
            query_type=QueryType.WORKPLAN,  # Should map to HIERARCHICAL
            confidence=0.88
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.results['query_type'] == 'hierarchical'

    def test_query_next_steps(self, executor, mock_state_manager):
        """Test NEXT_STEPS query."""
        mock_task1 = Mock()
        mock_task1.id = 10
        mock_task1.title = "High Priority Task"
        mock_task1.status = TaskStatus.RUNNING
        mock_task1.priority = 10
        mock_task1.project_id = 1
        mock_task1.task_type = TaskType.TASK

        mock_task2 = Mock()
        mock_task2.id = 11
        mock_task2.title = "Low Priority Task"
        mock_task2.status = TaskStatus.PENDING
        mock_task2.priority = 3
        mock_task2.project_id = 1
        mock_task2.task_type = TaskType.TASK

        mock_state_manager.list_tasks.return_value = [mock_task1, mock_task2]

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK,
            query_type=QueryType.NEXT_STEPS,
            confidence=0.93
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.results['query_type'] == 'next_steps'
        assert result.results['count'] == 2
        # Should be sorted by priority (high first)
        assert result.results['tasks'][0]['id'] == 10

    def test_query_backlog(self, executor, mock_state_manager):
        """Test BACKLOG query."""
        mock_task1 = Mock()
        mock_task1.id = 10
        mock_task1.title = "Backlog Task 1"
        mock_task1.status = TaskStatus.RUNNING
        mock_task1.priority = 5
        mock_task1.project_id = 1
        mock_task1.task_type = TaskType.TASK

        mock_state_manager.list_tasks.return_value = [mock_task1]

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK,
            query_type=QueryType.BACKLOG,
            confidence=0.90
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.results['query_type'] == 'backlog'
        assert result.results['count'] == 1

    def test_query_roadmap(self, executor, mock_state_manager):
        """Test ROADMAP query."""
        # Mock milestone
        mock_milestone = Mock()
        mock_milestone.id = 1
        mock_milestone.name = "v1.0 Release"
        mock_milestone.required_epic_ids = [5, 6]

        # Mock epics
        mock_epic1 = Mock()
        mock_epic1.id = 5
        mock_epic1.title = "Epic 1"
        mock_epic1.status = TaskStatus.RUNNING

        mock_epic2 = Mock()
        mock_epic2.id = 6
        mock_epic2.title = "Epic 2"
        mock_epic2.status = TaskStatus.COMPLETED

        mock_state_manager.list_milestones.return_value = [mock_milestone]
        mock_state_manager.get_task.side_effect = lambda eid: mock_epic1 if eid == 5 else mock_epic2

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.MILESTONE,
            query_type=QueryType.ROADMAP,
            confidence=0.92
        )

        result = executor.execute(context, project_id=1)

        assert result.success
        assert result.results['query_type'] == 'roadmap'
        assert result.results['milestone_count'] == 1
        assert len(result.results['milestones'][0]['required_epics']) == 2


class TestHelperMethods:
    """Test helper methods for operation handling."""

    def test_resolve_identifier_project_by_name(self, executor, mock_state_manager):
        """Test resolving project identifier by name."""
        mock_project = Mock()
        mock_project.id = 5
        mock_project.project_name = "Test Project"

        mock_state_manager.get_all_projects.return_value = [mock_project]

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT,
            identifier="test project",
            parameters={"status": "INACTIVE"}
        )

        entity_id = executor._resolve_identifier_to_id(context, project_id=1)

        assert entity_id == 5

    def test_resolve_identifier_task_by_name(self, executor, mock_state_manager):
        """Test resolving task identifier by name (partial match)."""
        mock_task = Mock()
        mock_task.id = 10
        mock_task.title = "Implement login feature"

        mock_state_manager.list_tasks.return_value = [mock_task]

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier="login",  # Partial match
            parameters={"status": "COMPLETED"}
        )

        entity_id = executor._resolve_identifier_to_id(context, project_id=1)

        assert entity_id == 10

    def test_resolve_identifier_returns_int_directly(self, executor):
        """Test resolving identifier when already an int."""
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier=42,  # Already an int
            parameters={"status": "COMPLETED"}
        )

        entity_id = executor._resolve_identifier_to_id(context, project_id=1)

        assert entity_id == 42


class TestBackwardCompatibility:
    """Test backward compatibility with legacy API."""

    def test_execute_legacy_deprecation_warning(self, executor, mock_state_manager):
        """Test execute_legacy() emits deprecation warning."""
        mock_task = Mock()
        mock_task.id = 10
        mock_state_manager.create_task.return_value = mock_task

        validated_command = {
            'entity_type': 'task',
            'entities': [{'title': 'Test Task', 'description': 'Test'}]
        }

        with pytest.warns(DeprecationWarning, match="execute_legacy.*deprecated"):
            result = executor.execute_legacy(validated_command)

        # Should still work
        assert isinstance(result, ExecutionResult)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
