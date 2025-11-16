"""Unit tests for model configuration loader.

Tests cover:
- Configuration loading and validation
- Schema validation
- Model retrieval methods
- Error handling
- Edge cases

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, Any
import yaml

from src.core.model_config_loader import (
    ModelConfigLoader,
    ModelConfigurationError
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def valid_config() -> Dict[str, Any]:
    """Create a valid model configuration for testing."""
    return {
        'llm_models': {
            'test_small': {
                'provider': 'ollama',
                'model': 'test-small:4k',
                'context_window': 4096,
                'optimization_profile': 'ultra-aggressive',
                'cost_per_1m_input_tokens': 0,
                'cost_per_1m_output_tokens': 0
            },
            'test_medium': {
                'provider': 'ollama',
                'model': 'test-medium:128k',
                'context_window': 128000,
                'optimization_profile': 'balanced',
                'cost_per_1m_input_tokens': 0,
                'cost_per_1m_output_tokens': 0
            },
            'test_cloud': {
                'provider': 'anthropic',
                'model': 'test-cloud',
                'context_window': 200000,
                'optimization_profile': 'balanced',
                'cost_per_1m_input_tokens': 3.00,
                'cost_per_1m_output_tokens': 15.00,
                'supports_prompt_caching': True
            }
        },
        'active_orchestrator_model': 'test_medium',
        'active_implementer_model': 'test_cloud',
        'optimization_profiles': {
            'ultra-aggressive': {
                'context_range': [4096, 8192],
                'summarization_threshold': 100
            },
            'balanced': {
                'context_range': [100001, 250000],
                'summarization_threshold': 500
            }
        }
    }


@pytest.fixture
def temp_config_file(valid_config) -> Path:
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.yaml',
        delete=False
    ) as f:
        yaml.dump(valid_config, f)
        return Path(f.name)


@pytest.fixture
def loader(temp_config_file) -> ModelConfigLoader:
    """Create a ModelConfigLoader with valid configuration."""
    return ModelConfigLoader(str(temp_config_file))


# ============================================================================
# Test: Initialization and Loading
# ============================================================================

def test_init_with_valid_config(temp_config_file):
    """Test initialization with valid configuration file."""
    loader = ModelConfigLoader(str(temp_config_file))

    assert len(loader.models) == 3
    assert 'test_small' in loader.models
    assert 'test_medium' in loader.models
    assert 'test_cloud' in loader.models
    assert loader.active_orchestrator_model == 'test_medium'
    assert loader.active_implementer_model == 'test_cloud'


def test_init_with_missing_file():
    """Test initialization with non-existent file."""
    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader('nonexistent.yaml')

    assert 'not found' in str(exc_info.value)
    assert 'nonexistent.yaml' in str(exc_info.value)


def test_init_with_invalid_yaml():
    """Test initialization with invalid YAML syntax."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: syntax:\n  - broken")
        invalid_file = Path(f.name)

    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader(str(invalid_file))

    assert 'Invalid YAML syntax' in str(exc_info.value)


def test_init_without_llm_models_key():
    """Test initialization with missing 'llm_models' key."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'some_other_key': {}}, f)
        invalid_file = Path(f.name)

    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader(str(invalid_file))

    assert "Missing required key: 'llm_models'" in str(exc_info.value)


# ============================================================================
# Test: Model Retrieval
# ============================================================================

def test_get_model_success(loader):
    """Test retrieving a model by ID."""
    model = loader.get_model('test_small')

    assert model['provider'] == 'ollama'
    assert model['model'] == 'test-small:4k'
    assert model['context_window'] == 4096
    assert model['optimization_profile'] == 'ultra-aggressive'


def test_get_model_returns_copy(loader):
    """Test that get_model returns a copy, not reference."""
    model1 = loader.get_model('test_small')
    model2 = loader.get_model('test_small')

    # Modify one
    model1['context_window'] = 999999

    # Other should be unchanged
    assert model2['context_window'] == 4096


def test_get_model_not_found(loader):
    """Test retrieving non-existent model."""
    with pytest.raises(ModelConfigurationError) as exc_info:
        loader.get_model('nonexistent_model')

    assert 'not found' in str(exc_info.value)
    assert 'Available models:' in str(exc_info.value)


def test_get_active_orchestrator_config(loader):
    """Test retrieving active orchestrator configuration."""
    config = loader.get_active_orchestrator_config()

    assert config['provider'] == 'ollama'
    assert config['model'] == 'test-medium:128k'
    assert config['context_window'] == 128000


def test_get_active_implementer_config(loader):
    """Test retrieving active implementer configuration."""
    config = loader.get_active_implementer_config()

    assert config['provider'] == 'anthropic'
    assert config['model'] == 'test-cloud'
    assert config['context_window'] == 200000
    assert config['supports_prompt_caching'] is True


def test_get_active_config_when_not_set():
    """Test retrieving active config when not set in configuration."""
    config = {'llm_models': {
        'test': {
            'provider': 'ollama',
            'model': 'test',
            'context_window': 4096
        }
    }}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        temp_file = Path(f.name)

    loader = ModelConfigLoader(str(temp_file))

    with pytest.raises(ModelConfigurationError) as exc_info:
        loader.get_active_orchestrator_config()

    assert 'No active orchestrator model configured' in str(exc_info.value)


# ============================================================================
# Test: Listing and Filtering
# ============================================================================

def test_list_models(loader):
    """Test listing all model IDs."""
    models = loader.list_models()

    assert len(models) == 3
    assert 'test_small' in models
    assert 'test_medium' in models
    assert 'test_cloud' in models


def test_get_models_by_provider(loader):
    """Test filtering models by provider."""
    ollama_models = loader.get_models_by_provider('ollama')

    assert len(ollama_models) == 2
    assert 'test_small' in ollama_models
    assert 'test_medium' in ollama_models
    assert 'test_cloud' not in ollama_models


def test_get_models_by_provider_empty(loader):
    """Test filtering with provider that has no models."""
    openai_models = loader.get_models_by_provider('openai')

    assert len(openai_models) == 0


def test_get_models_by_context_range(loader):
    """Test filtering models by context window range."""
    # Models with 100K-250K context
    medium_models = loader.get_models_by_context_range(100000, 250000)

    assert len(medium_models) == 2
    assert 'test_medium' in medium_models
    assert 'test_cloud' in medium_models
    assert 'test_small' not in medium_models


def test_get_models_by_context_range_min_only(loader):
    """Test filtering with minimum context only."""
    large_models = loader.get_models_by_context_range(100000)

    assert len(large_models) == 2
    assert 'test_medium' in large_models
    assert 'test_cloud' in large_models


def test_get_models_by_context_range_no_matches(loader):
    """Test filtering with range that matches no models."""
    huge_models = loader.get_models_by_context_range(1000000)

    assert len(huge_models) == 0


# ============================================================================
# Test: Schema Validation
# ============================================================================

def test_validate_schema_valid(loader, valid_config):
    """Test schema validation with valid configuration."""
    assert loader.validate_schema(valid_config) is True


def test_validate_schema_missing_required_field():
    """Test schema validation with missing required field."""
    invalid_config = {
        'llm_models': {
            'test': {
                'provider': 'ollama',
                # Missing 'model' and 'context_window'
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        temp_file = Path(f.name)

    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader(str(temp_file))

    error_msg = str(exc_info.value)
    assert "missing required field 'model'" in error_msg
    assert "missing required field 'context_window'" in error_msg


def test_validate_schema_invalid_provider():
    """Test schema validation with invalid provider."""
    invalid_config = {
        'llm_models': {
            'test': {
                'provider': 'invalid_provider',
                'model': 'test',
                'context_window': 4096
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        temp_file = Path(f.name)

    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader(str(temp_file))

    assert 'invalid provider' in str(exc_info.value)
    assert 'invalid_provider' in str(exc_info.value)


def test_validate_schema_invalid_context_window():
    """Test schema validation with invalid context window."""
    invalid_config = {
        'llm_models': {
            'test': {
                'provider': 'ollama',
                'model': 'test',
                'context_window': -1000  # Invalid: negative
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        temp_file = Path(f.name)

    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader(str(temp_file))

    assert 'context_window must be a positive integer' in str(exc_info.value)


def test_validate_schema_invalid_optimization_profile():
    """Test schema validation with invalid optimization profile."""
    invalid_config = {
        'llm_models': {
            'test': {
                'provider': 'ollama',
                'model': 'test',
                'context_window': 4096,
                'optimization_profile': 'invalid-profile'
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        temp_file = Path(f.name)

    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader(str(temp_file))

    assert 'invalid optimization_profile' in str(exc_info.value)


def test_validate_schema_invalid_cost():
    """Test schema validation with invalid cost values."""
    invalid_config = {
        'llm_models': {
            'test': {
                'provider': 'ollama',
                'model': 'test',
                'context_window': 4096,
                'cost_per_1m_input_tokens': -5.0  # Invalid: negative
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(invalid_config, f)
        temp_file = Path(f.name)

    with pytest.raises(ModelConfigurationError) as exc_info:
        ModelConfigLoader(str(temp_file))

    assert 'cost_per_1m_input_tokens must be a non-negative number' in str(exc_info.value)


# ============================================================================
# Test: load_models Method
# ============================================================================

def test_load_models_from_different_path(loader):
    """Test loading models from a different configuration file."""
    # Create alternative config
    alt_config = {
        'llm_models': {
            'alt_model': {
                'provider': 'openai',
                'model': 'alt-test',
                'context_window': 16384
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(alt_config, f)
        alt_file = Path(f.name)

    # Load from alternative path
    models = loader.load_models(str(alt_file))

    assert len(models) == 1
    assert 'alt_model' in models
    assert models['alt_model']['provider'] == 'openai'


def test_load_models_invalid_path():
    """Test loading models from invalid path."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({'llm_models': {}}, f)
        temp_file = Path(f.name)

    loader = ModelConfigLoader(str(temp_file))

    with pytest.raises(ModelConfigurationError):
        loader.load_models('nonexistent.yaml')


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_empty_models_dict():
    """Test with empty models dictionary."""
    config = {'llm_models': {}}

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        temp_file = Path(f.name)

    loader = ModelConfigLoader(str(temp_file))

    assert len(loader.models) == 0
    assert loader.list_models() == []


def test_optional_fields_missing(loader):
    """Test that optional fields can be missing."""
    config = {
        'llm_models': {
            'minimal': {
                'provider': 'ollama',
                'model': 'minimal-model',
                'context_window': 4096
                # No optimization_profile, costs, etc.
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        temp_file = Path(f.name)

    loader = ModelConfigLoader(str(temp_file))
    model = loader.get_model('minimal')

    assert 'provider' in model
    assert 'model' in model
    assert 'context_window' in model
    # Optional fields may or may not be present
    assert model.get('optimization_profile') is None


def test_warning_for_missing_active_model_reference(caplog):
    """Test warning when active model references non-existent model."""
    config = {
        'llm_models': {
            'test': {
                'provider': 'ollama',
                'model': 'test',
                'context_window': 4096
            }
        },
        'active_orchestrator_model': 'nonexistent_model'
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        temp_file = Path(f.name)

    with caplog.at_level('WARNING'):
        ModelConfigLoader(str(temp_file))

    assert 'not found in models' in caplog.text


# ============================================================================
# Test: ModelConfigurationError
# ============================================================================

def test_model_configuration_error_with_all_params():
    """Test ModelConfigurationError with all parameters."""
    error = ModelConfigurationError(
        "Test error",
        config_path="test/path.yaml",
        validation_errors=["Error 1", "Error 2"]
    )

    error_str = str(error)
    assert "Test error" in error_str
    assert "test/path.yaml" in error_str
    assert "Error 1" in error_str
    assert "Error 2" in error_str


def test_model_configuration_error_minimal():
    """Test ModelConfigurationError with minimal parameters."""
    error = ModelConfigurationError("Simple error")

    assert str(error) == "Simple error"
    assert error.config_path is None
    assert error.validation_errors == []


# ============================================================================
# Test: Constants and Class Attributes
# ============================================================================

def test_required_model_fields_constant():
    """Test that required fields constant is correct."""
    assert 'provider' in ModelConfigLoader.REQUIRED_MODEL_FIELDS
    assert 'model' in ModelConfigLoader.REQUIRED_MODEL_FIELDS
    assert 'context_window' in ModelConfigLoader.REQUIRED_MODEL_FIELDS


def test_valid_providers_constant():
    """Test that valid providers constant includes expected values."""
    assert 'ollama' in ModelConfigLoader.VALID_PROVIDERS
    assert 'anthropic' in ModelConfigLoader.VALID_PROVIDERS
    assert 'openai' in ModelConfigLoader.VALID_PROVIDERS


def test_valid_optimization_profiles_constant():
    """Test that valid optimization profiles are defined."""
    expected_profiles = [
        'ultra-aggressive',
        'aggressive',
        'balanced-aggressive',
        'balanced',
        'minimal'
    ]

    for profile in expected_profiles:
        assert profile in ModelConfigLoader.VALID_OPTIMIZATION_PROFILES
