"""Tests for LocalLLMInterface.

This module tests the Ollama integration including:
- Connection and initialization
- Generation (streaming and non-streaming)
- Caching behavior
- Retry logic with exponential backoff
- Token counting
- Health checks
- Performance metrics
"""

import json
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Iterator

from src.llm.local_interface import LocalLLMInterface
from src.plugins.exceptions import (
    LLMConnectionException,
    LLMTimeoutException,
    LLMModelNotFoundException,
    LLMResponseException,
    LLMException
)


class TestLocalLLMInterfaceInitialization:
    """Test initialization and configuration."""

    def test_initialization_default_config(self):
        """Test initialization with default configuration."""
        llm = LocalLLMInterface()
        assert llm.config == {}
        assert llm.endpoint == ''
        assert llm.model == ''
        assert llm.metrics['calls'] == 0

    @patch('src.llm.local_interface.requests.get')
    @patch('src.llm.local_interface.requests.post')
    def test_initialize_with_config(self, mock_post, mock_get):
        """Test initialization with custom configuration."""
        # Mock health check
        mock_get.return_value.status_code = 200
        # Mock model list
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        llm = LocalLLMInterface()
        config = {
            'endpoint': 'http://test:1234',
            'model': 'test-model',
            'temperature': 0.5,
            'max_tokens': 2048,
            'timeout': 60
        }
        llm.initialize(config)

        assert llm.endpoint == 'http://test:1234'
        assert llm.model == 'test-model'
        assert llm.temperature == 0.5
        assert llm.max_tokens == 2048
        assert llm.timeout == 60

    @patch('src.llm.local_interface.requests.get')
    def test_initialize_connection_failure(self, mock_get):
        """Test initialization when Ollama is not available."""
        mock_get.side_effect = Exception("Connection refused")

        llm = LocalLLMInterface()
        with pytest.raises(LLMConnectionException) as exc_info:
            llm.initialize({'endpoint': 'http://localhost:11434'})

        assert 'Cannot connect to ollama' in str(exc_info.value)

    @patch('src.llm.local_interface.requests.get')
    def test_initialize_model_not_found(self, mock_get):
        """Test initialization when model is not available."""
        # Mock health check success
        mock_get.return_value.status_code = 200
        # Mock model list without the requested model
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'other-model'}]
        }

        llm = LocalLLMInterface()
        with pytest.raises(LLMModelNotFoundException) as exc_info:
            llm.initialize({
                'endpoint': 'http://localhost:11434',
                'model': 'missing-model'
            })

        assert 'missing-model' in str(exc_info.value)

    def test_config_merging_with_defaults(self):
        """Test that custom config merges with defaults."""
        with patch('src.llm.local_interface.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                'models': [{'name': 'test-model'}]
            }

            llm = LocalLLMInterface()
            llm.initialize({
                'model': 'test-model',
                'temperature': 0.8
            })

            # Custom value used
            assert llm.temperature == 0.8
            # Default values used for unspecified keys
            assert llm.endpoint == 'http://localhost:11434'
            assert llm.timeout == 120


class TestGeneration:
    """Test text generation functionality."""

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_success(self, mock_get, mock_post):
        """Test successful text generation."""
        # Mock initialization
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        # Mock generation
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Generated text response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        response = llm.generate("Test prompt")

        assert response == 'Generated text response'
        assert llm.metrics['calls'] == 1
        assert llm.metrics['total_tokens'] > 0

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_with_kwargs(self, mock_get, mock_post):
        """Test generation with custom parameters."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        llm.generate(
            "Test",
            temperature=0.9,
            max_tokens=100,
            top_p=0.95,
            system="You are helpful"
        )

        # Verify request payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']

        assert payload['options']['temperature'] == 0.9
        assert payload['options']['num_predict'] == 100
        assert payload['options']['top_p'] == 0.95
        assert payload['system'] == "You are helpful"

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_timeout(self, mock_get, mock_post):
        """Test generation timeout handling."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        # Mock timeout on all attempts
        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model', 'retry_attempts': 2})

        with pytest.raises(LLMTimeoutException) as exc_info:
            llm.generate("Test")

        assert llm.metrics['timeouts'] >= 1
        assert llm.metrics['errors'] >= 1

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_invalid_response(self, mock_get, mock_post):
        """Test handling of invalid response format."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        # Mock response without 'response' field
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'error': 'something'}

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model', 'retry_attempts': 1})

        with pytest.raises(LLMResponseException):
            llm.generate("Test")

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_empty_response(self, mock_get, mock_post):
        """Test handling of empty response."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        # Mock empty response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'response': ''}

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model', 'retry_attempts': 1})

        with pytest.raises(LLMResponseException):
            llm.generate("Test")


class TestStreaming:
    """Test streaming generation."""

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_stream_success(self, mock_get, mock_post):
        """Test successful streaming generation."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        # Mock streaming response
        mock_response = Mock()
        mock_response.status_code = 200

        # Simulate SSE stream
        stream_data = [
            json.dumps({'response': 'Hello', 'done': False}).encode(),
            json.dumps({'response': ' world', 'done': False}).encode(),
            json.dumps({'response': '!', 'done': True}).encode()
        ]
        mock_response.iter_lines.return_value = stream_data
        mock_post.return_value = mock_response

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        chunks = list(llm.generate_stream("Test"))

        assert chunks == ['Hello', ' world', '!']
        assert llm.metrics['calls'] == 1

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_stream_timeout(self, mock_get, mock_post):
        """Test streaming timeout handling."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        import requests
        mock_post.side_effect = requests.exceptions.Timeout()

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        with pytest.raises(LLMTimeoutException):
            list(llm.generate_stream("Test"))

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_generate_stream_malformed_json(self, mock_get, mock_post):
        """Test handling of malformed JSON in stream."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_response = Mock()
        mock_response.status_code = 200

        # Include malformed JSON that should be skipped
        stream_data = [
            json.dumps({'response': 'Hello', 'done': False}).encode(),
            b'invalid json',
            json.dumps({'response': ' world', 'done': True}).encode()
        ]
        mock_response.iter_lines.return_value = stream_data
        mock_post.return_value = mock_response

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        chunks = list(llm.generate_stream("Test"))

        # Malformed line is skipped
        assert chunks == ['Hello', ' world']


class TestCaching:
    """Test response caching functionality."""

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_cache_hit(self, mock_get, mock_post):
        """Test that identical requests use cache."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Cached response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        # First call - cache miss
        response1 = llm.generate("Same prompt")
        # Second call - should be cache hit
        response2 = llm.generate("Same prompt")

        assert response1 == response2
        # Should only make one actual request
        assert mock_post.call_count == 1

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_cache_different_prompts(self, mock_get, mock_post):
        """Test that different prompts don't use cache."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        llm.generate("First prompt")
        llm.generate("Second prompt")

        # Should make two requests
        assert mock_post.call_count == 2

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_cache_different_kwargs(self, mock_get, mock_post):
        """Test that different kwargs create different cache keys."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        llm.generate("Prompt", temperature=0.3)
        llm.generate("Prompt", temperature=0.7)

        # Different temperatures should create different cache keys
        assert mock_post.call_count == 2

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_clear_cache(self, mock_get, mock_post):
        """Test cache clearing."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        llm.generate("Prompt")
        llm.clear_cache()
        llm.generate("Prompt")

        # After clearing cache, should make two requests
        assert mock_post.call_count == 2


class TestRetryLogic:
    """Test retry logic with exponential backoff."""

    @patch('src.llm.local_interface.time.sleep')  # Mock sleep to speed up tests
    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_retry_on_failure(self, mock_get, mock_post, mock_sleep):
        """Test retry on transient failure."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        # Fail first two attempts, succeed on third
        import requests
        mock_post.side_effect = [
            requests.exceptions.RequestException("Error 1"),
            requests.exceptions.RequestException("Error 2"),
            Mock(
                status_code=200,
                json=lambda: {'response': 'Success'}
            )
        ]

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model', 'retry_attempts': 3})

        response = llm.generate("Test")

        assert response == 'Success'
        assert mock_post.call_count == 3
        # Verify exponential backoff (2 sleeps for 3 attempts)
        assert mock_sleep.call_count == 2

    @patch('src.llm.local_interface.time.sleep')
    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_retry_exhausted(self, mock_get, mock_post, mock_sleep):
        """Test all retries exhausted."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Persistent error")

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model', 'retry_attempts': 3})

        with pytest.raises(LLMException):
            llm.generate("Test")

        assert mock_post.call_count == 3
        assert llm.metrics['errors'] >= 1

    @patch('src.llm.local_interface.time.sleep')
    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_exponential_backoff(self, mock_get, mock_post, mock_sleep):
        """Test exponential backoff timing."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Error")

        llm = LocalLLMInterface()
        llm.initialize({
            'model': 'test-model',
            'retry_attempts': 3,
            'retry_backoff_base': 2.0
        })

        with pytest.raises(LLMException):
            llm.generate("Test")

        # Verify backoff times: 2^0=1, 2^1=2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0  # 2^0
        assert sleep_calls[1] == 2.0  # 2^1


class TestTokenCounting:
    """Test token estimation."""

    @patch('src.llm.local_interface.requests.get')
    def test_estimate_tokens_with_tiktoken(self, mock_get):
        """Test token estimation with tiktoken."""
        mock_get.return_value.status_code = 200

        llm = LocalLLMInterface()

        # Test with some text
        count = llm.estimate_tokens("Hello world")
        assert count > 0
        assert isinstance(count, int)

    @patch('src.llm.local_interface.requests.get')
    def test_estimate_tokens_empty_string(self, mock_get):
        """Test token estimation with empty string."""
        mock_get.return_value.status_code = 200

        llm = LocalLLMInterface()

        count = llm.estimate_tokens("")
        assert count == 0

    @patch('src.llm.local_interface.requests.get')
    def test_estimate_tokens_fallback(self, mock_get):
        """Test token estimation fallback when tiktoken fails."""
        mock_get.return_value.status_code = 200

        llm = LocalLLMInterface()
        # Force encoder to None to test fallback
        llm._encoder = None

        count = llm.estimate_tokens("word1 word2 word3")
        # Should use word-based estimation: 3 words * 1.3 = 3.9 -> 3
        assert count == 3


class TestHealthCheck:
    """Test health checking functionality."""

    @patch('src.llm.local_interface.requests.get')
    def test_is_available_success(self, mock_get):
        """Test health check when service is available."""
        mock_get.return_value.status_code = 200

        llm = LocalLLMInterface()
        llm.endpoint = 'http://localhost:11434'

        assert llm.is_available() is True

    @patch('src.llm.local_interface.requests.get')
    def test_is_available_failure(self, mock_get):
        """Test health check when service is unavailable."""
        mock_get.side_effect = Exception("Connection refused")

        llm = LocalLLMInterface()
        llm.endpoint = 'http://localhost:11434'

        assert llm.is_available() is False

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_warmup(self, mock_get, mock_post):
        """Test model warmup."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Warmup response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        # Reset call count after initialization
        mock_post.reset_mock()

        llm.warmup()

        # Warmup should make a generate call
        assert mock_post.call_count == 1

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_warmup_failure(self, mock_get, mock_post):
        """Test warmup with failure (should not raise)."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.side_effect = Exception("Warmup failed")

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        # Warmup failure should be logged but not raise
        llm.warmup()  # Should not raise


class TestModelInfo:
    """Test model information retrieval."""

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_get_model_info_success(self, mock_get, mock_post):
        """Test retrieving model information."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'modelfile': 'PARAMETER num_ctx 8192',
            'details': {
                'family': 'qwen',
                'quantization_level': 'Q4_K_M',
                'size': 20 * 1024 ** 3  # 20 GB
            }
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        info = llm.get_model_info()

        assert info['model_name'] == 'test-model'
        assert info['context_length'] == 8192
        assert info['family'] == 'qwen'
        assert info['quantization'] == 'Q4_K_M'
        assert info['size_gb'] == 20.0

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_get_model_info_failure(self, mock_get, mock_post):
        """Test model info retrieval with failure."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.side_effect = Exception("API error")

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        # Should return defaults instead of raising
        info = llm.get_model_info()

        assert info['model_name'] == 'test-model'
        assert info['context_length'] == 4096
        assert info['quantization'] == 'unknown'


class TestMetrics:
    """Test performance metrics tracking."""

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_metrics_tracking(self, mock_get, mock_post):
        """Test that metrics are tracked correctly."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Test response'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        # Make some calls
        llm.generate("Test 1")
        llm.generate("Test 2")

        metrics = llm.get_metrics()

        assert metrics['calls'] == 2
        assert metrics['total_tokens'] > 0
        assert metrics['total_latency_ms'] > 0
        assert metrics['errors'] == 0

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_metrics_derived_values(self, mock_get, mock_post):
        """Test calculated metrics."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Test'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        llm.generate("Test")

        metrics = llm.get_metrics()

        # Check derived metrics
        assert 'avg_latency_ms' in metrics
        assert 'tokens_per_second' in metrics
        assert 'cache_hit_rate' in metrics
        assert metrics['avg_latency_ms'] > 0

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_metrics_cache_hit_rate(self, mock_get, mock_post):
        """Test cache hit rate calculation."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Test'
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'test-model'})

        # First call - cache miss
        llm.generate("Same")
        # Second call - cache hit
        llm.generate("Same")

        metrics = llm.get_metrics()

        # Should have at least one hit and one miss
        assert metrics['cache_misses'] >= 1
        assert metrics['cache_hit_rate'] >= 0.0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @patch('src.llm.local_interface.requests.get')
    def test_make_cache_key_consistency(self, mock_get):
        """Test that cache keys are consistent."""
        mock_get.return_value.status_code = 200

        llm = LocalLLMInterface()

        key1 = llm._make_cache_key("prompt", {'temperature': 0.5})
        key2 = llm._make_cache_key("prompt", {'temperature': 0.5})

        assert key1 == key2

    @patch('src.llm.local_interface.requests.get')
    def test_make_cache_key_different(self, mock_get):
        """Test that different inputs produce different cache keys."""
        mock_get.return_value.status_code = 200

        llm = LocalLLMInterface()

        key1 = llm._make_cache_key("prompt1", {})
        key2 = llm._make_cache_key("prompt2", {})

        assert key1 != key2

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_list_models(self, mock_get, mock_post):
        """Test listing available models."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [
                {'name': 'model1'},
                {'name': 'model2'}
            ]
        }

        llm = LocalLLMInterface()
        llm.initialize({'model': 'model1'})

        models = llm._list_models()

        assert 'model1' in models
        assert 'model2' in models
        assert len(models) == 2

    @patch('src.llm.local_interface.requests.get')
    def test_endpoint_trailing_slash_removal(self, mock_get):
        """Test that trailing slashes are removed from endpoint."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test'}]
        }

        llm = LocalLLMInterface()
        llm.initialize({
            'endpoint': 'http://localhost:11434/',
            'model': 'test'
        })

        assert llm.endpoint == 'http://localhost:11434'


class TestIntegration:
    """Integration-style tests combining multiple features."""

    @patch('src.llm.local_interface.requests.post')
    @patch('src.llm.local_interface.requests.get')
    def test_full_workflow(self, mock_get, mock_post):
        """Test complete workflow from init to generation."""
        # Setup mocks
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'models': [{'name': 'test-model'}]
        }

        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            'response': 'Generated response'
        }

        # Initialize
        llm = LocalLLMInterface()
        assert llm.is_available()

        llm.initialize({
            'model': 'test-model',
            'temperature': 0.5,
            'timeout': 60
        })

        # Test generation
        response = llm.generate("Test prompt")
        assert response == 'Generated response'

        # Test metrics
        metrics = llm.get_metrics()
        assert metrics['calls'] == 1

        # Test token counting
        tokens = llm.estimate_tokens(response)
        assert tokens > 0

        # Test model info
        info = llm.get_model_info()
        assert info['model_name'] == 'test-model'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
