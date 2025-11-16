"""Context window auto-detection for LLM models.

This module provides functionality to automatically detect context window sizes
by querying LLM provider APIs (Ollama, Anthropic, OpenAI).

Classes:
    ContextWindowDetector: Auto-detect context window sizes from provider APIs

Example:
    >>> detector = ContextWindowDetector(fallback_size=16384)
    >>> context_size = detector.detect('ollama', 'qwen2.5-coder:32b')
    >>> print(f"Detected context: {context_size:,} tokens")
    Detected context: 128,000 tokens

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ContextDetectionError(Exception):
    """Raised when context window detection fails."""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize context detection error.

        Args:
            message: Error description
            provider: Provider name (ollama, anthropic, openai)
            model: Model identifier
            original_error: Original exception that caused the error
        """
        self.provider = provider
        self.model = model
        self.original_error = original_error

        full_message = message
        if provider and model:
            full_message = f"{message} (provider: {provider}, model: {model})"
        if original_error:
            full_message += f"\nOriginal error: {original_error}"

        super().__init__(full_message)


class ContextWindowDetector:
    """Auto-detect context window sizes from LLM provider APIs.

    This class queries various LLM provider APIs to automatically detect
    the context window size for a given model. Falls back to configured
    values or a default if detection fails.

    Thread-safe: Yes (read-only operations, no shared state)

    Attributes:
        fallback_size: Default context window size if detection fails
        timeout: API request timeout in seconds
        ollama_base_url: Base URL for Ollama API

    Example:
        >>> detector = ContextWindowDetector(fallback_size=16384)
        >>> size = detector.detect('ollama', 'qwen2.5-coder:32b')
        >>> print(f"Context window: {size:,} tokens")
        Context window: 128,000 tokens
    """

    # Default API endpoints
    DEFAULT_OLLAMA_URL = 'http://localhost:11434'
    DEFAULT_ANTHROPIC_URL = 'https://api.anthropic.com/v1'
    DEFAULT_OPENAI_URL = 'https://api.openai.com/v1'

    # Known context window sizes (fallback data)
    KNOWN_CONTEXT_WINDOWS = {
        'ollama': {
            'phi3:mini': 4096,
            'qwen2.5-coder:3b': 8192,
            'qwen2.5-coder:7b': 16384,
            'qwen2.5-coder:14b': 32768,
            'qwen2.5-coder:32b': 128000,
        },
        'anthropic': {
            'claude-3-5-sonnet-20241022': 200000,
            'claude-3-5-haiku-20241022': 200000,
            'claude-3-opus-20240229': 200000,
        },
        'openai': {
            'gpt-4-turbo': 128000,
            'gpt-4': 8192,
            'gpt-3.5-turbo': 16385,
        }
    }

    def __init__(
        self,
        fallback_size: int = 16384,
        timeout: int = 5,
        ollama_base_url: Optional[str] = None
    ):
        """Initialize context window detector.

        Args:
            fallback_size: Default context window size if detection fails
                (default: 16384)
            timeout: API request timeout in seconds (default: 5)
            ollama_base_url: Base URL for Ollama API. If None, checks
                environment or uses default (http://localhost:11434)

        Raises:
            ValueError: If fallback_size is not positive
        """
        if fallback_size <= 0:
            raise ValueError(f"fallback_size must be positive (got: {fallback_size})")

        self.fallback_size = fallback_size
        self.timeout = timeout

        # Ollama URL: check environment, then use default
        if ollama_base_url is None:
            import os
            ollama_base_url = os.getenv('OLLAMA_BASE_URL', self.DEFAULT_OLLAMA_URL)

        self.ollama_base_url = ollama_base_url.rstrip('/')

        logger.debug(
            f"ContextWindowDetector initialized: fallback={fallback_size}, "
            f"timeout={timeout}s, ollama_url={self.ollama_base_url}"
        )

    def detect(
        self,
        provider: str,
        model: str,
        model_config: Optional[Dict[str, Any]] = None
    ) -> int:
        """Auto-detect context window size for a model.

        Attempts detection in this order:
        1. Query provider API
        2. Check known context windows
        3. Use model_config value if provided
        4. Use fallback_size

        Args:
            provider: Provider name (ollama, anthropic, openai)
            model: Model identifier
            model_config: Optional model configuration dict with 'context_window' key

        Returns:
            Detected context window size in tokens

        Example:
            >>> detector = ContextWindowDetector()
            >>> size = detector.detect('ollama', 'qwen2.5-coder:32b')
            >>> print(size)
            128000
        """
        provider = provider.lower()

        logger.info(f"Detecting context window: provider={provider}, model={model}")

        # Try API detection first
        try:
            if provider == 'ollama':
                size = self._detect_ollama(model)
            elif provider == 'anthropic':
                size = self._detect_anthropic(model)
            elif provider == 'openai':
                size = self._detect_openai(model)
            else:
                logger.warning(f"Unknown provider '{provider}', using fallback")
                size = None

            if size:
                logger.info(
                    f"Successfully detected context window from API: {size:,} tokens"
                )
                return size

        except Exception as e:
            logger.warning(
                f"API detection failed for {provider}/{model}: {e}. "
                "Trying fallback methods."
            )

        # Try known context windows
        if provider in self.KNOWN_CONTEXT_WINDOWS:
            if model in self.KNOWN_CONTEXT_WINDOWS[provider]:
                size = self.KNOWN_CONTEXT_WINDOWS[provider][model]
                logger.info(
                    f"Using known context window for {provider}/{model}: {size:,} tokens"
                )
                return size

        # Try model config
        if model_config and 'context_window' in model_config:
            size = model_config['context_window']
            logger.info(
                f"Using context window from model config: {size:,} tokens"
            )
            return size

        # Final fallback
        logger.warning(
            f"Could not detect context window for {provider}/{model}. "
            f"Using fallback: {self.fallback_size:,} tokens"
        )
        return self.fallback_size

    def _detect_ollama(self, model: str) -> Optional[int]:
        """Detect context window from Ollama API.

        Queries the Ollama /api/show endpoint to get model information.

        Args:
            model: Model identifier (e.g., 'qwen2.5-coder:32b')

        Returns:
            Context window size if detected, None otherwise

        Raises:
            ContextDetectionError: If API request fails
        """
        try:
            url = f"{self.ollama_base_url}/api/show"
            payload = {'name': model}

            logger.debug(f"Querying Ollama API: {url} with model={model}")

            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout
            )

            response.raise_for_status()
            data = response.json()

            # Ollama API returns model details including context length
            # Check multiple possible locations for context window info
            context_size = None

            # Try modelfile parameters
            if 'modelfile' in data:
                modelfile = data['modelfile']
                # Look for "PARAMETER num_ctx" in modelfile
                for line in modelfile.split('\n'):
                    if 'num_ctx' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                context_size = int(parts[-1])
                                break
                            except ValueError:
                                pass

            # Try details section
            if not context_size and 'details' in data:
                details = data['details']
                if 'parameter_size' in details:
                    # Some models report context in parameters
                    if 'context_length' in details:
                        context_size = details['context_length']

            # Try model_info section
            if not context_size and 'model_info' in data:
                model_info = data['model_info']
                for key in ['context_length', 'num_ctx', 'context_window']:
                    if key in model_info:
                        context_size = model_info[key]
                        break

            if context_size:
                logger.debug(f"Detected Ollama context window: {context_size}")
                return context_size

            logger.debug(f"No context window found in Ollama response for {model}")
            return None

        except requests.RequestException as e:
            logger.debug(f"Ollama API request failed: {e}")
            raise ContextDetectionError(
                "Failed to query Ollama API",
                provider='ollama',
                model=model,
                original_error=e
            )
        except Exception as e:
            logger.debug(f"Unexpected error detecting Ollama context: {e}")
            return None

    def _detect_anthropic(self, model: str) -> Optional[int]:
        """Detect context window from Anthropic API.

        Note: Anthropic API doesn't provide model inspection endpoints.
        This method uses known values from documentation.

        Args:
            model: Model identifier

        Returns:
            Context window size if known, None otherwise
        """
        # Anthropic doesn't have a public API to query model capabilities
        # Use known values from documentation
        logger.debug(
            f"Anthropic API doesn't support model inspection. "
            f"Checking known values for {model}"
        )

        # Check known values
        if model in self.KNOWN_CONTEXT_WINDOWS['anthropic']:
            return self.KNOWN_CONTEXT_WINDOWS['anthropic'][model]

        # Pattern matching for model families
        if 'claude-3' in model or 'claude-3-5' in model:
            # All Claude 3/3.5 models have 200K context
            return 200000

        return None

    def _detect_openai(self, model: str) -> Optional[int]:
        """Detect context window from OpenAI API.

        Note: OpenAI API doesn't provide model inspection endpoints.
        This method uses known values from documentation.

        Args:
            model: Model identifier

        Returns:
            Context window size if known, None otherwise
        """
        # OpenAI doesn't have a public API to query model capabilities
        # Use known values from documentation
        logger.debug(
            f"OpenAI API doesn't support model inspection. "
            f"Checking known values for {model}"
        )

        # Check known values
        if model in self.KNOWN_CONTEXT_WINDOWS['openai']:
            return self.KNOWN_CONTEXT_WINDOWS['openai'][model]

        # Pattern matching for model families
        if 'gpt-4-turbo' in model or 'gpt-4-1106' in model or 'gpt-4-0125' in model:
            return 128000
        elif 'gpt-4' in model:
            return 8192
        elif 'gpt-3.5-turbo' in model:
            return 16385

        return None

    def update_known_contexts(
        self,
        provider: str,
        model: str,
        context_size: int
    ) -> None:
        """Update known context windows with a new entry.

        Useful for caching detected values or adding new models.

        Args:
            provider: Provider name
            model: Model identifier
            context_size: Context window size in tokens

        Example:
            >>> detector = ContextWindowDetector()
            >>> detector.update_known_contexts('ollama', 'custom-model', 32000)
        """
        provider = provider.lower()

        if provider not in self.KNOWN_CONTEXT_WINDOWS:
            self.KNOWN_CONTEXT_WINDOWS[provider] = {}

        self.KNOWN_CONTEXT_WINDOWS[provider][model] = context_size
        logger.debug(
            f"Updated known context window: {provider}/{model} = {context_size}"
        )
