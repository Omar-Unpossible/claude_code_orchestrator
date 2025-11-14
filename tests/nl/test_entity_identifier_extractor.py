"""Unit tests for EntityIdentifierExtractor (ADR-016 Story 3).

Tests the entity identifier extraction component with 20 test cases covering:
- 10 name-based identifiers
- 10 ID-based identifiers

Target: 90%+ accuracy, 95%+ code coverage
"""

import pytest
import json
from unittest.mock import Mock

from src.nl.entity_identifier_extractor import (
    EntityIdentifierExtractor,
    EntityIdentifierExtractionException
)
from src.nl.types import EntityType, OperationType, IdentifierResult
from plugins.base import LLMPlugin


@pytest.fixture
def mock_llm():
    """Create a mock LLM plugin for testing."""
    llm = Mock(spec=LLMPlugin)
    return llm


@pytest.fixture
def extractor(mock_llm):
    """Create EntityIdentifierExtractor with mock LLM."""
    return EntityIdentifierExtractor(mock_llm, confidence_threshold=0.7)


class TestEntityIdentifierExtractorInit:
    """Test EntityIdentifierExtractor initialization."""

    def test_init_with_valid_threshold(self, mock_llm):
        """Test initialization with valid confidence threshold."""
        extractor = EntityIdentifierExtractor(mock_llm, confidence_threshold=0.8)
        assert extractor.confidence_threshold == 0.8
        assert extractor.llm == mock_llm

    def test_init_with_invalid_threshold(self, mock_llm):
        """Test initialization fails with invalid threshold."""
        with pytest.raises(ValueError, match="confidence_threshold must be between"):
            EntityIdentifierExtractor(mock_llm, confidence_threshold=1.5)

    def test_template_loaded(self, extractor):
        """Test that Jinja2 template is loaded successfully."""
        assert extractor.template is not None


class TestEntityIdentifierExtractorNameBased:
    """Test name-based identifier extraction."""

    def test_extract_name_update_with_article(self, extractor, mock_llm):
        """Test: 'Mark the manual tetris test as INACTIVE' → 'manual tetris test'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "manual tetris test",
            "identifier_type": "name",
            "confidence": 0.95,
            "reasoning": "Entity name after 'the' article in UPDATE operation"
        })

        result = extractor.extract(
            "Mark the manual tetris test as INACTIVE",
            entity_type=EntityType.PROJECT,
            operation=OperationType.UPDATE
        )

        assert result.identifier == "manual tetris test"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.9

    def test_extract_name_create_with_for(self, extractor, mock_llm):
        """Test: 'Create epic for auth' → 'auth'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "auth",
            "identifier_type": "name",
            "confidence": 0.88,
            "reasoning": "Entity name after 'for' preposition in CREATE operation"
        })

        result = extractor.extract(
            "Create epic for auth",
            entity_type=EntityType.EPIC,
            operation=OperationType.CREATE
        )

        assert result.identifier == "auth"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.85

    def test_extract_name_query_with_for_the(self, extractor, mock_llm):
        """Test: 'What's next for the tetris game development' → 'tetris game development'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "tetris game development",
            "identifier_type": "name",
            "confidence": 0.85,
            "reasoning": "Project name after 'for the' in question"
        })

        result = extractor.extract(
            "What's next for the tetris game development",
            entity_type=EntityType.TASK,
            operation=OperationType.QUERY
        )

        assert result.identifier == "tetris game development"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.80

    def test_extract_name_with_quotes(self, extractor, mock_llm):
        """Test: 'Add story called \"User Login Page\"' → 'User Login Page'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "User Login Page",
            "identifier_type": "name",
            "confidence": 0.94,
            "reasoning": "Entity name in quotes after 'called' keyword"
        })

        result = extractor.extract(
            "Add story called 'User Login Page'",
            entity_type=EntityType.STORY,
            operation=OperationType.CREATE
        )

        assert result.identifier == "User Login Page"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.9

    def test_extract_name_complex_phrase(self, extractor, mock_llm):
        """Test: 'Create project called Tetris Game' → 'Tetris Game'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "Tetris Game",
            "identifier_type": "name",
            "confidence": 0.92,
            "reasoning": "Project name after 'called' keyword"
        })

        result = extractor.extract(
            "Create project called Tetris Game",
            entity_type=EntityType.PROJECT,
            operation=OperationType.CREATE
        )

        assert result.identifier == "Tetris Game"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.9

    def test_extract_name_user_auth_system(self, extractor, mock_llm):
        """Test: 'Create epic for User Authentication System' → 'User Authentication System'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "User Authentication System",
            "identifier_type": "name",
            "confidence": 0.90,
            "reasoning": "Entity name after 'for' in CREATE operation"
        })

        result = extractor.extract(
            "Create epic for User Authentication System",
            entity_type=EntityType.EPIC,
            operation=OperationType.CREATE
        )

        assert result.identifier == "User Authentication System"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.85

    def test_extract_name_login_feature(self, extractor, mock_llm):
        """Test: 'Add login page to auth epic' → 'login page'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "login page",
            "identifier_type": "name",
            "confidence": 0.87,
            "reasoning": "Story name before 'to' preposition"
        })

        result = extractor.extract(
            "Add login page to auth epic",
            entity_type=EntityType.STORY,
            operation=OperationType.CREATE
        )

        assert result.identifier == "login page"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.80

    def test_extract_name_implement_validation(self, extractor, mock_llm):
        """Test: 'Implement validation for signup form' → 'validation for signup form'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "validation for signup form",
            "identifier_type": "name",
            "confidence": 0.83,
            "reasoning": "Task description after 'Implement' verb"
        })

        result = extractor.extract(
            "Implement validation for signup form",
            entity_type=EntityType.TASK,
            operation=OperationType.CREATE
        )

        assert result.identifier == "validation for signup form"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.80

    def test_extract_name_milestone_release(self, extractor, mock_llm):
        """Test: 'Create milestone for v1.0 release' → 'v1.0 release'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "v1.0 release",
            "identifier_type": "name",
            "confidence": 0.91,
            "reasoning": "Milestone name after 'for' keyword"
        })

        result = extractor.extract(
            "Create milestone for v1.0 release",
            entity_type=EntityType.MILESTONE,
            operation=OperationType.CREATE
        )

        assert result.identifier == "v1.0 release"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.85

    def test_extract_name_beta_launch(self, extractor, mock_llm):
        """Test: 'Add milestone for beta launch' → 'beta launch'"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": "beta launch",
            "identifier_type": "name",
            "confidence": 0.89,
            "reasoning": "Milestone name after 'for' keyword"
        })

        result = extractor.extract(
            "Add milestone for beta launch",
            entity_type=EntityType.MILESTONE,
            operation=OperationType.CREATE
        )

        assert result.identifier == "beta launch"
        assert isinstance(result.identifier, str)
        assert result.confidence >= 0.85


class TestEntityIdentifierExtractorIDBased:
    """Test ID-based identifier extraction."""

    def test_extract_id_simple_number(self, extractor, mock_llm):
        """Test: 'Delete task 5' → 5"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 5,
            "identifier_type": "id",
            "confidence": 0.97,
            "reasoning": "Explicit task ID in delete operation"
        })

        result = extractor.extract(
            "Delete task 5",
            entity_type=EntityType.TASK,
            operation=OperationType.DELETE
        )

        assert result.identifier == 5
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.95

    def test_extract_id_project_1(self, extractor, mock_llm):
        """Test: 'Set project 1 status to COMPLETED' → 1"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 1,
            "identifier_type": "id",
            "confidence": 0.96,
            "reasoning": "Explicit numeric ID 'project 1'"
        })

        result = extractor.extract(
            "Set project 1 status to COMPLETED",
            entity_type=EntityType.PROJECT,
            operation=OperationType.UPDATE
        )

        assert result.identifier == 1
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.95

    def test_extract_id_with_hash(self, extractor, mock_llm):
        """Test: 'Remove epic #3' → 3"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 3,
            "identifier_type": "id",
            "confidence": 0.96,
            "reasoning": "Numeric ID extracted from hash notation '#3'"
        })

        result = extractor.extract(
            "Remove epic #3",
            entity_type=EntityType.EPIC,
            operation=OperationType.DELETE
        )

        assert result.identifier == 3
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.95

    def test_extract_id_story_number(self, extractor, mock_llm):
        """Test: 'Rename story 3 to User Login' → 3"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 3,
            "identifier_type": "id",
            "confidence": 0.96,
            "reasoning": "Story ID in rename operation"
        })

        result = extractor.extract(
            "Rename story 3 to User Login",
            entity_type=EntityType.STORY,
            operation=OperationType.UPDATE
        )

        assert result.identifier == 3
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.95

    def test_extract_id_milestone_cancel(self, extractor, mock_llm):
        """Test: 'Cancel milestone 2' → 2"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 2,
            "identifier_type": "id",
            "confidence": 0.95,
            "reasoning": "Milestone ID in cancel operation"
        })

        result = extractor.extract(
            "Cancel milestone 2",
            entity_type=EntityType.MILESTONE,
            operation=OperationType.DELETE
        )

        assert result.identifier == 2
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.9

    def test_extract_id_query_filter(self, extractor, mock_llm):
        """Test: 'Show tasks for project 1' → 1 (project ID in filter)"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 1,
            "identifier_type": "id",
            "confidence": 0.95,
            "reasoning": "Project ID in query filter clause"
        })

        result = extractor.extract(
            "Show tasks for project 1",
            entity_type=EntityType.TASK,
            operation=OperationType.QUERY
        )

        assert result.identifier == 1
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.9

    def test_extract_id_epic_2(self, extractor, mock_llm):
        """Test: 'Change epic 2 priority to HIGH' → 2"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 2,
            "identifier_type": "id",
            "confidence": 0.94,
            "reasoning": "Epic ID in priority update operation"
        })

        result = extractor.extract(
            "Change epic 2 priority to HIGH",
            entity_type=EntityType.EPIC,
            operation=OperationType.UPDATE
        )

        assert result.identifier == 2
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.9

    def test_extract_id_update_task_priority(self, extractor, mock_llm):
        """Test: 'Update task 5 priority to HIGH' → 5"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 5,
            "identifier_type": "id",
            "confidence": 0.94,
            "reasoning": "Task ID in priority update"
        })

        result = extractor.extract(
            "Update task 5 priority to HIGH",
            entity_type=EntityType.TASK,
            operation=OperationType.UPDATE
        )

        assert result.identifier == 5
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.9

    def test_extract_id_delete_story(self, extractor, mock_llm):
        """Test: 'Delete story #5' → 5"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 5,
            "identifier_type": "id",
            "confidence": 0.96,
            "reasoning": "Story ID with hash notation in delete operation"
        })

        result = extractor.extract(
            "Delete story #5",
            entity_type=EntityType.STORY,
            operation=OperationType.DELETE
        )

        assert result.identifier == 5
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.95

    def test_extract_id_large_number(self, extractor, mock_llm):
        """Test: 'Show epic 42' → 42"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": 42,
            "identifier_type": "id",
            "confidence": 0.95,
            "reasoning": "Epic ID in query operation"
        })

        result = extractor.extract(
            "Show epic 42",
            entity_type=EntityType.EPIC,
            operation=OperationType.QUERY
        )

        assert result.identifier == 42
        assert isinstance(result.identifier, int)
        assert result.confidence >= 0.9


class TestEntityIdentifierExtractorBulkOperations:
    """Test bulk operation detection."""

    def test_bulk_keyword_all(self, extractor):
        """Test 'all' keyword returns bulk sentinel."""
        result = extractor.extract(
            "delete all tasks",
            entity_type=EntityType.TASK,
            operation=OperationType.DELETE
        )
        assert result.identifier == "__ALL__"
        assert result.confidence >= 0.95

    def test_bulk_keyword_every(self, extractor):
        """Test 'every' keyword returns bulk sentinel."""
        result = extractor.extract(
            "remove every epic",
            entity_type=EntityType.EPIC,
            operation=OperationType.DELETE
        )
        assert result.identifier == "__ALL__"
        assert result.confidence >= 0.95

    def test_bulk_keyword_each(self, extractor):
        """Test 'each' keyword returns bulk sentinel."""
        result = extractor.extract(
            "clear each story",
            entity_type=EntityType.STORY,
            operation=OperationType.DELETE
        )
        assert result.identifier == "__ALL__"
        assert result.confidence >= 0.95

    def test_bulk_keyword_entire(self, extractor):
        """Test 'entire' keyword returns bulk sentinel."""
        result = extractor.extract(
            "delete entire project",
            entity_type=EntityType.PROJECT,
            operation=OperationType.DELETE
        )
        assert result.identifier == "__ALL__"
        assert result.confidence >= 0.95


class TestEntityIdentifierExtractorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self, extractor):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            extractor.extract(
                "",
                entity_type=EntityType.PROJECT,
                operation=OperationType.CREATE
            )

    def test_whitespace_only_input(self, extractor):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            extractor.extract(
                "   ",
                entity_type=EntityType.TASK,
                operation=OperationType.QUERY
            )

    def test_no_identifier_query_all(self, extractor, mock_llm):
        """Test: 'Show me all projects' → None (no specific identifier)"""
        mock_llm.generate.return_value = json.dumps({
            "identifier": None,
            "identifier_type": "none",
            "confidence": 0.90,
            "reasoning": "Query requests all entities, no specific identifier"
        })

        result = extractor.extract(
            "Show me all projects",
            entity_type=EntityType.PROJECT,
            operation=OperationType.QUERY
        )

        assert result.identifier is None
        assert result.confidence >= 0.85

    def test_llm_failure(self, extractor, mock_llm):
        """Test that LLM failure raises EntityIdentifierExtractionException."""
        mock_llm.generate.side_effect = Exception("LLM connection failed")

        with pytest.raises(EntityIdentifierExtractionException, match="Failed to extract"):
            extractor.extract(
                "Create an epic",
                entity_type=EntityType.EPIC,
                operation=OperationType.CREATE
            )

    def test_invalid_json_with_quoted_fallback(self, extractor, mock_llm):
        """Test fallback parsing when JSON is invalid but has quoted string."""
        mock_llm.generate.return_value = "The identifier is 'tetris game' with high confidence"

        result = extractor.extract(
            "Create project",
            entity_type=EntityType.PROJECT,
            operation=OperationType.CREATE
        )

        assert result.identifier == "tetris game"

    def test_invalid_json_with_numeric_fallback(self, extractor, mock_llm):
        """Test fallback parsing when JSON is invalid but has number."""
        mock_llm.generate.return_value = "The identifier is 5 based on the command"

        result = extractor.extract(
            "Delete task",
            entity_type=EntityType.TASK,
            operation=OperationType.DELETE
        )

        assert result.identifier == 5

    def test_missing_identifier_in_response(self, extractor, mock_llm):
        """Test error when response has no identifier."""
        mock_llm.generate.return_value = json.dumps({
            "confidence": 0.9,
            "reasoning": "Some reasoning"
        })

        with pytest.raises(EntityIdentifierExtractionException, match="Failed to extract"):
            extractor.extract(
                "Some command",
                entity_type=EntityType.TASK,
                operation=OperationType.CREATE
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
