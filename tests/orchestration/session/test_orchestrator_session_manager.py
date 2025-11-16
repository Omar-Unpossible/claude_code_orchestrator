"""Unit tests for OrchestratorSessionManager.

Tests LLM lifecycle management, self-handoff workflow, and session tracking.
Follows TEST_GUIDELINES.md constraints (max 0.5s sleep, 5 threads, 20KB).
"""

import pytest
import time
from datetime import datetime, UTC
from unittest.mock import Mock, MagicMock, patch
from threading import RLock

from src.orchestration.session.orchestrator_session_manager import OrchestratorSessionManager
from src.core.config import Config
from src.core.exceptions import OrchestratorException


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)

    # Default config values
    config_data = {
        'orchestrator': {
            'session_continuity': {
                'self_handoff': {
                    'enabled': True,
                    'trigger_zone': 'red',
                    'require_task_boundary': True,
                    'max_handoffs_per_session': 10
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
def mock_llm_interface():
    """Create mock LocalLLMInterface."""
    llm = Mock()
    llm.disconnect = Mock()
    llm.connect = Mock()
    llm.is_connected = Mock(return_value=True)
    return llm


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock CheckpointManager (ADR-018)."""
    manager = Mock()
    manager.create_checkpoint = Mock(return_value='checkpoint_123')
    manager.load_checkpoint = Mock(return_value={
        'checkpoint_id': 'checkpoint_123',
        'timestamp': datetime.now(UTC),
        'context_snapshot': {
            'working_memory': ['op1', 'op2'],
            'session_memory': 'test session memory',
            'episodic_memory': ['episode1']
        },
        'resume_instructions': {'continue_from': 'step_5'},
        'metadata': {'handoff_count': 0}
    })
    return manager


@pytest.fixture
def mock_context_manager():
    """Create mock OrchestratorContextManager (ADR-018)."""
    context = Mock()
    context.get_usage_percentage = Mock(return_value=87.5)
    context.get_zone = Mock(return_value='red')
    context.load_from_checkpoint = Mock()
    return context


@pytest.fixture
def mock_checkpoint_verifier():
    """Create mock CheckpointVerifier."""
    verifier = Mock()
    verifier.verify_ready = Mock(return_value=(True, []))
    verifier.verify_resume = Mock(return_value=(True, []))
    return verifier


@pytest.fixture
def session_manager(mock_config, mock_llm_interface, mock_checkpoint_manager,
                   mock_context_manager, mock_checkpoint_verifier):
    """Create OrchestratorSessionManager instance."""
    return OrchestratorSessionManager(
        config=mock_config,
        llm_interface=mock_llm_interface,
        checkpoint_manager=mock_checkpoint_manager,
        context_manager=mock_context_manager,
        checkpoint_verifier=mock_checkpoint_verifier
    )


class TestInitialization:
    """Test OrchestratorSessionManager initialization."""

    def test_initialization_success(self, mock_config, mock_llm_interface,
                                   mock_checkpoint_manager, mock_context_manager,
                                   mock_checkpoint_verifier):
        """Test successful initialization with config loaded."""
        manager = OrchestratorSessionManager(
            config=mock_config,
            llm_interface=mock_llm_interface,
            checkpoint_manager=mock_checkpoint_manager,
            context_manager=mock_context_manager,
            checkpoint_verifier=mock_checkpoint_verifier
        )

        # Check attributes set correctly
        assert manager.config == mock_config
        assert manager.llm_interface == mock_llm_interface
        assert manager.checkpoint_manager == mock_checkpoint_manager
        assert manager.context_manager == mock_context_manager
        assert manager.checkpoint_verifier == mock_checkpoint_verifier

        # Check session state
        assert manager.current_session_id is not None
        assert manager.handoff_count == 0
        assert manager.last_checkpoint_id is None

        # Check lock exists
        assert isinstance(manager._lock, type(RLock()))

        # Check config loaded
        assert manager._enabled is True
        assert manager._trigger_zone == 'red'
        assert manager._require_task_boundary is True
        assert manager._max_handoffs == 10


class TestRestartWithCheckpoint:
    """Test restart_orchestrator_with_checkpoint workflow."""

    def test_restart_success_full_workflow(self, session_manager, mock_llm_interface,
                                          mock_checkpoint_manager, mock_context_manager,
                                          mock_checkpoint_verifier):
        """Test complete self-handoff workflow succeeds."""
        # Execute restart
        checkpoint_id = session_manager.restart_orchestrator_with_checkpoint()

        # Verify checkpoint created
        mock_checkpoint_manager.create_checkpoint.assert_called_once()
        call_kwargs = mock_checkpoint_manager.create_checkpoint.call_args[1]
        assert call_kwargs['trigger'] == 'self_handoff_threshold'
        assert 'session_id' in call_kwargs['metadata']
        assert 'handoff_count' in call_kwargs['metadata']

        # Verify LLM disconnect called
        mock_llm_interface.disconnect.assert_called_once()

        # Verify checkpoint loaded
        mock_checkpoint_manager.load_checkpoint.assert_called_once_with('checkpoint_123')

        # Verify LLM reconnect called
        mock_llm_interface.connect.assert_called_once()

        # Verify context injected
        mock_context_manager.load_from_checkpoint.assert_called_once()

        # Verify state updated
        assert session_manager.handoff_count == 1
        assert session_manager.last_checkpoint_id == 'checkpoint_123'
        assert checkpoint_id == 'checkpoint_123'

    def test_restart_with_provided_checkpoint_id(self, session_manager,
                                                 mock_checkpoint_manager,
                                                 mock_checkpoint_verifier):
        """Test restart with pre-existing checkpoint ID."""
        # Restart with specific checkpoint
        checkpoint_id = session_manager.restart_orchestrator_with_checkpoint(
            checkpoint_id='existing_checkpoint_456'
        )

        # Should NOT create new checkpoint
        mock_checkpoint_manager.create_checkpoint.assert_not_called()

        # Should load provided checkpoint
        mock_checkpoint_manager.load_checkpoint.assert_called_once_with('existing_checkpoint_456')

        # Checkpoint verifier should NOT be called (checkpoint already exists)
        # Note: verify_ready only called when creating NEW checkpoint
        assert checkpoint_id == 'existing_checkpoint_456'

    def test_disabled_self_handoff(self, mock_config, mock_llm_interface,
                                  mock_checkpoint_manager, mock_context_manager,
                                  mock_checkpoint_verifier):
        """Test restart skipped when self-handoff disabled."""
        # Disable self-handoff
        mock_config._config['orchestrator']['session_continuity']['self_handoff']['enabled'] = False

        manager = OrchestratorSessionManager(
            config=mock_config,
            llm_interface=mock_llm_interface,
            checkpoint_manager=mock_checkpoint_manager,
            context_manager=mock_context_manager,
            checkpoint_verifier=mock_checkpoint_verifier
        )

        # Attempt restart
        result = manager.restart_orchestrator_with_checkpoint()

        # Should return None and skip restart
        assert result is None
        mock_checkpoint_manager.create_checkpoint.assert_not_called()
        mock_llm_interface.disconnect.assert_not_called()

    def test_max_handoffs_limit_reached(self, session_manager):
        """Test error raised when max handoffs exceeded."""
        # Set handoff count to max
        session_manager.handoff_count = 10

        # Attempt restart (should fail)
        with pytest.raises(OrchestratorException) as exc_info:
            session_manager.restart_orchestrator_with_checkpoint()

        assert "Maximum handoffs reached" in str(exc_info.value)
        assert "10/10" in str(exc_info.value)


class TestLLMLifecycle:
    """Test LLM disconnect/reconnect with retry logic."""

    def test_disconnect_llm_success(self, session_manager, mock_llm_interface):
        """Test LLM disconnect succeeds on first attempt."""
        session_manager._disconnect_llm()

        # Should disconnect once
        mock_llm_interface.disconnect.assert_called_once()

    def test_disconnect_llm_retry_exponential_backoff(self, session_manager,
                                                      mock_llm_interface, fast_time):
        """Test disconnect retries with exponential backoff."""
        # Fail twice, succeed on third
        mock_llm_interface.disconnect.side_effect = [
            ConnectionError("Disconnect failed"),
            ConnectionError("Disconnect failed"),
            None  # Success
        ]

        start = time.time()
        session_manager._disconnect_llm()
        elapsed = time.time() - start

        # Should retry 3 times
        assert mock_llm_interface.disconnect.call_count == 3

        # Should have exponential backoff (1s, 2s)
        # With fast_time, this happens instantly
        assert elapsed < 5.0  # Fast with mock time

    def test_disconnect_llm_failure_after_retries(self, session_manager,
                                                  mock_llm_interface):
        """Test disconnect raises exception after max retries."""
        # Fail all attempts
        mock_llm_interface.disconnect.side_effect = ConnectionError("Permanent failure")

        with pytest.raises(OrchestratorException) as exc_info:
            session_manager._disconnect_llm()

        assert "Failed to disconnect" in str(exc_info.value)
        assert mock_llm_interface.disconnect.call_count == 3

    def test_reconnect_llm_success(self, session_manager, mock_llm_interface):
        """Test LLM reconnect succeeds on first attempt."""
        session_manager._reconnect_llm()

        # Should connect once
        mock_llm_interface.connect.assert_called_once()

        # Should verify connection
        mock_llm_interface.is_connected.assert_called_once()

    def test_reconnect_llm_retry_exponential_backoff(self, session_manager,
                                                     mock_llm_interface, fast_time):
        """Test reconnect retries with exponential backoff."""
        # Fail twice, succeed on third
        mock_llm_interface.connect.side_effect = [
            ConnectionError("Connect failed"),
            ConnectionError("Connect failed"),
            None  # Success
        ]

        start = time.time()
        session_manager._reconnect_llm()
        elapsed = time.time() - start

        # Should retry 3 times
        assert mock_llm_interface.connect.call_count == 3

        # Should have exponential backoff (1s, 2s)
        assert elapsed < 5.0  # Fast with mock time

    def test_reconnect_llm_failure_after_retries(self, session_manager,
                                                 mock_llm_interface):
        """Test reconnect raises exception after max retries."""
        # Fail all attempts
        mock_llm_interface.connect.side_effect = ConnectionError("Permanent failure")

        with pytest.raises(OrchestratorException) as exc_info:
            session_manager._reconnect_llm()

        assert "Failed to reconnect" in str(exc_info.value)
        assert mock_llm_interface.connect.call_count == 3

    def test_reconnect_llm_not_connected_after_connect(self, session_manager,
                                                       mock_llm_interface):
        """Test reconnect fails if is_connected returns False."""
        # Connect succeeds but is_connected returns False
        mock_llm_interface.is_connected.return_value = False

        with pytest.raises(OrchestratorException) as exc_info:
            session_manager._reconnect_llm()

        assert "Failed to reconnect" in str(exc_info.value)


class TestCheckpointContext:
    """Test checkpoint context loading."""

    def test_load_checkpoint_context_success(self, session_manager,
                                            mock_checkpoint_manager):
        """Test loading checkpoint context."""
        context = session_manager._load_checkpoint_context('checkpoint_123')

        # Verify checkpoint loaded
        mock_checkpoint_manager.load_checkpoint.assert_called_once_with('checkpoint_123')

        # Verify context structure
        assert context['checkpoint_id'] == 'checkpoint_123'
        assert 'timestamp' in context
        assert context['working_memory'] == ['op1', 'op2']
        assert context['session_memory'] == 'test session memory'
        assert context['episodic_memory'] == ['episode1']
        assert context['resume_instructions'] == {'continue_from': 'step_5'}
        assert 'metadata' in context


class TestHandoffTracking:
    """Test handoff counter and session tracking."""

    def test_handoff_counter_increments(self, session_manager, mock_checkpoint_verifier):
        """Test handoff counter increments correctly."""
        assert session_manager.get_handoff_count() == 0

        # Perform handoff
        session_manager.restart_orchestrator_with_checkpoint()
        assert session_manager.get_handoff_count() == 1

        # Perform another handoff
        session_manager.restart_orchestrator_with_checkpoint()
        assert session_manager.get_handoff_count() == 2

    def test_session_id_changes_after_handoff(self, session_manager):
        """Test session ID changes after handoff."""
        old_session_id = session_manager.get_current_session_id()

        # Perform handoff
        session_manager.restart_orchestrator_with_checkpoint()

        new_session_id = session_manager.get_current_session_id()
        assert new_session_id != old_session_id

    def test_last_checkpoint_id_tracked(self, session_manager):
        """Test last checkpoint ID tracked correctly."""
        assert session_manager.get_last_checkpoint_id() is None

        # Perform handoff
        checkpoint_id = session_manager.restart_orchestrator_with_checkpoint()

        assert session_manager.get_last_checkpoint_id() == checkpoint_id
        assert session_manager.get_last_checkpoint_id() == 'checkpoint_123'


class TestCheckpointVerification:
    """Test checkpoint verification integration."""

    def test_verification_called_before_checkpoint(self, session_manager,
                                                   mock_checkpoint_verifier):
        """Test verify_ready called before creating checkpoint."""
        session_manager.restart_orchestrator_with_checkpoint()

        # Should verify before checkpoint
        mock_checkpoint_verifier.verify_ready.assert_called_once()

    def test_verification_not_called_with_existing_checkpoint(self, session_manager,
                                                              mock_checkpoint_verifier):
        """Test verify_ready NOT called when using existing checkpoint."""
        session_manager.restart_orchestrator_with_checkpoint(checkpoint_id='existing_123')

        # Should NOT verify (checkpoint already exists)
        mock_checkpoint_verifier.verify_ready.assert_not_called()
