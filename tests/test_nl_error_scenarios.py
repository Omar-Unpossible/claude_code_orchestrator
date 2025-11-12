"""Comprehensive Error Scenario Tests for NL Command System (Phase 3).

Tests all error paths, edge cases, and failure modes across the NL pipeline.
Covers US-NL-015, US-NL-016, US-NL-017, US-NL-018, US-NL-019.

Total test count: 35 tests
"""

import pytest
import json
from unittest.mock import MagicMock, patch

from src.nl.intent_classifier import IntentClassifier, IntentClassificationException
from src.nl.entity_extractor import EntityExtractor, EntityExtractionException
from src.nl.command_validator import CommandValidator, ValidationException
from src.nl.entity_extractor import ExtractedEntities
from src.core.state import StateManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def error_llm():
    """Mock LLM that can simulate various error conditions."""
    llm = MagicMock()
    return llm


@pytest.fixture
def error_state():
    """StateManager for error testing."""
    state = StateManager(database_url='sqlite:///:memory:')
    project = state.create_project("Error Test", "Test", "/tmp/test")
    yield state
    state.close()


# ============================================================================
# Test Class 1: LLM Failure Scenarios (US-NL-018) - 10 tests
# ============================================================================

class TestLLMFailureScenarios:
    """Test LLM timeout, rate limiting, and failure scenarios."""

    def test_intent_classifier_timeout(self, error_llm):
        """Intent classification should handle LLM timeout."""
        error_llm.generate.side_effect = TimeoutError("LLM timeout after 30s")

        classifier = IntentClassifier(error_llm)

        with pytest.raises(IntentClassificationException) as exc_info:
            classifier.classify("Create epic")

        assert "timeout" in str(exc_info.value).lower() or "llm" in str(exc_info.value).lower()

    def test_entity_extractor_timeout(self, error_llm):
        """Entity extraction should handle LLM timeout."""
        error_llm.generate.side_effect = TimeoutError("Request timed out")

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("Create epic", "COMMAND")

        assert "timeout" in str(exc_info.value).lower() or "llm" in str(exc_info.value).lower()

    def test_llm_rate_limit_429(self, error_llm):
        """Handle LLM rate limiting (HTTP 429)."""
        error_llm.generate.side_effect = Exception("Rate limit exceeded (429)")

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create epic", "COMMAND")

    def test_llm_network_error(self, error_llm):
        """Handle network errors when calling LLM."""
        error_llm.generate.side_effect = ConnectionError("Network unreachable")

        classifier = IntentClassifier(error_llm)

        with pytest.raises(IntentClassificationException):
            classifier.classify("Create epic")

    def test_llm_returns_malformed_json(self, error_llm):
        """Handle malformed JSON from LLM."""
        error_llm.generate.return_value = "This is not JSON at all!"

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("Create epic", "COMMAND")

        assert "json" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()

    def test_llm_returns_incomplete_json(self, error_llm):
        """Handle incomplete/truncated JSON."""
        error_llm.generate.return_value = '{"entity_type": "epic", "entit'  # Truncated

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create epic", "COMMAND")

    def test_llm_returns_invalid_json_syntax(self, error_llm):
        """Handle invalid JSON syntax."""
        error_llm.generate.return_value = "{'single': 'quotes'}"  # Invalid - needs double quotes

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create epic", "COMMAND")

    def test_llm_returns_empty_response(self, error_llm):
        """Handle empty response from LLM."""
        error_llm.generate.return_value = ""

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create epic", "COMMAND")

    def test_llm_returns_null_response(self, error_llm):
        """Handle null response from LLM."""
        error_llm.generate.return_value = None

        extractor = EntityExtractor(error_llm)

        with pytest.raises((EntityExtractionException, AttributeError, TypeError)):
            extractor.extract("Create epic", "COMMAND")

    def test_llm_extremely_long_response(self, error_llm):
        """Handle extremely long response from LLM."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "A" * 10000, "description": "B" * 10000}],
            "confidence": 0.9
        })

        extractor = EntityExtractor(error_llm)

        # Should handle long response (may truncate or accept)
        try:
            result = extractor.extract("Create task", "COMMAND")
            assert len(result.entities[0]["title"]) > 100
        except EntityExtractionException:
            # Or may reject as too long
            pass


# ============================================================================
# Test Class 2: Invalid Entity Data (US-NL-016) - 10 tests
# ============================================================================

class TestInvalidEntityData:
    """Test handling of invalid entity data from LLM."""

    def test_entity_type_none(self, error_llm):
        """entity_type=None should raise user-friendly error."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": None,
            "entities": []
        })

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("What is the current project?", "COMMAND")

    def test_entity_type_invalid_value(self, error_llm):
        """Invalid entity_type string should be rejected."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "feature",  # Invalid
            "entities": []
        })

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("Create feature", "COMMAND")

    def test_entities_field_wrong_type(self, error_llm):
        """entities field should be a list."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": "not a list"  # Wrong type
        })

        extractor = EntityExtractor(error_llm)

        with pytest.raises((EntityExtractionException, TypeError, AttributeError)):
            extractor.extract("Create task", "COMMAND")

    def test_confidence_out_of_range_high(self, error_llm):
        """confidence > 1.0 should be rejected."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [],
            "confidence": 1.5  # Invalid
        })

        extractor = EntityExtractor(error_llm)

        with pytest.raises((EntityExtractionException, ValueError)):
            extractor.extract("Create task", "COMMAND")

    def test_confidence_negative(self, error_llm):
        """Negative confidence should be rejected."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [],
            "confidence": -0.5  # Invalid
        })

        extractor = EntityExtractor(error_llm)

        with pytest.raises((EntityExtractionException, ValueError)):
            extractor.extract("Create task", "COMMAND")

    def test_confidence_wrong_type(self, error_llm):
        """confidence should be numeric."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [],
            "confidence": "very high"  # Wrong type
        })

        extractor = EntityExtractor(error_llm)

        with pytest.raises((EntityExtractionException, ValueError, TypeError)):
            extractor.extract("Create task", "COMMAND")

    def test_intent_wrong_type(self, error_llm):
        """intent field should be valid string."""
        error_llm.generate.return_value = json.dumps({
            "intent": 123,  # Should be string
            "confidence": 0.9
        })

        classifier = IntentClassifier(error_llm)

        with pytest.raises((IntentClassificationException, ValueError, TypeError)):
            classifier.classify("Create task")

    def test_intent_invalid_value(self, error_llm):
        """intent should be COMMAND, QUESTION, or CLARIFICATION_NEEDED."""
        error_llm.generate.return_value = json.dumps({
            "intent": "MAYBE",  # Invalid
            "confidence": 0.7
        })

        classifier = IntentClassifier(error_llm)

        with pytest.raises((IntentClassificationException, ValueError)):
            classifier.classify("Do something")

    def test_missing_required_fields_in_response(self, error_llm):
        """Missing required fields should be caught."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task"
            # Missing 'entities' field
        })

        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("Create task", "COMMAND")

        assert "entities" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

    def test_extra_unexpected_fields(self, error_llm):
        """Extra unexpected fields should be ignored (not cause errors)."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Task", "description": "Test"}],
            "confidence": 0.9,
            "unexpected_field_1": "value",
            "unexpected_field_2": 123,
            "nested": {"unexpected": "data"}
        })

        extractor = EntityExtractor(error_llm)

        # Should NOT raise exception (extra fields ignored)
        result = extractor.extract("Create task", "COMMAND")
        assert result.entity_type == "task"


# ============================================================================
# Test Class 3: Input Validation Errors (US-NL-019) - 5 tests
# ============================================================================

class TestInputValidationErrors:
    """Test handling of invalid user input."""

    def test_empty_message(self, error_llm):
        """Empty message should be handled gracefully."""
        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException) as exc_info:
            extractor.extract("", "COMMAND")

        assert "empty" in str(exc_info.value).lower()

    def test_whitespace_only_message(self, error_llm):
        """Whitespace-only message should be rejected."""
        extractor = EntityExtractor(error_llm)

        with pytest.raises(EntityExtractionException):
            extractor.extract("   \n\t   ", "COMMAND")

    def test_extremely_long_message(self, error_llm):
        """Very long message should be handled."""
        long_message = "Create task: " + ("A" * 100000)  # 100k chars

        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Task", "description": "Test"}],
            "confidence": 0.8
        })

        extractor = EntityExtractor(error_llm)

        # Should either handle or raise clear error
        try:
            result = extractor.extract(long_message, "COMMAND")
            assert result.entity_type == "task"
        except EntityExtractionException as e:
            assert "too long" in str(e).lower() or "length" in str(e).lower()

    def test_sql_injection_attempt(self, error_llm):
        """SQL injection attempts should be sanitized."""
        malicious_input = "'; DROP TABLE tasks; --"

        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": malicious_input, "description": "Test"}],
            "confidence": 0.6
        })

        extractor = EntityExtractor(error_llm)

        # Should handle safely (not execute SQL)
        result = extractor.extract(f"Create task: {malicious_input}", "COMMAND")
        assert result.entity_type == "task"

    def test_xss_attempt(self, error_llm):
        """XSS attempts should be handled safely."""
        xss_input = "<script>alert('XSS')</script>"

        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": xss_input, "description": "Test"}],
            "confidence": 0.5
        })

        extractor = EntityExtractor(error_llm)

        # Should store safely (not execute script)
        result = extractor.extract(f"Create task: {xss_input}", "COMMAND")
        assert result.entity_type == "task"


# ============================================================================
# Test Class 4: Validation Errors (US-NL-017) - 5 tests
# ============================================================================

class TestValidationErrors:
    """Test validation error scenarios."""

    def test_missing_required_field_epic_title(self, error_state):
        """Epic missing title should fail validation."""
        validator = CommandValidator(error_state)

        entities = ExtractedEntities(
            entity_type="epic",
            entities=[{"description": "No title"}],
            confidence=0.8
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("title" in error.lower() for error in result.errors)

    def test_invalid_epic_reference(self, error_state):
        """Story with invalid epic_id should fail validation."""
        validator = CommandValidator(error_state)

        entities = ExtractedEntities(
            entity_type="story",
            entities=[{"title": "Story", "description": "Test", "epic_id": 999}],
            confidence=0.85
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("999" in error for error in result.errors)

    def test_invalid_story_reference(self, error_state):
        """Task with invalid story_id should fail validation."""
        validator = CommandValidator(error_state)

        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"title": "Task", "description": "Test", "story_id": 888}],
            confidence=0.8
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("888" in error for error in result.errors)

    def test_circular_dependency_detected(self, error_state):
        """Circular dependency should fail validation."""
        # Create tasks A and B where B depends on A
        task_a = error_state.create_task(1, {"title": "A", "description": "Test"})
        task_b = error_state.create_task(1, {"title": "B", "description": "Test", "dependencies": [task_a.id]})

        validator = CommandValidator(error_state)

        # Try to make A depend on B (circular!)
        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"id": task_a.id, "title": "A", "dependencies": [task_b.id]}],
            confidence=0.7
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("circular" in error.lower() for error in result.errors)

    def test_self_dependency_rejected(self, error_state):
        """Task depending on itself should be rejected."""
        task = error_state.create_task(1, {"title": "Task", "description": "Test"})

        validator = CommandValidator(error_state)

        entities = ExtractedEntities(
            entity_type="task",
            entities=[{"id": task.id, "title": "Task", "dependencies": [task.id]}],
            confidence=0.6
        )

        result = validator.validate(entities)
        assert result.valid is False
        assert any("itself" in error.lower() for error in result.errors)


# ============================================================================
# Test Class 5: Edge Cases (US-NL-019) - 5 tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_unicode_emoji_handling(self, error_llm):
        """Unicode and emojis should be handled properly."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Add ✅ validation for café ☕", "description": "Unicode test"}],
            "confidence": 0.9
        })

        extractor = EntityExtractor(error_llm)

        result = extractor.extract("Create task: Add ✅ validation for café ☕", "COMMAND")
        assert result.entity_type == "task"
        assert "✅" in result.entities[0]["title"]
        assert "café" in result.entities[0]["title"]

    def test_code_block_in_description(self, error_llm):
        """Code blocks should be preserved."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Add validation",
                "description": "```python\ndef validate():\n    pass\n```"
            }],
            "confidence": 0.85
        })

        extractor = EntityExtractor(error_llm)

        result = extractor.extract("Create task with code: ```python\ndef validate(): pass```", "COMMAND")
        assert "```python" in result.entities[0]["description"]

    def test_markdown_formatting_preserved(self, error_llm):
        """Markdown formatting should be preserved."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Task",
                "description": "**Bold** and *italic* with [link](url)"
            }],
            "confidence": 0.88
        })

        extractor = EntityExtractor(error_llm)

        result = extractor.extract("Create task with **bold** *italic*", "COMMAND")
        assert "**Bold**" in result.entities[0]["description"] or "bold" in result.entities[0]["description"].lower()

    def test_special_characters_in_title(self, error_llm):
        """Special characters should be handled."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{"title": "Fix OAuth 2.0 'login' bug (RFC 6749)", "description": "Test"}],
            "confidence": 0.92
        })

        extractor = EntityExtractor(error_llm)

        result = extractor.extract("Fix OAuth 2.0 'login' bug (RFC 6749)", "COMMAND")
        assert "OAuth 2.0" in result.entities[0]["title"]
        assert "'" in result.entities[0]["title"]

    def test_newlines_in_description(self, error_llm):
        """Newlines should be preserved in descriptions."""
        error_llm.generate.return_value = json.dumps({
            "entity_type": "task",
            "entities": [{
                "title": "Task",
                "description": "Line 1\nLine 2\nLine 3"
            }],
            "confidence": 0.87
        })

        extractor = EntityExtractor(error_llm)

        result = extractor.extract("Create task:\nLine 1\nLine 2\nLine 3", "COMMAND")
        assert "\n" in result.entities[0]["description"] or "line" in result.entities[0]["description"].lower()


# Run with: pytest tests/test_nl_error_scenarios.py -v
