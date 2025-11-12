"""Critical bug prevention test for NL entity extraction.

This test specifically targets the entity_type=None bug discovered on 2025-11-11.

Bug Log:
---------
[You → Orchestrator]: What is the current project?
[Orchestrator processing...]
2025-11-11 15:42:07,146 - nl.intent_classifier - INFO - Classified as COMMAND with confidence 0.93
2025-11-11 15:42:08,513 - src.nl.nl_command_processor - ERROR - Command handling failed:
Failed to parse LLM response: Invalid entity_type: None.
Must be one of ['epic', 'story', 'task', 'subtask', 'milestone']

Traceback (most recent call last):
  File "/home/omarwsl/projects/claude_code_orchestrator/src/nl/entity_extractor.py", line 305
    raise ValueError(
ValueError: Invalid entity_type: None. Must be one of ['epic', 'story', 'task', 'subtask', 'milestone']

Expected Behavior:
------------------
Should return EntityExtractionException with user-friendly message,
NOT raise ValueError with Python traceback to user.

Test Coverage:
--------------
- US-NL-001: Query current project information
- US-NL-016: Graceful handling of invalid entity types
"""

import pytest
import json
from unittest.mock import MagicMock
from src.nl.entity_extractor import EntityExtractor, EntityExtractionException
from src.core.state import StateManager
from src.core.config import Config


@pytest.fixture
def test_state_nl(tmp_path):
    """In-memory StateManager for NL tests."""
    # Use in-memory SQLite for faster tests (no file I/O)
    state = StateManager(database_url='sqlite:///:memory:')

    # Create test project with correct signature
    project = state.create_project(
        name="Test Project",
        description="Test project for NL command testing",
        working_dir="/tmp/test"
    )
    # Note: Project ID 1 will be the "current" project for these tests

    yield state

    # Cleanup (optional for in-memory DB, but good practice)
    state.close()


@pytest.fixture
def nl_test_config():
    """Config for NL tests."""
    config = Config.load()
    config.set('testing.mode', True)
    config.set('llm.timeout', 5.0)
    return config


class TestEntityTypeNoneBugPrevention:
    """Critical: Prevent regression of the entity_type=None bug (2025-11-11)."""

    def test_entity_type_none_raises_user_friendly_exception(
        self,
        test_state_nl,
        nl_test_config,
        mock_llm_responses
    ):
        """CRITICAL BUG TEST: entity_type=None should return helpful error.

        This is the exact bug from the log. LLM returned entity_type=None
        when user asked "What is the current project?", causing ValueError.

        Expected: EntityExtractionException with suggestion to user
        Actual (before fix): ValueError with Python traceback
        """
        # Setup: Mock LLM returns entity_type=None (the bug condition)
        mock_llm = MagicMock()
        mock_llm.generate.return_value = mock_llm_responses["invalid_null_entity_type"]

        extractor = EntityExtractor(
            llm_plugin=mock_llm
        )

        # Execute and verify exception type
        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("What is the current project?", "COMMAND")

        # Verify error message is user-friendly (not a Python traceback)
        error_msg = str(exc_info.value).lower()

        # Should contain helpful guidance
        assert any(phrase in error_msg for phrase in [
            "couldn't determine",
            "invalid entity",
            "failed to parse",
            "none"
        ]), f"Error message not user-friendly: {error_msg}"

        # Should NOT leak Python exception details to user
        assert "valueerror" not in error_msg, \
            "Should not expose ValueError to user"
        assert "traceback" not in error_msg, \
            "Should not show Python traceback to user"

    def test_entity_type_missing_field_entirely(
        self,
        test_state_nl,
        nl_test_config,
        mock_llm_responses
    ):
        """Should handle when entity_type field is missing from LLM response."""
        # Setup: LLM response missing entity_type field
        mock_llm = MagicMock()
        mock_llm.generate.return_value = mock_llm_responses["invalid_missing_entity_type"]

        extractor = EntityExtractor(
            llm_plugin=mock_llm
        )

        # Should raise EntityExtractionException (not KeyError)
        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("Show project", "COMMAND")

        error_msg = str(exc_info.value).lower()
        assert "missing" in error_msg or "required" in error_msg or "failed to parse" in error_msg

    def test_entity_type_invalid_value(
        self,
        test_state_nl,
        nl_test_config
    ):
        """Should reject entity_type values not in schema."""
        # Setup: LLM returns invalid entity_type
        invalid_types = [
            "feature",      # Common mistake
            "bug",          # Common mistake
            "requirement",  # Common mistake
            "user_story",   # Incorrect (should be "story")
            "TASK",         # Wrong case
            "",             # Empty string
            123,            # Wrong type (integer)
        ]

        for invalid_type in invalid_types:
            mock_llm = MagicMock()
            mock_llm.generate.return_value = json.dumps({
                "entity_type": invalid_type,
                "entities": [],
                "confidence": 0.8,
                "reasoning": "Test case"
            })

            extractor = EntityExtractor(
                llm_plugin=mock_llm
            )

            with pytest.raises(EntityExtractionException) as exc_info:
                extractor.extract(f"Create {invalid_type}", "COMMAND")

            error_msg = str(exc_info.value).lower()
            assert "invalid" in error_msg or "not recognized" in error_msg or "failed to parse" in error_msg, \
                f"Should reject invalid type: {invalid_type}"

    def test_valid_entity_types_all_accepted(
        self,
        test_state_nl,
        nl_test_config,
        mock_llm_smart
    ):
        """Verify all valid entity types are accepted."""
        valid_types = ["project", "epic", "story", "task", "subtask", "milestone"]

        extractor = EntityExtractor(
            llm_plugin=mock_llm_smart
        )

        for entity_type in valid_types:
            # Should NOT raise exception
            try:
                result = extractor.extract(f"Show {entity_type}", "COMMAND")
                assert result.entity_type == entity_type
            except EntityExtractionException as e:
                pytest.fail(f"Valid entity type '{entity_type}' was rejected: {e}")


class TestProjectLevelQuerySupport:
    """Verify project-level queries work (US-NL-001)."""

    def test_query_current_project_extracts_correctly(
        self,
        test_state_nl,
        nl_test_config,
        mock_llm_smart
    ):
        """Should correctly extract project entity from query."""
        extractor = EntityExtractor(
            llm_plugin=mock_llm_smart
        )

        # Execute
        result = extractor.extract("What is the current project?", "COMMAND")

        # Verify
        assert result.entity_type == "project"
        assert result.confidence >= 0.7  # Lowered threshold for smart mock

    def test_project_query_variations(
        self,
        test_state_nl,
        nl_test_config,
        mock_llm_smart
    ):
        """Should handle various phrasings of project queries."""
        queries = [
            "What is the current project?",
            "Show me the active project",
            "Which project am I working on?",
            "Project info",
            "Current project status"
        ]

        extractor = EntityExtractor(
            llm_plugin=mock_llm_smart
        )

        for query in queries:
            # Should all succeed
            result = extractor.extract(query, "COMMAND")
            assert result.entity_type == "project", \
                f"Failed to recognize project query: {query}"


# Run with: pytest tests/test_nl_entity_extractor_bug_prevention.py -v
# Expected: FAIL on first run (bug exists)
# After fixing src/nl/entity_extractor.py: PASS
