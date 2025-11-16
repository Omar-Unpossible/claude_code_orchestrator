"""Unit tests for SessionMetricsCollector.

Tests session metrics tracking, context zone distribution, and confidence trends.
Follows TEST_GUIDELINES.md constraints (max 0.5s sleep, 5 threads, 20KB).
"""

import pytest
from datetime import datetime, UTC
from threading import Thread
from unittest.mock import Mock

from src.orchestration.session.session_metrics_collector import SessionMetricsCollector
from src.core.config import Config
from src.core.exceptions import OrchestratorException


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)

    config_data = {
        'orchestrator': {
            'session_continuity': {
                'metrics': {
                    'enabled': True,
                    'track_context_zones': True,
                    'track_confidence_trends': True,
                    'summary_on_handoff': True
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
def mock_context_manager():
    """Create mock OrchestratorContextManager."""
    context_mgr = Mock()
    context_mgr.get_usage_percentage = Mock(return_value=0.45)  # 45% - green zone
    return context_mgr


@pytest.fixture
def mock_decision():
    """Create mock decision action."""
    decision = Mock()
    decision.confidence = 0.85
    return decision


@pytest.fixture
def collector(mock_config):
    """Create SessionMetricsCollector instance."""
    return SessionMetricsCollector(mock_config)


class TestInitialization:
    """Test SessionMetricsCollector initialization."""

    def test_initialization_success(self, mock_config):
        """Test successful initialization."""
        collector = SessionMetricsCollector(mock_config)

        assert collector.config == mock_config
        assert collector.enabled is True
        assert collector.track_context_zones is True
        assert collector.track_confidence_trends is True
        assert isinstance(collector.session_start, datetime)

    def test_initialization_creates_empty_metrics(self, collector):
        """Test initialization creates empty metrics."""
        metrics = collector.get_session_metrics()

        assert metrics['handoff_count'] == 0
        assert metrics['total_operations'] == 0
        assert metrics['avg_context_usage'] == 0.0
        assert metrics['peak_context_usage'] == 0.0
        assert metrics['avg_confidence'] == 0.0
        assert metrics['low_confidence_count'] == 0

    def test_initialization_disabled(self, mock_config):
        """Test initialization with metrics disabled."""
        mock_config._config['orchestrator']['session_continuity']['metrics']['enabled'] = False

        collector = SessionMetricsCollector(mock_config)

        assert collector.enabled is False


class TestRecordOperation:
    """Test operation recording."""

    def test_record_operation_increments_total(self, collector):
        """Test recording operation increments total count."""
        collector.record_operation('task_execution')

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 1

    def test_record_operation_tracks_by_type(self, collector):
        """Test operation recording tracks by type."""
        collector.record_operation('task_execution')
        collector.record_operation('task_execution')
        collector.record_operation('nl_command')

        metrics = collector.get_session_metrics()
        assert metrics['operations_by_type']['task_execution'] == 2
        assert metrics['operations_by_type']['nl_command'] == 1

    def test_record_operation_with_context_manager(self, collector, mock_context_manager):
        """Test recording operation with context manager."""
        collector.record_operation('task_execution', context_mgr=mock_context_manager)

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 1
        assert metrics['context_zones_distribution']['green'] == 1

    def test_record_operation_with_decision(self, collector, mock_decision):
        """Test recording operation with decision."""
        collector.record_operation('decision', decision=mock_decision)

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 1
        assert metrics['avg_confidence'] == 0.85

    def test_record_operation_disabled(self, mock_config):
        """Test record operation when disabled."""
        mock_config._config['orchestrator']['session_continuity']['metrics']['enabled'] = False
        collector = SessionMetricsCollector(mock_config)

        collector.record_operation('task_execution')

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 0

    def test_record_operation_with_exception_from_context_mgr(self, collector):
        """Test record operation handles context manager exceptions."""
        bad_context_mgr = Mock()
        bad_context_mgr.get_usage_percentage = Mock(side_effect=Exception("Context error"))

        # Should not raise, just log warning
        collector.record_operation('task_execution', context_mgr=bad_context_mgr)

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 1


class TestRecordHandoff:
    """Test handoff recording."""

    def test_record_handoff_increments_count(self, collector):
        """Test recording handoff increments count."""
        collector.record_handoff('checkpoint_123', 0.87)

        metrics = collector.get_session_metrics()
        assert metrics['handoff_count'] == 1

    def test_record_handoff_tracks_checkpoint_id(self, collector):
        """Test handoff tracks checkpoint ID."""
        collector.record_handoff('checkpoint_123', 0.87)

        metrics = collector.get_session_metrics()
        assert metrics['last_checkpoint_id'] == 'checkpoint_123'

    def test_record_handoff_tracks_timestamp(self, collector):
        """Test handoff tracks timestamp."""
        collector.record_handoff('checkpoint_123', 0.87)

        metrics = collector.get_session_metrics()
        assert metrics['last_handoff_timestamp'] is not None

    def test_record_handoff_updates_peak_usage(self, collector):
        """Test handoff updates peak context usage."""
        collector.record_handoff('checkpoint_1', 0.70)
        collector.record_handoff('checkpoint_2', 0.87)
        collector.record_handoff('checkpoint_3', 0.75)

        metrics = collector.get_session_metrics()
        assert metrics['peak_context_usage'] == 0.87

    def test_record_handoff_disabled(self, mock_config):
        """Test record handoff when disabled."""
        mock_config._config['orchestrator']['session_continuity']['metrics']['enabled'] = False
        collector = SessionMetricsCollector(mock_config)

        collector.record_handoff('checkpoint_123', 0.87)

        metrics = collector.get_session_metrics()
        assert metrics['handoff_count'] == 0


class TestContextZoneTracking:
    """Test context zone distribution tracking."""

    def test_green_zone_tracking(self, collector):
        """Test tracking green zone (0-60%)."""
        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.45)

        collector.record_operation('task_execution', context_mgr=context_mgr)

        metrics = collector.get_session_metrics()
        assert metrics['context_zones_distribution']['green'] == 1
        assert metrics['context_zones_distribution']['yellow'] == 0
        assert metrics['context_zones_distribution']['red'] == 0

    def test_yellow_zone_tracking(self, collector):
        """Test tracking yellow zone (60-85%)."""
        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.72)

        collector.record_operation('task_execution', context_mgr=context_mgr)

        metrics = collector.get_session_metrics()
        assert metrics['context_zones_distribution']['green'] == 0
        assert metrics['context_zones_distribution']['yellow'] == 1
        assert metrics['context_zones_distribution']['red'] == 0

    def test_red_zone_tracking(self, collector):
        """Test tracking red zone (85-100%)."""
        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.92)

        collector.record_operation('task_execution', context_mgr=context_mgr)

        metrics = collector.get_session_metrics()
        assert metrics['context_zones_distribution']['green'] == 0
        assert metrics['context_zones_distribution']['yellow'] == 0
        assert metrics['context_zones_distribution']['red'] == 1

    def test_zone_boundary_60_percent(self, collector):
        """Test zone boundary at exactly 60%."""
        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.60)

        collector.record_operation('task_execution', context_mgr=context_mgr)

        metrics = collector.get_session_metrics()
        assert metrics['context_zones_distribution']['yellow'] == 1

    def test_zone_boundary_85_percent(self, collector):
        """Test zone boundary at exactly 85%."""
        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.85)

        collector.record_operation('task_execution', context_mgr=context_mgr)

        metrics = collector.get_session_metrics()
        assert metrics['context_zones_distribution']['red'] == 1

    def test_multiple_zones_distribution(self, collector):
        """Test tracking distribution across multiple zones."""
        # 2 green, 3 yellow, 1 red
        for usage in [0.30, 0.50, 0.65, 0.70, 0.75, 0.90]:
            context_mgr = Mock()
            context_mgr.get_usage_percentage = Mock(return_value=usage)
            collector.record_operation('task_execution', context_mgr=context_mgr)

        metrics = collector.get_session_metrics()
        assert metrics['context_zones_distribution']['green'] == 2
        assert metrics['context_zones_distribution']['yellow'] == 3
        assert metrics['context_zones_distribution']['red'] == 1

    def test_zone_tracking_disabled(self, mock_config):
        """Test zone tracking when disabled."""
        mock_config._config['orchestrator']['session_continuity']['metrics']['track_context_zones'] = False
        collector = SessionMetricsCollector(mock_config)

        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.45)
        collector.record_operation('task_execution', context_mgr=context_mgr)

        # Zone distribution should still be initialized but not updated
        metrics = collector.get_session_metrics()
        assert 'context_zones_distribution' in metrics


class TestConfidenceTrending:
    """Test confidence trend tracking."""

    def test_confidence_averaging(self, collector):
        """Test averaging of confidence scores."""
        for confidence in [0.80, 0.90, 0.70]:
            decision = Mock()
            decision.confidence = confidence
            collector.record_operation('decision', decision=decision)

        metrics = collector.get_session_metrics()
        assert metrics['avg_confidence'] == pytest.approx(0.8, abs=0.01)

    def test_low_confidence_tracking(self, collector):
        """Test tracking of low confidence decisions."""
        confidences = [0.50, 0.85, 0.45, 0.90, 0.55]
        for confidence in confidences:
            decision = Mock()
            decision.confidence = confidence
            collector.record_operation('decision', decision=decision)

        metrics = collector.get_session_metrics()
        assert metrics['low_confidence_count'] == 3  # 0.50, 0.45, 0.55

    def test_high_confidence_not_counted_as_low(self, collector):
        """Test high confidence decisions not counted as low."""
        decision = Mock()
        decision.confidence = 0.95
        collector.record_operation('decision', decision=decision)

        metrics = collector.get_session_metrics()
        assert metrics['low_confidence_count'] == 0

    def test_confidence_boundary_at_60_percent(self, collector):
        """Test confidence boundary at exactly 0.6."""
        # Exactly 0.6 should not be counted as low
        decision = Mock()
        decision.confidence = 0.6
        collector.record_operation('decision', decision=decision)

        metrics = collector.get_session_metrics()
        assert metrics['low_confidence_count'] == 0

    def test_confidence_tracking_disabled(self, mock_config):
        """Test confidence tracking when disabled."""
        mock_config._config['orchestrator']['session_continuity']['metrics']['track_confidence_trends'] = False
        collector = SessionMetricsCollector(mock_config)

        decision = Mock()
        decision.confidence = 0.45
        collector.record_operation('decision', decision=decision)

        metrics = collector.get_session_metrics()
        # Should still have field but not updated
        assert metrics['avg_confidence'] == 0.0


class TestSessionSummary:
    """Test session summary generation."""

    def test_generate_summary_format(self, collector):
        """Test summary generates markdown format."""
        summary = collector.generate_session_summary()

        assert '# Session Metrics Summary' in summary
        assert '## Operations' in summary
        assert '## Context Usage' in summary

    def test_generate_summary_includes_operations(self, collector):
        """Test summary includes operation counts."""
        collector.record_operation('task_execution')
        collector.record_operation('nl_command')

        summary = collector.generate_session_summary()

        assert 'Total**: 2' in summary
        assert 'task_execution: 1' in summary
        assert 'nl_command: 1' in summary

    def test_generate_summary_includes_context_usage(self, collector):
        """Test summary includes context usage."""
        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.65)
        collector.record_operation('task_execution', context_mgr=context_mgr)

        summary = collector.generate_session_summary()

        assert '## Context Usage' in summary
        assert 'Average' in summary
        assert 'Peak' in summary

    def test_generate_summary_includes_zone_distribution(self, collector):
        """Test summary includes zone distribution."""
        for usage in [0.40, 0.70, 0.90]:
            context_mgr = Mock()
            context_mgr.get_usage_percentage = Mock(return_value=usage)
            collector.record_operation('task_execution', context_mgr=context_mgr)

        summary = collector.generate_session_summary()

        assert 'Zone Distribution' in summary
        assert 'Green (0-60%)' in summary
        assert 'Yellow (60-85%)' in summary
        assert 'Red (85-100%)' in summary

    def test_generate_summary_includes_confidence(self, collector):
        """Test summary includes confidence metrics."""
        decision = Mock()
        decision.confidence = 0.75
        collector.record_operation('decision', decision=decision)

        summary = collector.generate_session_summary()

        assert '## Decision Confidence' in summary
        assert 'Average' in summary
        assert 'Low Confidence Count' in summary


class TestResetSession:
    """Test session reset functionality."""

    def test_reset_clears_operations(self, collector):
        """Test reset clears operation count."""
        collector.record_operation('task_execution')
        collector.reset_session()

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 0

    def test_reset_clears_handoffs(self, collector):
        """Test reset clears handoff count."""
        collector.record_handoff('checkpoint_123', 0.87)
        collector.reset_session()

        metrics = collector.get_session_metrics()
        assert metrics['handoff_count'] == 0

    def test_reset_clears_context_zones(self, collector):
        """Test reset clears zone distribution."""
        context_mgr = Mock()
        context_mgr.get_usage_percentage = Mock(return_value=0.45)
        collector.record_operation('task_execution', context_mgr=context_mgr)
        collector.reset_session()

        metrics = collector.get_session_metrics()
        assert metrics['context_zones_distribution']['green'] == 0

    def test_reset_updates_session_start(self, collector):
        """Test reset updates session start time."""
        old_start = collector.session_start
        collector.reset_session()

        assert collector.session_start > old_start


class TestThreadSafety:
    """Test thread safety of metrics collection."""

    def test_concurrent_operation_recording(self, collector):
        """Test thread-safe concurrent operation recording (max 5 threads)."""
        def record_ops():
            for _ in range(10):
                collector.record_operation('task_execution')

        threads = [Thread(target=record_ops) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        metrics = collector.get_session_metrics()
        assert metrics['total_operations'] == 30

    def test_concurrent_handoff_recording(self, collector):
        """Test thread-safe concurrent handoff recording (max 5 threads)."""
        def record_handoffs():
            for i in range(5):
                collector.record_handoff(f'checkpoint_{i}', 0.80 + i * 0.01)

        threads = [Thread(target=record_handoffs) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        metrics = collector.get_session_metrics()
        assert metrics['handoff_count'] == 15
