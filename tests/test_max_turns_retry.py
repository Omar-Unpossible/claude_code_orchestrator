"""Tests for max_turns retry logic (Phase 4, Task 4.5).

Tests auto-retry functionality when Claude Code hits max_turns limit.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import json

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.orchestrator import Orchestrator
from src.orchestration.max_turns_calculator import MaxTurnsCalculator
from src.plugins.exceptions import AgentException
from src.core.exceptions import OrchestratorException


class TestClaudeCodeLocalAgentMaxTurns:
    """Test max_turns handling in ClaudeCodeLocalAgent."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent for testing."""
        agent = ClaudeCodeLocalAgent()
        agent.initialize({'workspace_path': str(tmp_path)})
        return agent

    def test_max_turns_passed_to_cli(self, agent):
        """Test that max_turns is passed to Claude CLI."""
        # Mock _run_claude to capture args
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'type': 'result',
            'subtype': 'success',
            'result': 'Success',
            'usage': {'input_tokens': 100, 'output_tokens': 50}
        })

        with patch.object(agent, '_run_claude', return_value=mock_result) as mock_run:
            agent.send_prompt("Test prompt", context={'max_turns': 15})

            # Verify --max-turns was passed
            args = mock_run.call_args[0][0]
            assert '--max-turns' in args
            assert '15' in args

    def test_max_turns_not_passed_if_not_in_context(self, agent):
        """Test that max_turns is not passed if not in context."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'type': 'result',
            'subtype': 'success',
            'result': 'Success',
            'usage': {'input_tokens': 100, 'output_tokens': 50}
        })

        with patch.object(agent, '_run_claude', return_value=mock_result) as mock_run:
            agent.send_prompt("Test prompt")

            # Verify --max-turns was NOT passed
            args = mock_run.call_args[0][0]
            assert '--max-turns' not in args

    def test_error_max_turns_raises_exception(self, agent):
        """Test that error_max_turns response raises AgentException."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'type': 'result',
            'subtype': 'error_max_turns',
            'is_error': True,
            'result': 'Task exceeded max_turns limit',
            'num_turns': 10,
            'usage': {'input_tokens': 1000, 'output_tokens': 500}
        })

        with patch.object(agent, '_run_claude', return_value=mock_result):
            with pytest.raises(AgentException) as exc_info:
                agent.send_prompt("Test prompt", context={'max_turns': 10})

            # Verify exception details
            assert exc_info.value.context_data.get('subtype') == 'error_max_turns'
            assert exc_info.value.context_data.get('num_turns') == 10
            assert exc_info.value.context_data.get('max_turns') == 10

    def test_error_max_turns_metadata_extracted(self, agent):
        """Test that error_max_turns metadata is properly extracted."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            'type': 'result',
            'subtype': 'error_max_turns',
            'is_error': True,
            'result': 'Hit max turns',
            'num_turns': 12,
            'session_id': 'test-session-123',
            'usage': {'input_tokens': 1500, 'output_tokens': 600}
        })

        with patch.object(agent, '_run_claude', return_value=mock_result):
            try:
                agent.send_prompt("Test", context={'max_turns': 12})
            except AgentException as e:
                # Verify metadata in exception
                assert e.context_data['subtype'] == 'error_max_turns'
                assert e.context_data['num_turns'] == 12
                assert e.context_data['max_turns'] == 12
                assert e.context_data['session_id']


class TestOrchestratorMaxTurnsRetry:
    """Test Orchestrator retry logic for max_turns."""

    @pytest.fixture
    def orchestrator(self, test_config, tmp_path):
        """Create orchestrator for testing."""
        # Configure max_turns settings
        test_config._config['database']['url'] = 'sqlite:///:memory:'
        test_config._config['agent']['local'] = {'workspace_path': str(tmp_path)}
        test_config._config['orchestration'] = {
            'max_turns': {
                'adaptive': True,
                'default': 10,
                'min': 3,
                'max': 30,
                'auto_retry': True,
                'max_retries': 1,
                'retry_multiplier': 2
            }
        }

        orch = Orchestrator(config=test_config)

        # Mock LLM initialization
        with patch.object(orch, '_initialize_llm'):
            orch.initialize()

        # Set up mock components
        orch.llm_interface = Mock()
        orch.agent = Mock()
        orch.agent.session_id = "test-session-123"  # Needs to be string for DB
        orch.agent.get_last_metadata = Mock(return_value={})
        orch.response_validator = Mock()
        orch.quality_controller = Mock()
        orch.decision_engine = Mock()

        # Mock prompt_generator (required for execute_task)
        orch.prompt_generator = Mock()
        orch.prompt_generator.generate_prompt = Mock(return_value="Test prompt")

        return orch

    @pytest.fixture
    def test_project(self, orchestrator, request, tmp_path):
        """Create test project with unique name."""
        project_name = f"Test Project - {request.node.name}"
        return orchestrator.state_manager.create_project(
            name=project_name,
            description="Test",
            working_dir=str(tmp_path)  # Use tmp_path instead of /test
        )

    @pytest.fixture
    def test_task(self, orchestrator, test_project):
        """Create test task."""
        return orchestrator.state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': "Test Task",
                'description': "Test task for max_turns retry",
                'assigned_to': "claude_code"
            }
        )

    def test_retry_on_error_max_turns(self, orchestrator, test_task):
        """Test that task is retried when hitting max_turns limit."""
        # First call: error_max_turns
        # Second call: success
        call_count = 0

        def mock_send_prompt(prompt, context=None):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # First call - hit max_turns
                raise AgentException(
                    "Hit max_turns",
                    context={
                        'subtype': 'error_max_turns',
                        'num_turns': 10,
                        'max_turns': 10
                    }
                )
            else:
                # Second call - success
                return "Task completed successfully"

        orchestrator.agent.send_prompt = mock_send_prompt
        orchestrator.agent.get_last_metadata = Mock(return_value={})

        # Mock other components
        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output') as mock_quality:
                mock_quality.return_value = Mock(
                    overall_score=85.0,
                    gate=Mock(name='PASS'),
                    validation_passed=True
                )

                with patch.object(orchestrator.decision_engine, 'decide_next_action') as mock_decide:
                    mock_decide.return_value = {
                        'action': 'complete',
                        'reason': 'Success',
                        'confidence': 0.95
                    }

                    # Execute task
                    result = orchestrator.execute_task(test_task.id, max_iterations=1)

        # Verify retry occurred
        assert call_count == 2
        assert result['status'] == 'completed'

    def test_max_turns_doubles_on_retry(self, orchestrator, test_task):
        """Test that max_turns is doubled on retry."""
        captured_contexts = []

        def mock_send_prompt(prompt, context=None):
            captured_contexts.append(context.copy() if context else {})

            if len(captured_contexts) == 1:
                # First call - hit max_turns
                raise AgentException(
                    "Hit max_turns",
                    context={
                        'subtype': 'error_max_turns',
                        'num_turns': 10,
                        'max_turns': 10
                    }
                )
            else:
                # Second call - success
                return "Success"

        orchestrator.agent.send_prompt = mock_send_prompt
        orchestrator.agent.get_last_metadata = Mock(return_value={})

        # Mock other components
        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output') as mock_quality:
                mock_quality.return_value = Mock(
                    overall_score=85.0,
                    gate=Mock(name='PASS'),
                    validation_passed=True
                )

                with patch.object(orchestrator.decision_engine, 'decide_next_action') as mock_decide:
                    mock_decide.return_value = {
                        'action': 'complete',
                        'reason': 'Success',
                        'confidence': 0.95
                    }

                    orchestrator.execute_task(test_task.id, max_iterations=1)

        # Verify max_turns doubled
        assert len(captured_contexts) == 2
        assert captured_contexts[0].get('max_turns') == 10  # Initial
        assert captured_contexts[1].get('max_turns') == 20  # Doubled

    def test_max_retries_respected(self, orchestrator, test_task):
        """Test that max_retries limit is respected."""
        call_count = 0

        def mock_send_prompt(prompt, context=None):
            nonlocal call_count
            call_count += 1

            # Always fail with error_max_turns
            raise AgentException(
                "Hit max_turns",
                context={
                    'subtype': 'error_max_turns',
                    'num_turns': 10,
                    'max_turns': context.get('max_turns', 10)
                }
            )

        orchestrator.agent.send_prompt = mock_send_prompt

        # Mock other components (won't be called due to exception)
        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output'):
                with patch.object(orchestrator.decision_engine, 'decide_next_action'):
                    with pytest.raises(AgentException):
                        orchestrator.execute_task(test_task.id, max_iterations=1)

        # Verify max_retries=1 means 2 total attempts
        assert call_count == 2

    def test_upper_bound_enforced_on_retry(self, orchestrator, test_task):
        """Test that upper bound (max: 30) is enforced on retry."""
        # Ensure max_turns_calculator exists
        if not orchestrator.max_turns_calculator:
            orchestrator.max_turns_calculator = MaxTurnsCalculator(
                config=orchestrator.config.get('orchestration.max_turns', {})
            )

        # Set initial max_turns to 20 (doubling would be 40, but max is 30)
        orchestrator.max_turns_calculator.max_turns = 30

        captured_contexts = []

        def mock_send_prompt(prompt, context=None):
            captured_contexts.append(context.copy() if context else {})

            if len(captured_contexts) == 1:
                raise AgentException(
                    "Hit max_turns",
                    context={
                        'subtype': 'error_max_turns',
                        'num_turns': 20,
                        'max_turns': 20
                    }
                )
            else:
                return "Success"

        # Modify task to trigger high max_turns
        test_task.task_type = 'debugging'  # Defaults to 20 turns

        orchestrator.agent.send_prompt = mock_send_prompt
        orchestrator.agent.get_last_metadata = Mock(return_value={})

        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output') as mock_quality:
                mock_quality.return_value = Mock(
                    overall_score=85.0,
                    gate=Mock(name='PASS'),
                    validation_passed=True
                )

                with patch.object(orchestrator.decision_engine, 'decide_next_action') as mock_decide:
                    mock_decide.return_value = {
                        'action': 'complete',
                        'reason': 'Success',
                        'confidence': 0.95
                    }

                    orchestrator.execute_task(test_task.id, max_iterations=1)

        # Verify max_turns capped at 30
        assert captured_contexts[1].get('max_turns') <= 30

    def test_no_retry_when_auto_retry_disabled(self, orchestrator, test_task):
        """Test that retry doesn't occur when auto_retry is disabled."""
        # Disable auto_retry
        orchestrator.config._config['orchestration']['max_turns']['auto_retry'] = False

        call_count = 0

        def mock_send_prompt(prompt, context=None):
            nonlocal call_count
            call_count += 1

            raise AgentException(
                "Hit max_turns",
                context={
                    'subtype': 'error_max_turns',
                    'num_turns': 10,
                    'max_turns': 10
                }
            )

        orchestrator.agent.send_prompt = mock_send_prompt

        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output'):
                with patch.object(orchestrator.decision_engine, 'decide_next_action'):
                    with pytest.raises(AgentException):
                        orchestrator.execute_task(test_task.id, max_iterations=1)

        # Verify no retry (only 1 attempt)
        assert call_count == 1

    def test_other_agent_errors_not_retried(self, orchestrator, test_task):
        """Test that non-max_turns errors are not retried."""
        call_count = 0

        def mock_send_prompt(prompt, context=None):
            nonlocal call_count
            call_count += 1

            # Raise different error
            raise AgentException(
                "Network error",
                context={'subtype': 'network_error'}
            )

        orchestrator.agent.send_prompt = mock_send_prompt

        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output'):
                with patch.object(orchestrator.decision_engine, 'decide_next_action'):
                    with pytest.raises(AgentException):
                        orchestrator.execute_task(test_task.id, max_iterations=1)

        # Verify no retry (only 1 attempt)
        assert call_count == 1


class TestMaxTurnsCalculatorIntegration:
    """Integration tests for MaxTurnsCalculator with retry logic."""

    @pytest.fixture
    def orchestrator(self, test_config, tmp_path):
        """Create orchestrator for testing."""
        test_config._config['database']['url'] = 'sqlite:///:memory:'
        test_config._config['agent']['local'] = {'workspace_path': str(tmp_path)}
        test_config._config['orchestration'] = {
            'max_turns': {
                'adaptive': True,
                'default': 10,
                'by_task_type': {
                    'debugging': 20
                },
                'min': 3,
                'max': 30,
                'auto_retry': True,
                'max_retries': 1,
                'retry_multiplier': 2
            }
        }

        orch = Orchestrator(config=test_config)

        with patch.object(orch, '_initialize_llm'):
            orch.initialize()

        orch.llm_interface = Mock()
        orch.agent = Mock()
        orch.agent.session_id = "test-session-456"  # Needs to be string for DB
        orch.agent.get_last_metadata = Mock(return_value={})
        orch.response_validator = Mock()
        orch.quality_controller = Mock()
        orch.decision_engine = Mock()

        # Mock prompt_generator (required for execute_task)
        orch.prompt_generator = Mock()
        orch.prompt_generator.generate_prompt = Mock(return_value="Test prompt")

        return orch

    @pytest.fixture
    def test_project(self, orchestrator, request, tmp_path):
        """Create test project with unique name."""
        project_name = f"Test Project - {request.node.name}"
        return orchestrator.state_manager.create_project(
            name=project_name,
            description="Test",
            working_dir=str(tmp_path)  # Use tmp_path instead of /test
        )

    def test_calculator_used_for_initial_max_turns(self, orchestrator, test_project):
        """Test that calculator determines initial max_turns."""
        # Create debugging task (should get 20 turns)
        task = orchestrator.state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': "Debug issue",
                'description': "Debug complex issue",
                'task_type': 'debugging',
                'assigned_to': "claude_code"
            }
        )

        captured_context = None

        def mock_send_prompt(prompt, context=None):
            nonlocal captured_context
            captured_context = context
            return "Success"

        orchestrator.agent.send_prompt = mock_send_prompt
        orchestrator.agent.get_last_metadata = Mock(return_value={})

        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output') as mock_quality:
                mock_quality.return_value = Mock(
                    overall_score=85.0,
                    gate=Mock(name='PASS'),
                    validation_passed=True
                )

                with patch.object(orchestrator.decision_engine, 'decide_next_action') as mock_decide:
                    mock_decide.return_value = {
                        'action': 'complete',
                        'reason': 'Success',
                        'confidence': 0.95
                    }

                    orchestrator.execute_task(task.id, max_iterations=1)

        # Verify debugging task got 20 turns
        assert captured_context.get('max_turns') == 20

    def test_full_flow_with_calculator_and_retry(self, orchestrator, test_project):
        """Test complete flow: calculator → error_max_turns → retry with doubled limit."""
        # Create simple task (should get 3 turns)
        task = orchestrator.state_manager.create_task(
            project_id=test_project.id,
            task_data={
                'title': "Simple fix",
                'description': "Fix typo in README",
                'assigned_to': "claude_code"
            }
        )

        captured_contexts = []

        def mock_send_prompt(prompt, context=None):
            captured_contexts.append(context.copy() if context else {})

            if len(captured_contexts) == 1:
                # First attempt with calculated turns
                raise AgentException(
                    "Hit max_turns",
                    context={
                        'subtype': 'error_max_turns',
                        'num_turns': context.get('max_turns'),
                        'max_turns': context.get('max_turns')
                    }
                )
            else:
                return "Success"

        orchestrator.agent.send_prompt = mock_send_prompt
        orchestrator.agent.get_last_metadata = Mock(return_value={})

        with patch.object(orchestrator.response_validator, 'validate_format', return_value=True):
            with patch.object(orchestrator.quality_controller, 'validate_output') as mock_quality:
                mock_quality.return_value = Mock(
                    overall_score=85.0,
                    gate=Mock(name='PASS'),
                    validation_passed=True
                )

                with patch.object(orchestrator.decision_engine, 'decide_next_action') as mock_decide:
                    mock_decide.return_value = {
                        'action': 'complete',
                        'reason': 'Success',
                        'confidence': 0.95
                    }

                    result = orchestrator.execute_task(task.id, max_iterations=1)

        # Verify flow
        assert len(captured_contexts) == 2
        # Simple task should get 3 turns initially
        assert captured_contexts[0].get('max_turns') == 3
        # After retry, doubled to 6
        assert captured_contexts[1].get('max_turns') == 6
        assert result['status'] == 'completed'
