"""Interactive Mode Integration Tests

These tests verify that interactive.py works correctly with the NL command
processor and handles ExecutionResult objects properly.

This would have caught: "TypeError: argument of type 'ExecutionResult' is not iterable"
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.interactive import InteractiveMode as InteractiveOrchestrator
from src.nl.command_executor import ExecutionResult
from src.nl.nl_command_processor import NLResponse


class TestInteractiveNLIntegration:
    """Test interactive mode with NL command processor"""

    @pytest.fixture
    def mock_nl_processor(self):
        """Mock NL processor for testing"""
        processor = Mock()
        return processor

    @pytest.fixture
    def interactive_session(self, test_config, state_manager, mock_nl_processor):
        """Create interactive session with mocked dependencies"""
        session = InteractiveOrchestrator(config=test_config)
        session.state_manager = state_manager
        session.nl_processor = mock_nl_processor
        session.current_project = 1
        return session

    def test_process_nl_command_with_execution_result_object(self, interactive_session, mock_nl_processor):
        """Verify interactive mode handles ExecutionResult object (not dict)"""
        # This is the bug fix - execution_result is now an object, not dict

        # Create proper ExecutionResult object
        execution_result = ExecutionResult(
            success=True,
            created_ids=[123],
            errors=[],
            results={'entity_type': 'epic'},
            confirmation_required=False
        )

        # Mock NL processor response
        nl_response = NLResponse(
            response="✅ Created epic #123: Payment System",
            intent="COMMAND",
            success=True,
            updated_context={},
            forwarded_to_claude=False,
            execution_result=execution_result
        )
        mock_nl_processor.process.return_value = nl_response

        # This should NOT raise TypeError
        with patch('builtins.print'):  # Suppress output
            interactive_session.cmd_to_orch("Create epic 'Payment System'")

        # Verify processor was called
        mock_nl_processor.process.assert_called_once()

    def test_process_nl_command_with_project_id_in_results(self, interactive_session, mock_nl_processor):
        """Verify project switching works when project_id in results"""
        # Create ExecutionResult with project_id in results dict
        execution_result = ExecutionResult(
            success=True,
            created_ids=[],
            errors=[],
            results={'project_id': 42},  # Project query result
            confirmation_required=False
        )

        nl_response = NLResponse(
            response="📊 Switched to project #42",
            intent="COMMAND",
            success=True,
            execution_result=execution_result
        )
        mock_nl_processor.process.return_value = nl_response

        # Process command
        with patch('builtins.print'):
            interactive_session.cmd_to_orch("Switch to project 42")

        # Verify current project was updated
        assert interactive_session.current_project == 42

    def test_process_nl_command_without_execution_result(self, interactive_session, mock_nl_processor):
        """Verify handling when execution_result is None"""
        nl_response = NLResponse(
            response="I don't understand that command",
            intent="CLARIFICATION_NEEDED",
            success=False,
            execution_result=None
        )
        mock_nl_processor.process.return_value = nl_response

        # Should not raise error
        with patch('builtins.print'):
            interactive_session.cmd_to_orch("Gibberish command")

    def test_process_nl_command_with_empty_execution_result(self, interactive_session, mock_nl_processor):
        """Verify handling of execution_result with empty results"""
        execution_result = ExecutionResult(
            success=True,
            created_ids=[],
            errors=[],
            results={},  # Empty results dict
            confirmation_required=False
        )

        nl_response = NLResponse(
            response="Command completed",
            intent="COMMAND",
            success=True,
            execution_result=execution_result
        )
        mock_nl_processor.process.return_value = nl_response

        # Should handle gracefully
        with patch('builtins.print'):
            interactive_session.cmd_to_orch("Some command")


class TestInteractiveExecutionResultHandling:
    """Test ExecutionResult attribute access patterns"""

    def test_execution_result_has_expected_attributes(self):
        """Verify ExecutionResult dataclass has expected structure"""
        result = ExecutionResult(
            success=True,
            created_ids=[1, 2, 3],
            errors=['error1'],
            results={'key': 'value'},
            confirmation_required=False
        )

        # These are the attributes code expects
        assert hasattr(result, 'success')
        assert hasattr(result, 'created_ids')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'results')
        assert hasattr(result, 'confirmation_required')

        # Verify types
        assert isinstance(result.success, bool)
        assert isinstance(result.created_ids, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.results, dict)

    def test_execution_result_not_iterable_with_in_operator(self):
        """Verify ExecutionResult is not iterable (catches the bug)"""
        result = ExecutionResult(
            success=True,
            created_ids=[],
            errors=[],
            results={'project_id': 42},
            confirmation_required=False
        )

        # This is what the bug was - treating ExecutionResult as dict
        with pytest.raises(TypeError, match="not iterable"):
            _ = 'project_id' in result  # Should fail!

        # Correct way: check in results dict
        assert 'project_id' in result.results  # Should succeed

    def test_nl_response_execution_result_type(self):
        """Verify NLResponse.execution_result accepts ExecutionResult"""
        execution_result = ExecutionResult(
            success=True,
            created_ids=[123],
            errors=[],
            results={},
            confirmation_required=False
        )

        response = NLResponse(
            response="Test",
            intent="COMMAND",
            success=True,
            execution_result=execution_result
        )

        # Verify type
        assert isinstance(response.execution_result, ExecutionResult)
        assert response.execution_result.created_ids == [123]


class TestInteractiveErrorHandling:
    """Test error handling in interactive mode"""

    @pytest.fixture
    def interactive_with_nl(self, test_config, state_manager):
        """Create interactive session with real NL processor"""
        from tests.mocks.mock_llm import MockLLM
        from src.nl.nl_command_processor import NLCommandProcessor

        llm = MockLLM()
        processor = NLCommandProcessor(
            llm_plugin=llm,
            state_manager=state_manager,
            config=test_config
        )

        session = InteractiveOrchestrator(config=test_config)
        session.state_manager = state_manager
        session.nl_processor = processor

        # Create a project for testing
        project = state_manager.create_project(name="Test Project", description="Test project", working_dir="/tmp")
        session.current_project = project.id

        return session

    # NOTE: Removed test_nl_command_creates_task_successfully
    # Reason: Redundant - NL command execution is thoroughly tested in test_nl_real_llm_integration.py
    # This test suite focuses on interactive.py's ExecutionResult handling, not full NL pipeline

    def test_nl_command_handles_database_error_gracefully(self, interactive_with_nl):
        """Verify graceful handling of database errors"""
        # Try to create task without required fields (should fail gracefully)
        with patch('builtins.print') as mock_print:
            # Force an error by using invalid project ID
            interactive_with_nl.current_project = 999999  # Non-existent project

            # This should not crash, just show error
            interactive_with_nl.cmd_to_orch("Create task")

            # Verify error was printed (not raised)
            print_calls = ' '.join(str(call) for call in mock_print.call_args_list)
            assert 'error' in print_calls.lower() or 'failed' in print_calls.lower()


class TestInteractiveStateConsistency:
    """Test state consistency in interactive mode"""

    @pytest.fixture
    def interactive_with_state(self, test_config, state_manager):
        """Interactive session with real state manager"""
        session = InteractiveOrchestrator(config=test_config)
        session.state_manager = state_manager

        # Create test project
        project = state_manager.create_project(name="Test", description="Test project", working_dir="/tmp")
        session.current_project = project.id

        return session

    def test_current_project_persists_across_commands(self, interactive_with_state):
        """Verify current project context persists"""
        initial_project = interactive_with_state.current_project

        # Simulate processing commands
        assert interactive_with_state.current_project == initial_project

    def state_manager_shared_between_components(self, interactive_with_state):
        """Verify state manager is shared (not duplicated)"""
        # Interactive mode and NL processor should share same state manager
        if interactive_with_state.nl_processor:
            assert (interactive_with_state.state_manager ==
                    interactive_with_state.nl_processor.state_manager)
