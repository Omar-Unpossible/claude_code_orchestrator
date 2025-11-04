"""Test StructuredPromptBuilder for hybrid prompt generation.

Tests for:
- StructuredPromptBuilder class
- All 5 prompt types (task_execution, validation, error_analysis, decision, planning)
- Rule injection from PromptRuleEngine
- Metadata formatting
- Error handling

Part of TASK_3.5: Test structured prompt system
"""

import pytest
from src.llm.structured_prompt_builder import StructuredPromptBuilder, StructuredPromptBuilderException
from src.llm.prompt_rule_engine import PromptRuleEngine


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def rule_engine():
    """Provide a PromptRuleEngine with loaded rules."""
    engine = PromptRuleEngine('config/prompt_rules.yaml')
    engine.load_rules_from_yaml()
    return engine


@pytest.fixture
def builder_with_rules(rule_engine):
    """Provide a StructuredPromptBuilder with PromptRuleEngine."""
    return StructuredPromptBuilder(rule_engine=rule_engine)


@pytest.fixture
def builder_without_rules():
    """Provide a StructuredPromptBuilder without PromptRuleEngine."""
    return StructuredPromptBuilder(rule_engine=None)


# ============================================================================
# Tests: Initialization
# ============================================================================

def test_structured_prompt_builder_initialization():
    """Test StructuredPromptBuilder initializes correctly."""
    builder = StructuredPromptBuilder()

    assert builder.rule_engine is None
    assert builder.stats['prompts_built'] == 0


def test_structured_prompt_builder_with_rule_engine(rule_engine):
    """Test initialization with PromptRuleEngine."""
    builder = StructuredPromptBuilder(rule_engine=rule_engine)

    assert builder.rule_engine is not None
    assert builder.rule_engine == rule_engine


# ============================================================================
# Tests: Task Execution Prompts
# ============================================================================

def test_build_task_execution_prompt(builder_with_rules):
    """Test building task execution prompt."""
    task_data = {
        'task_id': 123,
        'title': 'Implement authentication',
        'description': 'Add JWT-based user authentication'
    }
    context = {
        'project_id': 1,
        'files': ['/path/to/auth.py'],
        'dependencies': ['jwt', 'bcrypt']
    }

    prompt = builder_with_rules.build_task_execution_prompt(
        task_data=task_data,
        context=context
    )

    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '"prompt_type": "task_execution"' in prompt
    assert '"task_id": 123' in prompt
    assert 'Implement authentication' in prompt
    assert '"rules"' in prompt  # Rules should be injected


def test_build_task_execution_prompt_without_rules(builder_without_rules):
    """Test building task execution prompt without rules."""
    task_data = {
        'task_id': 123,
        'title': 'Test task',
        'description': 'Test description'
    }
    context = {}

    prompt = builder_without_rules.build_task_execution_prompt(
        task_data=task_data,
        context=context
    )

    assert '<METADATA>' in prompt
    assert '"rules": []' in prompt  # Empty rules when no rule engine


def test_build_task_execution_prompt_with_optional_fields(builder_with_rules):
    """Test building task execution prompt with optional fields."""
    task_data = {
        'task_id': 456,
        'title': 'Complex task',
        'description': 'Task with constraints and criteria',
        'constraints': ['No external dependencies', 'Must be backward compatible'],
        'acceptance_criteria': ['All tests pass', 'Code coverage >= 90%']
    }
    context = {'project_id': 1}

    prompt = builder_with_rules.build_task_execution_prompt(
        task_data=task_data,
        context=context
    )

    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '"constraints"' in prompt
    assert 'No external dependencies' in prompt
    assert '"acceptance_criteria"' in prompt
    assert 'Code coverage >= 90%' in prompt


def test_build_task_execution_prompt_missing_required_field(builder_with_rules):
    """Test that missing required fields raise exception."""
    task_data = {'task_id': 123, 'title': 'Missing description'}  # Missing description
    context = {}

    with pytest.raises(StructuredPromptBuilderException, match="Missing required task_data fields"):
        builder_with_rules.build_task_execution_prompt(task_data, context)


# ============================================================================
# Tests: Validation Prompts
# ============================================================================

def test_build_validation_prompt(builder_with_rules):
    """Test building validation prompt."""
    code = """
def example_function():
    pass
"""
    rules = builder_with_rules.rule_engine.get_rules_for_domain('code_generation')

    prompt = builder_with_rules.build_validation_prompt(code=code, rules=rules[:3])

    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '"prompt_type": "validation"' in prompt
    assert 'def example_function' in prompt
    assert '"rules"' in prompt


# ============================================================================
# Tests: Error Analysis Prompts
# ============================================================================

def test_build_error_analysis_prompt(builder_with_rules):
    """Test building error analysis prompt."""
    error_data = {
        'error_type': 'AttributeError',
        'error_message': 'NoneType object has no attribute id',
        'traceback': 'File auth.py, line 15...'
    }

    prompt = builder_with_rules.build_error_analysis_prompt(error_data=error_data)

    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '"prompt_type": "error_analysis"' in prompt
    assert 'AttributeError' in prompt


# ============================================================================
# Tests: Decision Prompts
# ============================================================================

def test_build_decision_prompt(builder_with_rules):
    """Test building decision prompt."""
    decision_context = {
        'task_id': 123,
        'current_state': 'completed',
        'validation_result': {
            'is_valid': False,
            'quality_score': 65
        },
        'quality_score': 0.65
    }

    prompt = builder_with_rules.build_decision_prompt(decision_context=decision_context)

    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '"prompt_type": "decision"' in prompt


# ============================================================================
# Tests: Planning Prompts
# ============================================================================

def test_build_planning_prompt(builder_with_rules):
    """Test building planning prompt."""
    planning_data = {
        'task_id': 145,
        'task_description': 'Build e-commerce checkout',
        'project_context': {'name': 'webapp', 'tech_stack': 'Django'}
    }

    prompt = builder_with_rules.build_planning_prompt(planning_data=planning_data)

    assert '<METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '"prompt_type": "planning"' in prompt


# ============================================================================
# Tests: Rule Injection
# ============================================================================

def test_inject_rules_with_rule_engine(builder_with_rules):
    """Test rule injection from PromptRuleEngine."""
    metadata = {
        'prompt_type': 'task_execution',
        'task_id': 123
    }

    result = builder_with_rules._inject_rules(
        metadata=metadata,
        prompt_type='task_execution',
        domains=['code_generation', 'testing']
    )

    assert 'rules' in result
    assert len(result['rules']) > 0
    # Check rule structure
    for rule in result['rules']:
        assert 'id' in rule
        assert 'name' in rule
        assert 'description' in rule
        assert 'severity' in rule


def test_inject_rules_without_rule_engine(builder_without_rules):
    """Test rule injection when no rule engine available."""
    metadata = {
        'prompt_type': 'task_execution',
        'task_id': 123
    }

    result = builder_without_rules._inject_rules(
        metadata=metadata,
        prompt_type='task_execution',
        domains=['code_generation']
    )

    assert 'rules' in result
    assert result['rules'] == []  # Empty when no rule engine


# ============================================================================
# Tests: Metadata Formatting
# ============================================================================

def test_format_hybrid_prompt():
    """Test hybrid prompt formatting."""
    builder = StructuredPromptBuilder()

    metadata = {
        'prompt_type': 'task_execution',
        'task_id': 123
    }
    instruction = 'Implement the authentication module.'

    prompt = builder._format_hybrid_prompt(metadata, instruction)

    assert '<METADATA>' in prompt
    assert '</METADATA>' in prompt
    assert '<INSTRUCTION>' in prompt
    assert '</INSTRUCTION>' in prompt
    assert '"prompt_type": "task_execution"' in prompt
    assert 'Implement the authentication module' in prompt


# ============================================================================
# Tests: Statistics
# ============================================================================

def test_get_stats(builder_with_rules):
    """Test getting statistics."""
    # Build a few prompts
    task_data = {'task_id': 1, 'title': 'Test', 'description': 'Test desc'}
    builder_with_rules.build_task_execution_prompt(task_data, {})
    builder_with_rules.build_task_execution_prompt(task_data, {})

    stats = builder_with_rules.stats

    assert 'prompts_built' in stats
    assert stats['prompts_built'] >= 2
    assert 'task_execution_count' in stats


def test_reset_stats(builder_with_rules):
    """Test resetting statistics."""
    # Build a prompt
    task_data = {'task_id': 1, 'title': 'Test', 'description': 'Test desc'}
    builder_with_rules.build_task_execution_prompt(task_data, {})

    # Reset stats
    builder_with_rules.reset_stats()

    stats = builder_with_rules.stats
    assert stats['prompts_built'] == 0


# ============================================================================
# Tests: Error Handling
# ============================================================================

def test_builder_exception_on_missing_task_id():
    """Test exception when task_id is missing."""
    builder = StructuredPromptBuilder()

    task_data = {'title': 'No task ID', 'description': 'Missing ID'}  # Missing task_id

    with pytest.raises(StructuredPromptBuilderException, match="Missing required task_data fields"):
        builder.build_task_execution_prompt(task_data, {})


def test_builder_exception_context():
    """Test that StructuredPromptBuilderException includes context."""
    builder = StructuredPromptBuilder()

    try:
        builder.build_task_execution_prompt({'title': 'Bad'}, {})
    except StructuredPromptBuilderException as e:
        assert hasattr(e, 'context')
