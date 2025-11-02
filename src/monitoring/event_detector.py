"""EventDetector - Detects significant events from file changes and patterns.

This module implements event detection for:
- Task completion (based on expected files, tests passing, quiescence)
- Failure patterns (consecutive errors, error rate, repeated errors)
- Milestone completion (all tasks done, tests passing)
- Anomaly detection (deviation from baseline metrics)
- State transitions (status changes)
- Threshold monitoring (budget, time, errors)
- Event correlation and debouncing
"""

import logging
import time
import statistics
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from threading import RLock

from src.core.state import StateManager
from src.core.models import Task, ProjectState, TaskStatus, Interaction
from src.core.exceptions import EventDetectionException

logger = logging.getLogger(__name__)


class FailurePattern:
    """Represents a detected failure pattern.

    Attributes:
        pattern_type: Type of failure pattern
        severity: Severity level (low, medium, high, critical)
        description: Human-readable description
        evidence: Supporting evidence
        recommendation: Recommended action
    """

    def __init__(
        self,
        pattern_type: str,
        severity: str,
        description: str,
        evidence: Dict[str, Any],
        recommendation: str
    ):
        """Initialize failure pattern.

        Args:
            pattern_type: Type of pattern (e.g., 'consecutive_errors')
            severity: Severity level
            description: Description of the failure
            evidence: Evidence dictionary
            recommendation: Recommended action
        """
        self.pattern_type = pattern_type
        self.severity = severity
        self.description = description
        self.evidence = evidence
        self.recommendation = recommendation
        self.detected_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'pattern_type': self.pattern_type,
            'severity': self.severity,
            'description': self.description,
            'evidence': self.evidence,
            'recommendation': self.recommendation,
            'detected_at': self.detected_at
        }


class Event:
    """Represents a detected event.

    Attributes:
        event_type: Type of event
        description: Human-readable description
        context: Event context data
        timestamp: When event was detected
    """

    def __init__(
        self,
        event_type: str,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """Initialize event.

        Args:
            event_type: Type of event (e.g., 'state_change')
            description: Description of the event
            context: Optional context dictionary
        """
        self.event_type = event_type
        self.description = description
        self.context = context or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'event_type': self.event_type,
            'description': self.description,
            'context': self.context,
            'timestamp': self.timestamp
        }


class ThresholdEvent:
    """Represents a threshold violation event.

    Attributes:
        threshold_name: Name of threshold
        current_value: Current value
        threshold_value: Threshold value
        exceeded: Whether threshold was exceeded
    """

    def __init__(
        self,
        threshold_name: str,
        current_value: float,
        threshold_value: float,
        exceeded: bool = True
    ):
        """Initialize threshold event.

        Args:
            threshold_name: Name of threshold
            current_value: Current value
            threshold_value: Threshold value
            exceeded: Whether threshold was exceeded
        """
        self.threshold_name = threshold_name
        self.current_value = current_value
        self.threshold_value = threshold_value
        self.exceeded = exceeded
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'threshold_name': self.threshold_name,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'exceeded': self.exceeded,
            'timestamp': self.timestamp
        }


class EventDetector:  # pylint: disable=too-many-instance-attributes
    """Detects significant events from file changes and patterns.

    The EventDetector analyzes file changes, interactions, and state to detect:
    - Task completion
    - Failure patterns
    - Milestone completion
    - Anomalies
    - State changes
    - Threshold violations

    Example:
        >>> state_manager = StateManager.get_instance('sqlite:///test.db')
        >>> detector = EventDetector(state_manager)
        >>>
        >>> # Detect task completion
        >>> task = state_manager.get_task(task_id)
        >>> file_changes = state_manager.get_file_changes(project_id)
        >>> is_complete = detector.detect_task_complete(task, file_changes)
        >>>
        >>> # Detect failures
        >>> recent_events = detector.get_recent_events(project_id)
        >>> failure = detector.detect_failure(recent_events)
        >>> if failure:
        ...     print(f"Failure detected: {failure.description}")
    """

    # Configuration constants
    DEFAULT_ERROR_WINDOW_SECONDS = 600  # 10 minutes
    DEFAULT_CONSECUTIVE_ERROR_THRESHOLD = 3
    DEFAULT_ERROR_RATE_THRESHOLD = 0.5  # 50%
    DEFAULT_QUIESCENCE_SECONDS = 5
    DEFAULT_BASELINE_WINDOW = 60
    DEFAULT_ANOMALY_SENSITIVITY = 2.5  # Standard deviations

    def __init__(
        self,
        state_manager: StateManager,
        error_window_seconds: int = DEFAULT_ERROR_WINDOW_SECONDS,
        consecutive_error_threshold: int = DEFAULT_CONSECUTIVE_ERROR_THRESHOLD,
        error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
        quiescence_seconds: float = DEFAULT_QUIESCENCE_SECONDS,
        baseline_window: int = DEFAULT_BASELINE_WINDOW,
        anomaly_sensitivity: float = DEFAULT_ANOMALY_SENSITIVITY
    ):
        """Initialize EventDetector.

        Args:
            state_manager: StateManager instance for querying state
            error_window_seconds: Time window for error rate calculation (default: 600)
            consecutive_error_threshold: Threshold for consecutive errors (default: 3)
            error_rate_threshold: Threshold for error rate (default: 0.5)
            quiescence_seconds: Seconds of no changes to consider quiescence (default: 5)
            baseline_window: Number of samples for baseline (default: 60)
            anomaly_sensitivity: Sensitivity for anomaly detection in std devs (default: 2.5)
        """
        self._state_manager = state_manager
        self._error_window_seconds = error_window_seconds
        self._consecutive_error_threshold = consecutive_error_threshold
        self._error_rate_threshold = error_rate_threshold
        self._quiescence_seconds = quiescence_seconds
        self._baseline_window = baseline_window
        self._anomaly_sensitivity = anomaly_sensitivity

        # Thread safety
        self._lock = RLock()

        # Event tracking for debouncing
        self._last_event_time: Dict[str, float] = {}
        self._event_debounce_window = 1.0  # 1 second

        # Baseline metrics storage
        self._metric_baselines: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self._baseline_window)
        )

        # Callbacks for event notifications
        self._event_callbacks: List[Callable[[Event], None]] = []

        logger.info("EventDetector initialized")

    def register_event_callback(self, callback: Callable[[Event], None]) -> None:
        """Register a callback for event notifications.

        Args:
            callback: Callable that takes an Event object

        Example:
            >>> def on_event(event):
            ...     print(f"Event detected: {event.event_type}")
            >>> detector.register_event_callback(on_event)
        """
        with self._lock:
            if callback not in self._event_callbacks:
                self._event_callbacks.append(callback)
                logger.debug("Registered event callback: %s", callback.__name__)

    def _emit_event(self, event: Event) -> None:
        """Emit an event to all registered callbacks.

        Args:
            event: Event to emit
        """
        logger.info(
            "Event detected: %s - %s",
            event.event_type,
            event.description
        )

        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Event callback failed: %s", exc)

    def detect_task_complete(
        self,
        task: Task,
        file_changes: List[Dict[str, Any]]
    ) -> bool:
        """Detect if a task is complete.

        Checks multiple conditions:
        1. All expected files created (from task.context['expected_files'])
        2. Tests passing (if task.context['requires_tests'])
        3. No errors in last N outputs (N=10)
        4. Completion marker in agent output
        5. No file changes for quiescence period (5 seconds)

        Scoring: All conditions true, or 4 out of 5

        Args:
            task: Task to check
            file_changes: Recent file changes (dicts with 'file_path', 'change_type', etc.)

        Returns:
            True if task appears complete

        Example:
            >>> task = state_manager.get_task(task_id)
            >>> changes = [
            ...     {'file_path': 'src/foo.py', 'change_type': 'created', 'timestamp': time.time()},
            ...     {'file_path': 'tests/test_foo.py', 'change_type': 'created', 'timestamp': time.time()}
            ... ]
            >>> is_complete = detector.detect_task_complete(task, changes)
        """
        with self._lock:
            try:
                conditions_met = 0
                total_conditions = 5

                # Condition 1: Expected files created
                expected_files = task.context.get('expected_files', [])
                if expected_files:
                    created_files = {
                        fc.get('file_path') for fc in file_changes
                        if fc.get('change_type') == 'created'
                    }
                    if all(f in created_files for f in expected_files):
                        conditions_met += 1
                        logger.debug("Task %s: Expected files created", task.id)
                else:
                    # No expected files specified - condition passes
                    conditions_met += 1

                # Condition 2: Tests passing (if required)
                requires_tests = task.context.get('requires_tests', False)
                if requires_tests:
                    # Check recent interactions for test results
                    interactions = self._state_manager.get_task_interactions(task.id)
                    test_passed = any(
                        'test' in i.response.lower() and 'pass' in i.response.lower()
                        for i in interactions[-5:] if i.response
                    )
                    if test_passed:
                        conditions_met += 1
                        logger.debug("Task %s: Tests passing", task.id)
                else:
                    # Tests not required - condition passes
                    conditions_met += 1

                # Condition 3: No errors in last N outputs
                interactions = self._state_manager.get_task_interactions(task.id)
                recent_interactions = interactions[-10:]
                has_recent_errors = any(
                    i.response and (
                        'error' in i.response.lower() or
                        'exception' in i.response.lower() or
                        'failed' in i.response.lower()
                    )
                    for i in recent_interactions
                )
                if not has_recent_errors:
                    conditions_met += 1
                    logger.debug("Task %s: No recent errors", task.id)

                # Condition 4: Completion marker in agent output
                has_completion_marker = any(
                    i.response and (
                        'complete' in i.response.lower() or
                        'done' in i.response.lower() or
                        'finished' in i.response.lower() or
                        'success' in i.response.lower()
                    )
                    for i in interactions[-3:]
                    if i.response
                )
                if has_completion_marker:
                    conditions_met += 1
                    logger.debug("Task %s: Completion marker found", task.id)

                # Condition 5: Quiescence (no file changes for N seconds)
                if file_changes:
                    # Convert file_changes dicts to have timestamp
                    recent_changes = [
                        fc for fc in file_changes
                        if 'timestamp' in fc
                    ]
                    if recent_changes:
                        last_change_time = max(
                            fc['timestamp'] for fc in recent_changes
                        )
                        time_since_change = time.time() - last_change_time
                        if time_since_change >= self._quiescence_seconds:
                            conditions_met += 1
                            logger.debug(
                                "Task %s: Quiescence period met (%.1fs)",
                                task.id, time_since_change
                            )
                    else:
                        conditions_met += 1
                else:
                    # No file changes - assume quiescence
                    conditions_met += 1

                # Task is complete if all conditions met OR 4 out of 5
                is_complete = conditions_met >= 4

                if is_complete:
                    logger.info(
                        "Task %s detected as complete (%d/%d conditions met)",
                        task.id, conditions_met, total_conditions
                    )

                    # Emit event
                    self._emit_event(Event(
                        event_type='task_complete',
                        description=f'Task {task.id} ({task.title}) is complete',
                        context={
                            'task_id': task.id,
                            'task_title': task.title,
                            'conditions_met': conditions_met,
                            'total_conditions': total_conditions
                        }
                    ))

                return is_complete

            except Exception as exc:
                logger.error("Error detecting task completion: %s", exc)
                raise EventDetectionException(
                    event_type='task_complete',
                    details=str(exc)
                ) from exc

    def detect_failure(
        self,
        recent_events: List[Dict[str, Any]]
    ) -> Optional[FailurePattern]:
        """Detect failure patterns from recent events.

        Detects:
        1. Consecutive errors (3+ errors in 10-minute window)
        2. High error rate (>50% errors in last 10 interactions)
        3. Same error repeated (same error message twice)

        Args:
            recent_events: List of recent event dictionaries with:
                - 'timestamp': Unix timestamp
                - 'event_type': Type of event
                - 'is_error': Whether event is an error (optional)
                - 'error_message': Error message if applicable (optional)

        Returns:
            FailurePattern if detected, None otherwise

        Example:
            >>> events = [
            ...     {'timestamp': time.time(), 'is_error': True, 'error_message': 'Timeout'},
            ...     {'timestamp': time.time(), 'is_error': True, 'error_message': 'Timeout'},
            ...     {'timestamp': time.time(), 'is_error': False}
            ... ]
            >>> failure = detector.detect_failure(events)
            >>> if failure:
            ...     print(failure.description)
        """
        with self._lock:
            try:
                if not recent_events:
                    return None

                current_time = time.time()

                # Pattern 1: Consecutive errors in time window
                errors_in_window = [
                    e for e in recent_events
                    if e.get('is_error', False) and
                    (current_time - e.get('timestamp', 0)) <= self._error_window_seconds
                ]

                if len(errors_in_window) >= self._consecutive_error_threshold:
                    return FailurePattern(
                        pattern_type='consecutive_errors',
                        severity='high',
                        description=(
                            f'{len(errors_in_window)} consecutive errors '
                            f'in {self._error_window_seconds}s window'
                        ),
                        evidence={
                            'error_count': len(errors_in_window),
                            'window_seconds': self._error_window_seconds,
                            'errors': errors_in_window[:5]  # First 5 errors
                        },
                        recommendation='Trigger breakpoint - pattern suggests systematic issue'
                    )

                # Pattern 2: High error rate
                last_n_events = recent_events[-10:]
                if len(last_n_events) >= 5:  # Need enough data
                    error_count = sum(1 for e in last_n_events if e.get('is_error', False))
                    error_rate = error_count / len(last_n_events)

                    if error_rate > self._error_rate_threshold:
                        return FailurePattern(
                            pattern_type='high_error_rate',
                            severity='medium',
                            description=(
                                f'Error rate {error_rate:.1%} exceeds threshold '
                                f'{self._error_rate_threshold:.1%}'
                            ),
                            evidence={
                                'error_rate': error_rate,
                                'threshold': self._error_rate_threshold,
                                'error_count': error_count,
                                'total_events': len(last_n_events)
                            },
                            recommendation='Review recent interactions for common failure cause'
                        )

                # Pattern 3: Same error repeated
                error_messages = [
                    e.get('error_message', '') for e in recent_events
                    if e.get('is_error', False) and e.get('error_message')
                ]

                if error_messages:
                    # Count occurrences
                    message_counts = defaultdict(int)
                    for msg in error_messages:
                        message_counts[msg] += 1

                    # Check for repeated errors
                    for msg, count in message_counts.items():
                        if count >= 2:
                            return FailurePattern(
                                pattern_type='repeated_error',
                                severity='medium',
                                description=f'Error repeated {count} times: {msg[:100]}',
                                evidence={
                                    'error_message': msg,
                                    'occurrence_count': count
                                },
                                recommendation=(
                                    'Same error repeating - likely needs different approach'
                                )
                            )

                return None

            except Exception as exc:
                logger.error("Error detecting failure patterns: %s", exc)
                raise EventDetectionException(
                    event_type='failure_detection',
                    details=str(exc)
                ) from exc

    def detect_milestone_complete(
        self,
        project_state: ProjectState
    ) -> bool:
        """Detect if a milestone is complete.

        Checks:
        1. All tasks in milestone marked complete
        2. All tests passing (if applicable)
        3. Documentation updated (if required)
        4. No blocking issues remaining

        Args:
            project_state: ProjectState to check

        Returns:
            True if milestone appears complete

        Example:
            >>> project = state_manager.get_project(project_id)
            >>> is_complete = detector.detect_milestone_complete(project)
        """
        with self._lock:
            try:
                # Get milestone info from project metadata
                milestone_config = project_state.project_metadata.get('current_milestone', {})
                if not milestone_config:
                    logger.debug("No milestone configured for project %s", project_state.id)
                    return False

                milestone_tasks = milestone_config.get('task_ids', [])
                if not milestone_tasks:
                    logger.debug("No tasks in milestone")
                    return False

                # Check all tasks are complete
                incomplete_tasks = []
                for task_id in milestone_tasks:
                    task = self._state_manager.get_task(task_id)
                    if task and task.status != TaskStatus.COMPLETED:
                        incomplete_tasks.append(task_id)

                if incomplete_tasks:
                    logger.debug(
                        "Milestone incomplete: %d tasks remaining",
                        len(incomplete_tasks)
                    )
                    return False

                # Check tests (if applicable)
                requires_tests = milestone_config.get('requires_tests', False)
                if requires_tests:
                    # Check recent interactions for test results
                    interactions = self._state_manager.get_interactions(
                        project_state.id,
                        limit=20
                    )
                    test_passed = any(
                        i.response and 'test' in i.response.lower() and
                        'pass' in i.response.lower()
                        for i in interactions
                    )
                    if not test_passed:
                        logger.debug("Milestone tests not passing")
                        return False

                # Check documentation (if required)
                requires_docs = milestone_config.get('requires_documentation', False)
                if requires_docs:
                    # Check for doc file changes
                    file_changes = self._state_manager.get_file_changes(project_state.id)
                    doc_files = [
                        fc for fc in file_changes
                        if fc.file_path.endswith(('.md', '.rst', '.txt'))
                    ]
                    if not doc_files:
                        logger.debug("Milestone documentation not updated")
                        return False

                # All checks passed
                logger.info("Milestone complete for project %s", project_state.id)

                # Emit event
                self._emit_event(Event(
                    event_type='milestone_complete',
                    description=f'Milestone {milestone_config.get("name", "unknown")} complete',
                    context={
                        'project_id': project_state.id,
                        'milestone_name': milestone_config.get('name'),
                        'tasks_completed': len(milestone_tasks)
                    }
                ))

                return True

            except Exception as exc:
                logger.error("Error detecting milestone completion: %s", exc)
                raise EventDetectionException(
                    event_type='milestone_complete',
                    details=str(exc)
                ) from exc

    def detect_anomaly(
        self,
        metric: str,
        value: float
    ) -> bool:
        """Detect anomalies using statistical methods.

        Uses baseline window to calculate mean and standard deviation,
        then checks if value deviates by more than sensitivity threshold.

        Args:
            metric: Metric name (e.g., 'file_change_rate', 'error_rate')
            value: Current value to check

        Returns:
            True if value is anomalous

        Example:
            >>> # Track normal values
            >>> for i in range(100):
            ...     detector.detect_anomaly('response_time', 2.5)
            >>>
            >>> # Check for anomaly
            >>> is_anomaly = detector.detect_anomaly('response_time', 25.0)  # True
        """
        with self._lock:
            try:
                # Add value to baseline
                baseline = self._metric_baselines[metric]
                baseline.append(value)

                # Need enough data for statistical analysis
                if len(baseline) < 10:
                    return False

                # Calculate statistics
                mean = statistics.mean(baseline)

                # Need variance for std dev
                if len(baseline) < 2:
                    return False

                try:
                    stdev = statistics.stdev(baseline)
                except statistics.StatisticsError:
                    # All values are the same
                    return abs(value - mean) > 0.01

                # Avoid division by zero
                if stdev < 0.001:
                    return abs(value - mean) > 0.01

                # Calculate z-score
                z_score = abs(value - mean) / stdev

                # Check if anomalous
                is_anomaly = z_score > self._anomaly_sensitivity

                if is_anomaly:
                    logger.warning(
                        "Anomaly detected for %s: value=%.2f, mean=%.2f, "
                        "stdev=%.2f, z-score=%.2f",
                        metric, value, mean, stdev, z_score
                    )

                    # Emit event
                    self._emit_event(Event(
                        event_type='anomaly_detected',
                        description=f'Anomaly in {metric}: {value:.2f} (z-score: {z_score:.2f})',
                        context={
                            'metric': metric,
                            'value': value,
                            'mean': mean,
                            'stdev': stdev,
                            'z_score': z_score
                        }
                    ))

                return is_anomaly

            except Exception as exc:
                logger.error("Error detecting anomaly: %s", exc)
                return False

    def detect_state_change(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any]
    ) -> Optional[Event]:
        """Detect significant state changes.

        Args:
            old_state: Previous state dictionary
            new_state: New state dictionary

        Returns:
            Event if significant change detected, None otherwise

        Example:
            >>> old = {'status': 'running', 'progress': 50}
            >>> new = {'status': 'completed', 'progress': 100}
            >>> event = detector.detect_state_change(old, new)
            >>> if event:
            ...     print(event.description)
        """
        with self._lock:
            try:
                # Detect status changes
                old_status = old_state.get('status')
                new_status = new_state.get('status')

                if old_status != new_status:
                    event = Event(
                        event_type='state_change',
                        description=f'Status changed from {old_status} to {new_status}',
                        context={
                            'field': 'status',
                            'old_value': old_status,
                            'new_value': new_status
                        }
                    )

                    logger.info(
                        "State change detected: status %s -> %s",
                        old_status, new_status
                    )

                    self._emit_event(event)
                    return event

                # Could add more state change detections here
                # (e.g., priority changes, assignment changes, etc.)

                return None

            except Exception as exc:
                logger.error("Error detecting state change: %s", exc)
                return None

    def check_thresholds(
        self,
        current_values: Dict[str, float]
    ) -> List[ThresholdEvent]:
        """Check current values against configured thresholds.

        Args:
            current_values: Dictionary of metric name -> current value
            Expected keys:
                - 'error_count': Number of errors
                - 'duration_seconds': Time elapsed
                - 'budget_used': Budget used (if applicable)
                - 'iteration_count': Number of iterations

        Returns:
            List of ThresholdEvent objects for violated thresholds

        Example:
            >>> values = {
            ...     'error_count': 15,
            ...     'duration_seconds': 7200,
            ...     'iteration_count': 50
            ... }
            >>> violations = detector.check_thresholds(values)
            >>> for v in violations:
            ...     print(f"{v.threshold_name}: {v.current_value} > {v.threshold_value}")
        """
        with self._lock:
            violations = []

            try:
                # Define thresholds
                thresholds = {
                    'error_count': 10,
                    'duration_seconds': 3600,  # 1 hour
                    'iteration_count': 100
                }

                for metric, threshold_value in thresholds.items():
                    current_value = current_values.get(metric, 0)

                    if current_value > threshold_value:
                        violation = ThresholdEvent(
                            threshold_name=metric,
                            current_value=current_value,
                            threshold_value=threshold_value,
                            exceeded=True
                        )
                        violations.append(violation)

                        logger.warning(
                            "Threshold violated: %s = %.2f > %.2f",
                            metric, current_value, threshold_value
                        )

                        # Emit event
                        self._emit_event(Event(
                            event_type='threshold_violated',
                            description=(
                                f'{metric} exceeded threshold: '
                                f'{current_value:.2f} > {threshold_value:.2f}'
                            ),
                            context={
                                'metric': metric,
                                'current_value': current_value,
                                'threshold_value': threshold_value
                            }
                        ))

                return violations

            except Exception as exc:
                logger.error("Error checking thresholds: %s", exc)
                return violations

    def should_trigger_event(
        self,
        event_type: str,
        context: Dict[str, Any]
    ) -> bool:
        """Check if event should be triggered based on debouncing.

        Prevents duplicate events within debounce window.

        Args:
            event_type: Type of event
            context: Event context (used for deduplication)

        Returns:
            True if event should be triggered

        Example:
            >>> if detector.should_trigger_event('task_complete', {'task_id': 123}):
            ...     # Trigger event
            ...     pass
        """
        with self._lock:
            # Create event key from type and context
            event_key = f"{event_type}:{hash(frozenset(context.items()))}"

            current_time = time.time()
            last_time = self._last_event_time.get(event_key, 0)

            # Check if within debounce window
            if current_time - last_time < self._event_debounce_window:
                logger.debug("Event %s debounced", event_type)
                return False

            # Update last event time
            self._last_event_time[event_key] = current_time
            return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get event detection statistics.

        Returns:
            Dictionary with statistics about detected events

        Example:
            >>> stats = detector.get_statistics()
            >>> print(f"Baseline metrics tracked: {stats['baseline_metrics']}")
        """
        with self._lock:
            return {
                'baseline_metrics': list(self._metric_baselines.keys()),
                'baseline_samples': {
                    metric: len(baseline)
                    for metric, baseline in self._metric_baselines.items()
                },
                'event_callbacks': len(self._event_callbacks),
                'last_events': len(self._last_event_time)
            }
