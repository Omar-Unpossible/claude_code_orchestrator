"""Tests for NLQueryHelper (ADR-017 Story 3).

This test suite validates the query-only NLQueryHelper class that replaced
CommandExecutor's query functionality after ADR-017 refactor.

Test Categories:
1. Query Operations (SIMPLE/HIERARCHICAL/NEXT_STEPS/BACKLOG/ROADMAP)
2. Write Operation Rejection (CREATE/UPDATE/DELETE should raise error)
3. Edge Cases and Error Handling

Target: 30+ tests, ≥90% coverage
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.nl.nl_query_helper import NLQueryHelper, QueryResult, QueryException
from src.nl.types import (
    OperationContext,
    OperationType,
    EntityType,
    QueryType
)
from core.models import TaskType, TaskStatus, ProjectStatus


# Fixtures

@pytest.fixture
def mock_state_manager():
    """Create mock StateManager."""
    mock_sm = Mock()
    # Set up common mock responses
    mock_sm.list_projects.return_value = []
    mock_sm.list_tasks.return_value = []
    mock_sm.list_milestones.return_value = []
    mock_sm.get_epic_stories.return_value = []
    mock_sm.get_story_tasks.return_value = []
    return mock_sm


@pytest.fixture
def query_helper(mock_state_manager):
    """Create NLQueryHelper instance."""
    return NLQueryHelper(mock_state_manager, default_project_id=1)


# Test Category 1: Query Operations

class TestQueryOperations:
    """Test query execution for all query types."""

    def test_query_simple_projects(self, query_helper, mock_state_manager):
        """Test SIMPLE query for projects."""
        # Setup mock
        mock_project = Mock()
        mock_project.id = 1
        mock_project.project_name = "Test Project"
        mock_project.description = "Test description"
        mock_project.status = ProjectStatus.ACTIVE
        mock_state_manager.list_projects.return_value = [mock_project]

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.PROJECT],
            query_type=QueryType.SIMPLE,
            confidence=0.95,
            raw_input="list projects"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.query_type == 'simple'
        assert result.entity_type == 'project'
        assert result.results['count'] == 1
        assert len(result.results['entities']) == 1
        assert result.results['entities'][0]['name'] == "Test Project"

    def test_query_simple_tasks(self, query_helper, mock_state_manager):
        """Test SIMPLE query for tasks."""
        # Setup mock
        mock_task = Mock()
        mock_task.id = 5
        mock_task.title = "Implement feature X"
        mock_task.description = "Feature description"
        mock_task.status = TaskStatus.PENDING
        mock_task.priority = 3
        mock_state_manager.list_tasks.return_value = [mock_task]

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.SIMPLE,
            confidence=0.90,
            raw_input="list tasks"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.query_type == 'simple'
        assert result.entity_type == 'task'
        assert result.results['count'] == 1
        assert result.results['entities'][0]['title'] == "Implement feature X"

    def test_query_simple_epics(self, query_helper, mock_state_manager):
        """Test SIMPLE query for epics."""
        # Setup mock
        mock_epic = Mock()
        mock_epic.id = 10
        mock_epic.title = "User Authentication"
        mock_epic.description = "Auth system"
        mock_epic.status = TaskStatus.RUNNING
        mock_epic.priority = 1
        mock_state_manager.list_tasks.return_value = [mock_epic]

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.EPIC],
            query_type=QueryType.SIMPLE,
            confidence=0.92,
            raw_input="list epics"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.entity_type == 'epic'
        assert result.results['count'] == 1
        mock_state_manager.list_tasks.assert_called_with(task_type=TaskType.EPIC, limit=50)

    def test_query_simple_milestones(self, query_helper, mock_state_manager):
        """Test SIMPLE query for milestones."""
        # Setup mock
        mock_milestone = Mock()
        mock_milestone.id = 3
        mock_milestone.name = "MVP Release"
        mock_milestone.description = "Minimum viable product"
        mock_milestone.achieved = False  # Use achieved boolean instead of status
        mock_state_manager.list_milestones.return_value = [mock_milestone]

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.MILESTONE],
            query_type=QueryType.SIMPLE,
            confidence=0.88,
            raw_input="list milestones"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.entity_type == 'milestone'
        assert result.results['count'] == 1
        assert result.results['entities'][0]['name'] == "MVP Release"

    def test_query_hierarchical(self, query_helper, mock_state_manager):
        """Test HIERARCHICAL query (epic → story → task hierarchy)."""
        # Setup mocks
        mock_epic = Mock()
        mock_epic.id = 1
        mock_epic.title = "User Auth"
        mock_epic.status = TaskStatus.RUNNING

        mock_story = Mock()
        mock_story.id = 2
        mock_story.title = "Login Feature"
        mock_story.status = TaskStatus.PENDING

        mock_task = Mock()
        mock_task.id = 3
        mock_task.title = "Create login API"
        mock_task.status = TaskStatus.READY

        mock_state_manager.list_tasks.return_value = [mock_epic]
        mock_state_manager.get_epic_stories.return_value = [mock_story]
        mock_state_manager.get_story_tasks.return_value = [mock_task]

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.HIERARCHICAL,
            confidence=0.90,
            raw_input="show work plan"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.query_type == 'hierarchical'
        assert result.results['epic_count'] == 1
        hierarchy = result.results['hierarchy'][0]
        assert hierarchy['epic_title'] == "User Auth"
        assert len(hierarchy['stories']) == 1
        assert hierarchy['stories'][0]['story_title'] == "Login Feature"
        assert len(hierarchy['stories'][0]['tasks']) == 1

    def test_query_workplan_maps_to_hierarchical(self, query_helper, mock_state_manager):
        """Test that WORKPLAN query type maps to HIERARCHICAL."""
        mock_state_manager.list_tasks.return_value = []

        # Create query context with WORKPLAN
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.WORKPLAN,  # User-facing synonym
            confidence=0.90,
            raw_input="show workplan"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify it executed as hierarchical
        assert result.success is True
        assert result.query_type == 'hierarchical'

    def test_query_next_steps(self, query_helper, mock_state_manager):
        """Test NEXT_STEPS query (next pending tasks)."""
        # Setup mocks
        mock_task1 = Mock()
        mock_task1.id = 1
        mock_task1.title = "High priority task"
        mock_task1.status = TaskStatus.READY
        mock_task1.priority = 1
        mock_task1.project_id = 1
        mock_task1.task_type = TaskType.TASK

        mock_task2 = Mock()
        mock_task2.id = 2
        mock_task2.title = "Low priority task"
        mock_task2.status = TaskStatus.PENDING
        mock_task2.priority = 5
        mock_task2.project_id = 1
        mock_task2.task_type = TaskType.TASK

        mock_state_manager.list_tasks.return_value = [mock_task1, mock_task2]

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.NEXT_STEPS,
            confidence=0.92,
            raw_input="what's next"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.query_type == 'next_steps'
        assert result.results['count'] == 2
        # Should be sorted by priority (lower = higher priority)
        assert result.results['tasks'][0]['title'] == "High priority task"
        assert result.results['tasks'][1]['title'] == "Low priority task"

    def test_query_backlog(self, query_helper, mock_state_manager):
        """Test BACKLOG query (all pending tasks)."""
        # Setup mocks
        mock_tasks = []
        for i in range(15):
            mock_task = Mock()
            mock_task.id = i
            mock_task.title = f"Task {i}"
            mock_task.status = TaskStatus.PENDING
            mock_task.priority = 5
            mock_task.project_id = 1
            mock_task.task_type = TaskType.TASK
            mock_tasks.append(mock_task)

        mock_state_manager.list_tasks.return_value = mock_tasks

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.BACKLOG,
            confidence=0.88,
            raw_input="show backlog"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.query_type == 'backlog'
        assert result.results['count'] == 15
        assert len(result.results['tasks']) == 15

    def test_query_roadmap(self, query_helper, mock_state_manager):
        """Test ROADMAP query (milestones and epics)."""
        # Setup mocks
        mock_epic = Mock()
        mock_epic.id = 5
        mock_epic.title = "User Auth"
        mock_epic.status = TaskStatus.COMPLETED

        mock_milestone = Mock()
        mock_milestone.id = 1
        mock_milestone.name = "Phase 1 Complete"
        mock_milestone.required_epic_ids = [5]
        mock_milestone.achieved = False  # Use achieved boolean instead of status

        mock_state_manager.list_milestones.return_value = [mock_milestone]
        mock_state_manager.get_task.return_value = mock_epic

        # Create query context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.MILESTONE],
            query_type=QueryType.ROADMAP,
            confidence=0.90,
            raw_input="show roadmap"
        )

        # Execute query
        result = query_helper.execute(context, project_id=1)

        # Verify
        assert result.success is True
        assert result.query_type == 'roadmap'
        assert result.results['milestone_count'] == 1
        milestone_data = result.results['milestones'][0]
        assert milestone_data['milestone_name'] == "Phase 1 Complete"
        assert len(milestone_data['required_epics']) == 1
        assert milestone_data['required_epics'][0]['epic_title'] == "User Auth"


# Test Category 2: Write Operation Rejection

class TestWriteOperationRejection:
    """Test that write operations (CREATE/UPDATE/DELETE) are rejected."""

    def test_create_operation_raises_exception(self, query_helper):
        """Test CREATE operation raises QueryException."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_types=[EntityType.EPIC],
            parameters={'title': 'New Epic'},
            confidence=0.95,
            raw_input="create epic"
        )

        with pytest.raises(QueryException) as exc_info:
            query_helper.execute(context, project_id=1)

        assert "only handles QUERY operations" in str(exc_info.value)
        assert "IntentToTaskConverter" in str(exc_info.value)

    def test_update_operation_raises_exception(self, query_helper):
        """Test UPDATE operation raises QueryException."""
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_types=[EntityType.TASK],
            identifier=5,
            parameters={'status': 'COMPLETED'},
            confidence=0.90,
            raw_input="update task 5"
        )

        with pytest.raises(QueryException) as exc_info:
            query_helper.execute(context, project_id=1)

        assert "only handles QUERY operations" in str(exc_info.value)

    def test_delete_operation_raises_exception(self, query_helper):
        """Test DELETE operation raises QueryException."""
        context = OperationContext(
            operation=OperationType.DELETE,
            entity_types=[EntityType.EPIC],
            identifier=10,
            confidence=0.85,
            raw_input="delete epic 10"
        )

        with pytest.raises(QueryException) as exc_info:
            query_helper.execute(context, project_id=1)

        assert "only handles QUERY operations" in str(exc_info.value)


# Test Category 3: Edge Cases and Error Handling

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_default_query_type_is_simple(self, query_helper, mock_state_manager):
        """Test that query_type defaults to SIMPLE if not specified."""
        mock_state_manager.list_tasks.return_value = []

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            # No query_type specified
            confidence=0.90,
            raw_input="list tasks"
        )

        result = query_helper.execute(context, project_id=1)

        assert result.success is True
        assert result.query_type == 'simple'

    def test_uses_default_project_id(self, query_helper, mock_state_manager):
        """Test that default project_id is used when not specified."""
        mock_state_manager.list_projects.return_value = []

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.PROJECT],
            query_type=QueryType.SIMPLE,
            confidence=0.90,
            raw_input="list projects"
        )

        # Don't specify project_id
        result = query_helper.execute(context)

        assert result.success is True

    def test_unknown_query_type_returns_error(self, query_helper, mock_state_manager):
        """Test unknown query type returns error result."""
        # Create a mock OperationContext with invalid query_type
        # We'll have to bypass the enum validation
        context = Mock()
        context.operation = OperationType.QUERY
        context.entity_type = EntityType.TASK
        context.query_type = "INVALID_QUERY_TYPE"
        context.confidence = 0.90
        context.raw_input = "invalid query"

        result = query_helper.execute(context, project_id=1)

        assert result.success is False
        assert len(result.errors) > 0
        assert "Unknown query type" in result.errors[0]

    def test_query_filters_by_project_id(self, query_helper, mock_state_manager):
        """Test that queries filter by project_id correctly."""
        # Setup mocks for different projects
        task_proj1 = Mock()
        task_proj1.id = 1
        task_proj1.title = "Project 1 task"
        task_proj1.status = TaskStatus.PENDING
        task_proj1.project_id = 1
        task_proj1.priority = 5
        task_proj1.task_type = TaskType.TASK

        task_proj2 = Mock()
        task_proj2.id = 2
        task_proj2.title = "Project 2 task"
        task_proj2.status = TaskStatus.PENDING
        task_proj2.project_id = 2
        task_proj2.priority = 5
        task_proj2.task_type = TaskType.TASK

        mock_state_manager.list_tasks.return_value = [task_proj1, task_proj2]

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.NEXT_STEPS,
            confidence=0.90,
            raw_input="next steps"
        )

        # Query for project 1
        result = query_helper.execute(context, project_id=1)

        # Should only return tasks for project 1
        assert result.success is True
        assert result.results['count'] == 1
        assert result.results['tasks'][0]['title'] == "Project 1 task"

    def test_empty_result_returns_success(self, query_helper, mock_state_manager):
        """Test that empty query results still return success=True."""
        mock_state_manager.list_tasks.return_value = []

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.EPIC],
            query_type=QueryType.SIMPLE,
            confidence=0.90,
            raw_input="list epics"
        )

        result = query_helper.execute(context, project_id=1)

        assert result.success is True
        assert result.results['count'] == 0
        assert len(result.results['entities']) == 0
