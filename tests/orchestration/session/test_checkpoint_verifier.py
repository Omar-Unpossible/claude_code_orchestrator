"""Unit tests for CheckpointVerifier.

Tests checkpoint integrity validation before creation and after loading.
Follows TEST_GUIDELINES.md constraints (max 0.5s sleep, 5 threads, 20KB).
"""

import pytest
import subprocess
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from src.orchestration.session.checkpoint_verifier import (
    CheckpointVerifier,
    CheckpointVerificationError,
    CheckpointCorruptedError
)
from src.core.config import Config
from src.core.models import TaskStatus, Task


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)

    # Default config values
    config_data = {
        'orchestrator': {
            'checkpoint': {
                'verification': {
                    'enabled': True,
                    'require_verification': True,
                    'verify_git_clean': True,
                    'verify_tests_passing': True,
                    'verify_coverage': True,
                    'min_coverage': 0.90,
                    'verify_task_boundary': False,
                    'quick_test_timeout': 30,
                    'verify_tests_on_resume': False,
                    'max_age_hours': 168,
                    'warn_on_branch_mismatch': True,
                    'require_file_existence': True
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
def mock_git_manager():
    """Create mock GitManager."""
    git = Mock()
    git.is_clean = Mock(return_value=True)
    git.get_current_branch = Mock(return_value='main')
    return git


@pytest.fixture
def mock_state_manager():
    """Create mock StateManager."""
    state = Mock()
    state.get_current_task = Mock(return_value=None)
    return state


@pytest.fixture
def verifier(mock_config, mock_git_manager, mock_state_manager):
    """Create CheckpointVerifier instance."""
    return CheckpointVerifier(
        config=mock_config,
        git_manager=mock_git_manager,
        state_manager=mock_state_manager
    )


@pytest.fixture
def sample_checkpoint():
    """Create sample checkpoint data."""
    return {
        'checkpoint_id': 'checkpoint_123',
        'timestamp': datetime.now(UTC),
        'git_branch': 'main',
        'files_modified': ['src/file1.py', 'src/file2.py'],
        'context_snapshot': {},
        'metadata': {}
    }


class TestInitialization:
    """Test CheckpointVerifier initialization."""

    def test_initialization_success(self, mock_config, mock_git_manager,
                                   mock_state_manager):
        """Test successful initialization with config loaded."""
        verifier = CheckpointVerifier(
            config=mock_config,
            git_manager=mock_git_manager,
            state_manager=mock_state_manager
        )

        # Check attributes set
        assert verifier.config == mock_config
        assert verifier.git_manager == mock_git_manager
        assert verifier.state_manager == mock_state_manager

        # Check config loaded
        assert verifier._enabled is True
        assert verifier._require_verification is True
        assert verifier._verify_git_clean is True
        assert verifier._verify_tests is True
        assert verifier._verify_coverage is True
        assert verifier._min_coverage == 0.90
        assert verifier._verify_task_boundary is False
        assert verifier._quick_test_timeout == 30


class TestVerifyReady:
    """Test pre-checkpoint verification (verify_ready)."""

    def test_verify_ready_all_pass(self, verifier, mock_git_manager):
        """Test verify_ready passes all checks."""
        # Mock all checks passing
        mock_git_manager.is_clean.return_value = True

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            ready, failed = verifier.verify_ready()

            assert ready is True
            assert failed == []

    def test_verify_ready_git_dirty(self, verifier, mock_git_manager):
        """Test verify_ready fails on dirty git working directory."""
        # Git is dirty
        mock_git_manager.is_clean.return_value = False

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            with pytest.raises(CheckpointVerificationError) as exc_info:
                verifier.verify_ready()

            assert "Uncommitted changes" in str(exc_info.value)

    def test_verify_ready_tests_failing(self, verifier, mock_git_manager):
        """Test verify_ready fails on failing tests."""
        mock_git_manager.is_clean.return_value = True

        with patch.object(verifier, '_run_quick_test') as mock_test:
            # Tests fail (non-zero return code)
            mock_test.return_value = Mock(
                returncode=1,
                stdout=b'FAILED tests/test_foo.py::test_bar',
                stderr=b''
            )

            with pytest.raises(CheckpointVerificationError) as exc_info:
                verifier.verify_ready()

            assert "Tests failing" in str(exc_info.value)

    def test_verify_ready_tests_timeout(self, verifier, mock_git_manager):
        """Test verify_ready fails on test timeout."""
        mock_git_manager.is_clean.return_value = True

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.side_effect = subprocess.TimeoutExpired('pytest', 30)

            with pytest.raises(CheckpointVerificationError) as exc_info:
                verifier.verify_ready()

            assert "timed out" in str(exc_info.value)

    def test_verify_ready_task_boundary_check_disabled(self, verifier, mock_git_manager,
                                                       mock_state_manager, mock_config):
        """Test verify_ready passes when task boundary check disabled (current behavior).

        Note: Task boundary check is disabled until StateManager has current_task tracking.
        """
        # Enable task boundary check (but it's disabled in implementation)
        mock_config._config['orchestrator']['checkpoint']['verification']['verify_task_boundary'] = True

        # Create new verifier with updated config
        verifier = CheckpointVerifier(mock_config, mock_git_manager, mock_state_manager)

        mock_git_manager.is_clean.return_value = True

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            # Should pass (check is disabled)
            ready, failed = verifier.verify_ready()

            assert ready is True
            assert failed == []

    def test_verify_ready_disabled(self, mock_config, mock_git_manager,
                                  mock_state_manager):
        """Test verify_ready passes when verification disabled."""
        # Disable verification
        mock_config._config['orchestrator']['checkpoint']['verification']['enabled'] = False

        verifier = CheckpointVerifier(mock_config, mock_git_manager, mock_state_manager)

        # Should pass without running any checks
        ready, failed = verifier.verify_ready()

        assert ready is True
        assert failed == []

    def test_verify_ready_warn_only_mode(self, mock_config, mock_git_manager,
                                        mock_state_manager):
        """Test verify_ready warns but doesn't raise when require_verification=False."""
        # Enable checks but don't require them
        mock_config._config['orchestrator']['checkpoint']['verification']['require_verification'] = False

        verifier = CheckpointVerifier(mock_config, mock_git_manager, mock_state_manager)

        # Git is dirty (would normally fail)
        mock_git_manager.is_clean.return_value = False

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            # Should NOT raise, just return failure
            ready, failed = verifier.verify_ready()

            assert ready is False
            assert len(failed) > 0
            assert "Uncommitted changes" in failed[0]


class TestVerifyResume:
    """Test post-resume verification (verify_resume)."""

    def test_verify_resume_all_pass(self, verifier, mock_git_manager,
                                   sample_checkpoint):
        """Test verify_resume passes all checks."""
        mock_git_manager.get_current_branch.return_value = 'main'

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            valid, failed = verifier.verify_resume(sample_checkpoint)

            assert valid is True
            assert failed == []

    def test_verify_resume_missing_files(self, verifier, mock_git_manager,
                                        sample_checkpoint):
        """Test verify_resume fails on missing files."""
        mock_git_manager.get_current_branch.return_value = 'main'

        with patch('pathlib.Path.exists') as mock_exists:
            # File1 exists, file2 missing
            mock_exists.side_effect = [True, False]

            with pytest.raises(CheckpointCorruptedError) as exc_info:
                verifier.verify_resume(sample_checkpoint)

            assert "Missing files" in str(exc_info.value)
            assert "src/file2.py" in str(exc_info.value)

    def test_verify_resume_branch_mismatch_warn(self, verifier, mock_git_manager,
                                               sample_checkpoint):
        """Test verify_resume warns on branch mismatch (warn mode)."""
        # Current branch different from checkpoint
        mock_git_manager.get_current_branch.return_value = 'feature-branch'

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            # Should warn but not fail (warn_on_branch_mismatch=True by default)
            valid, failed = verifier.verify_resume(sample_checkpoint)

            # In warn mode, should still pass
            assert valid is True
            assert failed == []

    def test_verify_resume_branch_mismatch_error(self, verifier, mock_git_manager,
                                                mock_config, sample_checkpoint):
        """Test verify_resume fails on branch mismatch (error mode)."""
        # Disable warn mode
        mock_config._config['orchestrator']['checkpoint']['verification']['warn_on_branch_mismatch'] = False

        verifier = CheckpointVerifier(mock_config, mock_git_manager, Mock())

        # Current branch different from checkpoint
        mock_git_manager.get_current_branch.return_value = 'feature-branch'

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            with pytest.raises(CheckpointCorruptedError) as exc_info:
                verifier.verify_resume(sample_checkpoint)

            assert "Branch mismatch" in str(exc_info.value)

    def test_verify_resume_checkpoint_too_old(self, verifier, mock_git_manager,
                                              sample_checkpoint):
        """Test verify_resume fails on old checkpoint (>168 hours)."""
        mock_git_manager.get_current_branch.return_value = 'main'

        # Checkpoint from 8 days ago (>168 hours)
        sample_checkpoint['timestamp'] = datetime.now(UTC) - timedelta(hours=200)

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            with pytest.raises(CheckpointCorruptedError) as exc_info:
                verifier.verify_resume(sample_checkpoint)

            assert "too old" in str(exc_info.value)

    def test_verify_resume_checkpoint_age_acceptable(self, verifier, mock_git_manager,
                                                     sample_checkpoint):
        """Test verify_resume passes on recent checkpoint."""
        mock_git_manager.get_current_branch.return_value = 'main'

        # Checkpoint from 24 hours ago (well within limit)
        sample_checkpoint['timestamp'] = datetime.now(UTC) - timedelta(hours=24)

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            valid, failed = verifier.verify_resume(sample_checkpoint)

            assert valid is True
            assert failed == []

    def test_verify_resume_tests_on_resume(self, verifier, mock_git_manager,
                                          mock_config, sample_checkpoint):
        """Test verify_resume runs tests when verify_tests_on_resume enabled."""
        # Enable test verification on resume
        mock_config._config['orchestrator']['checkpoint']['verification']['verify_tests_on_resume'] = True

        verifier = CheckpointVerifier(mock_config, mock_git_manager, Mock())

        mock_git_manager.get_current_branch.return_value = 'main'

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            with patch.object(verifier, '_run_quick_test') as mock_test:
                # Tests fail
                mock_test.return_value = Mock(returncode=1, stdout=b'', stderr=b'')

                with pytest.raises(CheckpointCorruptedError) as exc_info:
                    verifier.verify_resume(sample_checkpoint)

                assert "Tests failing" in str(exc_info.value)


class TestIndividualChecks:
    """Test individual check methods."""

    def test_check_git_clean_success(self, verifier, mock_git_manager):
        """Test _check_git_clean passes."""
        mock_git_manager.is_clean.return_value = True

        result = verifier._check_git_clean()

        assert result is None  # No error

    def test_check_git_clean_failure(self, verifier, mock_git_manager):
        """Test _check_git_clean detects dirty working directory."""
        mock_git_manager.is_clean.return_value = False

        result = verifier._check_git_clean()

        assert result is not None
        assert "Uncommitted changes" in result

    def test_check_git_clean_exception(self, verifier, mock_git_manager):
        """Test _check_git_clean handles exceptions."""
        mock_git_manager.is_clean.side_effect = Exception("Git error")

        result = verifier._check_git_clean()

        assert result is not None
        assert "Git check error" in result

    def test_check_tests_passing_success(self, verifier):
        """Test _check_tests_passing passes."""
        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            result = verifier._check_tests_passing()

            assert result is None  # No error

    def test_check_tests_passing_failure(self, verifier):
        """Test _check_tests_passing detects failing tests."""
        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=1, stdout=b'FAILED', stderr=b'')

            result = verifier._check_tests_passing()

            assert result is not None
            assert "Tests failing" in result

    def test_check_task_boundary_at_boundary(self, verifier, mock_state_manager):
        """Test _check_task_boundary passes when no task in progress."""
        mock_state_manager.get_current_task.return_value = None

        result = verifier._check_task_boundary()

        assert result is None  # No error

    def test_check_task_boundary_always_passes(self, verifier):
        """Test _check_task_boundary always passes (disabled until StateManager support).

        Note: This check is disabled until StateManager provides current_task tracking.
        """
        result = verifier._check_task_boundary()

        # Should always pass (disabled)
        assert result is None

    def test_check_files_exist_all_present(self, verifier):
        """Test _check_files_exist passes when all files exist."""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            missing = verifier._check_files_exist(['file1.py', 'file2.py'])

            assert missing == []

    def test_check_files_exist_some_missing(self, verifier):
        """Test _check_files_exist detects missing files."""
        with patch('pathlib.Path.exists') as mock_exists:
            # file1 exists, file2 missing
            mock_exists.side_effect = [True, False]

            missing = verifier._check_files_exist(['file1.py', 'file2.py'])

            assert missing == ['file2.py']

    def test_check_branch_match_success(self, verifier, mock_git_manager):
        """Test _check_branch_match passes."""
        mock_git_manager.get_current_branch.return_value = 'main'

        result = verifier._check_branch_match('main')

        assert result is None  # No error

    def test_check_branch_match_failure(self, verifier, mock_git_manager):
        """Test _check_branch_match detects mismatch."""
        mock_git_manager.get_current_branch.return_value = 'feature-branch'

        result = verifier._check_branch_match('main')

        assert result is not None
        assert "mismatch" in result
        assert "main" in result
        assert "feature-branch" in result

    def test_check_checkpoint_age_recent(self, verifier):
        """Test _check_checkpoint_age passes for recent checkpoint."""
        recent_time = datetime.now(UTC) - timedelta(hours=1)

        result = verifier._check_checkpoint_age(recent_time)

        assert result is None  # No error

    def test_check_checkpoint_age_too_old(self, verifier):
        """Test _check_checkpoint_age fails for old checkpoint."""
        old_time = datetime.now(UTC) - timedelta(hours=200)

        result = verifier._check_checkpoint_age(old_time)

        assert result is not None
        assert "too old" in result


class TestQuickTest:
    """Test quick test execution."""

    def test_run_quick_test_execution(self, verifier):
        """Test _run_quick_test runs pytest with correct args."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            result = verifier._run_quick_test()

            # Verify subprocess called with correct args
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == ['pytest', '--quiet', '--maxfail=1']
            assert call_args[1]['capture_output'] is True
            assert call_args[1]['timeout'] == 30

            assert result.returncode == 0
