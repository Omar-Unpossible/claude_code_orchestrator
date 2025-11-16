"""Unit tests for ProgressReporter.

Tests structured progress reporting, JSON serialization, and integration with ProductionLogger.
Follows TEST_GUIDELINES.md constraints (max 0.5s sleep, 5 threads, 20KB).
"""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, MagicMock, call

from src.orchestration.session.progress_reporter import (
    ProgressReporter,
    ProgressReport
)
from src.core.config import Config


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)

    config_data = {
        'orchestrator': {
            'session_continuity': {
                'progress_reporting': {
                    'enabled': True,
                    'destination': 'production_log'
                }
            }
        }
    }

    def get_nested(key, default=None):
        """Navigate nested config dict."""
        keys = key.split('.')
        value = config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    config.get = get_nested
    config._config = config_data

    return config


@pytest.fixture
def mock_production_logger():
    """Create mock ProductionLogger."""
    logger = Mock()
    logger._log_event = Mock()
    return logger


@pytest.fixture
def mock_task():
    """Create mock task."""
    task = Mock()
    task.id = 123
    task.title = "Implement feature X"
    task.status = "running"
    return task


@pytest.fixture
def mock_context_manager():
    """Create mock OrchestratorContextManager."""
    context_mgr = Mock()
    context_mgr.get_usage_percentage = Mock(return_value=45.5)
    context_mgr.get_zone = Mock(return_value='green')
    context_mgr.get_total_tokens = Mock(return_value=10000)
    return context_mgr


@pytest.fixture
def reporter(mock_config, mock_production_logger):
    """Create ProgressReporter instance."""
    return ProgressReporter(mock_config, mock_production_logger)


class TestInitialization:
    """Test ProgressReporter initialization."""

    def test_initialization_success(self, mock_config, mock_production_logger):
        """Test successful initialization."""
        reporter = ProgressReporter(mock_config, mock_production_logger)

        assert reporter.config == mock_config
        assert reporter.production_logger == mock_production_logger
        assert reporter.enabled is True
        assert reporter.destination == 'production_log'

    def test_initialization_disabled(self, mock_config, mock_production_logger):
        """Test initialization with reporting disabled."""
        mock_config._config['orchestrator']['session_continuity']['progress_reporting']['enabled'] = False

        reporter = ProgressReporter(mock_config, mock_production_logger)

        assert reporter.enabled is False

    def test_initialization_without_production_logger(self, mock_config):
        """Test initialization without production logger."""
        reporter = ProgressReporter(mock_config, production_logger=None)

        assert reporter.production_logger is None


class TestProgressReportGeneration:
    """Test progress report generation."""

    def test_generate_basic_report(self, reporter):
        """Test basic report generation."""
        report = reporter.generate_progress_report(
            session_id='sess_123',
            operation=reporter.OPERATION_TASK_EXECUTION,
            status=reporter.STATUS_SUCCESS
        )

        assert isinstance(report, ProgressReport)
        assert report.session_id == 'sess_123'
        assert report.operation == reporter.OPERATION_TASK_EXECUTION
        assert report.status == reporter.STATUS_SUCCESS
        assert report.timestamp is not None

    def test_generate_report_with_task(self, reporter, mock_task):
        """Test report generation with task."""
        report = reporter.generate_progress_report(
            session_id='sess_123',
            operation=reporter.OPERATION_TASK_EXECUTION,
            task=mock_task
        )

        assert report.metadata['task_id'] == 123
        assert report.metadata['task_title'] == "Implement feature X"
        assert report.metadata['task_status'] == "running"

    def test_generate_report_with_result(self, reporter):
        """Test report generation with execution result."""
        result = {
            'success': True,
            'duration_ms': 1500,
            'iterations': 3,
            'quality_score': 0.85,
            'confidence_score': 0.90,
            'test_info': {
                'passed': 10,
                'failed': 0,
                'coverage': 92.5
            }
        }

        report = reporter.generate_progress_report(
            session_id='sess_123',
            operation=reporter.OPERATION_TASK_EXECUTION,
            result=result
        )

        # Test status should be extracted
        assert report.test_status['tests_run'] is True
        assert report.test_status['tests_passed'] == 10
        assert report.test_status['tests_failed'] == 0
        assert report.test_status['coverage_percent'] == 92.5

        # Metadata should include result info
        assert report.metadata['execution_time_ms'] == 1500
        assert report.metadata['iterations'] == 3
        assert report.metadata['quality_score'] == 0.85
        assert report.metadata['confidence_score'] == 0.90

    def test_generate_report_with_context_manager(self, reporter, mock_context_manager):
        """Test report generation with context manager."""
        report = reporter.generate_progress_report(
            session_id='sess_123',
            operation=reporter.OPERATION_TASK_EXECUTION,
            context_mgr=mock_context_manager
        )

        # Context usage should be extracted
        assert report.context_usage['available'] is True
        assert report.context_usage['percentage'] == 45.5
        assert report.context_usage['zone'] == 'green'
        assert report.context_usage['tokens_used'] == 10000


class TestTestStatusExtraction:
    """Test test status extraction."""

    def test_extract_test_status_with_tests(self, reporter):
        """Test extraction when tests were run."""
        result = {
            'test_info': {
                'passed': 15,
                'failed': 2,
                'coverage': 88.5
            }
        }

        test_status = reporter._extract_test_status(result)  # pylint: disable=protected-access

        assert test_status['tests_run'] is True
        assert test_status['tests_passed'] == 15
        assert test_status['tests_failed'] == 2
        assert test_status['coverage_percent'] == 88.5

    def test_extract_test_status_no_tests(self, reporter):
        """Test extraction when no tests run."""
        result = {}

        test_status = reporter._extract_test_status(result)  # pylint: disable=protected-access

        assert test_status['tests_run'] is False

    def test_extract_test_status_none(self, reporter):
        """Test extraction with None result."""
        test_status = reporter._extract_test_status(None)  # pylint: disable=protected-access

        assert test_status['tests_run'] is False


class TestContextUsageExtraction:
    """Test context usage extraction."""

    def test_extract_context_usage_success(self, reporter, mock_context_manager):
        """Test successful context usage extraction."""
        context_usage = reporter._extract_context_usage(  # pylint: disable=protected-access
            mock_context_manager
        )

        assert context_usage['available'] is True
        assert context_usage['percentage'] == 45.5
        assert context_usage['zone'] == 'green'
        assert context_usage['tokens_used'] == 10000

    def test_extract_context_usage_none(self, reporter):
        """Test extraction when context manager is None."""
        context_usage = reporter._extract_context_usage(None)  # pylint: disable=protected-access

        assert context_usage['available'] is False
        assert context_usage['percentage'] == 0.0
        assert context_usage['zone'] == 'unknown'

    def test_extract_context_usage_error(self, reporter, mock_context_manager):
        """Test extraction when context manager raises error."""
        mock_context_manager.get_usage_percentage.side_effect = Exception("Context error")

        context_usage = reporter._extract_context_usage(  # pylint: disable=protected-access
            mock_context_manager
        )

        assert context_usage['available'] is False
        assert 'error' in context_usage


class TestNextStepsPrediction:
    """Test next steps prediction."""

    def test_predict_next_steps_task_success(self, reporter):
        """Test prediction for successful task execution."""
        next_steps = reporter._predict_next_steps(  # pylint: disable=protected-access
            reporter.OPERATION_TASK_EXECUTION,
            reporter.STATUS_SUCCESS,
            None
        )

        assert any('complete' in step.lower() for step in next_steps)
        assert any('next task' in step.lower() for step in next_steps)

    def test_predict_next_steps_nl_success(self, reporter):
        """Test prediction for successful NL command."""
        next_steps = reporter._predict_next_steps(  # pylint: disable=protected-access
            reporter.OPERATION_NL_COMMAND,
            reporter.STATUS_SUCCESS,
            None
        )

        assert any('return result' in step.lower() for step in next_steps)

    def test_predict_next_steps_handoff_success(self, reporter):
        """Test prediction for successful self-handoff."""
        next_steps = reporter._predict_next_steps(  # pylint: disable=protected-access
            reporter.OPERATION_SELF_HANDOFF,
            reporter.STATUS_SUCCESS,
            None
        )

        assert any('resume' in step.lower() for step in next_steps)

    def test_predict_next_steps_failure(self, reporter):
        """Test prediction for failure status."""
        next_steps = reporter._predict_next_steps(  # pylint: disable=protected-access
            reporter.OPERATION_TASK_EXECUTION,
            reporter.STATUS_FAILURE,
            None
        )

        assert any('analyze' in step.lower() for step in next_steps)
        assert any('retry' in step.lower() for step in next_steps)

    def test_predict_next_steps_failure_with_tests(self, reporter):
        """Test prediction for failure with failing tests."""
        result = {
            'test_info': {
                'passed': 5,
                'failed': 3
            }
        }

        next_steps = reporter._predict_next_steps(  # pylint: disable=protected-access
            reporter.OPERATION_TASK_EXECUTION,
            reporter.STATUS_FAILURE,
            result
        )

        assert any('fix' in step.lower() and 'test' in step.lower() for step in next_steps)

    def test_predict_next_steps_blocked(self, reporter):
        """Test prediction for blocked status."""
        next_steps = reporter._predict_next_steps(  # pylint: disable=protected-access
            reporter.OPERATION_TASK_EXECUTION,
            reporter.STATUS_BLOCKED,
            None
        )

        assert any('human' in step.lower() for step in next_steps)


class TestProgressLogging:
    """Test progress logging."""

    def test_log_progress_to_production_logger(self, reporter, mock_production_logger):
        """Test logging to ProductionLogger."""
        report = ProgressReport(
            timestamp=datetime.now(UTC),
            session_id='sess_123',
            operation='task_execution',
            status='success',
            test_status={'tests_run': True},
            context_usage={'percentage': 50.0},
            next_steps=['Next step'],
            metadata={'task_id': 123}
        )

        reporter.log_progress(report)

        # Should call production logger
        mock_production_logger._log_event.assert_called_once()

        # Verify call args
        call_args = mock_production_logger._log_event.call_args
        assert call_args[1]['event_type'] == 'progress_report'
        assert call_args[1]['session_id'] == 'sess_123'

    def test_log_progress_disabled(self, reporter, mock_production_logger):
        """Test logging when disabled."""
        reporter.enabled = False

        report = ProgressReport(
            timestamp=datetime.now(UTC),
            session_id='sess_123',
            operation='task_execution',
            status='success'
        )

        reporter.log_progress(report)

        # Should not log
        mock_production_logger._log_event.assert_not_called()

    def test_log_progress_without_production_logger(self, mock_config):
        """Test logging without production logger (fallback to standard logging)."""
        reporter = ProgressReporter(mock_config, production_logger=None)

        report = ProgressReport(
            timestamp=datetime.now(UTC),
            session_id='sess_123',
            operation='task_execution',
            status='success'
        )

        # Should not raise error
        reporter.log_progress(report)


class TestProgressReportSerialization:
    """Test ProgressReport serialization."""

    def test_to_dict_complete(self, reporter):
        """Test complete serialization."""
        report = reporter.generate_progress_report(
            session_id='sess_123',
            operation=reporter.OPERATION_TASK_EXECUTION,
            status=reporter.STATUS_SUCCESS,
            execution_time_ms=1500
        )

        data = report.to_dict()

        assert data['session_id'] == 'sess_123'
        assert data['operation'] == reporter.OPERATION_TASK_EXECUTION
        assert data['status'] == reporter.STATUS_SUCCESS
        assert 'timestamp' in data
        assert 'test_status' in data
        assert 'context_usage' in data
        assert 'next_steps' in data
        assert 'metadata' in data

    def test_to_dict_timestamp_format(self, reporter):
        """Test timestamp is ISO format."""
        report = reporter.generate_progress_report(
            session_id='sess_123',
            operation=reporter.OPERATION_TASK_EXECUTION
        )

        data = report.to_dict()

        # Should be ISO format string
        timestamp_str = data['timestamp']
        assert isinstance(timestamp_str, str)
        assert 'T' in timestamp_str  # ISO format has T separator


class TestIntegration:
    """Test integration scenarios."""

    def test_full_workflow_task_execution(self, reporter, mock_task,
                                          mock_context_manager, mock_production_logger):
        """Test complete workflow for task execution."""
        result = {
            'success': True,
            'duration_ms': 2000,
            'test_info': {
                'passed': 12,
                'failed': 0,
                'coverage': 95.0
            },
            'quality_score': 0.90,
            'confidence_score': 0.85
        }

        # Generate report
        report = reporter.generate_progress_report(
            session_id='sess_456',
            operation=reporter.OPERATION_TASK_EXECUTION,
            status=reporter.STATUS_SUCCESS,
            task=mock_task,
            result=result,
            context_mgr=mock_context_manager
        )

        # Log report
        reporter.log_progress(report)

        # Verify complete report
        assert report.session_id == 'sess_456'
        assert report.operation == reporter.OPERATION_TASK_EXECUTION
        assert report.status == reporter.STATUS_SUCCESS
        assert report.test_status['tests_passed'] == 12
        assert report.context_usage['percentage'] == 45.5
        assert len(report.next_steps) > 0
        assert report.metadata['task_id'] == 123

        # Verify logged
        mock_production_logger._log_event.assert_called_once()

    def test_full_workflow_nl_command(self, reporter, mock_production_logger):
        """Test complete workflow for NL command."""
        report = reporter.generate_progress_report(
            session_id='sess_789',
            operation=reporter.OPERATION_NL_COMMAND,
            status=reporter.STATUS_SUCCESS,
            command='list tasks',
            result_count=5
        )

        reporter.log_progress(report)

        # Verify report
        assert report.operation == reporter.OPERATION_NL_COMMAND
        assert report.metadata['command'] == 'list tasks'
        assert report.metadata['result_count'] == 5

        # Verify logged
        mock_production_logger._log_event.assert_called_once()

    def test_full_workflow_self_handoff(self, reporter, mock_context_manager,
                                       mock_production_logger):
        """Test complete workflow for self-handoff."""
        report = reporter.generate_progress_report(
            session_id='sess_100',
            operation=reporter.OPERATION_SELF_HANDOFF,
            status=reporter.STATUS_SUCCESS,
            context_mgr=mock_context_manager,
            checkpoint_id='ckpt_001',
            handoff_count=1
        )

        reporter.log_progress(report)

        # Verify report
        assert report.operation == reporter.OPERATION_SELF_HANDOFF
        assert report.context_usage['percentage'] == 45.5
        assert report.metadata['checkpoint_id'] == 'ckpt_001'
        assert report.metadata['handoff_count'] == 1

        # Verify logged
        mock_production_logger._log_event.assert_called_once()
