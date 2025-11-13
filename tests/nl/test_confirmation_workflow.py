"""Tests for interactive confirmation workflow."""

import pytest
from unittest.mock import Mock, MagicMock
from src.nl.nl_command_processor import NLCommandProcessor, PendingOperation
from src.nl.types import OperationContext, OperationType, EntityType
from src.core.state import StateManager
import time


class TestConfirmationWorkflow:
    """Test confirmation workflow for UPDATE/DELETE operations."""

    @pytest.fixture
    def processor(self, mock_llm_smart, state_manager):
        """Create NL processor with mocked components."""
        from src.nl.nl_command_processor import NLCommandProcessor
        config = {
            'nl_commands': {
                'enabled': True,
                'require_confirmation_for': ['update', 'delete'],
                'confirmation_timeout': 5
            }
        }
        return NLCommandProcessor(
            llm_plugin=mock_llm_smart,
            state_manager=state_manager,
            config=config
        )

    def test_update_requires_confirmation(self, processor, mock_llm_smart):
        """Test that UPDATE operations require confirmation."""
        # Setup LLM to return proper classifications
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "UPDATE", "confidence": 0.94}',
            '{"entity_type": "project", "confidence": 0.96}',
            '{"identifier": 1, "confidence": 0.98}',
            '{"parameters": {"status": "COMPLETED"}, "confidence": 0.90}'
        ]

        response = processor.process("update project 1 status to completed")

        assert response.intent == 'CONFIRMATION'
        assert not response.success
        assert 'yes' in response.response.lower()
        assert processor.pending_confirmation is not None

    def test_confirmation_yes_executes(self, processor, mock_llm_smart, state_manager):
        """Test that 'yes' executes pending operation."""
        # Create a project first
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        # First create pending operation
        context = OperationContext(
            operation=OperationType.UPDATE,
            entity_type=EntityType.PROJECT,
            identifier=project.id,
            parameters={'status': 'COMPLETED'},
            confidence=0.9,
            raw_input=f'update project {project.id}'
        )
        processor.pending_confirmation = PendingOperation(
            context=context,
            project_id=project.id,
            timestamp=time.time(),
            original_message=f'update project {project.id}'
        )

        # Now confirm
        response = processor.process("yes")

        assert response.success
        assert processor.pending_confirmation is None

    def test_confirmation_no_cancels(self, processor):
        """Test that 'no' cancels pending operation."""
        context = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.PROJECT,
            identifier=1,
            parameters={},
            confidence=0.9,
            raw_input='delete project 1'
        )
        processor.pending_confirmation = PendingOperation(
            context=context,
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        response = processor.process("no")

        assert response.success
        assert 'cancelled' in response.response.lower()
        assert processor.pending_confirmation is None

    def test_confirmation_timeout(self, processor):
        """Test that confirmations timeout."""
        context = OperationContext(
            operation=OperationType.DELETE,
            entity_type=EntityType.PROJECT,
            identifier=1,
            parameters={},
            confidence=0.9,
            raw_input='delete project 1'
        )
        processor.pending_confirmation = PendingOperation(
            context=context,
            project_id=1,
            timestamp=time.time() - 100,  # 100 seconds ago (timeout is 5s)
            original_message='delete project 1'
        )

        response = processor.process("yes")

        assert not response.success
        assert 'timeout' in response.response.lower()
        assert processor.pending_confirmation is None

    def test_new_command_cancels_pending(self, processor, mock_llm_smart):
        """Test that new command implicitly cancels pending confirmation."""
        # Setup pending operation
        processor.pending_confirmation = PendingOperation(
            context=Mock(),
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        # Setup LLM for new command
        mock_llm_smart.generate.side_effect = [
            '{"intent": "COMMAND", "confidence": 0.95}',
            '{"operation_type": "QUERY", "confidence": 0.94}',
            '{"entity_type": "project", "confidence": 0.96}',
            '{"identifier": null, "confidence": 0.98}',
            '{"parameters": {}, "confidence": 0.90}'
        ]

        # Issue new command
        response = processor.process("list projects")

        # Pending confirmation should be cleared
        assert processor.pending_confirmation is None

    @pytest.mark.parametrize("confirmation_word", [
        "yes", "y", "Y", "YES", "confirm", "ok", "proceed"
    ])
    def test_confirmation_variations(self, processor, confirmation_word):
        """Test various confirmation keywords."""
        processor.pending_confirmation = PendingOperation(
            context=Mock(operation=Mock(value='delete'), entity_type=Mock(value='project')),
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        assert processor._is_confirmation_response(confirmation_word)

    @pytest.mark.parametrize("cancellation_word", [
        "no", "n", "N", "NO", "cancel", "abort", "stop"
    ])
    def test_cancellation_variations(self, processor, cancellation_word):
        """Test various cancellation keywords."""
        processor.pending_confirmation = PendingOperation(
            context=Mock(operation=Mock(value='delete'), entity_type=Mock(value='project')),
            project_id=1,
            timestamp=time.time(),
            original_message='delete project 1'
        )

        assert processor._is_cancellation_response(cancellation_word)
