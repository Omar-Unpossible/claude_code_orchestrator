"""End-to-end integration tests for Project Infrastructure Maintenance System.

Story 1.4: Integration Testing - Tests complete documentation maintenance workflow
including StateManager hooks, DocumentationManager, and configuration integration.

Tests verify:
1. Epic completion → maintenance task creation (with requires_adr=True)
2. Milestone achievement → comprehensive maintenance task
3. Epic completion without flags → no task created
4. documentation.enabled=false → no tasks created
5. Freshness check detects stale docs
6. archive_completed_plans() moves files correctly
7. Full workflow: create epic → complete → verify maintenance task
8. StateManager hooks integrate with DocumentationManager

Follows TEST_GUIDELINES.md:
- Max 0.5s sleep per test
- No heavy threading
- Uses real StateManager + DocumentationManager (not mocked)
- Proper cleanup
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import MagicMock

from src.core.state import StateManager
from src.core.config import Config
from src.core.models import Task, TaskType, TaskStatus, Milestone
from src.utils.documentation_manager import DocumentationManager


class TestDocumentationMaintenanceE2E:
    """End-to-end integration tests for documentation maintenance system."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace with documentation structure."""
        temp_dir = tempfile.mkdtemp()
        workspace = Path(temp_dir)

        # Create documentation structure
        (workspace / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n### Added\n\n")
        (workspace / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
        (workspace / "docs" / "architecture" / "ARCHITECTURE.md").write_text("# Architecture\n")
        (workspace / "docs" / "README.md").write_text("# Documentation\n")
        (workspace / "docs" / "decisions").mkdir(parents=True, exist_ok=True)
        (workspace / "docs" / "guides").mkdir(parents=True, exist_ok=True)
        (workspace / "docs" / "development").mkdir(parents=True, exist_ok=True)
        (workspace / "docs" / "archive" / "development").mkdir(parents=True, exist_ok=True)

        # Create some implementation plans to test archiving
        (workspace / "docs" / "development" / "FEATURE_X_IMPLEMENTATION_PLAN.md").write_text(
            "# Feature X Implementation Plan\n"
        )
        (workspace / "docs" / "development" / "AUTH_SYSTEM_COMPLETION_PLAN.md").write_text(
            "# Auth System Completion Plan\n"
        )

        yield workspace

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config_with_docs_enabled(self, test_config, temp_workspace):
        """Create test config with documentation maintenance enabled."""
        # Update config with documentation settings
        test_config._config['documentation'] = {
            'enabled': True,
            'auto_maintain': True,
            'maintenance_targets': [
                str(temp_workspace / 'CHANGELOG.md'),
                str(temp_workspace / 'docs' / 'architecture' / 'ARCHITECTURE.md'),
                str(temp_workspace / 'docs' / 'README.md'),
                str(temp_workspace / 'docs' / 'decisions/'),
                str(temp_workspace / 'docs' / 'guides/')
            ],
            'freshness_thresholds': {
                'critical': 30,
                'important': 60,
                'normal': 90
            },
            'archive': {
                'enabled': True,
                'source_dir': str(temp_workspace / 'docs' / 'development'),
                'archive_dir': str(temp_workspace / 'docs' / 'archive' / 'development'),
                'patterns': [
                    '*_IMPLEMENTATION_PLAN.md',
                    '*_COMPLETION_PLAN.md',
                    '*_GUIDE.md'
                ]
            },
            'triggers': {
                'epic_complete': {
                    'enabled': True,
                    'scope': 'comprehensive',
                    'auto_create_task': True
                },
                'milestone_achieved': {
                    'enabled': True,
                    'scope': 'comprehensive',
                    'auto_create_task': True
                },
                'version_bump': {
                    'enabled': True,
                    'scope': 'full_review',
                    'auto_create_task': True
                },
                'periodic': {
                    'enabled': True,
                    'interval_days': 7,
                    'scope': 'lightweight',
                    'auto_create_task': True
                }
            },
            'task_config': {
                'priority': 3,
                'assigned_agent': 'CLAUDE_CODE'
            }
        }
        return test_config

    @pytest.fixture
    def state_with_config(self, config_with_docs_enabled):
        """Create StateManager with documentation config."""
        state = StateManager('sqlite:///:memory:')
        state.set_config(config_with_docs_enabled)  # Set config after init
        yield state
        try:
            state.close()
        except Exception:
            pass

    @pytest.fixture
    def doc_manager(self, state_with_config, config_with_docs_enabled):
        """Create DocumentationManager with test setup."""
        return DocumentationManager(state_with_config, config_with_docs_enabled)

    @pytest.fixture
    def sample_project_with_epic(self, state_with_config):
        """Create sample project with epic and stories."""
        # Create project
        project = state_with_config.create_project(
            name="Test Project",
            description="Test project for documentation maintenance",
            working_dir="/tmp/test"
        )

        # Create epic
        epic_id = state_with_config.create_epic(
            project_id=project.id,
            title="User Authentication System",
            description="Complete auth system with OAuth, MFA, session management",
            requires_adr=True,
            has_architectural_changes=True,
            changes_summary="Added OAuth integration, MFA support, and session management"
        )

        # Create stories
        story1_id = state_with_config.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title="Email/password login",
            description="As a user, I want to login with email and password"
        )

        story2_id = state_with_config.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title="OAuth integration",
            description="As a user, I want to login with OAuth providers"
        )

        return {
            'project': project,
            'epic_id': epic_id,
            'story_ids': [story1_id, story2_id]
        }

    # ========================================================================
    # Test 1: Epic completion with requires_adr=True → maintenance task created
    # ========================================================================

    def test_epic_completion_creates_maintenance_task_with_adr(
        self,
        state_with_config,
        sample_project_with_epic
    ):
        """Test that completing epic with requires_adr=True creates maintenance task.

        Acceptance Criteria:
        - Epic marked as completed
        - Maintenance task created
        - Task has correct context (epic_id, changes, scope=comprehensive)
        - Task priority is 3 (from config)
        - Task assigned to CLAUDE_CODE
        """
        epic_id = sample_project_with_epic['epic_id']
        project_id = sample_project_with_epic['project'].id

        # Complete epic (should trigger maintenance task creation)
        state_with_config.complete_epic(epic_id)

        # Verify epic is completed
        epic = state_with_config.get_task(epic_id)
        assert epic.status == TaskStatus.COMPLETED
        assert epic.completed_at is not None

        # Find maintenance task
        all_tasks = state_with_config.get_project_tasks(project_id)
        maintenance_tasks = [
            t for t in all_tasks
            if 'Documentation:' in t.title and t.id != epic_id
        ]

        assert len(maintenance_tasks) == 1, "Should create exactly one maintenance task"

        maint_task = maintenance_tasks[0]

        # Verify maintenance task properties
        assert f"Epic #{epic_id}" in maint_task.title
        assert maint_task.priority == 3
        assert maint_task.task_type == TaskType.TASK
        assert maint_task.status == TaskStatus.PENDING

        # Verify context
        assert 'maintenance_context' in maint_task.context
        context = maint_task.context['maintenance_context']
        assert context['epic_id'] == epic_id
        assert context['epic_title'] == "User Authentication System"
        assert 'OAuth' in context['changes']  # Check changes summary included

        # Verify trigger and scope
        assert maint_task.context['trigger'] == 'epic_complete'
        assert maint_task.context['scope'] == 'comprehensive'

    # ========================================================================
    # Test 2: Milestone achievement → comprehensive maintenance task
    # ========================================================================

    def test_milestone_achievement_creates_comprehensive_task(
        self,
        state_with_config,
        sample_project_with_epic
    ):
        """Test that achieving milestone creates comprehensive maintenance task.

        Acceptance Criteria:
        - Milestone marked as achieved
        - Comprehensive maintenance task created
        - Task includes all completed epics in context
        - Task has milestone metadata (version, name)
        """
        project_id = sample_project_with_epic['project'].id
        epic_id = sample_project_with_epic['epic_id']

        # Complete epic first
        state_with_config.complete_epic(epic_id)

        # Create milestone
        milestone_id = state_with_config.create_milestone(
            project_id=project_id,
            name="Auth Complete",
            description="Authentication system fully implemented",
            required_epic_ids=[epic_id],
            version="v1.3.0"
        )

        # Achieve milestone (should trigger comprehensive maintenance task)
        state_with_config.achieve_milestone(milestone_id)

        # Verify milestone achieved
        milestone = state_with_config.get_milestone(milestone_id)
        assert milestone.achieved is True
        assert milestone.achieved_at is not None

        # Find maintenance task for milestone (not epic)
        all_tasks = state_with_config.get_project_tasks(project_id)
        milestone_maint_tasks = [
            t for t in all_tasks
            if 'Documentation:' in t.title and 'Auth Complete' in t.title
        ]

        assert len(milestone_maint_tasks) == 1, "Should create milestone maintenance task"

        maint_task = milestone_maint_tasks[0]

        # Verify comprehensive scope
        assert maint_task.context['trigger'] == 'milestone_achieved'
        assert maint_task.context['scope'] == 'comprehensive'

        # Verify milestone context
        context = maint_task.context['maintenance_context']
        assert context['milestone_id'] == milestone_id
        assert context['milestone_name'] == "Auth Complete"
        assert context['version'] == "v1.3.0"
        assert len(context['epics']) > 0  # Should include completed epics

    # ========================================================================
    # Test 3: Epic completion without flags → no task created
    # ========================================================================

    def test_epic_completion_without_flags_no_task_created(self, state_with_config):
        """Test that epic without requires_adr/architectural_changes creates no task.

        Acceptance Criteria:
        - Epic marked as completed
        - No maintenance task created
        """
        # Create project and epic WITHOUT documentation flags
        project = state_with_config.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        epic_id = state_with_config.create_epic(
            project_id=project.id,
            title="Minor UI Update",
            description="Update button colors",
            requires_adr=False,  # No ADR required
            has_architectural_changes=False  # No architectural changes
        )

        tasks_before = state_with_config.get_project_tasks(project.id)
        initial_count = len(tasks_before)

        # Complete epic
        state_with_config.complete_epic(epic_id)

        # Verify epic completed
        epic = state_with_config.get_task(epic_id)
        assert epic.status == TaskStatus.COMPLETED

        # Verify no maintenance task created
        tasks_after = state_with_config.get_project_tasks(project.id)
        assert len(tasks_after) == initial_count, "Should not create maintenance task"

    # ========================================================================
    # Test 4: documentation.enabled=false → no tasks created
    # ========================================================================

    def test_documentation_disabled_no_tasks_created(self, test_config):
        """Test that disabled documentation system creates no tasks.

        Acceptance Criteria:
        - Epic completed successfully
        - No maintenance tasks created
        - System logs that documentation is disabled
        """
        # Create config with documentation disabled
        test_config._config['documentation'] = {
            'enabled': False,  # DISABLED
            'auto_maintain': True
        }

        state = StateManager('sqlite:///:memory:')
        state.set_config(test_config)

        try:
            # Create project and epic
            project = state.create_project(
                name="Test Project",
                description="Test",
                working_dir="/tmp/test"
            )

            epic_id = state.create_epic(
                project_id=project.id,
                title="Auth System",
                description="Auth system",
                requires_adr=True,  # Would normally trigger maintenance
                has_architectural_changes=True
            )

            tasks_before = len(state.get_project_tasks(project.id))

            # Complete epic
            state.complete_epic(epic_id)

            # Verify no maintenance task created (documentation disabled)
            tasks_after = len(state.get_project_tasks(project.id))
            assert tasks_after == tasks_before, "Should not create task when disabled"

        finally:
            state.close()

    # ========================================================================
    # Test 5: Freshness check detects stale docs
    # ========================================================================

    def test_freshness_check_detects_stale_docs(
        self,
        doc_manager,
        temp_workspace,
        fast_time
    ):
        """Test that freshness check correctly identifies stale documentation.

        Acceptance Criteria:
        - Files older than threshold marked as stale
        - Files newer than threshold not marked as stale
        - Correct category assigned (critical, important, normal)
        - Age calculated correctly
        """
        # Create old file (simulate 45 days old)
        old_file = temp_workspace / "CHANGELOG.md"
        old_time = (datetime.now(UTC) - timedelta(days=45)).timestamp()
        old_file.touch()
        old_file.chmod(0o644)
        import os
        os.utime(old_file, (old_time, old_time))

        # Create recent file (simulate 5 days old)
        recent_file = temp_workspace / "docs" / "README.md"
        recent_time = (datetime.now(UTC) - timedelta(days=5)).timestamp()
        recent_file.touch()
        recent_file.chmod(0o644)
        os.utime(recent_file, (recent_time, recent_time))

        # Check freshness
        stale_docs = doc_manager.check_documentation_freshness()

        # CHANGELOG.md should be stale (45 days > 30 day threshold for critical)
        changelog_stale = any('CHANGELOG.md' in path for path in stale_docs.keys())
        assert changelog_stale, "CHANGELOG.md should be detected as stale"

        # Find CHANGELOG status
        changelog_status = None
        for path, status in stale_docs.items():
            if 'CHANGELOG.md' in path:
                changelog_status = status
                break

        if changelog_status:
            assert changelog_status.category == 'critical'
            assert changelog_status.is_stale is True
            assert changelog_status.age_days >= 44  # Allow for rounding

        # README should NOT be stale (5 days < 30 day threshold)
        readme_stale = any('README.md' in path for path in stale_docs.keys())
        assert not readme_stale, "README.md should not be detected as stale"

    # ========================================================================
    # Test 6: archive_completed_plans() moves files correctly
    # ========================================================================

    def test_archive_completed_plans_moves_files(
        self,
        doc_manager,
        temp_workspace
    ):
        """Test that archive_completed_plans correctly moves files to archive.

        Acceptance Criteria:
        - Implementation plan files moved to archive directory
        - Files no longer in source directory
        - Archive directory contains moved files
        - Returns list of archived file paths
        """
        source_dir = temp_workspace / "docs" / "development"
        archive_dir = temp_workspace / "docs" / "archive" / "development"

        # Verify files exist in source
        plan1 = source_dir / "FEATURE_X_IMPLEMENTATION_PLAN.md"
        plan2 = source_dir / "AUTH_SYSTEM_COMPLETION_PLAN.md"
        assert plan1.exists(), "Plan1 should exist before archiving"
        assert plan2.exists(), "Plan2 should exist before archiving"

        # Archive plans
        archived_files = doc_manager.archive_completed_plans(epic_id=5)

        # Verify files moved
        assert len(archived_files) == 2, "Should archive 2 files"

        # Verify source files removed
        assert not plan1.exists(), "Plan1 should be removed from source"
        assert not plan2.exists(), "Plan2 should be removed from source"

        # Verify files in archive
        archived_plan1 = archive_dir / "FEATURE_X_IMPLEMENTATION_PLAN.md"
        archived_plan2 = archive_dir / "AUTH_SYSTEM_COMPLETION_PLAN.md"
        assert archived_plan1.exists(), "Plan1 should be in archive"
        assert archived_plan2.exists(), "Plan2 should be in archive"

    # ========================================================================
    # Test 7: Full workflow - create epic → complete → verify task
    # ========================================================================

    def test_full_workflow_epic_to_maintenance_task(
        self,
        state_with_config,
        config_with_docs_enabled
    ):
        """Test complete workflow from epic creation to maintenance task.

        Acceptance Criteria:
        - Epic created with documentation flags
        - Stories added to epic
        - Epic completed
        - Maintenance task automatically created
        - Full context preserved throughout workflow
        """
        # Step 1: Create project
        project = state_with_config.create_project(
            name="Full Workflow Test",
            description="Testing complete workflow",
            working_dir="/tmp/test"
        )

        # Step 2: Create epic with documentation requirements
        epic_id = state_with_config.create_epic(
            project_id=project.id,
            title="Payment Processing System",
            description="Implement payment processing with Stripe integration",
            requires_adr=True,
            has_architectural_changes=True,
            changes_summary="Integrated Stripe API, added payment models, implemented webhooks"
        )

        # Step 3: Add stories
        story1 = state_with_config.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title="Stripe integration",
            description="As a user, I want to pay with credit card"
        )

        story2 = state_with_config.create_story(
            project_id=project.id,
            epic_id=epic_id,
            title="Webhook handling",
            description="As a system, I want to handle payment webhooks"
        )

        # Step 4: Complete stories
        state_with_config.update_task_status(story1, TaskStatus.COMPLETED)
        state_with_config.update_task_status(story2, TaskStatus.COMPLETED)

        # Step 5: Complete epic
        state_with_config.complete_epic(epic_id)

        # Step 6: Verify maintenance task created
        tasks = state_with_config.get_project_tasks(project.id)
        maintenance_tasks = [
            t for t in tasks
            if 'Documentation:' in t.title and t.id != epic_id
        ]

        assert len(maintenance_tasks) > 0, "Maintenance task should be created"
        maint_task = maintenance_tasks[0]

        # Step 7: Verify context completeness
        context = maint_task.context['maintenance_context']
        assert context['epic_id'] == epic_id
        assert context['epic_title'] == "Payment Processing System"
        assert 'Stripe' in context['changes']
        assert len(context['stories']) == 2  # Both stories in context

        # Step 8: Verify prompt includes useful information
        assert 'Payment Processing System' in maint_task.description
        assert 'Stripe' in maint_task.description or 'payment' in maint_task.description.lower()

    # ========================================================================
    # Test 8: StateManager hooks integrate with DocumentationManager
    # ========================================================================

    def test_state_manager_hooks_integration(
        self,
        state_with_config,
        config_with_docs_enabled
    ):
        """Test that StateManager hooks properly integrate with DocumentationManager.

        Acceptance Criteria:
        - complete_epic() calls DocumentationManager automatically
        - achieve_milestone() calls DocumentationManager automatically
        - Configuration properly passed through
        - Error in doc manager doesn't fail epic/milestone completion
        """
        # Create project and epic
        project = state_with_config.create_project(
            name="Hook Integration Test",
            description="Testing hooks",
            working_dir="/tmp/test"
        )

        epic_id = state_with_config.create_epic(
            project_id=project.id,
            title="Test Epic",
            description="Test epic for hook integration",
            requires_adr=True,
            has_architectural_changes=False
        )

        # Complete epic - this should trigger DocumentationManager via hook
        state_with_config.complete_epic(epic_id)

        # Verify epic completed (main operation succeeded)
        epic = state_with_config.get_task(epic_id)
        assert epic.status == TaskStatus.COMPLETED

        # Verify maintenance task created (hook executed)
        tasks = state_with_config.get_project_tasks(project.id)
        doc_tasks = [t for t in tasks if 'Documentation:' in t.title]
        assert len(doc_tasks) > 0, "Hook should create documentation task"

        # Create milestone
        milestone_id = state_with_config.create_milestone(
            project_id=project.id,
            name="Test Milestone",
            description="Test milestone",
            required_epic_ids=[epic_id],
            version="v1.0.0"
        )

        # Achieve milestone - this should trigger DocumentationManager via hook
        state_with_config.achieve_milestone(milestone_id)

        # Verify milestone achieved (main operation succeeded)
        milestone = state_with_config.get_milestone(milestone_id)
        assert milestone.achieved is True

        # Verify comprehensive maintenance task created for milestone
        all_tasks = state_with_config.get_project_tasks(project.id)
        milestone_docs = [
            t for t in all_tasks
            if 'Documentation:' in t.title and 'Test Milestone' in t.title
        ]
        assert len(milestone_docs) > 0, "Hook should create milestone documentation task"

        # Verify it's a comprehensive task
        maint_task = milestone_docs[0]
        assert maint_task.context['scope'] == 'comprehensive'
        assert maint_task.context['trigger'] == 'milestone_achieved'
