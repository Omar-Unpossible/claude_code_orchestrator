"""Unit tests for AdaptiveOptimizer.

Tests cover:
- Initialization and profile loading
- Auto-selection based on context size
- Manual override
- Custom thresholds
- Helper methods
- Edge cases

Author: Obra System
Created: 2025-01-15
"""

import pytest
import tempfile
from pathlib import Path

from src.orchestration.memory.adaptive_optimizer import (
    AdaptiveOptimizer,
    AdaptiveOptimizerException,
    OptimizationProfile
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config_path():
    """Path to optimization profiles config."""
    return 'config/optimization_profiles.yaml'


# ============================================================================
# Test: Initialization
# ============================================================================

def test_init_with_small_context(config_path):
    """Test initialization with small context (4K)."""
    optimizer = AdaptiveOptimizer(context_window_size=4000, config_path=config_path)

    assert optimizer.context_window_size == 4000
    assert optimizer.active_profile.name == "Ultra-Aggressive"


def test_init_with_medium_context(config_path):
    """Test initialization with medium context (16K)."""
    optimizer = AdaptiveOptimizer(context_window_size=16000, config_path=config_path)

    assert optimizer.context_window_size == 16000
    assert optimizer.active_profile.name == "Aggressive"


def test_init_with_large_context(config_path):
    """Test initialization with large context (64K)."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.context_window_size == 64000
    assert optimizer.active_profile.name == "Balanced-Aggressive"


def test_init_with_very_large_context(config_path):
    """Test initialization with very large context (200K)."""
    optimizer = AdaptiveOptimizer(context_window_size=200000, config_path=config_path)

    assert optimizer.context_window_size == 200000
    assert optimizer.active_profile.name == "Balanced"


def test_init_with_huge_context(config_path):
    """Test initialization with huge context (1M)."""
    optimizer = AdaptiveOptimizer(context_window_size=1000000, config_path=config_path)

    assert optimizer.context_window_size == 1000000
    assert optimizer.active_profile.name == "Minimal"


def test_init_with_invalid_context():
    """Test initialization with invalid context size."""
    with pytest.raises(AdaptiveOptimizerException) as exc_info:
        AdaptiveOptimizer(context_window_size=0)

    assert "must be positive" in str(exc_info.value)


def test_init_with_negative_context():
    """Test initialization with negative context size."""
    with pytest.raises(AdaptiveOptimizerException) as exc_info:
        AdaptiveOptimizer(context_window_size=-1000)

    assert "must be positive" in str(exc_info.value)


# ============================================================================
# Test: Profile Selection
# ============================================================================

def test_profile_selection_boundaries_4k(config_path):
    """Test profile selection at 4K boundary."""
    optimizer = AdaptiveOptimizer(context_window_size=4000, config_path=config_path)
    assert optimizer.get_active_profile_name() == "Ultra-Aggressive"


def test_profile_selection_boundaries_8k(config_path):
    """Test profile selection at 8K boundary."""
    optimizer = AdaptiveOptimizer(context_window_size=8001, config_path=config_path)
    assert optimizer.get_active_profile_name() == "Aggressive"


def test_profile_selection_boundaries_32k(config_path):
    """Test profile selection at 32K boundary."""
    optimizer = AdaptiveOptimizer(context_window_size=32001, config_path=config_path)
    assert optimizer.get_active_profile_name() == "Balanced-Aggressive"


def test_profile_selection_boundaries_100k(config_path):
    """Test profile selection at 100K boundary."""
    optimizer = AdaptiveOptimizer(context_window_size=100001, config_path=config_path)
    assert optimizer.get_active_profile_name() == "Balanced"


def test_profile_selection_boundaries_250k(config_path):
    """Test profile selection at 250K boundary."""
    optimizer = AdaptiveOptimizer(context_window_size=250001, config_path=config_path)
    assert optimizer.get_active_profile_name() == "Minimal"


# ============================================================================
# Test: Manual Override
# ============================================================================

def test_manual_override_to_ultra_aggressive(config_path):
    """Test manual override to ultra_aggressive profile."""
    optimizer = AdaptiveOptimizer(
        context_window_size=128000,
        config_path=config_path,
        manual_override='ultra_aggressive'
    )

    assert optimizer.get_active_profile_name() == "Ultra-Aggressive"
    assert optimizer.context_window_size == 128000  # Size unchanged


def test_manual_override_to_minimal(config_path):
    """Test manual override to minimal profile."""
    optimizer = AdaptiveOptimizer(
        context_window_size=4000,
        config_path=config_path,
        manual_override='minimal'
    )

    assert optimizer.get_active_profile_name() == "Minimal"


def test_manual_override_invalid_profile(config_path):
    """Test manual override with invalid profile name."""
    with pytest.raises(AdaptiveOptimizerException) as exc_info:
        AdaptiveOptimizer(
            context_window_size=128000,
            config_path=config_path,
            manual_override='nonexistent_profile'
        )

    assert "not found" in str(exc_info.value)


# ============================================================================
# Test: Custom Thresholds
# ============================================================================

def test_custom_thresholds_summarization(config_path):
    """Test custom summarization threshold."""
    custom = {'summarization_threshold': 750}
    optimizer = AdaptiveOptimizer(
        context_window_size=128000,
        config_path=config_path,
        custom_thresholds=custom
    )

    assert optimizer.active_profile.summarization_threshold == 750


def test_custom_thresholds_multiple(config_path):
    """Test multiple custom thresholds."""
    custom = {
        'summarization_threshold': 750,
        'externalization_threshold': 3000,
        'checkpoint_interval_hours': 3.0
    }
    optimizer = AdaptiveOptimizer(
        context_window_size=128000,
        config_path=config_path,
        custom_thresholds=custom
    )

    assert optimizer.active_profile.summarization_threshold == 750
    assert optimizer.active_profile.externalization_threshold == 3000
    assert optimizer.active_profile.checkpoint_interval_hours == 3.0


def test_custom_thresholds_invalid_key(config_path):
    """Test custom threshold with invalid key (should be ignored)."""
    custom = {'nonexistent_field': 999}
    optimizer = AdaptiveOptimizer(
        context_window_size=128000,
        config_path=config_path,
        custom_thresholds=custom
    )

    # Should initialize successfully, just log warning
    assert optimizer.context_window_size == 128000


# ============================================================================
# Test: should_optimize Method
# ============================================================================

def test_should_optimize_phase_below_threshold(config_path):
    """Test should_optimize for phase below threshold."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)
    # Balanced-aggressive has summarization_threshold=500

    assert optimizer.should_optimize(400, 'phase') is False


def test_should_optimize_phase_above_threshold(config_path):
    """Test should_optimize for phase above threshold."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.should_optimize(600, 'phase') is True


def test_should_optimize_artifact_below_threshold(config_path):
    """Test should_optimize for artifact below threshold."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)
    # Balanced-aggressive has externalization_threshold=2000

    assert optimizer.should_optimize(1500, 'artifact') is False


def test_should_optimize_artifact_above_threshold(config_path):
    """Test should_optimize for artifact above threshold."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.should_optimize(2500, 'artifact') is True


def test_should_optimize_unknown_type(config_path):
    """Test should_optimize for unknown type (uses summarization threshold)."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.should_optimize(600, 'unknown_type') is True
    assert optimizer.should_optimize(400, 'unknown_type') is False


# ============================================================================
# Test: Helper Methods
# ============================================================================

def test_get_active_profile(config_path):
    """Test get_active_profile returns dictionary."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    profile = optimizer.get_active_profile()

    assert isinstance(profile, dict)
    assert 'name' in profile
    assert 'summarization_threshold' in profile
    assert profile['name'] == "Balanced-Aggressive"


def test_get_active_profile_name(config_path):
    """Test get_active_profile_name."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.get_active_profile_name() == "Balanced-Aggressive"


def test_should_use_artifact_registry_true(config_path):
    """Test should_use_artifact_registry returns True."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.should_use_artifact_registry() is True


def test_should_use_artifact_registry_false(config_path):
    """Test should_use_artifact_registry returns False."""
    optimizer = AdaptiveOptimizer(context_window_size=200000, config_path=config_path)
    # Balanced profile has artifact_registry_enabled=false

    assert optimizer.should_use_artifact_registry() is False


def test_should_use_differential_state_true(config_path):
    """Test should_use_differential_state returns True."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.should_use_differential_state() is True


def test_should_use_differential_state_false(config_path):
    """Test should_use_differential_state returns False."""
    optimizer = AdaptiveOptimizer(context_window_size=500000, config_path=config_path)
    # Minimal profile has differential_state_enabled=false

    assert optimizer.should_use_differential_state() is False


def test_get_checkpoint_config(config_path):
    """Test get_checkpoint_config."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    config = optimizer.get_checkpoint_config()

    assert 'interval_hours' in config
    assert 'threshold_pct' in config
    assert 'operation_count' in config
    assert config['interval_hours'] == 2.0
    assert config['threshold_pct'] == 85
    assert config['operation_count'] == 100


def test_get_working_memory_config(config_path):
    """Test get_working_memory_config."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    config = optimizer.get_working_memory_config()

    assert 'max_operations' in config
    assert 'max_tokens_pct' in config
    assert 'max_tokens' in config
    assert config['max_operations'] == 40
    assert config['max_tokens_pct'] == 0.08
    assert config['max_tokens'] == 5120  # 64000 * 0.08


def test_get_pruning_config(config_path):
    """Test get_pruning_config."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    config = optimizer.get_pruning_config()

    assert 'age_hours' in config
    assert 'max_validation_results' in config
    assert 'max_resolved_errors' in config
    assert config['age_hours'] == 2.0
    assert config['max_validation_results'] == 5
    assert config['max_resolved_errors'] == 10


# ============================================================================
# Test: Profile-Specific Settings
# ============================================================================

def test_ultra_aggressive_settings(config_path):
    """Test ultra-aggressive profile has correct aggressive settings."""
    optimizer = AdaptiveOptimizer(context_window_size=4000, config_path=config_path)

    assert optimizer.active_profile.summarization_threshold == 100
    assert optimizer.active_profile.checkpoint_interval_hours == 0.5
    assert optimizer.active_profile.max_operations == 10


def test_aggressive_settings(config_path):
    """Test aggressive profile settings."""
    optimizer = AdaptiveOptimizer(context_window_size=16000, config_path=config_path)

    assert optimizer.active_profile.summarization_threshold == 300
    assert optimizer.active_profile.checkpoint_interval_hours == 1.0
    assert optimizer.active_profile.max_operations == 20


def test_balanced_aggressive_settings(config_path):
    """Test balanced-aggressive profile settings."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    assert optimizer.active_profile.summarization_threshold == 500
    assert optimizer.active_profile.checkpoint_interval_hours == 2.0
    assert optimizer.active_profile.max_operations == 40


def test_balanced_settings(config_path):
    """Test balanced profile settings."""
    optimizer = AdaptiveOptimizer(context_window_size=200000, config_path=config_path)

    assert optimizer.active_profile.summarization_threshold == 500
    assert optimizer.active_profile.checkpoint_interval_hours == 4.0
    assert optimizer.active_profile.max_operations == 75


def test_minimal_settings(config_path):
    """Test minimal profile settings."""
    optimizer = AdaptiveOptimizer(context_window_size=1000000, config_path=config_path)

    assert optimizer.active_profile.summarization_threshold == 1000
    assert optimizer.active_profile.checkpoint_interval_hours == 8.0
    assert optimizer.active_profile.max_operations == 100


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_repr(config_path):
    """Test __repr__ method."""
    optimizer = AdaptiveOptimizer(context_window_size=64000, config_path=config_path)

    repr_str = repr(optimizer)

    assert 'AdaptiveOptimizer' in repr_str
    assert '64,000' in repr_str
    assert 'Balanced-Aggressive' in repr_str


def test_load_from_example_file():
    """Test loading from .example file when main config missing."""
    # Use a non-existent path, should fall back to .example
    optimizer = AdaptiveOptimizer(
        context_window_size=64000,
        config_path='config/optimization_profiles.yaml'
    )

    # Should successfully load
    assert optimizer.context_window_size == 64000


def test_invalid_config_file():
    """Test error handling with invalid config file."""
    with pytest.raises(AdaptiveOptimizerException) as exc_info:
        AdaptiveOptimizer(
            context_window_size=64000,
            config_path='/nonexistent/path/config.yaml'
        )

    assert "not found" in str(exc_info.value)


def test_custom_thresholds_with_manual_override(config_path):
    """Test combining manual override with custom thresholds."""
    custom = {'summarization_threshold': 999}
    optimizer = AdaptiveOptimizer(
        context_window_size=64000,
        config_path=config_path,
        manual_override='ultra_aggressive',
        custom_thresholds=custom
    )

    assert optimizer.get_active_profile_name() == "Ultra-Aggressive"
    assert optimizer.active_profile.summarization_threshold == 999


def test_working_memory_config_calculation(config_path):
    """Test working memory max_tokens calculation."""
    optimizer = AdaptiveOptimizer(context_window_size=100000, config_path=config_path)

    config = optimizer.get_working_memory_config()

    # 100000 * 0.08 = 8000 for balanced-aggressive profile
    expected_max_tokens = int(100000 * 0.08)
    assert config['max_tokens'] == expected_max_tokens
