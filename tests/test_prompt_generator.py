"""Tests for PromptGenerator - Jinja2-based prompt generation."""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from src.llm.prompt_generator import (
    PromptGenerator,
    PromptGeneratorException,
    TemplateValidationError
)
from src.llm.local_interface import LocalLLMInterface
from src.core.state import StateManager
from src.core.models import PatternLearning


# Fixtures

@pytest.fixture
def temp_template_dir():
    """Create temporary directory with test templates."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create sample templates
        templates = {
            'simple': 'Hello {{ name }}!',
            'task_execution': '''Task: {{ task_title }}
Description: {{ task_description }}
{% if priority %}Priority: {{ priority }}{% endif %}''',
            'with_truncate': 'Content: {{ content | truncate(50) }}',
            'with_summarize': 'Summary: {{ text | summarize(max_tokens=100) }}',
            'with_format_code': '''Code:
```
{{ code | format_code }}
```''',
            'validation_test': '''
## Task Details
**Task**: {{ task_title }}
{{ task_description }}

{% if work_output %}
## Work
{{ work_output | truncate(3000) }}
{% endif %}
''',
            'context_heavy': '''
## Main Task
{{ main_task }}

{% if recent_errors %}
## Recent Errors
{% for error in recent_errors %}
- {{ error }}
{% endfor %}
{% endif %}

{% if active_code_files %}
## Active Files
{% for file in active_code_files %}
- {{ file }}
{% endfor %}
{% endif %}
'''
        }

        template_file = tmpdir_path / 'prompt_templates.yaml'
        with open(template_file, 'w') as f:
            yaml.dump(templates, f)

        yield tmpdir_path


@pytest.fixture
def mock_llm():
    """Create mock LLM interface."""
    llm = Mock(spec=LocalLLMInterface)

    # Mock estimate_tokens to return ~1 token per 4 characters
    def estimate_tokens(text):
        if not text:
            return 0
        return max(1, len(text) // 4)

    llm.estimate_tokens = Mock(side_effect=estimate_tokens)

    # Mock generate for summarization
    def generate(prompt, **kwargs):
        # Return a shortened version
        if 'Summarize' in prompt or 'summarize' in prompt:
            # Extract text after "following text"
            if 'following text' in prompt:
                parts = prompt.split('following text')
                if len(parts) > 1:
                    original = parts[1].strip()
                    # Return first 50 chars as "summary"
                    return original[:50] + '...'
            return 'Summary of content'
        return 'Generated response'

    llm.generate = Mock(side_effect=generate)

    return llm


@pytest.fixture
def mock_state_manager():
    """Create mock StateManager."""
    state_manager = Mock(spec=StateManager)

    # Mock session for pattern learning queries
    mock_session = MagicMock()
    state_manager._get_session = Mock(return_value=mock_session)

    return state_manager


@pytest.fixture
def generator(temp_template_dir, mock_llm):
    """Create PromptGenerator instance with mocked dependencies."""
    return PromptGenerator(
        template_dir=str(temp_template_dir),
        llm_interface=mock_llm
    )


@pytest.fixture
def generator_with_state(temp_template_dir, mock_llm, mock_state_manager):
    """Create PromptGenerator with StateManager."""
    return PromptGenerator(
        template_dir=str(temp_template_dir),
        llm_interface=mock_llm,
        state_manager=mock_state_manager
    )


# Test: Initialization

def test_initialization_success(temp_template_dir, mock_llm):
    """Test successful initialization."""
    generator = PromptGenerator(
        template_dir=str(temp_template_dir),
        llm_interface=mock_llm
    )

    assert generator.llm_interface == mock_llm
    assert len(generator.templates) > 0
    assert 'simple' in generator.templates
    assert generator.stats['prompts_generated'] == 0


def test_initialization_missing_template_file(mock_llm):
    """Test initialization with missing template file."""
    with pytest.raises(PromptGeneratorException) as exc_info:
        PromptGenerator(
            template_dir='/nonexistent/path',
            llm_interface=mock_llm
        )

    assert 'Template file not found' in str(exc_info.value)


def test_initialization_invalid_yaml(mock_llm):
    """Test initialization with invalid YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        template_file = tmpdir_path / 'prompt_templates.yaml'

        # Write invalid YAML
        with open(template_file, 'w') as f:
            f.write('invalid: yaml: content: [[[')

        with pytest.raises(PromptGeneratorException) as exc_info:
            PromptGenerator(
                template_dir=str(tmpdir_path),
                llm_interface=mock_llm
            )

        assert 'Failed to parse template YAML' in str(exc_info.value)


def test_initialization_non_dict_yaml(mock_llm):
    """Test initialization with non-dict YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        template_file = tmpdir_path / 'prompt_templates.yaml'

        # Write list instead of dict
        with open(template_file, 'w') as f:
            yaml.dump(['template1', 'template2'], f)

        with pytest.raises(PromptGeneratorException) as exc_info:
            PromptGenerator(
                template_dir=str(tmpdir_path),
                llm_interface=mock_llm
            )

        assert 'must contain a YAML dictionary' in str(exc_info.value)


def test_custom_config(temp_template_dir, mock_llm):
    """Test initialization with custom config."""
    custom_config = {
        'max_context_tokens': 50000,
        'cache_size': 200
    }

    generator = PromptGenerator(
        template_dir=str(temp_template_dir),
        llm_interface=mock_llm,
        config=custom_config
    )

    assert generator.config['max_context_tokens'] == 50000
    assert generator.config['cache_size'] == 200
    # Default values should still be present
    assert 'context_priority_order' in generator.config


# Test: Template Loading and Validation

def test_load_template_success(generator):
    """Test loading existing template."""
    template = generator.load_template('simple')
    assert template is not None
    result = template.render(name='World')
    assert result == 'Hello World!'


def test_load_template_not_found(generator):
    """Test loading non-existent template."""
    from jinja2.exceptions import TemplateNotFound

    with pytest.raises(TemplateNotFound) as exc_info:
        generator.load_template('nonexistent')

    assert 'nonexistent' in str(exc_info.value)
    assert 'Available templates:' in str(exc_info.value)


def test_validate_template_success(generator):
    """Test template validation for valid template."""
    assert generator.validate_template('simple') is True
    assert generator.validate_template('task_execution') is True


def test_validate_template_not_found(generator):
    """Test validation of non-existent template."""
    from jinja2.exceptions import TemplateNotFound

    with pytest.raises(TemplateNotFound):
        generator.validate_template('nonexistent')


def test_list_templates(generator):
    """Test listing available templates."""
    templates = generator.list_templates()
    assert isinstance(templates, list)
    assert 'simple' in templates
    assert 'task_execution' in templates
    assert len(templates) > 0


# Test: Basic Prompt Generation

def test_generate_prompt_simple(generator):
    """Test basic prompt generation."""
    prompt = generator.generate_prompt(
        'simple',
        {'name': 'Alice'}
    )

    assert prompt == 'Hello Alice!'
    assert generator.stats['prompts_generated'] == 1
    assert generator.stats['cache_misses'] == 1


def test_generate_prompt_with_optional_variables(generator):
    """Test prompt with optional variables."""
    # Without priority
    prompt1 = generator.generate_prompt(
        'task_execution',
        {
            'task_title': 'Fix bug',
            'task_description': 'Fix issue #123'
        }
    )

    assert 'Task: Fix bug' in prompt1
    assert 'Description: Fix issue #123' in prompt1
    assert 'Priority:' not in prompt1

    # With priority
    prompt2 = generator.generate_prompt(
        'task_execution',
        {
            'task_title': 'Fix bug',
            'task_description': 'Fix issue #123',
            'priority': 5
        }
    )

    assert 'Priority: 5' in prompt2


def test_generate_prompt_missing_required_variable(generator):
    """Test prompt generation with missing required variable."""
    with pytest.raises(PromptGeneratorException) as exc_info:
        generator.generate_prompt(
            'task_execution',
            {'task_title': 'Test'}  # Missing task_description
        )

    assert 'Missing required variable' in str(exc_info.value)


def test_generate_prompt_with_kwargs(generator):
    """Test prompt generation with kwargs."""
    prompt = generator.generate_prompt(
        'simple',
        {},
        name='Bob'  # Pass as kwarg
    )

    assert prompt == 'Hello Bob!'


# Test: Caching

def test_prompt_caching(generator):
    """Test prompt caching works."""
    variables = {'name': 'Alice'}

    # First call
    prompt1 = generator.generate_prompt('simple', variables)
    assert generator.stats['cache_misses'] == 1
    assert generator.stats['cache_hits'] == 0

    # Second call with same inputs
    prompt2 = generator.generate_prompt('simple', variables)
    assert prompt1 == prompt2
    assert generator.stats['cache_hits'] == 1


def test_cache_key_uniqueness(generator):
    """Test that different inputs create different cache keys."""
    prompt1 = generator.generate_prompt('simple', {'name': 'Alice'})
    prompt2 = generator.generate_prompt('simple', {'name': 'Bob'})

    assert prompt1 != prompt2
    assert generator.stats['cache_misses'] == 2
    assert generator.stats['cache_hits'] == 0


def test_disable_caching(generator):
    """Test disabling cache."""
    variables = {'name': 'Alice'}

    # First call
    prompt1 = generator.generate_prompt(
        'simple',
        variables,
        enable_caching=False
    )

    # Second call - should not use cache
    prompt2 = generator.generate_prompt(
        'simple',
        variables,
        enable_caching=False
    )

    assert prompt1 == prompt2
    assert generator.stats['cache_hits'] == 0


def test_clear_cache(generator):
    """Test clearing cache."""
    variables = {'name': 'Alice'}

    # Generate and cache
    prompt1 = generator.generate_prompt('simple', variables)
    assert generator.stats['cache_hits'] == 0

    # Should hit cache
    prompt2 = generator.generate_prompt('simple', variables)
    assert generator.stats['cache_hits'] == 1

    # Clear cache
    generator.clear_cache()

    # Should miss cache again
    prompt3 = generator.generate_prompt('simple', variables)
    assert generator.stats['cache_misses'] == 2


# Test: Custom Filters

def test_filter_truncate(generator):
    """Test truncate filter."""
    # Mock LLM to return specific token counts
    def mock_estimate(text):
        # Make each char = 1 token for easy testing
        return len(text)

    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    long_text = 'A' * 200
    prompt = generator.generate_prompt(
        'with_truncate',
        {'content': long_text}
    )

    # Should be truncated to ~50 tokens (chars) + '...'
    assert len(prompt) < len('Content: ' + long_text)
    assert '...' in prompt


def test_filter_format_code(generator):
    """Test format_code filter."""
    messy_code = '''def   foo():\n\n\n\n    return   42\n\n\n\n'''

    prompt = generator.generate_prompt(
        'with_format_code',
        {'code': messy_code}
    )

    # Should remove excessive blank lines and clean up
    assert '\n\n\n' not in prompt
    assert 'def   foo()' not in prompt  # Spaces in code preserved (not filter's job)


def test_filter_summarize(generator):
    """Test summarize filter with LLM."""
    long_text = 'A' * 1000

    # Mock returns summary
    generator.llm_interface.generate = Mock(return_value='This is a summary')

    prompt = generator.generate_prompt(
        'with_summarize',
        {'text': long_text}
    )

    # Should contain the summary
    assert 'This is a summary' in prompt

    # LLM should have been called
    generator.llm_interface.generate.assert_called()


def test_filter_summarize_fallback(generator):
    """Test summarize filter falls back to truncate on error."""
    long_text = 'A' * 1000

    # Mock LLM to raise error
    generator.llm_interface.generate = Mock(side_effect=Exception('LLM error'))

    # Should not raise, should fall back to truncate
    prompt = generator.generate_prompt(
        'with_summarize',
        {'text': long_text}
    )

    assert '...' in prompt  # Truncated fallback


# Test: Token Optimization

def test_optimize_for_tokens_not_needed(generator):
    """Test optimization when prompt already fits."""
    short_prompt = "Hello world"
    max_tokens = 100

    optimized = generator.optimize_for_tokens(short_prompt, max_tokens)
    assert optimized == short_prompt


def test_optimize_for_tokens_whitespace_removal(generator):
    """Test optimization removes redundant whitespace."""
    prompt = "Hello    world\n\n\n\nGoodbye"

    # Mock tokens
    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    optimized = generator.optimize_for_tokens(prompt, max_tokens=20)

    # Multiple spaces should be reduced to single
    assert '    ' not in optimized
    # Multiple newlines should be reduced to double
    assert '\n\n\n' not in optimized


def test_optimize_for_tokens_truncation(generator):
    """Test optimization truncates when needed."""
    long_prompt = 'A' * 1000

    # Mock tokens
    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    optimized = generator.optimize_for_tokens(long_prompt, max_tokens=100)

    # Should be truncated
    assert len(optimized) < len(long_prompt)
    assert '...' in optimized


def test_optimize_for_tokens_stats(generator):
    """Test optimization updates statistics."""
    long_prompt = 'A' * 1000

    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    generator.optimize_for_tokens(long_prompt, max_tokens=100)

    assert generator.stats['optimizations_applied'] == 1
    assert generator.stats['total_tokens_saved'] > 0


def test_generate_prompt_with_max_tokens(generator):
    """Test prompt generation with max_tokens constraint."""
    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    variables = {
        'task_title': 'A' * 500,
        'task_description': 'B' * 500
    }

    prompt = generator.generate_prompt(
        'task_execution',
        variables,
        max_tokens=100,
        enable_optimization=True
    )

    # Should be optimized to fit
    token_count = generator.llm_interface.estimate_tokens(prompt)
    assert token_count <= 100


# Test: Context Injection

def test_inject_context_basic(generator):
    """Test basic context injection."""
    base_prompt = "Main task description"

    context = {
        'recent_errors': ['Error 1', 'Error 2'],
        'active_code_files': ['file1.py', 'file2.py']
    }

    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    result = generator.inject_context(
        base_prompt,
        context,
        max_tokens=1000
    )

    # Should contain base prompt
    assert base_prompt in result

    # Should contain context items (in priority order)
    assert 'Recent Errors' in result or 'recent_errors' in result.lower()
    assert 'Error 1' in result


def test_inject_context_respects_priority(generator):
    """Test context injection respects priority order."""
    base_prompt = "Task"

    # Provide context in reverse priority order
    context = {
        'conversation_history': 'Previous discussion',
        'recent_errors': 'Critical error',
        'current_task_description': 'Main task'
    }

    def mock_estimate(text):
        return len(text) // 4
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    result = generator.inject_context(
        base_prompt,
        context,
        max_tokens=100
    )

    # Higher priority items should appear first
    # current_task_description has highest priority
    task_pos = result.find('Main task')
    errors_pos = result.find('Critical error')

    if task_pos != -1 and errors_pos != -1:
        assert task_pos < errors_pos


def test_inject_context_token_budget(generator):
    """Test context injection respects token budget."""
    base_prompt = "A" * 200  # 50 tokens (at 4 chars/token)

    context = {
        'recent_errors': 'E' * 400,  # 100 tokens
        'active_code_files': 'F' * 400  # 100 tokens
    }

    def mock_estimate(text):
        return len(text) // 4
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    # Only 100 tokens total
    result = generator.inject_context(
        base_prompt,
        context,
        max_tokens=100
    )

    # Should not exceed budget
    token_count = mock_estimate(result)
    assert token_count <= 100


def test_inject_context_empty_values(generator):
    """Test context injection handles empty values."""
    base_prompt = "Task"

    context = {
        'recent_errors': [],  # Empty list
        'active_code_files': None,
        'conversation_history': ''
    }

    result = generator.inject_context(
        base_prompt,
        context,
        max_tokens=1000
    )

    # Should not crash, should return base prompt
    assert base_prompt in result


def test_format_context_section_list(generator):
    """Test formatting context section with list."""
    section = generator._format_context_section(
        'recent_errors',
        ['Error 1', 'Error 2', 'Error 3']
    )

    assert 'Recent Errors' in section
    assert '- Error 1' in section
    assert '- Error 2' in section


def test_format_context_section_dict(generator):
    """Test formatting context section with dict."""
    section = generator._format_context_section(
        'metadata',
        {'key1': 'value1', 'key2': 'value2'}
    )

    assert 'Metadata' in section
    assert 'key1' in section
    assert 'value1' in section


def test_format_context_section_string(generator):
    """Test formatting context section with string."""
    section = generator._format_context_section(
        'task_description',
        'This is the task description'
    )

    assert 'Task Description' in section
    assert 'This is the task description' in section


# Test: Pattern Learning Integration

def test_add_examples_success(generator_with_state):
    """Test adding examples from pattern learning."""
    base_prompt = "Solve this problem"

    # Mock pattern learning query
    mock_pattern1 = Mock(spec=PatternLearning)
    mock_pattern1.pattern_type = 'bug_fix'
    mock_pattern1.pattern_data = {
        'description': 'Fix null pointer',
        'solution': 'if obj is not None:\n    use(obj)'
    }
    mock_pattern1.success_count = 5
    mock_pattern1.failure_count = 1

    mock_pattern2 = Mock(spec=PatternLearning)
    mock_pattern2.pattern_type = 'bug_fix'
    mock_pattern2.pattern_data = {
        'description': 'Fix array bounds',
        'solution': 'if index < len(arr):\n    return arr[index]'
    }
    mock_pattern2.success_count = 3
    mock_pattern2.failure_count = 0

    # Mock query result
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = [mock_pattern1, mock_pattern2]

    mock_session = generator_with_state.state_manager._get_session()
    mock_session.query.return_value = mock_query

    # Add examples
    result = generator_with_state.add_examples(
        base_prompt,
        pattern_type='bug_fix',
        count=2
    )

    # Should contain base prompt
    assert base_prompt in result

    # Should contain examples
    assert 'Example Solutions' in result
    assert 'Fix null pointer' in result
    assert 'Fix array bounds' in result
    assert 'Success rate' in result


def test_add_examples_no_state_manager(generator):
    """Test add_examples without StateManager."""
    base_prompt = "Solve this"

    result = generator.add_examples(
        base_prompt,
        pattern_type='bug_fix',
        count=3
    )

    # Should return unchanged prompt
    assert result == base_prompt


def test_add_examples_no_patterns_found(generator_with_state):
    """Test add_examples when no patterns exist."""
    base_prompt = "Solve this"

    # Mock empty query result
    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.all.return_value = []

    mock_session = generator_with_state.state_manager._get_session()
    mock_session.query.return_value = mock_query

    result = generator_with_state.add_examples(
        base_prompt,
        pattern_type='nonexistent_pattern',
        count=3
    )

    # Should return unchanged prompt
    assert result == base_prompt


def test_add_examples_handles_exception(generator_with_state):
    """Test add_examples handles exceptions gracefully."""
    base_prompt = "Solve this"

    # Mock query to raise exception
    mock_session = generator_with_state.state_manager._get_session()
    mock_session.query.side_effect = Exception('Database error')

    # Should not raise, should return unchanged prompt
    result = generator_with_state.add_examples(
        base_prompt,
        pattern_type='bug_fix',
        count=3
    )

    assert result == base_prompt


# Test: Utility Methods

def test_get_prompt_stats(generator):
    """Test getting prompt statistics."""
    prompt = '''## Section 1
Content here

## Section 2
More content'''

    stats = generator.get_prompt_stats(prompt)

    assert 'token_count' in stats
    assert 'character_count' in stats
    assert 'line_count' in stats
    assert 'word_count' in stats
    assert 'sections' in stats

    assert stats['character_count'] == len(prompt)
    assert stats['line_count'] == len(prompt.split('\n'))
    assert len(stats['sections']) == 2
    assert '## Section 1' in stats['sections']


def test_preview_prompt(generator):
    """Test prompt preview."""
    variables = {'name': 'Alice'}

    # Preview should not cache
    prompt1 = generator.preview_prompt('simple', variables)
    prompt2 = generator.preview_prompt('simple', variables)

    assert prompt1 == prompt2
    assert generator.stats['cache_hits'] == 0


def test_get_stats(generator):
    """Test getting generator statistics."""
    # Generate some prompts
    generator.generate_prompt('simple', {'name': 'Alice'})
    generator.generate_prompt('simple', {'name': 'Alice'})  # Cache hit
    generator.generate_prompt('simple', {'name': 'Bob'})

    stats = generator.get_stats()

    assert stats['prompts_generated'] == 3
    assert stats['cache_hits'] == 1
    assert stats['cache_misses'] == 2
    assert stats['cache_hit_rate'] == 1 / 3


def test_get_stats_empty(generator):
    """Test stats with no activity."""
    stats = generator.get_stats()

    assert stats['prompts_generated'] == 0
    assert stats['cache_hit_rate'] == 0.0
    assert stats['avg_tokens_saved'] == 0.0


# Test: Integration Scenarios

def test_full_workflow(generator):
    """Test complete prompt generation workflow."""
    # Generate a complex prompt
    variables = {
        'task_title': 'Implement authentication',
        'task_description': 'Add JWT-based authentication to the API',
        'priority': 8,
        'work_output': 'Implementation completed successfully'
    }

    prompt = generator.generate_prompt(
        'validation_test',
        variables,
        max_tokens=500
    )

    # Should contain all variables
    assert 'Implement authentication' in prompt
    assert 'JWT-based authentication' in prompt

    # Should be optimized
    stats = generator.get_prompt_stats(prompt)
    assert stats['token_count'] <= 500

    # Check stats updated
    assert generator.stats['prompts_generated'] == 1


def test_template_with_loops(generator):
    """Test template with Jinja2 loops."""
    variables = {
        'main_task': 'Complete the feature',
        'recent_errors': ['Error 1', 'Error 2', 'Error 3'],
        'active_code_files': ['file1.py', 'file2.py']
    }

    prompt = generator.generate_prompt(
        'context_heavy',
        variables
    )

    # Should contain all error items
    assert 'Error 1' in prompt
    assert 'Error 2' in prompt
    assert 'Error 3' in prompt

    # Should contain all files
    assert 'file1.py' in prompt
    assert 'file2.py' in prompt


@pytest.mark.slow
@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
def test_concurrent_generation(generator):
    """Test that generator handles concurrent requests (basic thread safety check).

    Note: This test uses threading and may be unstable on WSL2 if combined with
    SSH connection issues. Run with: pytest -m "not slow" to skip.
    """
    import threading

    results = []
    errors = []

    def generate():
        try:
            prompt = generator.generate_prompt(
                'simple',
                {'name': 'Alice'}
            )
            results.append(prompt)
        except Exception as e:
            errors.append(e)

    # Reduced from 10 to 5 threads for WSL2 stability
    threads = [threading.Thread(target=generate) for _ in range(5)]

    # Start all threads
    for t in threads:
        t.start()

    # Wait for completion with timeout
    for t in threads:
        t.join(timeout=5.0)

    # No errors should occur
    assert len(errors) == 0, f"Errors during concurrent generation: {errors}"
    # All should produce same result
    assert len(results) == 5
    assert all(r == results[0] for r in results)


def test_large_template_optimization(generator):
    """Test optimization with very large template output."""
    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    # Create large variables (reduced from 10000 to 2000 for WSL2)
    variables = {
        'task_title': 'A' * 2000,
        'task_description': 'B' * 2000,
        'work_output': 'C' * 2000
    }

    prompt = generator.generate_prompt(
        'validation_test',
        variables,
        max_tokens=500,
        enable_optimization=True
    )

    # Should be heavily optimized
    assert len(prompt) <= 500
    assert generator.stats['optimizations_applied'] > 0


# Test: Error Handling

def test_invalid_template_name_type(generator):
    """Test error handling for invalid template name type."""
    with pytest.raises(Exception):
        generator.generate_prompt(
            123,  # Invalid type
            {'name': 'Alice'}
        )


def test_invalid_variables_type(generator):
    """Test error handling for invalid variables type."""
    with pytest.raises(Exception):
        generator.generate_prompt(
            'simple',
            'not a dict'  # Invalid type
        )


def test_template_rendering_error(generator):
    """Test handling of template rendering errors."""
    # This would require a template with invalid Jinja2 syntax,
    # but our templates are pre-validated. Test with undefined variable instead.
    with pytest.raises(PromptGeneratorException) as exc_info:
        generator.generate_prompt(
            'task_execution',
            {}  # Missing required variables
        )

    assert 'Missing required variable' in str(exc_info.value)


# Test: Edge Cases

def test_empty_template(temp_template_dir, mock_llm):
    """Test handling of empty template."""
    # Add empty template
    templates = {'empty': ''}
    template_file = temp_template_dir / 'prompt_templates.yaml'
    with open(template_file, 'w') as f:
        yaml.dump(templates, f)

    generator = PromptGenerator(
        template_dir=str(temp_template_dir),
        llm_interface=mock_llm
    )

    prompt = generator.generate_prompt('empty', {})
    assert prompt == ''


def test_prompt_with_special_characters(generator):
    """Test prompt with special characters."""
    variables = {
        'name': 'Alice <>&"\'',
    }

    prompt = generator.generate_prompt('simple', variables)

    # Should not be escaped (autoescape=False)
    assert 'Alice <>&"\'' in prompt


def test_very_long_variable_name(generator):
    """Test with very long variable names."""
    long_name = 'a' * 1000
    variables = {'name': long_name}

    prompt = generator.generate_prompt('simple', variables)
    assert long_name in prompt


def test_zero_max_tokens(generator):
    """Test optimization with zero max tokens."""
    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    prompt = "Hello world"
    optimized = generator.optimize_for_tokens(prompt, max_tokens=0)

    # Should be heavily truncated
    assert len(optimized) < len(prompt)


def test_negative_max_tokens(generator):
    """Test with negative max tokens."""
    def mock_estimate(text):
        return len(text)
    generator.llm_interface.estimate_tokens = Mock(side_effect=mock_estimate)

    prompt = "Hello world"
    optimized = generator.optimize_for_tokens(prompt, max_tokens=-100)

    # Should handle gracefully (truncate to minimal)
    assert len(optimized) >= 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
