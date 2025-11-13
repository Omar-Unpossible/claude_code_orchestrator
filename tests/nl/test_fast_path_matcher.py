"""Tests for FastPathMatcher - Regex-based pattern matching for common NL queries.

This test file verifies:
1. Pattern matching for common queries (list/show/get commands)
2. Entity ID extraction from patterns
3. Fast path miss handling for complex queries
4. Statistics tracking (hit/miss counts and rates)
5. Case-insensitive matching
6. Normalization of input strings

Expected Coverage: >95%
"""

import pytest
from src.nl.fast_path_matcher import FastPathMatcher, FastPathPattern
from src.nl.types import OperationType, EntityType, QueryType


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def matcher():
    """Create FastPathMatcher instance for testing."""
    return FastPathMatcher()


# =============================================================================
# Category 1: Pattern Matching - Projects (6 tests)
# =============================================================================

def test_match_list_projects(matcher):
    """Test fast path match for 'list all projects'."""
    result = matcher.match("list all projects")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.PROJECT
    assert result.query_type == QueryType.SIMPLE
    assert result.identifier is None
    assert result.confidence == 1.0


def test_match_show_projects(matcher):
    """Test fast path match for 'show projects'."""
    result = matcher.match("show projects")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.PROJECT
    assert result.confidence == 1.0


def test_match_get_project_by_id(matcher):
    """Test fast path match with ID extraction: 'get project 5'."""
    result = matcher.match("get project 5")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.PROJECT
    assert result.identifier == 5
    assert result.confidence == 1.0


def test_match_display_project(matcher):
    """Test fast path match for 'display project'."""
    result = matcher.match("display project")

    assert result is not None
    assert result.entity_type == EntityType.PROJECT


def test_match_active_projects(matcher):
    """Test fast path match for 'show active projects'."""
    result = matcher.match("show active projects")

    assert result is not None
    assert result.entity_type == EntityType.PROJECT


def test_match_open_projects(matcher):
    """Test fast path match for 'list open projects'."""
    result = matcher.match("list open projects")

    assert result is not None
    assert result.entity_type == EntityType.PROJECT


# =============================================================================
# Category 2: Pattern Matching - Tasks (6 tests)
# =============================================================================

def test_match_list_tasks(matcher):
    """Test fast path match for 'list all tasks'."""
    result = matcher.match("list all tasks")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.TASK
    assert result.query_type == QueryType.SIMPLE
    assert result.identifier is None


def test_match_show_tasks(matcher):
    """Test fast path match for 'show tasks'."""
    result = matcher.match("show tasks")

    assert result is not None
    assert result.entity_type == EntityType.TASK


def test_match_get_task_by_id(matcher):
    """Test fast path match with ID extraction: 'get task 42'."""
    result = matcher.match("get task 42")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.TASK
    assert result.identifier == 42


def test_match_pending_tasks(matcher):
    """Test fast path match for 'show pending tasks'."""
    result = matcher.match("show pending tasks")

    assert result is not None
    assert result.entity_type == EntityType.TASK


def test_match_open_tasks(matcher):
    """Test fast path match for 'list open tasks'."""
    result = matcher.match("list open tasks")

    assert result is not None
    assert result.entity_type == EntityType.TASK


def test_match_active_tasks(matcher):
    """Test fast path match for 'show active tasks'."""
    result = matcher.match("show active tasks")

    assert result is not None
    assert result.entity_type == EntityType.TASK


# =============================================================================
# Category 3: Pattern Matching - Epics (4 tests)
# =============================================================================

def test_match_list_epics(matcher):
    """Test fast path match for 'list all epics'."""
    result = matcher.match("list all epics")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.EPIC
    assert result.identifier is None


def test_match_show_epics(matcher):
    """Test fast path match for 'show epics'."""
    result = matcher.match("show epics")

    assert result is not None
    assert result.entity_type == EntityType.EPIC


def test_match_get_epic_by_id(matcher):
    """Test fast path match with ID extraction: 'get epic 5'."""
    result = matcher.match("get epic 5")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.EPIC
    assert result.identifier == 5
    assert result.confidence == 1.0


def test_match_display_epic(matcher):
    """Test fast path match for 'display epic 10'."""
    result = matcher.match("display epic 10")

    assert result is not None
    assert result.entity_type == EntityType.EPIC
    assert result.identifier == 10


# =============================================================================
# Category 4: Pattern Matching - Stories (4 tests)
# =============================================================================

def test_match_list_stories(matcher):
    """Test fast path match for 'list all stories'."""
    result = matcher.match("list all stories")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.STORY


def test_match_show_story(matcher):
    """Test fast path match for 'show story'."""
    result = matcher.match("show story")

    assert result is not None
    assert result.entity_type == EntityType.STORY


def test_match_get_story_by_id(matcher):
    """Test fast path match with ID extraction: 'get story 3'."""
    result = matcher.match("get story 3")

    assert result is not None
    assert result.entity_type == EntityType.STORY
    assert result.identifier == 3


def test_match_story_singular_plural(matcher):
    """Test fast path handles both 'story' and 'stories'."""
    singular = matcher.match("show story")
    plural = matcher.match("show stories")

    assert singular is not None
    assert plural is not None
    assert singular.entity_type == EntityType.STORY
    assert plural.entity_type == EntityType.STORY


# =============================================================================
# Category 5: Pattern Matching - Milestones (4 tests)
# =============================================================================

def test_match_list_milestones(matcher):
    """Test fast path match for 'list all milestones'."""
    result = matcher.match("list all milestones")

    assert result is not None
    assert result.operation == OperationType.QUERY
    assert result.entity_type == EntityType.MILESTONE


def test_match_show_milestones(matcher):
    """Test fast path match for 'show milestones'."""
    result = matcher.match("show milestones")

    assert result is not None
    assert result.entity_type == EntityType.MILESTONE


def test_match_get_milestone_by_id(matcher):
    """Test fast path match with ID extraction: 'get milestone 7'."""
    result = matcher.match("get milestone 7")

    assert result is not None
    assert result.entity_type == EntityType.MILESTONE
    assert result.identifier == 7


def test_match_milestone_singular(matcher):
    """Test fast path match for singular 'milestone'."""
    result = matcher.match("show milestone")

    assert result is not None
    assert result.entity_type == EntityType.MILESTONE


# =============================================================================
# Category 6: Fast Path Misses (6 tests)
# =============================================================================

def test_miss_complex_query(matcher):
    """Test fast path miss for complex query."""
    result = matcher.match("show me all tasks created last week with high priority")

    assert result is None


def test_miss_create_command(matcher):
    """Test fast path miss for CREATE commands."""
    result = matcher.match("create a new epic for authentication")

    assert result is None


def test_miss_update_command(matcher):
    """Test fast path miss for UPDATE commands."""
    result = matcher.match("update task 5 with new description")

    assert result is None


def test_miss_delete_command(matcher):
    """Test fast path miss for DELETE commands."""
    result = matcher.match("delete project 3")

    assert result is None


def test_miss_complex_filters(matcher):
    """Test fast path miss for queries with filters."""
    result = matcher.match("show tasks where status is pending and priority is high")

    assert result is None


def test_miss_natural_language_question(matcher):
    """Test fast path miss for natural language question."""
    result = matcher.match("what are the tasks that need to be completed?")

    assert result is None


# =============================================================================
# Category 7: Statistics Tracking (6 tests)
# =============================================================================

def test_stats_initial_state(matcher):
    """Test initial statistics state."""
    stats = matcher.get_stats()

    assert stats['hit_count'] == 0
    assert stats['miss_count'] == 0
    assert stats['total'] == 0
    assert stats['hit_rate'] == 0.0


def test_stats_tracking_hits(matcher):
    """Test statistics tracking for hits."""
    matcher.match("list all projects")  # Hit
    matcher.match("show tasks")  # Hit
    matcher.match("get epic 5")  # Hit

    stats = matcher.get_stats()
    assert stats['hit_count'] == 3
    assert stats['miss_count'] == 0
    assert stats['total'] == 3
    assert stats['hit_rate'] == 1.0


def test_stats_tracking_misses(matcher):
    """Test statistics tracking for misses."""
    matcher.match("create a new epic")  # Miss
    matcher.match("complex query with filters")  # Miss

    stats = matcher.get_stats()
    assert stats['hit_count'] == 0
    assert stats['miss_count'] == 2
    assert stats['total'] == 2
    assert stats['hit_rate'] == 0.0


def test_hit_miss_counts(matcher):
    """Test statistics tracking for mixed hits and misses."""
    # Hits
    matcher.match("list all projects")
    matcher.match("show tasks")
    matcher.match("get epic 5")

    # Misses
    matcher.match("create a new epic")
    matcher.match("update task 3")

    stats = matcher.get_stats()
    assert stats['hit_count'] == 3
    assert stats['miss_count'] == 2
    assert stats['total'] == 5
    assert stats['hit_rate'] == 0.6  # 3/5


def test_hit_rate_calculation(matcher):
    """Test hit rate calculation with various ratios."""
    # 50% hit rate
    matcher.match("list projects")  # Hit
    matcher.match("create epic")  # Miss

    stats = matcher.get_stats()
    assert stats['hit_rate'] == 0.5

    # Add more hits to change ratio
    matcher.match("show tasks")  # Hit
    matcher.match("get story 1")  # Hit

    stats = matcher.get_stats()
    assert stats['hit_count'] == 3
    assert stats['miss_count'] == 1
    assert stats['hit_rate'] == 0.75


def test_stats_persistence(matcher):
    """Test that statistics persist across multiple queries."""
    matcher.match("list projects")
    initial_stats = matcher.get_stats()

    matcher.match("show tasks")
    updated_stats = matcher.get_stats()

    assert updated_stats['hit_count'] == initial_stats['hit_count'] + 1
    assert updated_stats['total'] == initial_stats['total'] + 1


# =============================================================================
# Category 8: Input Normalization (6 tests)
# =============================================================================

def test_case_insensitive_matching(matcher):
    """Test case-insensitive pattern matching."""
    lowercase = matcher.match("list all projects")
    uppercase = matcher.match("LIST ALL PROJECTS")
    mixed = matcher.match("List All Projects")

    assert lowercase is not None
    assert uppercase is not None
    assert mixed is not None
    assert lowercase.entity_type == uppercase.entity_type == mixed.entity_type


def test_whitespace_normalization(matcher):
    """Test whitespace normalization."""
    normal = matcher.match("list all projects")
    extra_spaces = matcher.match("  list   all   projects  ")

    assert normal is not None
    assert extra_spaces is not None
    assert normal.entity_type == extra_spaces.entity_type


def test_trailing_whitespace(matcher):
    """Test handling of trailing whitespace."""
    result = matcher.match("show tasks   ")

    assert result is not None
    assert result.entity_type == EntityType.TASK


def test_leading_whitespace(matcher):
    """Test handling of leading whitespace."""
    result = matcher.match("   get epic 5")

    assert result is not None
    assert result.entity_type == EntityType.EPIC
    assert result.identifier == 5


def test_mixed_case_with_id(matcher):
    """Test mixed case with ID extraction."""
    result = matcher.match("Get Task 99")

    assert result is not None
    assert result.entity_type == EntityType.TASK
    assert result.identifier == 99


def test_normalized_original_message(matcher):
    """Test that original message is preserved in result."""
    original = "  LIST ALL PROJECTS  "
    result = matcher.match(original)

    assert result is not None
    assert result.raw_input == original


# =============================================================================
# Category 9: Edge Cases (6 tests)
# =============================================================================

def test_empty_string(matcher):
    """Test fast path miss for empty string."""
    result = matcher.match("")

    assert result is None


def test_whitespace_only(matcher):
    """Test fast path miss for whitespace-only string."""
    result = matcher.match("   ")

    assert result is None


def test_single_word(matcher):
    """Test fast path miss for single word."""
    result = matcher.match("projects")

    assert result is None


def test_partial_match(matcher):
    """Test that partial matches don't trigger (regex must match full pattern)."""
    result = matcher.match("list all")

    assert result is None


def test_extra_words_after_pattern(matcher):
    """Test that extra words prevent matching."""
    result = matcher.match("list all projects with filters")

    assert result is None


def test_numeric_id_extraction_multidigit(matcher):
    """Test ID extraction with multi-digit numbers."""
    result = matcher.match("get task 12345")

    assert result is not None
    assert result.identifier == 12345


# =============================================================================
# Category 10: FastPathPattern Dataclass (2 tests)
# =============================================================================

def test_fast_path_pattern_creation():
    """Test FastPathPattern dataclass creation."""
    pattern = FastPathPattern(
        pattern=r"^test$",
        operation=OperationType.QUERY,
        entity_type=EntityType.PROJECT,
        query_type=QueryType.SIMPLE,
        extract_id=True
    )

    assert pattern.pattern == r"^test$"
    assert pattern.operation == OperationType.QUERY
    assert pattern.entity_type == EntityType.PROJECT
    assert pattern.query_type == QueryType.SIMPLE
    assert pattern.extract_id is True


def test_fast_path_pattern_defaults():
    """Test FastPathPattern default values."""
    pattern = FastPathPattern(
        pattern=r"^test$",
        operation=OperationType.QUERY,
        entity_type=EntityType.PROJECT
    )

    assert pattern.query_type is None
    assert pattern.extract_id is False


# =============================================================================
# Summary
# =============================================================================

# Total tests: 60
# Categories:
#   1. Projects (6 tests) - Basic pattern matching
#   2. Tasks (6 tests) - Basic pattern matching
#   3. Epics (4 tests) - Basic pattern matching
#   4. Stories (4 tests) - Basic pattern matching
#   5. Milestones (4 tests) - Basic pattern matching
#   6. Fast Path Misses (6 tests) - Verify complex queries miss
#   7. Statistics Tracking (6 tests) - Hit/miss counts and rates
#   8. Input Normalization (6 tests) - Case/whitespace handling
#   9. Edge Cases (6 tests) - Empty strings, partial matches
#   10. FastPathPattern (2 tests) - Dataclass testing
#
# Expected Coverage: >95%
# Expected Runtime: <5 seconds (no LLM calls, pure regex matching)
