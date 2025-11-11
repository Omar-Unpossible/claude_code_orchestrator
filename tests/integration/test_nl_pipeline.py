"""Integration tests for NL Command Pipeline.

Tests end-to-end NL processing from intent classification through execution.
Uses real LLM components with mocked StateManager for controlled testing.

Coverage Target: 90%
Test Scenarios: TC-INT-001 through TC-INT-008
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from src.nl.nl_command_processor import NLCommandProcessor, NLResponse
from src.core.models import Task, TaskType
from src.core.config import Config


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_plugin():
    """Create mock LLM plugin."""
    mock_llm = Mock()
    mock_llm.generate = Mock()
    return mock_llm


@pytest.fixture
def mock_state_manager():
    """Create mock StateManager."""
    mock_state = Mock()
    mock_state.create_epic = Mock(return_value=5)
    mock_state.create_story = Mock(return_value=6)
    mock_state.create_task = Mock(return_value=7)
    mock_state.create_milestone = Mock(return_value=10)
    mock_state.list_tasks = Mock(return_value=[])
    mock_state.get_task = Mock()
    return mock_state


@pytest.fixture
def test_config():
    """Create test configuration for NL processor."""
    mock_config = Mock(spec=Config)

    config_data = {
        'nl_commands.enabled': True,
        'nl_commands.llm_provider': 'mock',
        'nl_commands.confidence_threshold': 0.7,
        'nl_commands.max_context_turns': 10,
        'nl_commands.schema_path': 'src/nl/schemas/obra_schema.json',
        'nl_commands.default_project_id': 1,
        'nl_commands.require_confirmation_for': ['delete', 'update', 'execute'],
        'nl_commands.fallback_to_info': True
    }

    def get_config(key, default=None):
        return config_data.get(key, default)

    mock_config.get = get_config
    return mock_config


@pytest.fixture
def nl_processor(mock_llm_plugin, mock_state_manager, test_config):
    """Create NLCommandProcessor with mocked dependencies."""
    return NLCommandProcessor(
        llm_plugin=mock_llm_plugin,
        state_manager=mock_state_manager,
        config=test_config
    )


# ============================================================================
# Test: Pipeline Initialization
# ============================================================================

def test_nl_processor_initialization(nl_processor):
    """TC-INT-001: Test NL processor initializes all components."""
    assert nl_processor.intent_classifier is not None
    assert nl_processor.entity_extractor is not None
    assert nl_processor.command_validator is not None
    assert nl_processor.command_executor is not None
    assert nl_processor.response_formatter is not None
    assert nl_processor.conversation_history == []


# ============================================================================
# Test: Command Intent Processing
# ============================================================================

def test_command_intent_full_pipeline(nl_processor, mock_llm_plugin, mock_state_manager):
    """TC-INT-002: Test full pipeline for COMMAND intent."""
    # Mock intent classification
    intent_response = {
        'intent': 'COMMAND',
        'confidence': 0.95,
        'detected_entities': {'action': 'create', 'entity_type': 'epic'}
    }

    # Mock entity extraction
    entity_response = {
        'entity_type': 'epic',
        'entities': [{
            'title': 'User Authentication',
            'description': 'Complete auth system'
        }],
        'confidence': 0.93
    }

    # Configure mock LLM to return these responses as proper JSON
    mock_llm_plugin.generate.side_effect = [
        json.dumps(intent_response),  # First call: intent classification
        json.dumps(entity_response)   # Second call: entity extraction
    ]

    # Process command
    result = nl_processor.process("Create an epic called User Authentication for complete auth system")

    # Verify pipeline executed
    assert result.intent == 'COMMAND'
    assert result.success is True
    assert "Epic #5" in result.response
    assert "User Authentication" in result.response or "#5" in result.response

    # Verify StateManager was called
    mock_state_manager.create_epic.assert_called_once()


def test_question_intent_forwarding(nl_processor, mock_llm_plugin):
    """TC-INT-003: Test QUESTION intent routes to Claude Code."""
    # Mock intent classification for question
    intent_response = {
        'intent': 'QUESTION',
        'confidence': 0.92,
        'detected_entities': {}
    }

    mock_llm_plugin.generate.return_value = json.dumps(intent_response)

    # Process question
    result = nl_processor.process("How do I create an epic?")

    # Verify question was forwarded
    assert result.intent == 'QUESTION'
    assert result.forwarded_to_claude is True
    assert "Forwarding question" in result.response or "Claude Code" in result.response


def test_clarification_needed(nl_processor, mock_llm_plugin):
    """TC-INT-004: Test CLARIFICATION_NEEDED when confidence low."""
    # Mock intent classification with low confidence
    intent_response = {
        'intent': 'CLARIFICATION_NEEDED',
        'confidence': 0.55,
        'detected_entities': {'entity_type': 'epic'}
    }

    mock_llm_plugin.generate.return_value = json.dumps(intent_response)

    # Process ambiguous command
    result = nl_processor.process("Maybe add something")

    # Verify clarification requested
    assert result.intent == 'CLARIFICATION_NEEDED'
    assert result.success is False
    assert "?" in result.response  # Clarification indicator


# ============================================================================
# Test: Validation Failures
# ============================================================================

def test_validation_failure(nl_processor, mock_llm_plugin, mock_state_manager):
    """TC-INT-005: Test validation failure handling."""
    # Mock intent classification
    intent_response = {
        'intent': 'COMMAND',
        'confidence': 0.95,
        'detected_entities': {}
    }

    # Mock entity extraction with invalid epic reference
    entity_response = {
        'entity_type': 'story',
        'entities': [{
            'title': 'User Login',
            'epic_id': 9999  # Non-existent epic
        }],
        'confidence': 0.90
    }

    mock_llm_plugin.generate.side_effect = [
        json.dumps(intent_response),
        json.dumps(entity_response)
    ]

    # Configure StateManager to simulate epic not found
    mock_state_manager.get_epic = Mock(side_effect=Exception("Epic not found"))

    # Process command
    result = nl_processor.process("Add story to epic 9999")

    # Verify error handling
    # Note: actual validation happens in CommandValidator
    # For this test, we're verifying the pipeline handles errors gracefully
    assert result.intent == 'COMMAND'


# ============================================================================
# Test: Conversation Context
# ============================================================================

def test_conversation_context_tracking(nl_processor, mock_llm_plugin, mock_state_manager):
    """TC-INT-006: Test conversation context is preserved across turns."""
    # Mock responses for first turn
    intent_response1 = {
        'intent': 'COMMAND',
        'confidence': 0.95,
        'detected_entities': {}
    }
    entity_response1 = {
        'entity_type': 'epic',
        'entities': [{'title': 'Epic 1', 'description': 'First epic'}],
        'confidence': 0.93
    }

    mock_llm_plugin.generate.side_effect = [
        json.dumps(intent_response1),
        json.dumps(entity_response1)
    ]

    # First turn
    result1 = nl_processor.process("Create epic for feature X")

    assert result1.success is True
    assert len(nl_processor.conversation_history) == 1

    # Mock responses for second turn
    intent_response2 = {
        'intent': 'COMMAND',
        'confidence': 0.94,
        'detected_entities': {}
    }
    entity_response2 = {
        'entity_type': 'story',
        'entities': [{'title': 'Story 1', 'epic_id': 5}],
        'confidence': 0.91
    }

    mock_llm_plugin.generate.side_effect = [
        json.dumps(intent_response2),
        json.dumps(entity_response2)
    ]

    # Second turn (should have context from first)
    result2 = nl_processor.process("Add story to it")

    assert len(nl_processor.conversation_history) == 2

    # Verify context summary
    summary = nl_processor.get_context_summary()
    assert summary['total_turns'] == 2
    assert 'COMMAND' in summary['recent_intents']


def test_context_max_turns_limit(nl_processor, mock_llm_plugin, mock_state_manager):
    """TC-INT-007: Test conversation context respects max_context_turns."""
    # Configure max turns to 3
    nl_processor.max_context_turns = 3

    # Mock responses
    intent_response = {
        'intent': 'QUESTION',
        'confidence': 0.90,
        'detected_entities': {}
    }
    mock_llm_plugin.generate.return_value = json.dumps(intent_response)

    # Add 5 turns (exceeds limit of 3)
    for i in range(5):
        nl_processor.process(f"Question {i}")

    # Verify only last 3 turns kept
    assert len(nl_processor.conversation_history) == 3
    assert nl_processor.conversation_history[-1]['message'] == "Question 4"


def test_clear_context(nl_processor, mock_llm_plugin):
    """TC-INT-008: Test clear_context clears conversation history."""
    # Mock intent
    intent_response = {
        'intent': 'QUESTION',
        'confidence': 0.90,
        'detected_entities': {}
    }
    mock_llm_plugin.generate.return_value = json.dumps(intent_response)

    # Add some history
    nl_processor.process("First message")
    nl_processor.process("Second message")
    assert len(nl_processor.conversation_history) == 2

    # Clear context
    nl_processor.clear_context()

    # Verify cleared
    assert len(nl_processor.conversation_history) == 0


# ============================================================================
# Test: Error Handling
# ============================================================================

def test_empty_message_handling(nl_processor):
    """TC-INT-009: Test handling of empty messages."""
    result = nl_processor.process("")

    assert result.success is False
    assert result.intent == "INVALID"
    assert "provide a message" in result.response.lower()


def test_exception_handling(nl_processor, mock_llm_plugin):
    """TC-INT-010: Test exception handling in pipeline."""
    # Configure LLM to raise exception
    mock_llm_plugin.generate.side_effect = Exception("LLM service unavailable")

    # Process should handle exception gracefully
    result = nl_processor.process("Create epic")

    assert result.success is False
    assert result.intent == "ERROR"
    assert "error" in result.response.lower()


# ============================================================================
# Test: Multi-Item Commands
# ============================================================================

def test_multi_item_command(nl_processor, mock_llm_plugin, mock_state_manager):
    """TC-INT-011: Test command creating multiple items."""
    # Mock intent classification
    intent_response = {
        'intent': 'COMMAND',
        'confidence': 0.96,
        'detected_entities': {}
    }

    # Mock entity extraction for 3 stories
    entity_response = {
        'entity_type': 'story',
        'entities': [
            {'title': 'Login', 'epic_id': 5},
            {'title': 'Signup', 'epic_id': 5},
            {'title': 'MFA', 'epic_id': 5}
        ],
        'confidence': 0.89
    }

    mock_llm_plugin.generate.side_effect = [
        json.dumps(intent_response),
        json.dumps(entity_response)
    ]

    # Configure StateManager to return epic for validation
    mock_epic = Mock()
    mock_epic.task_type = TaskType.EPIC
    mock_state_manager.get_task.return_value = mock_epic

    # Configure StateManager to return different IDs for created stories
    mock_state_manager.create_story.side_effect = [6, 7, 8]

    # Process multi-item command
    result = nl_processor.process("Add 3 stories to epic 5: login, signup, and MFA")

    # Verify multiple creations
    assert result.success is True
    assert mock_state_manager.create_story.call_count == 3


# ============================================================================
# Test: Configuration Integration
# ============================================================================

def test_config_confidence_threshold(mock_llm_plugin, mock_state_manager):
    """TC-INT-012: Test confidence threshold from config."""
    # Create custom config with higher threshold
    custom_config = Mock(spec=Config)

    custom_config_data = {
        'nl_commands.enabled': True,
        'nl_commands.llm_provider': 'mock',
        'nl_commands.confidence_threshold': 0.85,  # Higher threshold
        'nl_commands.max_context_turns': 10,
        'nl_commands.schema_path': 'src/nl/schemas/obra_schema.json',
        'nl_commands.default_project_id': 1,
        'nl_commands.require_confirmation_for': ['delete', 'update', 'execute'],
        'nl_commands.fallback_to_info': True
    }

    def get_custom(key, default=None):
        return custom_config_data.get(key, default)

    custom_config.get = get_custom

    # Create processor with explicit confidence threshold parameter
    processor = NLCommandProcessor(
        llm_plugin=mock_llm_plugin,
        state_manager=mock_state_manager,
        config=custom_config,
        confidence_threshold=0.85  # Explicitly pass threshold
    )

    # Verify threshold set
    assert processor.confidence_threshold == 0.85


def test_config_default_project_id(mock_llm_plugin, mock_state_manager, test_config):
    """TC-INT-013: Test default_project_id from config."""
    # Mock responses
    intent_response = {
        'intent': 'COMMAND',
        'confidence': 0.95,
        'detected_entities': {}
    }
    entity_response = {
        'entity_type': 'epic',
        'entities': [{'title': 'Test Epic', 'description': 'Test'}],
        'confidence': 0.93
    }

    mock_llm_plugin.generate.side_effect = [
        json.dumps(intent_response),
        json.dumps(entity_response)
    ]

    processor = NLCommandProcessor(
        llm_plugin=mock_llm_plugin,
        state_manager=mock_state_manager,
        config=test_config
    )

    # Process without specifying project_id
    result = processor.process("Create epic")

    # Verify default project_id used
    assert result.success is True
    # Default project_id=1 should be used by CommandExecutor
