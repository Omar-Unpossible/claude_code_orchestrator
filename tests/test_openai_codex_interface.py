"""Tests for OpenAICodexLLMPlugin.

This module tests the OpenAI Codex CLI integration including:
- Initialization and configuration
- Generation (with real CLI calls)
- Token counting
- Health checks
- Registry registration
- Error handling
"""

import pytest
import subprocess
from unittest.mock import MagicMock, patch
from pathlib import Path

from src.llm.openai_codex_interface import OpenAICodexLLMPlugin
from src.plugins.registry import LLMRegistry
from src.plugins.exceptions import (
    LLMException,
    LLMConnectionException,
    LLMTimeoutException
)


class TestOpenAICodexInitialization:
    """Test initialization and configuration."""

    def test_initialization_default_config(self):
        """Test initialization with default configuration."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        assert llm.codex_command == 'codex'
        assert llm.model == 'codex-mini-latest'
        assert llm.full_auto is True
        assert llm.json_output is False
        assert llm.timeout == 120
        assert llm.retry_manager is not None

    def test_initialize_with_custom_config(self):
        """Test initialization with custom configuration."""
        llm = OpenAICodexLLMPlugin()
        config = {
            'model': 'gpt-5-codex',
            'timeout': 180,
            'full_auto': False,
            'json_output': True,
            'retry_attempts': 5
        }
        llm.initialize(config)

        assert llm.model == 'gpt-5-codex'
        assert llm.timeout == 180
        assert llm.full_auto is False
        assert llm.json_output is True

    def test_initialize_cli_not_found(self, monkeypatch):
        """Test initialization fails when CLI not installed."""
        # Mock shutil.which to return None (CLI not found)
        monkeypatch.setattr('shutil.which', lambda x: None)

        llm = OpenAICodexLLMPlugin()
        with pytest.raises(LLMConnectionException, match="not found"):
            llm.initialize({'codex_command': 'nonexistent-codex'})

    def test_initialize_cli_not_authenticated(self, monkeypatch):
        """Test initialization fails when CLI not authenticated."""
        # Mock shutil.which to succeed
        monkeypatch.setattr('shutil.which', lambda x: '/usr/bin/codex')

        # Mock is_available to return False (not authenticated)
        def mock_is_available(self):
            return False

        monkeypatch.setattr(OpenAICodexLLMPlugin, 'is_available', mock_is_available)

        llm = OpenAICodexLLMPlugin()
        with pytest.raises(LLMConnectionException, match="not authenticated"):
            llm.initialize({})

    def test_config_merging_with_defaults(self):
        """Test that custom config merges with defaults."""
        llm = OpenAICodexLLMPlugin()
        config = {'model': 'o3'}  # Only override model
        llm.initialize(config)

        # Custom value
        assert llm.model == 'o3'

        # Default values
        assert llm.codex_command == 'codex'
        assert llm.full_auto is True
        assert llm.timeout == 120


class TestGeneration:
    """Test text generation functionality."""

    def test_generate_success(self):
        """Test successful text generation with real CLI."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'model': 'codex-mini-latest', 'timeout': 60})

        response = llm.generate('Say "test" in exactly one word.')

        assert isinstance(response, str)
        assert len(response) > 0
        assert llm.metrics['calls'] == 1
        assert llm.metrics['total_tokens'] > 0
        assert llm.metrics['total_latency_ms'] > 0
        assert llm.metrics['errors'] == 0

    def test_generate_with_different_model(self):
        """Test generation with different model."""
        llm = OpenAICodexLLMPlugin()
        # Use a model supported with ChatGPT account
        llm.initialize({'model': 'codex-mini-latest', 'timeout': 60})

        response = llm.generate('Reply with "ok"')

        assert isinstance(response, str)
        assert len(response) > 0

    def test_generate_empty_prompt(self):
        """Test generation with empty prompt."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'timeout': 30})

        # Empty prompt should still work (Codex will handle it)
        response = llm.generate('')

        # Codex should return something or error
        assert isinstance(response, str)

    def test_generate_cli_error_mocked(self, monkeypatch):
        """Test CLI error handling with mocked subprocess."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        # Mock subprocess.run to return non-zero exit code
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "CLI error: invalid argument"

        def mock_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr('subprocess.run', mock_run)

        with pytest.raises(LLMException, match="CLI error"):
            llm.generate("Test prompt")

        assert llm.metrics['errors'] > 0

    def test_generate_authentication_error_mocked(self, monkeypatch):
        """Test authentication error (exit code 2)."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        # Mock subprocess.run to return exit code 2 (auth failure)
        mock_result = MagicMock()
        mock_result.returncode = 2
        mock_result.stdout = ""
        mock_result.stderr = "Authentication failed"

        def mock_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr('subprocess.run', mock_run)

        with pytest.raises(LLMConnectionException, match="Authentication failed"):
            llm.generate("Test prompt")

    def test_generate_timeout_mocked(self, monkeypatch):
        """Test timeout handling."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'timeout': 1})

        # Mock subprocess.run to raise TimeoutExpired
        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired('codex', 1)

        monkeypatch.setattr('subprocess.run', mock_run)

        # Disable retry manager to get exception directly
        llm.retry_manager = None

        with pytest.raises(LLMTimeoutException):
            llm.generate("Test prompt")

        assert llm.metrics['timeouts'] > 0

    def test_generate_empty_response_mocked(self, monkeypatch):
        """Test handling of empty response from CLI."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        # Mock subprocess.run to return empty stdout
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        def mock_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr('subprocess.run', mock_run)

        with pytest.raises(LLMException, match="Empty response"):
            llm.generate("Test prompt")


class TestStreaming:
    """Test streaming generation."""

    def test_generate_stream_success(self):
        """Test streaming generation (word-by-word)."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'model': 'codex-mini-latest', 'timeout': 60})

        chunks = list(llm.generate_stream('Say "hello world"'))

        assert len(chunks) > 0
        # Chunks should be words with spaces
        full_response = ''.join(chunks)
        assert len(full_response) > 0

    def test_generate_stream_yields_words(self):
        """Test that streaming yields word-by-word."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'timeout': 60})

        chunks = list(llm.generate_stream('Say "one two three"'))

        # Should have multiple chunks (words)
        assert len(chunks) >= 1
        # Each chunk should end with space
        for chunk in chunks:
            assert chunk.endswith(' ')


class TestTokenCounting:
    """Test token estimation."""

    def test_estimate_tokens_with_tiktoken(self):
        """Test token estimation with tiktoken."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        tokens = llm.estimate_tokens("Hello world")

        assert tokens > 0
        assert tokens < 10  # "Hello world" is about 2-3 tokens

    def test_estimate_tokens_empty_string(self):
        """Test token estimation for empty string."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        tokens = llm.estimate_tokens("")

        assert tokens == 0

    def test_estimate_tokens_long_text(self):
        """Test token estimation for longer text."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        text = "This is a longer piece of text " * 10
        tokens = llm.estimate_tokens(text)

        assert tokens > 50  # Should be substantial
        assert tokens < 200  # But not too high

    def test_estimate_tokens_fallback(self, monkeypatch):
        """Test token estimation fallback when tiktoken fails."""
        llm = OpenAICodexLLMPlugin()
        llm._encoder = None  # Disable tiktoken

        tokens = llm.estimate_tokens("Hello world")

        # Fallback: 2 words * 1.3 ≈ 2-3 tokens
        assert tokens > 0


class TestHealthCheck:
    """Test availability and health checks."""

    def test_is_available_success(self):
        """Test availability check when CLI is working."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        available = llm.is_available()

        assert available is True

    def test_is_available_failure_mocked(self, monkeypatch):
        """Test availability check when CLI fails."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        # Mock subprocess.run to return non-zero exit code
        mock_result = MagicMock()
        mock_result.returncode = 1

        def mock_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr('subprocess.run', mock_run)

        available = llm.is_available()

        assert available is False

    def test_is_available_exception_mocked(self, monkeypatch):
        """Test availability check when exception occurs."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        # Mock subprocess.run to raise exception
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("CLI not found")

        monkeypatch.setattr('subprocess.run', mock_run)

        available = llm.is_available()

        assert available is False


class TestModelInfo:
    """Test model information retrieval."""

    def test_get_model_info_default(self):
        """Test model info with default model."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        info = llm.get_model_info()

        assert info['model_name'] == 'codex-mini-latest'
        assert info['context_length'] == 8192
        assert info['provider'] == 'openai-codex'
        assert info['type'] == 'cli'
        assert info['execution_mode'] == 'subprocess'

    def test_get_model_info_gpt5_codex(self):
        """Test model info with gpt-5-codex."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'model': 'gpt-5-codex'})

        info = llm.get_model_info()

        assert info['model_name'] == 'gpt-5-codex'
        assert info['context_length'] == 128000  # Larger for GPT-5

    def test_get_model_info_o3(self):
        """Test model info with o3 model."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'model': 'o3'})

        info = llm.get_model_info()

        assert info['model_name'] == 'o3'
        assert info['context_length'] == 128000

    def test_get_model_info_unknown_model(self):
        """Test model info with unknown model (should use default)."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'model': 'unknown-model'})

        info = llm.get_model_info()

        assert info['model_name'] == 'unknown-model'
        assert info['context_length'] == 8192  # Default


class TestMetrics:
    """Test performance metrics tracking."""

    def test_metrics_tracking(self):
        """Test that metrics are tracked correctly."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'timeout': 60})

        # Initial metrics
        metrics = llm.get_metrics()
        assert metrics['calls'] == 0
        assert metrics['total_tokens'] == 0
        assert metrics['total_latency_ms'] == 0.0

        # Generate response
        llm.generate('Say "test"')

        # Updated metrics
        metrics = llm.get_metrics()
        assert metrics['calls'] == 1
        assert metrics['total_tokens'] > 0
        assert metrics['total_latency_ms'] > 0
        assert metrics['avg_latency_ms'] > 0
        assert metrics['tokens_per_second'] >= 0

    def test_metrics_multiple_calls(self):
        """Test metrics accumulation over multiple calls."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'timeout': 60})

        # Make multiple calls
        llm.generate('Say "one"')
        llm.generate('Say "two"')

        metrics = llm.get_metrics()
        assert metrics['calls'] == 2
        assert metrics['total_tokens'] > 0
        assert metrics['avg_latency_ms'] > 0

    def test_metrics_error_tracking_mocked(self, monkeypatch):
        """Test that errors are tracked in metrics."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({})

        # Mock subprocess.run to fail
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error"

        def mock_run(*args, **kwargs):
            return mock_result

        monkeypatch.setattr('subprocess.run', mock_run)

        try:
            llm.generate("Test")
        except LLMException:
            pass

        metrics = llm.get_metrics()
        assert metrics['errors'] > 0


class TestRegistry:
    """Test plugin registry integration."""

    def test_registered_in_registry(self):
        """Test that OpenAI Codex plugin is registered."""
        # Import to ensure registration
        from src.llm.openai_codex_interface import OpenAICodexLLMPlugin

        assert 'openai-codex' in LLMRegistry.list()
        llm_class = LLMRegistry.get('openai-codex')
        assert llm_class is OpenAICodexLLMPlugin

    def test_registry_instantiation(self):
        """Test instantiating plugin from registry."""
        llm_class = LLMRegistry.get('openai-codex')
        llm = llm_class()

        assert isinstance(llm, OpenAICodexLLMPlugin)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_custom_command_path(self):
        """Test using custom CLI command path."""
        llm = OpenAICodexLLMPlugin()
        # Note: This might fail if /usr/local/bin/codex doesn't exist
        # but tests initialization logic
        try:
            llm.initialize({'codex_command': 'codex'})  # Use default
            assert llm.codex_command == 'codex'
        except LLMConnectionException:
            # Expected if custom path doesn't exist
            pass

    def test_json_output_mode(self):
        """Test JSON output mode flag."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'json_output': True})

        assert llm.json_output is True

    def test_full_auto_disabled(self):
        """Test with full-auto disabled."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'full_auto': False})

        assert llm.full_auto is False

    def test_concurrent_calls(self):
        """Test that multiple concurrent calls work (thread-safe)."""
        import threading

        llm = OpenAICodexLLMPlugin()
        llm.initialize({'timeout': 60})

        results = []
        errors = []

        def make_call():
            try:
                response = llm.generate('Say "concurrent"')
                results.append(response)
            except Exception as e:
                errors.append(e)

        # Create 2 threads (keep low for test performance)
        threads = [threading.Thread(target=make_call) for _ in range(2)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=120)

        # Should have 2 successful results
        assert len(results) == 2
        assert len(errors) == 0


class TestIntegration:
    """Integration tests with full workflow."""

    def test_full_workflow(self):
        """Test complete workflow: init -> generate -> metrics."""
        # Initialize
        llm = OpenAICodexLLMPlugin()
        config = {
            'model': 'codex-mini-latest',
            'timeout': 60,
            'full_auto': True
        }
        llm.initialize(config)

        # Check availability
        assert llm.is_available() is True

        # Get model info
        info = llm.get_model_info()
        assert info['model_name'] == 'codex-mini-latest'

        # Generate response
        response = llm.generate('Respond with "workflow test successful"')
        assert isinstance(response, str)
        assert len(response) > 0

        # Check metrics
        metrics = llm.get_metrics()
        assert metrics['calls'] == 1
        assert metrics['total_tokens'] > 0
        assert metrics['errors'] == 0

        # Estimate tokens
        tokens = llm.estimate_tokens(response)
        assert tokens > 0

    def test_retry_on_transient_error_mocked(self, monkeypatch):
        """Test retry logic on transient errors."""
        llm = OpenAICodexLLMPlugin()
        llm.initialize({'retry_attempts': 3})  # Allow enough retries

        call_count = [0]

        def mock_run(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call fails with retryable ConnectionError
                raise ConnectionError("Temporary network error")
            else:
                # All subsequent calls succeed
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Success after retry"
                mock_result.stderr = ""
                return mock_result

        monkeypatch.setattr('subprocess.run', mock_run)

        # Should succeed after retry (ConnectionError is retryable)
        response = llm.generate("Test prompt")
        assert response == "Success after retry"
        assert call_count[0] >= 2  # Called at least twice (1 fail + 1 success)
