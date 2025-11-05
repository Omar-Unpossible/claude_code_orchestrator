"""Comprehensive tests for configuration validation (Task 5.5).

Tests validate configuration values and rules:
- Context window thresholds (0.0-1.0, ordered)
- Max turns bounds (min/default/max, retry_multiplier)
- Timeout values (positive integers)
- Confidence and quality thresholds (0-100)
- Breakpoint configuration
- LLM configuration
- Agent configuration

Covers validation rules, error messages, and edge cases.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, Mock

from src.core.config import Config
from src.core.exceptions import ConfigValidationException


@pytest.fixture(autouse=True)
def reset_config():
    """Reset Config singleton before and after each test."""
    Config.reset()
    yield
    Config.reset()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory with default config."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    default_config = {
        'llm': {'type': 'ollama', 'model': 'qwen2.5-coder:32b'},
        'agent': {'type': 'claude-code-local', 'timeout': 120},
        'database': {'url': 'sqlite:///:memory:'},
        'orchestration': {'max_iterations': 50},
        'context': {'max_tokens': 8000},
        'validation': {'quality': {'threshold': 70}},
        'confidence': {'threshold': 50},
    }

    with open(config_dir / 'default_config.yaml', 'w') as f:
        yaml.dump(default_config, f)

    return config_dir


# ============================================================================
# CONTEXT WINDOW THRESHOLD VALIDATION
# ============================================================================

class TestContextThresholdValidation:
    """Tests for context window threshold validation."""

    def test_valid_thresholds(self, temp_config_dir):
        """Test valid context threshold configuration."""
        config_data = {
            'context': {
                'thresholds': {
                    'warning': 0.70,
                    'refresh': 0.80,
                    'critical': 0.95
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()
            assert config.get('context.thresholds.warning') == 0.70
            assert config.get('context.thresholds.refresh') == 0.80
            assert config.get('context.thresholds.critical') == 0.95

    def test_threshold_below_zero(self, temp_config_dir):
        """Test that negative threshold is rejected."""
        config_data = {
            'context': {
                'thresholds': {
                    'warning': -0.10,
                    'refresh': 0.80,
                    'critical': 0.95
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'context.thresholds.warning' in str(exc_info.value)

    def test_threshold_above_one(self, temp_config_dir):
        """Test that threshold > 1.0 is rejected."""
        config_data = {
            'context': {
                'thresholds': {
                    'warning': 0.70,
                    'refresh': 0.80,
                    'critical': 1.5
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'context.thresholds.critical' in str(exc_info.value)

    def test_threshold_ordering_violated(self, temp_config_dir):
        """Test that unordered thresholds are rejected."""
        config_data = {
            'context': {
                'thresholds': {
                    'warning': 0.95,  # Should be smallest
                    'refresh': 0.80,
                    'critical': 0.70  # Should be largest
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            assert 'warning < refresh < critical' in error_msg

    def test_threshold_not_number(self, temp_config_dir):
        """Test that non-numeric threshold is rejected."""
        config_data = {
            'context': {
                'thresholds': {
                    'warning': 'high',  # Should be number
                    'refresh': 0.80,
                    'critical': 0.95
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'context.thresholds.warning' in str(exc_info.value)


# ============================================================================
# MAX TURNS VALIDATION
# ============================================================================

class TestMaxTurnsValidation:
    """Tests for max_turns configuration validation."""

    def test_valid_max_turns(self, temp_config_dir):
        """Test valid max_turns configuration."""
        config_data = {
            'orchestration': {
                'max_turns': {
                    'min': 3,
                    'default': 10,
                    'max': 30,
                    'retry_multiplier': 2.0
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()
            assert config.get('orchestration.max_turns.min') == 3

    def test_min_less_than_three(self, temp_config_dir):
        """Test that min < 3 is rejected."""
        config_data = {
            'orchestration': {
                'max_turns': {
                    'min': 2,  # Too small
                    'default': 10,
                    'max': 30
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            assert 'orchestration.max_turns.min' in error_msg
            assert '>= 3' in error_msg

    def test_max_greater_than_thirty(self, temp_config_dir):
        """Test that max > 30 is rejected."""
        config_data = {
            'orchestration': {
                'max_turns': {
                    'min': 3,
                    'default': 10,
                    'max': 50  # Too large
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            assert 'orchestration.max_turns.max' in error_msg
            assert '<= 30' in error_msg

    def test_default_outside_bounds(self, temp_config_dir):
        """Test that default outside min/max is rejected."""
        config_data = {
            'orchestration': {
                'max_turns': {
                    'min': 3,
                    'default': 35,  # Exceeds max
                    'max': 30
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'orchestration.max_turns.default' in str(exc_info.value)

    def test_retry_multiplier_less_than_one(self, temp_config_dir):
        """Test that retry_multiplier < 1.0 is rejected."""
        config_data = {
            'orchestration': {
                'max_turns': {
                    'min': 3,
                    'default': 10,
                    'max': 30,
                    'retry_multiplier': 0.5  # Too small
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            assert 'retry_multiplier' in error_msg


# ============================================================================
# TIMEOUT VALIDATION
# ============================================================================

class TestTimeoutValidation:
    """Tests for timeout configuration validation."""

    def test_valid_timeouts(self, temp_config_dir):
        """Test valid timeout configuration."""
        config_data = {
            'agent': {'timeout': 120},
            'orchestration': {
                'iteration_timeout': 300,
                'task_timeout': 3600
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()
            assert config.get('agent.timeout') == 120

    def test_timeout_not_integer(self, temp_config_dir):
        """Test that non-integer timeout is rejected."""
        config_data = {
            'agent': {'timeout': '120'}  # String instead of int
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'agent.timeout' in str(exc_info.value)

    def test_response_timeout_below_minimum(self, temp_config_dir):
        """Test that response_timeout < 60 is rejected."""
        config_data = {
            'agent': {
                'local': {'response_timeout': 30}  # Minimum is 60
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            assert 'response_timeout' in error_msg


# ============================================================================
# CONFIDENCE AND QUALITY THRESHOLD VALIDATION
# ============================================================================

class TestThresholdValidation:
    """Tests for confidence and quality thresholds."""

    def test_valid_confidence_threshold(self, temp_config_dir):
        """Test valid confidence threshold."""
        config_data = {
            'confidence': {'threshold': 50}
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()
            assert config.get('confidence.threshold') == 50

    def test_confidence_threshold_below_zero(self, temp_config_dir):
        """Test that negative confidence is rejected."""
        config_data = {
            'confidence': {'threshold': -10}
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'confidence.threshold' in str(exc_info.value)

    def test_confidence_threshold_above_100(self, temp_config_dir):
        """Test that confidence > 100 is rejected."""
        config_data = {
            'confidence': {'threshold': 150}
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'confidence.threshold' in str(exc_info.value)

    def test_valid_quality_threshold(self, temp_config_dir):
        """Test valid quality threshold."""
        config_data = {
            'validation': {'quality': {'threshold': 75}}
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()
            assert config.get('validation.quality.threshold') == 75


# ============================================================================
# AGENT CONFIGURATION VALIDATION
# ============================================================================

class TestAgentConfigValidation:
    """Tests for agent configuration validation."""

    def test_valid_agent_type(self):
        """Test valid agent types (basic validation, not full config load)."""
        from src.core.config import Config as ConfigClass

        # Create a temporary instance and test validation directly
        config_obj = ConfigClass()
        config_obj._config = {
            'agent': {'type': 'claude-code-local'},
            'llm': {'model': 'test'},
            'confidence': {'threshold': 50},
            'validation': {'quality': {'threshold': 70}}
        }

        # Should not raise
        config_obj._validate_agent_config()
        assert True

    def test_invalid_agent_type(self, temp_config_dir):
        """Test that invalid agent type is rejected."""
        config_data = {'agent': {'type': 'invalid-agent'}}

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            assert 'agent.type' in error_msg

    def test_agent_max_retries_negative(self, temp_config_dir):
        """Test that negative max_retries is rejected."""
        config_data = {'agent': {'max_retries': -1}}

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'agent.max_retries' in str(exc_info.value)


# ============================================================================
# LLM CONFIGURATION VALIDATION
# ============================================================================

class TestLLMConfigValidation:
    """Tests for LLM configuration validation."""

    def test_valid_llm_config(self, temp_config_dir):
        """Test valid LLM configuration."""
        config_data = {
            'llm': {
                'temperature': 0.7,
                'max_tokens': 4096,
                'context_length': 32768
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()
            assert config.get('llm.temperature') == 0.7

    def test_temperature_below_zero(self, temp_config_dir):
        """Test that temperature < 0 is rejected."""
        config_data = {
            'llm': {'temperature': -0.5}
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'llm.temperature' in str(exc_info.value)

    def test_temperature_above_two(self, temp_config_dir):
        """Test that temperature > 2.0 is rejected."""
        config_data = {
            'llm': {'temperature': 3.0}
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            assert 'llm.temperature' in error_msg

    def test_max_tokens_negative(self, temp_config_dir):
        """Test that negative max_tokens is rejected."""
        config_data = {
            'llm': {'max_tokens': -1000}
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'llm.max_tokens' in str(exc_info.value)


# ============================================================================
# BREAKPOINT CONFIGURATION VALIDATION
# ============================================================================

class TestBreakpointValidation:
    """Tests for breakpoint configuration validation."""

    def test_valid_breakpoint_thresholds(self, temp_config_dir):
        """Test valid breakpoint thresholds."""
        config_data = {
            'breakpoints': {
                'triggers': {
                    'low_confidence': {'threshold': 30},
                    'quality_too_low': {'threshold': 50},
                    'validation_failed': {'max_retries': 3}
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()
            assert config.get('breakpoints.triggers.low_confidence.threshold') == 30

    def test_low_confidence_threshold_invalid(self, temp_config_dir):
        """Test that invalid low_confidence threshold is rejected."""
        config_data = {
            'breakpoints': {
                'triggers': {
                    'low_confidence': {'threshold': 150}  # > 100
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            assert 'low_confidence' in str(exc_info.value)


# ============================================================================
# ERROR MESSAGE QUALITY
# ============================================================================

class TestErrorMessageQuality:
    """Tests for helpful error messages."""

    def test_error_message_includes_recovery_suggestion(self, temp_config_dir):
        """Test that error messages include helpful information."""
        config_data = {
            'context': {
                'thresholds': {
                    'warning': 0.95,
                    'refresh': 0.80,
                    'critical': 0.70
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            error_msg = str(exc_info.value)
            # Error should mention the issue and recovery info is in exception context
            assert 'context.thresholds' in error_msg or 'warning' in error_msg
            # Check that recovery suggestion is in the exception object
            assert exc_info.value.recovery_suggestion is not None

    def test_error_includes_config_key(self, temp_config_dir):
        """Test that error messages include the problematic config key."""
        config_data = {
            'orchestration': {
                'max_turns': {
                    'max': 50  # Too large
                }
            }
        }

        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(config_data, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigValidationException) as exc_info:
                Config.load()

            # Error should mention the specific key
            assert 'max_turns.max' in str(exc_info.value)
