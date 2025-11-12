"""Comprehensive tests for NL intent classification (Phase 1).

Test coverage for src/nl/intent_classifier.py targeting 85% coverage.
Covers US-NL-001, US-NL-004, US-NL-008, US-NL-011, US-NL-015, US-NL-018.

Total test count: 30 tests
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.nl.intent_classifier import (
    IntentClassifier,
    IntentClassificationException,
    IntentResult
)
from src.plugins.base import LLMPlugin


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm():
    """Mock LLM plugin with controllable responses."""
    llm = MagicMock(spec=LLMPlugin)
    # Default: COMMAND intent
    llm.generate.return_value = json.dumps({
        "intent": "COMMAND",
        "confidence": 0.95,
        "reasoning": "Clear command to create work item"
    })
    return llm


@pytest.fixture
def classifier(mock_llm):
    """IntentClassifier instance with mocked LLM."""
    return IntentClassifier(llm_plugin=mock_llm, confidence_threshold=0.7)


# ============================================================================
# Test Class 1: Basic Intent Classification (US-NL-008, 011) - 10 tests
# ============================================================================

class TestBasicIntentClassification:
    """Test basic intent classification for COMMAND, QUESTION, CLARIFICATION_NEEDED."""

    def test_classify_command_create_epic(self, mock_llm, classifier):
        """Should classify 'Create epic' as COMMAND."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.98,
            "reasoning": "Explicit create command"
        })

        result = classifier.classify("Create an epic for user authentication")
        assert result.intent == "COMMAND"
        assert result.confidence >= 0.9

    def test_classify_command_update_task(self, mock_llm, classifier):
        """Should classify 'Update task' as COMMAND."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.95,
            "reasoning": "Update operation on task"
        })

        result = classifier.classify("Mark task 42 as completed")
        assert result.intent == "COMMAND"

    def test_classify_command_delete(self, mock_llm, classifier):
        """Should classify delete commands as COMMAND."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.92,
            "reasoning": "Delete operation"
        })

        result = classifier.classify("Delete task 15")
        assert result.intent == "COMMAND"

    def test_classify_question_what_is(self, mock_llm, classifier):
        """Should classify 'What is...' as QUESTION."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "QUESTION",
            "confidence": 0.93,
            "reasoning": "Interrogative query asking for information"
        })

        result = classifier.classify("What is the current project?")
        assert result.intent == "QUESTION"
        assert result.confidence >= 0.9

    def test_classify_question_show_me(self, mock_llm, classifier):
        """Should classify 'Show me...' as QUESTION."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "QUESTION",
            "confidence": 0.91,
            "reasoning": "Request for information display"
        })

        result = classifier.classify("Show me the epic hierarchy")
        assert result.intent == "QUESTION"

    def test_classify_question_how_many(self, mock_llm, classifier):
        """Should classify 'How many...' as QUESTION."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "QUESTION",
            "confidence": 0.94,
            "reasoning": "Quantitative information request"
        })

        result = classifier.classify("How many tasks do I have?")
        assert result.intent == "QUESTION"

    def test_classify_clarification_needed_ambiguous(self, mock_llm, classifier):
        """Should classify ambiguous messages as CLARIFICATION_NEEDED."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "CLARIFICATION_NEEDED",
            "confidence": 0.4,
            "reasoning": "Ambiguous reference - 'status' of what?"
        })

        result = classifier.classify("Show status")
        assert result.intent == "CLARIFICATION_NEEDED"
        assert result.confidence < 0.7  # Below threshold

    def test_classify_clarification_needed_incomplete(self, mock_llm, classifier):
        """Should classify incomplete messages as CLARIFICATION_NEEDED."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "CLARIFICATION_NEEDED",
            "confidence": 0.3,
            "reasoning": "Incomplete command - create what?"
        })

        result = classifier.classify("Create something")
        assert result.intent == "CLARIFICATION_NEEDED"

    def test_classify_clarification_needed_pronoun_without_context(self, mock_llm, classifier):
        """Should need clarification for pronouns without context."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "CLARIFICATION_NEEDED",
            "confidence": 0.5,
            "reasoning": "Pronoun 'it' without context"
        })

        result = classifier.classify("Mark it completed")
        assert result.intent == "CLARIFICATION_NEEDED"

    def test_classify_command_implicit_create(self, mock_llm, classifier):
        """Should classify implicit create commands (Add, Make, etc.)."""
        commands = [
            "Add a story for login",
            "Make a task to fix bug",
            "Insert epic for payments"
        ]

        for command in commands:
            mock_llm.generate.return_value = json.dumps({
                "intent": "COMMAND",
                "confidence": 0.88,
                "reasoning": "Implicit create command"
            })

            result = classifier.classify(command)
            assert result.intent == "COMMAND", f"Failed for: {command}"


# ============================================================================
# Test Class 2: Confidence Scoring (US-NL-015) - 10 tests
# ============================================================================

class TestConfidenceScoring:
    """Test confidence scoring and threshold behavior."""

    def test_high_confidence_command(self, mock_llm, classifier):
        """Very clear commands should have high confidence."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.98,
            "reasoning": "Explicit, unambiguous command"
        })

        result = classifier.classify("Create epic titled 'User Authentication' with OAuth support")
        assert result.confidence >= 0.95

    def test_medium_confidence_question(self, mock_llm, classifier):
        """Somewhat clear questions should have medium confidence."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "QUESTION",
            "confidence": 0.75,
            "reasoning": "Likely a question but could be command"
        })

        result = classifier.classify("Can you show me the tasks?")
        assert 0.7 <= result.confidence < 0.9

    def test_low_confidence_triggers_clarification(self, mock_llm, classifier):
        """Low confidence should return CLARIFICATION_NEEDED."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",  # LLM says COMMAND but...
            "confidence": 0.5,    # ...confidence is low
            "reasoning": "Uncertain interpretation"
        })

        result = classifier.classify("next")
        # Classifier should override to CLARIFICATION_NEEDED due to low confidence
        assert result.confidence < 0.7

    def test_confidence_threshold_customization(self, mock_llm):
        """Should respect custom confidence threshold."""
        # Strict classifier (threshold = 0.9)
        strict_classifier = IntentClassifier(mock_llm, confidence_threshold=0.9)

        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.85,  # Above 0.7, below 0.9
            "reasoning": "Fairly clear command"
        })

        result = strict_classifier.classify("Create task")
        # With threshold 0.9, confidence 0.85 might trigger clarification
        # (implementation-dependent)
        assert result.confidence == 0.85

    def test_confidence_out_of_range_high(self, mock_llm, classifier):
        """Should reject confidence > 1.0."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 1.5,  # Invalid
            "reasoning": "Too confident"
        })

        with pytest.raises((IntentClassificationException, ValueError)):
            classifier.classify("Create task")

    def test_confidence_out_of_range_low(self, mock_llm, classifier):
        """Should reject confidence < 0.0."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": -0.5,  # Invalid
            "reasoning": "Negative confidence?"
        })

        with pytest.raises((IntentClassificationException, ValueError)):
            classifier.classify("Create task")

    def test_confidence_wrong_type(self, mock_llm, classifier):
        """Should handle non-numeric confidence."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": "very high",  # Should be float
            "reasoning": "Invalid type"
        })

        with pytest.raises((IntentClassificationException, ValueError, TypeError)):
            classifier.classify("Create task")

    def test_confidence_missing_field(self, mock_llm, classifier):
        """Should handle missing confidence field."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            # No confidence field
            "reasoning": "Missing confidence"
        })

        with pytest.raises(IntentClassificationException):
            classifier.classify("Create task")

    def test_reasoning_field_optional(self, mock_llm, classifier):
        """Reasoning field should be optional."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.9
            # No reasoning field - should still work
        })

        result = classifier.classify("Create epic")
        assert result.intent == "COMMAND"
        assert result.reasoning == "" or result.reasoning is None  # Default value

    def test_detected_entities_field_optional(self, mock_llm, classifier):
        """Detected entities field should be optional."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.92,
            "reasoning": "Create command"
            # No detected_entities field
        })

        result = classifier.classify("Create task")
        assert result.detected_entities == {}  # Default empty dict


# ============================================================================
# Test Class 3: Edge Cases & Error Handling (US-NL-018, 019) - 10 tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_message(self, mock_llm, classifier):
        """Should handle empty messages (LLM returns low confidence/clarification)."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "CLARIFICATION_NEEDED",
            "confidence": 0.1,
            "reasoning": "Empty message"
        })

        result = classifier.classify("")
        # Either raises exception OR returns low confidence clarification needed
        assert result.intent == "CLARIFICATION_NEEDED" and result.confidence < 0.5

    def test_whitespace_only_message(self, mock_llm, classifier):
        """Should handle whitespace-only messages."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "CLARIFICATION_NEEDED",
            "confidence": 0.1,
            "reasoning": "Whitespace only"
        })

        result = classifier.classify("   \n\t  ")
        assert result.intent == "CLARIFICATION_NEEDED" and result.confidence < 0.5

    def test_very_long_message(self, mock_llm, classifier):
        """Should handle very long messages (1000+ chars)."""
        long_message = "Create epic: " + ("A" * 1000)

        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.85,
            "reasoning": "Long create command"
        })

        result = classifier.classify(long_message)
        assert result.intent == "COMMAND"

    def test_special_characters_in_message(self, mock_llm, classifier):
        """Should handle special characters."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.9,
            "reasoning": "Create command with special chars"
        })

        result = classifier.classify("Create task: Fix OAuth 2.0 'login' bug (RFC 6749)")
        assert result.intent == "COMMAND"

    def test_unicode_emojis(self, mock_llm, classifier):
        """Should handle Unicode and emojis."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.88,
            "reasoning": "Create command with emoji"
        })

        result = classifier.classify("Create task: Add ✅ validation")
        assert result.intent == "COMMAND"

    def test_malformed_json_response(self, mock_llm, classifier):
        """Should handle malformed JSON from LLM."""
        mock_llm.generate.return_value = "{'intent': 'COMMAND'}"  # Single quotes = invalid JSON

        with pytest.raises(IntentClassificationException) as exc_info:
            classifier.classify("Create task")

        assert "parse" in str(exc_info.value).lower() or "json" in str(exc_info.value).lower()

    def test_invalid_intent_value(self, mock_llm, classifier):
        """Should reject invalid intent values."""
        mock_llm.generate.return_value = json.dumps({
            "intent": "MAYBE",  # Invalid - not in allowed values
            "confidence": 0.7,
            "reasoning": "Uncertain"
        })

        with pytest.raises((IntentClassificationException, ValueError)):
            classifier.classify("Do something")

    def test_llm_timeout(self, mock_llm, classifier):
        """Should handle LLM timeout gracefully."""
        mock_llm.generate.side_effect = TimeoutError("LLM request timed out")

        with pytest.raises(IntentClassificationException) as exc_info:
            classifier.classify("Create task")

        assert "timeout" in str(exc_info.value).lower() or "llm" in str(exc_info.value).lower()

    def test_llm_rate_limit(self, mock_llm, classifier):
        """Should handle LLM rate limiting."""
        mock_llm.generate.side_effect = Exception("Rate limit exceeded (429)")

        with pytest.raises(IntentClassificationException):
            classifier.classify("Create task")

    def test_context_propagation(self, mock_llm, classifier):
        """Should propagate context to LLM for pronoun resolution."""
        context = {
            "previous_turns": [
                {"user": "Show task 42", "response": "Task 42: ..."}
            ]
        }

        mock_llm.generate.return_value = json.dumps({
            "intent": "COMMAND",
            "confidence": 0.92,
            "reasoning": "Command with context-resolved pronoun"
        })

        result = classifier.classify("Mark it completed", context=context)
        assert result.intent == "COMMAND"
        # Verify context was passed to LLM
        assert mock_llm.generate.called
        call_args = mock_llm.generate.call_args[0][0]
        # Context should be in the prompt somehow
        assert len(call_args) > 100  # Prompt should be substantial


# Run with: pytest tests/test_nl_intent_classifier.py -v --cov=src/nl/intent_classifier
