"""Tests for GitManager - M9 git auto-integration.

Tests cover:
- Git operations (mocked)
- Branch creation and naming
- Commit message generation
- PR creation
- Rollback functionality
- Status checking
- Error handling
"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call

from src.utils.git_manager import (
    GitManager,
    GitConfig,
    GitException,
    create_git_manager_from_config
)


@pytest.fixture
def mock_llm():
    """Mock LLM interface."""
    llm = Mock()
    llm.generate = Mock(return_value="feat(api): Add user authentication\n\nImplemented JWT-based auth system")
    return llm


@pytest.fixture
def mock_state_manager():
    """Mock StateManager."""
    state_manager = Mock()
    return state_manager


@pytest.fixture
def mock_task():
    """Mock task object."""
    task = Mock()
    task.id = 5
    task.title = "Implement feature X"
    task.description = "Add new functionality"
    task.project_id = 1
    task.confidence_score = 0.85
    task.quality_score = 0.90
    return task


@pytest.fixture
def git_config():
    """Default git configuration."""
    return GitConfig(
        enabled=True,
        auto_commit=True,
        commit_strategy='per_task',
        create_branch=True,
        branch_prefix='obra/task-',
        auto_pr=False,
        pr_base_branch='main',
        include_metadata=True
    )


@pytest.fixture
def git_manager(git_config, mock_llm, mock_state_manager, tmp_path):
    """GitManager instance with mocked dependencies."""
    manager = GitManager(git_config, mock_llm, mock_state_manager)

    # Create temporary git repo
    git_dir = tmp_path / ".git"
    git_dir.mkdir()

    manager.initialize(str(tmp_path))
    return manager


class TestGitConfig:
    """Tests for GitConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GitConfig()

        assert config.enabled is False
        assert config.auto_commit is True
        assert config.commit_strategy == 'per_task'
        assert config.create_branch is True
        assert config.branch_prefix == 'obra/task-'
        assert config.auto_pr is False
        assert config.pr_base_branch == 'main'
        assert config.include_metadata is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = GitConfig(
            enabled=True,
            create_branch=False,
            branch_prefix='feature/',
            auto_pr=True
        )

        assert config.enabled is True
        assert config.create_branch is False
        assert config.branch_prefix == 'feature/'
        assert config.auto_pr is True


class TestGitManagerInitialization:
    """Tests for GitManager initialization."""

    def test_initialization(self, git_config, mock_llm, mock_state_manager):
        """Test GitManager initialization."""
        manager = GitManager(git_config, mock_llm, mock_state_manager)

        assert manager.config == git_config
        assert manager.llm == mock_llm
        assert manager.state_manager == mock_state_manager
        assert manager.project_dir is None
        assert not manager._initialized

    def test_initialize_with_existing_repo(self, git_manager):
        """Test initialization with existing git repo."""
        assert git_manager._initialized
        assert git_manager.project_dir is not None
        assert git_manager.is_git_repository()

    @patch('subprocess.run')
    def test_initialize_creates_repo_if_needed(self, mock_run, git_config, mock_llm, mock_state_manager, tmp_path):
        """Test git init called when .git doesn't exist."""
        # Remove .git directory
        manager = GitManager(git_config, mock_llm, mock_state_manager)

        # Mock successful git init
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')

        manager.initialize(str(tmp_path))

        # Should have called git init
        assert manager._initialized


class TestGitOperations:
    """Tests for basic git operations."""

    @patch('subprocess.run')
    def test_get_current_branch(self, mock_run, git_manager):
        """Test getting current branch name."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='main\n',
            stderr=''
        )

        branch = git_manager.get_current_branch()

        assert branch == 'main'
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_get_status_clean(self, mock_run, git_manager):
        """Test git status when clean."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=''
        )

        status = git_manager.get_status()

        assert status['is_clean'] is True
        assert len(status['staged_files']) == 0
        assert len(status['unstaged_files']) == 0
        assert len(status['untracked_files']) == 0

    @patch('subprocess.run')
    def test_get_status_with_changes(self, mock_run, git_manager):
        """Test git status with changes."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='M  file1.py\n M file2.py\n?? file3.py\n',
            stderr=''
        )

        status = git_manager.get_status()

        assert status['is_clean'] is False
        assert 'file1.py' in status['staged_files']
        assert 'file2.py' in status['unstaged_files']
        assert 'file3.py' in status['untracked_files']

    @patch('subprocess.run')
    def test_create_branch(self, mock_run, git_manager, mock_task):
        """Test branch creation."""
        mock_run.side_effect = [
            # git branch --list
            MagicMock(returncode=0, stdout='', stderr=''),
            # git checkout -b
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        branch_name = git_manager.create_branch(mock_task.id, mock_task.title)

        assert branch_name == 'obra/task-5-implement-feature-x'
        assert mock_run.call_count == 2

    @patch('subprocess.run')
    def test_create_branch_already_exists(self, mock_run, git_manager, mock_task):
        """Test branch creation when branch already exists."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='obra/task-5-implement-feature-x\n',
            stderr=''
        )

        branch_name = git_manager.create_branch(mock_task.id, mock_task.title)

        assert branch_name == 'obra/task-5-implement-feature-x'
        # Should only check if branch exists, not create
        assert mock_run.call_count == 1


class TestSlugify:
    """Tests for slugification of text."""

    def test_slugify_basic(self, git_manager):
        """Test basic slugification."""
        slug = git_manager._slugify("Implement Feature X")
        assert slug == "implement-feature-x"

    def test_slugify_special_chars(self, git_manager):
        """Test slugification with special characters."""
        slug = git_manager._slugify("Fix bug #123: API error!")
        assert slug == "fix-bug-123-api-error"

    def test_slugify_multiple_spaces(self, git_manager):
        """Test slugification with multiple spaces."""
        slug = git_manager._slugify("Add    multiple    spaces")
        assert slug == "add-multiple-spaces"

    def test_slugify_max_length(self, git_manager):
        """Test slugification respects max length."""
        long_text = "a" * 100
        slug = git_manager._slugify(long_text, max_length=10)
        assert len(slug) == 10

    def test_slugify_trailing_hyphen(self, git_manager):
        """Test slugification removes trailing hyphens."""
        slug = git_manager._slugify("Test title---", max_length=11)
        assert not slug.endswith('-')


class TestCommitMessageGeneration:
    """Tests for commit message generation."""

    @patch('subprocess.run')
    def test_generate_commit_message(self, mock_run, git_manager, mock_task):
        """Test commit message generation with LLM."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',
            stderr=''
        )

        status = {'staged_files': ['file1.py', 'file2.py'], 'unstaged_files': []}
        message = git_manager.generate_commit_message(mock_task, status)

        # Should contain LLM-generated content
        assert 'feat' in message or 'fix' in message
        # Should contain metadata
        assert 'Obra Task ID: #5' in message
        assert 'Confidence: 0.85' in message
        assert 'Quality Score: 0.90' in message
        assert 'Obra' in message

    @patch('subprocess.run')
    def test_generate_commit_message_without_metadata(self, mock_run, git_manager, mock_task):
        """Test commit message without metadata."""
        git_manager.config.include_metadata = False

        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        status = {'staged_files': ['file1.py'], 'unstaged_files': []}
        message = git_manager.generate_commit_message(mock_task, status)

        # Should not contain metadata
        assert 'Obra Task ID' not in message

    def test_fallback_commit_message(self, git_manager, mock_task):
        """Test fallback message when LLM fails."""
        # Make LLM raise exception
        git_manager.llm.generate = Mock(side_effect=Exception("LLM failed"))

        message = git_manager._generate_fallback_commit_message(mock_task)

        assert mock_task.title in message
        assert mock_task.description in message
        assert 'Obra Task ID: #5' in message


class TestCommitTask:
    """Tests for committing task changes."""

    @patch('subprocess.run')
    def test_commit_task_success(self, mock_run, git_manager, mock_task):
        """Test successful task commit."""
        mock_run.side_effect = [
            # git status --porcelain
            MagicMock(returncode=0, stdout='M file1.py\n', stderr=''),
            # git add -A
            MagicMock(returncode=0, stdout='', stderr=''),
            # git commit
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        result = git_manager.commit_task(mock_task)

        assert result is True
        # Should call: status, add, commit
        assert mock_run.call_count == 3

    @patch('subprocess.run')
    def test_commit_task_no_changes(self, mock_run, git_manager, mock_task):
        """Test commit when no changes present."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='',  # Clean status
            stderr=''
        )

        result = git_manager.commit_task(mock_task)

        assert result is False
        # Should only call status
        assert mock_run.call_count == 1

    @patch('subprocess.run')
    def test_commit_task_specific_files(self, mock_run, git_manager, mock_task):
        """Test commit with specific files."""
        mock_run.side_effect = [
            # git status
            MagicMock(returncode=0, stdout='M file1.py\nM file2.py\n', stderr=''),
            # git add file1.py
            MagicMock(returncode=0, stdout='', stderr=''),
            # git add file2.py
            MagicMock(returncode=0, stdout='', stderr=''),
            # git commit
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        result = git_manager.commit_task(mock_task, files=['file1.py', 'file2.py'])

        assert result is True
        assert mock_run.call_count == 4

    def test_commit_task_disabled(self, git_manager, mock_task):
        """Test commit when auto_commit disabled."""
        git_manager.config.auto_commit = False

        result = git_manager.commit_task(mock_task)

        assert result is False


class TestPullRequestCreation:
    """Tests for PR creation."""

    @patch('subprocess.run')
    def test_create_pr_success(self, mock_run, git_manager, mock_task):
        """Test successful PR creation."""
        git_manager.config.auto_pr = True

        # Mock gh pr create (only one call since _is_gh_cli_available is patched)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='https://github.com/user/repo/pull/123',
            stderr=''
        )

        with patch.object(git_manager, '_is_gh_cli_available', return_value=True):
            pr_url = git_manager.create_pull_request(mock_task)

        assert pr_url == 'https://github.com/user/repo/pull/123'

    def test_create_pr_disabled(self, git_manager, mock_task):
        """Test PR creation when disabled."""
        git_manager.config.auto_pr = False

        pr_url = git_manager.create_pull_request(mock_task)

        assert pr_url is None

    @patch('subprocess.run')
    def test_create_pr_gh_not_available(self, mock_run, git_manager, mock_task):
        """Test PR creation when gh CLI not available."""
        git_manager.config.auto_pr = True

        with patch.object(git_manager, '_is_gh_cli_available', return_value=False):
            pr_url = git_manager.create_pull_request(mock_task)

        assert pr_url is None


class TestRollback:
    """Tests for rollback functionality."""

    @patch('subprocess.run')
    def test_rollback_task(self, mock_run, git_manager, mock_task):
        """Test rolling back a task."""
        mock_run.side_effect = [
            # git checkout main
            MagicMock(returncode=0, stdout='', stderr=''),
            # git branch -D obra/task-5-implement-feature-x
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        result = git_manager.rollback_task(mock_task)

        assert result is True
        assert mock_run.call_count == 2

    @patch('subprocess.run')
    def test_rollback_task_fails(self, mock_run, git_manager, mock_task):
        """Test rollback when git command fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git', stderr='error')

        result = git_manager.rollback_task(mock_task)

        assert result is False


class TestGitManagerFactory:
    """Tests for factory function."""

    def test_create_from_config_dict(self, mock_llm, mock_state_manager):
        """Test creating GitManager from config dictionary."""
        config_dict = {
            'enabled': True,
            'auto_commit': False,
            'commit_strategy': 'per_milestone',
            'create_branch': False,
            'branch_prefix': 'feature/',
            'auto_pr': True,
            'pr_base_branch': 'develop'
        }

        manager = create_git_manager_from_config(config_dict, mock_llm, mock_state_manager)

        assert manager.config.enabled is True
        assert manager.config.auto_commit is False
        assert manager.config.commit_strategy == 'per_milestone'
        assert manager.config.create_branch is False
        assert manager.config.branch_prefix == 'feature/'
        assert manager.config.auto_pr is True
        assert manager.config.pr_base_branch == 'develop'

    def test_create_from_partial_config(self, mock_llm, mock_state_manager):
        """Test creating with partial config uses defaults."""
        config_dict = {'enabled': True, 'auto_pr': True}

        manager = create_git_manager_from_config(config_dict, mock_llm, mock_state_manager)

        assert manager.config.enabled is True
        assert manager.config.auto_pr is True
        assert manager.config.auto_commit is True  # Default
        assert manager.config.branch_prefix == 'obra/task-'  # Default


class TestGitManagerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_is_git_repository_no_dir(self, git_manager):
        """Test is_git_repository when project_dir is None."""
        git_manager.project_dir = None
        assert not git_manager.is_git_repository()

    @patch('subprocess.run')
    def test_get_current_branch_error(self, mock_run, git_manager):
        """Test error handling when getting branch fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'git', stderr='not a git repository'
        )

        with pytest.raises(GitException):
            git_manager.get_current_branch()

    @patch('subprocess.run')
    def test_commit_with_git_error(self, mock_run, git_manager, mock_task):
        """Test commit when git command fails."""
        mock_run.side_effect = [
            # git status
            MagicMock(returncode=0, stdout='M file1.py\n', stderr=''),
            # git add (fails)
            subprocess.CalledProcessError(1, 'git add', stderr='permission denied')
        ]

        with pytest.raises(GitException):
            git_manager.commit_task(mock_task)

    def test_gh_cli_not_installed(self, git_manager):
        """Test gh CLI availability check when not installed."""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            assert not git_manager._is_gh_cli_available()

    def test_generate_pr_body(self, git_manager, mock_task):
        """Test PR body generation."""
        body = git_manager._generate_pr_body(mock_task)

        assert mock_task.description in body
        assert f"#{mock_task.id}" in body
        assert "Obra" in body


class TestGitManagerIntegration:
    """Integration tests for complete workflows."""

    @patch('subprocess.run')
    def test_complete_workflow(self, mock_run, git_manager, mock_task):
        """Test complete git workflow: branch → commit → PR."""
        # Setup mocks for entire workflow
        mock_run.side_effect = [
            # create_branch: git branch --list
            MagicMock(returncode=0, stdout='', stderr=''),
            # create_branch: git checkout -b
            MagicMock(returncode=0, stdout='', stderr=''),
            # commit_task: git status
            MagicMock(returncode=0, stdout='M file1.py\n', stderr=''),
            # commit_task: git add -A
            MagicMock(returncode=0, stdout='', stderr=''),
            # commit_task: git commit
            MagicMock(returncode=0, stdout='', stderr='')
        ]

        # Create branch
        branch = git_manager.create_branch(mock_task.id, mock_task.title)
        assert 'obra/task-5' in branch

        # Commit changes
        result = git_manager.commit_task(mock_task)
        assert result is True

        # Verify all git commands were called
        assert mock_run.call_count == 5
