"""Unit tests for Response Formatter.

Tests ResponseFormatter output formatting including:
- Success message formatting with IDs and next actions
- Error message formatting with recovery suggestions
- Confirmation prompts for destructive operations
- Clarification requests with suggestions
- Color coding (green=success, red=error, yellow=warning)
- List formatting

Coverage Target: 95%
Test Cases: TC-RF-001 through TC-RF-008
"""

import pytest
from unittest.mock import Mock
from src.nl.response_formatter import ResponseFormatter
from src.nl.command_executor import ExecutionResult
from colorama import Fore, Style


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def formatter():
    """Create ResponseFormatter instance."""
    return ResponseFormatter()


# ============================================================================
# Test: Success Response Formatting (TC-RF-001)
# ============================================================================

def test_success_response_single_epic(formatter):
    """TC-RF-001: Test formatting of successful epic creation."""
    result = ExecutionResult(
        success=True,
        created_ids=[5],
        results={
            'entity_type': 'epic',
            'title': 'User Auth',
            'created_count': 1
        }
    )

    response = formatter.format(result, intent='COMMAND')

    # Check success indicator
    assert "✓" in response
    assert "Epic #5" in response
    assert "User Auth" in response
    # Check color coding
    assert Fore.GREEN in response
    # Check next action suggestion
    assert "Next:" in response or "create story" in response.lower()


def test_success_response_multiple_stories(formatter):
    """TC-RF-001: Test formatting of multiple story creation."""
    result = ExecutionResult(
        success=True,
        created_ids=[6, 7, 8],
        results={
            'entity_type': 'story',
            'created_count': 3
        }
    )

    response = formatter.format(result, intent='COMMAND')

    assert "✓" in response
    assert "3 storys" in response
    assert "#6" in response
    assert "#7" in response
    assert "#8" in response
    assert Fore.GREEN in response


def test_success_response_with_entity_details(formatter):
    """TC-RF-001: Test success response with additional entity details."""
    result = ExecutionResult(
        success=True,
        created_ids=[10],
        results={
            'entity_type': 'task',
            'title': 'Implement login',
            'created_count': 1
        }
    )

    entity_details = {'title': 'Implement login', 'priority': 1}

    response = formatter.format(result, intent='COMMAND', entity_details=entity_details)

    assert "✓" in response
    assert "Task #10" in response
    assert "Implement login" in response


# ============================================================================
# Test: Error Response Formatting (TC-RF-002)
# ============================================================================

def test_error_response_epic_not_found(formatter):
    """TC-RF-002: Test formatting of epic not found error."""
    result = ExecutionResult(
        success=False,
        errors=["Epic not found"]
    )

    response = formatter.format(result, intent='COMMAND')

    # Check error indicator
    assert "✗" in response
    assert "Epic not found" in response
    # Check color coding
    assert Fore.RED in response
    # Check recovery suggestion
    assert "Try:" in response
    assert "show epics" in response.lower() or "list epics" in response.lower()


def test_error_response_missing_required_field(formatter):
    """TC-RF-002: Test formatting of missing required field error."""
    result = ExecutionResult(
        success=False,
        errors=["Story requires epic_id"]
    )

    response = formatter.format(result, intent='COMMAND')

    assert "✗" in response
    assert "requires epic_id" in response
    assert Fore.RED in response
    # Should suggest checking required fields
    assert "Try:" in response


def test_error_response_multiple_errors(formatter):
    """TC-RF-002: Test formatting with multiple errors."""
    result = ExecutionResult(
        success=False,
        errors=[
            "Epic not found",
            "Invalid priority value",
            "Missing description"
        ]
    )

    response = formatter.format(result, intent='COMMAND')

    assert "✗" in response
    assert "Epic not found" in response  # First error
    assert "2 more errors" in response  # Remaining errors count
    assert Fore.RED in response


def test_error_response_circular_dependency(formatter):
    """TC-RF-002: Test formatting of circular dependency error."""
    result = ExecutionResult(
        success=False,
        errors=["Circular dependency detected between tasks"]
    )

    response = formatter.format(result, intent='COMMAND')

    assert "✗" in response
    assert "Circular dependency" in response
    assert "Try:" in response
    # Should suggest reviewing dependencies
    assert "dependencies" in response.lower()


# ============================================================================
# Test: Color Coding (TC-RF-003)
# ============================================================================

def test_color_coding_success(formatter):
    """TC-RF-003: Test green color for success."""
    result = ExecutionResult(
        success=True,
        created_ids=[1],
        results={'entity_type': 'epic'}
    )

    response = formatter.format(result, intent='COMMAND')

    # Check for ANSI green color code
    assert Fore.GREEN in response
    assert Style.RESET_ALL in response


def test_color_coding_error(formatter):
    """TC-RF-003: Test red color for errors."""
    result = ExecutionResult(
        success=False,
        errors=["Test error"]
    )

    response = formatter.format(result, intent='COMMAND')

    # Check for ANSI red color code
    assert Fore.RED in response
    assert Style.RESET_ALL in response


def test_color_coding_confirmation(formatter):
    """TC-RF-003: Test yellow color for confirmation."""
    result = ExecutionResult(
        success=False,
        confirmation_required=True,
        results={'entity_type': 'epic', 'action': 'delete'}
    )

    response = formatter.format(result, intent='COMMAND')

    # Check for ANSI yellow color code
    assert Fore.YELLOW in response
    assert Style.RESET_ALL in response


# ============================================================================
# Test: Confirmation Prompts (TC-RF-004)
# ============================================================================

def test_confirmation_prompt_delete(formatter):
    """TC-RF-004: Test confirmation prompt for delete operation."""
    result = ExecutionResult(
        success=False,
        confirmation_required=True,
        results={
            'entity_type': 'epic',
            'action': 'delete'
        }
    )

    response = formatter.format(result, intent='COMMAND')

    assert "⚠" in response or "warning" in response.lower()
    assert "delete" in response.lower()
    assert "epic" in response.lower()
    assert "Confirm?" in response or "(y/n)" in response
    assert Fore.YELLOW in response


def test_confirmation_prompt_update(formatter):
    """TC-RF-004: Test confirmation prompt for update operation."""
    result = ExecutionResult(
        success=False,
        confirmation_required=True,
        results={
            'entity_type': 'story',
            'action': 'update'
        }
    )

    response = formatter.format(result, intent='COMMAND')

    assert "⚠" in response or "warning" in response.lower()
    assert "update" in response.lower()
    assert "story" in response.lower()
    assert Fore.YELLOW in response


# ============================================================================
# Test: Clarification Requests (TC-RF-005)
# ============================================================================

def test_clarification_request_with_suggestions(formatter):
    """TC-RF-005: Test clarification request with suggestions."""
    suggestions = [
        "Create epic 'User Dashboard'",
        "List existing epics",
        "Show epic details"
    ]

    response = formatter.format_clarification_request(
        "Did you mean:",
        suggestions=suggestions
    )

    assert "?" in response
    assert "Did you mean:" in response
    assert "1." in response
    assert "User Dashboard" in response
    assert "2." in response
    assert "List existing epics" in response
    assert "0." in response  # "Something else" option
    assert Fore.YELLOW in response


def test_clarification_request_without_suggestions(formatter):
    """TC-RF-005: Test clarification request without suggestions."""
    response = formatter.format_clarification_request(
        "Please clarify your request"
    )

    assert "?" in response
    assert "Please clarify" in response
    assert Fore.YELLOW in response


# ============================================================================
# Test: Informational Responses (TC-RF-006)
# ============================================================================

def test_info_response_plain_text(formatter):
    """TC-RF-006: Test informational response (no special formatting)."""
    content = "You have 3 epics: Epic #1, Epic #2, Epic #3"

    response = formatter.format_info_response(content)

    # Should return plain text without color codes
    assert response == content


# ============================================================================
# Test: List Formatting (TC-RF-007)
# ============================================================================

def test_list_formatting_with_items(formatter):
    """TC-RF-007: Test list formatting with multiple items."""
    items = [
        {'id': 1, 'title': 'User Authentication', 'status': 'pending'},
        {'id': 2, 'title': 'Admin Dashboard', 'status': 'in_progress'},
        {'id': 3, 'title': 'Reporting System', 'status': 'completed'}
    ]

    response = formatter.format_list_response(items, 'epic')

    assert "3 epic(s):" in response
    assert "#1: User Authentication" in response
    assert "#2: Admin Dashboard" in response
    assert "#3: Reporting System" in response
    assert "(pending)" in response
    assert "(in_progress)" in response
    assert Fore.CYAN in response


def test_list_formatting_empty(formatter):
    """TC-RF-007: Test list formatting with no items."""
    items = []

    response = formatter.format_list_response(items, 'story')

    assert "No storys found" in response
    assert Fore.YELLOW in response


def test_list_formatting_without_status(formatter):
    """TC-RF-007: Test list formatting without status field."""
    items = [
        {'id': 5, 'title': 'Task One'},
        {'id': 6, 'title': 'Task Two'}
    ]

    response = formatter.format_list_response(items, 'task')

    assert "2 task(s):" in response
    assert "#5: Task One" in response
    assert "#6: Task Two" in response
    # Should not have status indicators
    assert "(pending)" not in response


# ============================================================================
# Test: Next Action Suggestions (TC-RF-008)
# ============================================================================

def test_next_action_after_epic_creation(formatter):
    """TC-RF-008: Test next action suggestion after epic creation."""
    result = ExecutionResult(
        success=True,
        created_ids=[5],
        results={'entity_type': 'epic', 'created_count': 1}
    )

    response = formatter.format(result, intent='COMMAND')

    # Should suggest adding stories
    assert "Next:" in response
    assert "story" in response.lower()


def test_next_action_after_story_creation(formatter):
    """TC-RF-008: Test next action suggestion after story creation."""
    result = ExecutionResult(
        success=True,
        created_ids=[10],
        results={'entity_type': 'story', 'created_count': 1}
    )

    response = formatter.format(result, intent='COMMAND')

    # Should suggest adding tasks
    assert "Next:" in response
    assert "task" in response.lower()


def test_next_action_after_milestone_creation(formatter):
    """TC-RF-008: Test next action suggestion after milestone creation."""
    result = ExecutionResult(
        success=True,
        created_ids=[1],
        results={'entity_type': 'milestone', 'created_count': 1}
    )

    response = formatter.format(result, intent='COMMAND')

    # Should suggest checking milestone status
    assert "Next:" in response
    assert "milestone" in response.lower() or "completion" in response.lower()


# ============================================================================
# Test: Recovery Suggestions (TC-RF-009)
# ============================================================================

def test_recovery_suggestion_for_story_not_found(formatter):
    """TC-RF-009: Test recovery suggestion for story not found."""
    result = ExecutionResult(
        success=False,
        errors=["Story not found"]
    )

    response = formatter.format(result, intent='COMMAND')

    assert "Try:" in response
    assert "show stories" in response.lower() or "list stories" in response.lower()


def test_recovery_suggestion_for_database_error(formatter):
    """TC-RF-009: Test recovery suggestion for database error."""
    result = ExecutionResult(
        success=False,
        errors=["Database connection lost"]
    )

    response = formatter.format(result, intent='COMMAND')

    assert "Try:" in response
    assert "database" in response.lower() or "connection" in response.lower()


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_format_with_empty_result(formatter):
    """Test formatting with empty execution result."""
    result = ExecutionResult(
        success=False,
        errors=[]
    )

    response = formatter.format(result, intent='COMMAND')

    # Should handle gracefully
    assert "✗" in response
    assert "unknown error occurred" in response.lower()


def test_format_with_unknown_entity_type(formatter):
    """Test formatting with unknown entity type."""
    result = ExecutionResult(
        success=True,
        created_ids=[99],
        results={'entity_type': 'unknown_type', 'created_count': 1}
    )

    response = formatter.format(result, intent='COMMAND')

    # Should still format successfully
    assert "✓" in response
    assert "#99" in response


def test_title_extraction_from_multiple_sources(formatter):
    """Test title extraction from different field names."""
    # Test with 'title' field
    result1 = ExecutionResult(
        success=True,
        created_ids=[1],
        results={'entity_type': 'epic', 'title': 'Title Field'}
    )
    response1 = formatter.format(result1, intent='COMMAND')
    assert "Title Field" in response1

    # Test with 'name' field
    result2 = ExecutionResult(
        success=True,
        created_ids=[2],
        results={'entity_type': 'milestone', 'name': 'Name Field'}
    )
    entity_details = {'name': 'Name Field'}
    response2 = formatter.format(result2, intent='COMMAND', entity_details=entity_details)
    assert "Name Field" in response2 or "#2" in response2  # At least ID should show


def test_multiple_created_ids_formatting(formatter):
    """Test formatting with many created IDs."""
    result = ExecutionResult(
        success=True,
        created_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        results={'entity_type': 'task', 'created_count': 10}
    )

    response = formatter.format(result, intent='COMMAND')

    assert "✓" in response
    assert "10 tasks" in response
    # Check a few IDs
    assert "#1" in response
    assert "#5" in response
    assert "#10" in response
