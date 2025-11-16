"""Unit tests for context window detector.

Tests cover:
- API detection for Ollama, Anthropic, OpenAI
- Fallback mechanisms
- Known context windows
- Error handling
- Edge cases

All API calls are mocked to avoid network dependencies.

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.orchestration.memory.context_window_detector import (
    ContextWindowDetector,
    ContextDetectionError
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def detector() -> ContextWindowDetector:
    """Create a ContextWindowDetector instance."""
    return ContextWindowDetector(fallback_size=16384)


@pytest.fixture
def ollama_response_with_num_ctx() -> dict:
    """Mock Ollama API response with num_ctx in modelfile."""
    return {
        'modelfile': 'FROM qwen2.5-coder:32b\nPARAMETER num_ctx 128000\nPARAMETER temperature 0.7',
        'parameters': '',
        'template': '',
        'details': {
            'family': 'qwen2',
            'parameter_size': '32B'
        }
    }


@pytest.fixture
def ollama_response_with_model_info() -> dict:
    """Mock Ollama API response with context_length in model_info."""
    return {
        'modelfile': 'FROM model',
        'model_info': {
            'context_length': 200000,
            'architecture': 'transformer'
        }
    }


@pytest.fixture
def ollama_response_no_context() -> dict:
    """Mock Ollama API response without context information."""
    return {
        'modelfile': 'FROM model',
        'details': {
            'family': 'test',
            'parameter_size': '7B'
        }
    }


# ============================================================================
# Test: Initialization
# ============================================================================

def test_init_with_defaults():
    """Test initialization with default parameters."""
    detector = ContextWindowDetector()

    assert detector.fallback_size == 16384
    assert detector.timeout == 5
    assert 'localhost' in detector.ollama_base_url or '127.0.0.1' in detector.ollama_base_url


def test_init_with_custom_params():
    """Test initialization with custom parameters."""
    detector = ContextWindowDetector(
        fallback_size=32000,
        timeout=10,
        ollama_base_url='http://custom:11434'
    )

    assert detector.fallback_size == 32000
    assert detector.timeout == 10
    assert detector.ollama_base_url == 'http://custom:11434'


def test_init_strips_trailing_slash():
    """Test that trailing slash is stripped from Ollama URL."""
    detector = ContextWindowDetector(
        ollama_base_url='http://localhost:11434/'
    )

    assert detector.ollama_base_url == 'http://localhost:11434'


def test_init_with_invalid_fallback():
    """Test initialization with invalid fallback size."""
    with pytest.raises(ValueError) as exc_info:
        ContextWindowDetector(fallback_size=-1000)

    assert 'fallback_size must be positive' in str(exc_info.value)


@patch.dict('os.environ', {'OLLAMA_BASE_URL': 'http://env:11434'})
def test_init_uses_environment_variable():
    """Test that OLLAMA_BASE_URL environment variable is used."""
    detector = ContextWindowDetector()

    assert detector.ollama_base_url == 'http://env:11434'


# ============================================================================
# Test: Ollama Detection
# ============================================================================

@patch('requests.post')
def test_detect_ollama_success_with_num_ctx(
    mock_post,
    detector,
    ollama_response_with_num_ctx
):
    """Test successful Ollama detection with num_ctx in modelfile."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = ollama_response_with_num_ctx
    mock_post.return_value = mock_response

    size = detector.detect('ollama', 'qwen2.5-coder:32b')

    assert size == 128000
    mock_post.assert_called_once()


@patch('requests.post')
def test_detect_ollama_success_with_model_info(
    mock_post,
    detector,
    ollama_response_with_model_info
):
    """Test successful Ollama detection with model_info."""
    mock_response = Mock()
    mock_response.json.return_value = ollama_response_with_model_info
    mock_post.return_value = mock_response

    size = detector.detect('ollama', 'test-model')

    assert size == 200000


@patch('requests.post')
def test_detect_ollama_no_context_falls_back_to_known(
    mock_post,
    detector,
    ollama_response_no_context
):
    """Test Ollama detection falls back to known values when API doesn't return context."""
    mock_response = Mock()
    mock_response.json.return_value = ollama_response_no_context
    mock_post.return_value = mock_response

    # Use a model that's in KNOWN_CONTEXT_WINDOWS
    size = detector.detect('ollama', 'qwen2.5-coder:32b')

    assert size == 128000  # From KNOWN_CONTEXT_WINDOWS


@patch('requests.post')
def test_detect_ollama_request_exception(mock_post, detector):
    """Test Ollama detection handles request exceptions."""
    mock_post.side_effect = requests.RequestException("Connection error")

    # Should fall back to known values
    size = detector.detect('ollama', 'qwen2.5-coder:32b')

    assert size == 128000  # From KNOWN_CONTEXT_WINDOWS


@patch('requests.post')
def test_detect_ollama_http_error(mock_post, detector):
    """Test Ollama detection handles HTTP errors."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
    mock_post.return_value = mock_response

    # Should fall back to known values
    size = detector.detect('ollama', 'qwen2.5-coder:32b')

    assert size == 128000


@patch('requests.post')
def test_detect_ollama_invalid_json(mock_post, detector):
    """Test Ollama detection handles invalid JSON response."""
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_post.return_value = mock_response

    # Should fall back to known values
    size = detector.detect('ollama', 'qwen2.5-coder:32b')

    assert size == 128000


# ============================================================================
# Test: Anthropic Detection
# ============================================================================

def test_detect_anthropic_known_model(detector):
    """Test Anthropic detection with known model."""
    size = detector.detect('anthropic', 'claude-3-5-sonnet-20241022')

    assert size == 200000


def test_detect_anthropic_pattern_match_claude_3(detector):
    """Test Anthropic detection with Claude 3 pattern matching."""
    size = detector.detect('anthropic', 'claude-3-opus-latest')

    assert size == 200000


def test_detect_anthropic_pattern_match_claude_3_5(detector):
    """Test Anthropic detection with Claude 3.5 pattern matching."""
    size = detector.detect('anthropic', 'claude-3-5-haiku-custom')

    assert size == 200000


def test_detect_anthropic_unknown_model_with_config(detector):
    """Test Anthropic detection with unknown model but config provided."""
    model_config = {'context_window': 250000}

    size = detector.detect('anthropic', 'unknown-model', model_config=model_config)

    assert size == 250000


def test_detect_anthropic_unknown_model_without_config(detector):
    """Test Anthropic detection with unknown model and no config."""
    size = detector.detect('anthropic', 'future-model')

    assert size == 16384  # Fallback


# ============================================================================
# Test: OpenAI Detection
# ============================================================================

def test_detect_openai_known_model(detector):
    """Test OpenAI detection with known model."""
    size = detector.detect('openai', 'gpt-4-turbo')

    assert size == 128000


def test_detect_openai_pattern_match_gpt4_turbo(detector):
    """Test OpenAI detection with GPT-4 Turbo pattern matching."""
    size = detector.detect('openai', 'gpt-4-turbo-2024-04-09')

    assert size == 128000


def test_detect_openai_pattern_match_gpt4_1106(detector):
    """Test OpenAI detection with GPT-4-1106 pattern matching."""
    size = detector.detect('openai', 'gpt-4-1106-preview')

    assert size == 128000


def test_detect_openai_pattern_match_gpt4(detector):
    """Test OpenAI detection with GPT-4 pattern matching."""
    size = detector.detect('openai', 'gpt-4-0613')

    assert size == 8192


def test_detect_openai_pattern_match_gpt35(detector):
    """Test OpenAI detection with GPT-3.5-turbo pattern matching."""
    size = detector.detect('openai', 'gpt-3.5-turbo-0125')

    assert size == 16385


def test_detect_openai_unknown_model_with_config(detector):
    """Test OpenAI detection with unknown model but config provided."""
    model_config = {'context_window': 64000}

    size = detector.detect('openai', 'gpt-5-turbo', model_config=model_config)

    assert size == 64000


def test_detect_openai_unknown_model_without_config(detector):
    """Test OpenAI detection with unknown model and no config."""
    size = detector.detect('openai', 'future-gpt')

    assert size == 16384  # Fallback


# ============================================================================
# Test: Known Context Windows
# ============================================================================

def test_known_context_windows_ollama(detector):
    """Test detection using known Ollama context windows."""
    test_cases = [
        ('phi3:mini', 4096),
        ('qwen2.5-coder:3b', 8192),
        ('qwen2.5-coder:7b', 16384),
        ('qwen2.5-coder:32b', 128000),
    ]

    for model, expected_size in test_cases:
        size = detector.detect('ollama', model)
        assert size == expected_size, f"Failed for {model}"


def test_known_context_windows_anthropic(detector):
    """Test detection using known Anthropic context windows."""
    test_cases = [
        ('claude-3-5-sonnet-20241022', 200000),
        ('claude-3-5-haiku-20241022', 200000),
        ('claude-3-opus-20240229', 200000),
    ]

    for model, expected_size in test_cases:
        size = detector.detect('anthropic', model)
        assert size == expected_size, f"Failed for {model}"


def test_known_context_windows_openai(detector):
    """Test detection using known OpenAI context windows."""
    test_cases = [
        ('gpt-4-turbo', 128000),
        ('gpt-4', 8192),
        ('gpt-3.5-turbo', 16385),
    ]

    for model, expected_size in test_cases:
        size = detector.detect('openai', model)
        assert size == expected_size, f"Failed for {model}"


# ============================================================================
# Test: Fallback Mechanisms
# ============================================================================

def test_fallback_to_model_config(detector):
    """Test fallback to model_config when detection fails."""
    model_config = {'context_window': 75000}

    size = detector.detect('unknown_provider', 'unknown_model', model_config=model_config)

    assert size == 75000


def test_fallback_to_default_size(detector):
    """Test fallback to default size when all else fails."""
    size = detector.detect('unknown_provider', 'unknown_model')

    assert size == 16384


def test_fallback_with_custom_default():
    """Test fallback with custom default size."""
    detector = ContextWindowDetector(fallback_size=32000)

    size = detector.detect('unknown_provider', 'unknown_model')

    assert size == 32000


# ============================================================================
# Test: Case Insensitivity
# ============================================================================

def test_detect_case_insensitive_provider(detector):
    """Test that provider names are case-insensitive."""
    size_lower = detector.detect('ollama', 'qwen2.5-coder:32b')
    size_upper = detector.detect('OLLAMA', 'qwen2.5-coder:32b')
    size_mixed = detector.detect('Ollama', 'qwen2.5-coder:32b')

    assert size_lower == size_upper == size_mixed == 128000


# ============================================================================
# Test: update_known_contexts
# ============================================================================

def test_update_known_contexts_new_provider(detector):
    """Test adding a new provider to known contexts."""
    detector.update_known_contexts('custom_provider', 'custom_model', 64000)

    size = detector.detect('custom_provider', 'custom_model')

    assert size == 64000


def test_update_known_contexts_existing_provider(detector):
    """Test adding a new model to existing provider."""
    detector.update_known_contexts('ollama', 'new_model', 48000)

    size = detector.detect('ollama', 'new_model')

    assert size == 48000


def test_update_known_contexts_override_existing(detector):
    """Test overriding existing known context."""
    # Use a different model to avoid affecting other tests
    # Original value (not in known contexts, uses fallback)
    original = detector.detect('ollama', 'custom-test-model')
    assert original == 16384  # Fallback

    # Add to known contexts
    detector.update_known_contexts('ollama', 'custom-test-model', 64000)

    # New value
    updated = detector.detect('ollama', 'custom-test-model')
    assert updated == 64000

    # Override again
    detector.update_known_contexts('ollama', 'custom-test-model', 128000)

    # Verify override
    final = detector.detect('ollama', 'custom-test-model')
    assert final == 128000


# ============================================================================
# Test: ContextDetectionError
# ============================================================================

def test_context_detection_error_all_params():
    """Test ContextDetectionError with all parameters."""
    original_error = ValueError("Original")

    error = ContextDetectionError(
        "Test error",
        provider='ollama',
        model='test-model',
        original_error=original_error
    )

    error_str = str(error)
    assert "Test error" in error_str
    assert "provider: ollama" in error_str
    assert "model: test-model" in error_str
    assert "Original error:" in error_str


def test_context_detection_error_minimal():
    """Test ContextDetectionError with minimal parameters."""
    error = ContextDetectionError("Simple error")

    assert str(error) == "Simple error"
    assert error.provider is None
    assert error.model is None
    assert error.original_error is None


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_detect_with_empty_model_name(detector):
    """Test detection with empty model name."""
    size = detector.detect('ollama', '')

    assert size == 16384  # Falls back to default


def test_detect_with_none_model_config(detector):
    """Test detection with None model_config."""
    size = detector.detect('ollama', 'qwen2.5-coder:32b', model_config=None)

    assert size == 128000  # Falls back to known context windows


def test_detect_with_empty_model_config(detector):
    """Test detection with empty model_config dict."""
    size = detector.detect('ollama', 'qwen2.5-coder:32b', model_config={})

    assert size == 128000  # Falls back to known context windows


@patch('requests.post')
def test_detect_ollama_timeout(mock_post, detector):
    """Test Ollama detection handles timeout."""
    mock_post.side_effect = requests.Timeout("Request timed out")

    size = detector.detect('ollama', 'qwen2.5-coder:32b')

    assert size == 128000  # Falls back to known context windows


@patch('requests.post')
def test_detect_ollama_malformed_modelfile(mock_post, detector):
    """Test Ollama detection handles malformed modelfile."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'modelfile': 'INVALID FORMAT\nPARAMETER num_ctx not_a_number'
    }
    mock_post.return_value = mock_response

    size = detector.detect('ollama', 'qwen2.5-coder:32b')

    assert size == 128000  # Falls back to known context windows
