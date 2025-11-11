"""Tests for context window management functionality (Phase 3).

Tests manual token tracking, threshold detection, and session refresh.
"""

import pytest
import uuid
from datetime import datetime, UTC
from unittest.mock import Mock, MagicMock, patch, call

from src.core.state import StateManager
from src.core.models import SessionRecord, ContextWindowUsage, ProjectState
from src.core.config import Config
from src.orchestrator import Orchestrator


class TestContextWindowUsageModel:
    """Test ContextWindowUsage database model."""

    def test_context_window_usage_creation(self):
        """Test creating a context window usage record."""
        state_manager = StateManager(database_url='sqlite:///:memory:')

        # Create project and session
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/test"
        )
        session_id = str(uuid.uuid4())
        session = state_manager.create_session_record(
            session_id=session_id,
            project_id=project.id
        )

        # Create task
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': "Test Task",
                'description': "Test",
                'assigned_to': "claude_code"
            }
        )

        # Add tokens
        tokens_dict = {
            'total_tokens': 1000,
            'input_tokens': 500,
            'cache_creation_tokens': 200,
            'cache_read_tokens': 100,
            'output_tokens': 200
        }

        usage = state_manager.add_session_tokens(
            session_id=session_id,
            task_id=task.id,
            tokens_dict=tokens_dict
        )

        assert usage is not None
        assert usage.session_id == session_id
        assert usage.task_id == task.id
        assert usage.cumulative_tokens == 1000
        assert usage.input_tokens == 500
        assert usage.cache_creation_tokens == 200
        assert usage.cache_read_tokens == 100
        assert usage.output_tokens == 200

    def test_context_window_usage_to_dict(self):
        """Test ContextWindowUsage serialization."""
        usage = ContextWindowUsage()
        usage.id = 1
        usage.session_id = "test-session-123"
        usage.task_id = 5
        usage.cumulative_tokens = 10000
        usage.input_tokens = 5000
        usage.cache_creation_tokens = 2000
        usage.cache_read_tokens = 1000
        usage.output_tokens = 2000
        usage.timestamp = datetime(2025, 1, 1, 12, 0, 0)

        data = usage.to_dict()

        assert data['id'] == 1
        assert data['session_id'] == "test-session-123"
        assert data['task_id'] == 5
        assert data['cumulative_tokens'] == 10000
        assert data['input_tokens'] == 5000


class TestStateManagerTokenTracking:
    """Test StateManager token tracking methods."""

    @pytest.fixture
    def state_manager(self):
        """Create StateManager with in-memory database."""
        sm = StateManager(database_url='sqlite:///:memory:')
        return sm

    @pytest.fixture
    def test_project(self, state_manager):
        """Create test project."""
        return state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/test"
        )

    @pytest.fixture
    def test_session(self, state_manager, test_project):
        """Create test session."""
        session_id = str(uuid.uuid4())
        state_manager.create_session_record(
            session_id=session_id,
            project_id=test_project.id
        )
        return session_id

    @pytest.fixture
    def test_task(self, state_manager, test_project):
        """Create test task."""
        return state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': "Test Task",
            'description': "Test",
            'assigned_to': "claude_code"
            }
        )

    def test_add_session_tokens_first_interaction(self, state_manager, test_session, test_task):
        """Test adding tokens to session (first interaction)."""
        tokens_dict = {
            'total_tokens': 1000,
            'input_tokens': 500,
            'cache_creation_tokens': 200,
            'cache_read_tokens': 100,
            'output_tokens': 200
        }

        usage = state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict
        )

        assert usage.cumulative_tokens == 1000
        assert usage.input_tokens == 500

    def test_add_session_tokens_cumulative(self, state_manager, test_session, test_task):
        """Test cumulative token tracking across multiple interactions."""
        # First interaction
        tokens_dict_1 = {
            'total_tokens': 1000,
            'input_tokens': 500,
            'cache_creation_tokens': 200,
            'cache_read_tokens': 100,
            'output_tokens': 200
        }
        usage1 = state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict_1
        )
        assert usage1.cumulative_tokens == 1000

        # Second interaction
        tokens_dict_2 = {
            'total_tokens': 500,
            'input_tokens': 250,
            'cache_creation_tokens': 100,
            'cache_read_tokens': 50,
            'output_tokens': 100
        }
        usage2 = state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict_2
        )
        assert usage2.cumulative_tokens == 1500

        # Third interaction
        tokens_dict_3 = {
            'total_tokens': 800,
            'input_tokens': 400,
            'cache_creation_tokens': 150,
            'cache_read_tokens': 100,
            'output_tokens': 150
        }
        usage3 = state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict_3
        )
        assert usage3.cumulative_tokens == 2300

    def test_get_session_token_usage(self, state_manager, test_session, test_task):
        """Test retrieving session token usage."""
        # No tokens yet
        usage = state_manager.get_session_token_usage(test_session)
        assert usage == 0

        # Add tokens
        tokens_dict = {
            'total_tokens': 1500,
            'input_tokens': 750,
            'cache_creation_tokens': 300,
            'cache_read_tokens': 150,
            'output_tokens': 300
        }
        state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict
        )

        # Retrieve
        usage = state_manager.get_session_token_usage(test_session)
        assert usage == 1500

    def test_reset_session_tokens(self, state_manager, test_session):
        """Test resetting session tokens (no-op for fresh sessions)."""
        # Should not raise exception
        state_manager.reset_session_tokens(test_session)


class TestOrchestratorThresholdChecks:
    """Test Orchestrator context window threshold checks."""

    @pytest.fixture
    def orchestrator(self, test_config, tmp_path):
        """Create orchestrator for testing."""
        # Modify test_config directly
        test_config._config['database']['url'] = 'sqlite:///:memory:'
        test_config._config['agent']['local'] = {'workspace_path': str(tmp_path)}

        # Configure context window thresholds
        test_config._config['session'] = {
            'context_window': {
                'limit': 10000,  # Small limit for testing
                'thresholds': {
                    'warning': 0.70,
                    'refresh': 0.80,
                    'critical': 0.95
                }
            }
        }

        orch = Orchestrator(config=test_config)

        # Mock LLM initialization to avoid Ollama connection
        with patch.object(orch, '_initialize_llm'):
            orch.initialize()

        # Set up mock LLM interface
        orch.llm_interface = Mock()

        return orch

    @pytest.fixture
    def test_project(self, orchestrator, request):
        """Create test project with unique name."""
        # Use test name to ensure unique project names
        project_name = f"Test Project - {request.node.name}"
        return orchestrator.state_manager.create_project(
            name=project_name,
            description="Test",
            working_dir="/test"
        )

    @pytest.fixture
    def test_session(self, orchestrator, test_project):
        """Create test session."""
        session_id = str(uuid.uuid4())
        orchestrator.state_manager.create_session_record(
            session_id=session_id,
            project_id=test_project.id
        )
        return session_id

    @pytest.fixture
    def test_task(self, orchestrator, test_project):
        """Create test task."""
        return orchestrator.state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': "Test Task",
            'description': "Test",
            'assigned_to': "claude_code"
            }
        )

    def test_context_window_below_warning(self, orchestrator, test_session, test_task):
        """Test context window below warning threshold (no action)."""
        # Add 5000 tokens (50% of 10000 limit)
        tokens_dict = {
            'total_tokens': 5000,
            'input_tokens': 2500,
            'cache_creation_tokens': 1000,
            'cache_read_tokens': 500,
            'output_tokens': 1000
        }
        orchestrator.state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict
        )

        # Check context window
        summary = orchestrator._check_context_window_manual(test_session)

        # Should return None (no action needed)
        assert summary is None

    def test_context_window_warning_threshold(self, orchestrator, test_session, test_task, caplog):
        """Test warning at 70% threshold."""
        # Add 7000 tokens (70% of 10000 limit)
        tokens_dict = {
            'total_tokens': 7000,
            'input_tokens': 3500,
            'cache_creation_tokens': 1400,
            'cache_read_tokens': 700,
            'output_tokens': 1400
        }
        orchestrator.state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict
        )

        # Check context window
        with caplog.at_level('WARNING'):
            summary = orchestrator._check_context_window_manual(test_session)

        # Should log warning but not refresh
        assert summary is None
        assert "approaching refresh threshold" in caplog.text.lower()

    def test_context_window_refresh_threshold(self, orchestrator, test_session, test_task):
        """Test auto-refresh at 80% threshold."""
        # Add 8000 tokens (80% of 10000 limit)
        tokens_dict = {
            'total_tokens': 8000,
            'input_tokens': 4000,
            'cache_creation_tokens': 1600,
            'cache_read_tokens': 800,
            'output_tokens': 1600
        }
        orchestrator.state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict
        )

        # Set up orchestrator state
        orchestrator.agent = Mock()
        orchestrator.agent.session_id = test_session
        orchestrator._current_epic_id = 5

        # Mock LLM for summary generation
        with patch.object(orchestrator.llm_interface, 'generate', return_value="Session summary"):
            summary = orchestrator._check_context_window_manual(test_session)

        # Should return summary (session refreshed)
        assert summary is not None
        assert "Session summary" in summary

        # Verify old session marked as refreshed
        old_session = orchestrator.state_manager.get_session_record(test_session)
        assert old_session.status == 'refreshed'
        assert old_session.summary is not None

        # Verify agent has new session ID
        assert orchestrator.agent.session_id != test_session

    def test_context_window_critical_threshold(self, orchestrator, test_session, test_task, caplog):
        """Test emergency refresh at 95% threshold."""
        # Add 9500 tokens (95% of 10000 limit)
        tokens_dict = {
            'total_tokens': 9500,
            'input_tokens': 4750,
            'cache_creation_tokens': 1900,
            'cache_read_tokens': 950,
            'output_tokens': 1900
        }
        orchestrator.state_manager.add_session_tokens(
            session_id=test_session,
            task_id=test_task.id,
            tokens_dict=tokens_dict
        )

        # Set up orchestrator state
        orchestrator.agent = Mock()
        orchestrator.agent.session_id = test_session
        orchestrator._current_epic_id = 5

        # Mock LLM for summary generation
        with caplog.at_level('ERROR'):
            with patch.object(orchestrator.llm_interface, 'generate', return_value="Emergency summary"):
                summary = orchestrator._check_context_window_manual(test_session)

        # Should return summary and log error
        assert summary is not None
        assert "CRITICAL" in caplog.text

    def test_context_window_check_error_handling(self, orchestrator, test_session):
        """Test error handling in context window check."""
        # Cause error by using invalid session
        summary = orchestrator._check_context_window_manual("invalid-session-id")

        # Should return None (error caught)
        assert summary is None


class TestSessionRefreshMechanism:
    """Test session refresh mechanism."""

    @pytest.fixture
    def orchestrator(self, test_config, tmp_path):
        """Create orchestrator for testing."""
        # Modify test_config directly
        test_config._config['database']['url'] = 'sqlite:///:memory:'
        test_config._config['agent']['local'] = {'workspace_path': str(tmp_path)}

        orch = Orchestrator(config=test_config)

        # Mock LLM initialization to avoid Ollama connection
        with patch.object(orch, '_initialize_llm'):
            orch.initialize()

        # Set up mock LLM interface
        orch.llm_interface = Mock()

        return orch

    @pytest.fixture
    def test_project(self, orchestrator, request):
        """Create test project with unique name."""
        # Use test name to ensure unique project names
        project_name = f"Test Project - {request.node.name}"
        return orchestrator.state_manager.create_project(
            name=project_name,
            description="Test",
            working_dir="/test"
        )

    def test_refresh_session_with_summary(self, orchestrator, test_project):
        """Test session refresh creates new session with summary."""
        # Create initial session
        old_session_id = str(uuid.uuid4())
        orchestrator.state_manager.create_session_record(
            session_id=old_session_id,
            project_id=test_project.id,
            milestone_id=5
        )

        # Create some interactions
        task = orchestrator.state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': "Test Task",
            'description': "Test",
            'assigned_to': "claude_code"
            }
        )

        # Set up orchestrator state
        orchestrator.agent = Mock()
        orchestrator.agent.session_id = old_session_id
        orchestrator._current_epic_id = 5

        # Mock LLM for summary
        with patch.object(orchestrator.llm_interface, 'generate', return_value="Detailed summary"):
            new_session_id, summary = orchestrator._refresh_session_with_summary()

        # Verify new session created
        assert new_session_id != old_session_id
        assert summary == "Detailed summary"

        # Verify old session updated
        old_session = orchestrator.state_manager.get_session_record(old_session_id)
        assert old_session.status == 'refreshed'
        assert old_session.summary == "Detailed summary"
        assert old_session.ended_at is not None

        # Verify new session exists
        new_session = orchestrator.state_manager.get_session_record(new_session_id)
        assert new_session is not None
        assert new_session.status == 'active'
        assert new_session.milestone_id == 5

        # Verify agent updated
        assert orchestrator.agent.session_id == new_session_id


class TestContextWindowIntegration:
    """Integration tests for context window management."""

    @pytest.fixture
    def orchestrator(self, test_config, tmp_path):
        """Create orchestrator for testing."""
        # Modify test_config directly
        test_config._config['database']['url'] = 'sqlite:///:memory:'
        test_config._config['agent']['local'] = {'workspace_path': str(tmp_path)}

        # Small limit for testing
        test_config._config['session'] = {
            'context_window': {
                'limit': 5000,
                'thresholds': {
                    'warning': 0.70,
                    'refresh': 0.80,
                    'critical': 0.95
                }
            }
        }

        orch = Orchestrator(config=test_config)

        # Mock LLM initialization to avoid Ollama connection
        with patch.object(orch, '_initialize_llm'):
            orch.initialize()

        # Set up mock LLM interface
        orch.llm_interface = Mock()

        return orch

    @pytest.fixture
    def test_project(self, orchestrator, request):
        """Create test project with unique name."""
        # Use test name to ensure unique project names
        project_name = f"Test Project - {request.node.name}"
        return orchestrator.state_manager.create_project(
            name=project_name,
            description="Test",
            working_dir="/test"
        )

    def test_full_context_window_flow(self, orchestrator, test_project):
        """Test complete flow: track tokens → threshold → refresh → continue."""
        # Create task
        task = orchestrator.state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': "Test Task",
            'description': "Test",
            'assigned_to': "claude_code"
            }
        )

        # Start session
        session_id = str(uuid.uuid4())
        orchestrator.state_manager.create_session_record(
            session_id=session_id,
            project_id=test_project.id,
            milestone_id=1
        )

        # Set up orchestrator state
        orchestrator.agent = Mock()
        orchestrator.agent.session_id = session_id
        orchestrator.agent.use_session_persistence = True
        orchestrator._current_epic_id = 1

        # Simulate multiple interactions approaching limit
        # Interaction 1: 2000 tokens (40%)
        tokens_dict_1 = {'total_tokens': 2000, 'input_tokens': 1000, 'cache_creation_tokens': 400, 'cache_read_tokens': 200, 'output_tokens': 400}
        orchestrator.state_manager.add_session_tokens(session_id=session_id, task_id=task.id, tokens_dict=tokens_dict_1)
        summary = orchestrator._check_context_window_manual(session_id)
        assert summary is None  # No action

        # Interaction 2: 1500 tokens (cumulative 70%)
        tokens_dict_2 = {'total_tokens': 1500, 'input_tokens': 750, 'cache_creation_tokens': 300, 'cache_read_tokens': 150, 'output_tokens': 300}
        orchestrator.state_manager.add_session_tokens(session_id=session_id, task_id=task.id, tokens_dict=tokens_dict_2)
        summary = orchestrator._check_context_window_manual(session_id)
        assert summary is None  # Warning logged, no refresh

        # Interaction 3: 600 tokens (cumulative 82% - triggers refresh)
        tokens_dict_3 = {'total_tokens': 600, 'input_tokens': 300, 'cache_creation_tokens': 120, 'cache_read_tokens': 60, 'output_tokens': 120}
        orchestrator.state_manager.add_session_tokens(session_id=session_id, task_id=task.id, tokens_dict=tokens_dict_3)

        # Mock LLM for summary
        with patch.object(orchestrator.llm_interface, 'generate', return_value="Context summary"):
            summary = orchestrator._check_context_window_manual(session_id)

        # Should trigger refresh
        assert summary is not None
        assert "Context summary" in summary

        # Verify session was refreshed
        old_session = orchestrator.state_manager.get_session_record(session_id)
        assert old_session.status == 'refreshed'

        # Verify new session created
        new_session_id = orchestrator.agent.session_id
        assert new_session_id != session_id
        new_session = orchestrator.state_manager.get_session_record(new_session_id)
        assert new_session.status == 'active'

        # Verify token tracking reset for new session
        new_usage = orchestrator.state_manager.get_session_token_usage(new_session_id)
        assert new_usage == 0
