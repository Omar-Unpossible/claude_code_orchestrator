"""Local LLM interface for Ollama integration.

This module provides the LocalLLMInterface class that implements the LLMPlugin
interface for communicating with Ollama (running Qwen or other models locally).

Features:
- Streaming and non-streaming generation
- Request/response caching with LRU cache
- Retry logic with exponential backoff (M9: Uses RetryManager)
- Token counting approximation using tiktoken
- Performance metrics tracking
- Health checking
"""

import hashlib
import json
import logging
import time
from functools import lru_cache
from typing import Dict, Any, Iterator, Optional
import requests

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from src.plugins.base import LLMPlugin
from src.plugins.registry import register_llm
from src.plugins.exceptions import (
    LLMException,
    LLMConnectionException,
    LLMTimeoutException,
    LLMModelNotFoundException,
    LLMResponseException
)
from src.utils.retry_manager import RetryManager, RetryConfig, create_retry_manager_from_config

logger = logging.getLogger(__name__)


@register_llm('ollama')
class LocalLLMInterface(LLMPlugin):  # pylint: disable=too-many-instance-attributes
    """Interface to local LLM service via Ollama.

    This class provides communication with Ollama API for local LLM inference,
    with support for streaming, caching, retry logic, and performance monitoring.

    Example:
        >>> llm = LocalLLMInterface()
        >>> llm.initialize({
        ...     'endpoint': 'http://localhost:11434',
        ...     'model': 'qwen2.5-coder:32b',
        ...     'temperature': 0.3
        ... })
        >>> response = llm.generate("Explain this code: def foo(): pass")
        >>> print(response)
        'This function defines an empty function called foo...'

    Thread-safety:
        This class is thread-safe. Multiple threads can call methods simultaneously.
        The LRU cache is thread-safe by default.
    """

    # Default configuration values
    DEFAULT_CONFIG = {
        'endpoint': 'http://localhost:11434',
        'model': 'qwen2.5-coder:32b',
        'temperature': 0.3,
        'max_tokens': 4096,
        'timeout': 120,
        'retry_attempts': 3,
        'cache_size': 100,
        'retry_backoff_base': 2.0,
        'retry_backoff_max': 60.0
    }

    def __init__(self):
        """Initialize local LLM interface."""
        self.config: Dict[str, Any] = {}
        self.endpoint: str = ''
        self.model: str = ''
        self.temperature: float = 0.3
        self.max_tokens: int = 4096
        self.timeout: int = 120
        self.retry_attempts: int = 3
        self.retry_backoff_base: float = 2.0
        self.retry_backoff_max: float = 60.0

        # M9: Retry manager (initialized in initialize())
        self.retry_manager: Optional[RetryManager] = None

        # Performance metrics
        self.metrics = {
            'calls': 0,
            'total_tokens': 0,
            'total_latency_ms': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'timeouts': 0
        }

        # Token encoder (use tiktoken if available, fallback to approximation)
        self._encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base encoding (GPT-4 tokenizer) as approximation
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")

        # Initialize response cache
        self._init_cache()

    def _init_cache(self):
        """Initialize LRU cache for responses."""
        cache_size = self.config.get('cache_size', self.DEFAULT_CONFIG['cache_size'])

        # Create cached version of _generate_uncached
        self._generate_cached = lru_cache(maxsize=cache_size)(self._generate_uncached)

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize LLM provider with configuration.

        Args:
            config: Configuration dictionary with keys:
                - endpoint: Ollama API endpoint (default: http://localhost:11434)
                - model: Model name (default: qwen2.5-coder:32b)
                - temperature: Generation temperature (default: 0.3)
                - max_tokens: Maximum tokens to generate (default: 4096)
                - timeout: Request timeout in seconds (default: 120)
                - retry_attempts: Number of retry attempts (default: 3)
                - cache_size: LRU cache size (default: 100)

        Raises:
            LLMConnectionException: If unable to connect to Ollama
            LLMModelNotFoundException: If model not available

        Example:
            >>> llm = LocalLLMInterface()
            >>> llm.initialize({
            ...     'model': 'qwen2.5-coder:32b',
            ...     'endpoint': 'http://localhost:11434',
            ...     'temperature': 0.7
            ... })
        """
        # Merge with defaults
        self.config = {**self.DEFAULT_CONFIG, **config}

        self.endpoint = self.config['endpoint'].rstrip('/')
        self.model = self.config['model']
        self.temperature = self.config['temperature']
        self.max_tokens = self.config['max_tokens']
        self.timeout = self.config['timeout']
        self.retry_attempts = self.config['retry_attempts']
        self.retry_backoff_base = self.config.get('retry_backoff_base', 2.0)
        self.retry_backoff_max = self.config.get('retry_backoff_max', 60.0)

        # M9: Initialize retry manager
        retry_config = RetryConfig(
            max_attempts=self.retry_attempts,
            base_delay=1.0,
            max_delay=self.retry_backoff_max,
            backoff_multiplier=self.retry_backoff_base,
            jitter=0.1
        )
        self.retry_manager = RetryManager(retry_config)

        # Reinitialize cache with new size
        self._init_cache()

        logger.info(
            f"Initialized LocalLLMInterface: endpoint={self.endpoint}, "
            f"model={self.model}, temp={self.temperature}"
        )

        # Verify connection and model availability
        if not self.is_available():
            raise LLMConnectionException(
                provider='ollama',
                url=self.endpoint,
                details='Cannot connect to Ollama service'
            )

        # Check if model is available
        try:
            models = self._list_models()
            if self.model not in models:
                raise LLMModelNotFoundException(
                    provider='ollama',
                    model=self.model
                )
        except LLMModelNotFoundException:
            # Re-raise model not found exception
            raise
        except Exception as e:
            logger.warning(f"Could not verify model availability: {e}")

    def get_name(self) -> str:
        """Get LLM name for display purposes.

        Returns:
            Short name for display labels (e.g., 'ollama')

        Example:
            >>> llm = LocalLLMInterface()
            >>> llm.get_name()
            'ollama'
        """
        return 'ollama'

    def generate(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """Generate text completion.

        This method uses caching to avoid redundant generations for the same prompt.

        Args:
            prompt: Input prompt
            **kwargs: Generation parameters (override defaults):
                - temperature: float (0.0-2.0)
                - max_tokens: int
                - top_p: float
                - stop: list of stop sequences
                - system: system prompt

        Returns:
            Generated text as string

        Raises:
            LLMException: If generation fails
            LLMTimeoutException: If generation times out
            LLMResponseException: If response invalid

        Example:
            >>> response = llm.generate(
            ...     "Explain this code:",
            ...     temperature=0.3,
            ...     max_tokens=500
            ... )
        """
        start_time = time.time()
        self.metrics['calls'] += 1

        # Create cache key from prompt and kwargs
        cache_key = self._make_cache_key(prompt, kwargs)

        try:
            # Get cache info before call
            cache_info_before = self._generate_cached.cache_info()

            # Try to get from cache
            response = self._generate_cached(cache_key, prompt, **kwargs)

            # Check if this was a cache hit by comparing hits count
            cache_info_after = self._generate_cached.cache_info()
            if cache_info_after.hits > cache_info_before.hits:
                self.metrics['cache_hits'] += 1
            else:
                self.metrics['cache_misses'] += 1

            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self.metrics['total_latency_ms'] += elapsed_ms

            # Estimate tokens
            tokens = self.estimate_tokens(response)
            self.metrics['total_tokens'] += tokens

            logger.debug(
                f"Generated {tokens} tokens in {elapsed_ms:.1f}ms "
                f"(cache_hits={self.metrics['cache_hits']}, "
                f"cache_misses={self.metrics['cache_misses']})"
            )

            return response

        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Generation failed: {e}")
            raise

    def send_prompt(self, prompt: str, **kwargs) -> str:
        """Send prompt to LLM (wrapper for generate).

        Provides compatibility with AgentPlugin interface that uses send_prompt().
        This is a simple wrapper around generate() for API consistency.

        Args:
            prompt: Text prompt to send
            **kwargs: Additional arguments passed to generate()

        Returns:
            Generated response text

        Raises:
            LLMException: If generation fails
            LLMTimeoutException: If generation times out

        Example:
            >>> response = llm.send_prompt("Explain this code:")
        """
        return self.generate(prompt, **kwargs)

    def _make_cache_key(self, prompt: str, kwargs: dict) -> str:
        """Create cache key from prompt and kwargs.

        Args:
            prompt: Input prompt
            kwargs: Generation parameters

        Returns:
            Hash string for caching
        """
        # Normalize kwargs for consistent caching
        normalized = {
            'prompt': prompt,
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'top_p': kwargs.get('top_p'),
            'stop': kwargs.get('stop'),
            'system': kwargs.get('system')
        }

        # Create hash
        key_str = json.dumps(normalized, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def _generate_uncached(
        self,
        cache_key: str,  # Required for caching, but not used in implementation pylint: disable=unused-argument
        prompt: str,
        **kwargs
    ) -> str:
        """Generate text without caching (internal method).

        Args:
            cache_key: Cache key (required for lru_cache)
            prompt: Input prompt
            **kwargs: Generation parameters

        Returns:
            Generated text

        Raises:
            LLMException: If generation fails
            LLMTimeoutException: If generation times out
        """
        # Build request payload
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
            'options': {
                'temperature': kwargs.get('temperature', self.temperature),
                'num_predict': kwargs.get('max_tokens', self.max_tokens),
            }
        }

        # Add optional parameters
        if 'top_p' in kwargs:
            payload['options']['top_p'] = kwargs['top_p']  # type: ignore[index]
        if 'stop' in kwargs:
            payload['options']['stop'] = kwargs['stop']  # type: ignore[index]
        if 'system' in kwargs:
            payload['system'] = kwargs['system']

        # Make request with retry logic
        response_text = self._make_request_with_retry(
            endpoint='/api/generate',
            payload=payload
        )

        return response_text

    def generate_stream(
        self,
        prompt: str,
        **kwargs
    ) -> Iterator[str]:
        """Generate with streaming output.

        Yields text chunks as they're generated, enabling real-time display
        and early stopping. Note: Streaming responses are NOT cached.

        Args:
            prompt: Input prompt
            **kwargs: Same as generate()

        Yields:
            Text chunks as they're generated

        Raises:
            LLMException: If generation fails

        Example:
            >>> for chunk in llm.generate_stream("Write a story"):
            ...     print(chunk, end='', flush=True)
        """
        start_time = time.time()
        self.metrics['calls'] += 1

        # Build request payload
        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': True,
            'options': {
                'temperature': kwargs.get('temperature', self.temperature),
                'num_predict': kwargs.get('max_tokens', self.max_tokens),
            }
        }

        # Add optional parameters
        if 'top_p' in kwargs:
            payload['options']['top_p'] = kwargs['top_p']  # type: ignore[index]
        if 'stop' in kwargs:
            payload['options']['stop'] = kwargs['stop']  # type: ignore[index]
        if 'system' in kwargs:
            payload['system'] = kwargs['system']

        url = f"{self.endpoint}/api/generate"
        total_tokens = 0

        try:
            logger.debug(f"Streaming request to {url}")

            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()

            # Parse Server-Sent Events
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'response' in data:
                            chunk = data['response']
                            if chunk:
                                yield chunk
                                # Estimate tokens in chunk
                                total_tokens += self.estimate_tokens(chunk)

                        # Check if done
                        if data.get('done', False):
                            break

                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse streaming response: {e}")
                        continue

            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self.metrics['total_latency_ms'] += elapsed_ms
            self.metrics['total_tokens'] += total_tokens
            self.metrics['cache_misses'] += 1  # Streaming never uses cache

            logger.debug(f"Streamed {total_tokens} tokens in {elapsed_ms:.1f}ms")

        except requests.exceptions.Timeout:
            self.metrics['timeouts'] += 1
            self.metrics['errors'] += 1
            raise LLMTimeoutException(
                provider='ollama',
                model=self.model,
                timeout_seconds=self.timeout
            )
        except requests.exceptions.RequestException as e:
            self.metrics['errors'] += 1
            raise LLMException(
                f"Streaming generation failed: {e}",
                context={'endpoint': url, 'model': self.model},
                recovery='Check Ollama service status and network connectivity'
            )

    def _make_request_with_retry(
        self,
        endpoint: str,
        payload: dict
    ) -> str:
        """Make HTTP request with exponential backoff retry (M9: Uses RetryManager).

        Args:
            endpoint: API endpoint path (e.g., '/api/generate')
            payload: Request payload

        Returns:
            Response text

        Raises:
            LLMException: If all retries fail
            LLMTimeoutException: If request times out
        """
        url = f"{self.endpoint}{endpoint}"

        def _make_single_request() -> str:
            """Single request attempt (for retry manager)."""
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()

                # Parse response
                data = response.json()

                if 'response' not in data:
                    raise LLMResponseException(
                        provider='ollama',
                        details=f"Missing 'response' field in response: {data}"
                    )

                response_text = data['response']

                if not response_text or not isinstance(response_text, str):
                    raise LLMResponseException(
                        provider='ollama',
                        details=f"Invalid response text: {response_text}"
                    )

                return response_text

            except requests.exceptions.Timeout as e:
                self.metrics['timeouts'] += 1
                raise LLMTimeoutException(
                    provider='ollama',
                    model=self.model,
                    timeout_seconds=self.timeout
                ) from e

            except requests.exceptions.RequestException as e:
                raise LLMException(
                    f"Request failed: {e}",
                    context={'endpoint': url},
                    recovery='Check Ollama service status'
                ) from e

            except json.JSONDecodeError as e:
                raise LLMResponseException(
                    provider='ollama',
                    details=f"Failed to parse response: {e}"
                ) from e

        # Use retry manager if available (M9), otherwise fall back to direct call
        if self.retry_manager:
            try:
                return self.retry_manager.execute(_make_single_request)
            except Exception as e:
                self.metrics['errors'] += 1
                raise
        else:
            # Fallback for backward compatibility
            return _make_single_request()

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Uses tiktoken if available (GPT-4 tokenizer as approximation for Qwen),
        otherwise falls back to word-based estimation.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count

        Example:
            >>> count = llm.estimate_tokens("Hello world")
            >>> print(count)
            2
        """
        if not text:
            return 0

        if self._encoder:
            try:
                tokens = self._encoder.encode(text)
                return len(tokens)
            except Exception as e:
                logger.warning(f"Tiktoken encoding failed: {e}")

        # Fallback: approximate as 1.3 tokens per word
        # This is a rough estimate for code/text content
        word_count = len(text.split())
        return int(word_count * 1.3)

    def is_available(self) -> bool:
        """Check if LLM is accessible and ready.

        Quick health check - pings the Ollama API to verify it's running.

        Returns:
            True if LLM is available, False otherwise

        Example:
            >>> if llm.is_available():
            ...     response = llm.generate(prompt)
            ... else:
            ...     print("LLM service is down")
        """
        try:
            response = requests.get(
                f"{self.endpoint}/api/tags",
                timeout=5  # Short timeout for health check
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    def warmup(self) -> None:
        """Warm up the model by sending a test prompt.

        This can help reduce latency for the first real request by loading
        the model into memory.

        Example:
            >>> llm.warmup()  # Load model into memory
            >>> response = llm.generate(prompt)  # Faster response
        """
        logger.info(f"Warming up model {self.model}...")
        try:
            self.generate("Hello", max_tokens=10)
            logger.info("Model warmup complete")
        except Exception as e:
            logger.warning(f"Model warmup failed: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded model.

        Returns:
            Dictionary with model information:
                - model_name: str
                - context_length: int
                - quantization: str (if available)
                - size_gb: float (if available)
                - family: str (if available)

        Example:
            >>> info = llm.get_model_info()
            >>> print(f"Context length: {info['context_length']}")
        """
        try:
            response = requests.post(
                f"{self.endpoint}/api/show",
                json={'name': self.model},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            # Extract relevant information
            model_info = {
                'model_name': self.model,
                'context_length': 4096,  # Default
                'quantization': 'unknown',
                'size_gb': 0.0,
                'family': 'unknown'
            }

            # Parse modelfile for context length
            if 'modelfile' in data:
                for line in data['modelfile'].split('\n'):
                    if 'num_ctx' in line:
                        try:
                            ctx_len = int(line.split()[-1])
                            model_info['context_length'] = ctx_len
                        except (ValueError, IndexError):
                            pass

            # Get size from details
            if 'details' in data:
                details = data['details']
                model_info['family'] = details.get('family', 'unknown')
                model_info['quantization'] = details.get('quantization_level', 'unknown')

                # Convert size to GB
                if 'size' in details:
                    size_bytes = details['size']
                    model_info['size_gb'] = round(size_bytes / (1024 ** 3), 2)

            return model_info

        except Exception as e:
            logger.warning(f"Failed to get model info: {e}")
            return {
                'model_name': self.model,
                'context_length': 4096,
                'quantization': 'unknown',
                'size_gb': 0.0,
                'family': 'unknown'
            }

    def _list_models(self) -> list:
        """List available models in Ollama.

        Returns:
            List of model names

        Raises:
            LLMException: If request fails
        """
        try:
            response = requests.get(
                f"{self.endpoint}/api/tags",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            models = []
            if 'models' in data:
                for model in data['models']:
                    if 'name' in model:
                        models.append(model['name'])

            return models

        except Exception as e:
            raise LLMException(
                f"Failed to list models: {e}",
                context={'endpoint': self.endpoint},
                recovery='Check Ollama service status'
            )

    def clear_cache(self) -> None:
        """Clear the response cache.

        This forces all subsequent requests to regenerate responses instead
        of using cached values.

        Example:
            >>> llm.clear_cache()  # Clear all cached responses
        """
        self._generate_cached.cache_clear()
        logger.info("Response cache cleared")

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics.

        Returns:
            Dictionary with metrics:
                - calls: Total number of generate() calls
                - total_tokens: Total tokens generated
                - total_latency_ms: Total latency in milliseconds
                - cache_hits: Number of cache hits
                - cache_misses: Number of cache misses
                - errors: Number of errors
                - timeouts: Number of timeouts
                - avg_latency_ms: Average latency per call
                - tokens_per_second: Average generation speed
                - cache_hit_rate: Cache hit rate (0.0-1.0)

        Example:
            >>> metrics = llm.get_metrics()
            >>> print(f"Cache hit rate: {metrics['cache_hit_rate']:.2%}")
        """
        metrics = self.metrics.copy()

        # Calculate derived metrics
        if metrics['calls'] > 0:
            metrics['avg_latency_ms'] = metrics['total_latency_ms'] / metrics['calls']
        else:
            metrics['avg_latency_ms'] = 0.0

        if metrics['total_latency_ms'] > 0:
            metrics['tokens_per_second'] = (
                metrics['total_tokens'] / (metrics['total_latency_ms'] / 1000)
            )
        else:
            metrics['tokens_per_second'] = 0.0

        total_requests = metrics['cache_hits'] + metrics['cache_misses']
        if total_requests > 0:
            metrics['cache_hit_rate'] = metrics['cache_hits'] / total_requests
        else:
            metrics['cache_hit_rate'] = 0.0

        return metrics
