"""Unit tests for OperationClassifier (ADR-016 Story 2).

Tests the operation classification component with 20 test cases covering:
- 5 CREATE examples
- 5 UPDATE examples
- 5 DELETE examples
- 5 QUERY examples

Target: 95%+ accuracy, 95%+ code coverage
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.nl.operation_classifier import (
    OperationClassifier,
    OperationClassificationException
)
from src.nl.types import OperationType, OperationResult
from plugins.base import LLMPlugin


@pytest.fixture
def mock_llm():
    """Create a mock LLM plugin for testing."""
    llm = Mock(spec=LLMPlugin)
    return llm


@pytest.fixture
def classifier(mock_llm):
    """Create OperationClassifier with mock LLM."""
    return OperationClassifier(mock_llm, confidence_threshold=0.7)


class TestOperationClassifierInit:
    """Test OperationClassifier initialization."""

    def test_init_with_valid_threshold(self, mock_llm):
        """Test initialization with valid confidence threshold."""
        classifier = OperationClassifier(mock_llm, confidence_threshold=0.8)
        assert classifier.confidence_threshold == 0.8
        assert classifier.llm == mock_llm

    def test_init_with_invalid_threshold_high(self, mock_llm):
        """Test initialization fails with threshold > 1.0."""
        with pytest.raises(ValueError, match="confidence_threshold must be between"):
            OperationClassifier(mock_llm, confidence_threshold=1.5)

    def test_init_with_invalid_threshold_low(self, mock_llm):
        """Test initialization fails with threshold < 0.0."""
        with pytest.raises(ValueError, match="confidence_threshold must be between"):
            OperationClassifier(mock_llm, confidence_threshold=-0.5)

    def test_template_loaded(self, classifier):
        """Test that Jinja2 template is loaded successfully."""
        assert classifier.template is not None


class TestOperationClassifierCREATE:
    """Test CREATE operation classification."""

    def test_create_epic_explicit(self, classifier, mock_llm):
        """Test: 'Create an epic for auth' → CREATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.95,
            "reasoning": "Clear CREATE verb with target entity type"
        })

        result = classifier.classify("Create an epic for auth")

        assert result.operation_type == OperationType.CREATE
        assert result.confidence >= 0.9
        assert "create" in result.reasoning.lower()

    def test_create_task_add_verb(self, classifier, mock_llm):
        """Test: 'Add new task to implement login' → CREATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.92,
            "reasoning": "ADD verb indicates creation of new entity"
        })

        result = classifier.classify("Add new task to implement login")

        assert result.operation_type == OperationType.CREATE
        assert result.confidence >= 0.85

    def test_create_project_start_verb(self, classifier, mock_llm):
        """Test: 'Start a new project called Tetris' → CREATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.90,
            "reasoning": "START verb with 'new' modifier indicates creation"
        })

        result = classifier.classify("Start a new project called Tetris")

        assert result.operation_type == OperationType.CREATE
        assert result.confidence >= 0.85

    def test_create_story_make_verb(self, classifier, mock_llm):
        """Test: 'Make a story for user signup' → CREATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.88,
            "reasoning": "MAKE verb indicates creation"
        })

        result = classifier.classify("Make a story for user signup")

        assert result.operation_type == OperationType.CREATE
        assert result.confidence >= 0.80

    def test_create_milestone_initialize_verb(self, classifier, mock_llm):
        """Test: 'Initialize milestone for v1.0 release' → CREATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "CREATE",
            "confidence": 0.87,
            "reasoning": "INITIALIZE verb indicates creation"
        })

        result = classifier.classify("Initialize milestone for v1.0 release")

        assert result.operation_type == OperationType.CREATE
        assert result.confidence >= 0.80


class TestOperationClassifierUPDATE:
    """Test UPDATE operation classification."""

    def test_update_status_mark_verb(self, classifier, mock_llm):
        """Test: 'Mark the manual tetris test as INACTIVE' → UPDATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "UPDATE",
            "confidence": 0.93,
            "reasoning": "Status change operation on existing entity using 'mark' verb"
        })

        result = classifier.classify("Mark the manual tetris test as INACTIVE")

        assert result.operation_type == OperationType.UPDATE
        assert result.confidence >= 0.9

    def test_update_status_set_verb_with_id(self, classifier, mock_llm):
        """Test: 'Set project 1 status to COMPLETED' → UPDATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "UPDATE",
            "confidence": 0.95,
            "reasoning": "Explicit status update on project ID 1"
        })

        result = classifier.classify("Set project 1 status to COMPLETED")

        assert result.operation_type == OperationType.UPDATE
        assert result.confidence >= 0.9

    def test_update_priority_change_verb(self, classifier, mock_llm):
        """Test: 'Change epic 2 priority to HIGH' → UPDATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "UPDATE",
            "confidence": 0.91,
            "reasoning": "CHANGE verb on existing entity (epic 2)"
        })

        result = classifier.classify("Change epic 2 priority to HIGH")

        assert result.operation_type == OperationType.UPDATE
        assert result.confidence >= 0.85

    def test_update_modify_description(self, classifier, mock_llm):
        """Test: 'Modify task 5 description' → UPDATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "UPDATE",
            "confidence": 0.89,
            "reasoning": "MODIFY verb on existing task"
        })

        result = classifier.classify("Modify task 5 description")

        assert result.operation_type == OperationType.UPDATE
        assert result.confidence >= 0.80

    def test_update_rename(self, classifier, mock_llm):
        """Test: 'Rename story 3 to User Login' → UPDATE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "UPDATE",
            "confidence": 0.92,
            "reasoning": "RENAME is an update operation on existing entity"
        })

        result = classifier.classify("Rename story 3 to User Login")

        assert result.operation_type == OperationType.UPDATE
        assert result.confidence >= 0.85


class TestOperationClassifierDELETE:
    """Test DELETE operation classification."""

    def test_delete_task_by_id(self, classifier, mock_llm):
        """Test: 'Delete task 5' → DELETE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "DELETE",
            "confidence": 0.96,
            "reasoning": "Clear DELETE verb with target entity"
        })

        result = classifier.classify("Delete task 5")

        assert result.operation_type == OperationType.DELETE
        assert result.confidence >= 0.9

    def test_delete_epic_remove_verb(self, classifier, mock_llm):
        """Test: 'Remove epic 3' → DELETE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "DELETE",
            "confidence": 0.94,
            "reasoning": "REMOVE verb indicates deletion"
        })

        result = classifier.classify("Remove epic 3")

        assert result.operation_type == OperationType.DELETE
        assert result.confidence >= 0.9

    def test_delete_milestone_cancel_verb(self, classifier, mock_llm):
        """Test: 'Cancel milestone 2' → DELETE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "DELETE",
            "confidence": 0.90,
            "reasoning": "CANCEL verb on milestone indicates deletion"
        })

        result = classifier.classify("Cancel milestone 2")

        assert result.operation_type == OperationType.DELETE
        assert result.confidence >= 0.85

    def test_delete_project_drop_verb(self, classifier, mock_llm):
        """Test: 'Drop project Tetris' → DELETE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "DELETE",
            "confidence": 0.88,
            "reasoning": "DROP verb indicates deletion"
        })

        result = classifier.classify("Drop project Tetris")

        assert result.operation_type == OperationType.DELETE
        assert result.confidence >= 0.80

    def test_delete_clear_verb(self, classifier, mock_llm):
        """Test: 'Clear all completed tasks' → DELETE"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "DELETE",
            "confidence": 0.85,
            "reasoning": "CLEAR verb indicates deletion"
        })

        result = classifier.classify("Clear all completed tasks")

        assert result.operation_type == OperationType.DELETE
        assert result.confidence >= 0.75


class TestOperationClassifierQUERY:
    """Test QUERY operation classification."""

    def test_query_show_all(self, classifier, mock_llm):
        """Test: 'Show me all projects' → QUERY"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "QUERY",
            "confidence": 0.94,
            "reasoning": "Display request using 'show' verb"
        })

        result = classifier.classify("Show me all projects")

        assert result.operation_type == OperationType.QUERY
        assert result.confidence >= 0.9

    def test_query_list_verb(self, classifier, mock_llm):
        """Test: 'List tasks for project 1' → QUERY"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "QUERY",
            "confidence": 0.92,
            "reasoning": "LIST verb requests data display"
        })

        result = classifier.classify("List tasks for project 1")

        assert result.operation_type == OperationType.QUERY
        assert result.confidence >= 0.9

    def test_query_question_whats_next(self, classifier, mock_llm):
        """Test: 'What's next for the tetris game development' → QUERY"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "QUERY",
            "confidence": 0.90,
            "reasoning": "Question seeking information about next tasks"
        })

        result = classifier.classify("What's next for the tetris game development")

        assert result.operation_type == OperationType.QUERY
        assert result.confidence >= 0.85

    def test_query_hierarchical_workplan(self, classifier, mock_llm):
        """Test: 'List the workplans for the projects' → QUERY"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "QUERY",
            "confidence": 0.92,
            "reasoning": "Request to display hierarchical project information"
        })

        result = classifier.classify("List the workplans for the projects")

        assert result.operation_type == OperationType.QUERY
        assert result.confidence >= 0.85

    def test_query_status_question(self, classifier, mock_llm):
        """Test: 'How's project 1 going?' → QUERY"""
        mock_llm.generate.return_value = json.dumps({
            "operation_type": "QUERY",
            "confidence": 0.88,
            "reasoning": "Question requesting status information"
        })

        result = classifier.classify("How's project 1 going?")

        assert result.operation_type == OperationType.QUERY
        assert result.confidence >= 0.80


class TestOperationClassifierEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self, classifier):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            classifier.classify("")

    def test_whitespace_only_input(self, classifier):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            classifier.classify("   ")

    def test_llm_failure(self, classifier, mock_llm):
        """Test that LLM failure raises OperationClassificationException."""
        mock_llm.generate.side_effect = Exception("LLM connection failed")

        with pytest.raises(OperationClassificationException, match="Failed to classify"):
            classifier.classify("Create an epic")

    def test_invalid_json_response_with_fallback(self, classifier, mock_llm):
        """Test fallback parsing when JSON is invalid."""
        # Non-JSON response with operation type in text
        mock_llm.generate.return_value = "The operation type is CREATE with high confidence"

        result = classifier.classify("Create an epic")

        assert result.operation_type == OperationType.CREATE

    def test_missing_operation_type_in_response(self, classifier, mock_llm):
        """Test error when response has no operation type."""
        mock_llm.generate.return_value = json.dumps({
            "confidence": 0.9,
            "reasoning": "Some reasoning"
        })

        with pytest.raises(OperationClassificationException, match="Failed to parse"):
            classifier.classify("Some command")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
