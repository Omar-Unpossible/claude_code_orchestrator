"""End-to-end integration tests for ADR-019 Session Continuity (Phase 1-3).

Tests complete workflows combining all Phase 1-3 components:
- Phase 1: OrchestratorSessionManager, CheckpointVerifier
- Phase 2: DecisionRecordGenerator, ProgressReporter
- Phase 3: SessionMetricsCollector

Follows TEST_GUIDELINES.md constraints (max 0.5s sleep, 5 threads, 20KB).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, call, patch
from datetime import datetime, UTC

from src.orchestration.session import (
    DecisionRecordGenerator,
    ProgressReporter,
    SessionMetricsCollector
)
from src.orchestration.decision_engine import DecisionEngine, Action
from src.core.config import Config
from src.core.state import StateManager
from src.orchestration.breakpoint_manager import BreakpointManager


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)

    config_data = {
        'orchestrator': {
            'session_continuity': {
                'decision_logging': {
                    'enabled': True,
                    'significance_threshold': 0.7,
                    'output_dir': '/tmp/test_decisions'
                },
                'progress_reporting': {
                    'enabled': True,
                    'destination': 'production_log'
                },
                'metrics': {
                    'enabled': True,
                    'track_context_zones': True,
                    'track_confidence_trends': True,
                    'summary_on_handoff': True
                }
            }
        },
        'orchestration': {
            'decision': {}
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
def mock_state_manager():
    """Create mock StateManager."""
    state_mgr = Mock(spec=StateManager)
    return state_mgr


@pytest.fixture
def mock_breakpoint_manager():
    """Create mock BreakpointManager."""
    bp_mgr = Mock(spec=BreakpointManager)
    bp_mgr.evaluate_breakpoint_conditions = Mock(return_value=[])
    return bp_mgr


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
    context_mgr.get_usage_percentage = Mock(return_value=0.65)
    context_mgr.get_zone = Mock(return_value='yellow')
    context_mgr.get_total_tokens = Mock(return_value=15000)
    return context_mgr


@pytest.fixture
def decision_engine_with_dr(mock_config, mock_state_manager, mock_breakpoint_manager, tmp_path):
    """Create DecisionEngine with DecisionRecordGenerator."""
    # Override output directory to use tmp_path
    mock_config._config['orchestrator']['session_continuity']['decision_logging']['output_dir'] = str(tmp_path / 'decisions')

    dr_gen = DecisionRecordGenerator(mock_config, mock_state_manager)

    engine = DecisionEngine(
        mock_state_manager,
        mock_breakpoint_manager,
        config=mock_config.get('orchestration.decision', {}),
        decision_record_generator=dr_gen
    )

    return engine, dr_gen, tmp_path


class TestCompleteWorkflow:
    """Test complete workflow with all Phase 1-3 components."""

    def test_decision_with_dr_generation_and_progress_reporting(
        self,
        decision_engine_with_dr,
        mock_production_logger,
        mock_task,
        mock_context_manager,
        mock_config
    ):
        """Test decision triggers DR generation and progress reporting."""
        engine, dr_gen, tmp_path = decision_engine_with_dr

        # Create ProgressReporter and SessionMetricsCollector
        progress_reporter = ProgressReporter(mock_config, mock_production_logger)
        metrics_collector = SessionMetricsCollector(mock_config)

        # Make a high-confidence decision (should generate DR)
        context = {
            'task': mock_task,
            'response': 'implementation complete',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.85,
            'confidence_score': 0.90
        }

        action = engine.decide_next_action(context)

        # Verify decision was made
        assert action.type == 'proceed'
        assert action.confidence == 0.85

        # Verify DR was generated
        dr_files = list((tmp_path / 'decisions').glob('DR-*.md'))
        assert len(dr_files) == 1
        dr_content = dr_files[0].read_text()
        assert 'Orchestrator Decision Record' in dr_content
        assert 'Confidence**: 0.85' in dr_content

        # Generate and log progress report
        report = progress_reporter.generate_progress_report(
            session_id='sess_123',
            operation='task_execution',
            status='success',
            task=mock_task,
            result={'success': True},
            context_mgr=mock_context_manager
        )
        progress_reporter.log_progress(report)

        # Verify progress was logged
        assert mock_production_logger._log_event.called
        call_args = mock_production_logger._log_event.call_args
        assert call_args[1]['event_type'] == 'progress_report'

        # Record metrics
        metrics_collector.record_operation(
            'task_execution',
            context_mgr=mock_context_manager,
            decision=action
        )

        # Verify metrics collected
        metrics = metrics_collector.get_session_metrics()
        assert metrics['total_operations'] == 1
        assert metrics['avg_confidence'] == 0.85

    def test_multiple_operations_with_metrics_aggregation(
        self,
        mock_config,
        mock_context_manager
    ):
        """Test metrics aggregation across multiple operations."""
        metrics_collector = SessionMetricsCollector(mock_config)

        # Simulate multiple operations with varying context and confidence
        operations = [
            ('task_execution', 0.40, 0.75),  # Green zone, medium confidence
            ('nl_command', 0.70, 0.85),      # Yellow zone, high confidence
            ('task_execution', 0.90, 0.45),  # Red zone, low confidence
            ('decision', 0.50, 0.92),        # Green zone, high confidence
        ]

        for op_type, context_usage, confidence in operations:
            context_mgr = Mock()
            context_mgr.get_usage_percentage = Mock(return_value=context_usage)
            decision = Mock()
            decision.confidence = confidence

            metrics_collector.record_operation(
                op_type,
                context_mgr=context_mgr,
                decision=decision
            )

        # Verify aggregated metrics
        metrics = metrics_collector.get_session_metrics()

        assert metrics['total_operations'] == 4
        assert metrics['operations_by_type']['task_execution'] == 2
        assert metrics['operations_by_type']['nl_command'] == 1
        assert metrics['operations_by_type']['decision'] == 1

        # Zone distribution: 2 green, 1 yellow, 1 red
        assert metrics['context_zones_distribution']['green'] == 2
        assert metrics['context_zones_distribution']['yellow'] == 1
        assert metrics['context_zones_distribution']['red'] == 1

        # Confidence: avg should be ~0.74, low count should be 1 (0.45)
        assert 0.73 <= metrics['avg_confidence'] <= 0.75
        assert metrics['low_confidence_count'] == 1


class TestDecisionRecordGeneration:
    """Test decision record generation and persistence."""

    def test_decision_record_saved_to_file(
        self,
        decision_engine_with_dr,
        mock_task
    ):
        """Test decision record is saved to file with correct format."""
        engine, dr_gen, tmp_path = decision_engine_with_dr

        context = {
            'task': mock_task,
            'response': 'implementation',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.90,
            'confidence_score': 0.95
        }

        action = engine.decide_next_action(context)

        # Verify file was created
        dr_files = list((tmp_path / 'decisions').glob('DR-*.md'))
        assert len(dr_files) == 1

        # Verify file contents
        dr_content = dr_files[0].read_text()
        assert '# DR-' in dr_content
        assert 'Orchestrator Decision Record' in dr_content
        assert '## Context' in dr_content
        assert '## Decision' in dr_content
        assert '## Consequences' in dr_content
        assert 'Implement feature X' in dr_content  # Task title
        assert 'Action: proceed' in dr_content

    def test_low_confidence_no_dr_generated(
        self,
        decision_engine_with_dr,
        mock_task
    ):
        """Test low confidence decisions don't generate DR."""
        engine, dr_gen, tmp_path = decision_engine_with_dr

        context = {
            'task': mock_task,
            'response': 'partial implementation',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.55,  # Below threshold
            'confidence_score': 0.60
        }

        action = engine.decide_next_action(context)

        # Should still make decision but not generate DR
        assert action.type in ['proceed', 'clarify']

        # No DR files should be created
        dr_files = list((tmp_path / 'decisions').glob('DR-*.md'))
        assert len(dr_files) == 0


class TestProgressReporting:
    """Test progress reporting integration."""

    def test_progress_report_logged_to_production_logger(
        self,
        mock_config,
        mock_production_logger,
        mock_task,
        mock_context_manager
    ):
        """Test progress report is logged to ProductionLogger."""
        reporter = ProgressReporter(mock_config, mock_production_logger)

        report = reporter.generate_progress_report(
            session_id='sess_456',
            operation='nl_command',
            status='success',
            task=mock_task,
            result={'success': True, 'duration_ms': 1500},
            context_mgr=mock_context_manager
        )

        reporter.log_progress(report)

        # Verify log was called
        assert mock_production_logger._log_event.called
        call_args = mock_production_logger._log_event.call_args

        # Verify log contents
        assert call_args[1]['event_type'] == 'progress_report'
        assert call_args[1]['operation'] == 'nl_command'
        assert call_args[1]['status'] == 'success'

    def test_progress_report_includes_context_usage(
        self,
        mock_config,
        mock_production_logger,
        mock_context_manager
    ):
        """Test progress report includes context usage details."""
        reporter = ProgressReporter(mock_config, mock_production_logger)

        report = reporter.generate_progress_report(
            session_id='sess_789',
            operation='task_execution',
            status='success',
            context_mgr=mock_context_manager
        )

        # Verify context usage in report
        report_dict = report.to_dict()
        assert report_dict['context_usage']['available'] is True
        assert report_dict['context_usage']['percentage'] == 0.65
        assert report_dict['context_usage']['zone'] == 'yellow'
        assert report_dict['context_usage']['tokens_used'] == 15000


class TestSessionMetrics:
    """Test session metrics collection."""

    def test_session_summary_generated(
        self,
        mock_config,
        mock_context_manager
    ):
        """Test session summary generation includes all metrics."""
        collector = SessionMetricsCollector(mock_config)

        # Simulate some operations
        for i in range(5):
            decision = Mock()
            decision.confidence = 0.80 + (i * 0.02)
            collector.record_operation('task_execution', mock_context_manager, decision)

        # Record handoff
        collector.record_handoff('checkpoint_123', 0.87)

        # Generate summary
        summary = collector.generate_session_summary()

        # Verify summary contents
        assert '# Session Metrics Summary' in summary
        assert 'Total**: 5' in summary
        assert 'Handoffs**: 1' in summary
        assert 'task_execution: 5' in summary
        assert '## Context Usage' in summary
        assert '## Decision Confidence' in summary

    def test_handoff_metrics_tracking(
        self,
        mock_config
    ):
        """Test handoff metrics are tracked correctly."""
        collector = SessionMetricsCollector(mock_config)

        # Record multiple handoffs
        collector.record_handoff('checkpoint_1', 0.70)
        collector.record_handoff('checkpoint_2', 0.85)
        collector.record_handoff('checkpoint_3', 0.92)

        metrics = collector.get_session_metrics()

        assert metrics['handoff_count'] == 3
        assert metrics['peak_context_usage'] == 0.92
        assert metrics['last_checkpoint_id'] == 'checkpoint_3'


class TestGracefulDegradation:
    """Test graceful degradation when components disabled."""

    def test_decision_engine_without_dr_generator(
        self,
        mock_config,
        mock_state_manager,
        mock_breakpoint_manager,
        mock_task
    ):
        """Test DecisionEngine works without DecisionRecordGenerator."""
        engine = DecisionEngine(
            mock_state_manager,
            mock_breakpoint_manager,
            config=mock_config.get('orchestration.decision', {}),
            decision_record_generator=None  # No DR generator
        )

        context = {
            'task': mock_task,
            'response': 'implementation',
            'validation_result': {'complete': True, 'valid': True},
            'quality_score': 0.85,
            'confidence_score': 0.90
        }

        # Should still make decision
        action = engine.decide_next_action(context)
        assert action.type == 'proceed'

    def test_metrics_collector_disabled(
        self,
        mock_config,
        mock_context_manager
    ):
        """Test SessionMetricsCollector when disabled."""
        mock_config._config['orchestrator']['session_continuity']['metrics']['enabled'] = False

        collector = SessionMetricsCollector(mock_config)

        # Record operation - should be no-op
        collector.record_operation('task_execution', mock_context_manager)

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 0

    def test_progress_reporter_disabled(
        self,
        mock_config,
        mock_production_logger,
        mock_task
    ):
        """Test ProgressReporter when disabled."""
        mock_config._config['orchestrator']['session_continuity']['progress_reporting']['enabled'] = False

        reporter = ProgressReporter(mock_config, mock_production_logger)

        report = reporter.generate_progress_report(
            session_id='sess_999',
            operation='task_execution',
            task=mock_task
        )

        # Log should be no-op
        reporter.log_progress(report)
        assert not mock_production_logger._log_event.called


class TestErrorHandling:
    """Test error handling doesn't break orchestration."""

    def test_dr_generation_error_does_not_break_decision(
        self,
        mock_config,
        mock_state_manager,
        mock_breakpoint_manager,
        mock_task,
        tmp_path
    ):
        """Test DR generation error doesn't prevent decision."""
        # Create DR generator that will fail
        dr_gen = DecisionRecordGenerator(mock_config, mock_state_manager)

        engine = DecisionEngine(
            mock_state_manager,
            mock_breakpoint_manager,
            config=mock_config.get('orchestration.decision', {}),
            decision_record_generator=dr_gen
        )

        # Mock save_decision_record to raise exception
        with patch.object(dr_gen, 'save_decision_record', side_effect=Exception("Disk full")):
            context = {
                'task': mock_task,
                'response': 'implementation',
                'validation_result': {'complete': True, 'valid': True},
                'quality_score': 0.85,
                'confidence_score': 0.90
            }

            # Decision should still succeed
            action = engine.decide_next_action(context)
            assert action.type == 'proceed'

    def test_metrics_collection_error_does_not_break_operation(
        self,
        mock_config
    ):
        """Test metrics collection error doesn't break operation recording."""
        collector = SessionMetricsCollector(mock_config)

        # Create bad context manager
        bad_context_mgr = Mock()
        bad_context_mgr.get_usage_percentage = Mock(side_effect=Exception("Context error"))

        # Should not raise exception
        collector.record_operation('task_execution', bad_context_mgr)

        # Should still record operation count
        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 1
