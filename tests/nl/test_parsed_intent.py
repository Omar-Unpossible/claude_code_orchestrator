"""Tests for ParsedIntent dataclass and NLCommandProcessor routing (ADR-017 Story 4).

This test file verifies that:
1. ParsedIntent structure is correct for COMMAND and QUESTION intents
2. NLCommandProcessor.process() returns ParsedIntent (not NLResponse)
3. Routing logic correctly differentiates COMMAND vs QUESTION
4. Metadata includes all necessary information for orchestrator routing
"""

import pytest
from src.nl.types import ParsedIntent, OperationContext, OperationType, EntityType, QueryType
from src.nl.nl_command_processor import NLCommandProcessor
from src.core.state import StateManager
from src.core.config import Config
from unittest.mock import MagicMock, Mock


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def test_config():
    """Test configuration with LLM mocked."""
    config = Config.load()
    config.set('testing.mode', True)
    config.set('llm.type', 'mock')
    return config


@pytest.fixture
def mock_llm():
    """Mock LLM plugin for testing."""
    llm = Mock()
    llm.send_prompt = Mock(return_value="COMMAND")
    return llm


@pytest.fixture
def state_manager(test_config):
    """In-memory state manager for testing."""
    state = StateManager(database_url='sqlite:///:memory:', echo=False)
    # Create test project
    state.create_project(name='Test Project', description='Test project for testing', working_dir='/tmp/test')
    return state


@pytest.fixture
def processor(mock_llm, state_manager, test_config):
    """NLCommandProcessor with mocked LLM."""
    return NLCommandProcessor(
        llm_plugin=mock_llm,
        state_manager=state_manager,
        config=test_config
    )


# =============================================================================
# Category 1: ParsedIntent Structure (8 tests)
# =============================================================================

def test_parsed_intent_command_structure(processor):
    """Test ParsedIntent structure for COMMAND intent."""
    # Mock intent classification
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))

    # Mock 5-stage pipeline
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.CREATE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.EPIC,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier="Test Epic",
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={'description': 'Test description'},
        confidence=0.9
    ))

    # Mock validation
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("create epic Test Epic")

    assert isinstance(parsed_intent, ParsedIntent)
    assert parsed_intent.intent_type == "COMMAND"
    assert parsed_intent.operation_context is not None
    assert parsed_intent.requires_execution is True
    assert parsed_intent.original_message == "create epic Test Epic"
    assert 0.0 <= parsed_intent.confidence <= 1.0


def test_parsed_intent_question_structure(processor):
    """Test ParsedIntent structure for QUESTION intent."""
    # Mock intent classification
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='QUESTION',
        confidence=0.95
    ))

    # Mock question handler
    processor.question_handler.handle = Mock(return_value=Mock(
        answer="Here's the answer",
        question_type=Mock(value='status'),
        confidence=0.9,
        entities={},
        data={}
    ))

    parsed_intent = processor.process("what's the status?")

    assert isinstance(parsed_intent, ParsedIntent)
    assert parsed_intent.intent_type == "QUESTION"
    assert parsed_intent.operation_context is None
    assert parsed_intent.requires_execution is False
    assert parsed_intent.question_context is not None
    assert 'answer' in parsed_intent.question_context


def test_parsed_intent_is_command_helper(processor):
    """Test is_command() helper method."""
    # Create COMMAND intent
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.CREATE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.TASK,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier="Test Task",
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("create task Test Task")

    assert parsed_intent.is_command() is True
    assert parsed_intent.is_question() is False


def test_parsed_intent_is_question_helper(processor):
    """Test is_question() helper method."""
    # Create QUESTION intent
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='QUESTION',
        confidence=0.95
    ))
    processor.question_handler.handle = Mock(return_value=Mock(
        answer="Answer",
        question_type=Mock(value='general'),
        confidence=0.9,
        entities={},
        data={}
    ))

    parsed_intent = processor.process("help me")

    assert parsed_intent.is_question() is True
    assert parsed_intent.is_command() is False


def test_parsed_intent_confidence_included(processor):
    """Test that confidence is properly calculated and included."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.UPDATE,
        confidence=0.8
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.PROJECT,
        confidence=0.85
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier=1,
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={'status': 'completed'},
        confidence=0.75
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("mark project 1 complete")

    # Confidence is average of 4 stages: (0.8 + 0.85 + 0.9 + 0.75) / 4 = 0.825
    assert parsed_intent.confidence > 0.8
    assert parsed_intent.confidence < 0.9


def test_parsed_intent_metadata_included(processor):
    """Test that metadata includes all necessary information."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.DELETE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.TASK,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier=5,
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("delete task 5", project_id=1, confirmed=True)

    assert 'intent_confidence' in parsed_intent.metadata
    assert 'entity_confidence' in parsed_intent.metadata
    assert 'operation' in parsed_intent.metadata
    assert 'entity_type' in parsed_intent.metadata
    assert 'project_id' in parsed_intent.metadata
    assert 'confirmed' in parsed_intent.metadata
    assert parsed_intent.metadata['project_id'] == 1
    assert parsed_intent.metadata['confirmed'] is True


def test_parsed_intent_original_message_preserved(processor):
    """Test that original message is preserved in ParsedIntent."""
    original_message = "Create an epic for user authentication system"

    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.CREATE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.EPIC,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier="user authentication system",
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process(original_message)

    assert parsed_intent.original_message == original_message


def test_parsed_intent_operation_context_complete(processor):
    """Test that OperationContext is complete with all pipeline results."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.QUERY,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.TASK,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier=None,
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={'status': 'pending'},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("show all pending tasks")

    assert parsed_intent.operation_context is not None
    assert parsed_intent.operation_context.operation == OperationType.QUERY
    assert parsed_intent.operation_context.entity_type == EntityType.TASK
    # "pending" triggers BACKLOG query type
    assert parsed_intent.operation_context.query_type == QueryType.BACKLOG
    assert parsed_intent.operation_context.parameters == {'status': 'pending'}


# =============================================================================
# Category 2: Routing Logic (6 tests)
# =============================================================================

def test_command_intent_returns_operation_context(processor):
    """Test that COMMAND intent returns OperationContext."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.CREATE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.STORY,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier="User Login",
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={'epic_id': 5},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("create story User Login in epic 5")

    assert parsed_intent.is_command()
    assert parsed_intent.operation_context is not None
    assert isinstance(parsed_intent.operation_context, OperationContext)


def test_question_intent_returns_question_context(processor):
    """Test that QUESTION intent returns question_context."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='QUESTION',
        confidence=0.95
    ))
    processor.question_handler.handle = Mock(return_value=Mock(
        answer="Project is on track",
        question_type=Mock(value='status'),
        confidence=0.9,
        entities={'project_id': 1},
        data={}
    ))

    parsed_intent = processor.process("what's the project status?")

    assert parsed_intent.is_question()
    assert parsed_intent.question_context is not None
    assert 'answer' in parsed_intent.question_context
    assert 'question_type' in parsed_intent.question_context


def test_query_command_includes_query_type(processor):
    """Test that QUERY commands include query_type in OperationContext."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.QUERY,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.PROJECT,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier=None,
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("show project hierarchy")

    assert parsed_intent.operation_context.operation == OperationType.QUERY
    assert parsed_intent.operation_context.query_type in [
        QueryType.SIMPLE,
        QueryType.HIERARCHICAL,
        QueryType.NEXT_STEPS,
        QueryType.BACKLOG,
        QueryType.ROADMAP
    ]


def test_create_command_includes_parameters(processor):
    """Test that CREATE commands include parameters."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.CREATE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.TASK,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier="Write tests",
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={'priority': 'HIGH', 'status': 'PENDING'},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("create task Write tests with priority HIGH")

    assert parsed_intent.operation_context.parameters == {
        'priority': 'HIGH',
        'status': 'PENDING'
    }


def test_update_command_includes_identifier(processor):
    """Test that UPDATE commands include identifier."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.UPDATE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.EPIC,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier=3,
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={'status': 'COMPLETED'},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("mark epic 3 as completed")

    assert parsed_intent.operation_context.identifier == 3
    assert parsed_intent.operation_context.parameters == {'status': 'COMPLETED'}


def test_delete_command_includes_identifier(processor):
    """Test that DELETE commands include identifier."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.DELETE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.TASK,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier=7,
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))

    parsed_intent = processor.process("delete task 7")

    assert parsed_intent.operation_context.identifier == 7
    assert parsed_intent.operation_context.operation == OperationType.DELETE


# =============================================================================
# Category 3: Backward Compatibility (4 tests)
# =============================================================================

def test_process_and_execute_deprecation_warning(processor):
    """Test that process_and_execute() raises deprecation warning."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='QUESTION',
        confidence=0.95
    ))
    processor.question_handler.handle = Mock(return_value=Mock(
        answer="Answer",
        question_type=Mock(value='general'),
        confidence=0.9,
        entities={},
        data={}
    ))

    with pytest.warns(DeprecationWarning, match="process_and_execute.*deprecated"):
        response = processor.process_and_execute("help")
        assert response is not None


def test_process_and_execute_still_works(processor):
    """Test that process_and_execute() still returns NLResponse."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='QUESTION',
        confidence=0.95
    ))
    processor.question_handler.handle = Mock(return_value=Mock(
        answer="Test answer",
        question_type=Mock(value='help'),
        confidence=0.9,
        entities={},
        data={}
    ))

    with pytest.warns(DeprecationWarning):
        response = processor.process_and_execute("help")

        # Should return NLResponse, not ParsedIntent
        assert hasattr(response, 'response')
        assert hasattr(response, 'intent')
        assert hasattr(response, 'success')
        assert response.intent == 'QUESTION'


def test_process_and_execute_handles_questions(processor):
    """Test that process_and_execute() handles questions inline."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='QUESTION',
        confidence=0.95
    ))
    processor.question_handler.handle = Mock(return_value=Mock(
        answer="The status is good",
        question_type=Mock(value='status'),
        confidence=0.9,
        entities={},
        data={}
    ))

    with pytest.warns(DeprecationWarning):
        response = processor.process_and_execute("what's the status?")

        assert response.intent == 'QUESTION'
        assert response.success is True
        assert "status is good" in response.response


def test_process_and_execute_handles_commands(processor):
    """Test that process_and_execute() executes commands via command_executor."""
    processor.intent_classifier.classify = Mock(return_value=Mock(
        intent='COMMAND',
        confidence=0.95
    ))
    processor.operation_classifier.classify = Mock(return_value=Mock(
        operation_type=OperationType.CREATE,
        confidence=0.9
    ))
    processor.entity_type_classifier.classify = Mock(return_value=Mock(
        entity_type=EntityType.PROJECT,
        confidence=0.9
    ))
    processor.entity_identifier_extractor.extract = Mock(return_value=Mock(
        identifier="New Project",
        confidence=0.9
    ))
    processor.parameter_extractor.extract = Mock(return_value=Mock(
        parameters={},
        confidence=0.9
    ))
    processor.command_validator.validate = Mock(return_value=Mock(
        valid=True,
        errors=[]
    ))
    processor.command_executor.execute = Mock(return_value=Mock(
        success=True,
        created_ids=[1],
        errors=[]
    ))
    processor.response_formatter.format = Mock(return_value="Created project")

    with pytest.warns(DeprecationWarning):
        response = processor.process_and_execute("create project New Project")

        assert response.intent == 'COMMAND'
        assert response.success is True
        assert processor.command_executor.execute.called
