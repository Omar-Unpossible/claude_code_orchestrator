"""Unit tests for documentation configuration validation (Story 1.3).

Tests configuration loading and validation for ADR-015 documentation maintenance.

Part of v1.4.0: Project Infrastructure Maintenance System
"""

import pytest
import tempfile
import os
from pathlib import Path

from src.core.config import Config
from src.core.exceptions import ConfigValidationException


class TestDocumentationConfigLoading:
    """Test documentation configuration loading."""

    def test_config_loads_documentation_section(self):
        """Test that default config includes documentation section."""
        Config.reset()
        config = Config.load(defaults_only=True)

        assert config.get('documentation') is not None
        assert config.get('documentation.enabled') is True
        assert config.get('documentation.auto_maintain') is True

    def test_config_loads_all_documentation_subsections(self):
        """Test that all documentation subsections are present."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Check all major subsections exist
        assert config.get('documentation.triggers') is not None
        assert config.get('documentation.maintenance_targets') is not None
        assert config.get('documentation.freshness_thresholds') is not None
        assert config.get('documentation.archive') is not None
        assert config.get('documentation.task_config') is not None

    def test_config_loads_default_triggers(self):
        """Test that all trigger configurations load correctly."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Epic complete trigger
        assert config.get('documentation.triggers.epic_complete.enabled') is True
        assert config.get('documentation.triggers.epic_complete.scope') == 'lightweight'
        assert config.get('documentation.triggers.epic_complete.auto_create_task') is True

        # Milestone achieved trigger
        assert config.get('documentation.triggers.milestone_achieved.enabled') is True
        assert config.get('documentation.triggers.milestone_achieved.scope') == 'comprehensive'

        # Periodic trigger (Story 2.1)
        assert config.get('documentation.triggers.periodic.enabled') is True
        assert config.get('documentation.triggers.periodic.interval_days') == 7
        assert config.get('documentation.triggers.periodic.scope') == 'lightweight'
        assert config.get('documentation.triggers.periodic.auto_create_task') is True


class TestDocumentationConfigValidation:
    """Test documentation configuration validation."""

    def test_validation_accepts_valid_config(self):
        """Test that valid default configuration passes validation."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type (default 'mock' is not in allowed list)
        config.set('agent.type', 'local')

        # Should not raise
        assert config.validate() is True

    def test_validation_accepts_valid_periodic_interval(self):
        """Test that valid periodic interval is accepted."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        # Set valid interval_days
        config.set('documentation.triggers.periodic.interval_days', 30)

        # Should not raise
        assert config.validate() is True

    def test_validation_rejects_negative_freshness_threshold(self):
        """Test that negative freshness threshold is rejected."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        # Set negative threshold
        config.set('documentation.freshness_thresholds.critical', -5)

        with pytest.raises(ConfigValidationException, match="positive integer"):
            config.validate()

    def test_validation_rejects_unordered_thresholds(self):
        """Test that unordered freshness thresholds are rejected."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        # Set thresholds out of order (critical > important)
        config.set('documentation.freshness_thresholds.critical', 90)
        config.set('documentation.freshness_thresholds.important', 60)
        config.set('documentation.freshness_thresholds.normal', 30)

        with pytest.raises(ConfigValidationException, match="critical < important < normal"):
            config.validate()

    def test_validation_rejects_invalid_priority(self):
        """Test that invalid task priority is rejected."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        # Set priority out of range
        config.set('documentation.task_config.priority', 15)

        with pytest.raises(ConfigValidationException, match="between 1 and 10"):
            config.validate()

    def test_validation_rejects_non_list_maintenance_targets(self):
        """Test that non-list maintenance_targets is rejected."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        # Set maintenance_targets to non-list
        config.set('documentation.maintenance_targets', "not a list")

        with pytest.raises(ConfigValidationException, match="list of file paths"):
            config.validate()

    def test_validation_skips_when_documentation_disabled(self):
        """Test that validation is skipped when documentation.enabled=false."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        # Disable documentation
        config.set('documentation.enabled', False)

        # Set invalid values (should not raise since disabled)
        config.set('documentation.triggers.periodic.interval', 'invalid')
        config.set('documentation.freshness_thresholds.critical', -5)

        # Should not raise
        assert config.validate() is True


class TestDocumentationConfigDefaults:
    """Test documentation configuration defaults."""

    def test_default_freshness_thresholds(self):
        """Test default freshness threshold values."""
        Config.reset()
        config = Config.load(defaults_only=True)

        assert config.get('documentation.freshness_thresholds.critical') == 30
        assert config.get('documentation.freshness_thresholds.important') == 60
        assert config.get('documentation.freshness_thresholds.normal') == 90

    def test_default_task_config(self):
        """Test default task configuration values."""
        Config.reset()
        config = Config.load(defaults_only=True)

        assert config.get('documentation.task_config.priority') == 3
        assert config.get('documentation.task_config.assigned_agent') is None
        assert config.get('documentation.task_config.assigned_llm') is None
        assert config.get('documentation.task_config.auto_execute') is False

    def test_default_archive_config(self):
        """Test default archive configuration values."""
        Config.reset()
        config = Config.load(defaults_only=True)

        assert config.get('documentation.archive.enabled') is True
        assert config.get('documentation.archive.source_dir') == 'docs/development'
        assert config.get('documentation.archive.archive_dir') == 'docs/archive/development'

        patterns = config.get('documentation.archive.patterns')
        assert isinstance(patterns, list)
        assert len(patterns) == 3
        assert '*_IMPLEMENTATION_PLAN.md' in patterns


class TestDocumentationConfigOverrides:
    """Test documentation configuration overrides."""

    def test_can_override_documentation_enabled(self):
        """Test that documentation.enabled can be overridden."""
        Config.reset()
        config = Config.load(defaults_only=True)

        config.set('documentation.enabled', False)

        assert config.get('documentation.enabled') is False

    def test_can_override_freshness_thresholds(self):
        """Test that freshness thresholds can be overridden."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        config.set('documentation.freshness_thresholds.critical', 15)
        config.set('documentation.freshness_thresholds.important', 45)
        config.set('documentation.freshness_thresholds.normal', 75)

        assert config.get('documentation.freshness_thresholds.critical') == 15
        assert config.get('documentation.freshness_thresholds.important') == 45
        assert config.get('documentation.freshness_thresholds.normal') == 75

        # Should still be valid (ordered)
        assert config.validate() is True

    def test_can_disable_specific_triggers(self):
        """Test that individual triggers can be disabled."""
        Config.reset()
        config = Config.load(defaults_only=True)

        # Set valid agent type first
        config.set('agent.type', 'local')

        config.set('documentation.triggers.epic_complete.enabled', False)
        config.set('documentation.triggers.periodic.auto_create_task', False)

        assert config.get('documentation.triggers.epic_complete.enabled') is False
        assert config.get('documentation.triggers.periodic.auto_create_task') is False

        # Should still be valid
        assert config.validate() is True
