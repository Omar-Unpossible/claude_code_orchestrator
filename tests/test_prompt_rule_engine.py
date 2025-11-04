"""Test PromptRuleEngine, PromptRule, and RuleValidationResult.

Tests for:
- PromptRule data class
- RuleValidationResult data class
- PromptRuleEngine loading, filtering, application, and validation

Part of TASK_2.5: Test PromptRuleEngine and validators
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from src.llm.prompt_rule import PromptRule
from src.llm.rule_validation_result import RuleValidationResult
from src.llm.prompt_rule_engine import PromptRuleEngine
from src.core.state import StateManager


# ============================================================================
# Fixtures
# ============================================================================

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
        name='test_rule_engine',
        description='Test project for rule engine',
        working_dir='/tmp/test'
    )


@pytest.fixture
def test_task(state_manager, test_project):
    """Create a test task."""
    return state_manager.create_task(
        project_id=test_project.id,
        task_data={
            'title': 'Test task for rule engine',
            'description': 'Testing prompt rules',
            'priority': 5
        }
    )


@pytest.fixture
def sample_rule_dict() -> Dict[str, Any]:
    """Sample rule dictionary for testing."""
    return {
        'id': 'TEST_001',
        'name': 'Test Rule',
        'description': 'A test rule for validation',
        'validation_type': 'ast_check',
        'severity': 'high',
        'domain': 'testing',
        'examples': {
            'positive': 'good code',
            'negative': 'bad code'
        }
    }


# ============================================================================
# Tests: PromptRule
# ============================================================================

def test_prompt_rule_initialization(sample_rule_dict):
    """Test PromptRule can be initialized with required fields."""
    rule = PromptRule(
        id=sample_rule_dict['id'],
        name=sample_rule_dict['name'],
        description=sample_rule_dict['description'],
        validation_type=sample_rule_dict['validation_type'],
        severity=sample_rule_dict['severity'],
        domain=sample_rule_dict['domain']
    )

    assert rule.id == 'TEST_001'
    assert rule.name == 'Test Rule'
    assert rule.description == 'A test rule for validation'
    assert rule.validation_type == 'ast_check'
    assert rule.severity == 'high'
    assert rule.domain == 'testing'


def test_prompt_rule_validation(sample_rule_dict):
    """Test PromptRule.validate() checks required fields."""
    # Valid rule
    rule = PromptRule.from_dict(sample_rule_dict)
    assert rule.validate() is True

    # Invalid rule - missing id (from_dict raises ValueError for required fields)
    invalid_dict = sample_rule_dict.copy()
    del invalid_dict['id']
    with pytest.raises(ValueError, match="Missing required field"):
        PromptRule.from_dict(invalid_dict)

    # Invalid rule - invalid severity (from_dict validates severity)
    invalid_dict = sample_rule_dict.copy()
    invalid_dict['severity'] = 'invalid_severity'
    with pytest.raises(ValueError, match="Invalid severity"):
        PromptRule.from_dict(invalid_dict)


def test_prompt_rule_from_dict(sample_rule_dict):
    """Test PromptRule.from_dict() deserializes correctly."""
    rule = PromptRule.from_dict(sample_rule_dict)

    assert rule.id == 'TEST_001'
    assert rule.name == 'Test Rule'
    assert rule.domain == 'testing'
    assert rule.examples['positive'] == 'good code'


def test_prompt_rule_to_dict(sample_rule_dict):
    """Test PromptRule.to_dict() serializes correctly."""
    rule = PromptRule.from_dict(sample_rule_dict)
    serialized = rule.to_dict()

    assert serialized['id'] == 'TEST_001'
    assert serialized['name'] == 'Test Rule'
    assert serialized['domain'] == 'testing'
    assert serialized['examples']['positive'] == 'good code'


# ============================================================================
# Tests: RuleValidationResult
# ============================================================================

def test_rule_validation_result_initialization():
    """Test RuleValidationResult initializes correctly."""
    result = RuleValidationResult()

    assert result.is_valid is True
    assert len(result.violations) == 0
    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    assert len(result.checked_rules) == 0


def test_rule_validation_result_add_violation():
    """Test adding violations marks result as invalid."""
    result = RuleValidationResult()

    result.add_violation(
        rule_id='TEST_001',
        details={'message': 'Test violation', 'line': 42}
    )

    assert result.is_valid is False
    assert len(result.violations) == 1
    assert result.violations[0]['rule_id'] == 'TEST_001'
    assert result.violations[0]['message'] == 'Test violation'


def test_rule_validation_result_summary():
    """Test get_summary() returns formatted summary."""
    result = RuleValidationResult()

    result.add_violation('CODE_001', {'message': 'Stub function detected'})
    result.add_error('Parse error in file.py')
    result.add_warning('Deprecated method used')

    summary = result.get_summary()

    assert 'FAILED' in summary or 'Valid: False' in summary or 'Invalid' in summary
    assert '1' in summary  # 1 violation
    assert 'violation' in summary.lower()
    assert 'error' in summary.lower()
    assert 'warning' in summary.lower()


# ============================================================================
# Tests: PromptRuleEngine
# ============================================================================

def test_prompt_rule_engine_initialization():
    """Test PromptRuleEngine initializes correctly."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')

    assert engine.rules_file_path == Path('config/prompt_rules.yaml')
    assert engine._rules_loaded is False


def test_load_rules_from_yaml():
    """Test loading rules from YAML configuration."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')

    count = engine.load_rules_from_yaml()

    assert count > 0  # Should load at least some rules
    assert engine._rules_loaded is True
    assert len(engine._rules) == count
    assert len(engine._rules_by_domain) > 0


def test_get_rules_for_domain():
    """Test retrieving rules by domain."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    # Get code_generation rules
    code_rules = engine.get_rules_for_domain('code_generation')
    assert len(code_rules) > 0
    assert all(rule.domain == 'code_generation' for rule in code_rules)

    # Test severity filter
    critical_rules = engine.get_rules_for_domain(
        'code_generation',
        severity_filter=['critical']
    )
    assert all(rule.severity == 'critical' for rule in critical_rules)


def test_get_rule_by_id():
    """Test retrieving specific rule by ID."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    # Get all rules to find a valid ID
    all_rules = engine.get_all_rules()
    assert len(all_rules) > 0

    # Get first rule by ID
    first_rule_id = all_rules[0].id
    rule = engine.get_rule_by_id(first_rule_id)

    assert rule is not None
    assert rule.id == first_rule_id


def test_apply_rules_to_prompt():
    """Test applying rules to a prompt."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    prompt = {
        'instruction': 'Implement user authentication',
        'context': {'project': 'webapp'}
    }

    # Apply rules for task_execution prompt type
    prompt_with_rules = engine.apply_rules_to_prompt(
        prompt,
        prompt_type='task_execution',
        domains=['code_generation', 'security']
    )

    assert 'rules' in prompt_with_rules
    assert len(prompt_with_rules['rules']) > 0
    assert 'instruction' in prompt_with_rules

    # Check rule structure
    for rule in prompt_with_rules['rules']:
        assert 'id' in rule
        assert 'name' in rule
        assert 'description' in rule
        assert 'severity' in rule


def test_validate_response_against_rules():
    """Test validating response against rules."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    rules = engine.get_rules_for_domain('code_generation')
    response = {
        'status': 'completed',
        'code': 'def example(): pass',
        'files_modified': ['/path/to/file.py']
    }

    result = engine.validate_response_against_rules(
        response=response,
        applicable_rules=rules,
        context={'task_id': 123}
    )

    assert isinstance(result, RuleValidationResult)
    assert len(result.checked_rules) > 0


def test_rule_violation_logging_to_state_manager(state_manager, test_task):
    """Test that violations are logged to StateManager."""
    engine = PromptRuleEngine(
        rules_file_path='config/prompt_rules.yaml',
        state_manager=state_manager
    )
    engine.load_rules_from_yaml()

    # Create a violation manually
    state_manager.log_rule_violation(
        task_id=test_task.id,
        rule_data={
            'rule_id': 'CODE_001',
            'rule_name': 'NO_STUBS',
            'rule_domain': 'code_generation',
            'violation_details': {'message': 'Stub detected'},
            'severity': 'critical'
        }
    )

    # Verify violation was logged
    violations = state_manager.get_rule_violations(task_id=test_task.id)
    assert len(violations) == 1
    assert violations[0].rule_id == 'CODE_001'


def test_get_statistics():
    """Test getting rule statistics."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    stats = engine.get_statistics()

    assert 'total_rules' in stats
    assert stats['total_rules'] > 0
    assert 'domains' in stats
    assert len(stats['domains']) > 0
    assert 'severity_breakdown' in stats
    assert 'rules_loaded' in stats
    assert stats['rules_loaded'] is True


def test_reload_rules():
    """Test reloading rules from YAML."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')

    # Initial load
    count1 = engine.load_rules_from_yaml()

    # Reload
    count2 = engine.reload_rules()

    assert count1 == count2
    assert engine._rules_loaded is True


def test_load_rules_missing_file():
    """Test loading rules from nonexistent file."""
    engine = PromptRuleEngine(rules_file_path='nonexistent.yaml')

    with pytest.raises(FileNotFoundError):
        engine.load_rules_from_yaml()


def test_get_all_rules():
    """Test getting all loaded rules."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    all_rules = engine.get_all_rules()

    assert len(all_rules) > 0
    assert all(isinstance(rule, PromptRule) for rule in all_rules)


def test_apply_rules_without_domains():
    """Test applying rules with default domains for prompt type."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    prompt = {'instruction': 'Test task'}

    # Apply rules without specifying domains (uses defaults)
    prompt_with_rules = engine.apply_rules_to_prompt(
        prompt,
        prompt_type='task_execution'
    )

    assert 'rules' in prompt_with_rules
    # Should use default domains for task_execution


def test_apply_rules_before_loading():
    """Test applying rules before loading them."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')

    prompt = {'instruction': 'Test task'}

    # Apply rules before loading (should return prompt unchanged)
    prompt_with_rules = engine.apply_rules_to_prompt(
        prompt,
        prompt_type='task_execution'
    )

    # Should return prompt unchanged with warning
    assert prompt_with_rules == prompt


def test_engine_repr():
    """Test string representation of engine."""
    engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
    engine.load_rules_from_yaml()

    repr_str = repr(engine)

    assert 'PromptRuleEngine' in repr_str
    assert 'rules_loaded=True' in repr_str
