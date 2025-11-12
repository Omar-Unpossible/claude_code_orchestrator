"""Unit tests for ParameterExtractor (ADR-016 Story 3).

Tests the parameter extraction component with 25 test cases covering:
- 5 status updates
- 5 priority settings
- 5 dependencies
- 5 query parameters
- 5 complex combinations

Target: 90%+ accuracy, 90%+ code coverage
"""

import pytest
import json
from unittest.mock import Mock

from src.nl.parameter_extractor import (
    ParameterExtractor,
    ParameterExtractionException
)
from src.nl.types import EntityType, OperationType, ParameterResult
from plugins.base import LLMPlugin


@pytest.fixture
def mock_llm():
    """Create a mock LLM plugin for testing."""
    llm = Mock(spec=LLMPlugin)
    return llm


@pytest.fixture
def extractor(mock_llm):
    """Create ParameterExtractor with mock LLM."""
    return ParameterExtractor(mock_llm, confidence_threshold=0.7)


class TestParameterExtractorInit:
    """Test ParameterExtractor initialization."""

    def test_init_with_valid_threshold(self, mock_llm):
        """Test initialization with valid confidence threshold."""
        extractor = ParameterExtractor(mock_llm, confidence_threshold=0.8)
        assert extractor.confidence_threshold == 0.8
        assert extractor.llm == mock_llm

    def test_init_with_invalid_threshold(self, mock_llm):
        """Test initialization fails with invalid threshold."""
        with pytest.raises(ValueError, match="confidence_threshold must be between"):
            ParameterExtractor(mock_llm, confidence_threshold=1.5)

    def test_template_loaded(self, extractor):
        """Test that Jinja2 template is loaded successfully."""
        assert extractor.template is not None


class TestParameterExtractorStatusUpdates:
    """Test status parameter extraction."""

    def test_extract_status_mark_inactive(self, extractor, mock_llm):
        """Test: 'Mark project as INACTIVE' → {status: 'INACTIVE'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"status": "INACTIVE"},
            "confidence": 0.95,
            "reasoning": "Status parameter extracted from 'mark as INACTIVE'"
        })

        result = extractor.extract(
            "Mark project as INACTIVE",
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT
        )

        assert result.parameters == {"status": "INACTIVE"}
        assert result.confidence >= 0.9

    def test_extract_status_set_completed(self, extractor, mock_llm):
        """Test: 'Set project 1 status to COMPLETED' → {status: 'COMPLETED'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"status": "COMPLETED"},
            "confidence": 0.94,
            "reasoning": "Status parameter extracted from 'status to COMPLETED'"
        })

        result = extractor.extract(
            "Set project 1 status to COMPLETED",
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT
        )

        assert result.parameters == {"status": "COMPLETED"}
        assert result.confidence >= 0.9

    def test_extract_status_change_paused(self, extractor, mock_llm):
        """Test: 'Change epic 2 to PAUSED' → {status: 'PAUSED'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"status": "PAUSED"},
            "confidence": 0.92,
            "reasoning": "Status parameter extracted from 'to PAUSED'"
        })

        result = extractor.extract(
            "Change epic 2 to PAUSED",
            operation=OperationType.UPDATE,
            entity_type=EntityType.EPIC
        )

        assert result.parameters == {"status": "PAUSED"}
        assert result.confidence >= 0.9

    def test_extract_status_set_active(self, extractor, mock_llm):
        """Test: 'Set task status to ACTIVE' → {status: 'ACTIVE'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"status": "ACTIVE"},
            "confidence": 0.93,
            "reasoning": "Status parameter extracted"
        })

        result = extractor.extract(
            "Set task status to ACTIVE",
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {"status": "ACTIVE"}
        assert result.confidence >= 0.9

    def test_extract_status_mark_blocked(self, extractor, mock_llm):
        """Test: 'Mark story as BLOCKED' → {status: 'BLOCKED'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"status": "BLOCKED"},
            "confidence": 0.91,
            "reasoning": "Status parameter extracted from 'mark as BLOCKED'"
        })

        result = extractor.extract(
            "Mark story as BLOCKED",
            operation=OperationType.UPDATE,
            entity_type=EntityType.STORY
        )

        assert result.parameters == {"status": "BLOCKED"}
        assert result.confidence >= 0.9


class TestParameterExtractorPrioritySettings:
    """Test priority parameter extraction."""

    def test_extract_priority_high(self, extractor, mock_llm):
        """Test: 'Create task with priority HIGH' → {priority: 'HIGH'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"priority": "HIGH"},
            "confidence": 0.93,
            "reasoning": "Priority parameter extracted from 'with priority HIGH'"
        })

        result = extractor.extract(
            "Create task with priority HIGH",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {"priority": "HIGH"}
        assert result.confidence >= 0.9

    def test_extract_priority_update_high(self, extractor, mock_llm):
        """Test: 'Update task 5 priority to HIGH' → {priority: 'HIGH'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"priority": "HIGH"},
            "confidence": 0.94,
            "reasoning": "Priority parameter extracted"
        })

        result = extractor.extract(
            "Update task 5 priority to HIGH",
            operation=OperationType.UPDATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {"priority": "HIGH"}
        assert result.confidence >= 0.9

    def test_extract_priority_medium(self, extractor, mock_llm):
        """Test: 'Set epic priority to MEDIUM' → {priority: 'MEDIUM'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"priority": "MEDIUM"},
            "confidence": 0.92,
            "reasoning": "Priority parameter extracted"
        })

        result = extractor.extract(
            "Set epic priority to MEDIUM",
            operation=OperationType.UPDATE,
            entity_type=EntityType.EPIC
        )

        assert result.parameters == {"priority": "MEDIUM"}
        assert result.confidence >= 0.9

    def test_extract_priority_low(self, extractor, mock_llm):
        """Test: 'Change story priority to LOW' → {priority: 'LOW'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"priority": "LOW"},
            "confidence": 0.91,
            "reasoning": "Priority parameter extracted"
        })

        result = extractor.extract(
            "Change story priority to LOW",
            operation=OperationType.UPDATE,
            entity_type=EntityType.STORY
        )

        assert result.parameters == {"priority": "LOW"}
        assert result.confidence >= 0.9

    def test_extract_priority_change_high(self, extractor, mock_llm):
        """Test: 'Change epic 2 priority to HIGH' → {priority: 'HIGH'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"priority": "HIGH"},
            "confidence": 0.93,
            "reasoning": "Priority parameter extracted from 'priority to HIGH'"
        })

        result = extractor.extract(
            "Change epic 2 priority to HIGH",
            operation=OperationType.UPDATE,
            entity_type=EntityType.EPIC
        )

        assert result.parameters == {"priority": "HIGH"}
        assert result.confidence >= 0.9


class TestParameterExtractorDependencies:
    """Test dependency parameter extraction."""

    def test_extract_single_dependency(self, extractor, mock_llm):
        """Test: 'Create task depends on task 3' → {dependencies: [3]}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"dependencies": [3]},
            "confidence": 0.91,
            "reasoning": "Dependency extracted from 'depends on task 3'"
        })

        result = extractor.extract(
            "Create task depends on task 3",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {"dependencies": [3]}
        assert result.confidence >= 0.85

    def test_extract_multiple_dependencies_and(self, extractor, mock_llm):
        """Test: 'Add task that requires tasks 5 and 7' → {dependencies: [5, 7]}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"dependencies": [5, 7]},
            "confidence": 0.89,
            "reasoning": "Multiple dependencies extracted from 'requires tasks 5 and 7'"
        })

        result = extractor.extract(
            "Add task that requires tasks 5 and 7",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {"dependencies": [5, 7]}
        assert result.confidence >= 0.85

    def test_extract_multiple_dependencies_comma(self, extractor, mock_llm):
        """Test: 'Create task depends on 3, 5, and 8' → {dependencies: [3, 5, 8]}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"dependencies": [3, 5, 8]},
            "confidence": 0.88,
            "reasoning": "Multiple dependencies extracted"
        })

        result = extractor.extract(
            "Create task depends on 3, 5, and 8",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {"dependencies": [3, 5, 8]}
        assert result.confidence >= 0.85

    def test_extract_dependency_after_epic(self, extractor, mock_llm):
        """Test: 'Add story after epic 2' → {dependencies: [2]}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"dependencies": [2]},
            "confidence": 0.86,
            "reasoning": "Dependency extracted from 'after epic 2'"
        })

        result = extractor.extract(
            "Add story after epic 2",
            operation=OperationType.CREATE,
            entity_type=EntityType.STORY
        )

        assert result.parameters == {"dependencies": [2]}
        assert result.confidence >= 0.80

    def test_extract_dependency_requires(self, extractor, mock_llm):
        """Test: 'New task requires task 1' → {dependencies: [1]}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"dependencies": [1]},
            "confidence": 0.90,
            "reasoning": "Dependency extracted from 'requires task 1'"
        })

        result = extractor.extract(
            "New task requires task 1",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {"dependencies": [1]}
        assert result.confidence >= 0.85


class TestParameterExtractorQueryParameters:
    """Test query parameter extraction."""

    def test_extract_query_limit_top_5(self, extractor, mock_llm):
        """Test: 'Show top 5 tasks' → {limit: 5, order: 'priority'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"limit": 5, "order": "priority"},
            "confidence": 0.92,
            "reasoning": "Limit and ordering extracted from 'top 5'"
        })

        result = extractor.extract(
            "Show top 5 tasks",
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK
        )

        assert result.parameters["limit"] == 5
        assert result.parameters["order"] == "priority"
        assert result.confidence >= 0.9

    def test_extract_query_filter_pending(self, extractor, mock_llm):
        """Test: 'Show pending tasks' → {filter: {status: 'PENDING'}}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"filter": {"status": "PENDING"}},
            "confidence": 0.88,
            "reasoning": "Status filter extracted from 'pending tasks'"
        })

        result = extractor.extract(
            "Show pending tasks",
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK
        )

        assert result.parameters["filter"]["status"] == "PENDING"
        assert result.confidence >= 0.85

    def test_extract_query_hierarchical_workplan(self, extractor, mock_llm):
        """Test: 'List the workplans for the projects' → {query_type: 'hierarchical'}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"query_type": "hierarchical"},
            "confidence": 0.90,
            "reasoning": "Hierarchical query type inferred from 'workplans'"
        })

        result = extractor.extract(
            "List the workplans for the projects",
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT
        )

        assert result.parameters["query_type"] == "hierarchical"
        assert result.confidence >= 0.85

    def test_extract_query_next_steps(self, extractor, mock_llm):
        """Test: 'What's next for the tetris game' → {query_type: 'next_steps', filter, limit}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {
                "query_type": "next_steps",
                "filter": {"status": "PENDING"},
                "limit": 5
            },
            "confidence": 0.87,
            "reasoning": "Next steps query with pending filter and default limit"
        })

        result = extractor.extract(
            "What's next for the tetris game",
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK
        )

        assert result.parameters["query_type"] == "next_steps"
        assert result.parameters["limit"] == 5
        assert result.confidence >= 0.80

    def test_extract_query_limit_first_10(self, extractor, mock_llm):
        """Test: 'Show first 10 epics' → {limit: 10}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {"limit": 10},
            "confidence": 0.91,
            "reasoning": "Limit extracted from 'first 10'"
        })

        result = extractor.extract(
            "Show first 10 epics",
            operation=OperationType.QUERY,
            entity_type=EntityType.EPIC
        )

        assert result.parameters["limit"] == 10
        assert result.confidence >= 0.85


class TestParameterExtractorComplexCombinations:
    """Test complex multi-parameter extraction."""

    def test_extract_complex_priority_and_dependency(self, extractor, mock_llm):
        """Test: 'Create task with priority HIGH depends on task 3' → {priority, dependencies}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {
                "priority": "HIGH",
                "dependencies": [3]
            },
            "confidence": 0.90,
            "reasoning": "Both priority and dependency parameters extracted"
        })

        result = extractor.extract(
            "Create task with priority HIGH depends on task 3",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters["priority"] == "HIGH"
        assert result.parameters["dependencies"] == [3]
        assert result.confidence >= 0.85

    def test_extract_complex_priority_medium_deps(self, extractor, mock_llm):
        """Test: 'Add story with priority MEDIUM requires stories 1 and 2'"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {
                "priority": "MEDIUM",
                "dependencies": [1, 2]
            },
            "confidence": 0.88,
            "reasoning": "Priority and multiple dependencies extracted"
        })

        result = extractor.extract(
            "Add story with priority MEDIUM requires stories 1 and 2",
            operation=OperationType.CREATE,
            entity_type=EntityType.STORY
        )

        assert result.parameters["priority"] == "MEDIUM"
        assert result.parameters["dependencies"] == [1, 2]
        assert result.confidence >= 0.80

    def test_extract_complex_query_limit_and_filter(self, extractor, mock_llm):
        """Test: 'Show top 3 pending tasks' → {limit, filter}"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {
                "limit": 3,
                "filter": {"status": "PENDING"}
            },
            "confidence": 0.89,
            "reasoning": "Limit and status filter extracted"
        })

        result = extractor.extract(
            "Show top 3 pending tasks",
            operation=OperationType.QUERY,
            entity_type=EntityType.TASK
        )

        assert result.parameters["limit"] == 3
        assert result.parameters["filter"]["status"] == "PENDING"
        assert result.confidence >= 0.85

    def test_extract_no_parameters_delete(self, extractor, mock_llm):
        """Test: 'Delete task 5' → {} (no parameters)"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {},
            "confidence": 0.85,
            "reasoning": "No additional parameters for simple delete operation"
        })

        result = extractor.extract(
            "Delete task 5",
            operation=OperationType.DELETE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {}
        assert result.confidence >= 0.80

    def test_extract_no_parameters_simple_query(self, extractor, mock_llm):
        """Test: 'List all projects' → {} (no specific parameters)"""
        mock_llm.generate.return_value = json.dumps({
            "parameters": {},
            "confidence": 0.86,
            "reasoning": "No specific parameters for simple list query"
        })

        result = extractor.extract(
            "List all projects",
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT
        )

        assert result.parameters == {}
        assert result.confidence >= 0.80


class TestParameterExtractorEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self, extractor):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            extractor.extract(
                "",
                operation=OperationType.CREATE,
                entity_type=EntityType.TASK
            )

    def test_whitespace_only_input(self, extractor):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            extractor.extract(
                "   ",
                operation=OperationType.QUERY,
                entity_type=EntityType.PROJECT
            )

    def test_llm_failure(self, extractor, mock_llm):
        """Test that LLM failure raises ParameterExtractionException."""
        mock_llm.generate.side_effect = Exception("LLM connection failed")

        with pytest.raises(ParameterExtractionException, match="Failed to extract"):
            extractor.extract(
                "Create task",
                operation=OperationType.CREATE,
                entity_type=EntityType.TASK
            )

    def test_invalid_json_returns_empty_dict(self, extractor, mock_llm):
        """Test that invalid JSON returns empty parameters dict."""
        mock_llm.generate.return_value = "No valid JSON here"

        result = extractor.extract(
            "Some command",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {}

    def test_missing_parameters_key(self, extractor, mock_llm):
        """Test response with no parameters key returns empty dict."""
        mock_llm.generate.return_value = json.dumps({
            "confidence": 0.9,
            "reasoning": "Some reasoning"
        })

        result = extractor.extract(
            "Some command",
            operation=OperationType.CREATE,
            entity_type=EntityType.TASK
        )

        assert result.parameters == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
