"""Integration tests for NLCommandProcessor (ADR-016 Story 5 Task 3.3).

Tests the complete 5-stage NL command pipeline integration:
- IntentClassifier → OperationClassifier → EntityTypeClassifier →
  EntityIdentifierExtractor → ParameterExtractor → OperationContext →
  CommandValidator → CommandExecutor

Covers:
- Full CREATE pipeline (2 tests)
- Full UPDATE pipeline (2 tests)
- Full QUERY pipeline with different query types (3 tests)
- QUESTION intent with QuestionHandler (2 tests)
- Error handling at each stage (2 tests)

Target: 90%+ integration coverage for NLCommandProcessor
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import json

from src.nl.nl_command_processor import NLCommandProcessor, NLResponse
from src.nl.types import OperationType, EntityType, QueryType, QuestionType
from core.state import StateManager
from core.config import Config
from plugins.base import LLMPlugin


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    config = Mock(spec=Config)
    config.get = Mock(side_effect=lambda key, default=None: {
        'nl_commands.schema_path': 'src/nl/schemas/obra_schema.json',
        'nl_commands.require_confirmation_for': ['delete', 'update'],
        'nl_commands.default_project_id': 1,
        'nl_commands.fallback_to_info': True
    }.get(key, default))
    return config


@pytest.fixture
def mock_state_manager():
    """Create a mock StateManager."""
    state = Mock()
    state.db = Mock()
    state.db.commit = Mock()
    return state


@pytest.fixture
def mock_llm():
    """Create a mock LLM plugin."""
    llm = Mock(spec=LLMPlugin)
    return llm


@pytest.fixture
def processor(mock_llm, mock_state_manager, mock_config):
    """Create NLCommandProcessor with mocked dependencies."""
    return NLCommandProcessor(
        llm_plugin=mock_llm,
        state_manager=mock_state_manager,
        config=mock_config,
        confidence_threshold=0.7
    )


class TestCreatePipeline:
    """Test full CREATE operation pipeline."""

    def test_create_epic_full_pipeline(self, processor, mock_llm, mock_state_manager):
        """Test: 'Create an epic for user authentication' → CREATE EPIC"""
        # Mock pipeline stages
        # Stage 1: OperationClassifier
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),  # IntentClassifier
            json.dumps({"operation_type": "CREATE", "confidence": 0.93}),  # OperationClassifier
            json.dumps({"entity_type": "EPIC", "confidence": 0.92}),  # EntityTypeClassifier
            json.dumps({"identifier": None, "confidence": 0.90}),  # EntityIdentifierExtractor
            json.dumps({"parameters": {"title": "User Authentication"}, "confidence": 0.88})  # ParameterExtractor
        ]

        # Mock CommandExecutor
        mock_state_manager.create_epic.return_value = 10

        # Process command
        response = processor.process("Create an epic for user authentication", project_id=1)

        # Verify full pipeline executed
        assert response.success
        assert response.intent == 'COMMAND'
        assert mock_llm.generate.call_count == 5  # All 5 stages called
        mock_state_manager.create_epic.assert_called_once()

    def test_create_task_with_parameters(self, processor, mock_llm, mock_state_manager):
        """Test: 'Create a task with priority HIGH' → CREATE TASK with params"""
        # Mock pipeline stages
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.94}),  # IntentClassifier
            json.dumps({"operation_type": "CREATE", "confidence": 0.92}),  # OperationClassifier
            json.dumps({"entity_type": "TASK", "confidence": 0.91}),  # EntityTypeClassifier
            json.dumps({"identifier": None, "confidence": 0.89}),  # EntityIdentifierExtractor
            json.dumps({"parameters": {"title": "New task", "priority": "HIGH"}, "confidence": 0.87})  # ParameterExtractor
        ]

        # Mock task creation
        mock_task = Mock()
        mock_task.id = 20
        mock_state_manager.create_task.return_value = mock_task

        response = processor.process("Create a task with priority HIGH", project_id=1)

        assert response.success
        assert mock_state_manager.create_task.called


class TestUpdatePipeline:
    """Test full UPDATE operation pipeline."""

    def test_update_project_status_full_pipeline(self, processor, mock_llm, mock_state_manager):
        """Test: 'Mark the manual tetris test as INACTIVE' → UPDATE PROJECT (ISSUE-001)"""
        # Mock pipeline stages
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.96}),  # IntentClassifier
            json.dumps({"operation_type": "UPDATE", "confidence": 0.94}),  # OperationClassifier
            json.dumps({"entity_type": "PROJECT", "confidence": 0.93}),  # EntityTypeClassifier
            json.dumps({"identifier": "manual tetris test", "confidence": 0.91}),  # EntityIdentifierExtractor
            json.dumps({"parameters": {"status": "INACTIVE"}, "confidence": 0.90})  # ParameterExtractor
        ]

        # Mock project lookup and update
        mock_project = Mock()
        mock_project.id = 1
        mock_project.project_name = "Manual Tetris Test"
        mock_state_manager.get_all_projects.return_value = [mock_project]
        mock_state_manager.get_project.return_value = mock_project

        response = processor.process(
            "Mark the manual tetris test as INACTIVE",
            project_id=1,
            confirmed=True
        )

        assert response.success
        assert response.intent == 'COMMAND'
        # Verify UPDATE operation was classified correctly
        assert mock_llm.generate.call_count == 5

    def test_update_task_with_validation_error(self, processor, mock_llm, mock_state_manager):
        """Test UPDATE with validation error (entity not found)."""
        # Mock pipeline stages
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),  # IntentClassifier
            json.dumps({"operation_type": "UPDATE", "confidence": 0.93}),  # OperationClassifier
            json.dumps({"entity_type": "TASK", "confidence": 0.92}),  # EntityTypeClassifier
            json.dumps({"identifier": 999, "confidence": 0.90}),  # EntityIdentifierExtractor (non-existent)
            json.dumps({"parameters": {"status": "COMPLETED"}, "confidence": 0.89})  # ParameterExtractor
        ]

        # Mock task not found
        mock_state_manager.get_task.return_value = None

        response = processor.process(
            "Mark task 999 as completed",
            project_id=1,
            confirmed=True
        )

        # Should fail validation (entity not found)
        assert not response.success
        assert 'not found' in response.response.lower() or 'error' in response.response.lower()


class TestQueryPipeline:
    """Test full QUERY operation pipeline with different query types."""

    def test_query_hierarchical_workplan(self, processor, mock_llm, mock_state_manager):
        """Test: 'List the workplans for the projects' → QUERY HIERARCHICAL (ISSUE-002)"""
        # Mock pipeline stages
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.94}),  # IntentClassifier
            json.dumps({"operation_type": "QUERY", "confidence": 0.93}),  # OperationClassifier
            json.dumps({"entity_type": "PROJECT", "confidence": 0.91}),  # EntityTypeClassifier
            json.dumps({"identifier": None, "confidence": 0.90}),  # EntityIdentifierExtractor (show all)
            json.dumps({"parameters": {}, "confidence": 0.88})  # ParameterExtractor
        ]

        # Mock hierarchical query data
        mock_epic = Mock()
        mock_epic.id = 5
        mock_epic.title = "Epic 1"
        mock_epic.status = Mock(value='RUNNING')

        mock_story = Mock()
        mock_story.id = 10
        mock_story.title = "Story 1"
        mock_story.status = Mock(value='RUNNING')

        mock_task = Mock()
        mock_task.id = 20
        mock_task.title = "Task 1"
        mock_task.status = Mock(value='RUNNING')

        mock_state_manager.list_tasks.return_value = [mock_epic]
        mock_state_manager.get_epic_stories.return_value = [mock_story]
        mock_state_manager.get_story_tasks.return_value = [mock_task]

        response = processor.process("List the workplans for the projects", project_id=1)

        assert response.success
        # Verify QueryType.HIERARCHICAL was detected
        assert mock_state_manager.get_epic_stories.called

    def test_query_simple_list(self, processor, mock_llm, mock_state_manager):
        """Test: 'Show all tasks' → QUERY SIMPLE"""
        # Mock pipeline stages
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),  # IntentClassifier
            json.dumps({"operation_type": "QUERY", "confidence": 0.93}),  # OperationClassifier
            json.dumps({"entity_type": "TASK", "confidence": 0.92}),  # EntityTypeClassifier
            json.dumps({"identifier": None, "confidence": 0.90}),  # EntityIdentifierExtractor
            json.dumps({"parameters": {}, "confidence": 0.88})  # ParameterExtractor
        ]

        # Mock simple query
        mock_task1 = Mock()
        mock_task1.id = 10
        mock_task1.title = "Task 1"
        mock_task1.description = "Desc 1"
        mock_task1.status = Mock(value='RUNNING')

        mock_state_manager.list_tasks.return_value = [mock_task1]

        response = processor.process("Show all tasks", project_id=1)

        assert response.success
        mock_state_manager.list_tasks.assert_called()

    def test_query_next_steps(self, processor, mock_llm, mock_state_manager):
        """Test: 'What's next for the tetris project' → QUERY NEXT_STEPS"""
        # Mock pipeline stages
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.94}),  # IntentClassifier
            json.dumps({"operation_type": "QUERY", "confidence": 0.92}),  # OperationClassifier
            json.dumps({"entity_type": "TASK", "confidence": 0.91}),  # EntityTypeClassifier
            json.dumps({"identifier": None, "confidence": 0.89}),  # EntityIdentifierExtractor
            json.dumps({"parameters": {}, "confidence": 0.87})  # ParameterExtractor
        ]

        # Mock next steps query
        mock_task = Mock()
        mock_task.id = 10
        mock_task.title = "Next Task"
        mock_task.status = Mock(value='RUNNING')
        mock_task.priority = 10
        mock_task.project_id = 1
        mock_task.task_type = Mock(value='task')

        mock_state_manager.list_tasks.return_value = [mock_task]

        response = processor.process("What's next for the tetris project", project_id=1)

        assert response.success


class TestQuestionIntent:
    """Test QUESTION intent handling with QuestionHandler."""

    def test_question_next_steps(self, processor, mock_llm, mock_state_manager):
        """Test: 'What's next for the tetris game development' → QUESTION (ISSUE-003)"""
        # Mock IntentClassifier
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "QUESTION", "confidence": 0.93}),  # IntentClassifier
            json.dumps({"question_type": "NEXT_STEPS", "confidence": 0.91})  # QuestionHandler classification
        ]

        # Mock QuestionHandler data retrieval
        mock_task = Mock()
        mock_task.id = 10
        mock_task.title = "Implement scoring"
        mock_task.status = Mock(value='RUNNING')

        mock_state_manager.list_tasks.return_value = [mock_task]
        mock_state_manager.get_all_projects.return_value = []

        response = processor.process("What's next for the tetris game development", project_id=1)

        # Should be handled as QUESTION (not rejected)
        assert response.intent == 'QUESTION'
        # May succeed or fail depending on QuestionHandler implementation, but shouldn't reject

    def test_question_status(self, processor, mock_llm, mock_state_manager):
        """Test: 'What's the status of epic 5' → QUESTION STATUS"""
        # Mock IntentClassifier
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "QUESTION", "confidence": 0.94}),  # IntentClassifier
            json.dumps({"question_type": "STATUS", "confidence": 0.92})  # QuestionHandler classification
        ]

        # Mock epic data
        mock_epic = Mock()
        mock_epic.id = 5
        mock_epic.title = "Epic 5"
        mock_epic.status = Mock(value='RUNNING')

        mock_state_manager.get_task.return_value = mock_epic
        mock_state_manager.get_all_projects.return_value = []

        response = processor.process("What's the status of epic 5", project_id=1)

        assert response.intent == 'QUESTION'


class TestErrorHandling:
    """Test error handling at each pipeline stage."""

    def test_invalid_empty_message(self, processor):
        """Test empty message handling."""
        response = processor.process("", project_id=1)

        assert not response.success
        assert 'provide a message' in response.response.lower()

    def test_pipeline_stage_exception(self, processor, mock_llm):
        """Test exception during pipeline stage."""
        # Mock IntentClassifier success, but OperationClassifier fails
        mock_llm.generate.side_effect = [
            json.dumps({"intent": "COMMAND", "confidence": 0.95}),  # IntentClassifier
            Exception("LLM API error")  # OperationClassifier fails
        ]

        response = processor.process("Create an epic", project_id=1)

        assert not response.success
        assert 'error' in response.response.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
