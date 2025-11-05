"""Exception hierarchy for the orchestrator core components.

This module defines exceptions for:
- State management (database, transactions, checkpoints)
- Configuration
- Validation and quality control
- Orchestration (tasks, breakpoints)
- Monitoring (file watching)

Note: Agent and LLM exceptions are in src/plugins/exceptions.py
"""

from typing import Optional, Dict, Any


class OrchestratorException(Exception):
    """Base exception for all orchestrator errors.

    All orchestrator exceptions preserve context and provide recovery suggestions.

    Attributes:
        message: Human-readable error message
        context_data: Dictionary with error context
        recovery_suggestion: Actionable advice for recovery

    Example:
        >>> raise OrchestratorException(
        ...     "Operation failed",
        ...     context={'operation': 'task_scheduling'},
        ...     recovery="Retry the operation"
        ... )
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        recovery: Optional[str] = None
    ):
        """Initialize orchestrator exception.

        Args:
            message: Error message
            context: Optional context dictionary
            recovery: Optional recovery suggestion
        """
        super().__init__(message)
        self.context_data = context or {}
        self.recovery_suggestion = recovery

    def __repr__(self) -> str:
        """Return detailed representation."""
        return (
            f"{self.__class__.__name__}("
            f"message={str(self)!r}, "
            f"context={self.context_data!r}, "
            f"recovery={self.recovery_suggestion!r})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize exception to dictionary for logging/JSON.

        Returns:
            Dictionary with type, message, context, and recovery

        Example:
            >>> exc = OrchestratorException("Error", context={'key': 'value'})
            >>> exc.to_dict()
            {'type': 'OrchestratorException', 'message': 'Error', ...}
        """
        return {
            'type': self.__class__.__name__,
            'message': str(self),
            'context': self.context_data,
            'recovery': self.recovery_suggestion
        }


# State Management Exceptions

class StateManagerException(OrchestratorException):
    """Base exception for state management errors."""
    pass


class DatabaseException(StateManagerException):
    """Raised when database operations fail.

    Common causes:
    - Connection lost
    - Schema migration needed
    - Disk full
    - Permissions issue

    Example:
        >>> raise DatabaseException(
        ...     operation='insert_task',
        ...     details='Connection lost'
        ... )
    """

    def __init__(self, operation: str, details: str):
        """Initialize database exception.

        Args:
            operation: Database operation that failed
            details: Detailed error message
        """
        context = {
            'operation': operation,
            'details': details
        }
        recovery = (
            'Check database connectivity, verify schema is up to date, '
            'and ensure sufficient disk space'
        )
        super().__init__(
            f'Database operation "{operation}" failed: {details}',
            context,
            recovery
        )


class TransactionException(StateManagerException):
    """Raised when transaction fails.

    Common causes:
    - Deadlock
    - Constraint violation
    - Timeout
    - Connection lost during transaction

    Example:
        >>> raise TransactionException(
        ...     reason='Deadlock detected',
        ...     operations=['update_task', 'create_interaction']
        ... )
    """

    def __init__(self, reason: str, operations: list):
        """Initialize transaction exception.

        Args:
            reason: Why transaction failed
            operations: List of operations in the transaction
        """
        context = {
            'reason': reason,
            'operations': operations
        }
        recovery = (
            'Transaction has been rolled back. Retry the operation. '
            'If deadlocks persist, check for long-running transactions.'
        )
        super().__init__(
            f'Transaction failed: {reason}',
            context,
            recovery
        )


class CheckpointException(StateManagerException):
    """Raised when checkpoint operations fail.

    Common causes:
    - Disk full (cannot save checkpoint)
    - Checkpoint not found (cannot restore)
    - Checkpoint corrupted
    - Serialization error

    Example:
        >>> raise CheckpointException(
        ...     operation='restore',
        ...     checkpoint_id='chk_123',
        ...     details='Checkpoint not found'
        ... )
    """

    def __init__(self, operation: str, checkpoint_id: str, details: str):
        """Initialize checkpoint exception.

        Args:
            operation: Operation that failed ('create' or 'restore')
            checkpoint_id: Checkpoint identifier
            details: Error details
        """
        context = {
            'operation': operation,
            'checkpoint_id': checkpoint_id,
            'details': details
        }
        recovery = (
            'Check available checkpoints with list_checkpoints(). '
            'Ensure sufficient disk space for creating checkpoints.'
        )
        super().__init__(
            f'Checkpoint {operation} failed for {checkpoint_id}: {details}',
            context,
            recovery
        )


# Configuration Exceptions

class ConfigException(OrchestratorException):
    """Base exception for configuration errors."""
    pass


class ConfigValidationException(ConfigException):
    """Raised when configuration fails validation.

    Common causes:
    - Invalid YAML syntax
    - Missing required fields
    - Invalid values (wrong type, out of range)
    - Schema violation

    Example:
        >>> raise ConfigValidationException(
        ...     config_key='agent.type',
        ...     expected='string',
        ...     got='int'
        ... )
    """

    def __init__(self, config_key: str, expected: str, got: str):
        """Initialize config validation exception.

        Args:
            config_key: Configuration key that failed validation
            expected: Expected value/type
            got: Actual value/type received
        """
        context = {
            'config_key': config_key,
            'expected': expected,
            'got': got
        }
        recovery = (
            f'Check configuration file, ensure {config_key} is {expected}. '
            'See docs/configuration.md for examples.'
        )
        super().__init__(
            f'Configuration validation failed for {config_key}: '
            f'expected {expected}, got {got}',
            context,
            recovery
        )


class ConfigNotFoundException(ConfigException):
    """Raised when configuration file not found.

    Example:
        >>> raise ConfigNotFoundException(
        ...     config_path='/path/to/config.yaml'
        ... )
    """

    def __init__(self, config_path: str):
        """Initialize config not found exception.

        Args:
            config_path: Path to configuration file
        """
        context = {'config_path': config_path}
        recovery = (
            'Create configuration file at the specified path, '
            'or use --config flag to specify alternate location. '
            'See config/default_config.yaml for template.'
        )
        super().__init__(
            f'Configuration file not found: {config_path}',
            context,
            recovery
        )


# Validation Exceptions

class ValidationException(OrchestratorException):
    """Base exception for validation errors."""
    pass


class ResponseIncompleteException(ValidationException):
    """Raised when agent response is incomplete.

    Common causes:
    - Response truncated
    - Code blocks not closed
    - Missing required sections
    - Timeout during generation

    Example:
        >>> raise ResponseIncompleteException(
        ...     reason='Code block not closed',
        ...     response_preview='def main():\\n    ...'
        ... )
    """

    def __init__(self, reason: str, response_preview: str):
        """Initialize response incomplete exception.

        Args:
            reason: Why response is considered incomplete
            response_preview: First 100 chars of response
        """
        context = {
            'reason': reason,
            'response_preview': response_preview[:100]
        }
        recovery = (
            'Retry with clarification: "Please complete your response, '
            'you were cut off at..."'
        )
        super().__init__(
            f'Response incomplete: {reason}',
            context,
            recovery
        )


class QualityTooLowException(ValidationException):
    """Raised when quality score below threshold.

    Example:
        >>> raise QualityTooLowException(
        ...     quality_score=45,
        ...     threshold=70,
        ...     issues=['Tests failed', 'Missing docstrings']
        ... )
    """

    def __init__(self, quality_score: float, threshold: float, issues: list):
        """Initialize quality too low exception.

        Args:
            quality_score: Actual quality score (0-100)
            threshold: Minimum acceptable score
            issues: List of quality issues found
        """
        context = {
            'quality_score': quality_score,
            'threshold': threshold,
            'issues': issues
        }
        recovery = (
            'Retry with feedback highlighting specific issues. '
            'Consider lowering quality threshold if appropriate.'
        )
        super().__init__(
            f'Quality score {quality_score} below threshold {threshold}',
            context,
            recovery
        )


class ConfidenceTooLowException(ValidationException):
    """Raised when confidence score too low to proceed.

    Example:
        >>> raise ConfidenceTooLowException(
        ...     confidence_score=25,
        ...     threshold=30,
        ...     reason='Multiple validation failures'
        ... )
    """

    def __init__(self, confidence_score: float, threshold: float, reason: str):
        """Initialize confidence too low exception.

        Args:
            confidence_score: Actual confidence (0-100)
            threshold: Minimum acceptable confidence
            reason: Why confidence is low
        """
        context = {
            'confidence_score': confidence_score,
            'threshold': threshold,
            'reason': reason
        }
        recovery = (
            'Trigger breakpoint for human intervention. '
            'Consider adjusting confidence thresholds if too strict.'
        )
        super().__init__(
            f'Confidence {confidence_score} below threshold {threshold}: {reason}',
            context,
            recovery
        )


# Orchestration Exceptions

class OrchestrationException(OrchestratorException):
    """Base exception for orchestration errors."""
    pass


class TaskDependencyError(OrchestrationException):
    """Raised when task dependencies cannot be resolved.

    Common causes:
    - Circular dependency
    - Dependency on non-existent task
    - Dependency on failed task

    Example:
        >>> raise TaskDependencyError(
        ...     task_id='task-123',
        ...     dependency_chain=['task-123', 'task-456', 'task-123']
        ... )
    """

    def __init__(self, task_id: str, dependency_chain: list):
        """Initialize task dependency error.

        Args:
            task_id: ID of task with dependency issue
            dependency_chain: Chain showing circular dependency
        """
        context = {
            'task_id': task_id,
            'dependency_chain': dependency_chain
        }
        recovery = (
            'Break circular dependency by removing one dependency link, '
            'or ensure all referenced tasks exist.'
        )
        super().__init__(
            f'Task {task_id} has unresolvable dependencies: {dependency_chain}',
            context,
            recovery
        )


# Alias for consistency with other exception names
TaskDependencyException = TaskDependencyError


class TaskStateException(OrchestrationException):
    """Raised when task state transition is invalid or task state is inconsistent.

    Common causes:
    - Invalid state transition
    - Task not found
    - Task in unexpected state
    - State corruption

    Example:
        >>> raise TaskStateException(
        ...     message='Invalid transition: completed -> running',
        ...     context={'task_id': 123, 'current_state': 'completed'},
        ...     recovery='Task cannot be re-run once completed'
        ... )
    """
    pass


class BreakpointTriggered(OrchestrationException):
    """Raised when breakpoint is triggered (not an error, but uses exception for flow control).

    Example:
        >>> raise BreakpointTriggered(
        ...     reason='Low confidence',
        ...     task_id='task-123',
        ...     context_info={'confidence': 25}
        ... )
    """

    def __init__(self, reason: str, task_id: str, context_info: dict):
        """Initialize breakpoint triggered.

        Args:
            reason: Why breakpoint was triggered
            task_id: Current task ID
            context_info: Additional context for user
        """
        context = {
            'reason': reason,
            'task_id': task_id,
            **context_info
        }
        recovery = (
            'User intervention required. Review context and provide guidance.'
        )
        super().__init__(
            f'Breakpoint triggered: {reason}',
            context,
            recovery
        )


class RateLimitHit(OrchestrationException):
    """Raised when rate limit is hit.

    Example:
        >>> raise RateLimitHit(
        ...     service='claude-code',
        ...     retry_after=60
        ... )
    """

    def __init__(self, service: str, retry_after: int):
        """Initialize rate limit exception.

        Args:
            service: Service that hit rate limit
            retry_after: Seconds to wait before retry
        """
        context = {
            'service': service,
            'retry_after': retry_after
        }
        recovery = (
            f'Wait {retry_after} seconds before retrying. '
            'Consider adding rate limit handling to prevent this.'
        )
        super().__init__(
            f'Rate limit hit for {service}, retry after {retry_after}s',
            context,
            recovery
        )


class TaskStoppedException(OrchestrationException):
    """Raised when user requests task stop via /stop command.

    This is used for flow control in interactive mode, not an error condition.
    The task is gracefully stopped after completing the current turn.

    Example:
        >>> raise TaskStoppedException(
        ...     'User requested stop',
        ...     context={'task_id': 123, 'iterations_completed': 5}
        ... )
    """
    pass


# Monitoring Exceptions

class MonitoringException(OrchestratorException):
    """Base exception for monitoring errors."""
    pass


class FileWatcherException(MonitoringException):
    """Raised when file watching fails.

    Common causes:
    - Too many open files
    - Permission denied
    - Path doesn't exist
    - Watchdog library issue

    Example:
        >>> raise FileWatcherException(
        ...     path='/workspace',
        ...     details='Permission denied'
        ... )
    """

    def __init__(self, path: str, details: str):
        """Initialize file watcher exception.

        Args:
            path: Path being watched
            details: Error details
        """
        context = {
            'path': path,
            'details': details
        }
        recovery = (
            'Check path exists and has correct permissions. '
            'Verify system file descriptor limits (ulimit -n).'
        )
        super().__init__(
            f'File watcher failed for {path}: {details}',
            context,
            recovery
        )


class EventDetectionException(MonitoringException):
    """Raised when event detection fails.

    Example:
        >>> raise EventDetectionException(
        ...     event_type='completion',
        ...     details='Timeout waiting for completion marker'
        ... )
    """

    def __init__(self, event_type: str, details: str):
        """Initialize event detection exception.

        Args:
            event_type: Type of event being detected
            details: Error details
        """
        context = {
            'event_type': event_type,
            'details': details
        }
        recovery = (
            'Check event detection patterns are correct. '
            'Verify agent output format hasn\'t changed.'
        )
        super().__init__(
            f'Event detection failed for {event_type}: {details}',
            context,
            recovery
        )
