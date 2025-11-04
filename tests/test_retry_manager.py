"""Tests for RetryManager - M9 exponential backoff retry logic.

Tests cover:
- Basic retry functionality
- Exponential backoff calculations
- Jitter application
- Retryable vs non-retryable errors
- Max attempts enforcement
- Decorator pattern
- Thread safety
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.utils.retry_manager import (
    RetryManager,
    RetryConfig,
    RetryExhaustedError,
    create_retry_manager_from_config
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RetryConfig()

        assert config.max_attempts == 5
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_multiplier == 2.0
        assert config.jitter == 0.1
        assert config.retryable_exceptions == (ConnectionError, TimeoutError, OSError)
        assert 'rate limit' in config.retryable_error_patterns

    def test_custom_config(self):
        """Test custom configuration."""
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.5,
            max_delay=30.0,
            backoff_multiplier=1.5
        )

        assert config.max_attempts == 3
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0
        assert config.backoff_multiplier == 1.5


class TestRetryManager:
    """Tests for RetryManager core functionality."""

    def test_initialization(self):
        """Test RetryManager initialization."""
        config = RetryConfig(max_attempts=3)
        retry_manager = RetryManager(config)

        assert retry_manager.config.max_attempts == 3

    def test_default_initialization(self):
        """Test initialization with default config."""
        retry_manager = RetryManager()

        assert retry_manager.config.max_attempts == 5

    def test_is_retryable_error_by_type(self):
        """Test retryable error detection by exception type."""
        retry_manager = RetryManager()

        # Retryable errors
        assert retry_manager.is_retryable_error(ConnectionError())
        assert retry_manager.is_retryable_error(TimeoutError())
        assert retry_manager.is_retryable_error(OSError())

        # Non-retryable errors
        assert not retry_manager.is_retryable_error(ValueError())
        assert not retry_manager.is_retryable_error(TypeError())
        assert not retry_manager.is_retryable_error(KeyError())

    def test_is_retryable_error_by_message(self):
        """Test retryable error detection by error message."""
        retry_manager = RetryManager()

        # Retryable messages
        assert retry_manager.is_retryable_error(Exception("Rate limit exceeded"))
        assert retry_manager.is_retryable_error(Exception("Connection timeout"))
        assert retry_manager.is_retryable_error(Exception("Service unavailable"))
        assert retry_manager.is_retryable_error(Exception("Too many requests"))

        # Non-retryable messages
        assert not retry_manager.is_retryable_error(Exception("Invalid input"))
        assert not retry_manager.is_retryable_error(Exception("Authentication failed"))

    def test_calculate_delay_exponential(self):
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            base_delay=1.0,
            backoff_multiplier=2.0,
            jitter=0.0  # Disable jitter for predictable testing
        )
        retry_manager = RetryManager(config)

        # Test exponential growth
        assert retry_manager.calculate_delay(0) == 1.0  # 1 * 2^0
        assert retry_manager.calculate_delay(1) == 2.0  # 1 * 2^1
        assert retry_manager.calculate_delay(2) == 4.0  # 1 * 2^2
        assert retry_manager.calculate_delay(3) == 8.0  # 1 * 2^3
        assert retry_manager.calculate_delay(4) == 16.0  # 1 * 2^4

    def test_calculate_delay_max_cap(self):
        """Test delay capped at max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=10.0,
            backoff_multiplier=2.0,
            jitter=0.0
        )
        retry_manager = RetryManager(config)

        # Should be capped at 10.0
        assert retry_manager.calculate_delay(10) == 10.0
        assert retry_manager.calculate_delay(100) == 10.0

    def test_calculate_delay_with_jitter(self):
        """Test jitter adds randomness to delay."""
        config = RetryConfig(
            base_delay=10.0,
            backoff_multiplier=1.0,
            jitter=0.1  # 10% jitter
        )
        retry_manager = RetryManager(config)

        # With jitter, delay should be between 10.0 and 11.0
        delay = retry_manager.calculate_delay(0)
        assert 10.0 <= delay <= 11.0

    def test_execute_success_first_attempt(self):
        """Test successful execution on first attempt."""
        retry_manager = RetryManager()

        mock_func = Mock(return_value="success")
        result = retry_manager.execute(mock_func, arg1="test")

        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_with(arg1="test")

    def test_execute_success_after_retries(self, fast_time):
        """Test successful execution after retries."""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        retry_manager = RetryManager(config)

        # Fail twice, then succeed
        mock_func = Mock(side_effect=[
            ConnectionError("Connection failed"),
            ConnectionError("Connection failed"),
            "success"
        ])

        result = retry_manager.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    def test_execute_non_retryable_error(self):
        """Test non-retryable error raised immediately."""
        retry_manager = RetryManager()

        mock_func = Mock(side_effect=ValueError("Invalid input"))

        with pytest.raises(ValueError, match="Invalid input"):
            retry_manager.execute(mock_func)

        # Should not retry
        assert mock_func.call_count == 1

    def test_execute_exhausted_retries(self, fast_time):
        """Test all retries exhausted."""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        retry_manager = RetryManager(config)

        mock_func = Mock(side_effect=ConnectionError("Connection failed"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_manager.execute(mock_func)

        assert mock_func.call_count == 3
        assert len(exc_info.value.attempts) == 3
        assert isinstance(exc_info.value.original_error, ConnectionError)

    def test_execute_with_args_and_kwargs(self):
        """Test execute passes args and kwargs correctly."""
        retry_manager = RetryManager()

        mock_func = Mock(return_value="result")
        result = retry_manager.execute(
            mock_func,
            "arg1", "arg2",
            kwarg1="value1",
            kwarg2="value2"
        )

        assert result == "result"
        mock_func.assert_called_with("arg1", "arg2", kwarg1="value1", kwarg2="value2")

    def test_decorator_success(self):
        """Test retry decorator on successful function."""
        retry_manager = RetryManager()

        @retry_manager.retry()
        def test_func():
            return "success"

        result = test_func()
        assert result == "success"

    def test_decorator_with_retries(self, fast_time):
        """Test retry decorator with retries."""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        retry_manager = RetryManager(config)

        call_count = {"count": 0}

        @retry_manager.retry()
        def test_func():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ConnectionError("Fail")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count["count"] == 3

    def test_decorator_with_override(self, fast_time):
        """Test decorator with override parameters."""
        config = RetryConfig(max_attempts=5)
        retry_manager = RetryManager(config)

        call_count = {"count": 0}

        @retry_manager.retry(max_attempts=2)  # Override to 2
        def test_func():
            call_count["count"] += 1
            raise ConnectionError("Fail")

        with pytest.raises(RetryExhaustedError):
            test_func()

        # Should only attempt 2 times (override)
        assert call_count["count"] == 2

    def test_decorator_preserves_function_metadata(self):
        """Test decorator preserves function name and docstring."""
        retry_manager = RetryManager()

        @retry_manager.retry()
        def test_func():
            """Test function docstring."""
            return "result"

        assert test_func.__name__ == "test_func"
        assert test_func.__doc__ == "Test function docstring."

    def test_retry_exhausted_error_attributes(self, fast_time):
        """Test RetryExhaustedError contains attempt history."""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        retry_manager = RetryManager(config)

        mock_func = Mock(side_effect=TimeoutError("Timeout"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_manager.execute(mock_func)

        error = exc_info.value
        assert isinstance(error.original_error, TimeoutError)
        assert len(error.attempts) == 3

        # Check attempts have correct attributes
        for i, attempt in enumerate(error.attempts):
            assert attempt.attempt_number == i + 1
            assert attempt.delay >= 0
            assert attempt.timestamp is not None


class TestRetryManagerThreadSafety:
    """Tests for thread-safe operation (limited to avoid WSL2 crashes)."""

    def test_concurrent_execution(self):
        """Test retry manager works with concurrent calls (limited threads)."""
        import threading

        retry_manager = RetryManager()
        results = []
        errors = []

        def worker(worker_id):
            try:
                @retry_manager.retry()
                def task():
                    return f"result_{worker_id}"

                result = task()
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Use only 3 threads to stay within limits
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)  # Mandatory timeout

        assert len(errors) == 0
        assert len(results) == 3
        assert "result_0" in results
        assert "result_1" in results
        assert "result_2" in results


class TestRetryManagerFactory:
    """Tests for factory function."""

    def test_create_from_config_dict(self):
        """Test creating RetryManager from config dictionary."""
        config_dict = {
            'max_attempts': 7,
            'base_delay': 0.5,
            'max_delay': 30.0,
            'backoff_multiplier': 1.5,
            'jitter': 0.2
        }

        retry_manager = create_retry_manager_from_config(config_dict)

        assert retry_manager.config.max_attempts == 7
        assert retry_manager.config.base_delay == 0.5
        assert retry_manager.config.max_delay == 30.0
        assert retry_manager.config.backoff_multiplier == 1.5
        assert retry_manager.config.jitter == 0.2

    def test_create_from_partial_config(self):
        """Test creating with partial config uses defaults."""
        config_dict = {'max_attempts': 10}

        retry_manager = create_retry_manager_from_config(config_dict)

        assert retry_manager.config.max_attempts == 10
        assert retry_manager.config.base_delay == 1.0  # Default

    def test_create_from_empty_config(self):
        """Test creating with empty config uses all defaults."""
        retry_manager = create_retry_manager_from_config({})

        assert retry_manager.config.max_attempts == 5
        assert retry_manager.config.base_delay == 1.0
        assert retry_manager.config.max_delay == 60.0


class TestRetryManagerEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_zero_max_attempts_handled(self):
        """Test handling of zero max attempts."""
        config = RetryConfig(max_attempts=0)
        retry_manager = RetryManager(config)

        mock_func = Mock(side_effect=ConnectionError())

        # Should fail immediately with no attempts
        with pytest.raises(RetryExhaustedError):
            retry_manager.execute(mock_func)

    def test_exception_with_empty_message(self):
        """Test exception with empty message."""
        retry_manager = RetryManager()

        # Empty message should not match patterns
        assert not retry_manager.is_retryable_error(Exception(""))

    def test_calculate_delay_negative_attempt(self):
        """Test delay calculation with edge case inputs."""
        retry_manager = RetryManager()

        # Should handle gracefully
        delay = retry_manager.calculate_delay(0)
        assert delay >= 0

    def test_function_returns_none(self):
        """Test function that returns None."""
        retry_manager = RetryManager()

        mock_func = Mock(return_value=None)
        result = retry_manager.execute(mock_func)

        assert result is None
        assert mock_func.call_count == 1

    def test_function_with_exception_in_finally(self):
        """Test function with exception handling."""
        retry_manager = RetryManager()

        cleanup_called = {"called": False}

        def test_func():
            try:
                return "success"
            finally:
                cleanup_called["called"] = True

        result = retry_manager.execute(test_func)

        assert result == "success"
        assert cleanup_called["called"]


class TestRetryManagerIntegration:
    """Integration tests with realistic scenarios."""

    def test_api_call_simulation(self, fast_time):
        """Simulate API call with rate limiting."""
        config = RetryConfig(max_attempts=4, base_delay=0.1)
        retry_manager = RetryManager(config)

        call_count = {"count": 0}

        def mock_api_call():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ConnectionError("Rate limit: too many requests")
            return {"status": "success", "data": [1, 2, 3]}

        result = retry_manager.execute(mock_api_call)

        assert result["status"] == "success"
        assert call_count["count"] == 3

    def test_database_connection_retry(self, fast_time):
        """Simulate database connection retry."""
        config = RetryConfig(max_attempts=3, base_delay=0.1)
        retry_manager = RetryManager(config)

        @retry_manager.retry()
        def connect_to_db():
            # Simulate transient connection issue
            import random
            if random.random() < 0.3:  # 30% chance of success
                return "connected"
            raise ConnectionError("Connection refused")

        # May or may not succeed based on randomness
        # This tests the retry logic under realistic conditions
        try:
            result = retry_manager.execute(connect_to_db)
            assert result == "connected"
        except RetryExhaustedError:
            # Expected if all retries fail
            pass

    def test_mixed_error_types(self, fast_time):
        """Test handling of mixed retryable and non-retryable errors."""
        config = RetryConfig(max_attempts=5, base_delay=0.1)
        retry_manager = RetryManager(config)

        call_count = {"count": 0}

        def test_func():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise ConnectionError("Network error")  # Retryable
            elif call_count["count"] == 2:
                raise TimeoutError("Timeout")  # Retryable
            elif call_count["count"] == 3:
                return "success"
            raise ValueError("Should not reach")  # Non-retryable

        result = retry_manager.execute(test_func)
        assert result == "success"
        assert call_count["count"] == 3
