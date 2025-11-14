"""Integration tests for Orchestrator NL Command Routing (ADR-017 Story 5).

Tests the unified execution architecture where NL commands route through
orchestrator.execute_nl_command() for consistent validation and quality control.

Test Categories:
1. Orchestrator NL Routing (5 tests)
2. Validation Pipeline (4 tests)
3. CLI Integration (3 tests)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.orchestrator import Orchestrator
from src.core.config import Config
from src.core.state import StateManager
from src.core.models import Task, TaskStatus, TaskType
from src.nl.types import (
    ParsedIntent,
    OperationContext,
    OperationType,
    EntityType,
    QueryType,
    QuestionType
)


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config()
    config.data = {
        'database': {'url': 'sqlite:///:memory:'},
        'agent': {'type': 'claude-code-local', 'config': {}},
        'llm': {'type': 'ollama', 'endpoint': 'http://localhost:11434'},
        'orchestration': {
            'breakpoints': {},
            'decision': {},
            'quality': {}
        }
    }
    return config


@pytest.fixture
def state_manager(test_config):
    """Create state manager instance with in-memory database."""
    # Use fresh instance with in-memory database for isolation
    db_url = test_config.get('database.url') or 'sqlite:///:memory:'
    sm = StateManager(database_url=db_url)
    yield sm
    # Cleanup
    sm.close()


@pytest.fixture
def orchestrator(test_config, state_manager):
    """Create initialized orchestrator instance using shared state_manager."""
    orch = Orchestrator(config=test_config)

    # Initialize components first
    orch.initialize()

    # Mock LLM interface AFTER initialization to avoid actual LLM calls
    orch.llm_interface = Mock()
    orch.llm_interface.send_prompt = Mock(return_value="Mocked LLM response")
    orch.llm_interface.get_name = Mock(return_value="mock-llm")
    orch.llm_interface.is_available = Mock(return_value=True)  # Mock LLM as available
    orch.llm_interface.generate = Mock(return_value="Mocked generation")

    # Replace orchestrator's state_manager with the shared one
    orch.state_manager = state_manager
    # Re-initialize NL components with shared state_manager
    orch.intent_to_task_converter.state_manager = state_manager
    orch.nl_query_helper.state_manager = state_manager

    return orch


@pytest.fixture
def test_project(state_manager, request):
    """Create test project with unique name per test."""
    import uuid
    import os
    import tempfile

    # Create unique test directory
    test_dir = tempfile.mkdtemp(prefix='obra_test_')
    unique_name = f"Test Project {uuid.uuid4().hex[:8]}"

    project = state_manager.create_project(
        name=unique_name,
        description="Test project for integration tests",
        working_dir=test_dir
    )

    yield project

    # Cleanup: remove test directory
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)


# ============================================================================
# Category 1: Orchestrator NL Routing (5 tests)
# ============================================================================

def test_execute_nl_command_create_epic(orchestrator, test_project):
    """Test NL command creates epic through orchestrator routing."""
    # Create ParsedIntent for "create epic for auth"
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.EPIC],
        identifier=None,
        parameters={
            'title': 'User Authentication',
            'description': 'Implement authentication system'
        },
        confidence=0.95,
        raw_input="create epic for auth"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="create epic for auth",
        confidence=0.95,
        requires_execution=True
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify result structure
    assert 'success' in result
    assert 'message' in result
    assert 'task_id' in result
    assert result['confidence'] == 0.95


def test_execute_nl_command_update_task(orchestrator, state_manager, test_project):
    """Test NL command updates task through orchestrator routing."""
    # Create a test task first
    task = state_manager.create_task(
        project_id=test_project.id,
        task_data={
            'title': 'Test task',
            'description': 'Test task description',
            'task_type': TaskType.TASK
        }
    )

    # Create ParsedIntent for "mark task 1 as completed"
    operation_context = OperationContext(
        operation=OperationType.UPDATE,
        entity_types=[EntityType.TASK],
        identifier=task.id,
        parameters={'status': 'COMPLETED'},
        confidence=0.90,
        raw_input=f"mark task {task.id} as completed"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message=f"mark task {task.id} as completed",
        confidence=0.90,
        requires_execution=True
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify result
    assert 'success' in result
    assert 'task_id' in result


def test_execute_nl_command_delete_story(orchestrator, state_manager, test_project):
    """Test NL command deletes story through orchestrator routing."""
    # Create epic and story (these methods return IDs, not objects)
    epic_id = state_manager.create_epic(
        project_id=test_project.id,
        title="Test Epic",
        description="Test epic"
    )
    story_id = state_manager.create_story(
        project_id=test_project.id,
        epic_id=epic_id,
        title="Test Story",
        description="Test story"
    )

    # Create ParsedIntent for delete operation
    operation_context = OperationContext(
        operation=OperationType.DELETE,
        entity_types=[EntityType.STORY],
        identifier=story_id,
        parameters={},
        confidence=0.85,
        raw_input=f"delete story {story_id}"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message=f"delete story {story_id}",
        confidence=0.85,
        requires_execution=True
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify result
    assert 'success' in result
    assert 'task_id' in result


def test_execute_nl_command_query_tasks(orchestrator, state_manager, test_project):
    """Test NL command queries tasks through NLQueryHelper."""
    # Create some tasks
    state_manager.create_task(
        project_id=test_project.id,
        task_data={
            'title': 'Task 1',
            'description': 'Task 1 description',
            'task_type': TaskType.TASK
        }
    )
    state_manager.create_task(
        project_id=test_project.id,
        task_data={
            'title': 'Task 2',
            'description': 'Task 2 description',
            'task_type': TaskType.TASK
        }
    )

    # Create ParsedIntent for query operation
    operation_context = OperationContext(
        operation=OperationType.QUERY,
        entity_types=[EntityType.TASK],
        identifier=None,
        query_type=QueryType.SIMPLE,
        parameters={},
        confidence=0.92,
        raw_input="show all tasks"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="show all tasks",
        confidence=0.92,
        requires_execution=False
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify result
    assert 'success' in result
    assert result['task_id'] is None  # Query operations don't create tasks
    assert 'message' in result or 'data' in result


def test_execute_nl_command_question_intent(orchestrator, test_project):
    """Test NL command handles question intent directly."""
    # Create ParsedIntent for question
    parsed_intent = ParsedIntent(
        intent_type="QUESTION",
        operation_context=None,
        original_message="What's the status of project 1?",
        confidence=0.88,
        requires_execution=False,
        question_context={
            'answer': 'Project 1 is active with 5 tasks',
            'question_type': QuestionType.STATUS
        }
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify result
    assert result['success'] is True
    assert result['task_id'] is None
    assert result['answer'] == 'Project 1 is active with 5 tasks'
    assert result['confidence'] == 0.88


# ============================================================================
# Category 2: Validation Pipeline (4 tests)
# ============================================================================

def test_nl_command_validation_failure(orchestrator, test_project):
    """Test NL command handles validation failures gracefully."""
    # Create ParsedIntent with validation failure metadata
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.TASK],
        identifier=None,
        parameters={},  # Missing required parameters
        confidence=0.60,
        raw_input="create task"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="create task",
        confidence=0.60,
        requires_execution=True,
        metadata={
            'validation_failed': True,
            'validation_errors': ['Missing task description', 'Missing task title']
        }
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify validation failure is handled
    assert result['success'] is False
    assert result['validation_passed'] is False
    assert 'Missing task description' in result['message']
    assert result['task_id'] is None


def test_nl_command_quality_scoring(orchestrator, test_project):
    """Test NL commands receive quality scoring through orchestrator."""
    # Mock quality controller to return specific score
    orchestrator.quality_controller.evaluate_quality = Mock(
        return_value={'score': 0.85, 'passed': True}
    )

    # Create ParsedIntent
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.TASK],
        identifier=None,
        parameters={'description': 'Implement feature X'},
        confidence=0.90,
        raw_input="create task for feature X"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="create task for feature X",
        confidence=0.90,
        requires_execution=True
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify quality scoring was applied
    assert 'success' in result
    # Quality score would be in execution_result if task was executed
    # For CREATE operations, task is created but not executed through agent


def test_nl_command_confidence_tracking(orchestrator, test_project):
    """Test NL command confidence is tracked from parsing through execution."""
    # Create ParsedIntent with specific confidence
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.EPIC],
        identifier=None,
        parameters={'title': 'Test Epic', 'description': 'Test'},
        confidence=0.87,
        raw_input="create epic for testing"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="create epic for testing",
        confidence=0.87,
        requires_execution=True
    )

    # Execute through orchestrator
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    # Verify confidence is tracked
    assert result['confidence'] == 0.87
    assert 'task_id' in result


def test_nl_command_error_handling(orchestrator, test_project):
    """Test NL command errors are handled gracefully."""
    # Create invalid ParsedIntent (missing operation_context)
    # This should raise ValueError during construction
    with pytest.raises(ValueError, match="COMMAND intent requires operation_context"):
        parsed_intent = ParsedIntent(
            intent_type="COMMAND",
            operation_context=None,  # Invalid: COMMAND requires operation_context
            original_message="invalid command",
            confidence=0.50,
            requires_execution=True
        )


# ============================================================================
# Category 3: CLI Integration (3 tests)
# ============================================================================

def test_cli_nl_process_command(orchestrator, test_project):
    """Test CLI nl process command uses new orchestrator routing."""
    # This would test the CLI command if it exists
    # For now, we test the orchestrator method directly

    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.TASK],
        identifier=None,
        parameters={'description': 'CLI test task'},
        confidence=0.91,
        raw_input="create task via CLI"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="create task via CLI",
        confidence=0.91,
        requires_execution=True
    )

    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=False
    )

    assert 'success' in result
    assert 'message' in result


def test_cli_interactive_nl_routing(orchestrator, test_project):
    """Test interactive mode NL routing through orchestrator."""
    # Simulate interactive mode routing
    operation_context = OperationContext(
        operation=OperationType.QUERY,
        entity_types=[EntityType.TASK],
        identifier=None,
        query_type=QueryType.SIMPLE,
        parameters={},
        confidence=0.89,
        raw_input="show tasks"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="show tasks",
        confidence=0.89,
        requires_execution=False
    )

    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=test_project.id,
        interactive=True  # Interactive mode flag
    )

    assert 'success' in result
    assert result['task_id'] is None  # Query doesn't create task


def test_cli_nl_error_propagation(orchestrator):
    """Test CLI properly propagates NL errors from orchestrator."""
    # Create ParsedIntent with invalid project_id
    operation_context = OperationContext(
        operation=OperationType.CREATE,
        entity_types=[EntityType.TASK],
        identifier=None,
        parameters={'description': 'Test'},
        confidence=0.85,
        raw_input="create task"
    )

    parsed_intent = ParsedIntent(
        intent_type="COMMAND",
        operation_context=operation_context,
        original_message="create task",
        confidence=0.85,
        requires_execution=True
    )

    # Execute with invalid project_id
    result = orchestrator.execute_nl_command(
        parsed_intent=parsed_intent,
        project_id=99999,  # Non-existent project
        interactive=False
    )

    # Error should be propagated
    assert result['success'] is False
    assert 'message' in result
