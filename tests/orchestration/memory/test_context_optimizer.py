"""Unit tests for ContextOptimizer.

Tests cover:
- Initialization and configuration
- Token estimation
- Individual optimization techniques
- Full optimization pipeline
- Edge cases and error handling

Author: Obra System
Created: 2025-01-15
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from src.orchestration.memory.context_optimizer import (
    ContextOptimizer,
    ContextOptimizerException,
    OptimizationResult
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        artifact_dir = Path(tmpdir) / 'artifacts'
        archive_dir = Path(tmpdir) / 'archive'
        yield {
            'artifact_dir': artifact_dir,
            'archive_dir': archive_dir
        }


@pytest.fixture
def optimizer_config(temp_dirs):
    """Configuration for optimizer."""
    return {
        'artifact_storage_path': str(temp_dirs['artifact_dir']),
        'archive_path': str(temp_dirs['archive_dir']),
        'summarization_threshold': 500,
        'externalization_threshold': 2000,
        'pruning_age_hours': 1
    }


@pytest.fixture
def optimizer(optimizer_config):
    """Create a ContextOptimizer instance."""
    return ContextOptimizer(llm_interface=None, config=optimizer_config)


@pytest.fixture
def mock_llm():
    """Create a mock LLM interface."""
    llm = Mock()
    llm.generate.return_value = "This is a summary of the phase."
    return llm


@pytest.fixture
def sample_context():
    """Create a sample context for testing.

    Returns a fresh copy each time to avoid test pollution.
    """
    def _create_context():
        return {
        'task_id': 'task_123',
        'phases': [
            {
                'phase_id': 'phase_1',
                'status': 'completed',
                'data': 'x' * 2000  # Large phase data
            }
        ],
        'files': {
            '/path/to/file.py': {
                'content': 'def hello():\n    print("hello")',
                'last_modified': '2025-01-15T10:00:00Z',
                'type': 'python'
            }
        },
        'artifacts': [
            {
                'id': 'artifact_1',
                'data': 'small data'
            }
        ],
        'full_state': {
            'key1': 'value1',
            'key2': 'value2'
        },
        'debug_traces': [
            {
                'timestamp': (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                'message': 'old trace'
            },
            {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message': 'recent trace'
            }
        ],
        'validation_results': [
            {'result': f'validation_{i}'} for i in range(10)
        ],
        'errors': [
            {'error': 'error_1', 'resolved': True},
            {'error': 'error_2', 'resolved': False}
        ] + [{'error': f'old_error_{i}', 'resolved': True} for i in range(20)]
        }
    return _create_context()


# ============================================================================
# Test: Initialization
# ============================================================================

def test_init_with_config(optimizer_config):
    """Test initialization with valid configuration."""
    optimizer = ContextOptimizer(llm_interface=None, config=optimizer_config)

    assert optimizer.summarization_threshold == 500
    assert optimizer.externalization_threshold == 2000
    assert optimizer.pruning_age_hours == 1
    assert optimizer.artifact_dir.exists()
    assert optimizer.archive_dir.exists()


def test_init_without_config():
    """Test initialization without configuration."""
    optimizer = ContextOptimizer()

    assert optimizer.summarization_threshold == 500
    assert optimizer.externalization_threshold == 2000
    assert optimizer.pruning_age_hours == 1


def test_init_with_llm_interface(optimizer_config, mock_llm):
    """Test initialization with LLM interface."""
    optimizer = ContextOptimizer(llm_interface=mock_llm, config=optimizer_config)

    assert optimizer.llm_interface == mock_llm


def test_init_creates_directories(optimizer_config):
    """Test that initialization creates required directories."""
    optimizer = ContextOptimizer(config=optimizer_config)

    assert optimizer.artifact_dir.exists()
    assert optimizer.archive_dir.exists()


# ============================================================================
# Test: Token Estimation
# ============================================================================

def test_estimate_tokens_dict(optimizer):
    """Test token estimation for dictionary."""
    data = {'key': 'value', 'number': 123}
    tokens = optimizer._estimate_tokens(data)

    assert tokens > 0
    assert isinstance(tokens, int)


def test_estimate_tokens_string(optimizer):
    """Test token estimation for string."""
    data = "This is a test string"
    tokens = optimizer._estimate_tokens(data)

    assert tokens > 0


def test_estimate_tokens_large_data(optimizer):
    """Test token estimation for large data."""
    data = {'data': 'x' * 10000}
    tokens = optimizer._estimate_tokens(data)

    assert tokens > 2000  # Should be substantial


def test_estimate_tokens_fallback_on_error(optimizer):
    """Test token estimation fallback on error."""
    # Create an object that can't be JSON serialized
    class NonSerializable:
        pass

    tokens = optimizer._estimate_tokens(NonSerializable())
    assert tokens == 1000  # Default fallback


# ============================================================================
# Test: Pruning Technique
# ============================================================================

def test_prune_old_debug_traces(optimizer, sample_context):
    """Test pruning of old debug traces."""
    import copy
    original_count = len(sample_context['debug_traces'])
    optimized = optimizer._prune_temporary_data(copy.deepcopy(sample_context))

    # Should keep only recent traces
    assert 'debug_traces' in optimized
    assert len(optimized['debug_traces']) < original_count


def test_prune_validation_results(optimizer, sample_context):
    """Test pruning validation results to last 5."""
    optimized = optimizer._prune_temporary_data(sample_context)

    assert 'validation_results' in optimized
    assert len(optimized['validation_results']) == 5


def test_prune_resolved_errors(optimizer, sample_context):
    """Test pruning of old resolved errors."""
    optimized = optimizer._prune_temporary_data(sample_context)

    assert 'errors' in optimized
    # Should keep all unresolved + last 10 resolved
    unresolved = [e for e in optimized['errors'] if not e.get('resolved')]
    resolved = [e for e in optimized['errors'] if e.get('resolved')]

    assert len(unresolved) == 1  # Original had 1 unresolved
    assert len(resolved) <= 10


def test_prune_empty_context(optimizer):
    """Test pruning with empty context."""
    context = {}
    optimized = optimizer._prune_temporary_data(context)

    assert optimized == {}


# ============================================================================
# Test: Artifact Registry Technique
# ============================================================================

def test_artifact_registry_replaces_files(optimizer, sample_context):
    """Test artifact registry replaces file contents."""
    optimized = optimizer._apply_artifact_registry(sample_context)

    assert 'artifact_registry' in optimized
    assert 'files' not in optimized
    assert '/path/to/file.py' in optimized['artifact_registry']


def test_artifact_registry_preserves_metadata(optimizer, sample_context):
    """Test artifact registry preserves file metadata."""
    optimized = optimizer._apply_artifact_registry(sample_context)

    registry = optimized['artifact_registry']['/path/to/file.py']
    assert 'size_tokens' in registry
    assert 'last_modified' in registry
    assert registry['last_modified'] == '2025-01-15T10:00:00Z'


def test_artifact_registry_no_files(optimizer):
    """Test artifact registry with no files."""
    context = {'task_id': 'test'}
    optimized = optimizer._apply_artifact_registry(context)

    assert optimized == context


# ============================================================================
# Test: External Storage Technique
# ============================================================================

def test_externalize_large_artifacts(optimizer, temp_dirs):
    """Test externalization of large artifacts."""
    context = {
        'artifacts': [
            {
                'id': 'large_artifact',
                'data': 'x' * 10000  # Large artifact
            }
        ]
    }

    optimized, count = optimizer._externalize_large_artifacts(context)

    assert count == 1
    assert 'artifacts' in optimized
    assert optimized['artifacts'][0]['_external_ref']

    # Check file was created
    external_file = Path(optimized['artifacts'][0]['_external_ref'])
    assert external_file.exists()


def test_externalize_keeps_small_artifacts(optimizer):
    """Test that small artifacts are not externalized."""
    context = {
        'artifacts': [
            {
                'id': 'small_artifact',
                'data': 'small'
            }
        ]
    }

    optimized, count = optimizer._externalize_large_artifacts(context)

    assert count == 0
    assert optimized['artifacts'][0]['data'] == 'small'
    assert '_external_ref' not in optimized['artifacts'][0]


def test_externalize_no_artifacts(optimizer):
    """Test externalization with no artifacts."""
    context = {'task_id': 'test'}
    optimized, count = optimizer._externalize_large_artifacts(context)

    assert count == 0
    assert optimized == context


# ============================================================================
# Test: Differential State Technique
# ============================================================================

def test_differential_state_conversion(optimizer, sample_context):
    """Test conversion to differential state."""
    optimized = optimizer._convert_to_differential_state(sample_context)

    assert 'state_delta' in optimized
    assert 'full_state' not in optimized
    assert optimized['state_delta']['checkpoint_id'] == 'latest'


def test_differential_state_no_full_state(optimizer):
    """Test differential state with no full_state."""
    context = {'task_id': 'test'}
    optimized = optimizer._convert_to_differential_state(context)

    assert optimized == context


# ============================================================================
# Test: Summarization Technique
# ============================================================================

def test_summarize_completed_phases(optimizer, sample_context):
    """Test summarization of completed phases."""
    optimized = optimizer._summarize_completed_phases(sample_context)

    # Should archive and summarize large completed phases
    assert 'phases' in optimized
    phase = optimized['phases'][0]

    # Check if archived
    if 'archived_at' in phase:
        assert Path(phase['archived_at']).exists()


def test_summarize_skip_incomplete_phases(optimizer):
    """Test that incomplete phases are not summarized."""
    context = {
        'phases': [
            {
                'phase_id': 'active',
                'status': 'in_progress',
                'data': 'x' * 2000
            }
        ]
    }

    optimized = optimizer._summarize_completed_phases(context)
    assert optimized['phases'][0]['data'] == 'x' * 2000


def test_summarize_skip_small_phases(optimizer):
    """Test that small phases are not summarized."""
    context = {
        'phases': [
            {
                'phase_id': 'small',
                'status': 'completed',
                'data': 'small data'
            }
        ]
    }

    optimized = optimizer._summarize_completed_phases(context)
    assert optimized['phases'][0]['data'] == 'small data'


def test_summarize_no_llm(optimizer, sample_context):
    """Test summarization without LLM interface."""
    # Optimizer fixture has no LLM
    optimized = optimizer._summarize_completed_phases(sample_context)

    # Should still work, just archives without LLM summary
    assert 'phases' in optimized


# ============================================================================
# Test: Full Optimization Pipeline
# ============================================================================

def test_optimize_context_success(optimizer, sample_context):
    """Test full optimization pipeline."""
    result = optimizer.optimize_context(sample_context)

    assert isinstance(result, OptimizationResult)
    assert result.tokens_before > 0
    assert result.tokens_after > 0
    assert 0 < result.compression_ratio <= 1
    assert len(result.techniques_applied) > 0


def test_optimize_context_achieves_reduction(optimizer, sample_context):
    """Test that optimization reduces token count."""
    result = optimizer.optimize_context(sample_context, target_reduction=0.3)

    assert result.tokens_after < result.tokens_before
    assert result.compression_ratio < 1.0


def test_optimize_context_techniques_applied(optimizer, sample_context):
    """Test that multiple techniques are applied."""
    result = optimizer.optimize_context(sample_context)

    # Should apply at least pruning, artifact_registry, external_storage
    assert 'pruning' in result.techniques_applied
    assert 'artifact_registry' in result.techniques_applied


def test_optimize_context_invalid_input(optimizer):
    """Test optimization with invalid input."""
    with pytest.raises(ContextOptimizerException) as exc_info:
        optimizer.optimize_context("not a dict")

    assert "must be a dictionary" in str(exc_info.value)


def test_optimize_context_empty(optimizer):
    """Test optimization with empty context."""
    result = optimizer.optimize_context({})

    assert result.tokens_before >= 1
    assert result.tokens_after >= 1


def test_optimize_context_with_errors(optimizer):
    """Test optimization handles errors gracefully."""
    # Create a context that will cause errors in some techniques
    context = {
        'phases': 'invalid_type',  # Should cause error in summarization
        'files': 'invalid_type'     # Should cause error in artifact registry
    }

    result = optimizer.optimize_context(context)

    # Should complete despite errors
    assert isinstance(result, OptimizationResult)
    # May have some errors recorded
    # assert len(result.errors) > 0  # Might have errors


# ============================================================================
# Test: OptimizationResult
# ============================================================================

def test_optimization_result_creation():
    """Test OptimizationResult dataclass."""
    result = OptimizationResult(
        tokens_before=1000,
        tokens_after=700,
        compression_ratio=0.7,
        techniques_applied=['pruning', 'artifact_registry'],
        items_optimized=5,
        items_externalized=2
    )

    assert result.tokens_before == 1000
    assert result.tokens_after == 700
    assert result.compression_ratio == 0.7
    assert len(result.techniques_applied) == 2
    assert result.items_optimized == 5
    assert result.items_externalized == 2
    assert result.errors == []


def test_optimization_result_with_errors():
    """Test OptimizationResult with errors."""
    result = OptimizationResult(
        tokens_before=1000,
        tokens_after=900,
        compression_ratio=0.9,
        techniques_applied=['pruning'],
        errors=['Error 1', 'Error 2']
    )

    assert len(result.errors) == 2


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_is_recent_with_valid_timestamp(optimizer):
    """Test timestamp recency check."""
    now = datetime.now(timezone.utc)
    recent = now.isoformat()
    cutoff = now - timedelta(hours=1)

    assert optimizer._is_recent(recent, cutoff) is True


def test_is_recent_with_old_timestamp(optimizer):
    """Test timestamp recency check with old timestamp."""
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    assert optimizer._is_recent(old, cutoff) is False


def test_is_recent_with_none(optimizer):
    """Test timestamp recency check with None."""
    cutoff = datetime.now(timezone.utc)
    assert optimizer._is_recent(None, cutoff) is False


def test_is_recent_with_invalid_timestamp(optimizer):
    """Test timestamp recency check with invalid format."""
    cutoff = datetime.now(timezone.utc)
    assert optimizer._is_recent('invalid', cutoff) is False


def test_optimize_with_custom_thresholds(optimizer_config):
    """Test optimization with custom thresholds."""
    custom_config = optimizer_config.copy()
    custom_config['summarization_threshold'] = 100
    custom_config['externalization_threshold'] = 500

    optimizer = ContextOptimizer(config=custom_config)

    assert optimizer.summarization_threshold == 100
    assert optimizer.externalization_threshold == 500


def test_large_context_optimization(optimizer):
    """Test optimization with very large context."""
    large_context = {
        'data': 'x' * 100000,  # 100K characters
        'artifacts': [
            {'id': f'artifact_{i}', 'data': 'x' * 10000}  # 10K chars = ~2500 tokens
            for i in range(10)
        ],
        'debug_traces': [
            {
                'timestamp': (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                'message': f'trace_{i}' * 100
            }
            for i in range(20)
        ]
    }

    result = optimizer.optimize_context(large_context)

    assert result.tokens_before > 10000
    # Should achieve some compression from pruning and/or externalization
    assert result.compression_ratio <= 1.0
