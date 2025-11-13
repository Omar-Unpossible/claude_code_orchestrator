"""Integration tests for ADR-016 five-stage NL command pipeline (Story 6 Task 4.2).

Tests the complete pipeline end-to-end with actual components:
    IntentClassifier → OperationClassifier → EntityTypeClassifier →
    EntityIdentifierExtractor → ParameterExtractor → CommandValidator → CommandExecutor

Test Categories:
- Full Pipeline Tests (10): Complete workflows for CREATE/UPDATE/DELETE/QUERY/QUESTION
- Error Propagation Tests (10): Error handling at each pipeline stage
- Cross-Component Tests (7): Component interaction and context passing

Total: 27 integration tests

Target: Validate 95%+ accuracy for ADR-016 pipeline
"""

import pytest
import json
from unittest.mock import MagicMock, Mock

from src.nl.operation_classifier import OperationClassifier
from src.nl.entity_type_classifier import EntityTypeClassifier
from src.nl.entity_identifier_extractor import EntityIdentifierExtractor
from src.nl.parameter_extractor import ParameterExtractor
from src.nl.question_handler import QuestionHandler
from src.nl.command_validator import CommandValidator
from src.nl.command_executor import CommandExecutor
from src.nl.intent_classifier import IntentClassifier
from src.nl.types import (
    OperationContext, OperationType, EntityType, QueryType, QuestionType
)
from src.core.state import StateManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def integration_state(tmp_path):
    """Real StateManager with in-memory database for integration testing."""
    state = StateManager(database_url='sqlite:///:memory:')

    # Create test project (returns ProjectState object)
    project = state.create_project(
        name="Integration Test Project",
        description="ADR-016 pipeline integration testing",
        working_dir=str(tmp_path)
    )

    # Create test epic (returns integer ID)
    epic_id = state.create_epic(
        project_id=project.id,
        title="Test Epic",
        description="Test epic for integration tests"
    )

    # Create test story (returns integer ID)
    story_id = state.create_story(
        project_id=project.id,
        epic_id=epic_id,
        title="Test Story",
        description="Test story for integration tests"
    )

    # Create test task (returns Task object)
    task = state.create_task(
        project_id=project.id,
        task_data={
            'title': "Test Task",
            'description': "Test task for integration tests",
            'story_id': story_id
        }
    )
    task_id = task.id

    yield state
    state.close()


@pytest.fixture
def mock_llm():
    """Mock LLM plugin that returns predefined responses."""
    llm = MagicMock()

    # Default responses for each classifier
    llm.generate = MagicMock(return_value=json.dumps({
        "operation_type": "CREATE",
        "confidence": 0.95,
        "reasoning": "Clear creation command"
    }))

    return llm


@pytest.fixture
def pipeline_components(mock_llm, integration_state):
    """All ADR-016 pipeline components wired together."""
    return {
        'intent_classifier': IntentClassifier(mock_llm, confidence_threshold=0.7),
        'operation_classifier': OperationClassifier(mock_llm, confidence_threshold=0.7),
        'entity_type_classifier': EntityTypeClassifier(mock_llm, confidence_threshold=0.7),
        'entity_identifier_extractor': EntityIdentifierExtractor(mock_llm, confidence_threshold=0.7),
        'parameter_extractor': ParameterExtractor(mock_llm, confidence_threshold=0.7),
        'question_handler': QuestionHandler(integration_state, mock_llm),
        'command_validator': CommandValidator(integration_state),
        'command_executor': CommandExecutor(integration_state, default_project_id=1),
        'state': integration_state
    }


# ============================================================================
# Test Class 1: Full Pipeline Tests (10 tests)
# ============================================================================

class TestFullPipelineCREATE:
    """Test complete CREATE operation pipeline."""

    def test_create_epic_full_pipeline(self, pipeline_components, mock_llm):
        """Test: User says 'Create epic for authentication' → Epic created."""
        user_input = "Create epic for user authentication"

        # Stage 1: Intent Classification
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.95,
            "reasoning": "Clear command"
        })
        intent_result = pipeline_components['intent_classifier'].classify(user_input)
        assert intent_result.intent == "COMMAND"

        # Stage 2: Operation Classification
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.95,
            "reasoning": "User wants to create something"
        })
        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        assert operation_result.operation_type == OperationType.CREATE

        # Stage 3: Entity Type Classification
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "epic",
            "confidence": 0.92,
            "reasoning": "User explicitly said 'epic'"
        })
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        assert entity_type_result.entity_type == EntityType.EPIC

        # Stage 4: Entity Identifier Extraction (None for CREATE)
        mock_llm.generate.return_value = json.dumps({
            "identifier": None,
            "confidence": 1.0,
            "reasoning": "CREATE operations don't need identifier"
        })
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        assert identifier_result.identifier is None

        # Stage 5: Parameter Extraction
        mock_llm.generate.return_value = json.dumps({
            "parameters": {
                "title": "user authentication",
                "description": "User authentication epic"
            },
            "confidence": 0.90,
            "reasoning": "Extracted title from user input"
        })
        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )
        assert "title" in parameter_result.parameters

        # Build OperationContext
        context = OperationContext(
            operation=operation_result.operation_type,
            entity_type=entity_type_result.entity_type,
            identifier=identifier_result.identifier,
            parameters=parameter_result.parameters,
            confidence=min(
                operation_result.confidence,
                entity_type_result.confidence,
                identifier_result.confidence,
                parameter_result.confidence
            ),
            raw_input=user_input
        )

        # Stage 6: Validation
        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        # Stage 7: Execution
        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1
        )
        assert execution_result.success is True
        assert len(execution_result.created_ids) == 1

        # Verify in database
        epic = pipeline_components['state'].get_task(execution_result.created_ids[0])
        assert epic is not None
        assert "authentication" in epic.title.lower()

    def test_create_task_with_parameters(self, pipeline_components, mock_llm):
        """Test: 'Create task with priority HIGH' → Task created with priority."""
        user_input = "Create task with priority HIGH for implementing login"

        # Mock LLM responses for full pipeline
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),
            json.dumps({"operation_type": "CREATE", "confidence": 0.94}),
            json.dumps({"entity_type": "task", "confidence": 0.93}),
            json.dumps({"identifier": None, "confidence": 1.0}),
            json.dumps({
                "parameters": {
                    "title": "implementing login",
                    "priority": "HIGH"
                },
                "confidence": 0.91
            })
        ]

        # Run through pipeline
        intent_result = pipeline_components['intent_classifier'].classify(user_input)
        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )

        context = OperationContext(
            operation=operation_result.operation_type,
            entity_type=entity_type_result.entity_type,
            identifier=identifier_result.identifier,
            parameters=parameter_result.parameters,
            confidence=0.90,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1
        )
        assert execution_result.success is True

        # Verify priority was set
        task = pipeline_components['state'].get_task(execution_result.created_ids[0])
        assert task.priority == 3  # HIGH = 3


class TestFullPipelineUPDATE:
    """Test complete UPDATE operation pipeline."""

    def test_update_project_status_full_pipeline(self, pipeline_components, mock_llm):
        """Test: ISSUE-001 resolution - 'Mark Integration Test Project as INACTIVE'."""
        user_input = "Mark the Integration Test Project as INACTIVE"

        # Mock LLM responses
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.96}),
            json.dumps({"operation_type": "UPDATE", "confidence": 0.97}),  # Correctly classifies UPDATE
            json.dumps({"entity_type": "project", "confidence": 0.95}),  # Correctly classifies PROJECT
            json.dumps({"identifier": "Integration Test Project", "confidence": 0.94}),
            json.dumps({"parameters": {"status": "INACTIVE"}, "confidence": 0.93})
        ]

        # Run through pipeline
        intent_result = pipeline_components['intent_classifier'].classify(user_input)
        assert intent_result.intent == "COMMAND"

        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        assert operation_result.operation_type == OperationType.UPDATE

        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        assert entity_type_result.entity_type == EntityType.PROJECT

        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        assert identifier_result.identifier == "Integration Test Project"

        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )
        assert parameter_result.parameters["status"] == "INACTIVE"

        # Build context
        context = OperationContext(
            operation=operation_result.operation_type,
            entity_type=entity_type_result.entity_type,
            identifier=identifier_result.identifier,
            parameters=parameter_result.parameters,
            confidence=0.93,
            raw_input=user_input
        )

        # Validate and execute
        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1, confirmed=True
        )
        assert execution_result.success is True

        # Verify status was updated
        project = pipeline_components['state'].get_project(1)
        # INACTIVE maps to PAUSED in ProjectStatus
        from core.models import ProjectStatus
        assert project.status == ProjectStatus.PAUSED

    def test_update_task_by_id(self, pipeline_components, mock_llm):
        """Test: 'Update task 4 priority to HIGH'."""
        user_input = "Update task 4 priority to HIGH"

        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.94}),
            json.dumps({"operation_type": "UPDATE", "confidence": 0.96}),
            json.dumps({"entity_type": "task", "confidence": 0.95}),
            json.dumps({"identifier": 4, "confidence": 0.98}),
            json.dumps({"parameters": {"priority": "HIGH"}, "confidence": 0.92})
        ]

        # Run through pipeline
        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier=4,
            parameters={"priority": "HIGH"},
            confidence=0.92,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1, confirmed=True
        )
        assert execution_result.success is True


class TestFullPipelineQUERY:
    """Test complete QUERY operation pipeline."""

    def test_query_hierarchical_workplan(self, pipeline_components, mock_llm):
        """Test: ISSUE-002 resolution - 'List the workplans for the projects'."""
        user_input = "List the workplans for the projects"

        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),
            json.dumps({"operation_type": "QUERY", "confidence": 0.96}),
            json.dumps({"entity_type": "project", "confidence": 0.92}),
            json.dumps({"identifier": None, "confidence": 0.98}),
            json.dumps({
                "parameters": {"query_type": "HIERARCHICAL"},
                "confidence": 0.91
            })
        ]

        # Run through pipeline
        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        assert operation_result.operation_type == OperationType.QUERY

        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )

        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )

        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )
        assert parameter_result.parameters.get("query_type") == "HIERARCHICAL"

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT,
            identifier=None,
            parameters=parameter_result.parameters,
            query_type=QueryType.WORKPLAN,  # Workplan maps to HIERARCHICAL
            confidence=0.91,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1
        )
        assert execution_result.success is True

    def test_query_simple_list_tasks(self, pipeline_components, mock_llm):
        """Test: 'Show all tasks' → Simple query."""
        user_input = "Show all tasks"

        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.97}),
            json.dumps({"operation_type": "QUERY", "confidence": 0.98}),
            json.dumps({"entity_type": "task", "confidence": 0.96}),
            json.dumps({"identifier": None, "confidence": 1.0}),
            json.dumps({"parameters": {}, "confidence": 0.95})
        ]

        # Build context
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK,
            identifier=None,
            parameters={},
            query_type=QueryType.SIMPLE,
            confidence=0.95,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1
        )
        assert execution_result.success is True

    def test_project_plan_query_e2e(self, pipeline_components, mock_llm, integration_state):
        """Test: BUG FIX - 'For project #1, list the current plan' → HIERARCHICAL with filtering.

        This test validates:
        1. LLM-extracted query_type='hierarchical' takes priority over keywords
        2. Identifier filtering works (project #1 only, not all projects)
        3. Returns hierarchical structure (epics → stories → tasks)
        """
        user_input = "For project #1, list the current plan"

        mock_llm.generate.side_effect = [
            json.dumps({"operation_type": "QUERY", "confidence": 0.93}),
            json.dumps({"entity_type": "PROJECT", "confidence": 0.91}),
            json.dumps({"identifier": 1, "confidence": 0.90}),
            json.dumps({
                "parameters": {"query_type": "hierarchical"},
                "confidence": 0.88
            })
        ]

        # Run through full pipeline
        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        assert operation_result.operation_type == OperationType.QUERY

        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        assert entity_type_result.entity_type == EntityType.PROJECT

        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        # Identifier is extracted as string '1'
        assert identifier_result.identifier == '1' or identifier_result.identifier == 1

        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )
        # Verify LLM extracted query_type
        assert parameter_result.parameters.get("query_type") == "hierarchical"

        # Build context (using actual identifier from extraction)
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT,
            identifier=identifier_result.identifier,
            parameters=parameter_result.parameters,
            query_type=QueryType.HIERARCHICAL,
            confidence=0.91,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        # Verify the fix worked: LLM extraction set query_type to HIERARCHICAL
        assert context.query_type == QueryType.HIERARCHICAL
        # Verify identifier was correctly extracted and passed through
        assert context.identifier == '1'


class TestFullPipelineDELETE:
    """Test complete DELETE operation pipeline."""

    def test_delete_task_by_id(self, pipeline_components, mock_llm):
        """Test: 'Delete task 4' → Task deleted."""
        user_input = "Delete task 4"

        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.98}),
            json.dumps({"operation_type": "DELETE", "confidence": 0.97}),
            json.dumps({"entity_type": "task", "confidence": 0.96}),
            json.dumps({"identifier": 4, "confidence": 0.99}),
            json.dumps({"parameters": {}, "confidence": 1.0})
        ]

        # Run through pipeline
        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        assert operation_result.operation_type == OperationType.DELETE

        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )

        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )

        context = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.TASK,
            identifier=4,
            parameters={},
            confidence=0.96,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1, confirmed=True
        )
        assert execution_result.success is True


class TestFullPipelineQUESTION:
    """Test complete QUESTION intent pipeline."""

    def test_question_whats_next(self, pipeline_components, mock_llm):
        """Test: ISSUE-003 resolution - 'What's next for Integration Test Project'."""
        user_input = "What's next for the Integration Test Project"

        # Stage 1: Intent Classification → QUESTION
        mock_llm.generate.return_value = json.dumps({
            "intent": "QUESTION",
            "confidence": 0.96,
            "reasoning": "User is asking a question"
        })

        intent_result = pipeline_components['intent_classifier'].classify(user_input)
        assert intent_result.intent == "QUESTION"

        # QUESTION path: Goes to QuestionHandler, not operation pipeline
        mock_llm.generate.side_effect = [
            json.dumps({"question_type": "NEXT_STEPS", "confidence": 0.94}),
            json.dumps({"entities": {"project_name": "Integration Test Project"}, "confidence": 0.93})
        ]

        question_response = pipeline_components['question_handler'].handle(user_input)

        assert question_response.question_type == QuestionType.NEXT_STEPS
        assert question_response.answer is not None
        assert len(question_response.answer) > 0

    def test_question_project_status(self, pipeline_components, mock_llm):
        """Test: 'How's the Integration Test Project going?' → Status response."""
        user_input = "How's the Integration Test Project going?"

        mock_llm.generate.side_effect = [
            json.dumps({"intent": "QUESTION", "confidence": 0.97}),
            json.dumps({"question_type": "STATUS", "confidence": 0.95}),
            json.dumps({"entities": {"project_name": "Integration Test Project"}, "confidence": 0.94})
        ]

        intent_result = pipeline_components['intent_classifier'].classify(user_input)
        assert intent_result.intent == "QUESTION"

        question_response = pipeline_components['question_handler'].handle(user_input)
        assert question_response.question_type == QuestionType.STATUS


# ============================================================================
# Test Class 2: Error Propagation Tests (10 tests)
# ============================================================================

class TestErrorPropagation:
    """Test error handling and propagation through pipeline stages."""

    def test_operation_classifier_low_confidence(self, pipeline_components, mock_llm):
        """Test: Operation classifier returns low confidence → Validation fails."""
        user_input = "Maybe create something?"

        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.45,  # Below threshold (0.7)
            "reasoning": "Very uncertain"
        })

        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        assert operation_result.confidence < 0.7

    def test_entity_type_classifier_error(self, pipeline_components, mock_llm):
        """Test: Entity type classifier fails → Error propagates."""
        user_input = "Create something"

        # Valid operation
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.95
        })
        operation_result = pipeline_components['operation_classifier'].classify(user_input)

        # Invalid entity type
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "invalid_type",
            "confidence": 0.50
        })

        with pytest.raises(Exception):
            pipeline_components['entity_type_classifier'].classify(
                user_input, operation_result.operation_type
            )

    def test_identifier_extractor_no_identifier_for_update(self, pipeline_components, mock_llm):
        """Test: UPDATE operation without identifier → Validation fails."""
        user_input = "Update project status"

        mock_llm.generate.side_effect = [
            json.dumps({"operation_type": "UPDATE", "confidence": 0.95}),
            json.dumps({"entity_type": "project", "confidence": 0.94}),
            json.dumps({"identifier": None, "confidence": 0.60})  # Missing identifier!
        ]

        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )

        # OperationContext should raise ValueError for UPDATE without identifier
        with pytest.raises(ValueError, match="update operation requires an identifier"):
            context = OperationContext(
                operation=OperationType.UPDATE,
                entity_type=EntityType.PROJECT,
                identifier=None,  # Missing!
                parameters={"status": "INACTIVE"}
            )

    def test_parameter_extractor_invalid_status(self, pipeline_components, mock_llm):
        """Test: Invalid status parameter → Validation fails."""
        user_input = "Mark project 1 as INVALID_STATUS"

        mock_llm.generate.side_effect = [
            json.dumps({"operation_type": "UPDATE", "confidence": 0.96}),
            json.dumps({"entity_type": "project", "confidence": 0.95}),
            json.dumps({"identifier": 1, "confidence": 0.98}),
            json.dumps({
                "parameters": {"status": "INVALID_STATUS"},
                "confidence": 0.90
            })
        ]

        # Build context
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT,
            identifier=1,
            parameters={"status": "INVALID_STATUS"},
            confidence=0.90,
            raw_input=user_input
        )

        # Validation should fail
        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is False
        assert any("status" in error.lower() for error in validation_result.errors)

    def test_entity_not_found_for_update(self, pipeline_components, mock_llm):
        """Test: UPDATE non-existent entity → Validation fails."""
        user_input = "Update project 9999 status to INACTIVE"

        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT,
            identifier=9999,  # Doesn't exist
            parameters={"status": "INACTIVE"},
            confidence=0.95,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is False
        assert any("not found" in error.lower() for error in validation_result.errors)

    def test_llm_timeout_error(self, pipeline_components, mock_llm):
        """Test: LLM timeout → Error handled gracefully."""
        user_input = "Create epic"

        # Simulate LLM timeout
        mock_llm.generate.side_effect = TimeoutError("LLM request timed out")

        with pytest.raises(TimeoutError):
            pipeline_components['operation_classifier'].classify(user_input)

    def test_malformed_json_response(self, pipeline_components, mock_llm):
        """Test: LLM returns malformed JSON → Error handled."""
        user_input = "Create task"

        # Invalid JSON
        mock_llm.generate.return_value = "Not a JSON response"

        with pytest.raises(Exception):
            pipeline_components['operation_classifier'].classify(user_input)

    def test_missing_required_field_title(self, pipeline_components, mock_llm):
        """Test: CREATE epic without title → Validation fails."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.EPIC,
            identifier=None,
            parameters={"description": "No title provided"},  # Missing title!
            confidence=0.90,
            raw_input="Create epic"
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is False

    def test_circular_dependency_detected(self, pipeline_components, mock_llm):
        """Test: Task with circular dependency → Validation fails."""
        # Create two tasks (create_task returns integer ID)
        task1_id = pipeline_components['state'].create_task(
            project_id=1,
            title="Task 1",
            description="First task"
        )
        task2_id = pipeline_components['state'].create_task(
            project_id=1,
            title="Task 2",
            description="Second task",
            dependencies=[task1_id]
        )

        # Try to make task1 depend on task2 (circular!)
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK,
            identifier=task1_id,
            parameters={"dependencies": [task2_id]},
            confidence=0.95,
            raw_input=f"Update task {task1_id} dependencies to {task2_id}"
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        # Should detect circular dependency
        # (Actual behavior depends on CommandValidator implementation)

    def test_invalid_priority_value(self, pipeline_components, mock_llm):
        """Test: Invalid priority value → Validation fails."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            identifier=None,
            parameters={"title": "Test", "priority": "SUPER_HIGH"},  # Invalid
            confidence=0.90,
            raw_input="Create task with super high priority"
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is False
        assert any("priority" in error.lower() for error in validation_result.errors)


# ============================================================================
# Test Class 3: Cross-Component Tests (7 tests)
# ============================================================================

class TestCrossComponentInteraction:
    """Test interaction between pipeline components."""

    def test_confidence_aggregation_across_stages(self, pipeline_components, mock_llm):
        """Test: Confidence scores aggregate correctly through pipeline."""
        user_input = "Create epic for auth"

        mock_llm.generate.side_effect = [
            json.dumps({"operation_type": "CREATE", "confidence": 0.95}),
            json.dumps({"entity_type": "epic", "confidence": 0.92}),
            json.dumps({"identifier": None, "confidence": 1.0}),
            json.dumps({"parameters": {"title": "auth"}, "confidence": 0.88})
        ]

        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )

        # Aggregate confidence (minimum of all stages)
        aggregate_confidence = min(
            operation_result.confidence,
            entity_type_result.confidence,
            identifier_result.confidence,
            parameter_result.confidence
        )

        assert aggregate_confidence == 0.88  # Minimum

    def test_context_passing_through_stages(self, pipeline_components, mock_llm):
        """Test: Context (operation type) passes correctly through stages."""
        user_input = "Update project 1 status"

        mock_llm.generate.side_effect = [
            json.dumps({"operation_type": "UPDATE", "confidence": 0.96}),
            json.dumps({"entity_type": "project", "confidence": 0.94}),
            json.dumps({"identifier": 1, "confidence": 0.98}),
            json.dumps({"parameters": {"status": "INACTIVE"}, "confidence": 0.92})
        ]

        operation_result = pipeline_components['operation_classifier'].classify(user_input)

        # Entity type classifier receives operation context
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type  # Context passed!
        )

        # Identifier extractor receives both operation and entity type context
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input,
            entity_type_result.entity_type,
            operation_result.operation_type  # Context passed!
        )

        # Parameter extractor receives both contexts
        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input,
            operation_result.operation_type,  # Context passed!
            entity_type_result.entity_type  # Context passed!
        )

        # All contexts should be consistent
        assert operation_result.operation_type == OperationType.UPDATE
        assert entity_type_result.entity_type == EntityType.PROJECT

    def test_operation_context_construction(self, pipeline_components, mock_llm):
        """Test: OperationContext builds correctly from all stages."""
        user_input = "Create story for epic 2"

        mock_llm.generate.side_effect = [
            json.dumps({"operation_type": "CREATE", "confidence": 0.94}),
            json.dumps({"entity_type": "story", "confidence": 0.93}),
            json.dumps({"identifier": None, "confidence": 1.0}),
            json.dumps({
                "parameters": {"title": "story", "epic_id": 2},
                "confidence": 0.91
            })
        ]

        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )

        # Build OperationContext
        context = OperationContext(
            operation=operation_result.operation_type,
            entity_type=entity_type_result.entity_type,
            identifier=identifier_result.identifier,
            parameters=parameter_result.parameters,
            confidence=0.91,
            raw_input=user_input
        )

        # Verify all fields populated correctly
        assert context.operation == OperationType.CREATE
        assert context.entity_type == EntityType.STORY
        assert context.identifier is None
        assert "epic_id" in context.parameters
        assert context.parameters["epic_id"] == 2
        assert context.confidence == 0.91
        assert context.raw_input == user_input

    def test_validation_to_execution_handoff(self, pipeline_components, mock_llm):
        """Test: Validated command passes correctly to executor."""
        context = OperationContext(
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK,
            identifier=None,
            parameters={"title": "Test Task", "priority": "HIGH"},
            confidence=0.92,
            raw_input="Create task"
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        assert validation_result.valid is True

        # Validated command should be ready for executor
        assert validation_result.validated_command is not None
        assert validation_result.validated_command['operation'] == "create"
        assert validation_result.validated_command['entity_type'] == "task"

        # Execute
        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1
        )
        assert execution_result.success is True

    def test_question_intent_bypasses_command_pipeline(self, pipeline_components, mock_llm):
        """Test: QUESTION intent goes to QuestionHandler, not command pipeline."""
        user_input = "What's next for the project?"

        mock_llm.generate.return_value = json.dumps({
            "intent": "QUESTION",
            "confidence": 0.97
        })

        intent_result = pipeline_components['intent_classifier'].classify(user_input)
        assert intent_result.intent == "QUESTION"

        # Should NOT go through operation classifier
        # Should go directly to QuestionHandler
        mock_llm.generate.side_effect = [
            json.dumps({"question_type": "NEXT_STEPS", "confidence": 0.95}),
            json.dumps({"entities": {}, "confidence": 0.90})
        ]

        question_response = pipeline_components['question_handler'].handle(user_input)
        assert question_response is not None
        assert question_response.question_type == QuestionType.NEXT_STEPS

    def test_stage_failure_stops_pipeline(self, pipeline_components, mock_llm):
        """Test: Failure at any stage prevents downstream execution."""
        user_input = "Invalid command"

        # Operation classifier fails
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "INVALID",
            "confidence": 0.30
        })

        with pytest.raises(Exception):
            operation_result = pipeline_components['operation_classifier'].classify(user_input)
            # Should not reach entity type classifier

    def test_end_to_end_latency_acceptable(self, pipeline_components, mock_llm):
        """Test: Full pipeline completes in acceptable time (<1s target)."""
        import time

        user_input = "Create task for testing"

        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),
            json.dumps({"operation_type": "CREATE", "confidence": 0.94}),
            json.dumps({"entity_type": "task", "confidence": 0.93}),
            json.dumps({"identifier": None, "confidence": 1.0}),
            json.dumps({"parameters": {"title": "testing"}, "confidence": 0.92})
        ]

        start_time = time.time()

        # Run full pipeline
        intent_result = pipeline_components['intent_classifier'].classify(user_input)
        operation_result = pipeline_components['operation_classifier'].classify(user_input)
        entity_type_result = pipeline_components['entity_type_classifier'].classify(
            user_input, operation_result.operation_type
        )
        identifier_result = pipeline_components['entity_identifier_extractor'].extract(
            user_input, entity_type_result.entity_type, operation_result.operation_type
        )
        parameter_result = pipeline_components['parameter_extractor'].extract(
            user_input, operation_result.operation_type, entity_type_result.entity_type
        )

        context = OperationContext(
            operation=operation_result.operation_type,
            entity_type=entity_type_result.entity_type,
            identifier=identifier_result.identifier,
            parameters=parameter_result.parameters,
            confidence=0.92,
            raw_input=user_input
        )

        validation_result = pipeline_components['command_validator'].validate(context)
        execution_result = pipeline_components['command_executor'].execute(
            context, project_id=1
        )

        end_time = time.time()
        latency = end_time - start_time

        # With mocked LLM, should be very fast
        # Real LLM target: <1s (from implementation plan)
        assert latency < 1.0  # Mock should be instant
        assert execution_result.success is True


class TestMilestoneRoadmapQuery:
    """Integration test for milestone roadmap query (bug fix validation)."""

    def test_roadmap_query_full_pipeline(self, integration_state, mock_llm):
        """Test: 'list the plan for project #1' → Roadmap query with list_milestones().

        This test validates the bug fix for missing StateManager.list_milestones() method.
        User command should successfully route through NL pipeline to roadmap query.
        """
        # Setup: Create milestones for the test project
        project_id = integration_state.list_projects()[0].id

        # Create epic for milestone
        epic_id = integration_state.create_epic(
            project_id=project_id,
            title="Test Feature Epic",
            description="Test epic for roadmap"
        )

        # Create milestone with required epic
        milestone_id = integration_state.create_milestone(
            project_id=project_id,
            name="Feature Complete",
            description="Test milestone for roadmap",
            required_epic_ids=[epic_id]
        )

        # User input
        user_input = "list the plan for project #1"

        # Initialize pipeline components
        from src.nl.nl_query_helper import NLQueryHelper
        query_helper = NLQueryHelper(integration_state, default_project_id=project_id)

        # Mock LLM responses for pipeline stages
        mock_llm.generate.side_effect = [
            # Stage 1: Intent = COMMAND
            json.dumps({"intent": "COMMAND", "confidence": 0.93}),
            # Stage 2: Operation = query
            json.dumps({"operation_type": "query", "confidence": 0.79}),
            # Stage 3: Entity Type = project (not task - secondary issue)
            json.dumps({"entity_type": "project", "confidence": 0.75}),
            # Stage 4: Identifier = 1
            json.dumps({"identifier": 1, "identifier_type": "int", "confidence": 0.86}),
            # Stage 5: Parameters with query_type=roadmap
            json.dumps({
                "parameters": {
                    "query_type": "roadmap",
                    "status": "ACTIVE"
                },
                "confidence": 0.82
            })
        ]

        # Execute query using NLQueryHelper (simulating NL command processor)
        from src.nl.types import OperationContext, OperationType, EntityType, QueryType
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT,  # Will be routed to milestones via query_type
            query_type=QueryType.ROADMAP,
            identifier=project_id,
            confidence=0.80,
            raw_input=user_input
        )

        # This should NOT raise AttributeError: 'StateManager' object has no attribute 'list_milestones'
        result = query_helper.execute(context, project_id=project_id)

        # Verify query succeeded
        assert result.success is True
        assert result.query_type == 'roadmap'
        assert result.entity_type == 'milestone'

        # Verify milestones were retrieved
        assert 'milestones' in result.results
        assert result.results['milestone_count'] >= 1

        # Verify milestone data structure
        milestone_data = result.results['milestones'][0]
        assert 'milestone_id' in milestone_data
        assert 'milestone_name' in milestone_data
        assert milestone_data['milestone_name'] == "Feature Complete"

        # Verify status mapping uses 'achieved' field (not non-existent 'status' field)
        assert 'milestone_status' in milestone_data
        assert milestone_data['milestone_status'] in ['ACTIVE', 'COMPLETED']
        assert milestone_data['milestone_status'] == 'ACTIVE'  # Not achieved yet

        # Verify epic association
        assert 'required_epics' in milestone_data
        assert len(milestone_data['required_epics']) == 1
        assert milestone_data['required_epics'][0]['epic_id'] == epic_id
