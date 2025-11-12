"""Unit tests for QuestionHandler (ADR-016 Story 4).

Tests the question handling component with 30 test cases covering:
- 6 NEXT_STEPS questions
- 6 STATUS questions
- 6 BLOCKERS questions
- 6 PROGRESS questions
- 6 GENERAL questions

Target: 90%+ accuracy, 90%+ code coverage
"""

import pytest
import json
from unittest.mock import Mock, MagicMock
from dataclasses import dataclass

from src.nl.question_handler import (
    QuestionHandler,
    QuestionHandlingException
)
from src.nl.types import QuestionType, QuestionResponse
from plugins.base import LLMPlugin


# Mock task class for testing
@dataclass
class MockTask:
    """Mock task for testing."""
    id: int
    title: str
    status: str
    priority: str = 'MEDIUM'
    description: str = ''
    blocked_reason: str = None


# Mock project class for testing
@dataclass
class MockProject:
    """Mock project for testing."""
    id: int
    project_name: str
    status: str
    working_directory: str


@pytest.fixture
def mock_llm():
    """Create a mock LLM plugin for testing."""
    llm = Mock(spec=LLMPlugin)
    return llm


@pytest.fixture
def mock_state():
    """Create a mock StateManager for testing."""
    state = Mock()

    # Mock project
    test_project = MockProject(
        id=1,
        project_name="Tetris Game",
        status="ACTIVE",
        working_directory="/path/to/tetris"
    )

    # Mock tasks
    pending_tasks = [
        MockTask(1, "Implement scoring system", "PENDING", "HIGH"),
        MockTask(2, "Add sound effects", "PENDING", "MEDIUM"),
        MockTask(3, "Create menu UI", "PENDING", "MEDIUM"),
    ]

    completed_tasks = [
        MockTask(4, "Setup project structure", "COMPLETED", "HIGH"),
        MockTask(5, "Implement game loop", "COMPLETED", "HIGH"),
    ]

    blocked_tasks = [
        MockTask(6, "Deploy to production", "BLOCKED", "HIGH", blocked_reason="Waiting for API keys"),
    ]

    # Setup mock methods
    state.get_project.return_value = test_project
    state.list_projects.return_value = [test_project]

    def mock_list_tasks(project_id=None, status=None):
        """Mock list_tasks method."""
        all_tasks = pending_tasks + completed_tasks + blocked_tasks

        if status == 'PENDING':
            return pending_tasks
        elif status == 'COMPLETED':
            return completed_tasks
        elif status == 'BLOCKED':
            return blocked_tasks
        else:
            return all_tasks

    state.list_tasks.side_effect = mock_list_tasks

    return state


@pytest.fixture
def handler(mock_state, mock_llm):
    """Create QuestionHandler with mocks."""
    return QuestionHandler(mock_state, mock_llm)


class TestQuestionHandlerInit:
    """Test QuestionHandler initialization."""

    def test_init_with_state_and_llm(self, mock_state, mock_llm):
        """Test initialization with StateManager and LLM."""
        handler = QuestionHandler(mock_state, mock_llm)
        assert handler.state == mock_state
        assert handler.llm == mock_llm

    def test_template_loaded(self, handler):
        """Test that Jinja2 template is loaded successfully."""
        assert handler.template is not None


class TestQuestionHandlerNEXT_STEPS:
    """Test NEXT_STEPS question handling."""

    def test_next_steps_whats_next(self, handler, mock_llm):
        """Test: 'What's next for the tetris game development?' → NEXT_STEPS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "NEXT_STEPS",
            "confidence": 0.95,
            "reasoning": "Explicit 'what's next' keyword"
        })

        result = handler.handle("What's next for the tetris game development?")

        assert result.question_type == QuestionType.NEXT_STEPS
        assert "Implement scoring system" in result.answer
        assert result.confidence >= 0.8

    def test_next_steps_what_should_work_on(self, handler, mock_llm):
        """Test: 'What should I work on next?' → NEXT_STEPS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "NEXT_STEPS",
            "confidence": 0.94,
            "reasoning": "Asking for next task to work on"
        })

        result = handler.handle("What should I work on next?")

        assert result.question_type == QuestionType.NEXT_STEPS
        assert "pending tasks" in result.answer.lower() or "next steps" in result.answer.lower()

    def test_next_steps_show_next_tasks(self, handler, mock_llm):
        """Test: 'Show me the next tasks' → NEXT_STEPS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "NEXT_STEPS",
            "confidence": 0.93,
            "reasoning": "Requesting next tasks"
        })

        result = handler.handle("Show me the next tasks")

        assert result.question_type == QuestionType.NEXT_STEPS
        assert len(result.data.get('tasks', [])) > 0

    def test_next_steps_upcoming_tasks(self, handler, mock_llm):
        """Test: 'What are the upcoming tasks?' → NEXT_STEPS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "NEXT_STEPS",
            "confidence": 0.92,
            "reasoning": "Asking for upcoming tasks"
        })

        result = handler.handle("What are the upcoming tasks?")

        assert result.question_type == QuestionType.NEXT_STEPS
        assert result.answer is not None

    def test_next_steps_for_project_1(self, handler, mock_llm):
        """Test: 'What's next for project 1?' → NEXT_STEPS with project_id"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "NEXT_STEPS",
            "confidence": 0.95,
            "reasoning": "Next steps for specific project"
        })

        result = handler.handle("What's next for project 1?")

        assert result.question_type == QuestionType.NEXT_STEPS
        assert result.entities.get('project_id') == 1

    def test_next_steps_what_to_do_next(self, handler, mock_llm):
        """Test: 'What do I need to do next?' → NEXT_STEPS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "NEXT_STEPS",
            "confidence": 0.91,
            "reasoning": "Asking what to do next"
        })

        result = handler.handle("What do I need to do next?")

        assert result.question_type == QuestionType.NEXT_STEPS


class TestQuestionHandlerSTATUS:
    """Test STATUS question handling."""

    def test_status_hows_project_going(self, handler, mock_llm):
        """Test: 'How's project 1 going?' → STATUS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "STATUS",
            "confidence": 0.92,
            "reasoning": "General status inquiry"
        })

        result = handler.handle("How's project 1 going?")

        assert result.question_type == QuestionType.STATUS
        assert "Project #1" in result.answer
        assert "Tetris Game" in result.answer

    def test_status_whats_the_status(self, handler, mock_llm):
        """Test: 'What's the status of project 1?' → STATUS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "STATUS",
            "confidence": 0.95,
            "reasoning": "Explicit status inquiry"
        })

        result = handler.handle("What's the status of project 1?")

        assert result.question_type == QuestionType.STATUS
        assert "ACTIVE" in result.answer

    def test_status_is_it_done(self, handler, mock_llm):
        """Test: 'Is the tetris game done?' → STATUS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "STATUS",
            "confidence": 0.93,
            "reasoning": "Status inquiry asking if completed"
        })

        result = handler.handle("Is the tetris game done?")

        assert result.question_type == QuestionType.STATUS

    def test_status_is_epic_finished(self, handler, mock_llm):
        """Test: 'Is epic 3 finished?' → STATUS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "STATUS",
            "confidence": 0.94,
            "reasoning": "Completion status inquiry"
        })

        result = handler.handle("Is epic 3 finished?")

        assert result.question_type == QuestionType.STATUS

    def test_status_hows_it_going(self, handler, mock_llm):
        """Test: 'How's it going?' → STATUS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "STATUS",
            "confidence": 0.85,
            "reasoning": "General status inquiry"
        })

        result = handler.handle("How's it going?")

        assert result.question_type == QuestionType.STATUS

    def test_status_project_status(self, handler, mock_llm):
        """Test: 'Tell me about project 1 status' → STATUS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "STATUS",
            "confidence": 0.91,
            "reasoning": "Project status request"
        })

        result = handler.handle("Tell me about project 1 status")

        assert result.question_type == QuestionType.STATUS


class TestQuestionHandlerBLOCKERS:
    """Test BLOCKERS question handling."""

    def test_blockers_whats_blocking(self, handler, mock_llm):
        """Test: 'What's blocking project 1?' → BLOCKERS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "BLOCKERS",
            "confidence": 0.96,
            "reasoning": "Explicit 'blocking' keyword"
        })

        result = handler.handle("What's blocking project 1?")

        assert result.question_type == QuestionType.BLOCKERS
        assert "blocked" in result.answer.lower() or "Deploy to production" in result.answer

    def test_blockers_any_issues(self, handler, mock_llm):
        """Test: 'Any issues with the auth epic?' → BLOCKERS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "BLOCKERS",
            "confidence": 0.88,
            "reasoning": "Asking for issues/blockers"
        })

        result = handler.handle("Any issues with the auth epic?")

        assert result.question_type == QuestionType.BLOCKERS

    def test_blockers_what_tasks_stuck(self, handler, mock_llm):
        """Test: 'What tasks are stuck?' → BLOCKERS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "BLOCKERS",
            "confidence": 0.93,
            "reasoning": "Asking for stuck tasks (blockers)"
        })

        result = handler.handle("What tasks are stuck?")

        assert result.question_type == QuestionType.BLOCKERS

    def test_blockers_show_blockers(self, handler, mock_llm):
        """Test: 'Show me the blockers' → BLOCKERS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "BLOCKERS",
            "confidence": 0.95,
            "reasoning": "Explicit 'blockers' keyword"
        })

        result = handler.handle("Show me the blockers")

        assert result.question_type == QuestionType.BLOCKERS

    def test_blockers_any_problems(self, handler, mock_llm):
        """Test: 'Any problems with project 1?' → BLOCKERS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "BLOCKERS",
            "confidence": 0.89,
            "reasoning": "Asking for problems (blockers)"
        })

        result = handler.handle("Any problems with project 1?")

        assert result.question_type == QuestionType.BLOCKERS

    def test_blockers_blocked_tasks(self, handler, mock_llm):
        """Test: 'Which tasks are blocked?' → BLOCKERS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "BLOCKERS",
            "confidence": 0.94,
            "reasoning": "Asking for blocked tasks"
        })

        result = handler.handle("Which tasks are blocked?")

        assert result.question_type == QuestionType.BLOCKERS


class TestQuestionHandlerPROGRESS:
    """Test PROGRESS question handling."""

    def test_progress_show_progress(self, handler, mock_llm):
        """Test: 'Show progress for project 1' → PROGRESS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "PROGRESS",
            "confidence": 0.94,
            "reasoning": "Explicit 'progress' keyword"
        })

        result = handler.handle("Show progress for project 1")

        assert result.question_type == QuestionType.PROGRESS
        assert "Progress" in result.answer
        assert "%" in result.answer  # Should show percentage

    def test_progress_completion_percentage(self, handler, mock_llm):
        """Test: 'What's the completion percentage?' → PROGRESS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "PROGRESS",
            "confidence": 0.95,
            "reasoning": "Asking for completion metrics"
        })

        result = handler.handle("What's the completion percentage?")

        assert result.question_type == QuestionType.PROGRESS

    def test_progress_how_far_along(self, handler, mock_llm):
        """Test: 'How far along is the implementation?' → PROGRESS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "PROGRESS",
            "confidence": 0.91,
            "reasoning": "Asking how far along (progress)"
        })

        result = handler.handle("How far along is the implementation?")

        assert result.question_type == QuestionType.PROGRESS

    def test_progress_metrics(self, handler, mock_llm):
        """Test: 'Show me the progress metrics' → PROGRESS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "PROGRESS",
            "confidence": 0.93,
            "reasoning": "Requesting progress metrics"
        })

        result = handler.handle("Show me the progress metrics")

        assert result.question_type == QuestionType.PROGRESS

    def test_progress_completion_status(self, handler, mock_llm):
        """Test: 'What's the completion status?' → PROGRESS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "PROGRESS",
            "confidence": 0.90,
            "reasoning": "Asking for completion status (metrics)"
        })

        result = handler.handle("What's the completion status?")

        assert result.question_type == QuestionType.PROGRESS

    def test_progress_tasks_completed(self, handler, mock_llm):
        """Test: 'How many tasks are completed?' → PROGRESS"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "PROGRESS",
            "confidence": 0.92,
            "reasoning": "Asking for task completion (progress metric)"
        })

        result = handler.handle("How many tasks are completed?")

        assert result.question_type == QuestionType.PROGRESS


class TestQuestionHandlerGENERAL:
    """Test GENERAL question handling."""

    def test_general_how_to_create_epic(self, handler, mock_llm):
        """Test: 'How do I create an epic?' → GENERAL"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "GENERAL",
            "confidence": 0.90,
            "reasoning": "Guidance question asking how to do something"
        })

        result = handler.handle("How do I create an epic?")

        assert result.question_type == QuestionType.GENERAL
        assert "help" in result.answer.lower() or "task" in result.answer.lower()

    def test_general_what_is_obra(self, handler, mock_llm):
        """Test: 'What is Obra?' → GENERAL"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "GENERAL",
            "confidence": 0.92,
            "reasoning": "General informational question"
        })

        result = handler.handle("What is Obra?")

        assert result.question_type == QuestionType.GENERAL

    def test_general_can_you_help(self, handler, mock_llm):
        """Test: 'Can you help me?' → GENERAL"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "GENERAL",
            "confidence": 0.88,
            "reasoning": "General help request"
        })

        result = handler.handle("Can you help me?")

        assert result.question_type == QuestionType.GENERAL

    def test_general_explain_tasks(self, handler, mock_llm):
        """Test: 'Explain how tasks work' → GENERAL"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "GENERAL",
            "confidence": 0.89,
            "reasoning": "Explanation request"
        })

        result = handler.handle("Explain how tasks work")

        assert result.question_type == QuestionType.GENERAL

    def test_general_whats_the_difference(self, handler, mock_llm):
        """Test: 'What's the difference between epic and story?' → GENERAL"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "GENERAL",
            "confidence": 0.91,
            "reasoning": "Conceptual question"
        })

        result = handler.handle("What's the difference between epic and story?")

        assert result.question_type == QuestionType.GENERAL

    def test_general_help_with_commands(self, handler, mock_llm):
        """Test: 'Help me with commands' → GENERAL"""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "GENERAL",
            "confidence": 0.87,
            "reasoning": "General help request"
        })

        result = handler.handle("Help me with commands")

        assert result.question_type == QuestionType.GENERAL


class TestQuestionHandlerEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self, handler):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            handler.handle("")

    def test_whitespace_only_input(self, handler):
        """Test that whitespace-only input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            handler.handle("   ")

    def test_llm_failure_defaults_to_general(self, handler, mock_llm):
        """Test that LLM failure defaults to GENERAL question type."""
        mock_llm.generate.side_effect = Exception("LLM connection failed")

        # Should not raise exception, should default to GENERAL
        result = handler.handle("Some question")

        assert result.question_type == QuestionType.GENERAL

    def test_entity_extraction_project_id(self, handler, mock_llm):
        """Test entity extraction recognizes project ID."""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "STATUS",
            "confidence": 0.92,
            "reasoning": "Status inquiry"
        })

        result = handler.handle("What's the status of project 3?")

        assert result.entities.get('project_id') == 3

    def test_entity_extraction_project_name(self, handler, mock_llm):
        """Test entity extraction recognizes project name."""
        mock_llm.generate.return_value = json.dumps({
            "question_type": "NEXT_STEPS",
            "confidence": 0.95,
            "reasoning": "Next steps inquiry"
        })

        result = handler.handle("What's next for the tetris game?")

        assert result.entities.get('project_name') is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
