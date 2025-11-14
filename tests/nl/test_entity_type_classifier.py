"""Unit tests for EntityTypeClassifier (ADR-016 Story 2).

Tests the entity type classification component with 25 test cases covering:
- 5 PROJECT examples with different operations
- 5 EPIC examples with different operations
- 5 STORY examples with different operations
- 5 TASK examples with different operations
- 5 MILESTONE examples with different operations

Target: 95%+ accuracy, 95%+ code coverage
"""

import pytest
import json
from unittest.mock import Mock

from src.nl.entity_type_classifier import (
    EntityTypeClassifier,
    EntityTypeClassificationException
)
from src.nl.types import EntityType, OperationType, EntityTypeResult
from plugins.base import LLMPlugin


@pytest.fixture
def mock_llm():
    """Create a mock LLM plugin for testing."""
    llm = Mock(spec=LLMPlugin)
    return llm


@pytest.fixture
def classifier(mock_llm):
    """Create EntityTypeClassifier with mock LLM."""
    return EntityTypeClassifier(mock_llm, confidence_threshold=0.7)


class TestEntityTypeClassifierInit:
    """Test EntityTypeClassifier initialization."""

    def test_init_with_valid_threshold(self, mock_llm):
        """Test initialization with valid confidence threshold."""
        classifier = EntityTypeClassifier(mock_llm, confidence_threshold=0.8)
        assert classifier.confidence_threshold == 0.8
        assert classifier.llm == mock_llm

    def test_init_with_invalid_threshold(self, mock_llm):
        """Test initialization fails with invalid threshold."""
        with pytest.raises(ValueError, match="confidence_threshold must be between"):
            EntityTypeClassifier(mock_llm, confidence_threshold=1.5)

    def test_template_loaded(self, classifier):
        """Test that Jinja2 template is loaded successfully."""
        assert classifier.template is not None


class TestEntityTypeClassifierPROJECT:
    """Test PROJECT entity type classification."""

    def test_project_update_status_change(self, classifier, mock_llm):
        """Test: 'Mark the manual tetris test as INACTIVE' + UPDATE → PROJECT"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "PROJECT",
            "confidence": 0.92,
            "reasoning": "Status change operation on named entity suggests project-level update"
        })

        entity_types, confidence = classifier.classify(
            "Mark the manual tetris test as INACTIVE",
            operation=OperationType.UPDATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.PROJECT
        assert confidence >= 0.9

    def test_project_query_explicit(self, classifier, mock_llm):
        """Test: 'Show me all projects' + QUERY → PROJECT"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "PROJECT",
            "confidence": 0.95,
            "reasoning": "Explicit 'projects' plural indicates PROJECT entity type"
        })

        entity_types, confidence = classifier.classify(
            "Show me all projects",
            operation=OperationType.QUERY
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.PROJECT
        assert confidence >= 0.9

    def test_project_create_explicit(self, classifier, mock_llm):
        """Test: 'Create project called Tetris' + CREATE → PROJECT"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "PROJECT",
            "confidence": 0.94,
            "reasoning": "Explicit 'project' entity type mentioned"
        })

        entity_types, confidence = classifier.classify(
            "Create project called Tetris",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.PROJECT
        assert confidence >= 0.9

    def test_project_update_by_id(self, classifier, mock_llm):
        """Test: 'Set project 1 status to COMPLETED' + UPDATE → PROJECT"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "PROJECT",
            "confidence": 0.95,
            "reasoning": "Explicit 'project 1' reference with status change"
        })

        entity_types, confidence = classifier.classify(
            "Set project 1 status to COMPLETED",
            operation=OperationType.UPDATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.PROJECT
        assert confidence >= 0.9

    def test_project_delete(self, classifier, mock_llm):
        """Test: 'Delete project Tetris' + DELETE → PROJECT"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "PROJECT",
            "confidence": 0.93,
            "reasoning": "Explicit 'project' reference in delete operation"
        })

        entity_types, confidence = classifier.classify(
            "Delete project Tetris",
            operation=OperationType.DELETE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.PROJECT
        assert confidence >= 0.9


class TestEntityTypeClassifierEPIC:
    """Test EPIC entity type classification."""

    def test_epic_create_explicit(self, classifier, mock_llm):
        """Test: 'Create epic for auth' + CREATE → EPIC"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "EPIC",
            "confidence": 0.96,
            "reasoning": "Explicit 'epic' entity type mentioned"
        })

        entity_types, confidence = classifier.classify(
            "Create epic for auth",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.EPIC
        assert confidence >= 0.9

    def test_epic_update_status(self, classifier, mock_llm):
        """Test: 'Change epic 2 to PAUSED' + UPDATE → EPIC"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "EPIC",
            "confidence": 0.94,
            "reasoning": "Explicit 'epic 2' reference with status change"
        })

        entity_types, confidence = classifier.classify(
            "Change epic 2 to PAUSED",
            operation=OperationType.UPDATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.EPIC
        assert confidence >= 0.9

    def test_epic_delete_by_id(self, classifier, mock_llm):
        """Test: 'Remove epic 3' + DELETE → EPIC"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "EPIC",
            "confidence": 0.95,
            "reasoning": "Explicit 'epic 3' reference in delete operation"
        })

        entity_types, confidence = classifier.classify(
            "Remove epic 3",
            operation=OperationType.DELETE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.EPIC
        assert confidence >= 0.9

    def test_epic_query_list(self, classifier, mock_llm):
        """Test: 'List all epics' + QUERY → EPIC"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "EPIC",
            "confidence": 0.93,
            "reasoning": "Explicit 'epics' plural indicates EPIC entity type"
        })

        entity_types, confidence = classifier.classify(
            "List all epics",
            operation=OperationType.QUERY
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.EPIC
        assert confidence >= 0.9

    def test_epic_create_inferred_large_system(self, classifier, mock_llm):
        """Test: 'Create auth system' + CREATE → EPIC (inferred from complexity)"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "EPIC",
            "confidence": 0.88,
            "reasoning": "Large system feature suggests EPIC complexity"
        })

        entity_types, confidence = classifier.classify(
            "Create auth system",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.EPIC
        assert confidence >= 0.85


class TestEntityTypeClassifierSTORY:
    """Test STORY entity type classification."""

    def test_story_create_explicit(self, classifier, mock_llm):
        """Test: 'Add story for user signup' + CREATE → STORY"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "STORY",
            "confidence": 0.94,
            "reasoning": "Explicit 'story' entity type mentioned"
        })

        entity_types, confidence = classifier.classify(
            "Add story for user signup",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.STORY
        assert confidence >= 0.9

    def test_story_create_user_feature(self, classifier, mock_llm):
        """Test: 'Add login page to auth epic' + CREATE → STORY (user-facing)"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "STORY",
            "confidence": 0.88,
            "reasoning": "User-facing page feature suggests STORY (user deliverable)"
        })

        entity_types, confidence = classifier.classify(
            "Add login page to auth epic",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.STORY
        assert confidence >= 0.85

    def test_story_update_by_id(self, classifier, mock_llm):
        """Test: 'Rename story 3 to User Login' + UPDATE → STORY"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "STORY",
            "confidence": 0.93,
            "reasoning": "Explicit 'story 3' reference in update operation"
        })

        entity_types, confidence = classifier.classify(
            "Rename story 3 to User Login",
            operation=OperationType.UPDATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.STORY
        assert confidence >= 0.9

    def test_story_query_for_epic(self, classifier, mock_llm):
        """Test: 'Show stories for epic 1' + QUERY → STORY"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "STORY",
            "confidence": 0.95,
            "reasoning": "Explicit 'stories' plural indicates STORY entity type"
        })

        entity_types, confidence = classifier.classify(
            "Show stories for epic 1",
            operation=OperationType.QUERY
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.STORY
        assert confidence >= 0.9

    def test_story_delete(self, classifier, mock_llm):
        """Test: 'Delete story #5' + DELETE → STORY"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "STORY",
            "confidence": 0.94,
            "reasoning": "Explicit 'story' reference with ID in delete operation"
        })

        entity_types, confidence = classifier.classify(
            "Delete story #5",
            operation=OperationType.DELETE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.STORY
        assert confidence >= 0.9


class TestEntityTypeClassifierTASK:
    """Test TASK entity type classification."""

    def test_task_query_explicit(self, classifier, mock_llm):
        """Test: 'Show tasks for project 1' + QUERY → TASK"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "TASK",
            "confidence": 0.95,
            "reasoning": "Explicit 'tasks' plural indicates TASK entity type"
        })

        entity_types, confidence = classifier.classify(
            "Show tasks for project 1",
            operation=OperationType.QUERY
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.TASK
        assert confidence >= 0.9

    def test_task_create_technical_work(self, classifier, mock_llm):
        """Test: 'Implement validation for signup form' + CREATE → TASK"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "TASK",
            "confidence": 0.85,
            "reasoning": "Technical implementation work suggests TASK"
        })

        entity_types, confidence = classifier.classify(
            "Implement validation for signup form",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.TASK
        assert confidence >= 0.80

    def test_task_update_priority(self, classifier, mock_llm):
        """Test: 'Update task 5 priority to HIGH' + UPDATE → TASK"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "TASK",
            "confidence": 0.94,
            "reasoning": "Explicit 'task 5' reference in update operation"
        })

        entity_types, confidence = classifier.classify(
            "Update task 5 priority to HIGH",
            operation=OperationType.UPDATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.TASK
        assert confidence >= 0.9

    def test_task_delete_by_id(self, classifier, mock_llm):
        """Test: 'Delete task 5' + DELETE → TASK"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "TASK",
            "confidence": 0.96,
            "reasoning": "Explicit 'task 5' reference in delete operation"
        })

        entity_types, confidence = classifier.classify(
            "Delete task 5",
            operation=OperationType.DELETE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.TASK
        assert confidence >= 0.9

    def test_task_query_next_steps(self, classifier, mock_llm):
        """Test: 'What's next for the tetris game development' + QUERY → TASK"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "TASK",
            "confidence": 0.85,
            "reasoning": "Next steps query typically refers to pending tasks"
        })

        entity_types, confidence = classifier.classify(
            "What's next for the tetris game development",
            operation=OperationType.QUERY
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.TASK
        assert confidence >= 0.80


class TestEntityTypeClassifierMILESTONE:
    """Test MILESTONE entity type classification."""

    def test_milestone_create_explicit(self, classifier, mock_llm):
        """Test: 'Create milestone for v1.0 release' + CREATE → MILESTONE"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "MILESTONE",
            "confidence": 0.93,
            "reasoning": "Explicit 'milestone' with version/release context"
        })

        entity_types, confidence = classifier.classify(
            "Create milestone for v1.0 release",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.MILESTONE
        assert confidence >= 0.9

    def test_milestone_update_by_id(self, classifier, mock_llm):
        """Test: 'Update milestone 2 date' + UPDATE → MILESTONE"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "MILESTONE",
            "confidence": 0.92,
            "reasoning": "Explicit 'milestone 2' reference in update operation"
        })

        entity_types, confidence = classifier.classify(
            "Update milestone 2 date",
            operation=OperationType.UPDATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.MILESTONE
        assert confidence >= 0.9

    def test_milestone_delete(self, classifier, mock_llm):
        """Test: 'Cancel milestone 2' + DELETE → MILESTONE"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "MILESTONE",
            "confidence": 0.90,
            "reasoning": "Cancel operation on milestone indicates deletion"
        })

        entity_types, confidence = classifier.classify(
            "Cancel milestone 2",
            operation=OperationType.DELETE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.MILESTONE
        assert confidence >= 0.85

    def test_milestone_query_roadmap(self, classifier, mock_llm):
        """Test: 'Show milestones' + QUERY → MILESTONE"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "MILESTONE",
            "confidence": 0.94,
            "reasoning": "Explicit 'milestones' plural indicates MILESTONE entity type"
        })

        entity_types, confidence = classifier.classify(
            "Show milestones",
            operation=OperationType.QUERY
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.MILESTONE
        assert confidence >= 0.9

    def test_milestone_create_beta_launch(self, classifier, mock_llm):
        """Test: 'Add milestone for beta launch' + CREATE → MILESTONE"""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "MILESTONE",
            "confidence": 0.91,
            "reasoning": "Milestone with launch/release context"
        })

        entity_types, confidence = classifier.classify(
            "Add milestone for beta launch",
            operation=OperationType.CREATE
        )

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.MILESTONE
        assert confidence >= 0.85


class TestEntityTypeClassifierEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self, classifier):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            classifier.classify("", operation=OperationType.CREATE)

    def test_whitespace_only_input(self, classifier):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            classifier.classify("   ", operation=OperationType.QUERY)

    def test_llm_failure(self, classifier, mock_llm):
        """Test that LLM failure raises EntityTypeClassificationException."""
        mock_llm.generate.side_effect = Exception("LLM connection failed")

        with pytest.raises(EntityTypeClassificationException, match="Failed to classify"):
            entity_types, confidence = classifier.classify("Create an epic", operation=OperationType.CREATE)

    def test_invalid_json_response_with_fallback(self, classifier, mock_llm):
        """Test fallback parsing when JSON is invalid."""
        # Non-JSON response with entity type in text
        mock_llm.generate.return_value = "The entity type is EPIC with high confidence"

        entity_types, confidence = classifier.classify("Create an epic", operation=OperationType.CREATE)

        assert len(entity_types) == 1
        assert entity_types[0] == EntityType.EPIC

    def test_missing_entity_type_in_response(self, classifier, mock_llm):
        """Test error when response has no entity type."""
        mock_llm.generate.return_value = json.dumps({
            "confidence": 0.9,
            "reasoning": "Some reasoning"
        })

        with pytest.raises(EntityTypeClassificationException, match="Failed to parse"):
            classifier.classify("Some command", operation=OperationType.CREATE)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
