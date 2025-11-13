"""Tests for IntentToTaskConverter (ADR-017 Story 2).

This test suite validates the conversion of parsed NL intents (OperationContext)
into Task objects for orchestrator execution.

Test Categories:
1. Operation Mapping (8 tests): CREATE/UPDATE/DELETE/QUERY for different entity types
2. Parameter Extraction (5 tests): Correct mapping of parsed params → task data
3. NL Context Enrichment (4 tests): Metadata attached correctly
4. Error Handling (4 tests): Missing params, invalid entity types
5. Integration (4+ tests): End-to-end with real OperationContext

Target: 25+ tests, ≥90% coverage
"""

import pytest
from datetime import datetime, UTC

from src.orchestration.intent_to_task_converter import (
    IntentToTaskConverter,
    IntentConversionException
)
from src.core.state import StateManager
from src.core.models import Task, TaskType, TaskStatus
from src.nl.types import (
    OperationContext,
    OperationType,
    EntityType,
    QueryType
)


# Fixtures

@pytest.fixture
def state_manager(tmp_path):
    """Create StateManager with temporary database."""
    StateManager.reset_instance()  # Reset singleton first
    db_path = tmp_path / "test.db"
    sm = StateManager.get_instance(f"sqlite:///{db_path}")
    yield sm
    sm.close()
    StateManager.reset_instance()


@pytest.fixture
def test_project(state_manager):
    """Create a test project."""
    project = state_manager.create_project(
        name="Test Project",
        description="Test project for intent conversion",
        working_dir="/tmp/test"
    )
    return project


@pytest.fixture
def converter(state_manager):
    """Create IntentToTaskConverter instance."""
    return IntentToTaskConverter(state_manager)


# Test Category 1: Operation Mapping (8 tests)

class TestOperationMapping:
    """Test mapping of operations to task data."""

    def test_create_epic_operation(self, converter, test_project):
        """Test CREATE operation for EPIC entity."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.EPIC,
            parameters={
                'title': 'User Authentication System',
                'description': 'Complete auth with OAuth and MFA',
                'priority': 3
            },
            confidence=0.95,
            raw_input='create epic for user authentication'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create epic for user authentication'
        )

        assert task is not None
        assert task.title == 'Create epic: User Authentication System'
        assert 'Complete auth with OAuth and MFA' in task.description
        assert task.task_type == TaskType.EPIC
        assert task.priority == 3
        assert task.status == TaskStatus.PENDING

    def test_create_story_operation(self, converter, test_project, state_manager):
        """Test CREATE operation for STORY entity."""
        # Create parent epic first
        epic = state_manager.create_epic(
            project_id=test_project.id,
            title='User Auth',
            description='Authentication features'
        )

        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.STORY,
            parameters={
                'title': 'User Login',
                'description': 'Email/password login',
                'epic_id': epic,
                'priority': 5
            },
            confidence=0.92,
            raw_input='add story for user login'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='add story for user login'
        )

        assert task.title == 'Create story: User Login'
        assert task.task_type == TaskType.STORY
        assert task.epic_id == epic

    def test_create_task_operation(self, converter, test_project):
        """Test CREATE operation for TASK entity."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={
                'title': 'Implement password hashing',
                'description': 'Use bcrypt with salt rounds=10',
                'priority': 7
            },
            confidence=0.88,
            raw_input='create task for password hashing'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create task for password hashing'
        )

        assert task.title == 'Create task: Implement password hashing'
        assert task.task_type == TaskType.TASK
        assert 'bcrypt' in task.description

    def test_create_subtask_operation(self, converter, test_project, state_manager):
        """Test CREATE operation for SUBTASK entity."""
        # Create parent task first
        parent_task_data = {
            'title': 'Setup authentication',
            'description': 'Auth setup',
            'task_type': TaskType.TASK
        }
        parent = state_manager.create_task(test_project.id, parent_task_data)

        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.SUBTASK,
            parameters={
                'title': 'Define User model',
                'description': 'SQLAlchemy model with email, password_hash',
                'parent_task_id': parent.id
            },
            confidence=0.90,
            raw_input='add subtask to define user model'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='add subtask to define user model'
        )

        assert task.title == 'Create subtask: Define User model'
        assert task.task_type == TaskType.SUBTASK
        assert task.parent_task_id == parent.id

    def test_update_operation(self, converter, test_project):
        """Test UPDATE operation mapping."""
        parsed_intent = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier='authentication-setup',
            parameters={
                'status': 'COMPLETED',
                'priority': 1
            },
            confidence=0.85,
            raw_input='mark authentication-setup as completed'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='mark authentication-setup as completed'
        )

        assert 'Update task' in task.title
        assert 'authentication-setup' in task.title
        assert 'status, priority' in task.title or 'priority, status' in task.title
        assert 'COMPLETED' in task.description
        assert task.context['update_target']['entity_type'] == 'task'
        assert task.context['update_target']['identifier'] == 'authentication-setup'

    def test_delete_operation(self, converter, test_project):
        """Test DELETE operation mapping."""
        parsed_intent = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.EPIC,
            identifier='old-feature',
            parameters={},
            confidence=0.80,
            raw_input='delete epic old-feature'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='delete epic old-feature'
        )

        assert 'Delete epic' in task.title
        assert 'old-feature' in task.title
        assert '⚠️ WARNING' in task.description
        assert 'permanently remove' in task.description
        assert task.context['delete_target']['entity_type'] == 'epic'
        assert task.context['delete_target']['identifier'] == 'old-feature'

    def test_query_operation_raises_exception(self, converter, test_project):
        """Test QUERY operation raises exception (should not create tasks)."""
        parsed_intent = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK,
            query_type=QueryType.SIMPLE,
            confidence=0.90,
            raw_input='show all tasks'
        )

        with pytest.raises(IntentConversionException) as exc_info:
            converter.convert(
                parsed_intent=parsed_intent,
                project_id=test_project.id,
                original_message='show all tasks'
            )

        assert 'QUERY operations should not be converted to tasks' in str(exc_info.value)

    def test_create_with_dependencies(self, converter, test_project, state_manager):
        """Test CREATE operation with task dependencies."""
        # Create dependency tasks
        dep1_data = {'title': 'Setup database', 'description': 'DB setup'}
        dep2_data = {'title': 'Create models', 'description': 'Model creation'}
        dep1 = state_manager.create_task(test_project.id, dep1_data)
        dep2 = state_manager.create_task(test_project.id, dep2_data)

        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={
                'title': 'Write migrations',
                'description': 'Alembic migrations',
                'dependencies': [dep1.id, dep2.id]
            },
            confidence=0.87,
            raw_input='create task for migrations depending on db and models'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create task for migrations'
        )

        assert task.dependencies == [dep1.id, dep2.id]
        assert 'dependencies' in task.description.lower()


# Test Category 2: Parameter Extraction (5 tests)

class TestParameterExtraction:
    """Test correct extraction and mapping of parameters."""

    def test_title_extraction(self, converter, test_project):
        """Test title parameter extraction."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'My Awesome Task'},
            confidence=0.90,
            raw_input='create task my awesome task'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create task my awesome task'
        )

        assert 'My Awesome Task' in task.title

    def test_priority_extraction(self, converter, test_project):
        """Test priority parameter extraction and default."""
        # Explicit priority
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'High priority task', 'priority': 2},
            confidence=0.90,
            raw_input='create high priority task'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create high priority task'
        )

        assert task.priority == 2

        # Default priority (5)
        parsed_intent_default = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'Normal task'},
            confidence=0.90,
            raw_input='create normal task'
        )

        task_default = converter.convert(
            parsed_intent=parsed_intent_default,
            project_id=test_project.id,
            original_message='create normal task'
        )

        assert task_default.priority == 5

    def test_description_extraction(self, converter, test_project):
        """Test description parameter extraction."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.EPIC,
            parameters={
                'title': 'Payment System',
                'description': 'Stripe integration with webhooks and subscriptions'
            },
            confidence=0.92,
            raw_input='create epic for payment system'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create epic for payment system'
        )

        assert 'Stripe integration' in task.description
        assert 'webhooks and subscriptions' in task.description

    def test_hierarchical_relationship_extraction(self, converter, test_project, state_manager):
        """Test extraction of epic_id, story_id, parent_task_id."""
        # Create parent items
        epic = state_manager.create_epic(
            test_project.id,
            'Parent Epic',
            'Epic description'
        )
        story_data = {
            'title': 'Parent Story',
            'description': 'Story description',
            'task_type': TaskType.STORY,
            'epic_id': epic
        }
        story = state_manager.create_task(test_project.id, story_data)

        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={
                'title': 'Child Task',
                'epic_id': epic,
                'story_id': story.id
            },
            confidence=0.88,
            raw_input='create task under story'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create task under story'
        )

        assert task.epic_id == epic
        assert task.story_id == story.id

    def test_update_field_extraction(self, converter, test_project):
        """Test extraction of update fields."""
        parsed_intent = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier=123,
            parameters={
                'status': 'RUNNING',
                'priority': 1,
                'description': 'Updated description'
            },
            confidence=0.85,
            raw_input='update task 123'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='update task 123'
        )

        update_target = task.context['update_target']
        assert update_target['fields']['status'] == 'RUNNING'
        assert update_target['fields']['priority'] == 1
        assert update_target['fields']['description'] == 'Updated description'


# Test Category 3: NL Context Enrichment (4 tests)

class TestNLContextEnrichment:
    """Test NL context metadata attachment."""

    def test_nl_context_attached(self, converter, test_project):
        """Test that nl_context is attached to task."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'Test Task'},
            confidence=0.92,
            raw_input='create a test task'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create a test task'
        )

        assert task.context is not None
        assert 'nl_context' in task.context

    def test_nl_context_source(self, converter, test_project):
        """Test nl_context source field."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'Test'},
            confidence=0.90,
            raw_input='test'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='test'
        )

        assert task.context['nl_context']['source'] == 'natural_language'

    def test_nl_context_confidence(self, converter, test_project):
        """Test nl_context preserves intent confidence."""
        confidence_value = 0.876
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.EPIC,
            parameters={'title': 'Test Epic'},
            confidence=confidence_value,
            raw_input='create epic'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create epic'
        )

        assert task.context['nl_context']['intent_confidence'] == confidence_value

    def test_nl_context_metadata_complete(self, converter, test_project):
        """Test nl_context contains all required metadata."""
        original_msg = 'create a high priority task for testing'
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'Testing Task', 'priority': 2},
            confidence=0.94,
            raw_input=original_msg
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message=original_msg
        )

        nl_ctx = task.context['nl_context']
        assert nl_ctx['source'] == 'natural_language'
        assert nl_ctx['original_message'] == original_msg
        assert nl_ctx['intent_confidence'] == 0.94
        assert nl_ctx['operation_type'] == 'create'
        assert nl_ctx['entity_type'] == 'task'
        assert 'parsed_at' in nl_ctx
        # Validate ISO format timestamp
        datetime.fromisoformat(nl_ctx['parsed_at'].replace('Z', '+00:00'))


# Test Category 4: Error Handling (4 tests)

class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_missing_title_raises_exception(self, converter, test_project):
        """Test CREATE without title raises exception."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={},  # Missing title
            confidence=0.80,
            raw_input='create task'
        )

        with pytest.raises(IntentConversionException) as exc_info:
            converter.convert(
                parsed_intent=parsed_intent,
                project_id=test_project.id,
                original_message='create task'
            )

        assert 'title' in str(exc_info.value).lower()

    def test_update_without_identifier_raises_exception(self, converter, test_project):
        """Test UPDATE without identifier raises exception."""
        with pytest.raises(ValueError) as exc_info:
            OperationContext(
                operation=OperationType.UPDATE,
                entity_type=EntityType.TASK,
                identifier=None,  # Missing identifier
                parameters={'status': 'COMPLETED'},
                confidence=0.85,
                raw_input='update task'
            )

        assert 'requires an identifier' in str(exc_info.value)

    def test_delete_without_identifier_raises_exception(self, converter, test_project):
        """Test DELETE without identifier raises exception."""
        with pytest.raises(ValueError) as exc_info:
            OperationContext(
                operation=OperationType.DELETE,
                entity_type=EntityType.EPIC,
                identifier=None,  # Missing identifier
                parameters={},
                confidence=0.80,
                raw_input='delete epic'
            )

        assert 'requires an identifier' in str(exc_info.value)

    def test_invalid_project_id_raises_exception(self, converter):
        """Test invalid project_id raises exception."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'Test'},
            confidence=0.90,
            raw_input='test'
        )

        # Non-existent project
        with pytest.raises(IntentConversionException) as exc_info:
            converter.convert(
                parsed_intent=parsed_intent,
                project_id=99999,
                original_message='test'
            )

        assert 'does not exist' in str(exc_info.value)

    def test_update_without_fields_raises_exception(self, converter, test_project):
        """Test UPDATE without any fields to update raises exception."""
        parsed_intent = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier='task-123',
            parameters={},  # No fields to update
            confidence=0.85,
            raw_input='update task-123'
        )

        with pytest.raises(IntentConversionException) as exc_info:
            converter.convert(
                parsed_intent=parsed_intent,
                project_id=test_project.id,
                original_message='update task-123'
            )

        assert 'at least one field to update' in str(exc_info.value)


# Test Category 5: Integration Tests (4+ tests)

class TestIntegration:
    """End-to-end integration tests with real OperationContext."""

    def test_full_create_epic_workflow(self, converter, test_project, state_manager):
        """Test complete workflow: parse intent → convert → verify in DB."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.EPIC,
            parameters={
                'title': 'E-commerce Platform',
                'description': 'Build complete e-commerce with cart, checkout, payments',
                'priority': 1
            },
            confidence=0.95,
            raw_input='create epic for e-commerce platform'
        )

        # Convert intent to task
        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create epic for e-commerce platform'
        )

        # Verify task created in database
        db_task = state_manager.get_task(task.id)
        assert db_task is not None
        assert db_task.id == task.id
        assert db_task.task_type == TaskType.EPIC
        assert db_task.priority == 1
        assert 'E-commerce Platform' in db_task.title

        # Verify NL context persisted
        assert db_task.context['nl_context']['source'] == 'natural_language'
        assert db_task.context['nl_context']['intent_confidence'] == 0.95

    def test_full_create_story_under_epic_workflow(self, converter, test_project, state_manager):
        """Test creating story under epic with full workflow."""
        # Create epic first
        epic = state_manager.create_epic(
            test_project.id,
            'Shopping Cart',
            'Shopping cart functionality'
        )

        # Create story under epic
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.STORY,
            parameters={
                'title': 'Add to Cart',
                'description': 'User can add items to shopping cart',
                'epic_id': epic,
                'priority': 3
            },
            confidence=0.91,
            raw_input='add story for add to cart feature'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='add story for add to cart feature'
        )

        # Verify relationships
        db_task = state_manager.get_task(task.id)
        assert db_task.task_type == TaskType.STORY
        assert db_task.epic_id == epic

    def test_full_update_workflow(self, converter, test_project, state_manager):
        """Test UPDATE operation end-to-end."""
        parsed_intent = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier='payment-integration',
            parameters={
                'status': 'RUNNING',
                'priority': 1,
                'description': 'Integrating Stripe payment gateway'
            },
            confidence=0.88,
            raw_input='update payment-integration to running priority 1'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='update payment-integration to running priority 1'
        )

        # Verify update metadata
        assert 'update_target' in task.context
        update_info = task.context['update_target']
        assert update_info['identifier'] == 'payment-integration'
        assert update_info['fields']['status'] == 'RUNNING'
        assert update_info['fields']['priority'] == 1

    def test_full_delete_workflow(self, converter, test_project):
        """Test DELETE operation end-to-end."""
        parsed_intent = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.STORY,
            identifier=42,
            parameters={},
            confidence=0.79,
            raw_input='delete story 42'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='delete story 42'
        )

        # Verify delete metadata
        assert 'delete_target' in task.context
        delete_info = task.context['delete_target']
        assert delete_info['identifier'] == 42
        assert delete_info['entity_type'] == 'story'
        assert '⚠️ WARNING' in task.description

    def test_complex_hierarchy_workflow(self, converter, test_project, state_manager):
        """Test creating full hierarchy: Epic → Story → Task → Subtask."""
        # 1. Create Epic
        epic_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.EPIC,
            parameters={
                'title': 'User Management',
                'description': 'Complete user CRUD'
            },
            confidence=0.95,
            raw_input='create user management epic'
        )
        epic_task = converter.convert(epic_intent, test_project.id, 'create epic')
        assert epic_task.task_type == TaskType.EPIC

        # 2. Create Story under Epic
        story_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.STORY,
            parameters={
                'title': 'User Registration',
                'epic_id': epic_task.id
            },
            confidence=0.92,
            raw_input='create story'
        )
        story_task = converter.convert(story_intent, test_project.id, 'create story')
        assert story_task.task_type == TaskType.STORY
        assert story_task.epic_id == epic_task.id

        # 3. Create Task under Story
        task_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={
                'title': 'Create registration endpoint',
                'story_id': story_task.id,
                'epic_id': epic_task.id
            },
            confidence=0.89,
            raw_input='create task'
        )
        task_task = converter.convert(task_intent, test_project.id, 'create task')
        assert task_task.task_type == TaskType.TASK
        assert task_task.story_id == story_task.id

        # 4. Create Subtask under Task
        subtask_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.SUBTASK,
            parameters={
                'title': 'Add input validation',
                'parent_task_id': task_task.id
            },
            confidence=0.87,
            raw_input='create subtask'
        )
        subtask_task = converter.convert(subtask_intent, test_project.id, 'create subtask')
        assert subtask_task.task_type == TaskType.SUBTASK
        assert subtask_task.parent_task_id == task_task.id

        # Verify hierarchy in database
        db_epic = state_manager.get_task(epic_task.id)
        db_story = state_manager.get_task(story_task.id)
        db_task = state_manager.get_task(task_task.id)
        db_subtask = state_manager.get_task(subtask_task.id)

        assert db_epic.task_type == TaskType.EPIC
        assert db_story.epic_id == db_epic.id
        assert db_task.story_id == db_story.id
        assert db_subtask.parent_task_id == db_task.id


# Edge Cases and Additional Tests

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_title_raises_exception(self, converter, test_project):
        """Test CREATE with empty title (whitespace only)."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': '   '},  # Whitespace only
            confidence=0.80,
            raw_input='create task'
        )

        with pytest.raises(IntentConversionException):
            converter.convert(
                parsed_intent=parsed_intent,
                project_id=test_project.id,
                original_message='create task'
            )

    def test_very_long_title(self, converter, test_project):
        """Test handling of very long titles."""
        long_title = 'A' * 500
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': long_title},
            confidence=0.85,
            raw_input='create task with long title'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='create task'
        )

        assert long_title in task.title

    def test_special_characters_in_title(self, converter, test_project):
        """Test special characters in title."""
        special_title = "Fix bug: API returns 500 for /users/{id}"
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': special_title},
            confidence=0.90,
            raw_input='fix bug'
        )

        task = converter.convert(
            parsed_intent=parsed_intent,
            project_id=test_project.id,
            original_message='fix bug'
        )

        assert special_title in task.title

    def test_invalid_operation_context_type(self, converter, test_project):
        """Test passing non-OperationContext raises exception."""
        with pytest.raises(IntentConversionException) as exc_info:
            converter.convert(
                parsed_intent={'not': 'valid'},  # Dict instead of OperationContext
                project_id=test_project.id,
                original_message='test'
            )

        assert 'must be an OperationContext instance' in str(exc_info.value)

    def test_negative_project_id(self, converter):
        """Test negative project_id raises exception."""
        parsed_intent = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            parameters={'title': 'Test'},
            confidence=0.90,
            raw_input='test'
        )

        with pytest.raises(IntentConversionException) as exc_info:
            converter.convert(
                parsed_intent=parsed_intent,
                project_id=-1,
                original_message='test'
            )

        assert 'positive integer' in str(exc_info.value)
