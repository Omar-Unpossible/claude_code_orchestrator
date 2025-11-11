"""Unit tests for StateManager documentation hooks (Story 1.2).

Tests the integration of documentation maintenance with StateManager:
- Task model documentation fields
- Milestone model version field
- complete_epic() hook
- achieve_milestone() hook

Part of ADR-015: Project Infrastructure Maintenance System (v1.4.0)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, UTC

from src.core.state import StateManager
from src.core.models import Task, Milestone, TaskType, TaskStatus
from src.core.config import Config


class TestTaskDocumentationFields:
    """Test Task model documentation fields."""

    def test_task_has_documentation_fields(self, test_config):
        """Test that Task model has all required documentation fields."""
        task = Task(
            project_id=1,
            title="Test Task",
            description="Test",
            requires_adr=True,
            has_architectural_changes=True,
            changes_summary="Added new architecture",
            documentation_status="pending"
        )

        assert hasattr(task, 'requires_adr')
        assert hasattr(task, 'has_architectural_changes')
        assert hasattr(task, 'changes_summary')
        assert hasattr(task, 'documentation_status')

        assert task.requires_adr is True
        assert task.has_architectural_changes is True
        assert task.changes_summary == "Added new architecture"
        assert task.documentation_status == "pending"

    def test_task_documentation_fields_defaults(self, test_config):
        """Test documentation field defaults."""
        task = Task(
            project_id=1,
            title="Test Task",
            description="Test"
        )

        assert task.requires_adr is False
        assert task.has_architectural_changes is False
        assert task.changes_summary is None
        assert task.documentation_status == "pending"

    def test_task_to_dict_includes_documentation_fields(self, test_config):
        """Test that to_dict() includes documentation fields."""
        task = Task(
            project_id=1,
            title="Test Task",
            description="Test",
            requires_adr=True,
            has_architectural_changes=True,
            changes_summary="Added OAuth",
            documentation_status="updated"
        )

        task_dict = task.to_dict()

        assert 'requires_adr' in task_dict
        assert 'has_architectural_changes' in task_dict
        assert 'changes_summary' in task_dict
        assert 'documentation_status' in task_dict

        assert task_dict['requires_adr'] is True
        assert task_dict['has_architectural_changes'] is True
        assert task_dict['changes_summary'] == "Added OAuth"
        assert task_dict['documentation_status'] == "updated"


class TestMilestoneVersionField:
    """Test Milestone model version field."""

    def test_milestone_has_version_field(self, test_config):
        """Test that Milestone model has version field."""
        milestone = Milestone(
            project_id=1,
            name="Test Milestone",
            version="v1.4.0"
        )

        assert hasattr(milestone, 'version')
        assert milestone.version == "v1.4.0"

    def test_milestone_version_nullable(self, test_config):
        """Test that version field is nullable."""
        milestone = Milestone(
            project_id=1,
            name="Test Milestone"
        )

        assert hasattr(milestone, 'version')
        assert milestone.version is None

    def test_milestone_to_dict_includes_version(self, test_config):
        """Test that to_dict() includes version field."""
        milestone = Milestone(
            project_id=1,
            name="Test Milestone",
            version="v1.4.0"
        )

        milestone_dict = milestone.to_dict()

        assert 'version' in milestone_dict
        assert milestone_dict['version'] == "v1.4.0"


class TestStateManagerConfigIntegration:
    """Test StateManager config integration."""

    def test_state_manager_set_config(self, state_manager, test_config):
        """Test setting config in StateManager."""
        state_manager.set_config(test_config)
        assert state_manager._config == test_config

    def test_state_manager_config_initially_none(self, state_manager):
        """Test that config is initially None."""
        assert state_manager._config is None


class TestCompleteEpicHook:
    """Test complete_epic() documentation hook."""

    def test_complete_epic_marks_epic_complete(self, state_manager, test_config):
        """Test that complete_epic marks epic as completed."""
        # Create project and epic
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Test Epic",
            description="Test epic"
        )

        # Complete epic
        state_manager.complete_epic(epic_id)

        # Verify epic marked complete
        epic = state_manager.get_task(epic_id)
        assert epic.status == TaskStatus.COMPLETED
        assert epic.completed_at is not None

    def test_complete_epic_creates_maintenance_task_when_requires_adr(
        self, state_manager, test_config
    ):
        """Test that complete_epic creates maintenance task when requires_adr=True."""
        # Set config
        state_manager.set_config(test_config)

        # Create project and epic
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Test Epic",
            description="Test epic",
            requires_adr=True,
            changes_summary="Added OAuth and MFA"
        )

        # Complete epic
        state_manager.complete_epic(epic_id)

        # Verify maintenance task created
        tasks = state_manager.get_all_tasks(project_id)
        maintenance_tasks = [
            t for t in tasks
            if 'Documentation' in t.title and t.status == TaskStatus.PENDING
        ]

        assert len(maintenance_tasks) > 0

    def test_complete_epic_skips_maintenance_when_no_flags(
        self, state_manager, test_config
    ):
        """Test that complete_epic skips maintenance when no documentation flags set."""
        # Set config
        state_manager.set_config(test_config)

        # Create project and epic WITHOUT flags
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Test Epic",
            description="Test epic"
            # No requires_adr or has_architectural_changes
        )

        # Count tasks before
        tasks_before = len(state_manager.get_all_tasks(project_id))

        # Complete epic
        state_manager.complete_epic(epic_id)

        # Count tasks after (should be same - no new maintenance task)
        tasks_after = len(state_manager.get_all_tasks(project_id))

        assert tasks_after == tasks_before

    def test_complete_epic_raises_error_for_nonexistent_epic(self, state_manager):
        """Test that complete_epic raises ValueError for non-existent epic."""
        with pytest.raises(ValueError, match="does not exist"):
            state_manager.complete_epic(999)

    def test_complete_epic_raises_error_for_non_epic_task(self, state_manager):
        """Test that complete_epic raises ValueError for non-Epic task."""
        # Create project and regular task
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        task_id = state_manager.create_task(
            project_id,
            {
                'title': "Regular Task",
                'description': "Not an epic",
                'task_type': TaskType.TASK
            }
        ).id

        with pytest.raises(ValueError, match="is not an Epic"):
            state_manager.complete_epic(task_id)


class TestAchieveMilestoneHook:
    """Test achieve_milestone() documentation hook."""

    def test_achieve_milestone_marks_milestone_achieved(self, state_manager, test_config):
        """Test that achieve_milestone marks milestone as achieved."""
        # Create project and milestone
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        milestone_id = state_manager.create_milestone(
            project_id=project_id,
            name="Test Milestone",
            description="Test milestone",
            version="v1.4.0"
        )

        # Achieve milestone
        state_manager.achieve_milestone(milestone_id)

        # Verify milestone achieved
        milestone = state_manager.get_milestone(milestone_id)
        assert milestone.achieved is True
        assert milestone.achieved_at is not None

    def test_achieve_milestone_creates_comprehensive_maintenance_task(
        self, state_manager, test_config
    ):
        """Test that achieve_milestone creates comprehensive maintenance task."""
        # Set config
        state_manager.set_config(test_config)

        # Create project, epic, and milestone
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Test Epic",
            description="Test epic"
        )

        milestone_id = state_manager.create_milestone(
            project_id=project_id,
            name="v1.4.0 Release",
            description="Major release",
            version="v1.4.0",
            required_epic_ids=[epic_id]
        )

        # Achieve milestone
        state_manager.achieve_milestone(milestone_id)

        # Verify comprehensive maintenance task created
        tasks = state_manager.get_all_tasks(project_id)
        maintenance_tasks = [
            t for t in tasks
            if 'Documentation' in t.title and 'milestone' in t.title.lower()
        ]

        assert len(maintenance_tasks) > 0

    def test_achieve_milestone_handles_nonexistent_milestone_gracefully(
        self, state_manager
    ):
        """Test that achieve_milestone handles non-existent milestone gracefully."""
        # Should not raise, just log warning
        state_manager.achieve_milestone(999)
        # No assertion needed - just verify it doesn't crash


class TestDocumentationHookDisabled:
    """Test documentation hooks when documentation.enabled=False."""

    def test_complete_epic_skips_hook_when_disabled(self, state_manager):
        """Test that complete_epic skips documentation hook when disabled."""
        # Create config with documentation disabled
        mock_config = Mock(spec=Config)
        mock_config.get = Mock(return_value=False)  # documentation.enabled=False

        state_manager.set_config(mock_config)

        # Create project and epic
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Test Epic",
            description="Test epic",
            requires_adr=True  # Flag is set but should be ignored
        )

        # Count tasks before
        tasks_before = len(state_manager.get_all_tasks(project_id))

        # Complete epic
        state_manager.complete_epic(epic_id)

        # Count tasks after (should be same - no maintenance task)
        tasks_after = len(state_manager.get_all_tasks(project_id))

        assert tasks_after == tasks_before

    def test_achieve_milestone_skips_hook_when_disabled(self, state_manager):
        """Test that achieve_milestone skips documentation hook when disabled."""
        # Create config with documentation disabled
        mock_config = Mock(spec=Config)
        mock_config.get = Mock(return_value=False)

        state_manager.set_config(mock_config)

        # Create project and milestone
        project_id = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        milestone_id = state_manager.create_milestone(
            project_id=project_id,
            name="Test Milestone",
            version="v1.4.0"
        )

        # Count tasks before
        tasks_before = len(state_manager.get_all_tasks(project_id))

        # Achieve milestone
        state_manager.achieve_milestone(milestone_id)

        # Count tasks after (should be same)
        tasks_after = len(state_manager.get_all_tasks(project_id))

        assert tasks_after == tasks_before
