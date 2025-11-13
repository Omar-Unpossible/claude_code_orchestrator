"""Tests for Phase 3: Error Recovery & Polish."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.nl.nl_command_processor import NLCommandProcessor
from src.nl.response_formatter import ResponseFormatter
from src.nl.command_executor import ExecutionResult
from src.nl.types import OperationType, EntityType
import time


class TestErrorMessages:
    """Test enhanced error messages with recovery suggestions."""

    @pytest.fixture
    def formatter(self):
        """Create ResponseFormatter."""
        return ResponseFormatter()

    def test_entity_not_found_error(self, formatter):
        """Test error message for entity not found."""
        result = ExecutionResult(
            success=False,
            errors=['Epic 99 not found'],
            results={'entity_type': 'epic'}
        )

        response = formatter._format_error(result)

        assert 'not found' in response.lower()
        # Should suggest listing epics
        assert 'list epics' in response.lower()

    def test_missing_required_field_error(self, formatter):
        """Test error message for missing required field."""
        result = ExecutionResult(
            success=False,
            errors=['Epic requires epic_id'],
            results={'entity_type': 'story'}
        )

        response = formatter._format_error(result)

        assert 'in epic' in response.lower()

    def test_circular_dependency_error(self, formatter):
        """Test error message for circular dependency."""
        result = ExecutionResult(
            success=False,
            errors=['Circular dependency detected'],
            results={}
        )

        response = formatter._format_error(result)

        assert 'circular' in response.lower()

    def test_priority_validation_error(self, formatter):
        """Test error message for invalid priority."""
        result = ExecutionResult(
            success=False,
            errors=['Invalid priority value'],
            results={}
        )

        response = formatter._format_error(result)

        assert 'priority must be' in response.lower()

    def test_format_error_with_examples(self, formatter):
        """Test that examples are shown for errors."""
        result = ExecutionResult(
            success=False,
            errors=['Failed to create epic'],
            results={'entity_type': 'epic'}
        )

        response = formatter.format_error_with_examples(result, 'create')

        assert 'Examples:' in response
        assert 'create epic' in response


class TestRetryLogic:
    """Test automatic retry for transient failures."""

    @pytest.fixture
    def processor(self, mock_llm_smart, state_manager):
        """Create NL processor."""
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

    def test_is_retryable_detects_transient_errors(self, processor):
        """Test that transient errors are detected as retryable."""
        # Timeout error
        result = ExecutionResult(
            success=False,
            errors=['Connection timeout occurred'],
            results={}
        )
        assert processor._is_retryable(result, ['timeout', 'connection'])

        # Lock error
        result = ExecutionResult(
            success=False,
            errors=['Database lock detected'],
            results={}
        )
        assert processor._is_retryable(result, ['lock', 'busy'])

    def test_is_retryable_rejects_permanent_errors(self, processor):
        """Test that permanent errors are not retryable."""
        result = ExecutionResult(
            success=False,
            errors=['Project not found'],
            results={}
        )
        assert not processor._is_retryable(result, ['timeout', 'connection'])

    def test_execute_with_retry_succeeds_first_attempt(self, processor, state_manager):
        """Test that successful execution on first attempt doesn't retry."""
        from src.nl.types import OperationContext

        # Create project
        project = state_manager.create_project(
            name="Test Project",
            description="Test",
            working_dir="/tmp/test"
        )

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT,
            identifier=None,
            parameters={},
            confidence=0.9,
            raw_input='list projects'
        )

        # Should succeed on first attempt
        result = processor._execute_with_retry(context, project.id, confirmed=False, max_retries=3)

        assert result.success

    def test_execute_with_retry_no_retry_on_success(self, processor, mock_llm_smart):
        """Test that successful operations are not retried."""
        from src.nl.types import OperationContext

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_type=EntityType.PROJECT,
            identifier=None,
            parameters={},
            confidence=0.9,
            raw_input='list projects'
        )

        with patch.object(processor.command_executor, 'execute') as mock_execute:
            mock_execute.return_value = ExecutionResult(
                success=True,
                created_ids=[],
                results={}
            )

            result = processor._execute_with_retry(context, 1, max_retries=3)

            # Should only call execute once (no retries)
            assert mock_execute.call_count == 1
            assert result.success


class TestHelpSystem:
    """Test help command functionality."""

    @pytest.fixture
    def processor(self, mock_llm_smart, state_manager):
        """Create NL processor."""
        config = {'nl_commands': {'enabled': True}}
        return NLCommandProcessor(
            llm_plugin=mock_llm_smart,
            state_manager=state_manager,
            config=config
        )

    def test_general_help(self, processor):
        """Test general help command."""
        response = processor.process("help")

        assert response.success
        assert response.intent == 'HELP'
        assert 'Creating Entities:' in response.response
        assert 'Querying:' in response.response
        assert 'Updating:' in response.response
        assert 'Deleting:' in response.response

    def test_help_variations(self, processor):
        """Test various help keywords."""
        # Test '?'
        response = processor.process("?")
        assert response.success
        assert response.intent == 'HELP'

        # Test 'help me'
        response = processor.process("help me")
        assert response.success
        assert response.intent == 'HELP'

    def test_entity_specific_help_project(self, processor):
        """Test project-specific help."""
        response = processor.process("help project")

        assert response.success
        assert response.intent == 'HELP'
        assert 'Project Commands' in response.response
        assert 'create project' in response.response

    def test_entity_specific_help_epic(self, processor):
        """Test epic-specific help."""
        response = processor.process("help epic")

        assert response.success
        assert response.intent == 'HELP'
        assert 'Epic Commands' in response.response
        assert 'create epic' in response.response

    def test_entity_specific_help_story(self, processor):
        """Test story-specific help."""
        response = processor.process("help story")

        assert response.success
        assert response.intent == 'HELP'
        assert 'Story Commands' in response.response

    def test_entity_specific_help_task(self, processor):
        """Test task-specific help."""
        response = processor.process("help task")

        assert response.success
        assert response.intent == 'HELP'
        assert 'Task Commands' in response.response

    def test_entity_specific_help_milestone(self, processor):
        """Test milestone-specific help."""
        response = processor.process("help milestone")

        assert response.success
        assert response.intent == 'HELP'
        assert 'Milestone Commands' in response.response

    def test_entity_specific_help_unknown(self, processor):
        """Test help for unknown entity type."""
        response = processor.process("help invalid_entity")

        assert not response.success
        assert response.intent == 'HELP'
        assert 'Unknown entity type' in response.response
        assert 'Available:' in response.response


class TestExamples:
    """Test example command generation."""

    @pytest.fixture
    def formatter(self):
        """Create ResponseFormatter."""
        return ResponseFormatter()

    def test_get_examples_project_create(self, formatter):
        """Test examples for project creation."""
        examples = formatter._get_examples('project', 'create')

        assert len(examples) > 0
        assert any('create project' in ex for ex in examples)

    def test_get_examples_epic_update(self, formatter):
        """Test examples for epic update."""
        examples = formatter._get_examples('epic', 'update')

        assert len(examples) > 0
        assert any('update epic' in ex for ex in examples)

    def test_get_examples_task_query(self, formatter):
        """Test examples for task query."""
        examples = formatter._get_examples('task', 'query')

        assert len(examples) > 0
        assert any('list tasks' in ex or 'show tasks' in ex for ex in examples)

    def test_get_examples_unknown_returns_empty(self, formatter):
        """Test that unknown combinations return empty list."""
        examples = formatter._get_examples('unknown', 'invalid')

        assert examples == []
