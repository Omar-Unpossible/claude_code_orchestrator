"""Unit tests for DocumentationManager.

Tests all functionality of automatic documentation maintenance:
- Freshness checking (stale doc detection)
- Maintenance task creation
- Prompt generation
- Plan archiving
- CHANGELOG updates
- ADR creation suggestions

Follows TEST_GUIDELINES.md:
- Max 0.5s sleep per test
- Max 5 threads per test
- Max 20KB allocations
- Fast timeouts (0.1-0.2s)
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, MagicMock, patch

from src.utils.documentation_manager import DocumentationManager, DocumentStatus
from src.core.models import Task, TaskType, TaskStatus, TaskAssignee
from src.core.config import Config
from src.core.state import StateManager


class TestDocumentationManager:
    """Test suite for DocumentationManager."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory with docs structure."""
        temp_dir = tempfile.mkdtemp()

        # Create directory structure
        docs_dir = Path(temp_dir) / 'docs'
        docs_dir.mkdir()

        (docs_dir / 'architecture').mkdir()
        (docs_dir / 'decisions').mkdir()
        (docs_dir / 'guides').mkdir()
        (docs_dir / 'development').mkdir()
        (docs_dir / 'archive' / 'development').mkdir(parents=True)

        # Create sample files
        (Path(temp_dir) / 'CHANGELOG.md').write_text(
            "# Changelog\n\n## [Unreleased]\n\n### Added\n\n"
        )
        (Path(temp_dir) / 'README.md').write_text("# Project\n")
        (docs_dir / 'architecture' / 'ARCHITECTURE.md').write_text("# Architecture\n")
        (docs_dir / 'README.md').write_text("# Documentation\n")

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_state_manager(self):
        """Create mock StateManager."""
        mock_sm = Mock(spec=StateManager)
        mock_sm.create_task = MagicMock(return_value=Mock(id=123))
        return mock_sm

    @pytest.fixture
    def mock_config(self):
        """Create mock Config with documentation settings."""
        mock_cfg = Mock(spec=Config)

        # Default configuration
        config_data = {
            'documentation.enabled': True,
            'documentation.auto_maintain': True,
            'documentation.maintenance_targets': [
                'CHANGELOG.md',
                'README.md',
                'docs/architecture/ARCHITECTURE.md',
                'docs/README.md'
            ],
            'documentation.freshness_thresholds': {
                'critical': 30,
                'important': 60,
                'normal': 90
            },
            'documentation.archive': {
                'enabled': True,
                'source_dir': 'docs/development',
                'archive_dir': 'docs/archive/development',
                'patterns': ['*_IMPLEMENTATION_PLAN.md', '*_GUIDE.md']
            },
            'documentation.task_config': {
                'priority': 3,
                'assigned_agent': None,
                'auto_execute': False
            },
            'documentation.triggers.epic_complete.enabled': True,
            'documentation.triggers.epic_complete.auto_create_task': True,
            'documentation.triggers.milestone_achieved.enabled': True,
            'documentation.triggers.milestone_achieved.auto_create_task': True,
            'documentation.triggers.periodic.enabled': True,
            'documentation.triggers.periodic.auto_create_task': False
        }

        mock_cfg.get = lambda key, default=None: config_data.get(key, default)
        return mock_cfg

    @pytest.fixture
    def doc_manager(self, mock_state_manager, mock_config, temp_project_dir):
        """Create DocumentationManager instance."""
        # Save original directory before any potential errors
        try:
            original_cwd = os.getcwd()
        except (FileNotFoundError, OSError):
            # If getcwd fails, use /tmp as fallback
            original_cwd = '/tmp'
            os.chdir(original_cwd)

        try:
            # Change to temp directory for tests
            os.chdir(temp_project_dir)

            manager = DocumentationManager(mock_state_manager, mock_config)

            yield manager
        finally:
            # Always restore original directory
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                # If original_cwd or current dir doesn't exist, just go to /tmp
                os.chdir('/tmp')

    # ==================== Initialization Tests ====================

    def test_initialization(self, mock_state_manager, mock_config):
        """Test DocumentationManager initializes correctly."""
        doc_mgr = DocumentationManager(mock_state_manager, mock_config)

        assert doc_mgr.state_manager == mock_state_manager
        assert doc_mgr.config == mock_config
        assert doc_mgr.enabled is True
        assert len(doc_mgr.maintenance_targets) == 4
        assert doc_mgr.freshness_thresholds['critical'] == 30

    def test_initialization_disabled(self, mock_state_manager):
        """Test DocumentationManager with disabled configuration."""
        mock_cfg = Mock(spec=Config)
        mock_cfg.get = lambda key, default=None: False if 'enabled' in key else default

        doc_mgr = DocumentationManager(mock_state_manager, mock_cfg)
        assert doc_mgr.enabled is False

    # ==================== Freshness Checking Tests ====================

    def test_check_documentation_freshness_all_fresh(self, doc_manager):
        """Test freshness check when all docs are fresh."""
        # All files just created, should be fresh
        stale_docs = doc_manager.check_documentation_freshness()

        assert len(stale_docs) == 0

    def test_check_documentation_freshness_with_stale_docs(self, doc_manager, temp_project_dir):
        """Test freshness check detects stale documents."""
        # Make CHANGELOG.md appear old (35 days)
        changelog_path = Path(temp_project_dir) / 'CHANGELOG.md'
        old_time = (datetime.now(UTC) - timedelta(days=35)).timestamp()
        os.utime(changelog_path, (old_time, old_time))

        stale_docs = doc_manager.check_documentation_freshness()

        assert len(stale_docs) > 0

        # Find the CHANGELOG entry (could be relative or absolute path)
        changelog_key = None
        for key in stale_docs.keys():
            if 'CHANGELOG.md' in key:
                changelog_key = key
                break

        assert changelog_key is not None, f"CHANGELOG.md not found in {list(stale_docs.keys())}"

        # Check DocumentStatus details
        status = stale_docs[changelog_key]
        assert status.age_days >= 35
        assert status.category == 'critical'
        assert status.is_stale is True
        assert status.threshold_days == 30

    def test_check_documentation_freshness_disabled(self, mock_state_manager, temp_project_dir):
        """Test freshness check when documentation maintenance disabled."""
        mock_cfg = Mock(spec=Config)
        mock_cfg.get = lambda key, default=None: False if 'enabled' in key else default

        os.chdir(temp_project_dir)
        doc_mgr = DocumentationManager(mock_state_manager, mock_cfg)

        stale_docs = doc_mgr.check_documentation_freshness()
        assert len(stale_docs) == 0

    def test_check_documentation_freshness_missing_target(self, doc_manager):
        """Test freshness check handles missing documentation targets gracefully."""
        # Add non-existent target
        doc_manager.maintenance_targets.append('nonexistent.md')

        # Should not crash, just log warning
        stale_docs = doc_manager.check_documentation_freshness()
        assert isinstance(stale_docs, dict)

    def test_check_file_freshness(self, doc_manager, temp_project_dir):
        """Test _check_file_freshness helper method."""
        file_path = Path(temp_project_dir) / 'CHANGELOG.md'
        now = datetime.now(UTC)

        status = doc_manager._check_file_freshness(file_path, now)

        assert status is not None
        assert status.path == str(file_path)
        assert status.category == 'critical'
        assert status.age_days >= 0

    def test_check_file_freshness_nonexistent(self, doc_manager):
        """Test _check_file_freshness with nonexistent file."""
        file_path = Path('nonexistent.md')
        now = datetime.now(UTC)

        status = doc_manager._check_file_freshness(file_path, now)
        assert status is None

    # ==================== Task Creation Tests ====================

    def test_create_maintenance_task_epic_complete(self, doc_manager, mock_state_manager):
        """Test creating maintenance task for epic completion."""
        context = {
            'epic_id': 5,
            'epic_title': 'User Authentication',
            'changes': 'Added OAuth, MFA, session management',
            'project_id': 1
        }

        task_id = doc_manager.create_maintenance_task(
            trigger='epic_complete',
            scope='comprehensive',
            context=context
        )

        assert task_id == 123  # Mock returns 123
        mock_state_manager.create_task.assert_called_once()

        # Verify task data
        call_args = mock_state_manager.create_task.call_args
        project_id, task_data = call_args[0]

        assert project_id == 1
        assert 'Epic #5' in task_data['title']
        assert task_data['priority'] == 3
        assert task_data['task_type'] == TaskType.TASK
        assert task_data['context']['trigger'] == 'epic_complete'

    def test_create_maintenance_task_milestone_achieved(self, doc_manager, mock_state_manager):
        """Test creating maintenance task for milestone achievement."""
        context = {
            'milestone_id': 3,
            'milestone_name': 'v1.4.0 Release',
            'version': 'v1.4.0',
            'epics': [1, 2, 3],
            'project_id': 1
        }

        task_id = doc_manager.create_maintenance_task(
            trigger='milestone_achieved',
            scope='comprehensive',
            context=context
        )

        assert task_id == 123
        mock_state_manager.create_task.assert_called_once()

        call_args = mock_state_manager.create_task.call_args
        _, task_data = call_args[0]

        assert 'v1.4.0 Release' in task_data['title']
        assert task_data['context']['scope'] == 'comprehensive'

    def test_create_maintenance_task_disabled(self, mock_state_manager, temp_project_dir):
        """Test task creation when documentation maintenance disabled."""
        mock_cfg = Mock(spec=Config)
        mock_cfg.get = lambda key, default=None: False if 'enabled' in key else default

        os.chdir(temp_project_dir)
        doc_mgr = DocumentationManager(mock_state_manager, mock_cfg)

        task_id = doc_mgr.create_maintenance_task(
            trigger='epic_complete',
            scope='lightweight',
            context={'epic_id': 1}
        )

        assert task_id == -1
        mock_state_manager.create_task.assert_not_called()

    def test_create_maintenance_task_auto_maintain_false(self, doc_manager, mock_state_manager):
        """Test task creation when auto_maintain is false."""
        doc_manager.config.get = lambda key, default=None: (
            False if 'auto_maintain' in key else
            doc_manager.config.get(key, default)
        )

        task_id = doc_manager.create_maintenance_task(
            trigger='epic_complete',
            scope='lightweight',
            context={'epic_id': 1}
        )

        assert task_id == -1
        mock_state_manager.create_task.assert_not_called()

    def test_create_maintenance_task_trigger_disabled(self, mock_state_manager, mock_config):
        """Test task creation when specific trigger disabled."""
        # Create new config with epic_complete disabled
        import tempfile
        import os

        temp_dir = tempfile.mkdtemp()
        try:
            original_cwd = os.getcwd()
        except (FileNotFoundError, OSError):
            original_cwd = '/tmp'
            os.chdir(original_cwd)

        try:
            os.chdir(temp_dir)

            # Create mock config with trigger disabled
            config_data = {
                'documentation.enabled': True,
                'documentation.auto_maintain': True,
                'documentation.triggers.epic_complete.enabled': False,  # Disabled!
                'documentation.triggers.epic_complete.auto_create_task': True,
                'documentation.maintenance_targets': ['CHANGELOG.md'],
                'documentation.freshness_thresholds': {'critical': 30, 'important': 60, 'normal': 90},
                'documentation.archive': {
                    'enabled': True,
                    'source_dir': 'docs/development',
                    'archive_dir': 'docs/archive/development',
                    'patterns': ['*_IMPLEMENTATION_PLAN.md']
                },
                'documentation.task_config': {'priority': 3, 'assigned_agent': None, 'auto_execute': False}
            }

            mock_cfg = Mock(spec=Config)
            mock_cfg.get = lambda key, default=None: config_data.get(key, default)

            doc_mgr = DocumentationManager(mock_state_manager, mock_cfg)

            task_id = doc_mgr.create_maintenance_task(
                trigger='epic_complete',
                scope='lightweight',
                context={'epic_id': 1}
            )

            assert task_id == -1
            mock_state_manager.create_task.assert_not_called()
        finally:
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                os.chdir('/tmp')
            import shutil
            shutil.rmtree(temp_dir)

    # ==================== Prompt Generation Tests ====================

    def test_generate_maintenance_prompt_epic_complete(self, doc_manager):
        """Test generating prompt for epic completion."""
        context = {
            'trigger': 'epic_complete',
            'scope': 'comprehensive',
            'epic_id': 5,
            'epic_title': 'User Authentication',
            'changes': 'Added OAuth and MFA support'
        }

        prompt = doc_manager.generate_maintenance_prompt(
            stale_docs=['CHANGELOG.md', 'docs/architecture/ARCHITECTURE.md'],
            context=context
        )

        assert '# Documentation Maintenance Task' in prompt
        assert 'Epic Completion: #5' in prompt
        assert 'User Authentication' in prompt
        assert 'Added OAuth and MFA support' in prompt
        assert 'CHANGELOG.md' in prompt
        assert 'ARCHITECTURE.md' in prompt

    def test_generate_maintenance_prompt_milestone_achieved(self, doc_manager):
        """Test generating prompt for milestone achievement."""
        context = {
            'trigger': 'milestone_achieved',
            'scope': 'comprehensive',
            'milestone_id': 3,
            'milestone_name': 'v1.4.0 Complete',
            'version': 'v1.4.0',
            'epics': [1, 2, 3]
        }

        prompt = doc_manager.generate_maintenance_prompt(
            stale_docs=[],
            context=context
        )

        assert 'Milestone Achievement' in prompt
        assert 'v1.4.0 Complete' in prompt
        assert 'Completed Epics**: 3' in prompt

    def test_generate_maintenance_prompt_no_stale_docs(self, doc_manager):
        """Test prompt generation with no stale docs."""
        context = {
            'trigger': 'epic_complete',
            'scope': 'lightweight',
            'epic_id': 1
        }

        prompt = doc_manager.generate_maintenance_prompt(
            stale_docs=[],
            context=context
        )

        assert '# Documentation Maintenance Task' in prompt
        assert 'Stale Documentation' not in prompt

    # ==================== Archive Tests ====================

    def test_archive_completed_plans(self, doc_manager, temp_project_dir):
        """Test archiving completed implementation plans."""
        # Create sample implementation plan
        dev_dir = Path(temp_project_dir) / 'docs' / 'development'
        plan_file = dev_dir / 'FEATURE_X_IMPLEMENTATION_PLAN.md'
        plan_file.write_text("# Implementation Plan\n")

        archived = doc_manager.archive_completed_plans(epic_id=5)

        assert len(archived) == 1
        assert 'FEATURE_X_IMPLEMENTATION_PLAN.md' in archived[0]

        # Verify file moved
        assert not plan_file.exists()
        archive_path = Path(temp_project_dir) / 'docs' / 'archive' / 'development' / plan_file.name
        assert archive_path.exists()

    def test_archive_completed_plans_disabled(self, doc_manager):
        """Test archive when disabled in config."""
        doc_manager.archive_config['enabled'] = False

        archived = doc_manager.archive_completed_plans(epic_id=1)
        assert len(archived) == 0

    def test_archive_completed_plans_no_files(self, doc_manager):
        """Test archive when no matching files exist."""
        archived = doc_manager.archive_completed_plans(epic_id=1)
        assert len(archived) == 0

    def test_archive_completed_plans_duplicate_handling(self, doc_manager, temp_project_dir):
        """Test archive handles duplicate filenames."""
        dev_dir = Path(temp_project_dir) / 'docs' / 'development'
        archive_dir = Path(temp_project_dir) / 'docs' / 'archive' / 'development'

        # Create plan in both locations
        plan_file = dev_dir / 'TEST_IMPLEMENTATION_PLAN.md'
        plan_file.write_text("# Plan\n")

        existing_file = archive_dir / 'TEST_IMPLEMENTATION_PLAN.md'
        existing_file.write_text("# Old Plan\n")

        archived = doc_manager.archive_completed_plans(epic_id=1)

        # Should archive with timestamp suffix
        assert len(archived) == 1
        assert 'TEST_IMPLEMENTATION_PLAN' in archived[0]

    # ==================== CHANGELOG Update Tests ====================

    def test_update_changelog(self, doc_manager, temp_project_dir):
        """Test updating CHANGELOG.md with epic completion."""
        epic = Mock(spec=Task)
        epic.id = 5
        epic.title = 'User Authentication System'

        doc_manager.update_changelog(epic)

        # Verify CHANGELOG updated
        changelog_path = Path(temp_project_dir) / 'CHANGELOG.md'
        content = changelog_path.read_text()

        assert 'User Authentication System' in content
        assert 'Epic #5' in content

    def test_update_changelog_missing_file(self, doc_manager, temp_project_dir):
        """Test CHANGELOG update when file doesn't exist."""
        # Remove CHANGELOG
        (Path(temp_project_dir) / 'CHANGELOG.md').unlink()

        epic = Mock(spec=Task)
        epic.id = 1
        epic.title = 'Test Epic'

        # Should not crash
        doc_manager.update_changelog(epic)

    def test_update_changelog_no_unreleased_section(self, doc_manager, temp_project_dir):
        """Test CHANGELOG update when no [Unreleased] section exists."""
        changelog_path = Path(temp_project_dir) / 'CHANGELOG.md'
        changelog_path.write_text("# Changelog\n\n## [1.0.0]\n")

        epic = Mock(spec=Task)
        epic.id = 1
        epic.title = 'Test Epic'

        # Should log warning but not crash
        doc_manager.update_changelog(epic)

    # ==================== ADR Suggestion Tests ====================

    def test_suggest_adr_creation_with_flag(self, doc_manager):
        """Test ADR suggestion when requires_adr flag set."""
        epic = Mock(spec=Task)
        epic.id = 5
        epic.title = 'Test Epic'
        epic.description = 'Test description'
        epic.requires_adr = True

        result = doc_manager.suggest_adr_creation(epic)
        assert result is True

    def test_suggest_adr_creation_with_architectural_changes(self, doc_manager):
        """Test ADR suggestion when has_architectural_changes flag set."""
        epic = Mock(spec=Task)
        epic.id = 5
        epic.title = 'Test Epic'
        epic.description = 'Test description'
        epic.requires_adr = False
        epic.has_architectural_changes = True

        result = doc_manager.suggest_adr_creation(epic)
        assert result is True

    def test_suggest_adr_creation_with_keywords(self, doc_manager):
        """Test ADR suggestion based on keywords in title/description."""
        epic = Mock(spec=Task)
        epic.id = 5
        epic.title = 'Architecture Decision: New Design Pattern'
        epic.description = 'Implementing new architecture'

        # Mock missing attributes
        if not hasattr(epic, 'requires_adr'):
            epic.requires_adr = None
        if not hasattr(epic, 'has_architectural_changes'):
            epic.has_architectural_changes = None

        result = doc_manager.suggest_adr_creation(epic)
        assert result is True

    def test_suggest_adr_creation_no_flags(self, doc_manager):
        """Test ADR suggestion when no flags or keywords present."""
        epic = Mock(spec=Task)
        epic.id = 5
        epic.title = 'Simple Bug Fix'
        epic.description = 'Fixed a small bug'

        # Ensure attributes exist
        epic.requires_adr = False
        epic.has_architectural_changes = False

        result = doc_manager.suggest_adr_creation(epic)
        assert result is False


    def test_create_maintenance_task_auto_create_false(self, mock_state_manager, mock_config):
        """Test task creation when auto_create_task is false for specific trigger."""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            original_cwd = os.getcwd()
        except (FileNotFoundError, OSError):
            original_cwd = '/tmp'

        try:
            os.chdir(temp_dir)

            # Config with auto_create_task disabled for periodic
            config_data = {
                'documentation.enabled': True,
                'documentation.auto_maintain': True,
                'documentation.triggers.periodic.enabled': True,
                'documentation.triggers.periodic.auto_create_task': False,  # Disabled
                'documentation.maintenance_targets': ['CHANGELOG.md'],
                'documentation.freshness_thresholds': {'critical': 30, 'important': 60, 'normal': 90},
                'documentation.archive': {
                    'enabled': True,
                    'source_dir': 'docs/development',
                    'archive_dir': 'docs/archive/development',
                    'patterns': ['*_IMPLEMENTATION_PLAN.md']
                },
                'documentation.task_config': {'priority': 3, 'assigned_agent': None, 'auto_execute': False}
            }

            mock_cfg = Mock(spec=Config)
            mock_cfg.get = lambda key, default=None: config_data.get(key, default)

            doc_mgr = DocumentationManager(mock_state_manager, mock_cfg)

            task_id = doc_mgr.create_maintenance_task(
                trigger='periodic',
                scope='freshness_check',
                context={'stale_docs': {}}
            )

            assert task_id == -1
            mock_state_manager.create_task.assert_not_called()
        finally:
            try:
                os.chdir(original_cwd)
            except (FileNotFoundError, OSError):
                os.chdir('/tmp')
            shutil.rmtree(temp_dir)

    def test_create_maintenance_task_exception_handling(self, mock_state_manager, mock_config, temp_project_dir):
        """Test task creation handles exceptions gracefully."""
        os.chdir(temp_project_dir)
        doc_mgr = DocumentationManager(mock_state_manager, mock_config)

        # Make create_task raise an exception
        mock_state_manager.create_task.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            doc_mgr.create_maintenance_task(
                trigger='epic_complete',
                scope='lightweight',
                context={'epic_id': 1, 'project_id': 1}
            )


class TestDocumentStatus:
    """Test DocumentStatus dataclass."""

    def test_document_status_creation(self):
        """Test creating DocumentStatus instance."""
        now = datetime.now(UTC)
        status = DocumentStatus(
            path='CHANGELOG.md',
            last_modified=now,
            age_days=35,
            category='critical',
            is_stale=True,
            threshold_days=30
        )

        assert status.path == 'CHANGELOG.md'
        assert status.age_days == 35
        assert status.category == 'critical'
        assert status.is_stale is True
        assert status.threshold_days == 30


# ============================================================================
# Story 2.1: Periodic Scheduler Tests
# ============================================================================

class TestPeriodicScheduler:
    """Test suite for periodic documentation freshness checks."""

    @pytest.fixture
    def temp_project_dir(self):
        """Create temporary project directory for periodic tests."""
        temp_dir = tempfile.mkdtemp()
        workspace = Path(temp_dir)

        # Create documentation structure
        (workspace / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n### Added\n\n")
        (workspace / "docs" / "architecture").mkdir(parents=True, exist_ok=True)
        (workspace / "docs" / "architecture" / "ARCHITECTURE.md").write_text("# Architecture\n")

        yield workspace

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def config_with_periodic(self, test_config, temp_project_dir):
        """Create config with periodic checks enabled."""
        test_config._config['documentation'] = {
            'enabled': True,
            'auto_maintain': True,
            'maintenance_targets': [
                str(temp_project_dir / 'CHANGELOG.md'),
                str(temp_project_dir / 'docs/architecture/ARCHITECTURE.md')
            ],
            'freshness_thresholds': {
                'critical': 30,
                'important': 60,
                'normal': 90
            },
            'triggers': {
                'periodic': {
                    'enabled': True,
                    'interval_days': 7,
                    'scope': 'lightweight',
                    'auto_create_task': True
                }
            }
        }
        return test_config

    @pytest.fixture
    def state_manager_mock(self):
        """Create mock StateManager for testing."""
        state_mock = Mock(spec=StateManager)
        task_mock = Mock(spec=Task)
        task_mock.id = 42
        state_mock.create_task.return_value = task_mock
        return state_mock

    @pytest.fixture
    def doc_manager_with_periodic(self, state_manager_mock, config_with_periodic):
        """Create DocumentationManager with periodic checks enabled."""
        doc_mgr = DocumentationManager(state_manager_mock, config_with_periodic)
        yield doc_mgr
        # Cleanup: stop periodic checks
        doc_mgr.stop_periodic_checks()

    # ========================================================================
    # Test 1: Start periodic checks successfully
    # ========================================================================

    def test_start_periodic_checks_success(self, doc_manager_with_periodic):
        """Test starting periodic checks successfully."""
        result = doc_manager_with_periodic.start_periodic_checks(project_id=1)

        assert result is True
        assert doc_manager_with_periodic._periodic_timer is not None
        assert doc_manager_with_periodic._periodic_timer.is_alive()

        # Cleanup
        doc_manager_with_periodic.stop_periodic_checks()

    # ========================================================================
    # Test 2: Start fails when documentation disabled
    # ========================================================================

    def test_start_periodic_checks_documentation_disabled(
        self,
        state_manager_mock,
        test_config
    ):
        """Test that periodic checks don't start when documentation disabled."""
        test_config._config['documentation'] = {'enabled': False}
        doc_mgr = DocumentationManager(state_manager_mock, test_config)

        result = doc_mgr.start_periodic_checks(project_id=1)

        assert result is False
        assert doc_mgr._periodic_timer is None

    # ========================================================================
    # Test 3: Start fails when periodic disabled
    # ========================================================================

    def test_start_periodic_checks_periodic_disabled(
        self,
        state_manager_mock,
        test_config,
        temp_project_dir
    ):
        """Test that periodic checks don't start when periodic.enabled=False."""
        test_config._config['documentation'] = {
            'enabled': True,
            'triggers': {
                'periodic': {
                    'enabled': False  # DISABLED
                }
            }
        }
        doc_mgr = DocumentationManager(state_manager_mock, test_config)

        result = doc_mgr.start_periodic_checks(project_id=1)

        assert result is False
        assert doc_mgr._periodic_timer is None

    # ========================================================================
    # Test 4: Start fails when already running
    # ========================================================================

    def test_start_periodic_checks_already_running(self, doc_manager_with_periodic):
        """Test that starting checks twice doesn't create duplicate timers."""
        # Start first time
        result1 = doc_manager_with_periodic.start_periodic_checks(project_id=1)
        assert result1 is True

        # Try to start again
        result2 = doc_manager_with_periodic.start_periodic_checks(project_id=1)
        assert result2 is False

        # Cleanup
        doc_manager_with_periodic.stop_periodic_checks()

    # ========================================================================
    # Test 5: Stop periodic checks
    # ========================================================================

    def test_stop_periodic_checks(self, doc_manager_with_periodic):
        """Test stopping periodic checks."""
        # Start checks
        doc_manager_with_periodic.start_periodic_checks(project_id=1)
        assert doc_manager_with_periodic._periodic_timer is not None
        assert doc_manager_with_periodic._periodic_timer.is_alive()

        # Stop checks
        doc_manager_with_periodic.stop_periodic_checks()
        assert doc_manager_with_periodic._periodic_timer is None

    # ========================================================================
    # Test 6: Stop when no timer exists
    # ========================================================================

    def test_stop_periodic_checks_no_timer(self, doc_manager_with_periodic):
        """Test that stop_periodic_checks is idempotent."""
        # Stop without starting (should not error)
        doc_manager_with_periodic.stop_periodic_checks()
        assert doc_manager_with_periodic._periodic_timer is None

        # Stop again (should still not error)
        doc_manager_with_periodic.stop_periodic_checks()
        assert doc_manager_with_periodic._periodic_timer is None

    # ========================================================================
    # Test 7: Periodic check creates task with stale docs
    # ========================================================================

    def test_periodic_check_creates_task_with_stale_docs(
        self,
        doc_manager_with_periodic,
        temp_project_dir
    ):
        """Test that periodic check creates maintenance task when stale docs found."""
        # Create a stale file
        old_file = temp_project_dir / 'CHANGELOG.md'
        old_file.write_text("# Changelog\n")
        old_time = (datetime.now(UTC) - timedelta(days=45)).timestamp()
        os.utime(old_file, (old_time, old_time))

        # Mock check_documentation_freshness to return stale doc
        stale_docs = {
            str(old_file): DocumentStatus(
                path=str(old_file),
                last_modified=datetime.fromtimestamp(old_time, tz=UTC),
                age_days=45,
                category='critical',
                is_stale=True,
                threshold_days=30
            )
        }

        with patch.object(
            doc_manager_with_periodic,
            'check_documentation_freshness',
            return_value=stale_docs
        ):
            # Run periodic check
            doc_manager_with_periodic._run_periodic_check(project_id=1)

            # Verify maintenance task was created
            assert doc_manager_with_periodic.state_manager.create_task.called
            call_args = doc_manager_with_periodic.state_manager.create_task.call_args
            assert call_args[0][0] == 1  # project_id
            task_data = call_args[0][1]
            assert 'Documentation:' in task_data['title']
            assert 'periodic' in task_data['context']['trigger']

    # ========================================================================
    # Test 8: Periodic check notification only (no task)
    # ========================================================================

    def test_periodic_check_notification_only_no_task(
        self,
        state_manager_mock,
        config_with_periodic,
        temp_project_dir
    ):
        """Test that periodic check only logs when auto_create_task=False."""
        # Set auto_create_task to false
        config_with_periodic._config['documentation']['triggers']['periodic']['auto_create_task'] = False

        doc_mgr = DocumentationManager(state_manager_mock, config_with_periodic)

        # Create stale file
        old_file = temp_project_dir / 'CHANGELOG.md'
        old_file.write_text("# Changelog\n")
        old_time = (datetime.now(UTC) - timedelta(days=45)).timestamp()
        os.utime(old_file, (old_time, old_time))

        stale_docs = {
            str(old_file): DocumentStatus(
                path=str(old_file),
                last_modified=datetime.fromtimestamp(old_time, tz=UTC),
                age_days=45,
                category='critical',
                is_stale=True,
                threshold_days=30
            )
        }

        with patch.object(doc_mgr, 'check_documentation_freshness', return_value=stale_docs):
            with patch('src.utils.documentation_manager.logger') as mock_logger:
                # Run periodic check
                doc_mgr._run_periodic_check(project_id=1)

                # Verify warning logged but no task created
                mock_logger.warning.assert_called()
                assert not doc_mgr.state_manager.create_task.called

        # Cleanup
        doc_mgr.stop_periodic_checks()

    # ========================================================================
    # Test 9: Periodic check with no stale docs
    # ========================================================================

    def test_periodic_check_no_stale_docs(self, doc_manager_with_periodic):
        """Test periodic check when all docs are fresh."""
        with patch.object(
            doc_manager_with_periodic,
            'check_documentation_freshness',
            return_value={}  # No stale docs
        ):
            # Run periodic check
            doc_manager_with_periodic._run_periodic_check(project_id=1)

            # Verify no task created
            assert not doc_manager_with_periodic.state_manager.create_task.called

    # ========================================================================
    # Test 10: Periodic check rescheduling
    # ========================================================================

    def test_periodic_check_rescheduling(self, doc_manager_with_periodic):
        """Test that periodic check reschedules itself after running."""
        # Start checks
        doc_manager_with_periodic.start_periodic_checks(project_id=1)
        first_timer = doc_manager_with_periodic._periodic_timer

        # Mock check to return no stale docs (fast execution)
        with patch.object(
            doc_manager_with_periodic,
            'check_documentation_freshness',
            return_value={}
        ):
            # Manually trigger the check (simulating timer firing)
            doc_manager_with_periodic._run_periodic_check(project_id=1)

            # Verify a new timer was scheduled
            assert doc_manager_with_periodic._periodic_timer is not None
            assert doc_manager_with_periodic._periodic_timer != first_timer

        # Cleanup
        doc_manager_with_periodic.stop_periodic_checks()

    # ========================================================================
    # Test 11: Periodic check error handling
    # ========================================================================

    def test_periodic_check_error_handling(self, doc_manager_with_periodic):
        """Test that periodic check handles errors gracefully."""
        # Mock check to raise exception
        with patch.object(
            doc_manager_with_periodic,
            'check_documentation_freshness',
            side_effect=Exception("Test error")
        ):
            with patch('src.utils.documentation_manager.logger') as mock_logger:
                # Run periodic check (should not crash)
                doc_manager_with_periodic._run_periodic_check(project_id=1)

                # Verify error logged
                mock_logger.error.assert_called()

                # Verify still rescheduled
                assert doc_manager_with_periodic._periodic_timer is not None

        # Cleanup
        doc_manager_with_periodic.stop_periodic_checks()

    # ========================================================================
    # Test 12: Graceful shutdown
    # ========================================================================

    def test_graceful_shutdown(self, doc_manager_with_periodic):
        """Test that stop_periodic_checks ensures graceful shutdown."""
        # Start checks
        doc_manager_with_periodic.start_periodic_checks(project_id=1)
        assert doc_manager_with_periodic._periodic_timer is not None
        assert doc_manager_with_periodic._periodic_timer.is_alive()

        # Stop checks
        doc_manager_with_periodic.stop_periodic_checks()

        # Verify timer cancelled and cleared
        assert doc_manager_with_periodic._periodic_timer is None

        # Verify we can stop again without error (idempotent)
        doc_manager_with_periodic.stop_periodic_checks()
        assert doc_manager_with_periodic._periodic_timer is None
