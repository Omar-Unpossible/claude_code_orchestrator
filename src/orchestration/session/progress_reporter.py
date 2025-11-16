"""Progress reporter for structured session progress tracking.

This module implements the ProgressReporter class that generates structured
JSON progress reports after each task or NL command execution.

Example:
    >>> from src.orchestration.session import ProgressReporter
    >>> reporter = ProgressReporter(config, production_logger)
    >>> report = reporter.generate_progress_report(
    ...     session_id='sess_123',
    ...     operation='task_execution',
    ...     task=task,
    ...     result=result
    ... )
    >>> reporter.log_progress(report)

Author: Obra System
Created: 2025-11-15
Version: 1.0.0
"""

import logging
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List

from src.core.config import Config


logger = logging.getLogger(__name__)


class ProgressReport:
    """Represents a structured progress report.

    Attributes:
        timestamp: When report was generated
        session_id: Orchestrator session ID
        operation: Operation type (task_execution, nl_command, handoff, etc.)
        status: Operation status (success, failure, in_progress)
        test_status: Test execution status
        context_usage: Context window usage info
        next_steps: Predicted next steps
        metadata: Additional operation-specific data
    """

    def __init__(
        self,
        timestamp: datetime,
        session_id: str,
        operation: str,
        status: str,
        test_status: Optional[Dict[str, Any]] = None,
        context_usage: Optional[Dict[str, Any]] = None,
        next_steps: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize progress report."""
        self.timestamp = timestamp
        self.session_id = session_id
        self.operation = operation
        self.status = status
        self.test_status = test_status or {}
        self.context_usage = context_usage or {}
        self.next_steps = next_steps or []
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation suitable for JSON logging
        """
        return {
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'operation': self.operation,
            'status': self.status,
            'test_status': self.test_status,
            'context_usage': self.context_usage,
            'next_steps': self.next_steps,
            'metadata': self.metadata
        }


class ProgressReporter:
    """Generate and log structured progress reports.

    This class creates progress reports after each task/NL command execution,
    providing visibility into session progress, context usage, and next steps.

    Thread-safe: Yes (uses ProductionLogger which is thread-safe)

    Attributes:
        config: Obra configuration
        production_logger: ProductionLogger for JSON Lines output
        enabled: Whether progress reporting is enabled

    Example:
        >>> reporter = ProgressReporter(config, production_logger)
        >>>
        >>> # After task execution
        >>> report = reporter.generate_progress_report(
        ...     session_id='sess_123',
        ...     operation='task_execution',
        ...     task=task,
        ...     result={'success': True},
        ...     context_mgr=context_manager
        ... )
        >>> reporter.log_progress(report)
    """

    # Operation types
    OPERATION_TASK_EXECUTION = 'task_execution'
    OPERATION_NL_COMMAND = 'nl_command'
    OPERATION_SELF_HANDOFF = 'self_handoff'
    OPERATION_CHECKPOINT = 'checkpoint'
    OPERATION_DECISION = 'decision'

    # Status values
    STATUS_SUCCESS = 'success'
    STATUS_FAILURE = 'failure'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_BLOCKED = 'blocked'

    def __init__(self, config: Config, production_logger: Any = None):
        """Initialize progress reporter.

        Args:
            config: Obra configuration
            production_logger: Optional ProductionLogger instance
        """
        self.config = config
        self.production_logger = production_logger

        # Configuration
        self.enabled = config.get(
            'orchestrator.session_continuity.progress_reporting.enabled', True
        )
        self.destination = config.get(
            'orchestrator.session_continuity.progress_reporting.destination',
            'production_log'
        )

        logger.info(
            "ProgressReporter initialized: enabled=%s, destination=%s",
            self.enabled, self.destination
        )

    def generate_progress_report(
        self,
        session_id: str,
        operation: str,
        status: str = STATUS_SUCCESS,
        task: Any = None,
        result: Optional[Dict[str, Any]] = None,
        context_mgr: Any = None,
        **kwargs
    ) -> ProgressReport:
        """Generate progress report from execution context.

        Args:
            session_id: Orchestrator session ID
            operation: Operation type
            status: Operation status
            task: Optional task being executed
            result: Optional execution result
            context_mgr: Optional OrchestratorContextManager (ADR-018)
            **kwargs: Additional metadata

        Returns:
            ProgressReport object
        """
        # Extract test status
        test_status = self._extract_test_status(result)

        # Extract context usage
        context_usage = self._extract_context_usage(context_mgr)

        # Predict next steps
        next_steps = self._predict_next_steps(operation, status, result)

        # Build metadata
        metadata = self._build_metadata(task, result, kwargs)

        # Create report
        report = ProgressReport(
            timestamp=datetime.now(UTC),
            session_id=session_id,
            operation=operation,
            status=status,
            test_status=test_status,
            context_usage=context_usage,
            next_steps=next_steps,
            metadata=metadata
        )

        logger.debug(
            "Generated progress report: session=%s, operation=%s, status=%s",
            session_id, operation, status
        )

        return report

    def log_progress(self, report: ProgressReport) -> None:
        """Log progress report to configured destination.

        Args:
            report: ProgressReport to log
        """
        if not self.enabled:
            return

        if self.destination == 'production_log' and self.production_logger:
            # Log to ProductionLogger
            report_dict = report.to_dict()
            # Remove session_id from dict since it's passed separately
            report_dict_without_session = {k: v for k, v in report_dict.items() if k != 'session_id'}

            self.production_logger._log_event(  # pylint: disable=protected-access
                event_type='progress_report',
                session_id=report.session_id,
                **report_dict_without_session
            )
        else:
            # Fallback to standard logging
            logger.info(
                "Progress: session=%s, operation=%s, status=%s",
                report.session_id, report.operation, report.status
            )

    def _extract_test_status(self, result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract test execution status from result.

        Args:
            result: Execution result

        Returns:
            Test status dictionary
        """
        if not result:
            return {'tests_run': False}

        test_info = result.get('test_info', {})

        return {
            'tests_run': bool(test_info),
            'tests_passed': test_info.get('passed', 0),
            'tests_failed': test_info.get('failed', 0),
            'coverage_percent': test_info.get('coverage', 0.0)
        }

    def _extract_context_usage(
        self,
        context_mgr: Any  # Type: OrchestratorContextManager from ADR-018
    ) -> Dict[str, Any]:
        """Extract context window usage from context manager.

        Args:
            context_mgr: OrchestratorContextManager instance

        Returns:
            Context usage dictionary
        """
        if not context_mgr:
            return {
                'available': False,
                'percentage': 0.0,
                'zone': 'unknown'
            }

        try:
            return {
                'available': True,
                'percentage': context_mgr.get_usage_percentage(),
                'zone': context_mgr.get_zone(),
                'tokens_used': context_mgr.get_total_tokens()
            }
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to extract context usage: %s", e)
            return {
                'available': False,
                'error': str(e)
            }

    def _predict_next_steps(
        self,
        operation: str,
        status: str,
        result: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Predict next steps based on operation and status.

        Args:
            operation: Operation type
            status: Operation status
            result: Execution result

        Returns:
            List of predicted next steps
        """
        next_steps = []

        if status == self.STATUS_SUCCESS:
            if operation == self.OPERATION_TASK_EXECUTION:
                next_steps.append("Mark task as complete")
                next_steps.append("Move to next task in queue")
            elif operation == self.OPERATION_NL_COMMAND:
                next_steps.append("Return result to user")
            elif operation == self.OPERATION_SELF_HANDOFF:
                next_steps.append("Resume operation with fresh context")
        elif status == self.STATUS_FAILURE:
            next_steps.append("Analyze failure cause")
            next_steps.append("Determine if retry is appropriate")
            if result and result.get('test_info', {}).get('failed', 0) > 0:
                next_steps.append("Fix failing tests")
        elif status == self.STATUS_BLOCKED:
            next_steps.append("Request human intervention")

        return next_steps

    def _build_metadata(
        self,
        task: Any,
        result: Optional[Dict[str, Any]],
        additional: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build metadata dictionary.

        Args:
            task: Task being executed
            result: Execution result
            additional: Additional metadata from kwargs

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # Task info
        if task:
            metadata['task_id'] = getattr(task, 'id', None)
            metadata['task_title'] = getattr(task, 'title', None)
            metadata['task_status'] = getattr(task, 'status', None)

        # Result info
        if result:
            metadata['execution_time_ms'] = result.get('duration_ms')
            metadata['iterations'] = result.get('iterations', 0)
            metadata['quality_score'] = result.get('quality_score')
            metadata['confidence_score'] = result.get('confidence_score')

        # Additional metadata
        metadata.update(additional)

        return metadata
