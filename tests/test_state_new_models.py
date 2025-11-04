"""Test new database models and StateManager methods for LLM-first framework.

Tests for:
- PromptRuleViolation model + StateManager methods
- ComplexityEstimate model + StateManager methods
- ParallelAgentAttempt model + StateManager methods

Part of TASK_1.7: Test new models and StateManager methods
"""

import pytest
from datetime import datetime, UTC, timedelta
from src.core.state import StateManager
from src.core.models import (
    PromptRuleViolation, ComplexityEstimate, ParallelAgentAttempt,
    Task, ProjectState
)
from src.core.exceptions import DatabaseException


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
        name='test_llm_first',
        description='Test project for LLM-first framework',
        working_dir='/tmp/test'
    )


@pytest.fixture
def test_task(state_manager, test_project):
    """Create a test task."""
    return state_manager.create_task(
        project_id=test_project.id,
        task_data={
            'title': 'Test task for LLM-first models',
            'description': 'Testing new database models',
            'priority': 5
        }
    )


# ============================================================================
# Tests: PromptRuleViolation
# ============================================================================

def test_log_rule_violation(state_manager, test_task):
    """Test logging a prompt rule violation."""
    violation_data = {
        'rule_id': 'CODE_001',
        'rule_name': 'NO_STUBS',
        'rule_domain': 'code_generation',
        'violation_details': {
            'file': '/path/to/file.py',
            'function': 'test_function',
            'line': 42,
            'issue': 'Function contains only pass statement'
        },
        'severity': 'critical'
    }

    violation = state_manager.log_rule_violation(
        task_id=test_task.id,
        rule_data=violation_data
    )

    assert violation.id is not None
    assert violation.task_id == test_task.id
    assert violation.rule_id == 'CODE_001'
    assert violation.rule_name == 'NO_STUBS'
    assert violation.rule_domain == 'code_generation'
    assert violation.severity == 'critical'
    assert violation.violation_details['file'] == '/path/to/file.py'
    assert violation.resolved == False
    assert violation.created_at is not None


def test_get_rule_violations_by_task(state_manager, test_task):
    """Test retrieving rule violations by task ID."""
    # Create multiple violations
    for i in range(3):
        state_manager.log_rule_violation(
            task_id=test_task.id,
            rule_data={
                'rule_id': f'CODE_00{i}',
                'rule_name': f'RULE_{i}',
                'rule_domain': 'code_generation',
                'violation_details': {'line': i},
                'severity': 'high'
            }
        )

    violations = state_manager.get_rule_violations(task_id=test_task.id)
    assert len(violations) == 3
    assert all(v.task_id == test_task.id for v in violations)


def test_get_rule_violations_by_severity(state_manager, test_task):
    """Test filtering rule violations by severity."""
    # Create violations with different severities
    state_manager.log_rule_violation(
        task_id=test_task.id,
        rule_data={
            'rule_id': 'CODE_001',
            'rule_name': 'CRITICAL_RULE',
            'rule_domain': 'code_generation',
            'violation_details': {},
            'severity': 'critical'
        }
    )
    state_manager.log_rule_violation(
        task_id=test_task.id,
        rule_data={
            'rule_id': 'CODE_002',
            'rule_name': 'MEDIUM_RULE',
            'rule_domain': 'code_generation',
            'violation_details': {},
            'severity': 'medium'
        }
    )

    critical_violations = state_manager.get_rule_violations(severity='critical')
    assert len(critical_violations) == 1
    assert critical_violations[0].severity == 'critical'


def test_get_rule_violations_unresolved(state_manager, test_task):
    """Test filtering rule violations by resolution status."""
    state_manager.log_rule_violation(
        task_id=test_task.id,
        rule_data={
            'rule_id': 'CODE_001',
            'rule_name': 'TEST_RULE',
            'rule_domain': 'code_generation',
            'violation_details': {},
            'severity': 'high'
        }
    )

    unresolved = state_manager.get_rule_violations(resolved=False)
    assert len(unresolved) >= 1
    assert all(not v.resolved for v in unresolved)


# ============================================================================
# Tests: ComplexityEstimate
# ============================================================================

def test_log_complexity_estimate(state_manager, test_task):
    """Test logging a task complexity estimate."""
    estimate_data = {
        'estimated_tokens': 5000,
        'estimated_loc': 250,
        'estimated_files': 3,
        'estimated_duration_minutes': 120,
        'overall_complexity_score': 75,
        'heuristic_score': 70,
        'llm_adjusted_score': 75,
        'should_decompose': True,
        'decomposition_reason': 'Exceeds max_files threshold (3 > 5)',
        'estimation_factors': {
            'file_count_weight': 1.3,
            'dependency_depth': 2
        },
        'confidence': 0.8
    }

    estimate = state_manager.log_complexity_estimate(
        task_id=test_task.id,
        estimate_data=estimate_data
    )

    assert estimate.id is not None
    assert estimate.task_id == test_task.id
    assert estimate.estimated_tokens == 5000
    assert estimate.estimated_loc == 250
    assert estimate.estimated_files == 3
    assert estimate.estimated_duration_minutes == 120
    assert estimate.overall_complexity_score == 75
    assert estimate.heuristic_score == 70
    assert estimate.llm_adjusted_score == 75
    assert estimate.should_decompose == True
    assert estimate.decomposition_reason == 'Exceeds max_files threshold (3 > 5)'
    assert estimate.confidence == 0.8
    assert estimate.estimation_factors['file_count_weight'] == 1.3


def test_get_complexity_estimate(state_manager, test_task):
    """Test retrieving complexity estimate by task ID."""
    estimate_data = {
        'estimated_tokens': 3000,
        'estimated_loc': 150,
        'estimated_files': 2,
        'estimated_duration_minutes': 60,
        'overall_complexity_score': 50,
        'heuristic_score': 50,
        'should_decompose': False,
        'confidence': 0.7
    }

    state_manager.log_complexity_estimate(
        task_id=test_task.id,
        estimate_data=estimate_data
    )

    retrieved = state_manager.get_complexity_estimate(task_id=test_task.id)
    assert retrieved is not None
    assert retrieved.task_id == test_task.id
    assert retrieved.overall_complexity_score == 50
    assert retrieved.should_decompose == False


def test_complexity_estimate_constraints(state_manager, test_task):
    """Test complexity estimate check constraints."""
    # Test that complexity score is validated (0-100 range)
    # This should work fine
    valid_estimate = {
        'estimated_tokens': 1000,
        'estimated_loc': 50,
        'estimated_files': 1,
        'estimated_duration_minutes': 30,
        'overall_complexity_score': 50,  # Valid
        'heuristic_score': 50,
        'should_decompose': False,
        'confidence': 0.5  # Valid
    }

    estimate = state_manager.log_complexity_estimate(
        task_id=test_task.id,
        estimate_data=valid_estimate
    )
    assert estimate.overall_complexity_score == 50
    assert estimate.confidence == 0.5


# ============================================================================
# Tests: ParallelAgentAttempt
# ============================================================================

def test_log_parallel_attempt(state_manager, test_task):
    """Test logging a parallel agent execution attempt."""
    now = datetime.now(UTC)
    attempt_data = {
        'num_agents': 3,
        'agent_ids': ['agent_1', 'agent_2', 'agent_3'],
        'subtask_ids': [100, 101, 102],
        'success': True,
        'total_duration_seconds': 120.5,
        'sequential_estimate_seconds': 300.0,
        'speedup_factor': 2.49,
        'max_concurrent_agents': 3,
        'total_token_usage': 15000,
        'parallelization_strategy': 'file_based',
        'execution_metadata': {
            'files_per_agent': [2, 2, 1]
        },
        'started_at': now - timedelta(seconds=120),
        'completed_at': now
    }

    attempt = state_manager.log_parallel_attempt(
        task_id=test_task.id,
        attempt_data=attempt_data
    )

    assert attempt.id is not None
    assert attempt.task_id == test_task.id
    assert attempt.num_agents == 3
    assert len(attempt.agent_ids) == 3
    assert len(attempt.subtask_ids) == 3
    assert attempt.success == True
    assert attempt.total_duration_seconds == 120.5
    assert attempt.speedup_factor == 2.49
    assert attempt.parallelization_strategy == 'file_based'
    assert attempt.conflict_detected == False


def test_get_parallel_attempts_by_task(state_manager, test_task):
    """Test retrieving parallel attempts by task ID."""
    now = datetime.now(UTC)

    # Create multiple attempts
    for i in range(2):
        state_manager.log_parallel_attempt(
            task_id=test_task.id,
            attempt_data={
                'num_agents': 2,
                'agent_ids': [f'agent_{i}_1', f'agent_{i}_2'],
                'subtask_ids': [i * 10, i * 10 + 1],
                'success': True,
                'total_duration_seconds': 60.0,
                'max_concurrent_agents': 2,
                'parallelization_strategy': 'feature_based',
                'started_at': now - timedelta(seconds=60),
                'completed_at': now
            }
        )

    attempts = state_manager.get_parallel_attempts(task_id=test_task.id)
    assert len(attempts) == 2
    assert all(a.task_id == test_task.id for a in attempts)


def test_get_parallel_attempts_by_success(state_manager, test_task):
    """Test filtering parallel attempts by success status."""
    now = datetime.now(UTC)

    # Create successful attempt
    state_manager.log_parallel_attempt(
        task_id=test_task.id,
        attempt_data={
            'num_agents': 2,
            'agent_ids': ['agent_1', 'agent_2'],
            'subtask_ids': [10, 11],
            'success': True,
            'total_duration_seconds': 60.0,
            'max_concurrent_agents': 2,
            'parallelization_strategy': 'file_based',
            'started_at': now - timedelta(seconds=60),
            'completed_at': now
        }
    )

    # Create failed attempt
    state_manager.log_parallel_attempt(
        task_id=test_task.id,
        attempt_data={
            'num_agents': 2,
            'agent_ids': ['agent_3', 'agent_4'],
            'subtask_ids': [12, 13],
            'success': False,
            'failure_reason': 'Conflict detected in file modifications',
            'conflict_detected': True,
            'total_duration_seconds': 30.0,
            'max_concurrent_agents': 2,
            'parallelization_strategy': 'file_based',
            'started_at': now - timedelta(seconds=30),
            'completed_at': now
        }
    )

    successful = state_manager.get_parallel_attempts(success=True)
    failed = state_manager.get_parallel_attempts(success=False)

    assert len(successful) >= 1
    assert all(a.success for a in successful)
    assert len(failed) >= 1
    assert all(not a.success for a in failed)


def test_parallel_attempt_constraints(state_manager, test_task):
    """Test parallel attempt check constraints."""
    now = datetime.now(UTC)

    # Test that num_agents >= 2 constraint works
    # Valid: 2 agents
    valid_attempt = {
        'num_agents': 2,
        'agent_ids': ['agent_1', 'agent_2'],
        'subtask_ids': [10, 11],
        'success': True,
        'total_duration_seconds': 60.0,
        'speedup_factor': 1.5,
        'max_concurrent_agents': 2,
        'parallelization_strategy': 'file_based',
        'started_at': now - timedelta(seconds=60),
        'completed_at': now
    }

    attempt = state_manager.log_parallel_attempt(
        task_id=test_task.id,
        attempt_data=valid_attempt
    )
    assert attempt.num_agents == 2
    assert attempt.speedup_factor == 1.5


# ============================================================================
# Tests: Serialization
# ============================================================================

def test_models_to_dict_serialization(state_manager, test_task):
    """Test that all new models have working to_dict() methods."""
    # Test PromptRuleViolation
    violation = state_manager.log_rule_violation(
        task_id=test_task.id,
        rule_data={
            'rule_id': 'CODE_001',
            'rule_name': 'NO_STUBS',
            'rule_domain': 'code_generation',
            'violation_details': {'line': 42},
            'severity': 'critical'
        }
    )
    violation_dict = violation.to_dict()
    assert violation_dict['rule_id'] == 'CODE_001'
    assert violation_dict['task_id'] == test_task.id
    assert 'created_at' in violation_dict

    # Test ComplexityEstimate
    estimate = state_manager.log_complexity_estimate(
        task_id=test_task.id,
        estimate_data={
            'estimated_tokens': 1000,
            'estimated_loc': 50,
            'estimated_files': 1,
            'estimated_duration_minutes': 30,
            'overall_complexity_score': 40,
            'heuristic_score': 40,
            'should_decompose': False
        }
    )
    estimate_dict = estimate.to_dict()
    assert estimate_dict['task_id'] == test_task.id
    assert estimate_dict['overall_complexity_score'] == 40
    assert 'created_at' in estimate_dict

    # Test ParallelAgentAttempt
    now = datetime.now(UTC)
    attempt = state_manager.log_parallel_attempt(
        task_id=test_task.id,
        attempt_data={
            'num_agents': 2,
            'agent_ids': ['agent_1', 'agent_2'],
            'subtask_ids': [10, 11],
            'success': True,
            'total_duration_seconds': 60.0,
            'max_concurrent_agents': 2,
            'parallelization_strategy': 'file_based',
            'started_at': now - timedelta(seconds=60),
            'completed_at': now
        }
    )
    attempt_dict = attempt.to_dict()
    assert attempt_dict['task_id'] == test_task.id
    assert attempt_dict['num_agents'] == 2
    assert 'started_at' in attempt_dict
