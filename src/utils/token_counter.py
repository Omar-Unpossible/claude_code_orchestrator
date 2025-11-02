"""Token counting with caching and model-specific tokenization.

This module implements the TokenCounter class for accurate token counting,
supporting multiple tokenizers and providing caching for performance.

Example:
    >>> counter = TokenCounter()
    >>> tokens = counter.count_tokens("Hello, world!", model="gpt-4")
    >>> print(f"Token count: {tokens}")

    >>> if counter.fits_in_context(text, max_tokens=1000):
    ...     send_to_llm(text)
"""

import hashlib
import logging
from functools import lru_cache
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class TokenCounter:
    """Accurate token counting for context management.

    Provides token counting with caching, model-specific tokenizers,
    and estimation for unknown models.

    Attributes:
        supported_models: Dictionary of supported models and their configurations
        cache_hits: Number of cache hits for performance tracking
        cache_misses: Number of cache misses

    Example:
        >>> counter = TokenCounter()
        >>> count = counter.count_tokens("def hello(): pass", model="gpt-4")
        >>> batch_counts = counter.count_batch(["text1", "text2"])
    """

    # Model configurations
    MODELS = {
        'claude-sonnet-4': {
            'tokenizer': 'cl100k_base',
            'context_window': 200000
        },
        'qwen2.5-coder': {
            'tokenizer': 'cl100k_base',
            'context_window': 32768
        },
        'gpt-4': {
            'tokenizer': 'cl100k_base',
            'context_window': 8192
        },
        'gpt-4-turbo': {
            'tokenizer': 'cl100k_base',
            'context_window': 128000
        }
    }

    # Default estimation: ~4 characters per token
    CHARS_PER_TOKEN = 4.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize token counter.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._encoding_cache: Dict[str, Any] = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # Try to import tiktoken
        try:
            import tiktoken
            self._tiktoken = tiktoken
            self._tiktoken_available = True
            logger.info("TokenCounter initialized with tiktoken support")
        except ImportError:
            self._tiktoken = None
            self._tiktoken_available = False
            logger.warning("tiktoken not available, using character-based estimation")

    def get_encoding_for_model(self, model: str) -> Any:
        """Get tiktoken encoding for a model.

        Args:
            model: Model name

        Returns:
            Tiktoken encoding object

        Raises:
            ImportError: If tiktoken not available
            ValueError: If model not supported
        """
        if not self._tiktoken_available:
            raise ImportError("tiktoken not installed")

        # Check cache first
        if model in self._encoding_cache:
            return self._encoding_cache[model]

        # Get tokenizer name for model
        model_config = self.MODELS.get(model)
        if not model_config:
            logger.warning(f"Unknown model: {model}, using cl100k_base")
            tokenizer_name = 'cl100k_base'
        else:
            tokenizer_name = model_config['tokenizer']

        # Get encoding
        try:
            encoding = self._tiktoken.get_encoding(tokenizer_name)
            self._encoding_cache[model] = encoding
            return encoding
        except Exception as e:
            logger.error(f"Failed to get encoding for {model}: {e}")
            raise

    @lru_cache(maxsize=1000)
    def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in text using model-specific tokenizer.

        Uses LRU cache for performance. Cached by text and model.

        Args:
            text: Text to count tokens for
            model: Model name (optional, defaults to estimation)

        Returns:
            Number of tokens

        Example:
            >>> counter = TokenCounter()
            >>> count = counter.count_tokens("Hello, world!")
            >>> assert count > 0
        """
        if not text:
            return 0

        # If tiktoken available and model specified, use exact counting
        if self._tiktoken_available and model:
            try:
                encoding = self.get_encoding_for_model(model)
                token_count = len(encoding.encode(text))
                self.cache_misses += 1  # First time
                return token_count
            except Exception as e:
                logger.warning(f"Tokenizer counting failed: {e}, falling back to estimation")

        # Fall back to estimation
        return self.estimate_tokens(text)

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using character count.

        Uses rough approximation of 4 characters per token.
        Accuracy typically within 20%.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count

        Example:
            >>> counter = TokenCounter()
            >>> estimate = counter.estimate_tokens("Hello, world!")
            >>> assert estimate >= 3  # Rough estimate
        """
        if not text:
            return 0

        # Simple estimation: characters / 4
        return int(len(text) / self.CHARS_PER_TOKEN)

    def count_batch(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[int]:
        """Count tokens for multiple texts efficiently.

        Args:
            texts: List of texts to count
            model: Model name (optional)

        Returns:
            List of token counts

        Example:
            >>> counter = TokenCounter()
            >>> counts = counter.count_batch(["text1", "text2"])
            >>> assert len(counts) == 2
        """
        return [self.count_tokens(text, model) for text in texts]

    def fits_in_context(
        self,
        text: str,
        max_tokens: int,
        model: Optional[str] = None
    ) -> bool:
        """Check if text fits within token budget.

        Args:
            text: Text to check
            max_tokens: Maximum allowed tokens
            model: Model name (optional)

        Returns:
            True if text fits, False otherwise

        Example:
            >>> counter = TokenCounter()
            >>> fits = counter.fits_in_context("Hello", max_tokens=1000)
            >>> assert fits is True
        """
        token_count = self.count_tokens(text, model)
        return token_count <= max_tokens

    def truncate_to_tokens(
        self,
        text: str,
        max_tokens: int,
        model: Optional[str] = None,
        strategy: str = 'middle'
    ) -> str:
        """Truncate text to fit within token budget.

        Supports different truncation strategies:
        - 'middle': Keep beginning and end, truncate middle
        - 'end': Truncate from end
        - 'start': Truncate from start

        Args:
            text: Text to truncate
            max_tokens: Maximum allowed tokens
            model: Model name (optional)
            strategy: Truncation strategy ('middle', 'end', 'start')

        Returns:
            Truncated text

        Example:
            >>> counter = TokenCounter()
            >>> truncated = counter.truncate_to_tokens("Long text...", max_tokens=10)
            >>> assert counter.count_tokens(truncated) <= 10
        """
        current_tokens = self.count_tokens(text, model)

        # Already fits
        if current_tokens <= max_tokens:
            return text

        # Calculate target character count (conservative estimate)
        target_chars = int(max_tokens * self.CHARS_PER_TOKEN * 0.9)  # 10% safety margin

        if strategy == 'middle':
            # Keep first half and last half
            if len(text) <= target_chars:
                return text

            keep_per_side = target_chars // 2
            truncated = (
                text[:keep_per_side] +
                "\n\n... [truncated] ...\n\n" +
                text[-keep_per_side:]
            )

            # Verify fits (may need another iteration)
            if self.count_tokens(truncated, model) > max_tokens:
                # Recurse with smaller target
                return self.truncate_to_tokens(
                    truncated,
                    max_tokens,
                    model,
                    strategy='middle'
                )

            return truncated

        elif strategy == 'end':
            # Truncate from end
            truncated = text[:target_chars] + "\n\n... [truncated]"

            # Verify and adjust if needed
            while self.count_tokens(truncated, model) > max_tokens and target_chars > 0:
                target_chars = int(target_chars * 0.9)
                truncated = text[:target_chars] + "\n\n... [truncated]"

            return truncated

        elif strategy == 'start':
            # Truncate from start
            truncated = "[truncated] ...\n\n" + text[-target_chars:]

            # Verify and adjust if needed
            while self.count_tokens(truncated, model) > max_tokens and target_chars > 0:
                target_chars = int(target_chars * 0.9)
                truncated = "[truncated] ...\n\n" + text[-target_chars:]

            return truncated

        else:
            raise ValueError(f"Unknown truncation strategy: {strategy}")

    def get_model_context_window(self, model: str) -> int:
        """Get context window size for a model.

        Args:
            model: Model name

        Returns:
            Context window size in tokens

        Example:
            >>> counter = TokenCounter()
            >>> window = counter.get_model_context_window("gpt-4")
            >>> assert window == 8192
        """
        model_config = self.MODELS.get(model)
        if not model_config:
            logger.warning(f"Unknown model: {model}, returning default")
            return 4096  # Conservative default

        return model_config['context_window']

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics for performance monitoring.

        Returns:
            Dictionary with cache hits and misses

        Example:
            >>> counter = TokenCounter()
            >>> counter.count_tokens("test")
            >>> counter.count_tokens("test")  # Cache hit
            >>> stats = counter.get_cache_stats()
            >>> assert 'hits' in stats
        """
        # Get LRU cache info
        cache_info = self.count_tokens.cache_info()

        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'size': cache_info.currsize,
            'maxsize': cache_info.maxsize
        }

    def clear_cache(self) -> None:
        """Clear the token count cache.

        Useful for testing or when memory is constrained.

        Example:
            >>> counter = TokenCounter()
            >>> counter.count_tokens("test")
            >>> counter.clear_cache()
            >>> stats = counter.get_cache_stats()
            >>> assert stats['size'] == 0
        """
        self.count_tokens.cache_clear()
        logger.info("Token count cache cleared")
