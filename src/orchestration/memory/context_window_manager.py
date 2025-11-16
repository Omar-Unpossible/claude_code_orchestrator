"""Context window manager with utilization limits and adaptive thresholds.

This module provides the ContextWindowManager class which tracks context window
usage, applies utilization limits, and manages threshold-based zones.

Classes:
    ContextWindowManager: Manage context window with adaptive thresholds

Example:
    >>> from src.core.model_config_loader import ModelConfigLoader
    >>> loader = ModelConfigLoader()
    >>> model_config = loader.get_active_orchestrator_config()
    >>> manager = ContextWindowManager(model_config, utilization_limit=0.75)
    >>> manager.add_usage(50000)
    >>> print(manager.get_zone())
    'yellow'

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import logging
from typing import Dict, Any, Optional
from threading import RLock

logger = logging.getLogger(__name__)


class ContextWindowManager:
    """Manage Orchestrator's context window with adaptive thresholds.

    This class tracks cumulative token usage across operations and triggers
    actions when usage crosses threshold zones (green, yellow, orange, red).
    Supports configurable utilization limits to use less than full capacity.

    Thread-safe: Yes (uses RLock for concurrent operations)

    Attributes:
        max_tokens: Maximum context window size (configured)
        utilization_limit: Fraction of max_tokens to actually use (0.0-1.0)
        effective_max_tokens: Actual maximum after applying utilization limit
        thresholds: Dictionary mapping zone names to absolute token counts
        used_tokens: Current token usage count

    Example:
        >>> # Use only 75% of 128K context window
        >>> config = {'model': 'qwen2.5-coder:32b', 'context_window': 128000}
        >>> manager = ContextWindowManager(config, utilization_limit=0.75)
        >>> print(f"Effective max: {manager.effective_max_tokens:,}")
        Effective max: 96,000
        >>> manager.add_usage(70000)
        >>> print(manager.get_zone())
        'yellow'
    """

    # Industry-standard threshold percentages
    DEFAULT_THRESHOLDS = {
        'green_upper': 0.50,     # 50% - normal operation
        'yellow_upper': 0.70,    # 70% - monitor and plan checkpoint
        'orange_upper': 0.85,    # 85% - optimize then checkpoint
        'red': 0.95              # 95% - emergency checkpoint
    }

    def __init__(
        self,
        model_config: Dict[str, Any],
        utilization_limit: float = 1.0,
        custom_thresholds: Optional[Dict[str, float]] = None
    ):
        """Initialize context window manager.

        Args:
            model_config: Model configuration from ModelConfigLoader
                Must contain 'context_window' key with integer value
            utilization_limit: Fraction of context window to use (0.0-1.0)
                Default: 1.0 (100% usage)
                Example: 0.75 means use only 75% of available context
            custom_thresholds: Optional custom threshold percentages
                If None, uses DEFAULT_THRESHOLDS

        Raises:
            ValueError: If model_config missing 'context_window' or
                utilization_limit is out of range (0.0, 1.0]

        Example:
            >>> config = {'context_window': 128000}
            >>> # Use only 80% of capacity
            >>> manager = ContextWindowManager(config, utilization_limit=0.8)
        """
        if 'context_window' not in model_config:
            raise ValueError(
                "model_config must contain 'context_window' key"
            )

        if not 0.0 < utilization_limit <= 1.0:
            raise ValueError(
                f"utilization_limit must be in range (0.0, 1.0], "
                f"got: {utilization_limit}"
            )

        self.max_tokens = model_config['context_window']
        self.utilization_limit = utilization_limit
        self.model_name = model_config.get('model', 'unknown')

        # Calculate effective maximum after applying utilization limit
        self.effective_max_tokens = int(self.max_tokens * self.utilization_limit)

        # Thread safety
        self._lock = RLock()

        # Current usage
        self._used_tokens = 0

        # Calculate thresholds based on effective max
        threshold_pcts = custom_thresholds or self.DEFAULT_THRESHOLDS
        self.thresholds = self._calculate_thresholds(threshold_pcts)

        logger.info(
            f"ContextWindowManager initialized: model={self.model_name}, "
            f"max_tokens={self.max_tokens:,}, "
            f"utilization_limit={self.utilization_limit:.0%}, "
            f"effective_max={self.effective_max_tokens:,}, "
            f"thresholds={self._format_thresholds()}"
        )

    def _calculate_thresholds(
        self,
        threshold_percentages: Dict[str, float]
    ) -> Dict[str, int]:
        """Calculate absolute token thresholds from percentages.

        Thresholds are calculated based on effective_max_tokens (after
        applying utilization limit), not the raw max_tokens.

        Args:
            threshold_percentages: Dictionary of threshold names to percentages
                Example: {'green_upper': 0.50, 'yellow_upper': 0.70, ...}

        Returns:
            Dictionary mapping threshold names to absolute token counts

        Example:
            >>> # With 128K context and 0.75 limit (96K effective)
            >>> manager = ContextWindowManager(config, utilization_limit=0.75)
            >>> manager.thresholds['yellow_upper']  # 70% of 96K
            67200
        """
        return {
            name: int(self.effective_max_tokens * percentage)
            for name, percentage in threshold_percentages.items()
        }

    def _format_thresholds(self) -> str:
        """Format thresholds for logging.

        Returns:
            Formatted string of thresholds

        Example:
            "green=64K, yellow=89K, orange=108K, red=121K"
        """
        return ", ".join(
            f"{name.replace('_upper', '')}={value//1000}K"
            for name, value in sorted(self.thresholds.items())
        )

    def add_usage(self, tokens: int) -> None:
        """Record token usage from an operation.

        Thread-safe method to increment usage counter. Logs warnings
        when crossing threshold boundaries.

        Args:
            tokens: Number of tokens consumed

        Side Effects:
            - Updates internal usage counter
            - Logs warnings at threshold crossings
            - May trigger zone transition

        Example:
            >>> manager = ContextWindowManager(config)
            >>> manager.add_usage(50000)
            >>> manager.add_usage(30000)  # Total now 80000
        """
        with self._lock:
            previous_zone = self.get_zone()
            self._used_tokens += tokens

            # Check for zone transition
            new_zone = self.get_zone()
            if new_zone != previous_zone:
                usage_pct = self.usage_percentage()
                logger.warning(
                    f"Context zone transition: {previous_zone} → {new_zone} "
                    f"({usage_pct:.1%} of effective max, "
                    f"{self._used_tokens:,}/{self.effective_max_tokens:,} tokens)"
                )

                # Log recommended action
                action = self.get_recommended_action()
                logger.info(f"Recommended action: {action}")

    def used_tokens(self) -> int:
        """Get current token usage count.

        Thread-safe accessor for usage counter.

        Returns:
            Number of tokens currently used

        Example:
            >>> manager.add_usage(50000)
            >>> manager.used_tokens()
            50000
        """
        with self._lock:
            return self._used_tokens

    def available_tokens(self) -> int:
        """Get remaining available tokens.

        Calculates tokens available before hitting effective max.

        Returns:
            Number of tokens available (effective_max - used)

        Example:
            >>> manager = ContextWindowManager({'context_window': 100000})
            >>> manager.add_usage(60000)
            >>> manager.available_tokens()
            40000
        """
        with self._lock:
            return max(0, self.effective_max_tokens - self._used_tokens)

    def usage_percentage(self) -> float:
        """Get current usage as percentage of effective max.

        Returns:
            Usage percentage as decimal (0.0 to 1.0+)
                Note: Can exceed 1.0 if usage exceeds effective max

        Example:
            >>> manager = ContextWindowManager({'context_window': 100000})
            >>> manager.add_usage(70000)
            >>> manager.usage_percentage()
            0.7
        """
        with self._lock:
            if self.effective_max_tokens == 0:
                return 1.0
            return self._used_tokens / self.effective_max_tokens

    def get_zone(self) -> str:
        """Get current context usage zone.

        Zones are based on threshold crossings:
        - green: Usage < 50% of effective max (normal operation)
        - yellow: 50% ≤ usage < 70% (monitor, plan checkpoint)
        - orange: 70% ≤ usage < 85% (optimize then checkpoint)
        - red: usage ≥ 85% (emergency checkpoint required)

        Returns:
            Zone name: 'green', 'yellow', 'orange', or 'red'

        Example:
            >>> manager = ContextWindowManager({'context_window': 100000})
            >>> manager.add_usage(60000)
            >>> manager.get_zone()
            'yellow'
        """
        with self._lock:
            if self._used_tokens < self.thresholds['green_upper']:
                return 'green'
            elif self._used_tokens < self.thresholds['yellow_upper']:
                return 'yellow'
            elif self._used_tokens < self.thresholds['orange_upper']:
                return 'orange'
            else:
                return 'red'

    def get_recommended_action(self) -> str:
        """Get recommended action based on current zone.

        Returns:
            Action string describing what should be done

        Example:
            >>> manager.add_usage(90000)  # Pushes to red zone
            >>> manager.get_recommended_action()
            'emergency_checkpoint_and_refresh'
        """
        zone = self.get_zone()

        actions = {
            'green': 'proceed_normally',
            'yellow': 'monitor_and_plan_checkpoint',
            'orange': 'optimize_then_checkpoint',
            'red': 'emergency_checkpoint_and_refresh'
        }

        return actions[zone]

    def reset(self) -> None:
        """Reset usage counter to zero.

        Typically called after checkpoint/refresh operations.

        Thread-safe operation.

        Example:
            >>> manager.add_usage(80000)
            >>> manager.reset()
            >>> manager.used_tokens()
            0
        """
        with self._lock:
            previous_usage = self._used_tokens
            self._used_tokens = 0
            logger.info(
                f"Context usage reset: {previous_usage:,} → 0 tokens"
            )

    def can_accommodate(self, additional_tokens: int) -> bool:
        """Check if context can accommodate additional tokens.

        Checks whether adding tokens would stay within yellow zone
        (safe operating range).

        Args:
            additional_tokens: Tokens to be added

        Returns:
            True if addition stays within yellow zone, False otherwise

        Example:
            >>> manager = ContextWindowManager({'context_window': 100000})
            >>> manager.add_usage(50000)
            >>> manager.can_accommodate(15000)  # Would be 65K, still yellow
            True
            >>> manager.can_accommodate(50000)  # Would be 100K, red zone
            False
        """
        with self._lock:
            projected_usage = self._used_tokens + additional_tokens
            return projected_usage < self.thresholds['yellow_upper']

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status information.

        Returns:
            Dictionary with usage statistics and thresholds

        Example:
            >>> status = manager.get_status()
            >>> print(status['usage_percentage'])
            0.65
            >>> print(status['zone'])
            'yellow'
        """
        with self._lock:
            return {
                'model': self.model_name,
                'max_tokens': self.max_tokens,
                'utilization_limit': self.utilization_limit,
                'effective_max_tokens': self.effective_max_tokens,
                'used_tokens': self._used_tokens,
                'available_tokens': self.available_tokens(),
                'usage_percentage': self.usage_percentage(),
                'zone': self.get_zone(),
                'recommended_action': self.get_recommended_action(),
                'thresholds': self.thresholds.copy()
            }
