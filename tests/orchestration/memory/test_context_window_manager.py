"""Unit tests for context window manager.

Tests cover:
- Initialization with utilization limits
- Threshold calculations
- Usage tracking and zone transitions
- Thread safety
- All accessor methods
- Edge cases

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
import threading
import time
from typing import Dict, Any

from src.orchestration.memory.context_window_manager import ContextWindowManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def basic_config() -> Dict[str, Any]:
    """Create a basic model configuration."""
    return {
        'model': 'test-model',
        'context_window': 100000
    }


@pytest.fixture
def manager(basic_config) -> ContextWindowManager:
    """Create a ContextWindowManager with default settings."""
    return ContextWindowManager(basic_config)


@pytest.fixture
def manager_with_limit(basic_config) -> ContextWindowManager:
    """Create a ContextWindowManager with 75% utilization limit."""
    return ContextWindowManager(basic_config, utilization_limit=0.75)


# ============================================================================
# Test: Initialization
# ============================================================================

def test_init_with_default_limit(basic_config):
    """Test initialization with default 100% utilization limit."""
    manager = ContextWindowManager(basic_config)

    assert manager.max_tokens == 100000
    assert manager.utilization_limit == 1.0
    assert manager.effective_max_tokens == 100000
    assert manager.used_tokens() == 0


def test_init_with_custom_limit(basic_config):
    """Test initialization with custom utilization limit."""
    manager = ContextWindowManager(basic_config, utilization_limit=0.75)

    assert manager.max_tokens == 100000
    assert manager.utilization_limit == 0.75
    assert manager.effective_max_tokens == 75000  # 100K * 0.75


def test_init_with_various_limits(basic_config):
    """Test initialization with various utilization limits."""
    test_cases = [
        (0.5, 50000),   # 50% of 100K
        (0.8, 80000),   # 80% of 100K
        (0.9, 90000),   # 90% of 100K
        (1.0, 100000),  # 100% of 100K
    ]

    for limit, expected_effective_max in test_cases:
        manager = ContextWindowManager(basic_config, utilization_limit=limit)
        assert manager.effective_max_tokens == expected_effective_max, \
            f"Failed for limit={limit}"


def test_init_missing_context_window():
    """Test initialization with missing context_window in config."""
    invalid_config = {'model': 'test'}

    with pytest.raises(ValueError) as exc_info:
        ContextWindowManager(invalid_config)

    assert 'context_window' in str(exc_info.value)


def test_init_invalid_utilization_limit_zero(basic_config):
    """Test initialization with zero utilization limit."""
    with pytest.raises(ValueError) as exc_info:
        ContextWindowManager(basic_config, utilization_limit=0.0)

    assert 'utilization_limit must be in range (0.0, 1.0]' in str(exc_info.value)


def test_init_invalid_utilization_limit_negative(basic_config):
    """Test initialization with negative utilization limit."""
    with pytest.raises(ValueError) as exc_info:
        ContextWindowManager(basic_config, utilization_limit=-0.5)

    assert 'utilization_limit must be in range' in str(exc_info.value)


def test_init_invalid_utilization_limit_too_large(basic_config):
    """Test initialization with utilization limit > 1.0."""
    with pytest.raises(ValueError) as exc_info:
        ContextWindowManager(basic_config, utilization_limit=1.5)

    assert 'utilization_limit must be in range' in str(exc_info.value)


# ============================================================================
# Test: Threshold Calculations
# ============================================================================

def test_thresholds_with_default_limit(manager):
    """Test threshold calculations with 100% utilization."""
    # With 100K context at 100% utilization
    assert manager.thresholds['green_upper'] == 50000   # 50% of 100K
    assert manager.thresholds['yellow_upper'] == 70000  # 70% of 100K
    assert manager.thresholds['orange_upper'] == 85000  # 85% of 100K
    assert manager.thresholds['red'] == 95000           # 95% of 100K


def test_thresholds_with_custom_limit(manager_with_limit):
    """Test threshold calculations with 75% utilization limit."""
    # With 100K context at 75% utilization (75K effective)
    assert manager_with_limit.thresholds['green_upper'] == 37500   # 50% of 75K
    assert manager_with_limit.thresholds['yellow_upper'] == 52500  # 70% of 75K
    assert manager_with_limit.thresholds['orange_upper'] == 63750  # 85% of 75K
    assert manager_with_limit.thresholds['red'] == 71250           # 95% of 75K


def test_thresholds_with_small_context():
    """Test threshold calculations with small context window."""
    small_config = {'context_window': 4096}
    manager = ContextWindowManager(small_config, utilization_limit=0.75)

    # 4096 * 0.75 = 3072 effective
    assert manager.effective_max_tokens == 3072
    assert manager.thresholds['green_upper'] == 1536   # 50% of 3072
    assert manager.thresholds['yellow_upper'] == 2150  # 70% of 3072
    assert manager.thresholds['orange_upper'] == 2611  # 85% of 3072


def test_thresholds_with_large_context():
    """Test threshold calculations with large context window."""
    large_config = {'context_window': 1000000}  # 1M
    manager = ContextWindowManager(large_config, utilization_limit=0.8)

    # 1M * 0.8 = 800K effective
    assert manager.effective_max_tokens == 800000
    assert manager.thresholds['green_upper'] == 400000   # 50% of 800K
    assert manager.thresholds['yellow_upper'] == 560000  # 70% of 800K
    assert manager.thresholds['orange_upper'] == 680000  # 85% of 800K


def test_custom_thresholds(basic_config):
    """Test initialization with custom threshold percentages."""
    custom_thresholds = {
        'green_upper': 0.40,
        'yellow_upper': 0.60,
        'orange_upper': 0.80,
        'red': 0.90
    }

    manager = ContextWindowManager(
        basic_config,
        custom_thresholds=custom_thresholds
    )

    assert manager.thresholds['green_upper'] == 40000
    assert manager.thresholds['yellow_upper'] == 60000
    assert manager.thresholds['orange_upper'] == 80000
    assert manager.thresholds['red'] == 90000


# ============================================================================
# Test: Usage Tracking
# ============================================================================

def test_add_usage(manager):
    """Test adding token usage."""
    manager.add_usage(10000)
    assert manager.used_tokens() == 10000

    manager.add_usage(15000)
    assert manager.used_tokens() == 25000


def test_add_usage_multiple_operations(manager):
    """Test cumulative usage across multiple operations."""
    operations = [5000, 10000, 7500, 12500]

    for tokens in operations:
        manager.add_usage(tokens)

    assert manager.used_tokens() == sum(operations)


def test_available_tokens(manager):
    """Test available tokens calculation."""
    manager.add_usage(30000)

    available = manager.available_tokens()
    assert available == 70000  # 100K - 30K


def test_available_tokens_with_limit(manager_with_limit):
    """Test available tokens with utilization limit."""
    manager_with_limit.add_usage(50000)

    available = manager_with_limit.available_tokens()
    assert available == 25000  # 75K effective - 50K used


def test_available_tokens_when_exceeded(manager):
    """Test available tokens when usage exceeds maximum."""
    manager.add_usage(110000)  # Exceeds 100K

    available = manager.available_tokens()
    assert available == 0  # Should not go negative


def test_usage_percentage(manager):
    """Test usage percentage calculation."""
    manager.add_usage(60000)

    pct = manager.usage_percentage()
    assert pct == 0.6  # 60K / 100K


def test_usage_percentage_with_limit(manager_with_limit):
    """Test usage percentage with utilization limit."""
    manager_with_limit.add_usage(60000)

    pct = manager_with_limit.usage_percentage()
    assert pct == 0.8  # 60K / 75K effective


def test_usage_percentage_exceeds_max(manager):
    """Test usage percentage when exceeding maximum."""
    manager.add_usage(120000)

    pct = manager.usage_percentage()
    assert pct == 1.2  # Can exceed 1.0


# ============================================================================
# Test: Zone Determination
# ============================================================================

def test_get_zone_green(manager):
    """Test zone determination in green zone."""
    manager.add_usage(40000)  # < 50K (green threshold)

    assert manager.get_zone() == 'green'


def test_get_zone_yellow(manager):
    """Test zone determination in yellow zone."""
    manager.add_usage(60000)  # 50K ≤ x < 70K

    assert manager.get_zone() == 'yellow'


def test_get_zone_orange(manager):
    """Test zone determination in orange zone."""
    manager.add_usage(75000)  # 70K ≤ x < 85K

    assert manager.get_zone() == 'orange'


def test_get_zone_red(manager):
    """Test zone determination in red zone."""
    manager.add_usage(90000)  # ≥ 85K

    assert manager.get_zone() == 'red'


def test_zone_transitions(manager):
    """Test zone transitions as usage increases."""
    assert manager.get_zone() == 'green'

    manager.add_usage(45000)
    assert manager.get_zone() == 'green'

    manager.add_usage(10000)  # Total 55K
    assert manager.get_zone() == 'yellow'

    manager.add_usage(20000)  # Total 75K
    assert manager.get_zone() == 'orange'

    manager.add_usage(20000)  # Total 95K
    assert manager.get_zone() == 'red'


def test_zone_with_utilization_limit(manager_with_limit):
    """Test zone determination with utilization limit."""
    # Effective max is 75K

    manager_with_limit.add_usage(30000)  # < 37.5K
    assert manager_with_limit.get_zone() == 'green'

    manager_with_limit.add_usage(15000)  # Total 45K (37.5-52.5K)
    assert manager_with_limit.get_zone() == 'yellow'

    manager_with_limit.add_usage(15000)  # Total 60K (52.5-63.75K)
    assert manager_with_limit.get_zone() == 'orange'

    manager_with_limit.add_usage(15000)  # Total 75K (≥63.75K)
    assert manager_with_limit.get_zone() == 'red'


# ============================================================================
# Test: Recommended Actions
# ============================================================================

def test_recommended_action_green(manager):
    """Test recommended action in green zone."""
    manager.add_usage(40000)

    action = manager.get_recommended_action()
    assert action == 'proceed_normally'


def test_recommended_action_yellow(manager):
    """Test recommended action in yellow zone."""
    manager.add_usage(60000)

    action = manager.get_recommended_action()
    assert action == 'monitor_and_plan_checkpoint'


def test_recommended_action_orange(manager):
    """Test recommended action in orange zone."""
    manager.add_usage(75000)

    action = manager.get_recommended_action()
    assert action == 'optimize_then_checkpoint'


def test_recommended_action_red(manager):
    """Test recommended action in red zone."""
    manager.add_usage(90000)

    action = manager.get_recommended_action()
    assert action == 'emergency_checkpoint_and_refresh'


# ============================================================================
# Test: Reset Functionality
# ============================================================================

def test_reset(manager):
    """Test resetting usage counter."""
    manager.add_usage(80000)
    assert manager.used_tokens() == 80000

    manager.reset()

    assert manager.used_tokens() == 0
    assert manager.get_zone() == 'green'


def test_reset_preserves_configuration(manager_with_limit):
    """Test that reset preserves configuration."""
    original_max = manager_with_limit.max_tokens
    original_limit = manager_with_limit.utilization_limit
    original_effective = manager_with_limit.effective_max_tokens

    manager_with_limit.add_usage(50000)
    manager_with_limit.reset()

    assert manager_with_limit.max_tokens == original_max
    assert manager_with_limit.utilization_limit == original_limit
    assert manager_with_limit.effective_max_tokens == original_effective


# ============================================================================
# Test: can_accommodate Method
# ============================================================================

def test_can_accommodate_within_yellow(manager):
    """Test can_accommodate when result stays in yellow zone."""
    manager.add_usage(50000)

    # Adding 15K would be 65K total (still < 70K yellow threshold)
    assert manager.can_accommodate(15000) is True


def test_can_accommodate_exceeds_yellow(manager):
    """Test can_accommodate when result would exceed yellow zone."""
    manager.add_usage(50000)

    # Adding 25K would be 75K total (> 70K yellow threshold)
    assert manager.can_accommodate(25000) is False


def test_can_accommodate_with_limit(manager_with_limit):
    """Test can_accommodate with utilization limit."""
    # Effective max is 75K, yellow threshold is 52.5K
    manager_with_limit.add_usage(40000)

    # Adding 10K would be 50K (< 52.5K)
    assert manager_with_limit.can_accommodate(10000) is True

    # Adding 20K would be 60K (> 52.5K)
    assert manager_with_limit.can_accommodate(20000) is False


# ============================================================================
# Test: get_status Method
# ============================================================================

def test_get_status(manager):
    """Test get_status returns comprehensive information."""
    manager.add_usage(60000)

    status = manager.get_status()

    assert status['model'] == 'test-model'
    assert status['max_tokens'] == 100000
    assert status['utilization_limit'] == 1.0
    assert status['effective_max_tokens'] == 100000
    assert status['used_tokens'] == 60000
    assert status['available_tokens'] == 40000
    assert status['usage_percentage'] == 0.6
    assert status['zone'] == 'yellow'
    assert status['recommended_action'] == 'monitor_and_plan_checkpoint'
    assert 'thresholds' in status


def test_get_status_returns_copy_of_thresholds(manager):
    """Test that get_status returns a copy of thresholds, not reference."""
    status1 = manager.get_status()
    status2 = manager.get_status()

    # Modify first
    status1['thresholds']['green_upper'] = 999999

    # Second should be unchanged
    assert status2['thresholds']['green_upper'] == 50000


# ============================================================================
# Test: Thread Safety
# ============================================================================

def test_concurrent_add_usage(manager):
    """Test thread-safe concurrent usage additions."""
    errors = []

    def add_tokens():
        try:
            for _ in range(10):
                manager.add_usage(100)
        except Exception as e:
            errors.append(e)

    # Create 3 threads (within WSL2 limits)
    threads = [threading.Thread(target=add_tokens) for _ in range(3)]

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=5.0)  # Mandatory timeout

    assert len(errors) == 0, f"Thread errors: {errors}"
    assert manager.used_tokens() == 3000  # 3 threads × 10 iterations × 100 tokens


def test_concurrent_operations(manager):
    """Test thread-safe concurrent mixed operations."""
    errors = []
    results = []

    def mixed_operations():
        try:
            manager.add_usage(1000)
            zone = manager.get_zone()
            available = manager.available_tokens()
            pct = manager.usage_percentage()
            results.append((zone, available, pct))
        except Exception as e:
            errors.append(e)

    # Create 5 threads (max for WSL2)
    threads = [threading.Thread(target=mixed_operations) for _ in range(5)]

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=5.0)

    assert len(errors) == 0
    assert manager.used_tokens() == 5000
    assert len(results) == 5


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_zero_usage(manager):
    """Test manager with zero usage."""
    assert manager.used_tokens() == 0
    assert manager.available_tokens() == manager.effective_max_tokens
    assert manager.usage_percentage() == 0.0
    assert manager.get_zone() == 'green'


def test_exact_threshold_boundaries(manager):
    """Test behavior at exact threshold boundaries."""
    # Exactly at green/yellow boundary (50K)
    manager.add_usage(50000)
    assert manager.get_zone() == 'yellow'  # At boundary = next zone

    manager.reset()

    # Exactly at yellow/orange boundary (70K)
    manager.add_usage(70000)
    assert manager.get_zone() == 'orange'

    manager.reset()

    # Exactly at orange/red boundary (85K)
    manager.add_usage(85000)
    assert manager.get_zone() == 'red'


def test_exceeding_effective_max(manager_with_limit):
    """Test behavior when usage exceeds effective max."""
    # Effective max is 75K
    manager_with_limit.add_usage(100000)  # Exceeds effective max

    assert manager_with_limit.used_tokens() == 100000
    assert manager_with_limit.available_tokens() == 0
    assert manager_with_limit.usage_percentage() > 1.0
    assert manager_with_limit.get_zone() == 'red'


def test_very_small_context():
    """Test with very small context window."""
    tiny_config = {'context_window': 1000}
    manager = ContextWindowManager(tiny_config)

    assert manager.effective_max_tokens == 1000
    assert manager.thresholds['green_upper'] == 500
    assert manager.thresholds['yellow_upper'] == 700
    assert manager.thresholds['orange_upper'] == 850


def test_model_name_optional(basic_config):
    """Test that model name is optional in config."""
    config_without_model = {'context_window': 100000}
    manager = ContextWindowManager(config_without_model)

    assert manager.model_name == 'unknown'
    status = manager.get_status()
    assert status['model'] == 'unknown'
