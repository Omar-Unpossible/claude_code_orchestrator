"""Tests for BreakpointManager - triggering, resolution, and rule evaluation."""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock

from src.core.exceptions import OrchestratorException
from src.core.state import StateManager
from src.orchestration.breakpoint_manager import BreakpointManager, BreakpointEvent


@pytest.fixture
def state_manager(tmp_path):
    """Create StateManager with temporary database."""
    StateManager.reset_instance()
    db_path = tmp_path / "test.db"
    sm = StateManager.get_instance(f"sqlite:///{db_path}")
    yield sm
    sm.close()
    try:
        db_path.unlink()
    except:
        pass


@pytest.fixture
def manager(state_manager):
    """Create BreakpointManager instance."""
    return BreakpointManager(state_manager)


@pytest.fixture
def custom_config():
    """Create custom configuration for testing."""
    return {
        'breakpoint_rules': {
            'test_breakpoint': {
                'enabled': True,
                'priority': 'high',
                'auto_resolve': False,
                'conditions': ['test_value > 50'],
                'notification': 'immediate',
                'description': 'Test breakpoint'
            }
        }
    }


class TestBreakpointEvent:
    """Test BreakpointEvent data class."""

    def test_event_creation(self):
        """Test creating breakpoint event."""
        event = BreakpointEvent(
            id=1,
            breakpoint_type='test',
            priority='high',
            context={'task_id': 123},
            triggered_at=datetime.now(UTC)
        )

        assert event.id == 1
        assert event.breakpoint_type == 'test'
        assert event.priority == 'high'
        assert event.is_pending()
        assert not event.auto_resolved

    def test_event_to_dict(self):
        """Test serializing event to dictionary."""
        now = datetime.now(UTC)
        event = BreakpointEvent(
            id=1,
            breakpoint_type='test',
            priority='high',
            context={'task_id': 123},
            triggered_at=now
        )

        result = event.to_dict()
        assert result['id'] == 1
        assert result['breakpoint_type'] == 'test'
        assert result['priority'] == 'high'
        assert result['context'] == {'task_id': 123}
        assert result['triggered_at'] == now.isoformat()
        assert result['resolved_at'] is None
        assert result['auto_resolved'] is False


class TestBreakpointInitialization:
    """Test BreakpointManager initialization."""

    def test_default_initialization(self, state_manager):
        """Test manager initializes with default rules."""
        manager = BreakpointManager(state_manager)

        assert manager.state_manager is state_manager
        assert 'confidence_too_low' in manager._rules
        assert 'breaking_test_failure' in manager._rules
        assert 'rate_limit_hit' in manager._rules

    def test_custom_config_initialization(self, state_manager, custom_config):
        """Test manager initializes with custom configuration."""
        manager = BreakpointManager(state_manager, custom_config)

        assert 'test_breakpoint' in manager._rules
        assert manager._rules['test_breakpoint']['priority'] == 'high'


class TestConditionEvaluation:
    """Test breakpoint condition evaluation."""

    def test_evaluate_simple_condition(self, manager):
        """Test evaluating simple condition."""
        context = {'confidence_score': 0.2, 'critical_task': True}
        triggered = manager.evaluate_breakpoint_conditions(context)

        # Should trigger confidence_too_low (score < 0.3 and critical)
        assert 'confidence_too_low' in triggered

    def test_evaluate_multiple_conditions(self, manager):
        """Test evaluating multiple conditions."""
        context = {
            'test_failed': True,
            'previously_passing': True,
            'affects_critical_functionality': True
        }
        triggered = manager.evaluate_breakpoint_conditions(context)

        # Should trigger breaking_test_failure
        assert 'breaking_test_failure' in triggered

    def test_no_conditions_met(self, manager):
        """Test when no conditions are met."""
        context = {'confidence_score': 0.95, 'critical_task': True}
        triggered = manager.evaluate_breakpoint_conditions(context)

        # Confidence is high, shouldn't trigger
        assert 'confidence_too_low' not in triggered

    def test_disabled_breakpoint_not_triggered(self, manager):
        """Test disabled breakpoints are not triggered."""
        manager.disable_breakpoint_type('confidence_too_low')

        context = {'confidence_score': 0.2, 'critical_task': True}
        triggered = manager.evaluate_breakpoint_conditions(context)

        assert 'confidence_too_low' not in triggered

    def test_condition_evaluation_error_handling(self, manager):
        """Test handling of condition evaluation errors."""
        # Add rule with invalid condition
        manager.add_custom_rule({
            'type': 'bad_condition',
            'enabled': True,
            'priority': 'high',
            'conditions': ['invalid python code!!!'],
            'notification': 'immediate'
        })

        context = {}
        triggered = manager.evaluate_breakpoint_conditions(context)

        # Should not trigger due to evaluation error
        assert 'bad_condition' not in triggered


class TestBreakpointTriggering:
    """Test triggering breakpoints."""

    def test_trigger_breakpoint_creates_event(self, manager):
        """Test triggering breakpoint creates event."""
        context = {'task_id': 123, 'confidence_score': 0.25}
        event = manager.trigger_breakpoint('confidence_too_low', context)

        assert event.breakpoint_type == 'confidence_too_low'
        assert event.priority == 'high'
        assert event.context['task_id'] == 123
        assert event.is_pending()

    def test_trigger_unknown_breakpoint(self, manager):
        """Test triggering unknown breakpoint type raises exception."""
        with pytest.raises(OrchestratorException) as exc_info:
            manager.trigger_breakpoint('nonexistent_type', {})

        assert 'unknown breakpoint type' in str(exc_info.value).lower()

    def test_trigger_increments_event_id(self, manager):
        """Test event IDs increment."""
        event1 = manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})
        event2 = manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})

        assert event2.id == event1.id + 1

    def test_trigger_updates_statistics(self, manager):
        """Test triggering updates statistics."""
        manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})
        manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})

        stats = manager._stats['confidence_too_low']
        assert stats['triggered'] == 2


class TestAutoResolution:
    """Test automatic breakpoint resolution."""

    def test_auto_resolve_wait_and_retry(self, manager):
        """Test auto-resolution with wait_and_retry action."""
        context = {'rate_limit_detected': True}
        event = manager.trigger_breakpoint('rate_limit_hit', context)

        # Should auto-resolve
        assert event.auto_resolved is True
        assert event.resolution is not None
        assert event.resolution['action'] == 'wait_and_retry'
        assert 'wait_duration' in event.resolution

    def test_auto_resolve_cancel_and_retry(self, manager):
        """Test auto-resolution with cancel_and_retry action."""
        context = {'task_running_time': 4000, 'timeout_seconds': 3600}
        event = manager.trigger_breakpoint('time_threshold_exceeded', context)

        # Should auto-resolve
        assert event.auto_resolved is True
        assert event.resolution['action'] == 'cancel_and_retry'

    def test_non_auto_resolvable_breakpoint(self, manager):
        """Test non-auto-resolvable breakpoints remain pending."""
        context = {'confidence_score': 0.2, 'critical_task': True}
        event = manager.trigger_breakpoint('confidence_too_low', context)

        # Should NOT auto-resolve
        assert event.auto_resolved is False
        assert event.resolution is None
        assert event.is_pending()


class TestBreakpointResolution:
    """Test manual breakpoint resolution."""

    def test_resolve_breakpoint(self, manager):
        """Test resolving a pending breakpoint."""
        event = manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})

        resolution = {'action': 'proceed', 'notes': 'Manually reviewed'}
        manager.resolve_breakpoint(event.id, resolution)

        assert not event.is_pending()
        assert event.resolution == resolution
        assert event.resolved_at is not None

    def test_resolve_nonexistent_breakpoint(self, manager):
        """Test resolving nonexistent breakpoint raises exception."""
        with pytest.raises(OrchestratorException) as exc_info:
            manager.resolve_breakpoint(99999, {})

        assert 'not found' in str(exc_info.value).lower()

    def test_resolve_already_resolved_breakpoint(self, manager):
        """Test resolving already resolved breakpoint raises exception."""
        event = manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})
        manager.resolve_breakpoint(event.id, {'action': 'proceed'})

        with pytest.raises(OrchestratorException) as exc_info:
            manager.resolve_breakpoint(event.id, {'action': 'retry'})

        assert 'already resolved' in str(exc_info.value).lower()

    def test_resolution_updates_statistics(self, manager):
        """Test resolution updates statistics."""
        event = manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})
        manager.resolve_breakpoint(event.id, {'action': 'proceed'})

        stats = manager._stats['confidence_too_low']
        assert stats['resolved'] == 1
        assert stats['total_resolution_time'] > 0


class TestBreakpointQueries:
    """Test querying breakpoints."""

    def test_get_pending_breakpoints(self, manager, state_manager):
        """Test getting pending breakpoints for a project."""
        project = state_manager.create_project(
            name="test",
            description="test",
            working_dir="/tmp"
        )

        # Create some events
        event1 = manager.trigger_breakpoint('confidence_too_low', {
            'project_id': project.id,
            'critical_task': True
        })
        event2 = manager.trigger_breakpoint('confidence_too_low', {
            'project_id': project.id,
            'critical_task': True
        })

        # Resolve one
        manager.resolve_breakpoint(event1.id, {'action': 'proceed'})

        pending = manager.get_pending_breakpoints(project.id)
        assert len(pending) == 1
        assert pending[0].id == event2.id

    def test_get_breakpoint_history(self, manager, state_manager):
        """Test getting breakpoint history."""
        project = state_manager.create_project(
            name="test",
            description="test",
            working_dir="/tmp"
        )

        # Create multiple events
        for i in range(5):
            manager.trigger_breakpoint('confidence_too_low', {
                'project_id': project.id,
                'critical_task': True
            })

        history = manager.get_breakpoint_history(project.id, limit=3)
        assert len(history) == 3
        # Should be ordered by triggered_at descending
        assert history[0].triggered_at >= history[1].triggered_at

    def test_get_breakpoint_stats(self, manager, state_manager):
        """Test getting breakpoint statistics."""
        project = state_manager.create_project(
            name="test",
            description="test",
            working_dir="/tmp"
        )

        # Create and resolve some events
        event1 = manager.trigger_breakpoint('confidence_too_low', {
            'project_id': project.id,
            'critical_task': True
        })
        event2 = manager.trigger_breakpoint('confidence_too_low', {
            'project_id': project.id,
            'critical_task': True
        })

        manager.resolve_breakpoint(event1.id, {'action': 'proceed'})

        stats = manager.get_breakpoint_stats(project.id)
        assert stats['confidence_too_low']['triggered'] == 2
        assert stats['confidence_too_low']['resolved'] == 1
        assert stats['confidence_too_low']['pending'] == 1
        assert stats['confidence_too_low']['avg_resolution_time'] >= 0


class TestCustomRules:
    """Test custom breakpoint rules."""

    def test_add_custom_rule(self, manager):
        """Test adding custom rule at runtime."""
        rule = {
            'type': 'custom_metric',
            'enabled': True,
            'priority': 'medium',
            'conditions': ['metric_value > 100'],
            'notification': 'batched',
            'description': 'Custom metric threshold'
        }

        manager.add_custom_rule(rule)

        assert 'custom_metric' in manager._rules
        assert manager._rules['custom_metric']['priority'] == 'medium'

    def test_add_rule_without_type(self, manager):
        """Test adding rule without type raises exception."""
        rule = {'enabled': True, 'priority': 'high'}

        with pytest.raises(OrchestratorException) as exc_info:
            manager.add_custom_rule(rule)

        assert 'missing' in str(exc_info.value).lower()

    def test_custom_rule_evaluation(self, manager):
        """Test custom rule is evaluated."""
        rule = {
            'type': 'custom_check',
            'enabled': True,
            'priority': 'high',
            'conditions': ['custom_value == 42'],
            'notification': 'immediate'
        }
        manager.add_custom_rule(rule)

        context = {'custom_value': 42}
        triggered = manager.evaluate_breakpoint_conditions(context)

        assert 'custom_check' in triggered


class TestBreakpointEnableDisable:
    """Test enabling/disabling breakpoint types."""

    def test_disable_breakpoint_type(self, manager):
        """Test disabling breakpoint type."""
        manager.disable_breakpoint_type('confidence_too_low')

        context = {'confidence_score': 0.2, 'critical_task': True}
        triggered = manager.evaluate_breakpoint_conditions(context)

        assert 'confidence_too_low' not in triggered

    def test_enable_breakpoint_type(self, manager):
        """Test re-enabling breakpoint type."""
        manager.disable_breakpoint_type('confidence_too_low')
        manager.enable_breakpoint_type('confidence_too_low')

        context = {'confidence_score': 0.2, 'critical_task': True}
        triggered = manager.evaluate_breakpoint_conditions(context)

        assert 'confidence_too_low' in triggered


class TestNotifications:
    """Test notification system."""

    def test_should_notify_immediate(self, manager):
        """Test immediate notification for high priority."""
        should = manager.should_notify('breaking_test_failure', 'high')
        assert should is True

    def test_should_notify_batched_low_priority(self, manager):
        """Test batched notification for low priority."""
        should = manager.should_notify('milestone_completion', 'low')
        assert should is False

    def test_register_notification_callback(self, manager):
        """Test registering notification callback."""
        callback = Mock()
        manager.register_notification_callback(callback)

        # Trigger high-priority immediate notification
        context = {'test_failed': True, 'previously_passing': True, 'affects_critical_functionality': True}
        manager.trigger_breakpoint('breaking_test_failure', context)

        # Callback should have been called
        assert callback.called


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_breakpoint_triggering(self, manager, state_manager):
        """Test triggering breakpoints concurrently."""
        import threading

        project = state_manager.create_project(
            name="test",
            description="test",
            working_dir="/tmp"
        )

        def trigger_breakpoints():
            for _ in range(3):
                manager.trigger_breakpoint('confidence_too_low', {
                    'project_id': project.id,
                    'critical_task': True
                })

        threads = [
            threading.Thread(target=trigger_breakpoints)
            for _ in range(3)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Should have 9 events total
        history = manager.get_breakpoint_history(project.id, limit=100)
        assert len(history) == 9


class TestPriorityOrdering:
    """Test priority-based breakpoint ordering."""

    def test_high_priority_evaluated_first(self, manager):
        """Test high priority breakpoints evaluated first."""
        # Add custom low-priority rule
        manager.add_custom_rule({
            'type': 'low_priority_check',
            'enabled': True,
            'priority': 'low',
            'conditions': ['value == 1'],
            'notification': 'batched'
        })

        context = {
            'value': 1,
            'confidence_score': 0.2,
            'critical_task': True
        }

        triggered = manager.evaluate_breakpoint_conditions(context)

        # High priority should come before low priority
        high_idx = triggered.index('confidence_too_low')
        low_idx = triggered.index('low_priority_check')
        assert high_idx < low_idx


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_context(self, manager):
        """Test evaluation with empty context."""
        triggered = manager.evaluate_breakpoint_conditions({})
        # Should not crash, may or may not trigger based on conditions
        assert isinstance(triggered, list)

    def test_resolve_with_empty_resolution(self, manager):
        """Test resolving with empty resolution dict."""
        event = manager.trigger_breakpoint('confidence_too_low', {'critical_task': True})
        manager.resolve_breakpoint(event.id, {})

        assert not event.is_pending()
        assert event.resolution == {}

    def test_get_stats_for_nonexistent_project(self, manager):
        """Test getting stats for nonexistent project."""
        stats = manager.get_breakpoint_stats(99999)

        # Should return empty stats
        for breakpoint_type in manager._rules.keys():
            assert stats[breakpoint_type]['triggered'] == 0
