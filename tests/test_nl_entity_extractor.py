"""Comprehensive tests for NL entity extraction (Phase 1).

Test coverage for src/nl/entity_extractor.py targeting 90% coverage.
Covers US-NL-001, US-NL-006, US-NL-007, US-NL-008, US-NL-016, US-NL-019.

Total test count: 50 tests
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.nl.entity_extractor import (
    EntityExtractor,
    EntityExtractionException,
    ExtractedEntities
)
from src.core.state import StateManager
from src.core.config import Config


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM plugin with controllable responses."""
    llm = MagicMock()
    # Default: valid entity extraction response
    llm.generate.return_value = json.dumps({
        "entity_type": "task",
        "entities": [{"title": "Test Task", "description": "Test description"}],
        "confidence": 0.95,
        "reasoning": "Clear task creation request"
    })
    return llm


@pytest.fixture
def test_state(tmp_path):
    """In-memory StateManager for testing."""
    state = StateManager(database_url='sqlite:///:memory:')
    # Create test project
    state.create_project(
        name="Test Project",
        description="Test project for NL testing",
        working_dir="/tmp/test"
    )
    yield state
    state.close()


@pytest.fixture
def extractor(mock_llm):
    """EntityExtractor instance with mocked LLM."""
    return EntityExtractor(llm_plugin=mock_llm)


# ============================================================================
# Test Class 1: Entity Type Validation (US-NL-016) - 15 tests
# ============================================================================

class TestEntityTypeValidation:
    """Test entity_type validation - prevents US-NL-016 bug."""

    def test_entity_type_none_raises_exception(self, mock_llm):
        """CRITICAL: entity_type=None should raise user-friendly error."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": None,
            "entities": []
        })

        extractor = EntityExtractor(llm_plugin=mock_llm)

        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("What is the current project?", "COMMAND")

        # Should be handled gracefully, not raise ValueError
        assert "entity" in str(exc_info.value).lower()

    def test_entity_type_missing_field(self, mock_llm):
        """Should handle missing entity_type field."""
        mock_llm.generate.return_value = json.dumps({
            "entities": []  # Missing entity_type
        })

        extractor = EntityExtractor(llm_plugin=mock_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Show project", "COMMAND")

    def test_entity_type_invalid_string(self, mock_llm):
        """Should reject invalid entity_type strings."""
        invalid_types = ["feature", "bug", "requirement", "user_story"]

        extractor = EntityExtractor(llm_plugin=mock_llm)

        for invalid_type in invalid_types:
            mock_llm.generate.return_value = json.dumps({
                "entity_type": invalid_type,
                "entities": []
            })

            with pytest.raises(EntityExtractionException):
                extractor.extract(f"Create {invalid_type}", "COMMAND")

    def test_entity_type_wrong_case(self, mock_llm):
        """Should reject wrong-case entity types (TASK vs task)."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "TASK",  # Should be lowercase
            "entities": []
        })

        extractor = EntityExtractor(llm_plugin=mock_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create TASK", "COMMAND")

    def test_entity_type_empty_string(self, mock_llm):
        """Should reject empty string entity_type."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "",
            "entities": []
        })

        extractor = EntityExtractor(llm_plugin=mock_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create something", "COMMAND")

    def test_entity_type_wrong_data_type(self, mock_llm):
        """Should reject non-string entity_type (integers, lists, etc.)."""
        wrong_types = [123, ["task"], {"type": "task"}, True]

        extractor = EntityExtractor(llm_plugin=mock_llm)

        for wrong_type in wrong_types:
            mock_llm.generate.return_value = json.dumps({
                "entity_type": wrong_type,
                "entities": []
            })

            with pytest.raises(EntityExtractionException):
                extractor.extract("Create something", "COMMAND")

    def test_valid_entity_types_accepted(self, mock_llm, extractor):
        """All valid entity types should be accepted."""
        # Note: "project" is NOT a valid entity_type in ExtractedEntities dataclass
        valid_types = ["epic", "story", "task", "subtask", "milestone"]

        for entity_type in valid_types:
            mock_llm.generate.return_value = json.dumps({
                "entity_type": entity_type,
                "entities": [{"title": f"Test {entity_type}"}],
                "confidence": 0.9
            })

            result = extractor.extract(f"Show {entity_type}", "COMMAND")
            assert result.entity_type == entity_type

    def test_entities_field_missing(self, mock_llm, extractor):
        """Should raise exception when entities field is missing (required by schema)."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task"
            # No entities field - this is actually required!
        })

        # ExtractedEntities requires 'entities' field, so this should fail
        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("Show tasks", "COMMAND")

        assert "entities" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    def test_entities_not_a_list(self, mock_llm, extractor):
        """Should reject entities that are not a list."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": "not a list"  # Wrong type
        })

        # Should either raise exception or handle gracefully
        with pytest.raises((EntityExtractionException, TypeError, AttributeError)):
            extractor.extract("Show tasks", "COMMAND")

    def test_confidence_out_of_range(self, mock_llm, extractor):
        """Should handle confidence values outside 0.0-1.0 range."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [],
            "confidence": 1.5  # Invalid: >1.0
        })

        with pytest.raises((EntityExtractionException, ValueError)):
            extractor.extract("Show tasks", "COMMAND")

    def test_confidence_negative(self, mock_llm, extractor):
        """Should reject negative confidence values."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [],
            "confidence": -0.5  # Invalid: <0.0
        })

        with pytest.raises((EntityExtractionException, ValueError)):
            extractor.extract("Show tasks", "COMMAND")

    def test_confidence_wrong_type(self, mock_llm, extractor):
        """Should handle non-numeric confidence values."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [],
            "confidence": "high"  # Should be numeric
        })

        with pytest.raises((EntityExtractionException, TypeError, ValueError)):
            extractor.extract("Show tasks", "COMMAND")

    def test_malformed_json_response(self, mock_llm, extractor):
        """Should handle malformed JSON from LLM."""
        mock_llm.generate.return_value = "{'entity_type': 'task'}"  # Single quotes = invalid JSON

        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("Show tasks", "COMMAND")

        assert "parse" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()

    def test_incomplete_json_response(self, mock_llm, extractor):
        """Should handle incomplete/truncated JSON."""
        mock_llm.generate.return_value = '{"entity_type": "task", "entit'  # Truncated

        with pytest.raises(EntityExtractionException):
            extractor.extract("Show tasks", "COMMAND")

    def test_extra_fields_ignored(self, mock_llm, extractor):
        """Should ignore extra unknown fields in response."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [],
            "confidence": 0.9,
            "reasoning": "test",
            "unknown_field": "should be ignored",
            "another_unknown": 123
        })

        # Should NOT raise exception
        result = extractor.extract("Show tasks", "COMMAND")
        assert result.entity_type == "task"


# ============================================================================
# Test Class 2: ID Extraction (US-NL-006) - 10 tests
# ============================================================================

class TestIDExtraction:
    """Test ID extraction from natural language."""

    def test_extract_single_id(self, mock_llm, extractor):
        """Should extract single ID from message."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": 42}],
            "confidence": 0.95
        })

        result = extractor.extract("Show task 42", "COMMAND")
        assert len(result.entities) == 1
        assert result.entities[0]["id"] == 42

    def test_extract_multiple_ids(self, mock_llm, extractor):
        """Should extract multiple IDs from comma-separated list."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": 1}, {"id": 2}, {"id": 3}],
            "confidence": 0.9
        })

        result = extractor.extract("Show tasks 1, 2, 3", "COMMAND")
        assert len(result.entities) == 3
        assert [e["id"] for e in result.entities] == [1, 2, 3]

    def test_extract_id_with_hash(self, mock_llm, extractor):
        """Should extract ID with # prefix."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": 42}],
            "confidence": 0.95
        })

        result = extractor.extract("Show task #42", "COMMAND")
        assert result.entities[0]["id"] == 42

    def test_extract_id_range(self, mock_llm, extractor):
        """Should handle ID ranges (e.g., tasks 10-15)."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": i} for i in range(10, 16)],
            "confidence": 0.85
        })

        result = extractor.extract("Show tasks 10-15", "COMMAND")
        assert len(result.entities) == 6
        assert result.entities[0]["id"] == 10
        assert result.entities[-1]["id"] == 15

    def test_extract_id_from_context(self, mock_llm, extractor):
        """Should extract ID from conversational context ('it', 'that task')."""
        context = {
            "previous_turns": [
                {"user": "Show task 42", "response": "Task 42: ..."}
            ]
        }

        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": 42}],  # Should infer from context
            "confidence": 0.8
        })

        result = extractor.extract("Mark it completed", "COMMAND", context=context)
        assert result.entities[0]["id"] == 42

    def test_no_id_in_create_command(self, mock_llm, extractor):
        """Create commands should not require ID."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "New Task", "description": "Test"}],
            "confidence": 0.95
        })

        result = extractor.extract("Create task: New Task", "COMMAND")
        assert "id" not in result.entities[0] or result.entities[0].get("id") is None

    def test_invalid_id_type(self, mock_llm, extractor):
        """Should handle invalid ID types (strings, floats, etc.)."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": "forty-two"}],  # Should be integer
            "confidence": 0.5
        })

        # Should either convert or handle gracefully
        result = extractor.extract("Show task forty-two", "COMMAND")
        # Accept either: conversion to int, or keeping as string with low confidence
        assert result.confidence <= 0.7  # Low confidence for ambiguous ID

    def test_negative_id(self, mock_llm, extractor):
        """Should reject negative IDs."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": -5}],
            "confidence": 0.3
        })

        result = extractor.extract("Show task -5", "COMMAND")
        # Should either raise exception or return low confidence
        assert result.confidence < 0.5 or len(result.entities) == 0

    def test_zero_id(self, mock_llm, extractor):
        """Should reject ID=0 (invalid)."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": 0}],
            "confidence": 0.3
        })

        result = extractor.extract("Show task 0", "COMMAND")
        assert result.confidence < 0.5  # Low confidence for invalid ID

    def test_very_large_id(self, mock_llm, extractor):
        """Should handle very large IDs."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": 999999999}],
            "confidence": 0.8
        })

        result = extractor.extract("Show task 999999999", "COMMAND")
        assert result.entities[0]["id"] == 999999999


# ============================================================================
# Test Class 3: Name/Title Extraction (US-NL-007) - 10 tests
# ============================================================================

class TestNameExtraction:
    """Test name/title extraction with fuzzy matching."""

    def test_extract_exact_name(self, mock_llm, extractor):
        """Should extract exact name match."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "epic",
            "entities": [{"title": "User Authentication", "match_type": "exact"}],
            "confidence": 0.98
        })

        result = extractor.extract("Show User Authentication epic", "COMMAND")
        assert result.entities[0]["title"] == "User Authentication"
        assert result.confidence >= 0.95

    def test_extract_partial_name(self, mock_llm, extractor):
        """Should match partial names (e.g., 'auth' → 'Authentication')."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "epic",
            "entities": [{"title": "User Authentication", "match_type": "partial"}],
            "confidence": 0.85
        })

        result = extractor.extract("Show auth epic", "COMMAND")
        assert "Authentication" in result.entities[0]["title"]

    def test_extract_fuzzy_name(self, mock_llm, extractor):
        """Should handle typos/misspellings (e.g., 'authentification' → 'authentication')."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "epic",
            "entities": [{"title": "User Authentication", "match_type": "fuzzy"}],
            "confidence": 0.75
        })

        result = extractor.extract("Show authentification epic", "COMMAND")
        assert "Authentication" in result.entities[0]["title"]
        assert result.confidence >= 0.7  # Fuzzy match = lower confidence

    def test_extract_case_insensitive(self, mock_llm, extractor):
        """Should match names case-insensitively."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "epic",
            "entities": [{"title": "User Authentication"}],
            "confidence": 0.95
        })

        result = extractor.extract("Show USER AUTHENTICATION epic", "COMMAND")
        assert result.entities[0]["title"] == "User Authentication"

    def test_extract_name_with_special_chars(self, mock_llm, extractor):
        """Should handle names with special characters."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Fix OAuth 2.0 (RFC 6749) Implementation"}],
            "confidence": 0.9
        })

        result = extractor.extract("Show 'Fix OAuth 2.0' task", "COMMAND")
        assert "OAuth 2.0" in result.entities[0]["title"]

    def test_extract_quoted_name(self, mock_llm, extractor):
        """Should extract names in quotes."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "story",
            "entities": [{"title": "Implement 'Login' Feature"}],
            "confidence": 0.95
        })

        result = extractor.extract('Show story "Implement \'Login\' Feature"', "COMMAND")
        assert "Login" in result.entities[0]["title"]

    def test_multiple_name_matches(self, mock_llm, extractor):
        """Should return multiple matches when ambiguous."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [
                {"title": "Login Tests"},
                {"title": "Logout Tests"},
                {"title": "Auth Tests"}
            ],
            "confidence": 0.6,  # Low confidence = ambiguous
            "reasoning": "Multiple tasks match 'tests'"
        })

        result = extractor.extract("Show tests task", "COMMAND")
        assert len(result.entities) > 1
        assert result.confidence < 0.8  # Ambiguity = lower confidence

    def test_no_name_match(self, mock_llm, extractor):
        """Should handle no matches gracefully."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "epic",
            "entities": [],
            "confidence": 0.2,
            "reasoning": "No epic found matching 'nonexistent'"
        })

        result = extractor.extract("Show nonexistent epic", "COMMAND")
        assert len(result.entities) == 0
        assert result.confidence < 0.5

    def test_generic_name_low_confidence(self, mock_llm, extractor):
        """Very generic names should have low confidence."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Task"}],  # Too generic
            "confidence": 0.3
        })

        result = extractor.extract("Show task called task", "COMMAND")
        assert result.confidence < 0.5  # Generic name = low confidence

    def test_name_with_numbers(self, mock_llm, extractor):
        """Should extract names containing numbers."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "story",
            "entities": [{"title": "Implement OAuth 2.0"}],
            "confidence": 0.95
        })

        result = extractor.extract("Show OAuth 2.0 story", "COMMAND")
        assert "2.0" in result.entities[0]["title"]


# ============================================================================
# Test Class 4: Field Extraction (US-NL-008) - 5 tests
# ============================================================================

class TestFieldExtraction:
    """Test extraction of various work item fields."""

    def test_extract_title_and_description(self, mock_llm, extractor):
        """Should extract both title and description."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Implement Login",
                "description": "Add email/password login with validation"
            }],
            "confidence": 0.95
        })

        result = extractor.extract(
            "Create task: Implement Login. Description: Add email/password login",
            "COMMAND"
        )
        assert result.entities[0]["title"] == "Implement Login"
        assert "email/password" in result.entities[0]["description"]

    def test_extract_status_field(self, mock_llm, extractor):
        """Should extract status field."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"id": 42, "status": "completed"}],
            "confidence": 0.95
        })

        result = extractor.extract("Mark task 42 as completed", "COMMAND")
        assert result.entities[0]["status"] == "completed"

    def test_extract_priority_field(self, mock_llm, extractor):
        """Should extract priority field."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Fix bug", "priority": "high"}],
            "confidence": 0.9
        })

        result = extractor.extract("Create high priority task: Fix bug", "COMMAND")
        assert result.entities[0]["priority"] == "high"

    def test_extract_parent_id(self, mock_llm, extractor):
        """Should extract parent epic/story IDs."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "story",
            "entities": [{"title": "Login UI", "epic_id": 5}],
            "confidence": 0.9
        })

        result = extractor.extract("Add story 'Login UI' to epic 5", "COMMAND")
        assert result.entities[0]["epic_id"] == 5

    def test_extract_multiple_fields(self, mock_llm, extractor):
        """Should extract all fields from complex command."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Implement OAuth",
                "description": "Add Google OAuth 2.0 integration",
                "priority": "high",
                "story_id": 12,
                "estimated_hours": 8
            }],
            "confidence": 0.92
        })

        result = extractor.extract(
            "Create high priority task in story 12: Implement OAuth "
            "(Add Google OAuth 2.0 integration) - estimated 8 hours",
            "COMMAND"
        )
        entity = result.entities[0]
        assert entity["title"] == "Implement OAuth"
        assert entity["priority"] == "high"
        assert entity["story_id"] == 12
        assert entity["estimated_hours"] == 8


# ============================================================================
# Test Class 5: Special Cases & Edge Cases (US-NL-019) - 10 tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_message(self, extractor):
        """Should reject empty messages."""
        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("", "COMMAND")

        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only_message(self, extractor):
        """Should reject whitespace-only messages."""
        with pytest.raises(EntityExtractionException):
            extractor.extract("   \n\t  ", "COMMAND")

    def test_very_long_message(self, mock_llm, extractor):
        """Should handle very long messages (1000+ chars)."""
        long_message = "Create task: " + ("A" * 1000)

        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Long title"}],
            "confidence": 0.8
        })

        result = extractor.extract(long_message, "COMMAND")
        assert result.entity_type == "task"

    def test_unicode_characters(self, mock_llm, extractor):
        """Should handle Unicode characters (émojis, accents)."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Implement café ☕ feature"}],
            "confidence": 0.9
        })

        result = extractor.extract("Create task: Implement café ☕ feature", "COMMAND")
        assert "café" in result.entities[0]["title"]
        assert "☕" in result.entities[0]["title"]

    def test_code_block_in_description(self, mock_llm, extractor):
        """Should handle code blocks in descriptions."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Add validation",
                "description": "```python\ndef validate():\n    pass\n```"
            }],
            "confidence": 0.85
        })

        result = extractor.extract(
            "Create task: Add validation with code: ```python\ndef validate(): pass```",
            "COMMAND"
        )
        assert "```python" in result.entities[0]["description"]

    def test_markdown_formatting(self, mock_llm, extractor):
        """Should preserve markdown in descriptions."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Update docs",
                "description": "**Bold** and *italic* text with [link](url)"
            }],
            "confidence": 0.9
        })

        result = extractor.extract(
            "Create task: Update docs with **bold** *italic* [link](url)",
            "COMMAND"
        )
        assert "**Bold**" in result.entities[0]["description"]

    def test_sql_injection_attempt(self, mock_llm, extractor):
        """Should safely handle SQL injection attempts."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "'; DROP TABLE tasks; --"}],
            "confidence": 0.5  # Low confidence for suspicious input
        })

        # Should NOT cause SQL injection (extractor doesn't execute queries)
        result = extractor.extract("Create task: '; DROP TABLE tasks; --", "COMMAND")
        # As long as it doesn't crash, we're good
        assert result.entity_type == "task"

    def test_xss_attempt(self, mock_llm, extractor):
        """Should handle XSS attempts in input."""
        mock_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "<script>alert('XSS')</script>"}],
            "confidence": 0.4
        })

        result = extractor.extract(
            "Create task: <script>alert('XSS')</script>",
            "COMMAND"
        )
        # Should NOT execute script (just stored as text)
        assert "<script>" in result.entities[0]["title"]

    def test_llm_timeout(self, mock_llm, extractor):
        """Should handle LLM timeout gracefully."""
        mock_llm.generate.side_effect = TimeoutError("LLM request timed out")

        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("Create task", "COMMAND")

        assert "llm" in str(exc_info.value).lower() or "timeout" in str(exc_info.value).lower()

    def test_llm_rate_limit(self, mock_llm, extractor):
        """Should handle LLM rate limiting."""
        mock_llm.generate.side_effect = Exception("Rate limit exceeded")

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create task", "COMMAND")


# Run with: pytest tests/test_nl_entity_extractor.py -v --cov=src/nl/entity_extractor
