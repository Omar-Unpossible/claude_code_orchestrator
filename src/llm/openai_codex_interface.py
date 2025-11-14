"""OpenAI Codex CLI LLM interface for remote orchestrator.

Implements LLMPlugin interface for OpenAI Codex CLI (subscription or API key),
enabling CLI-based remote LLM orchestration as alternative to local Qwen/Ollama.

This uses subprocess execution similar to ClaudeCodeLocalAgent pattern.
"""

import logging
import os
import shutil
import subprocess
import time
from typing import Dict, Any, Iterator, Optional

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
    LLMResponseException
)
from src.utils.retry_manager import RetryManager, create_retry_manager_from_config

logger = logging.getLogger(__name__)


@register_llm('openai-codex')
class OpenAICodexLLMPlugin(LLMPlugin):
    """OpenAI Codex CLI interface for remote LLM orchestration.

    Provides CLI-based LLM capabilities via OpenAI Codex CLI (subscription or API key)
    as alternative to local Qwen/Ollama or HTTP API-based providers.

    Uses subprocess execution pattern similar to ClaudeCodeLocalAgent:
    - `codex exec --full-auto --quiet "prompt"` for non-interactive execution
    - `--model` flag for model selection (codex-mini-latest, gpt-5-codex, o3, etc.)
    - Supports both OAuth (codex --login) and API key (OPENAI_API_KEY) authentication

    Example:
        >>> llm = OpenAICodexLLMPlugin()
        >>> llm.initialize({
        ...     'codex_command': 'codex',
        ...     'model': 'gpt-5-codex',
        ...     'temperature': 0.7,
        ...     'timeout': 120
        ... })
        >>> response = llm.generate("Validate this code output...")

    Thread-safety: This class is thread-safe. Multiple threads can call
    methods simultaneously (each subprocess is independent).

    Note: Assumes Codex CLI is already installed and authenticated (similar
    to Claude Code CLI authentication pattern).
    """

    DEFAULT_CONFIG = {
        'codex_command': 'codex',  # CLI command name
        'model': None,  # No default model - let Codex CLI auto-select based on account
        'full_auto': True,  # Use --full-auto for automatic execution
        'json_output': False,  # Use --json for JSONL output (optional)
        'timeout': 120,  # Longer timeout for CLI execution
        'retry_attempts': 3,
        'retry_backoff_base': 2.0,
        'retry_backoff_max': 60.0,
    }

    def __init__(self):
        """Initialize OpenAI Codex LLM interface."""
        # Configuration (set in initialize())
        self.codex_command: str = 'codex'
        self.model: Optional[str] = None  # No default - let Codex CLI auto-select
        self.full_auto: bool = True
        self.json_output: bool = False
        self.timeout: int = 120
        self.retry_attempts: int = 3
        self.retry_backoff_base: float = 2.0
        self.retry_backoff_max: float = 60.0

        # Retry manager (M9 pattern)
        self.retry_manager: Optional[RetryManager] = None

        # Performance metrics (match LocalLLMInterface structure exactly)
        self.metrics = {
            'calls': 0,
            'total_tokens': 0,
            'total_latency_ms': 0.0,
            'errors': 0,
            'timeouts': 0
        }

        # Token encoder (use tiktoken if available)
        self._encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use GPT-4 tokenizer as approximation
                self._encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize Codex CLI with configuration.

        Args:
            config: Configuration dictionary with keys:
                - codex_command: Command to execute (default: 'codex')
                - model: Model to use (default: None = auto-select based on account)
                - full_auto: Use --full-auto flag (default: True)
                - json_output: Use --json for JSONL output (default: False)
                - timeout: Subprocess timeout in seconds (default: 120)
                - retry_attempts: Number of retry attempts (default: 3)

        Raises:
            LLMConnectionException: If Codex CLI not found or not authenticated

        Example:
            >>> llm.initialize({
            ...     'model': 'gpt-5-codex',
            ...     'timeout': 180
            ... })
        """
        # Merge with defaults
        merged_config = {**self.DEFAULT_CONFIG, **config}

        self.codex_command = merged_config['codex_command']
        self.model = merged_config['model']
        self.full_auto = merged_config['full_auto']
        self.json_output = merged_config['json_output']
        self.timeout = merged_config['timeout']
        self.retry_attempts = merged_config['retry_attempts']
        self.retry_backoff_base = merged_config.get('retry_backoff_base', 2.0)
        self.retry_backoff_max = merged_config.get('retry_backoff_max', 60.0)

        # Initialize retry manager (M9 pattern)
        self.retry_manager = create_retry_manager_from_config(merged_config)

        # Verify Codex CLI is installed
        codex_path = shutil.which(self.codex_command)
        if not codex_path:
            raise LLMConnectionException(
                provider='openai-codex',
                url=self.codex_command,
                details=f'Codex CLI not found: {self.codex_command}'
            )

        model_info = self.model if self.model else "auto-select"
        logger.info(
            f"Initialized OpenAICodexLLMPlugin: command={codex_path}, "
            f"model={model_info}, full_auto={self.full_auto}"
        )

        # Verify CLI is authenticated (quick check)
        if not self.is_available():
            raise LLMConnectionException(
                provider='openai-codex',
                url=self.codex_command,
                details='Codex CLI not authenticated or not working. '
                       'Run `codex --login` or set OPENAI_API_KEY environment variable.'
            )

    def get_name(self) -> str:
        """Get LLM name for display purposes.

        Returns:
            Short name for display labels (e.g., 'openai-codex')

        Example:
            >>> llm = OpenAICodexLLMPlugin()
            >>> llm.get_name()
            'openai-codex'
        """
        return 'openai-codex'

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate response using Codex CLI.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters (currently unused for CLI)

        Returns:
            Generated text as string

        Raises:
            LLMException: If generation fails
            LLMTimeoutException: If generation times out
            LLMConnectionException: If CLI not available

        Example:
            >>> response = llm.generate("Explain this function")
        """
        start_time = time.time()
        self.metrics['calls'] += 1

        # Build command
        cmd = [self.codex_command, 'exec']

        # Add full-auto flag for automatic execution
        if self.full_auto:
            cmd.append('--full-auto')

        # Add JSON output mode (optional)
        if self.json_output:
            cmd.append('--json')

        # Add model (only if explicitly configured)
        # If model is None, Codex CLI will auto-select based on account type
        if self.model:
            cmd.extend(['--model', self.model])

        # Add prompt
        cmd.append(prompt)

        # Execute with retry logic
        def _execute():
            return self._execute_codex_command(cmd)

        try:
            # Use retry manager if available
            if self.retry_manager:
                response = self.retry_manager.execute(_execute)
            else:
                response = _execute()

            # Update metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self.metrics['total_latency_ms'] += elapsed_ms

            # Estimate tokens
            tokens = self.estimate_tokens(response)
            self.metrics['total_tokens'] += tokens

            logger.debug(f"Codex CLI generation: {elapsed_ms:.0f}ms, ~{tokens} tokens")

            return response

        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Codex CLI generation failed: {e}")
            raise

    def _execute_codex_command(self, cmd: list) -> str:
        """Execute Codex CLI command and return output.

        Args:
            cmd: Command list to execute

        Returns:
            stdout output from command

        Raises:
            LLMTimeoutException: If command times out
            LLMConnectionException: If CLI not found
            LLMException: If command fails
        """
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                text=True,
                check=False  # Don't raise on non-zero returncode, handle manually
            )

            # Check exit code
            if result.returncode == 2:
                # Exit code 2 = authentication failure
                self.metrics['errors'] += 1
                raise LLMConnectionException(
                    provider='openai-codex',
                    url=self.codex_command,
                    details=f"Authentication failed. Run `codex --login` or set OPENAI_API_KEY.\n"
                           f"stderr: {result.stderr}"
                )

            if result.returncode != 0:
                # Non-zero exit code (not auth failure)
                self.metrics['errors'] += 1
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Codex CLI failed (code {result.returncode}): {error_msg}")
                raise LLMException(
                    f"Codex CLI error (exit {result.returncode}): {error_msg}",
                    context={'command': ' '.join(cmd), 'returncode': result.returncode},
                    recovery='Check Codex CLI installation and authentication'
                )

            # Success - return stdout
            response = result.stdout.strip()

            if not response:
                raise LLMResponseException(
                    provider='openai-codex',
                    details="Empty response from Codex CLI"
                )

            return response

        except subprocess.TimeoutExpired as e:
            self.metrics['timeouts'] += 1
            logger.error(f"Codex CLI timeout after {self.timeout}s")
            raise LLMTimeoutException(
                provider='openai-codex',
                model=self.model,
                timeout_seconds=self.timeout
            ) from e

        except FileNotFoundError as e:
            self.metrics['errors'] += 1
            logger.error(f"Codex CLI not found: {self.codex_command}")
            raise LLMConnectionException(
                provider='openai-codex',
                url=self.codex_command,
                details=f"Codex CLI not installed at: {self.codex_command}"
            ) from e

        except (LLMException, LLMConnectionException, LLMTimeoutException):
            # Re-raise our custom exceptions
            raise

        except (ConnectionError, TimeoutError, OSError) as e:
            # Re-raise retryable exceptions so retry manager can handle them
            logger.warning(f"Retryable error in Codex CLI: {e}")
            raise

        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Codex CLI unexpected error: {e}")
            raise LLMException(
                f"Unexpected CLI error: {e}",
                context={'command': ' '.join(cmd)},
                recovery='Check system resources and Codex CLI logs'
            ) from e

    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]:
        """Generate with streaming output.

        Note: Codex CLI `exec` command does not support streaming in the same way
        as the interactive mode. This implementation calls generate() and yields
        the result word-by-word for compatibility.

        Args:
            prompt: Input prompt
            **kwargs: Additional parameters

        Yields:
            Text chunks (words)

        Example:
            >>> for chunk in llm.generate_stream("Write a story"):
            ...     print(chunk, end='', flush=True)
        """
        # Codex exec doesn't stream, so we fake it by yielding words
        response = self.generate(prompt, **kwargs)

        # Yield word by word
        words = response.split()
        for word in words:
            yield word + ' '

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count

        Example:
            >>> count = llm.estimate_tokens("Hello world")
            >>> print(count)  # ~2-3 tokens
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
        word_count = len(text.split())
        return int(word_count * 1.3)

    def is_available(self) -> bool:
        """Check if Codex CLI is accessible and authenticated.

        Quick health check that runs `codex --version` to verify:
        - CLI is installed
        - CLI is working
        - CLI is authenticated (exit code 0 means auth OK)

        Returns:
            True if CLI is available and authenticated, False otherwise

        Example:
            >>> if llm.is_available():
            ...     response = llm.generate(prompt)
        """
        try:
            result = subprocess.run(
                [self.codex_command, '--version'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True,
                check=False
            )

            # Exit code 0 = success (CLI working and authenticated)
            # Exit code 2 = auth failure
            # Other codes = other issues
            return result.returncode == 0

        except Exception as e:
            logger.debug(f"Codex CLI health check failed: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information.

        Returns:
            Dictionary with model information:
                - model_name: str
                - context_length: int (estimated)
                - provider: str
                - type: str
                - execution_mode: str

        Example:
            >>> info = llm.get_model_info()
            >>> print(info['model_name'])  # 'gpt-5-codex'
        """
        # Context lengths for different models (from Codex CLI docs)
        context_lengths = {
            'codex-mini-latest': 8192,
            'o4-mini': 8192,
            'gpt-5-codex': 128000,
            'gpt-5': 128000,
            'o3': 128000,
        }

        return {
            'model_name': self.model,
            'context_length': context_lengths.get(self.model, 8192),
            'provider': 'openai-codex',
            'type': 'cli',
            'execution_mode': 'subprocess'
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics.

        Returns:
            Dictionary with metrics:
                - calls: Total number of generate() calls
                - total_tokens: Total tokens generated (estimated)
                - total_latency_ms: Total latency in milliseconds
                - errors: Number of errors
                - timeouts: Number of timeouts
                - avg_latency_ms: Average latency per call
                - tokens_per_second: Average generation speed

        Example:
            >>> metrics = llm.get_metrics()
            >>> print(f"Avg latency: {metrics['avg_latency_ms']:.1f}ms")
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

        return metrics
