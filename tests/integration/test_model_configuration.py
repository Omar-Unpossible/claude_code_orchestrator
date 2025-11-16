"""Integration tests for model configuration system.

Tests the complete flow from model config loading through context window
detection to context window management.

Tests cover:
- End-to-end configuration loading and detection
- Integration of ModelConfigLoader, ContextWindowDetector, ContextWindowManager
- Multiple model configurations
- Utilization limits
- Real-world usage scenarios

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
import yaml

from src.core.model_config_loader import ModelConfigLoader
from src.orchestration.memory.context_window_detector import ContextWindowDetector
from src.orchestration.memory.context_window_manager import ContextWindowManager


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_models_config():
    """Create a test models configuration."""
    return {
        'llm_models': {
            'small_local': {
                'provider': 'ollama',
                'model': 'qwen2.5-coder:7b',
                'context_window': 16384,
                'optimization_profile': 'aggressive'
            },
            'medium_local': {
                'provider': 'ollama',
                'model': 'qwen2.5-coder:32b',
                'context_window': 128000,
                'optimization_profile': 'balanced'
            },
            'cloud_model': {
                'provider': 'anthropic',
                'model': 'claude-3-5-sonnet-20241022',
                'context_window': 200000,
                'optimization_profile': 'balanced'
            }
        },
        'active_orchestrator_model': 'medium_local',
        'active_implementer_model': 'cloud_model'
    }


@pytest.fixture
def temp_models_file(test_models_config):
    """Create a temporary models.yaml file."""
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.yaml',
        delete=False
    ) as f:
        yaml.dump(test_models_config, f)
        return Path(f.name)


# ============================================================================
# Test: End-to-End Configuration Flow
# ============================================================================

def test_complete_configuration_flow(temp_models_file):
    """Test complete flow from config load to manager creation."""
    # Step 1: Load model configurations
    loader = ModelConfigLoader(str(temp_models_file))

    assert len(loader.models) == 3
    assert loader.active_orchestrator_model == 'medium_local'

    # Step 2: Get active model config
    model_config = loader.get_active_orchestrator_config()

    assert model_config['model'] == 'qwen2.5-coder:32b'
    assert model_config['context_window'] == 128000

    # Step 3: Create context window manager
    manager = ContextWindowManager(model_config, utilization_limit=0.75)

    assert manager.max_tokens == 128000
    assert manager.effective_max_tokens == 96000  # 128K * 0.75

    # Step 4: Verify thresholds calculated correctly
    assert manager.thresholds['green_upper'] == 48000   # 50% of 96K
    assert manager.thresholds['yellow_upper'] == 67200  # 70% of 96K
    assert manager.thresholds['orange_upper'] == 81600  # 85% of 96K

    # Step 5: Use the manager
    manager.add_usage(50000)
    assert manager.get_zone() == 'yellow'


@patch('requests.post')
def test_configuration_with_auto_detection(
    mock_post,
    temp_models_file
):
    """Test configuration flow with auto-detection."""
    # Mock Ollama API response
    mock_response = Mock()
    mock_response.json.return_value = {
        'modelfile': 'PARAMETER num_ctx 128000'
    }
    mock_post.return_value = mock_response

    # Load config
    loader = ModelConfigLoader(str(temp_models_file))
    model_config = loader.get_model('medium_local')

    # Auto-detect (should use mocked API)
    detector = ContextWindowDetector(fallback_size=16384)
    detected_size = detector.detect(
        model_config['provider'],
        model_config['model'],
        model_config=model_config
    )

    # Should detect from API
    assert detected_size == 128000

    # Create manager with detected size
    model_config_with_detected = model_config.copy()
    model_config_with_detected['context_window'] = detected_size

    manager = ContextWindowManager(model_config_with_detected)

    assert manager.max_tokens == 128000


# ============================================================================
# Test: Multiple Model Configurations
# ============================================================================

def test_multiple_models_workflow(temp_models_file):
    """Test managing multiple models with different configurations."""
    loader = ModelConfigLoader(str(temp_models_file))

    # Test small local model (16K context)
    small_config = loader.get_model('small_local')
    small_manager = ContextWindowManager(
        small_config,
        utilization_limit=0.8  # Use 80% = 13,107 tokens
    )

    assert small_manager.effective_max_tokens == 13107  # 16384 * 0.8
    assert small_manager.thresholds['yellow_upper'] == 9174  # 70% of 13107

    # Test medium local model (128K context)
    medium_config = loader.get_model('medium_local')
    medium_manager = ContextWindowManager(
        medium_config,
        utilization_limit=1.0  # Use 100%
    )

    assert medium_manager.effective_max_tokens == 128000
    assert medium_manager.thresholds['yellow_upper'] == 89600  # 70% of 128K

    # Test cloud model (200K context)
    cloud_config = loader.get_model('cloud_model')
    cloud_manager = ContextWindowManager(
        cloud_config,
        utilization_limit=0.9  # Use 90% = 180K
    )

    assert cloud_manager.effective_max_tokens == 180000
    assert cloud_manager.thresholds['yellow_upper'] == 125999  # int(180K * 0.7)


def test_switching_between_models(temp_models_file):
    """Test switching between different model configurations."""
    loader = ModelConfigLoader(str(temp_models_file))

    # Start with small model
    config = loader.get_model('small_local')
    manager = ContextWindowManager(config)

    manager.add_usage(9000)
    assert manager.get_zone() == 'yellow'  # 9K / 16K = 56% (>50% threshold)

    # Switch to medium model
    config = loader.get_model('medium_local')
    manager = ContextWindowManager(config)

    manager.add_usage(8000)
    assert manager.get_zone() == 'green'  # 8K / 128K = 6.25%


# ============================================================================
# Test: Utilization Limit Scenarios
# ============================================================================

def test_conservative_utilization_limit(temp_models_file):
    """Test conservative (50%) utilization limit."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_model('medium_local')  # 128K

    # Use only 50% of capacity
    manager = ContextWindowManager(config, utilization_limit=0.5)

    assert manager.effective_max_tokens == 64000  # 128K * 0.5

    # Yellow zone starts at 50% of 64K = 32K
    manager.add_usage(35000)
    assert manager.get_zone() == 'yellow'

    # This would be green in full 128K, but yellow in 64K effective
    assert manager.usage_percentage() > 0.5


def test_aggressive_utilization_limit(temp_models_file):
    """Test aggressive (100%) utilization limit."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_model('medium_local')  # 128K

    # Use full capacity
    manager = ContextWindowManager(config, utilization_limit=1.0)

    assert manager.effective_max_tokens == 128000

    # Can use more before hitting yellow (need >50% of 128K = >64K)
    manager.add_usage(70000)
    assert manager.get_zone() == 'yellow'  # 70K / 128K = 54.7% (>50% threshold)


def test_utilization_limit_affects_all_operations(temp_models_file):
    """Test that utilization limit affects all manager operations."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_model('medium_local')  # 128K

    manager = ContextWindowManager(config, utilization_limit=0.75)

    # Effective max is 96K
    assert manager.available_tokens() == 96000

    manager.add_usage(50000)
    assert manager.available_tokens() == 46000  # 96K - 50K

    # can_accommodate based on effective max
    assert manager.can_accommodate(10000) is True   # Would be 60K < 67.2K yellow
    assert manager.can_accommodate(30000) is False  # Would be 80K > 67.2K yellow


# ============================================================================
# Test: Real-World Usage Patterns
# ============================================================================

def test_typical_orchestrator_session(temp_models_file):
    """Test typical orchestrator session workflow."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_active_orchestrator_config()

    # Use 80% of capacity for safety
    manager = ContextWindowManager(config, utilization_limit=0.8)

    # Effective: 128K * 0.8 = 102,400 tokens
    # Yellow threshold: 102.4K * 0.7 = 71,680 tokens

    # Simulate various operations
    operations = [
        ('task_validation', 5000),
        ('quality_scoring', 3000),
        ('decision_making', 2000),
        ('nl_processing', 4000),
        ('context_building', 8000),
    ]

    cumulative = 0
    for op_type, tokens in operations:
        manager.add_usage(tokens)
        cumulative += tokens

    assert manager.used_tokens() == cumulative
    assert manager.get_zone() == 'green'  # 22K / 102.4K = 21.5%

    # Continue until yellow zone
    while manager.get_zone() == 'green':
        manager.add_usage(5000)

    # Should now be in yellow zone
    assert manager.get_zone() == 'yellow'
    assert manager.get_recommended_action() == 'monitor_and_plan_checkpoint'


def test_checkpoint_workflow(temp_models_file):
    """Test checkpoint workflow with context reset."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_active_orchestrator_config()

    manager = ContextWindowManager(config, utilization_limit=0.75)

    # Build up context
    for _ in range(10):
        manager.add_usage(8000)  # Total 80K

    assert manager.get_zone() == 'orange'  # 80K / 96K = 83.3%

    # Checkpoint and reset
    status_before = manager.get_status()
    manager.reset()

    assert manager.used_tokens() == 0
    assert manager.get_zone() == 'green'

    # Configuration preserved
    assert manager.max_tokens == status_before['max_tokens']
    assert manager.utilization_limit == status_before['utilization_limit']


# ============================================================================
# Test: Error Handling and Edge Cases
# ============================================================================

def test_configuration_error_handling():
    """Test error handling in configuration flow."""
    # Invalid config file
    with pytest.raises(Exception):  # ModelConfigurationError
        ModelConfigLoader('nonexistent.yaml')

    # Invalid model reference
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'llm_models': {}}, f)
        temp_file = Path(f.name)

    loader = ModelConfigLoader(str(temp_file))

    with pytest.raises(Exception):  # ModelConfigurationError
        loader.get_model('nonexistent_model')


def test_detection_fallback_chain(temp_models_file):
    """Test detection fallback chain."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_model('medium_local')

    detector = ContextWindowDetector(fallback_size=16384)

    # Detection chain:
    # 1. API (will fail - not mocked) →
    # 2. Known contexts (has qwen2.5-coder:32b) →
    # 3. Config (128000) →
    # 4. Fallback (16384)

    size = detector.detect(
        config['provider'],
        config['model'],
        model_config=config
    )

    # Should use known contexts (128000) or config
    assert size in [128000, 16384]


# ============================================================================
# Test: Status and Monitoring
# ============================================================================

def test_status_reporting(temp_models_file):
    """Test comprehensive status reporting."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_active_orchestrator_config()

    manager = ContextWindowManager(config, utilization_limit=0.75)
    manager.add_usage(60000)

    status = manager.get_status()

    # Verify all expected fields
    assert status['model'] == 'qwen2.5-coder:32b'
    assert status['max_tokens'] == 128000
    assert status['utilization_limit'] == 0.75
    assert status['effective_max_tokens'] == 96000
    assert status['used_tokens'] == 60000
    assert status['available_tokens'] == 36000
    assert 0.6 < status['usage_percentage'] < 0.7
    assert status['zone'] == 'yellow'
    assert 'thresholds' in status


def test_active_model_selection(temp_models_file):
    """Test active model selection for different roles."""
    loader = ModelConfigLoader(str(temp_models_file))

    # Orchestrator uses medium local model
    orch_config = loader.get_active_orchestrator_config()
    assert orch_config['model'] == 'qwen2.5-coder:32b'
    assert orch_config['provider'] == 'ollama'

    # Implementer uses cloud model
    impl_config = loader.get_active_implementer_config()
    assert impl_config['model'] == 'claude-3-5-sonnet-20241022'
    assert impl_config['provider'] == 'anthropic'


# ============================================================================
# Test: Performance and Scalability
# ============================================================================

def test_large_scale_usage_tracking(temp_models_file):
    """Test usage tracking with many operations."""
    loader = ModelConfigLoader(str(temp_models_file))
    config = loader.get_active_orchestrator_config()

    manager = ContextWindowManager(config)

    # Simulate 150 operations to exceed green zone (need >50% of 128K = >64K)
    for i in range(150):
        manager.add_usage(500)  # Total 75,000 tokens

    assert manager.used_tokens() == 75000
    assert manager.get_zone() == 'yellow'  # 75K / 128K = 58.6% (>50% threshold)


def test_concurrent_config_access():
    """Test thread-safe access to configuration."""
    # This is primarily a ContextWindowManager test, but validates
    # that the full integration is thread-safe

    config = {'model': 'test', 'context_window': 100000}
    manager = ContextWindowManager(config)

    import threading
    errors = []

    def concurrent_operations():
        try:
            for _ in range(5):
                manager.add_usage(100)
                _ = manager.get_zone()
                _ = manager.get_status()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=concurrent_operations) for _ in range(3)]

    for t in threads:
        t.start()

    for t in threads:
        t.join(timeout=5.0)

    assert len(errors) == 0
    assert manager.used_tokens() == 1500  # 3 threads × 5 ops × 100 tokens
