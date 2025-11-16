"""Integration tests for session continuity (ADR-019).

Tests multi-component interactions for self-handoff workflow.
Follows TEST_GUIDELINES.md constraints (max 0.5s sleep, 5 threads, 20KB).
"""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from src.orchestration.session.orchestrator_session_manager import OrchestratorSessionManager
from src.orchestration.session.checkpoint_verifier import (
    CheckpointVerifier,
    CheckpointVerificationError,
    CheckpointCorruptedError
)
from src.core.config import Config
from src.core.exceptions import OrchestratorException


@pytest.fixture
def integrated_config():
    """Create integrated config for session continuity."""
    config = Mock(spec=Config)

    config_data = {
        'orchestrator': {
            'session_continuity': {
                'self_handoff': {
                    'enabled': True,
                    'trigger_zone': 'red',
                    'require_task_boundary': True,
                    'max_handoffs_per_session': 10
                }
            },
            'checkpoint': {
                'verification': {
                    'enabled': True,
                    'require_verification': True,
                    'verify_git_clean': True,
                    'verify_tests_passing': True,
                    'verify_coverage': False,  # Disabled for integration tests
                    'verify_task_boundary': False,
                    'verify_tests_on_resume': False,
                    'max_age_hours': 168
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
def mock_components():
    """Create all mock components needed for integration."""
    llm = Mock()
    llm.disconnect = Mock()
    llm.connect = Mock()
    llm.is_connected = Mock(return_value=True)

    checkpoint_mgr = Mock()
    checkpoint_mgr.create_checkpoint = Mock(return_value='ckpt_001')
    checkpoint_mgr.load_checkpoint = Mock(return_value={
        'checkpoint_id': 'ckpt_001',
        'timestamp': datetime.now(UTC),
        'git_branch': 'main',
        'files_modified': ['src/file1.py'],
        'context_snapshot': {
            'working_memory': ['op1', 'op2'],
            'session_memory': 'memory',
            'episodic_memory': []
        },
        'resume_instructions': {},
        'metadata': {}
    })

    context_mgr = Mock()
    context_mgr.get_usage_percentage = Mock(return_value=87.5)
    context_mgr.get_zone = Mock(return_value='red')
    context_mgr.load_from_checkpoint = Mock()

    git_mgr = Mock()
    git_mgr.is_clean = Mock(return_value=True)
    git_mgr.get_current_branch = Mock(return_value='main')

    state_mgr = Mock()

    return {
        'llm': llm,
        'checkpoint_mgr': checkpoint_mgr,
        'context_mgr': context_mgr,
        'git_mgr': git_mgr,
        'state_mgr': state_mgr
    }


class TestSelfHandoffWorkflow:
    """Test complete self-handoff workflow."""

    def test_successful_self_handoff_during_task_execution(self, integrated_config,
                                                           mock_components):
        """Test self-handoff triggered during task execution (context >85%)."""
        # Create verifier and session manager
        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        # Mock quick test to pass
        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            # Trigger handoff
            checkpoint_id = session_mgr.restart_orchestrator_with_checkpoint()

            # Verify complete workflow
            assert checkpoint_id == 'ckpt_001'
            assert session_mgr.handoff_count == 1

            # Verify checkpoint created
            mock_components['checkpoint_mgr'].create_checkpoint.assert_called_once()

            # Verify LLM lifecycle
            mock_components['llm'].disconnect.assert_called_once()
            mock_components['llm'].connect.assert_called_once()

            # Verify context loaded
            mock_components['context_mgr'].load_from_checkpoint.assert_called_once()

    def test_multiple_handoffs_in_session(self, integrated_config, mock_components):
        """Test multiple consecutive handoffs (3 handoffs)."""
        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        # Mock incrementing checkpoint IDs
        mock_components['checkpoint_mgr'].create_checkpoint.side_effect = [
            'ckpt_001', 'ckpt_002', 'ckpt_003'
        ]

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            # Perform 3 handoffs
            for i in range(3):
                checkpoint_id = session_mgr.restart_orchestrator_with_checkpoint()
                assert checkpoint_id == f'ckpt_00{i+1}'
                assert session_mgr.handoff_count == i + 1

            # Verify 3 checkpoints created
            assert mock_components['checkpoint_mgr'].create_checkpoint.call_count == 3

            # Verify 3 disconnect/connect cycles
            assert mock_components['llm'].disconnect.call_count == 3
            assert mock_components['llm'].connect.call_count == 3

    def test_handoff_with_git_dirty_warning(self, integrated_config, mock_components):
        """Test handoff proceeds with warning when git dirty (require_verification=True)."""
        # Set git dirty
        mock_components['git_mgr'].is_clean.return_value = False

        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            # Should raise CheckpointVerificationError (require_verification=True)
            with pytest.raises(CheckpointVerificationError) as exc_info:
                session_mgr.restart_orchestrator_with_checkpoint()

            assert "Uncommitted changes" in str(exc_info.value)

            # Checkpoint should NOT be created
            mock_components['checkpoint_mgr'].create_checkpoint.assert_not_called()


class TestCheckpointResume:
    """Test checkpoint resume workflow."""

    def test_checkpoint_resume_with_missing_files(self, integrated_config, mock_components):
        """Test resume fails when files from checkpoint missing."""
        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        # Mock file missing
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False  # File missing

            checkpoint = {
                'checkpoint_id': 'ckpt_001',
                'timestamp': datetime.now(UTC),
                'git_branch': 'main',
                'files_modified': ['src/missing_file.py']
            }

            # Should raise CheckpointCorruptedError
            with pytest.raises(CheckpointCorruptedError) as exc_info:
                verifier.verify_resume(checkpoint)

            assert "Missing files" in str(exc_info.value)

    def test_checkpoint_resume_with_branch_mismatch(self, integrated_config, mock_components):
        """Test resume warns on branch mismatch."""
        # Current branch different from checkpoint
        mock_components['git_mgr'].get_current_branch.return_value = 'feature-branch'

        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            checkpoint = {
                'checkpoint_id': 'ckpt_001',
                'timestamp': datetime.now(UTC),
                'git_branch': 'main',
                'files_modified': ['src/file1.py']
            }

            # Should warn but pass (warn_on_branch_mismatch=True by default)
            valid, failed = verifier.verify_resume(checkpoint)

            assert valid is True
            assert failed == []

    def test_checkpoint_resume_checkpoint_too_old(self, integrated_config, mock_components):
        """Test resume fails when checkpoint too old (>168 hours)."""
        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = True

            # Checkpoint from 200 hours ago
            checkpoint = {
                'checkpoint_id': 'ckpt_001',
                'timestamp': datetime.now(UTC) - timedelta(hours=200),
                'git_branch': 'main',
                'files_modified': ['src/file1.py']
            }

            # Should raise CheckpointCorruptedError
            with pytest.raises(CheckpointCorruptedError) as exc_info:
                verifier.verify_resume(checkpoint)

            assert "too old" in str(exc_info.value)


class TestHandoffCounterTracking:
    """Test handoff counter and session tracking."""

    def test_handoff_counter_and_session_tracking(self, integrated_config, mock_components):
        """Test handoff counter increments and session ID changes."""
        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        # Track initial state
        initial_session_id = session_mgr.get_current_session_id()
        assert session_mgr.get_handoff_count() == 0
        assert session_mgr.get_last_checkpoint_id() is None

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            # First handoff
            checkpoint_id = session_mgr.restart_orchestrator_with_checkpoint()

            assert session_mgr.get_handoff_count() == 1
            assert session_mgr.get_last_checkpoint_id() == checkpoint_id
            assert session_mgr.get_current_session_id() != initial_session_id

    def test_max_handoffs_limit_enforcement(self, integrated_config, mock_components):
        """Test error raised when max handoffs limit reached."""
        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        # Manually set to max limit
        session_mgr.handoff_count = 10

        # Attempt handoff (should fail)
        with pytest.raises(OrchestratorException) as exc_info:
            session_mgr.restart_orchestrator_with_checkpoint()

        assert "Maximum handoffs reached" in str(exc_info.value)
        assert "10/10" in str(exc_info.value)


class TestGracefulDegradation:
    """Test graceful degradation when components unavailable."""

    def test_disabled_self_handoff(self, integrated_config, mock_components):
        """Test self-handoff skipped when disabled in config."""
        # Disable self-handoff
        integrated_config._config['orchestrator']['session_continuity']['self_handoff']['enabled'] = False

        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        # Attempt handoff
        result = session_mgr.restart_orchestrator_with_checkpoint()

        # Should return None and skip
        assert result is None
        mock_components['checkpoint_mgr'].create_checkpoint.assert_not_called()
        mock_components['llm'].disconnect.assert_not_called()

    def test_disabled_verification(self, integrated_config, mock_components):
        """Test verification skipped when disabled."""
        # Disable verification
        integrated_config._config['orchestrator']['checkpoint']['verification']['enabled'] = False

        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        # Git is dirty (would normally fail)
        mock_components['git_mgr'].is_clean.return_value = False

        # Should pass (verification disabled)
        ready, failed = verifier.verify_ready()

        assert ready is True
        assert failed == []


class TestErrorRecovery:
    """Test error recovery scenarios."""

    def test_llm_reconnect_failure_recovery(self, integrated_config, mock_components):
        """Test handling of LLM reconnect failure."""
        # LLM connect fails
        mock_components['llm'].connect.side_effect = ConnectionError("Connection refused")

        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            # Should raise OrchestratorException after retries
            with pytest.raises(OrchestratorException) as exc_info:
                session_mgr.restart_orchestrator_with_checkpoint()

            assert "Failed to reconnect" in str(exc_info.value)

            # Verify retry attempts (3 attempts)
            assert mock_components['llm'].connect.call_count == 3

    def test_checkpoint_verification_blocks_handoff(self, integrated_config, mock_components):
        """Test verification failure blocks handoff (require_verification=True)."""
        # Tests failing
        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        with patch.object(verifier, '_run_quick_test') as mock_test:
            # Tests fail
            mock_test.return_value = Mock(returncode=1, stdout=b'FAILED', stderr=b'')

            # Should raise CheckpointVerificationError
            with pytest.raises(CheckpointVerificationError) as exc_info:
                session_mgr.restart_orchestrator_with_checkpoint()

            assert "Tests failing" in str(exc_info.value)

            # Checkpoint should NOT be created
            mock_components['checkpoint_mgr'].create_checkpoint.assert_not_called()


class TestConfigurationOptions:
    """Test various configuration options."""

    def test_warn_only_verification_mode(self, integrated_config, mock_components):
        """Test verification in warn-only mode (require_verification=False)."""
        # Set warn-only mode
        integrated_config._config['orchestrator']['checkpoint']['verification']['require_verification'] = False

        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        # Git is dirty (would normally fail)
        mock_components['git_mgr'].is_clean.return_value = False

        # Should NOT raise, just return failure
        ready, failed = verifier.verify_ready()

        assert ready is False
        assert len(failed) > 0
        assert "Uncommitted changes" in failed[0]

    def test_custom_max_handoffs_limit(self, integrated_config, mock_components):
        """Test custom max handoffs limit."""
        # Set custom limit
        integrated_config._config['orchestrator']['session_continuity']['self_handoff']['max_handoffs_per_session'] = 3

        verifier = CheckpointVerifier(
            integrated_config,
            mock_components['git_mgr'],
            mock_components['state_mgr']
        )

        session_mgr = OrchestratorSessionManager(
            integrated_config,
            mock_components['llm'],
            mock_components['checkpoint_mgr'],
            mock_components['context_mgr'],
            verifier
        )

        # Perform 3 handoffs (should succeed)
        mock_components['checkpoint_mgr'].create_checkpoint.side_effect = [
            'ckpt_001', 'ckpt_002', 'ckpt_003'
        ]

        with patch.object(verifier, '_run_quick_test') as mock_test:
            mock_test.return_value = Mock(returncode=0, stdout=b'', stderr=b'')

            for i in range(3):
                session_mgr.restart_orchestrator_with_checkpoint()

            # 4th handoff should fail
            with pytest.raises(OrchestratorException) as exc_info:
                session_mgr.restart_orchestrator_with_checkpoint()

            assert "3/3" in str(exc_info.value)
