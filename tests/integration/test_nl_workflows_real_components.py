"""Real component workflow tests (mock LLM only).

These tests use REAL StateManager, REAL NLCommandProcessor, REAL NLQueryHelper.
Only the LLM is mocked (with realistic responses).

Purpose: Validate NL command PARSING with real components.
Tests validate ParsedIntent structure, not execution results.
Execution will be tested in Phase 2 with real LLM.

Test Coverage:
- Project workflows (list, query stats)
- Epic/Story/Task creation
- Modification operations (update, delete)
- Bulk operations
- Query workflows
"""

import pytest
from src.core.models import TaskType, TaskStatus
from src.nl.types import EntityType, OperationType


class TestProjectWorkflowsRealComponents:
    """Project-level workflows with real components."""

    def test_list_projects_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'list all projects' → parsed as QUERY PROJECT command"""
        # Create 3 test projects
        for i in range(3):
            real_state_manager.create_project(
                name=f"Project {i}",
                description=f"Description {i}",
                working_dir=f"/tmp/project_{i}"
            )

        # Process NL command through REAL processor
        parsed_intent = real_nl_processor.process("list all projects")

        # Validate ParsedIntent structure (parsing, not execution)
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.QUERY
        assert EntityType.PROJECT in parsed_intent.operation_context.entity_types
        assert parsed_intent.confidence > 0.7

    def test_query_project_statistics_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'show project stats' → parsed as QUERY PROJECT command"""
        project = real_state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test_stats"
        )

        parsed_intent = real_nl_processor.process(
            "show me project statistics",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.QUERY
        assert parsed_intent.confidence > 0.7


class TestEpicStoryTaskCreationRealComponents:
    """Work item creation workflows with real components."""

    def test_create_epic_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'create epic for auth' → parsed as CREATE EPIC command"""
        project = real_state_manager.create_project(
            name="Test Project",
            description="desc",
            working_dir="/tmp/test_epic"
        )

        parsed_intent = real_nl_processor.process(
            "create epic for user authentication",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.CREATE
        assert EntityType.EPIC in parsed_intent.operation_context.entity_types
        assert parsed_intent.confidence > 0.7
        assert parsed_intent.requires_execution is True

    def test_create_story_in_epic_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'add story to epic 5' → parsed as CREATE STORY command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_story"
        )
        epic_id = real_state_manager.create_epic(
            project_id=project.id,
            title="Epic",
            description="Desc"
        )

        parsed_intent = real_nl_processor.process(
            f"add story for password reset to epic {epic_id}",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.CREATE
        assert EntityType.STORY in parsed_intent.operation_context.entity_types
        assert parsed_intent.confidence > 0.7

    def test_create_task_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'create task for login' → parsed as CREATE TASK command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_task"
        )

        parsed_intent = real_nl_processor.process(
            "create task for implementing login form",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.CREATE
        assert EntityType.TASK in parsed_intent.operation_context.entity_types
        assert parsed_intent.confidence > 0.7

    def test_create_multiple_tasks_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: Multiple create task commands parse correctly"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_multi"
        )

        # Parse 3 task creation commands
        for i in range(3):
            parsed_intent = real_nl_processor.process(
                f"create task for feature {i}",
                context={'project_id': project.id}
            )
            # Each should parse correctly
            assert parsed_intent.intent_type == 'COMMAND'
            assert parsed_intent.operation_context.operation == OperationType.CREATE
            assert EntityType.TASK in parsed_intent.operation_context.entity_types


class TestModificationWorkflowsRealComponents:
    """Update/delete workflows with real components."""

    def test_update_task_status_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'mark task 42 as complete' → parsed as UPDATE TASK command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_update"
        )
        task = real_state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test task',
                'description': 'Test task description',
                'task_type': TaskType.TASK
            }
        )

        parsed_intent = real_nl_processor.process(
            f"mark task {task.id} as complete",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.UPDATE
        assert EntityType.TASK in parsed_intent.operation_context.entity_types
        assert parsed_intent.operation_context.identifier == task.id
        assert parsed_intent.confidence > 0.7

    def test_update_task_description_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'update task description' → parsed as UPDATE TASK command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_update_desc"
        )
        task = real_state_manager.create_task(
            project_id=project.id,
            task_data={'title': 'Test task', 'description': 'Old description'}
        )

        parsed_intent = real_nl_processor.process(
            f"update task {task.id} description to New description",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.UPDATE
        assert EntityType.TASK in parsed_intent.operation_context.entity_types
        assert parsed_intent.operation_context.identifier == task.id

    def test_delete_single_task_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'delete task 42' → parsed as DELETE TASK command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_delete"
        )
        task = real_state_manager.create_task(
            project_id=project.id,
            task_data={'title': 'To Delete', 'description': 'Delete me'}
        )

        parsed_intent = real_nl_processor.process(
            f"delete task {task.id}",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.DELETE
        assert EntityType.TASK in parsed_intent.operation_context.entity_types
        assert parsed_intent.operation_context.identifier == task.id


class TestBulkOperationsRealComponents:
    """Bulk operations with real components."""

    def test_bulk_delete_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'delete all tasks' → parsed as DELETE TASK command (bulk)"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_bulk_delete"
        )

        parsed_intent = real_nl_processor.process(
            "delete all tasks",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.DELETE
        assert EntityType.TASK in parsed_intent.operation_context.entity_types

    def test_list_all_epics_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'list all epics' → parsed as QUERY EPIC command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_list_epics"
        )

        parsed_intent = real_nl_processor.process(
            "list all epics",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.QUERY
        assert EntityType.EPIC in parsed_intent.operation_context.entity_types


class TestQueryWorkflowsRealComponents:
    """Query workflows with real components."""

    def test_query_tasks_by_status_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'show completed tasks' → parsed as QUERY TASK command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_query_status"
        )

        parsed_intent = real_nl_processor.process(
            "show completed tasks",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.QUERY
        assert EntityType.TASK in parsed_intent.operation_context.entity_types

    def test_query_epic_stories_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'show stories in epic 5' → parsed as QUERY STORY command"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_epic_stories"
        )
        epic_id = real_state_manager.create_epic(
            project_id=project.id,
            title="Epic",
            description="Desc"
        )

        parsed_intent = real_nl_processor.process(
            f"show stories in epic {epic_id}",
            context={'project_id': project.id}
        )

        # Validate parsing
        assert parsed_intent.intent_type == 'COMMAND'
        assert parsed_intent.operation_context.operation == OperationType.QUERY
        assert EntityType.STORY in parsed_intent.operation_context.entity_types

    def test_query_task_count_workflow(self, real_nl_processor, real_state_manager):
        """Workflow: 'how many tasks' → parsed as QUERY or QUESTION"""
        project = real_state_manager.create_project(
            name="Test",
            description="Test",
            working_dir="/tmp/test_count"
        )

        parsed_intent = real_nl_processor.process(
            "how many tasks are there",
            context={'project_id': project.id}
        )

        # Validate parsing (could be COMMAND with QUERY or QUESTION intent)
        assert parsed_intent.intent_type in ['COMMAND', 'QUESTION']
        assert parsed_intent.confidence > 0.5
