"""Session metrics collector for tracking orchestrator session patterns.

This module implements the SessionMetricsCollector class that tracks session
patterns, handoff metrics, and context usage for analytics.

Example:
    >>> from src.orchestration.session import SessionMetricsCollector
    >>> collector = SessionMetricsCollector(config)
    >>> collector.record_operation('task_execution', context_mgr, decision)
    >>> collector.record_handoff('checkpoint_123', 0.87)
    >>> summary = collector.generate_session_summary()

Author: Obra System
Created: 2025-11-15
Version: 1.0.0
"""

import logging
from datetime import datetime, UTC
from threading import RLock
from typing import Dict, Any, Optional

from src.core.config import Config
from src.core.exceptions import OrchestratorException


logger = logging.getLogger(__name__)


class SessionMetricsCollector:
    """Track session patterns, handoffs, and context usage.

    This class collects metrics about orchestrator session behavior including
    handoff frequency, context usage patterns, decision confidence trends, and
    operation statistics.

    Thread-safe: Yes (uses RLock for concurrent access)

    Attributes:
        config: Obra configuration
        enabled: Whether metrics collection is enabled
        track_context_zones: Whether to track context zone distribution
        track_confidence_trends: Whether to track decision confidence
        session_start: Session start timestamp
        metrics: Current session metrics

    Example:
        >>> collector = SessionMetricsCollector(config)
        >>> # During operation
        >>> collector.record_operation('task_execution', context_mgr, decision)
        >>> # After handoff
        >>> collector.record_handoff('checkpoint_123', 0.87)
        >>> # Get summary
        >>> summary = collector.generate_session_summary()
    """

    # Context zones (from ADR-018)
    ZONE_GREEN = 'green'  # 0-60%
    ZONE_YELLOW = 'yellow'  # 60-85%
    ZONE_RED = 'red'  # 85-100%

    # Operation types
    OPERATION_TASK_EXECUTION = 'task_execution'
    OPERATION_NL_COMMAND = 'nl_command'
    OPERATION_DECISION = 'decision'
    OPERATION_VALIDATION = 'validation'
    OPERATION_HANDOFF = 'handoff'

    def __init__(self, config: Config):
        """Initialize session metrics collector.

        Args:
            config: Obra configuration
        """
        self.config = config
        self._lock = RLock()

        # Configuration
        self.enabled = config.get(
            'orchestrator.session_continuity.metrics.enabled', True
        )
        self.track_context_zones = config.get(
            'orchestrator.session_continuity.metrics.track_context_zones', True
        )
        self.track_confidence_trends = config.get(
            'orchestrator.session_continuity.metrics.track_confidence_trends', True
        )
        self.summary_on_handoff = config.get(
            'orchestrator.session_continuity.metrics.summary_on_handoff', True
        )

        # Session state
        self.session_start = datetime.now(UTC)
        self._session_id: Optional[str] = None

        # Initialize metrics
        self._metrics = self._initialize_metrics()

        logger.info(
            "SessionMetricsCollector initialized: enabled=%s, zones=%s, confidence=%s",
            self.enabled, self.track_context_zones, self.track_confidence_trends
        )

    def record_operation(
        self,
        operation_type: str,
        context_mgr: Any = None,  # Type: OrchestratorContextManager
        decision: Any = None  # Type: Action
    ) -> None:
        """Record a single operation for metrics.

        Args:
            operation_type: Type of operation (task_execution, nl_command, etc.)
            context_mgr: Optional orchestrator context manager (ADR-018)
            decision: Optional decision action from DecisionEngine

        Raises:
            OrchestratorException: If recording fails
        """
        if not self.enabled:
            return

        try:
            with self._lock:
                # Increment operation count
                self._metrics['total_operations'] += 1
                self._metrics['operations_by_type'][operation_type] = \
                    self._metrics['operations_by_type'].get(operation_type, 0) + 1

                # Track context usage
                if context_mgr and self.track_context_zones:
                    self._record_context_usage(context_mgr)

                # Track decision confidence
                if decision and self.track_confidence_trends:
                    self._record_confidence(decision)

                logger.debug(
                    "Recorded operation: type=%s, total_ops=%d",
                    operation_type, self._metrics['total_operations']
                )

        except Exception as e:
            raise OrchestratorException(
                f"Failed to record operation metrics: {e}",
                context={'operation_type': operation_type},
                recovery="Check metrics collector configuration"
            ) from e

    def record_handoff(self, checkpoint_id: str, context_usage: float) -> None:
        """Record a handoff event.

        Args:
            checkpoint_id: Checkpoint ID for handoff
            context_usage: Context usage percentage at handoff (0.0-1.0)

        Raises:
            OrchestratorException: If recording fails
        """
        if not self.enabled:
            return

        try:
            with self._lock:
                # Increment handoff count
                self._metrics['handoff_count'] += 1

                # Track last checkpoint
                self._metrics['last_checkpoint_id'] = checkpoint_id
                self._metrics['last_handoff_timestamp'] = datetime.now(UTC).isoformat()

                # Update peak context usage
                if context_usage > self._metrics['peak_context_usage']:
                    self._metrics['peak_context_usage'] = context_usage

                logger.info(
                    "Recorded handoff: checkpoint=%s, usage=%.2f%%, total_handoffs=%d",
                    checkpoint_id, context_usage * 100, self._metrics['handoff_count']
                )

        except Exception as e:
            raise OrchestratorException(
                f"Failed to record handoff metrics: {e}",
                context={'checkpoint_id': checkpoint_id},
                recovery="Check handoff recording configuration"
            ) from e

    def get_session_metrics(self) -> Dict[str, Any]:
        """Get current session metrics.

        Returns:
            Dictionary containing session metrics

        Example:
            >>> metrics = collector.get_session_metrics()
            >>> print(f"Operations: {metrics['total_operations']}")
            >>> print(f"Handoffs: {metrics['handoff_count']}")
        """
        with self._lock:
            # Calculate session duration
            duration = (datetime.now(UTC) - self.session_start).total_seconds()
            self._metrics['session_duration_seconds'] = duration

            # Calculate average context usage
            context_samples = self._metrics.get('_context_samples', [])
            if context_samples:
                self._metrics['avg_context_usage'] = sum(context_samples) / len(context_samples)

            # Calculate average confidence
            confidence_samples = self._metrics.get('_confidence_samples', [])
            if confidence_samples:
                self._metrics['avg_confidence'] = sum(confidence_samples) / len(confidence_samples)

            # Return copy without internal tracking fields
            metrics_copy = {
                k: v for k, v in self._metrics.items()
                if not k.startswith('_')
            }

            return metrics_copy

    def generate_session_summary(self) -> str:
        """Generate markdown summary of session metrics.

        Returns:
            Markdown-formatted session summary

        Example:
            >>> summary = collector.generate_session_summary()
            >>> print(summary)
        """
        metrics = self.get_session_metrics()

        # Format duration
        duration_mins = metrics['session_duration_seconds'] / 60

        # Build summary
        summary = "# Session Metrics Summary\n\n"
        summary += f"**Session Start**: {self.session_start.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        summary += f"**Duration**: {duration_mins:.1f} minutes\n\n"

        summary += "## Operations\n\n"
        summary += f"- **Total**: {metrics['total_operations']}\n"
        summary += f"- **Handoffs**: {metrics['handoff_count']}\n"

        if metrics['operations_by_type']:
            summary += "\n**By Type**:\n"
            for op_type, count in sorted(metrics['operations_by_type'].items()):
                summary += f"- {op_type}: {count}\n"

        summary += "\n## Context Usage\n\n"
        summary += f"- **Average**: {metrics['avg_context_usage']:.1%}\n"
        summary += f"- **Peak**: {metrics['peak_context_usage']:.1%}\n"

        if self.track_context_zones and metrics['context_zones_distribution']:
            zones = metrics['context_zones_distribution']
            summary += "\n**Zone Distribution**:\n"
            summary += f"- Green (0-60%): {zones.get('green', 0)} operations\n"
            summary += f"- Yellow (60-85%): {zones.get('yellow', 0)} operations\n"
            summary += f"- Red (85-100%): {zones.get('red', 0)} operations\n"

        if self.track_confidence_trends:
            summary += "\n## Decision Confidence\n\n"
            summary += f"- **Average**: {metrics['avg_confidence']:.2f}\n"
            summary += f"- **Low Confidence Count** (<0.6): {metrics['low_confidence_count']}\n"

        return summary

    def reset_session(self) -> None:
        """Reset metrics for new session.

        This should be called after a handoff to start fresh metrics
        for the new session.
        """
        with self._lock:
            logger.info("Resetting session metrics")
            self.session_start = datetime.now(UTC)
            self._metrics = self._initialize_metrics()

    def _initialize_metrics(self) -> Dict[str, Any]:
        """Initialize metrics dictionary.

        Returns:
            Initial metrics dictionary
        """
        return {
            'session_id': self._session_id,
            'handoff_count': 0,
            'total_operations': 0,
            'avg_context_usage': 0.0,
            'peak_context_usage': 0.0,
            'operations_by_type': {},
            'avg_confidence': 0.0,
            'low_confidence_count': 0,
            'session_duration_seconds': 0.0,
            'context_zones_distribution': {
                'green': 0,
                'yellow': 0,
                'red': 0
            },
            'last_checkpoint_id': None,
            'last_handoff_timestamp': None,
            # Internal tracking (not exposed)
            '_context_samples': [],
            '_confidence_samples': []
        }

    def _record_context_usage(self, context_mgr: Any) -> None:
        """Record context usage from context manager.

        Args:
            context_mgr: OrchestratorContextManager instance
        """
        try:
            usage_pct = context_mgr.get_usage_percentage()

            # Track sample for averaging
            self._metrics['_context_samples'].append(usage_pct)

            # Track zone distribution
            zone = self._get_zone_for_usage(usage_pct)
            self._metrics['context_zones_distribution'][zone] += 1

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to record context usage: %s", e)

    def _record_confidence(self, decision: Any) -> None:
        """Record decision confidence.

        Args:
            decision: Action with confidence score
        """
        try:
            confidence = decision.confidence

            # Track sample for averaging
            self._metrics['_confidence_samples'].append(confidence)

            # Track low confidence
            if confidence < 0.6:
                self._metrics['low_confidence_count'] += 1

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to record confidence: %s", e)

    def _get_zone_for_usage(self, usage_pct: float) -> str:
        """Determine context zone for usage percentage.

        Args:
            usage_pct: Usage percentage (0.0-1.0)

        Returns:
            Zone identifier (green, yellow, red)
        """
        if usage_pct < 0.60:
            return self.ZONE_GREEN
        elif usage_pct < 0.85:
            return self.ZONE_YELLOW
        else:
            return self.ZONE_RED
