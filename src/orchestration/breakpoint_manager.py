"""Breakpoint triggering and resolution tracking with configurable rules.

This module implements the BreakpointManager, which determines when to pause
execution and request human intervention based on configurable rules and conditions.

Breakpoint Types:
    - architecture_decision: Major architectural decisions
    - breaking_test_failure: Previously passing tests now fail
    - conflicting_solutions: Disagreement between validators
    - milestone_completion: Milestone complete, ready for review
    - rate_limit_hit: API rate limit (auto-resolvable)
    - time_threshold_exceeded: Task timeout (auto-resolvable)
    - confidence_too_low: Confidence below threshold for critical task
    - consecutive_failures: Multiple consecutive failures

Example:
    >>> manager = BreakpointManager(state_manager, config)
    >>> breakpoints = manager.evaluate_breakpoint_conditions(context)
    >>> if breakpoints:
    ...     event = manager.trigger_breakpoint('low_confidence', context)
    ...     # Wait for human resolution
    ...     manager.resolve_breakpoint(event.id, resolution)
"""

import logging
import ast
from collections import defaultdict
from datetime import datetime, UTC, timedelta
from threading import RLock
from typing import Dict, List, Optional, Any, Callable

from src.core.exceptions import OrchestratorException
from src.core.state import StateManager


logger = logging.getLogger(__name__)


class BreakpointEvent:
    """Represents a triggered breakpoint event.

    Attributes:
        id: Unique breakpoint event ID
        breakpoint_type: Type of breakpoint
        priority: Priority level (high, medium, low)
        context: Context data when triggered
        triggered_at: When breakpoint was triggered
        resolved_at: When breakpoint was resolved (None if pending)
        resolution: Resolution data (None if pending)
        auto_resolved: Whether breakpoint was auto-resolved
    """

    def __init__(
        self,
        id: int,
        breakpoint_type: str,
        priority: str,
        context: Dict[str, Any],
        triggered_at: datetime
    ):
        """Initialize breakpoint event.

        Args:
            id: Event ID
            breakpoint_type: Type of breakpoint
            priority: Priority level
            context: Context dictionary
            triggered_at: Trigger timestamp
        """
        self.id = id
        self.breakpoint_type = breakpoint_type
        self.priority = priority
        self.context = context
        self.triggered_at = triggered_at
        self.resolved_at: Optional[datetime] = None
        self.resolution: Optional[Dict[str, Any]] = None
        self.auto_resolved = False

    def is_pending(self) -> bool:
        """Check if breakpoint is still pending resolution.

        Returns:
            True if pending, False if resolved
        """
        return self.resolved_at is None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'id': self.id,
            'breakpoint_type': self.breakpoint_type,
            'priority': self.priority,
            'context': self.context,
            'triggered_at': self.triggered_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution': self.resolution,
            'auto_resolved': self.auto_resolved
        }


class BreakpointManager:
    """Manages breakpoint triggering and resolution.

    Evaluates configurable rules to determine when to pause execution and
    request human intervention. Tracks breakpoint history and analytics.

    Thread-safe for concurrent access.

    Example:
        >>> manager = BreakpointManager(state_manager, config)
        >>>
        >>> # Evaluate conditions
        >>> context = {
        ...     'confidence_score': 0.25,
        ...     'critical_task': True,
        ...     'task_id': 123
        ... }
        >>> breakpoints = manager.evaluate_breakpoint_conditions(context)
        >>>
        >>> # Trigger breakpoint
        >>> if breakpoints:
        ...     event = manager.trigger_breakpoint('confidence_too_low', context)
        ...     print(f"Breakpoint {event.id} triggered, awaiting resolution")
        >>>
        >>> # Resolve breakpoint
        >>> resolution = {'action': 'proceed', 'notes': 'Reviewed and approved'}
        >>> manager.resolve_breakpoint(event.id, resolution)
    """

    # Priority levels
    PRIORITY_HIGH = 'high'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_LOW = 'low'

    # Notification methods
    NOTIFY_IMMEDIATE = 'immediate'
    NOTIFY_BATCHED = 'batched'

    def __init__(self, state_manager: StateManager, config: Optional[Dict[str, Any]] = None):
        """Initialize breakpoint manager.

        Args:
            state_manager: StateManager instance
            config: Optional configuration dictionary with breakpoint rules
        """
        self.state_manager = state_manager
        self.config = config or {}
        self._lock = RLock()

        # Breakpoint rules (type -> rule config)
        self._rules: Dict[str, Dict[str, Any]] = self._load_breakpoint_rules()

        # Disabled breakpoint types
        self._disabled_types: set = set()

        # Event storage (project_id -> List[BreakpointEvent])
        self._events: Dict[int, List[BreakpointEvent]] = defaultdict(list)

        # Event ID counter
        self._next_event_id = 1

        # Statistics tracking
        self._stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Notification callbacks
        self._notification_callbacks: List[Callable] = []

        logger.info("BreakpointManager initialized")

    def evaluate_breakpoint_conditions(self, context: Dict[str, Any]) -> List[str]:
        """Evaluate all breakpoint conditions against context.

        Args:
            context: Context dictionary with variables for rule evaluation

        Returns:
            List of breakpoint types whose conditions are met

        Example:
            >>> context = {
            ...     'confidence_score': 0.25,
            ...     'critical_task': True,
            ...     'test_failed': True,
            ...     'previously_passing': True
            ... }
            >>> triggered = manager.evaluate_breakpoint_conditions(context)
            >>> print(triggered)  # ['confidence_too_low', 'breaking_test_failure']
        """
        with self._lock:
            triggered_types = []

            # Sort rules by priority
            sorted_rules = sorted(
                self._rules.items(),
                key=lambda x: self._priority_to_int(x[1].get('priority', self.PRIORITY_MEDIUM)),
                reverse=True
            )

            for breakpoint_type, rule in sorted_rules:
                # Skip if disabled
                if breakpoint_type in self._disabled_types:
                    continue

                # Skip if not enabled
                if not rule.get('enabled', True):
                    continue

                # Merge rule config values into context for evaluation
                eval_context = context.copy()
                if 'threshold' in rule:
                    eval_context['threshold'] = rule['threshold']
                if 'count_threshold' in rule:
                    eval_context['count_threshold'] = rule['count_threshold']
                if 'timeout_seconds' in rule:
                    eval_context['timeout_seconds'] = rule['timeout_seconds']

                # Evaluate conditions
                if self._evaluate_conditions(rule.get('conditions', []), eval_context):
                    triggered_types.append(breakpoint_type)
                    logger.debug(f"Breakpoint condition met: {breakpoint_type}")

            return triggered_types

    def trigger_breakpoint(
        self,
        breakpoint_type: str,
        context: Dict[str, Any]
    ) -> BreakpointEvent:
        """Trigger a breakpoint and create event.

        Args:
            breakpoint_type: Type of breakpoint to trigger
            context: Context dictionary with breakpoint details

        Returns:
            Created BreakpointEvent

        Raises:
            OrchestratorException: If breakpoint type unknown

        Example:
            >>> event = manager.trigger_breakpoint(
            ...     'confidence_too_low',
            ...     {'task_id': 123, 'confidence': 0.25}
            ... )
            >>> print(f"Breakpoint {event.id} awaiting resolution")
        """
        with self._lock:
            # Validate breakpoint type
            if breakpoint_type not in self._rules:
                raise OrchestratorException(
                    f"Unknown breakpoint type: {breakpoint_type}",
                    context={'breakpoint_type': breakpoint_type},
                    recovery="Use a registered breakpoint type"
                )

            rule = self._rules[breakpoint_type]

            # Create event
            event = BreakpointEvent(
                id=self._next_event_id,
                breakpoint_type=breakpoint_type,
                priority=rule.get('priority', self.PRIORITY_MEDIUM),
                context=context.copy(),
                triggered_at=datetime.now(UTC)
            )
            self._next_event_id += 1

            # Store event
            project_id = context.get('project_id', 0)
            self._events[project_id].append(event)

            # Update statistics
            self._stats[breakpoint_type]['triggered'] += 1

            # Check for auto-resolution
            if rule.get('auto_resolve', False):
                self._auto_resolve_breakpoint(event, rule)

            # Send notification
            if self.should_notify(breakpoint_type, event.priority):
                self._send_notification(event, rule)

            logger.info(
                f"Breakpoint triggered: {breakpoint_type} (priority: {event.priority}, "
                f"event_id: {event.id})"
            )

            # Persist to database
            self._persist_breakpoint_event(event)

            return event

    def get_pending_breakpoints(self, project_id: int) -> List[BreakpointEvent]:
        """Get all pending (unresolved) breakpoints for a project.

        Args:
            project_id: Project ID

        Returns:
            List of pending breakpoint events

        Example:
            >>> pending = manager.get_pending_breakpoints(project_id)
            >>> for bp in pending:
            ...     print(f"{bp.breakpoint_type}: {bp.context}")
        """
        with self._lock:
            return [
                event for event in self._events.get(project_id, [])
                if event.is_pending()
            ]

    def resolve_breakpoint(
        self,
        breakpoint_id: int,
        resolution: Dict[str, Any]
    ) -> None:
        """Resolve a pending breakpoint.

        Args:
            breakpoint_id: Breakpoint event ID
            resolution: Resolution dictionary with action and notes

        Raises:
            OrchestratorException: If breakpoint not found or already resolved

        Example:
            >>> resolution = {
            ...     'action': 'proceed',
            ...     'notes': 'Manually reviewed, looks good',
            ...     'modified_files': ['src/main.py']
            ... }
            >>> manager.resolve_breakpoint(event_id, resolution)
        """
        with self._lock:
            # Find event
            event = self._find_event(breakpoint_id)
            if not event:
                raise OrchestratorException(
                    f"Breakpoint event {breakpoint_id} not found",
                    context={'breakpoint_id': breakpoint_id},
                    recovery="Verify breakpoint ID is correct"
                )

            if not event.is_pending():
                raise OrchestratorException(
                    f"Breakpoint {breakpoint_id} already resolved",
                    context={'breakpoint_id': breakpoint_id, 'resolved_at': event.resolved_at},
                    recovery="Cannot re-resolve breakpoint"
                )

            # Resolve event
            event.resolved_at = datetime.now(UTC)
            event.resolution = resolution.copy()

            # Calculate resolution time
            resolution_time = (event.resolved_at - event.triggered_at).total_seconds()

            # Update statistics
            self._stats[event.breakpoint_type]['resolved'] += 1
            self._stats[event.breakpoint_type]['total_resolution_time'] += resolution_time

            logger.info(
                f"Breakpoint resolved: {event.breakpoint_type} (event_id: {breakpoint_id}, "
                f"resolution_time: {resolution_time:.1f}s)"
            )

            # Persist update
            self._persist_breakpoint_event(event)

    def get_breakpoint_history(
        self,
        project_id: int,
        limit: int = 50
    ) -> List[BreakpointEvent]:
        """Get breakpoint history for a project.

        Args:
            project_id: Project ID
            limit: Maximum number of events to return

        Returns:
            List of breakpoint events (most recent first)

        Example:
            >>> history = manager.get_breakpoint_history(project_id, limit=10)
            >>> for event in history:
            ...     print(f"{event.triggered_at}: {event.breakpoint_type}")
        """
        with self._lock:
            events = self._events.get(project_id, [])
            # Sort by triggered_at descending
            sorted_events = sorted(
                events,
                key=lambda e: e.triggered_at,
                reverse=True
            )
            return sorted_events[:limit]

    def add_custom_rule(self, rule_definition: Dict[str, Any]) -> None:
        """Add a custom breakpoint rule at runtime.

        Args:
            rule_definition: Rule definition with type, conditions, priority, etc.

        Example:
            >>> rule = {
            ...     'type': 'custom_check',
            ...     'enabled': True,
            ...     'priority': 'high',
            ...     'conditions': ['custom_metric > 100'],
            ...     'notification': 'immediate',
            ...     'description': 'Custom metric threshold exceeded'
            ... }
            >>> manager.add_custom_rule(rule)
        """
        with self._lock:
            rule_type = rule_definition.get('type')
            if not rule_type:
                raise OrchestratorException(
                    "Rule definition missing 'type'",
                    context={'rule': rule_definition},
                    recovery="Provide 'type' field in rule definition"
                )

            self._rules[rule_type] = rule_definition
            logger.info(f"Custom rule added: {rule_type}")

    def disable_breakpoint_type(self, breakpoint_type: str) -> None:
        """Temporarily disable a breakpoint type.

        Args:
            breakpoint_type: Type to disable

        Example:
            >>> manager.disable_breakpoint_type('milestone_completion')
        """
        with self._lock:
            self._disabled_types.add(breakpoint_type)
            logger.info(f"Breakpoint type disabled: {breakpoint_type}")

    def enable_breakpoint_type(self, breakpoint_type: str) -> None:
        """Re-enable a disabled breakpoint type.

        Args:
            breakpoint_type: Type to enable

        Example:
            >>> manager.enable_breakpoint_type('milestone_completion')
        """
        with self._lock:
            self._disabled_types.discard(breakpoint_type)
            logger.info(f"Breakpoint type enabled: {breakpoint_type}")

    def get_breakpoint_stats(self, project_id: int) -> Dict[str, Any]:
        """Get breakpoint statistics for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with statistics per breakpoint type

        Example:
            >>> stats = manager.get_breakpoint_stats(project_id)
            >>> print(f"Triggered: {stats['confidence_too_low']['triggered']}")
            >>> print(f"Avg resolution time: {stats['confidence_too_low']['avg_resolution_time']}")
        """
        with self._lock:
            result = {}
            events = self._events.get(project_id, [])

            for breakpoint_type in self._rules.keys():
                type_events = [e for e in events if e.breakpoint_type == breakpoint_type]

                triggered_count = len(type_events)
                resolved_count = len([e for e in type_events if not e.is_pending()])
                pending_count = triggered_count - resolved_count

                # Calculate average resolution time
                resolution_times = [
                    (e.resolved_at - e.triggered_at).total_seconds()
                    for e in type_events
                    if e.resolved_at
                ]
                avg_resolution_time = (
                    sum(resolution_times) / len(resolution_times)
                    if resolution_times else 0
                )

                result[breakpoint_type] = {
                    'triggered': triggered_count,
                    'resolved': resolved_count,
                    'pending': pending_count,
                    'avg_resolution_time': avg_resolution_time,
                    'auto_resolved': len([e for e in type_events if e.auto_resolved])
                }

            return result

    def should_notify(self, breakpoint_type: str, severity: str) -> bool:
        """Determine if notification should be sent for breakpoint.

        Args:
            breakpoint_type: Breakpoint type
            severity: Severity/priority level

        Returns:
            True if notification should be sent

        Example:
            >>> if manager.should_notify('rate_limit_hit', 'high'):
            ...     send_alert()
        """
        rule = self._rules.get(breakpoint_type, {})
        notification_method = rule.get('notification', self.NOTIFY_BATCHED)

        # Always notify immediate high-priority breakpoints
        if notification_method == self.NOTIFY_IMMEDIATE:
            return True

        # Batch low-priority breakpoints
        if severity == self.PRIORITY_LOW:
            return False

        return True

    def register_notification_callback(self, callback: Callable) -> None:
        """Register a callback for breakpoint notifications.

        Args:
            callback: Callable taking (BreakpointEvent, rule_config)

        Example:
            >>> def send_email(event, rule):
            ...     print(f"ALERT: {event.breakpoint_type}")
            >>> manager.register_notification_callback(send_email)
        """
        self._notification_callbacks.append(callback)

    # Private helper methods

    def _load_breakpoint_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load breakpoint rules from configuration.

        Returns:
            Dictionary mapping breakpoint type to rule config
        """
        # Default rules (from plans/04_orchestration.json)
        default_rules = {
            'architecture_decision': {
                'enabled': True,
                'priority': self.PRIORITY_HIGH,
                'auto_resolve': False,
                'conditions': [
                    "task_type == 'design'",
                    "confidence < 0.9",
                    "affects_multiple_components == True"
                ],
                'notification': self.NOTIFY_IMMEDIATE,
                'description': 'Major architectural decision requiring human judgment'
            },
            'breaking_test_failure': {
                'enabled': True,
                'priority': self.PRIORITY_HIGH,
                'auto_resolve': False,
                'conditions': [
                    "test_failed == True",
                    "previously_passing == True",
                    "affects_critical_functionality == True"
                ],
                'notification': self.NOTIFY_IMMEDIATE,
                'description': 'Previously passing test now fails - regression detected'
            },
            'conflicting_solutions': {
                'enabled': True,
                'priority': self.PRIORITY_MEDIUM,
                'auto_resolve': False,
                'conditions': [
                    "local_validation != remote_validation",
                    "confidence_difference > 0.3"
                ],
                'notification': self.NOTIFY_BATCHED,
                'description': 'Local and remote LLM disagree on solution'
            },
            'milestone_completion': {
                'enabled': True,
                'priority': self.PRIORITY_MEDIUM,
                'auto_resolve': False,
                'conditions': [
                    "all_milestone_tasks_complete == True",
                    "tests_passing == True",
                    "documentation_complete == True"
                ],
                'notification': self.NOTIFY_BATCHED,
                'description': 'Milestone complete - review before proceeding'
            },
            'rate_limit_hit': {
                'enabled': True,
                'priority': self.PRIORITY_HIGH,
                'auto_resolve': True,
                'wait_duration_seconds': 3600,
                'conditions': ["rate_limit_detected == True"],
                'notification': self.NOTIFY_IMMEDIATE,
                'auto_resolution_action': 'wait_and_retry',
                'description': 'Claude Code rate limit hit - automatic wait'
            },
            'time_threshold_exceeded': {
                'enabled': True,
                'priority': self.PRIORITY_MEDIUM,
                'auto_resolve': True,
                'timeout_seconds': 3600,
                'conditions': ["task_running_time > timeout_seconds"],
                'notification': self.NOTIFY_BATCHED,
                'auto_resolution_action': 'cancel_and_retry',
                'description': 'Task taking too long - timeout'
            },
            'confidence_too_low': {
                'enabled': True,
                'priority': self.PRIORITY_HIGH,
                'auto_resolve': False,
                'threshold': 0.3,
                'conditions': [
                    "confidence_score < threshold",
                    "critical_task == True"
                ],
                'notification': self.NOTIFY_IMMEDIATE,
                'description': 'Confidence too low for critical task'
            },
            'consecutive_failures': {
                'enabled': True,
                'priority': self.PRIORITY_HIGH,
                'auto_resolve': False,
                'count_threshold': 3,
                'conditions': ["consecutive_task_failures >= count_threshold"],
                'notification': self.NOTIFY_IMMEDIATE,
                'description': 'Multiple consecutive failures - intervention needed'
            }
        }

        # Merge with config if provided
        config_rules = self.config.get('breakpoint_rules', {})
        default_rules.update(config_rules)

        return default_rules

    def _evaluate_conditions(
        self,
        conditions: List[str],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate list of condition expressions against context.

        Args:
            conditions: List of Python expressions as strings
            context: Context dictionary with variables

        Returns:
            True if all conditions evaluate to True
        """
        if not conditions:
            return False

        try:
            # Create safe evaluation context
            safe_context = {
                'True': True,
                'False': False,
                'None': None,
                **context
            }

            # Evaluate all conditions
            for condition in conditions:
                try:
                    result = eval(condition, {"__builtins__": {}}, safe_context)
                    if not result:
                        return False
                except Exception as e:
                    logger.warning(f"Condition evaluation failed: {condition} - {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False

    def _auto_resolve_breakpoint(
        self,
        event: BreakpointEvent,
        rule: Dict[str, Any]
    ) -> None:
        """Automatically resolve a breakpoint according to rule.

        Args:
            event: Breakpoint event to resolve
            rule: Rule configuration
        """
        action = rule.get('auto_resolution_action', 'wait')

        if action == 'wait_and_retry':
            wait_duration = rule.get('wait_duration_seconds', 3600)
            event.resolved_at = datetime.now(UTC) + timedelta(seconds=wait_duration)
            event.resolution = {
                'action': 'wait_and_retry',
                'wait_duration': wait_duration,
                'auto_resolved': True
            }
            event.auto_resolved = True

            logger.info(f"Auto-resolving breakpoint {event.id}: wait {wait_duration}s and retry")

        elif action == 'cancel_and_retry':
            event.resolved_at = datetime.now(UTC)
            event.resolution = {
                'action': 'cancel_and_retry',
                'auto_resolved': True
            }
            event.auto_resolved = True

            logger.info(f"Auto-resolving breakpoint {event.id}: cancel and retry")

    def _send_notification(
        self,
        event: BreakpointEvent,
        rule: Dict[str, Any]
    ) -> None:
        """Send notification for breakpoint event.

        Args:
            event: Breakpoint event
            rule: Rule configuration
        """
        # Call registered callbacks
        for callback in self._notification_callbacks:
            try:
                callback(event, rule)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")

        # Log notification
        logger.info(
            f"Breakpoint notification: {event.breakpoint_type} "
            f"(priority: {event.priority}, event_id: {event.id})"
        )

    def _find_event(self, breakpoint_id: int) -> Optional[BreakpointEvent]:
        """Find breakpoint event by ID.

        Args:
            breakpoint_id: Event ID

        Returns:
            BreakpointEvent if found, None otherwise
        """
        for events in self._events.values():
            for event in events:
                if event.id == breakpoint_id:
                    return event
        return None

    def _persist_breakpoint_event(self, event: BreakpointEvent) -> None:
        """Persist breakpoint event to database.

        Args:
            event: Breakpoint event to persist
        """
        # TODO: Store in Event table via StateManager
        # For now, just log
        logger.debug(f"Persisting breakpoint event {event.id} (type: {event.breakpoint_type})")

    def _priority_to_int(self, priority: str) -> int:
        """Convert priority string to integer for sorting.

        Args:
            priority: Priority string

        Returns:
            Integer priority (higher is more important)
        """
        priorities = {
            self.PRIORITY_HIGH: 3,
            self.PRIORITY_MEDIUM: 2,
            self.PRIORITY_LOW: 1
        }
        return priorities.get(priority, 2)
