"""Context window management with prioritization and summarization.

This module implements the ContextManager class for managing context within
token limits using priority-based inclusion and summarization.

Example:
    >>> manager = ContextManager(token_counter, llm_interface)
    >>> context = manager.build_context(items, max_tokens=10000)
    >>> print(f"Built context: {len(context)} characters")
"""

import hashlib
import logging
from datetime import datetime, UTC
from typing import List, Dict, Any, Tuple, Optional
from threading import RLock

from src.core.models import Task
from src.utils.token_counter import TokenCounter

logger = logging.getLogger(__name__)


class ContextManager:
    """Context window management with prioritization and summarization.

    Manages context to fit within token limits by:
    - Prioritizing most relevant information
    - Summarizing less important content
    - Caching built contexts for reuse

    Thread-safe for concurrent access.

    Example:
        >>> manager = ContextManager(token_counter)
        >>> items = [
        ...     {'type': 'task', 'content': 'Implement feature X', 'priority': 10},
        ...     {'type': 'code', 'content': 'def foo(): pass', 'priority': 8}
        ... ]
        >>> context = manager.build_context(items, max_tokens=1000)
    """

    # Priority weights for different factors
    WEIGHT_RECENCY = 0.3
    WEIGHT_RELEVANCE = 0.4
    WEIGHT_IMPORTANCE = 0.2
    WEIGHT_SIZE_EFFICIENCY = 0.1

    # Default priority order for context items
    DEFAULT_PRIORITY_ORDER = [
        'current_task_description',
        'recent_errors',
        'active_code_files',
        'task_dependencies',
        'project_goals',
        'conversation_history',
        'documentation'
    ]

    def __init__(
        self,
        token_counter: TokenCounter,
        llm_interface: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize context manager.

        Args:
            token_counter: TokenCounter instance for measuring text
            llm_interface: Optional LLM interface for summarization
            config: Optional configuration dictionary
        """
        self.token_counter = token_counter
        self.llm_interface = llm_interface
        self.config = config or {}
        self._lock = RLock()

        # Context storage
        self._context_items: List[Dict[str, Any]] = []
        self._context_cache: Dict[str, str] = {}

        # Configuration
        self._max_tokens = self.config.get('max_tokens', 100000)
        self._summarization_threshold = self.config.get('summarization_threshold', 50000)
        self._compression_ratio = self.config.get('compression_ratio', 0.3)

        logger.info("ContextManager initialized")

    def build_context(
        self,
        items: List[Dict[str, Any]],
        max_tokens: int,
        priority_order: Optional[List[str]] = None
    ) -> str:
        """Build context from items within token limit.

        Args:
            items: List of context items with 'type', 'content', optional 'priority'
            max_tokens: Maximum tokens allowed
            priority_order: Optional priority ordering for types

        Returns:
            Built context string

        Example:
            >>> items = [{'type': 'task', 'content': 'Do X', 'priority': 10}]
            >>> context = manager.build_context(items, max_tokens=1000)
        """
        with self._lock:
            # Check cache
            cache_key = self._get_cache_key(items, max_tokens)
            if cache_key in self._context_cache:
                logger.debug("Context cache hit")
                return self._context_cache[cache_key]

            # Prioritize items
            priority_order = priority_order or self.DEFAULT_PRIORITY_ORDER
            prioritized = self.prioritize_context(items, None, priority_order)

            # Build context greedily
            context_parts = []
            current_tokens = 0

            for item, score in prioritized:
                content = item.get('content', '')
                item_tokens = self.token_counter.count_tokens(content)

                # Check if adding this item would exceed limit
                if current_tokens + item_tokens <= max_tokens:
                    context_parts.append(content)
                    current_tokens += item_tokens
                else:
                    # Try summarizing remaining items if LLM available
                    remaining_items = [i for i, s in prioritized[len(context_parts):]]
                    if remaining_items and self.llm_interface:
                        remaining_text = "\n\n".join(i.get('content', '') for i in remaining_items)
                        tokens_available = max_tokens - current_tokens

                        if tokens_available > 100:  # Need some space for summary
                            summary = self.summarize_context(remaining_text, tokens_available)
                            context_parts.append(f"\n[Summarized content below]\n{summary}")

                    break

            # Join and cache
            final_context = "\n\n".join(context_parts)
            self._context_cache[cache_key] = final_context

            logger.info(f"Built context: {current_tokens}/{max_tokens} tokens")
            return final_context

    def prioritize_context(
        self,
        items: List[Dict[str, Any]],
        task: Optional[Task] = None,
        priority_order: Optional[List[str]] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Prioritize context items by relevance score.

        Scoring factors:
        - Recency (30%): How recent the item is
        - Relevance (40%): Keyword overlap with task
        - Importance (20%): Manual priority assignment
        - Size efficiency (10%): Information density

        Args:
            items: List of context items
            task: Optional task for relevance scoring
            priority_order: Optional type priority ordering

        Returns:
            List of (item, score) tuples, sorted by score (highest first)

        Example:
            >>> items = [{'type': 'code', 'content': 'def foo(): pass'}]
            >>> prioritized = manager.prioritize_context(items)
            >>> assert all(isinstance(score, float) for _, score in prioritized)
        """
        priority_order = priority_order or self.DEFAULT_PRIORITY_ORDER
        scored_items = []

        for item in items:
            score = self._score_context_item(item, task, priority_order)
            scored_items.append((item, score))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[1], reverse=True)

        return scored_items

    def _score_context_item(
        self,
        item: Dict[str, Any],
        task: Optional[Task],
        priority_order: List[str]
    ) -> float:
        """Score a single context item.

        Args:
            item: Context item
            task: Optional task
            priority_order: Type priority ordering

        Returns:
            Score (0.0-1.0)
        """
        score = 0.0

        # Recency score
        if 'timestamp' in item:
            try:
                timestamp = item['timestamp']
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                days_old = (datetime.now(UTC) - timestamp).days
                recency_score = 1.0 / (1.0 + days_old)
            except:
                recency_score = 0.5  # Default
        else:
            recency_score = 0.5

        score += recency_score * self.WEIGHT_RECENCY

        # Relevance score (keyword overlap)
        if task and task.description:
            content = item.get('content', '').lower()
            task_words = set(task.description.lower().split())
            content_words = set(content.split())
            overlap = len(task_words & content_words)
            relevance_score = min(1.0, overlap / max(len(task_words), 1))
        else:
            relevance_score = 0.5

        score += relevance_score * self.WEIGHT_RELEVANCE

        # Importance score (priority + type priority)
        importance_score = item.get('priority', 5) / 10.0  # Normalize to 0-1

        # Add type priority bonus
        item_type = item.get('type', '')
        if item_type in priority_order:
            type_priority = (len(priority_order) - priority_order.index(item_type)) / len(priority_order)
            importance_score = (importance_score + type_priority) / 2.0

        score += importance_score * self.WEIGHT_IMPORTANCE

        # Size efficiency score
        content = item.get('content', '')
        if content:
            words = len(content.split())
            tokens = self.token_counter.estimate_tokens(content)
            efficiency = words / max(tokens, 1)  # Words per token
            efficiency_score = min(1.0, efficiency / 2.0)  # Normalize
        else:
            efficiency_score = 0.0

        score += efficiency_score * self.WEIGHT_SIZE_EFFICIENCY

        return min(1.0, max(0.0, score))

    def summarize_context(
        self,
        text: str,
        target_tokens: int
    ) -> str:
        """Summarize context using local LLM.

        Falls back to extractive summarization if LLM unavailable.

        Args:
            text: Text to summarize
            target_tokens: Target token count

        Returns:
            Summarized text

        Example:
            >>> text = "Long text..." * 100
            >>> summary = manager.summarize_context(text, target_tokens=100)
            >>> assert len(summary) < len(text)
        """
        if not self.llm_interface:
            # Fall back to extractive summarization
            return self._extractive_summary(text, target_tokens)

        # Use LLM for summarization
        prompt = f"""Summarize the following context concisely, preserving key information:

{text}

Target length: approximately {target_tokens} tokens.

Summary:"""

        try:
            summary = self.llm_interface.send_prompt(prompt)
            # Verify it fits
            if self.token_counter.count_tokens(summary) <= target_tokens:
                return summary
            else:
                # Truncate if still too long
                return self.token_counter.truncate_to_tokens(summary, target_tokens)
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}, using extractive")
            return self._extractive_summary(text, target_tokens)

    def _extractive_summary(self, text: str, target_tokens: int) -> str:
        """Extract key sentences to create summary.

        Args:
            text: Text to summarize
            target_tokens: Target token count

        Returns:
            Extractive summary
        """
        # Split into sentences
        sentences = [s.strip() for s in text.split('.') if s.strip()]

        if not sentences:
            return text[:int(target_tokens * self.token_counter.CHARS_PER_TOKEN)]

        # Take first and last sentences, fill middle
        summary_parts = []
        current_tokens = 0

        # Always include first sentence
        if sentences:
            first = sentences[0] + '.'
            summary_parts.append(first)
            current_tokens += self.token_counter.estimate_tokens(first)

        # Include middle sentences if space
        for sent in sentences[1:-1]:
            sent_with_period = sent + '.'
            sent_tokens = self.token_counter.estimate_tokens(sent_with_period)

            if current_tokens + sent_tokens < target_tokens - 50:  # Reserve space for last
                summary_parts.append(sent_with_period)
                current_tokens += sent_tokens
            else:
                break

        # Always include last sentence if different from first
        if len(sentences) > 1:
            last = sentences[-1] + '.'
            summary_parts.append(last)

        return " ".join(summary_parts)

    def compress_context(
        self,
        text: str,
        compression_ratio: float
    ) -> str:
        """Compress context by removing redundancy.

        Args:
            text: Text to compress
            compression_ratio: Target compression (0.0-1.0)

        Returns:
            Compressed text

        Example:
            >>> text = "Hello world. Hello world."
            >>> compressed = manager.compress_context(text, compression_ratio=0.5)
        """
        target_tokens = int(self.token_counter.count_tokens(text) * compression_ratio)
        return self.summarize_context(text, target_tokens)

    def add_to_context(
        self,
        item: Dict[str, Any],
        priority: int = 5
    ) -> None:
        """Add item to context storage.

        Args:
            item: Context item with 'type' and 'content'
            priority: Priority level (0-10)

        Example:
            >>> manager.add_to_context({'type': 'note', 'content': 'Important'}, priority=10)
        """
        with self._lock:
            item['priority'] = priority
            item['timestamp'] = datetime.now(UTC)
            self._context_items.append(item)
            logger.debug(f"Added context item: {item.get('type')}")

    def search_context(
        self,
        query: str,
        top_k: int = 5
    ) -> List[str]:
        """Search context items for relevant content.

        Uses simple keyword matching. For better results, consider
        implementing semantic search with embeddings (future enhancement).

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of matching content strings

        Example:
            >>> manager.add_to_context({'type': 'note', 'content': 'Python code'})
            >>> results = manager.search_context('Python', top_k=5)
        """
        with self._lock:
            query_words = set(query.lower().split())
            scored_items = []

            for item in self._context_items:
                content = item.get('content', '').lower()
                content_words = set(content.split())

                # Calculate overlap score
                overlap = len(query_words & content_words)
                if overlap > 0:
                    score = overlap / len(query_words)
                    scored_items.append((item.get('content', ''), score))

            # Sort by score and return top K
            scored_items.sort(key=lambda x: x[1], reverse=True)
            return [content for content, _ in scored_items[:top_k]]

    def get_relevant_context(
        self,
        task: Task,
        max_tokens: int
    ) -> str:
        """Get relevant context for a task.

        Args:
            task: Task to get context for
            max_tokens: Maximum tokens allowed

        Returns:
            Relevant context string

        Example:
            >>> context = manager.get_relevant_context(task, max_tokens=1000)
        """
        return self.build_context(self._context_items, max_tokens)

    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update context storage with new information.

        Args:
            updates: Dictionary of updates

        Example:
            >>> manager.update_context({'new_data': 'value'})
        """
        with self._lock:
            for key, value in updates.items():
                self.add_to_context({
                    'type': key,
                    'content': str(value),
                    'timestamp': datetime.now(UTC)
                })

    def clear_context(self) -> None:
        """Clear all context storage.

        Example:
            >>> manager.clear_context()
            >>> assert len(manager._context_items) == 0
        """
        with self._lock:
            self._context_items.clear()
            self._context_cache.clear()
            logger.info("Context cleared")

    def _get_cache_key(self, items: List[Dict[str, Any]], max_tokens: int) -> str:
        """Generate cache key for context items.

        Args:
            items: Context items
            max_tokens: Max tokens

        Returns:
            Cache key string
        """
        # Create hash from items and max_tokens
        items_str = str(sorted([(i.get('type'), i.get('content', '')[:100]) for i in items]))
        key_data = f"{items_str}:{max_tokens}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """Get context manager statistics.

        Returns:
            Dictionary with statistics

        Example:
            >>> stats = manager.get_stats()
            >>> assert 'total_items' in stats
        """
        with self._lock:
            return {
                'total_items': len(self._context_items),
                'cache_size': len(self._context_cache),
                'max_tokens': self._max_tokens,
                'summarization_threshold': self._summarization_threshold
            }
