"""Working Memory (Tier 1) for Orchestrator context management.

This module implements a FIFO buffer of recent operations with adaptive sizing
based on context window size. Working memory provides fast access to recent
operations for context building and reference resolution.

Classes:
    WorkingMemory: FIFO buffer with adaptive sizing and token tracking

Example:
    >>> config = {'context_window': 128000, 'max_operations': 50}
    >>> memory = WorkingMemory(config)
    >>> memory.add_operation({'type': 'task', 'data': '...', 'tokens': 500})
    >>> recent = memory.get_recent_operations(limit=10)

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import logging
import threading
from collections import deque
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WorkingMemoryException(Exception):
    """Exception raised for working memory errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            context: Additional context about the error
        """
        super().__init__(message)
        self.context = context or {}
        logger.error(f"WorkingMemoryException: {message}", extra=context)


class WorkingMemory:
    """FIFO working memory buffer with adaptive sizing.

    Maintains a sliding window of recent operations with automatic eviction
    when capacity limits are exceeded. Supports adaptive sizing based on
    context window size.

    Attributes:
        max_operations: Maximum number of operations to store
        max_tokens: Maximum total tokens across all operations
        _operations: Deque storing operation records
        _current_tokens: Current total token count
        _lock: Thread lock for concurrent access
        _eviction_count: Number of operations evicted

    Example:
        >>> memory = WorkingMemory({'context_window': 128000})
        >>> memory.add_operation({
        ...     'type': 'task',
        ...     'operation': 'create_task',
        ...     'data': {'title': 'Example'},
        ...     'tokens': 100,
        ...     'timestamp': '2025-01-15T10:00:00'
        ... })
        >>> recent = memory.get_recent_operations(limit=5)
        >>> len(recent)
        1
    """

    # Default sizing based on context windows
    DEFAULT_SIZING = {
        4000: {'max_operations': 10, 'max_tokens_pct': 0.05},      # 4K: 10 ops, 5%
        8000: {'max_operations': 20, 'max_tokens_pct': 0.05},      # 8K: 20 ops, 5%
        16000: {'max_operations': 30, 'max_tokens_pct': 0.07},     # 16K: 30 ops, 7%
        32000: {'max_operations': 40, 'max_tokens_pct': 0.08},     # 32K: 40 ops, 8%
        128000: {'max_operations': 50, 'max_tokens_pct': 0.10},    # 128K: 50 ops, 10%
        200000: {'max_operations': 75, 'max_tokens_pct': 0.10},    # 200K: 75 ops, 10%
        1000000: {'max_operations': 100, 'max_tokens_pct': 0.10},  # 1M: 100 ops, 10%
    }

    def __init__(self, config: Dict[str, Any]):
        """Initialize working memory.

        Args:
            config: Configuration dictionary with keys:
                - context_window (int): Context window size in tokens
                - max_operations (int, optional): Override default max operations
                - max_tokens (int, optional): Override default max tokens
                - max_tokens_pct (float, optional): Percentage of context for tokens

        Raises:
            WorkingMemoryException: If configuration is invalid
        """
        if not isinstance(config, dict):
            raise WorkingMemoryException(
                "Configuration must be a dictionary",
                context={'config_type': type(config).__name__}
            )

        context_window = config.get('context_window')
        if not context_window or not isinstance(context_window, int) or context_window <= 0:
            raise WorkingMemoryException(
                "Invalid context_window in configuration",
                context={'context_window': context_window}
            )

        # Calculate adaptive sizing
        sizing = self._calculate_adaptive_sizing(context_window, config)

        self.max_operations = sizing['max_operations']
        self.max_tokens = sizing['max_tokens']
        self.context_window = context_window

        # Initialize state
        self._operations: deque = deque(maxlen=self.max_operations)
        self._current_tokens = 0
        self._lock = threading.RLock()
        self._eviction_count = 0

        logger.info(
            f"WorkingMemory initialized: context={context_window:,}, "
            f"max_ops={self.max_operations}, max_tokens={self.max_tokens:,}"
        )

    def _calculate_adaptive_sizing(
        self,
        context_window: int,
        config: Dict[str, Any]
    ) -> Dict[str, int]:
        """Calculate adaptive sizing based on context window.

        Args:
            context_window: Context window size in tokens
            config: Configuration dictionary (may contain overrides)

        Returns:
            Dictionary with 'max_operations' and 'max_tokens'
        """
        # Find appropriate default sizing
        default_size = None
        for threshold in sorted(self.DEFAULT_SIZING.keys()):
            if context_window <= threshold:
                default_size = self.DEFAULT_SIZING[threshold].copy()
                break

        if default_size is None:
            # Use largest default for very large contexts
            default_size = self.DEFAULT_SIZING[max(self.DEFAULT_SIZING.keys())].copy()

        # Calculate max_tokens from percentage
        max_tokens_pct = config.get('max_tokens_pct', default_size['max_tokens_pct'])
        default_max_tokens = int(context_window * max_tokens_pct)

        # Apply configuration overrides
        max_operations = config.get('max_operations', default_size['max_operations'])
        max_tokens = config.get('max_tokens', default_max_tokens)

        logger.debug(
            f"Adaptive sizing for context={context_window:,}: "
            f"max_ops={max_operations}, max_tokens={max_tokens:,} "
            f"({max_tokens_pct:.1%} of context)"
        )

        return {
            'max_operations': max_operations,
            'max_tokens': max_tokens
        }

    def add_operation(self, operation: Dict[str, Any]) -> None:
        """Add an operation to working memory.

        Automatically evicts oldest operations if capacity exceeded.

        Args:
            operation: Operation record with keys:
                - type (str): Operation type (e.g., 'task', 'nl_command')
                - operation (str): Specific operation (e.g., 'create_task')
                - data (dict): Operation data
                - tokens (int): Token count for this operation
                - timestamp (str): ISO timestamp

        Raises:
            WorkingMemoryException: If operation format is invalid
        """
        with self._lock:
            # Validate operation
            if not isinstance(operation, dict):
                raise WorkingMemoryException(
                    "Operation must be a dictionary",
                    context={'operation_type': type(operation).__name__}
                )

            required_fields = ['type', 'operation', 'tokens']
            missing = [f for f in required_fields if f not in operation]
            if missing:
                raise WorkingMemoryException(
                    "Operation missing required fields",
                    context={'missing_fields': missing, 'operation': operation}
                )

            tokens = operation.get('tokens', 0)
            if not isinstance(tokens, int) or tokens < 0:
                raise WorkingMemoryException(
                    "Invalid token count",
                    context={'tokens': tokens}
                )

            # Add timestamp if not present
            if 'timestamp' not in operation:
                operation['timestamp'] = datetime.now(timezone.utc).isoformat()

            # Check token budget before adding
            # Evict operations if needed to make room
            while (self._current_tokens + tokens > self.max_tokens and
                   len(self._operations) > 0):
                self._evict_oldest()

            # Add operation (deque handles maxlen automatically for count limit)
            if len(self._operations) >= self.max_operations:
                self._evict_oldest()

            self._operations.append(operation)
            self._current_tokens += tokens

            logger.debug(
                f"Added operation: type={operation['type']}, "
                f"op={operation['operation']}, tokens={tokens}, "
                f"total={self._current_tokens}/{self.max_tokens}"
            )

    def _evict_oldest(self) -> None:
        """Evict the oldest operation (FIFO)."""
        if len(self._operations) == 0:
            return

        evicted = self._operations.popleft()
        evicted_tokens = evicted.get('tokens', 0)
        self._current_tokens -= evicted_tokens
        self._eviction_count += 1

        logger.debug(
            f"Evicted operation: type={evicted['type']}, "
            f"tokens={evicted_tokens}, eviction_count={self._eviction_count}"
        )

    def get_all_operations(self) -> List[Dict[str, Any]]:
        """Get all operations in chronological order.

        Returns:
            List of operation dictionaries (oldest to newest)
        """
        with self._lock:
            return list(self._operations)

    def get_recent_operations(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent operations (most recent first).

        Args:
            limit: Maximum number of operations to return (default: all)

        Returns:
            List of operation dictionaries (newest to oldest)
        """
        with self._lock:
            operations = list(reversed(self._operations))
            if limit is not None:
                operations = operations[:limit]
            return operations

    def get_operations(
        self,
        operation_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get operations filtered by type.

        Args:
            operation_type: Filter by operation type (e.g., 'task', 'nl_command')
                If None, returns all operations
            limit: Maximum number of operations to return

        Returns:
            List of operation dictionaries (newest to oldest)
        """
        with self._lock:
            if operation_type is None:
                return self.get_recent_operations(limit)

            filtered = [
                op for op in reversed(self._operations)
                if op.get('type') == operation_type
            ]
            return filtered[:limit]

    def search(self, query: str, max_results: int = 5) -> List[str]:
        """Search operations by keyword.

        Performs case-insensitive keyword search across operation data.

        Args:
            query: Search keyword
            max_results: Maximum number of results to return

        Returns:
            List of operation summaries matching the query
        """
        with self._lock:
            query_lower = query.lower()
            results = []

            for op in reversed(self._operations):
                # Search in operation type, operation name, and data
                searchable = f"{op.get('type', '')} {op.get('operation', '')} {str(op.get('data', ''))}"
                if query_lower in searchable.lower():
                    # Include data snippet in summary for context
                    data_str = str(op.get('data', {}))
                    data_preview = data_str[:50] + '...' if len(data_str) > 50 else data_str

                    summary = (
                        f"{op.get('timestamp', 'N/A')}: "
                        f"{op.get('type', 'unknown')}/{op.get('operation', 'unknown')} "
                        f"- {data_preview}"
                    )
                    results.append(summary)

                    if len(results) >= max_results:
                        break

            return results

    def clear(self) -> None:
        """Clear all operations from working memory."""
        with self._lock:
            self._operations.clear()
            self._current_tokens = 0
            logger.info("Working memory cleared")

    def get_status(self) -> Dict[str, Any]:
        """Get current status of working memory.

        Returns:
            Dictionary with status information
        """
        with self._lock:
            return {
                'operation_count': len(self._operations),
                'max_operations': self.max_operations,
                'current_tokens': self._current_tokens,
                'max_tokens': self.max_tokens,
                'token_utilization': self._current_tokens / self.max_tokens if self.max_tokens > 0 else 0,
                'eviction_count': self._eviction_count,
                'context_window': self.context_window
            }

    def __len__(self) -> int:
        """Get number of operations in memory."""
        with self._lock:
            return len(self._operations)

    def __repr__(self) -> str:
        """String representation of working memory."""
        with self._lock:
            return (
                f"WorkingMemory(ops={len(self._operations)}/{self.max_operations}, "
                f"tokens={self._current_tokens}/{self.max_tokens})"
            )
