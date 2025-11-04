"""Test PromptGenerator structured mode integration.

Tests for:
- PromptGenerator initialization with structured mode
- Mode switching (structured vs unstructured)
- Delegation to StructuredPromptBuilder in structured mode
- Backward compatibility (unstructured mode still works)

Part of TASK_3.5: Test structured prompt system
"""

import pytest
from unittest.mock import Mock, MagicMock
from pathlib import Path
from src.llm.prompt_generator import PromptGenerator
from src.llm.structured_prompt_builder import StructuredPromptBuilder
from src.llm.prompt_rule_engine import PromptRuleEngine
from src.core.state import StateManager
from src.core.models import Task


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_interface():
    """Provide a mock LLM interface."""
    mock = Mock()
    mock.count_tokens = Mock(return_value=100)
    mock.summarize = Mock(return_value="Summary")
    return mock


@pytest.fixture
def template_dir():
    """Provide path to template directory."""
    return str(Path('templates'))


@pytest.fixture
def state_manager():
    """Provide a StateManager with test database."""
    StateManager.reset_instance()
    sm = StateManager.get_instance(
        database_url='sqlite:///:memory:',
        echo=False
    )
    yield sm
    sm.close()
    StateManager.reset_instance()


@pytest.fixture
def test_project(state_manager):
    """Create a test project."""
    return state_manager.create_project(
        name='test_structured_mode',
        description='Test project for structured mode',
        working_dir='/tmp/test'
    )


@pytest.fixture
def test_task(state_manager, test_project):
    """Create a test task."""
    return state_manager.create_task(
        project_id=test_project.id,
        task_data={
            'title': 'Test task for structured prompts',
            'description': 'Testing structured mode',
            'priority': 5
        }
    )


@pytest.fixture
def rule_engine():
    """Provide a PromptRuleEngine with loaded rules."""
    engine = PromptRuleEngine('config/prompt_rules.yaml')
    engine.load_rules_from_yaml()
    return engine


@pytest.fixture
def structured_builder(rule_engine):
    """Provide a StructuredPromptBuilder."""
    return StructuredPromptBuilder(rule_engine=rule_engine)


# ============================================================================
# Tests: Initialization
# ============================================================================

def test_prompt_generator_initialization_unstructured_mode(template_dir, mock_llm_interface, state_manager):
    """Test default initialization (unstructured mode)."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager
    )

    assert generator._is_structured_mode() is False
    assert generator._structured_builder is None


def test_prompt_generator_initialization_with_structured_mode(template_dir, mock_llm_interface, state_manager, structured_builder):
    """Test initialization with structured mode enabled."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=True,
        structured_builder=structured_builder
    )

    assert generator._is_structured_mode() is True
    assert generator._structured_builder is not None


# ============================================================================
# Tests: Mode Checking and Switching
# ============================================================================

def test_is_structured_mode(template_dir, mock_llm_interface, state_manager, structured_builder):
    """Test checking if structured mode is enabled."""
    # Unstructured
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager
    )
    assert generator._is_structured_mode() is False

    # Structured
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=True,
        structured_builder=structured_builder
    )
    assert generator._is_structured_mode() is True


def test_set_structured_mode(template_dir, mock_llm_interface, state_manager, structured_builder):
    """Test toggling structured mode at runtime."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager
    )

    # Initially unstructured
    assert generator._is_structured_mode() is False

    # Enable structured mode
    generator.set_structured_mode(enabled=True, builder=structured_builder)
    assert generator._is_structured_mode() is True
    assert generator._structured_builder is not None

    # Disable structured mode
    generator.set_structured_mode(enabled=False)
    assert generator._is_structured_mode() is False


def test_ensure_structured_builder_raises_without_builder(template_dir, mock_llm_interface, state_manager):
    """Test that _ensure_structured_builder raises when no builder provided."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=True,
        structured_builder=None  # No builder
    )

    with pytest.raises(Exception):
        generator._ensure_structured_builder()


# ============================================================================
# Tests: Structured Mode Prompt Generation
# ============================================================================

def test_generate_task_prompt_structured_mode(template_dir, mock_llm_interface, state_manager, test_task, structured_builder):
    """Test generating task prompt in structured mode."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=True,
        structured_builder=structured_builder
    )

    context = {'project_id': 1, 'files': ['/path/to/file.py']}
    prompt = generator.generate_task_prompt(task=test_task, context=context)

    # Should contain structured format
    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '"prompt_type": "task_execution"' in prompt


def test_generate_validation_prompt_structured_mode(template_dir, mock_llm_interface, state_manager, test_task, structured_builder):
    """Test generating validation prompt in structured mode."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=True,
        structured_builder=structured_builder
    )

    work_output = {'files_modified': ['/path/to/file.py'], 'code': 'def foo(): pass'}
    context = {}

    prompt = generator.generate_validation_prompt(
        task=test_task,
        work_output=work_output,
        context=context
    )

    # Should contain structured format
    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt


def test_generate_error_analysis_prompt_structured_mode(template_dir, mock_llm_interface, state_manager, test_task, structured_builder):
    """Test generating error analysis prompt in structured mode."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=True,
        structured_builder=structured_builder
    )

    error_data = {
        'error_type': 'runtime',
        'error_message': 'AttributeError',
        'traceback': 'File test.py, line 10',  # Changed from 'stack_trace' to 'traceback'
        'failed_file': '/path/to/file.py',
        'failed_line': 10
    }
    context = {}

    prompt = generator.generate_error_analysis_prompt(
        task=test_task,
        error_data=error_data,
        context=context
    )

    # Should contain structured format
    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt


def test_generate_decision_prompt_structured_mode(template_dir, mock_llm_interface, state_manager, test_task, structured_builder):
    """Test generating decision prompt in structured mode."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=True,
        structured_builder=structured_builder
    )

    agent_response = {'status': 'completed', 'confidence': 0.85}
    context = {
        'current_state': 'completed',  # Added required field
        'validation_result': {'is_valid': False, 'quality_score': 65}  # Changed to singular
    }

    prompt = generator.generate_decision_prompt(
        task=test_task,
        agent_response=agent_response,
        context=context
    )

    # Should contain structured format
    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt


# ============================================================================
# Tests: Unstructured Mode (Backward Compatibility)
# ============================================================================

def test_generate_task_prompt_unstructured_mode(template_dir, mock_llm_interface, state_manager, test_task):
    """Test generating task prompt in unstructured mode (backward compatibility)."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager,
        structured_mode=False  # Explicit unstructured
    )

    context = {}
    prompt = generator.generate_task_prompt(task=test_task, context=context)

    # Should NOT contain structured tags (uses templates instead)
    # Note: This depends on actual unstructured implementation
    assert isinstance(prompt, str)
    assert len(prompt) > 0


# ============================================================================
# Tests: Mode Toggle at Runtime
# ============================================================================

def test_mode_toggle_at_runtime(template_dir, mock_llm_interface, state_manager, test_task, structured_builder):
    """Test toggling between structured and unstructured modes."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager
    )

    context = {}

    # Start in unstructured mode
    assert generator._is_structured_mode() is False

    # Switch to structured mode
    generator.set_structured_mode(enabled=True, builder=structured_builder)
    assert generator._is_structured_mode() is True

    prompt = generator.generate_task_prompt(task=test_task, context=context)
    assert '<METADATA>' in prompt

    # Switch back to unstructured mode
    generator.set_structured_mode(enabled=False)
    assert generator._is_structured_mode() is False


# ============================================================================
# Tests: Task Conversion
# ============================================================================

def test_task_to_dict(template_dir, mock_llm_interface, state_manager, test_task):
    """Test _task_to_dict helper method."""
    generator = PromptGenerator(
        template_dir=template_dir,
        llm_interface=mock_llm_interface,
        state_manager=state_manager
    )

    task_dict = generator._task_to_dict(test_task)

    assert 'task_id' in task_dict  # StructuredPromptBuilder expects 'task_id'
    assert 'title' in task_dict
    assert 'description' in task_dict
    assert task_dict['task_id'] == test_task.id
    assert task_dict['title'] == test_task.title
