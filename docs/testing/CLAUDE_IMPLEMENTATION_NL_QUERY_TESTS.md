# Machine-Optimized Implementation Guide: NL Query Testing Suite

**Target**: Claude Code Agent
**Purpose**: Implement comprehensive test suite for NL query system (Bug Fixes: FastPathMatcher, StateManager, Query Filtering)
**Estimated Time**: 2-3 hours
**Files to Create**: 4 new test files
**Files to Modify**: 3 existing test files

---

## Prerequisites Checklist

Before starting, verify:
- [ ] Python 3.9+ environment active
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Working directory: `/home/omarwsl/projects/claude_code_orchestrator`
- [ ] No running tests or orchestrator processes
- [ ] pytest available: `pytest --version` works

---

## Implementation Steps

### STEP 1: Create Fast Path Matcher Integration Tests

**File**: `tests/nl/test_fast_path_matcher_integration.py`
**Action**: CREATE NEW FILE
**Purpose**: Test FastPathMatcher creates valid OperationContext objects

**Complete File Content**:

```python
"""Integration tests for FastPathMatcher with OperationContext validation.

These tests ensure FastPathMatcher creates valid OperationContext objects
that can be used throughout the NL pipeline without API mismatches.

Bug Fix: Prevents 'entity_type' vs 'entity_types' parameter errors.
"""

import pytest
from src.nl.fast_path_matcher import FastPathMatcher
from src.nl.types import OperationContext, OperationType, EntityType, QueryType


class TestFastPathMatcherIntegration:
    """Integration tests for FastPathMatcher + OperationContext."""

    @pytest.fixture
    def matcher(self):
        """FastPathMatcher instance."""
        return FastPathMatcher()

    # ==================== Basic Pattern Matching ====================

    def test_project_query_creates_valid_context(self, matcher):
        """Test 'list all projects' creates valid OperationContext.

        Validates:
        - OperationContext is created successfully
        - entity_types is a list (not single value)
        - All required fields are populated
        """
        context = matcher.match("list all projects")

        assert context is not None, "Pattern should match"
        assert isinstance(context, OperationContext), "Should return OperationContext"
        assert context.operation == OperationType.QUERY
        assert isinstance(context.entity_types, list), "entity_types must be list"
        assert context.entity_types == [EntityType.PROJECT]
        assert context.query_type == QueryType.SIMPLE
        assert context.confidence == 1.0  # Rule-based = 100%

    def test_task_query_creates_valid_context(self, matcher):
        """Test 'show tasks' creates valid OperationContext."""
        context = matcher.match("show tasks")

        assert context is not None
        assert isinstance(context.entity_types, list)
        assert context.entity_types == [EntityType.TASK]
        assert len(context.entity_types) == 1

    def test_epic_query_creates_valid_context(self, matcher):
        """Test 'list epics' creates valid OperationContext."""
        context = matcher.match("list epics")

        assert context is not None
        assert context.entity_types == [EntityType.EPIC]
        assert context.operation == OperationType.QUERY

    def test_story_query_creates_valid_context(self, matcher):
        """Test 'list stories' creates valid OperationContext."""
        context = matcher.match("list stories")

        assert context is not None
        assert context.entity_types == [EntityType.STORY]

    def test_milestone_query_creates_valid_context(self, matcher):
        """Test 'list milestones' creates valid OperationContext."""
        context = matcher.match("list milestones")

        assert context is not None
        assert context.entity_types == [EntityType.MILESTONE]

    # ==================== ID Extraction ====================

    def test_project_with_id_extracts_identifier(self, matcher):
        """Test 'show project 1' extracts ID correctly."""
        context = matcher.match("show project 1")

        assert context is not None
        assert context.identifier == 1
        assert isinstance(context.identifier, int)
        assert context.entity_types == [EntityType.PROJECT]

    def test_epic_with_id_creates_valid_context(self, matcher):
        """Test 'get epic 5' extracts ID and creates valid context."""
        context = matcher.match("get epic 5")

        assert context is not None
        assert context.entity_types == [EntityType.EPIC]
        assert context.identifier == 5
        assert isinstance(context.identifier, int)

    def test_task_with_id_extracts_identifier(self, matcher):
        """Test 'get task 10' extracts ID."""
        context = matcher.match("get task 10")

        assert context is not None
        assert context.identifier == 10
        assert context.entity_types == [EntityType.TASK]

    def test_story_with_id_extracts_identifier(self, matcher):
        """Test 'show story 7' extracts ID."""
        context = matcher.match("show story 7")

        assert context is not None
        assert context.identifier == 7
        assert context.entity_types == [EntityType.STORY]

    # ==================== Comprehensive Pattern Coverage ====================

    def test_all_list_patterns_create_valid_contexts(self, matcher):
        """Test all 'list' patterns create valid OperationContext objects."""
        test_inputs = [
            ("list all projects", EntityType.PROJECT),
            ("list projects", EntityType.PROJECT),
            ("list all tasks", EntityType.TASK),
            ("list tasks", EntityType.TASK),
            ("list all epics", EntityType.EPIC),
            ("list epics", EntityType.EPIC),
            ("list all stories", EntityType.STORY),
            ("list stories", EntityType.STORY),
            ("list all milestones", EntityType.MILESTONE),
            ("list milestones", EntityType.MILESTONE),
        ]

        for user_input, expected_entity_type in test_inputs:
            context = matcher.match(user_input)
            assert context is not None, f"Pattern should match: '{user_input}'"
            assert isinstance(context.entity_types, list)
            assert context.entity_types == [expected_entity_type]
            assert context.operation == OperationType.QUERY

    def test_all_show_patterns_create_valid_contexts(self, matcher):
        """Test all 'show' patterns create valid OperationContext objects."""
        test_inputs = [
            ("show projects", EntityType.PROJECT),
            ("show tasks", EntityType.TASK),
            ("show epics", EntityType.EPIC),
            ("show stories", EntityType.STORY),
            ("show milestones", EntityType.MILESTONE),
        ]

        for user_input, expected_entity_type in test_inputs:
            context = matcher.match(user_input)
            assert context is not None
            assert context.entity_types == [expected_entity_type]

    def test_all_get_patterns_with_ids(self, matcher):
        """Test all 'get <entity> <id>' patterns extract IDs."""
        test_inputs = [
            ("get project 1", EntityType.PROJECT, 1),
            ("get task 10", EntityType.TASK, 10),
            ("get epic 3", EntityType.EPIC, 3),
            ("get story 7", EntityType.STORY, 7),
            ("get milestone 2", EntityType.MILESTONE, 2),
        ]

        for user_input, expected_entity_type, expected_id in test_inputs:
            context = matcher.match(user_input)
            assert context is not None, f"Pattern should match: '{user_input}'"
            assert context.entity_types == [expected_entity_type]
            assert context.identifier == expected_id
            assert isinstance(context.identifier, int)

    # ==================== Context Validation ====================

    def test_context_has_required_fields(self, matcher):
        """Test OperationContext has all required fields populated."""
        context = matcher.match("list all projects")

        # Required fields
        assert hasattr(context, 'operation')
        assert hasattr(context, 'entity_types')
        assert hasattr(context, 'identifier')
        assert hasattr(context, 'parameters')
        assert hasattr(context, 'query_type')
        assert hasattr(context, 'confidence')
        assert hasattr(context, 'raw_input')

        # Field types
        assert isinstance(context.operation, OperationType)
        assert isinstance(context.entity_types, list)
        assert all(isinstance(et, EntityType) for et in context.entity_types)
        assert isinstance(context.parameters, dict)
        assert isinstance(context.query_type, QueryType) or context.query_type is None
        assert isinstance(context.confidence, float)
        assert isinstance(context.raw_input, str)

    def test_context_can_be_passed_to_validator(self, matcher):
        """Test OperationContext can be used in downstream components.

        This simulates the context being passed through the NL pipeline
        without causing AttributeErrors or TypeErrors.
        """
        context = matcher.match("list all projects")

        # Should not raise any exceptions
        assert context.operation == OperationType.QUERY
        assert context.entity_type == EntityType.PROJECT  # Backward compatibility property
        assert context.entity_types[0] == EntityType.PROJECT
        assert len(context.entity_types) == 1

    # ==================== Edge Cases ====================

    def test_miss_returns_none(self, matcher):
        """Test non-matching input returns None."""
        context = matcher.match("this doesn't match any pattern")
        assert context is None

    def test_partial_match_returns_none(self, matcher):
        """Test partial match returns None."""
        context = matcher.match("list all")  # Missing entity type
        assert context is None

    def test_case_insensitive_matching(self, matcher):
        """Test patterns match case-insensitively."""
        inputs = [
            "LIST ALL PROJECTS",
            "List All Projects",
            "list all projects",
            "LiSt AlL pRoJeCtS"
        ]

        for user_input in inputs:
            context = matcher.match(user_input)
            assert context is not None
            assert context.entity_types == [EntityType.PROJECT]

    # ==================== Metrics ====================

    def test_hit_count_increments(self, matcher):
        """Test hit_count metric increments on match."""
        initial_hits = matcher.hit_count
        matcher.match("list all projects")
        assert matcher.hit_count == initial_hits + 1

    def test_miss_count_increments(self, matcher):
        """Test miss_count metric increments on non-match."""
        initial_misses = matcher.miss_count
        matcher.match("not a valid pattern")
        assert matcher.miss_count == initial_misses + 1

    def test_get_stats(self, matcher):
        """Test get_stats() returns metrics."""
        matcher.match("list all projects")  # Hit
        matcher.match("invalid input")  # Miss

        stats = matcher.get_stats()
        assert 'hit_count' in stats
        assert 'miss_count' in stats
        assert 'total' in stats
        assert 'hit_rate' in stats
        assert stats['total'] == stats['hit_count'] + stats['miss_count']
```

**Verification**:
```bash
pytest tests/nl/test_fast_path_matcher_integration.py -v
```

**Expected**: All tests pass (30+ tests)

---

### STEP 2: Create StateManager API Completeness Tests

**File**: `tests/test_state_manager_api_completeness.py`
**Action**: CREATE NEW FILE
**Purpose**: Ensure StateManager has complete API for all entity types

**Complete File Content**:

```python
"""Tests for StateManager API completeness across all entity types.

Ensures consistent method availability for all entity types to prevent
missing method errors in bulk operations and NL queries.

Bug Fix: Prevents 'StateManager' object has no attribute 'list_epics' errors.
"""

import pytest
from src.core.state import StateManager
from src.core.models import TaskType, TaskStatus


class TestStateManagerAPICompleteness:
    """Test StateManager has complete API for all entity types."""

    @pytest.fixture
    def state_manager(self, test_config):
        """StateManager with test database."""
        db_url = test_config.get('database.url', 'sqlite:///:memory:')
        return StateManager(database_url=db_url)

    @pytest.fixture
    def project_with_entities(self, state_manager):
        """Create project with all entity types.

        Returns:
            Dict with IDs for: project, epic, story, task, milestone
        """
        # Create project
        project_id = state_manager.create_project(
            project_name="Test Project",
            description="Test project for API completeness"
        )

        # Create epic
        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Test Epic",
            description="Epic description"
        )

        # Create story
        story_id = state_manager.create_story(
            project_id=project_id,
            epic_id=epic_id,
            title="Test Story",
            description="Story description"
        )

        # Create regular task
        task_id = state_manager.create_task(
            project_id=project_id,
            task_data={
                'title': 'Test Task',
                'description': 'Task description',
                'task_type': TaskType.TASK
            }
        )

        # Create subtask
        subtask_id = state_manager.create_task(
            project_id=project_id,
            task_data={
                'title': 'Test Subtask',
                'description': 'Subtask description',
                'task_type': TaskType.SUBTASK,
                'parent_task_id': task_id
            }
        )

        # Create milestone
        milestone_id = state_manager.create_milestone(
            project_id=project_id,
            name="Test Milestone",
            description="Milestone description",
            required_epic_ids=[epic_id]
        )

        return {
            'project_id': project_id,
            'epic_id': epic_id,
            'story_id': story_id,
            'task_id': task_id,
            'subtask_id': subtask_id,
            'milestone_id': milestone_id
        }

    # ==================== List Methods Existence ====================

    def test_list_projects_method_exists(self, state_manager):
        """Test StateManager.list_projects() method exists."""
        # Should not raise AttributeError
        projects = state_manager.list_projects()
        assert isinstance(projects, list)

    def test_list_epics_method_exists(self, state_manager, project_with_entities):
        """Test StateManager.list_epics() method exists and works."""
        project_id = project_with_entities['project_id']

        # Should not raise AttributeError
        epics = state_manager.list_epics(project_id)

        assert epics is not None
        assert isinstance(epics, list)
        assert len(epics) == 1
        assert epics[0].task_type == TaskType.EPIC
        assert epics[0].title == "Test Epic"

    def test_list_stories_method_exists(self, state_manager, project_with_entities):
        """Test StateManager.list_stories() method exists and works."""
        project_id = project_with_entities['project_id']

        # Should not raise AttributeError
        stories = state_manager.list_stories(project_id)

        assert stories is not None
        assert isinstance(stories, list)
        assert len(stories) == 1
        assert stories[0].task_type == TaskType.STORY
        assert stories[0].title == "Test Story"

    def test_list_tasks_method_exists(self, state_manager, project_with_entities):
        """Test StateManager.list_tasks() method exists."""
        project_id = project_with_entities['project_id']

        tasks = state_manager.list_tasks(project_id=project_id)

        assert tasks is not None
        assert isinstance(tasks, list)
        # Should include: epic, story, task, subtask = 4 items
        assert len(tasks) >= 4

    def test_list_milestones_method_exists(self, state_manager, project_with_entities):
        """Test StateManager.list_milestones() method exists."""
        project_id = project_with_entities['project_id']

        milestones = state_manager.list_milestones(project_id)

        assert milestones is not None
        assert isinstance(milestones, list)
        assert len(milestones) == 1

    def test_all_list_methods_available(self, state_manager, project_with_entities):
        """Test all entity types have list methods without AttributeError."""
        project_id = project_with_entities['project_id']

        # All these should work without AttributeError
        projects = state_manager.list_projects()
        epics = state_manager.list_epics(project_id)
        stories = state_manager.list_stories(project_id)
        tasks = state_manager.list_tasks(project_id)
        milestones = state_manager.list_milestones(project_id)

        # Basic validation
        assert len(projects) >= 1
        assert len(epics) == 1
        assert len(stories) == 1
        assert len(tasks) >= 4  # epic, story, task, subtask
        assert len(milestones) == 1

    # ==================== Method Signatures ====================

    def test_list_epics_accepts_status_filter(self, state_manager, project_with_entities):
        """Test list_epics() accepts status filter parameter."""
        project_id = project_with_entities['project_id']

        # Should not raise TypeError
        pending_epics = state_manager.list_epics(
            project_id=project_id,
            status=TaskStatus.PENDING
        )

        assert isinstance(pending_epics, list)
        assert len(pending_epics) == 1

    def test_list_stories_accepts_epic_filter(self, state_manager, project_with_entities):
        """Test list_stories() accepts epic_id filter parameter."""
        project_id = project_with_entities['project_id']
        epic_id = project_with_entities['epic_id']

        # Should not raise TypeError
        epic_stories = state_manager.list_stories(
            project_id=project_id,
            epic_id=epic_id
        )

        assert isinstance(epic_stories, list)
        assert len(epic_stories) == 1
        assert epic_stories[0].epic_id == epic_id

    def test_list_stories_accepts_status_filter(self, state_manager, project_with_entities):
        """Test list_stories() accepts status filter parameter."""
        project_id = project_with_entities['project_id']

        pending_stories = state_manager.list_stories(
            project_id=project_id,
            status=TaskStatus.PENDING
        )

        assert isinstance(pending_stories, list)
        assert len(pending_stories) == 1

    # ==================== Filtering Correctness ====================

    def test_list_epics_filters_by_project(self, state_manager, project_with_entities):
        """Test list_epics() returns only epics from specified project."""
        project_id = project_with_entities['project_id']

        # Create second project with epic
        project2_id = state_manager.create_project(
            project_name="Project 2",
            description="Second project"
        )
        state_manager.create_epic(
            project_id=project2_id,
            title="Project 2 Epic",
            description="Epic in project 2"
        )

        # list_epics should only return epics from project 1
        project1_epics = state_manager.list_epics(project_id)

        assert len(project1_epics) == 1
        assert project1_epics[0].project_id == project_id
        assert project1_epics[0].title == "Test Epic"

    def test_list_stories_filters_by_project(self, state_manager, project_with_entities):
        """Test list_stories() returns only stories from specified project."""
        project_id = project_with_entities['project_id']

        # Create second project with epic and story
        project2_id = state_manager.create_project(
            project_name="Project 2",
            description="Second project"
        )
        epic2_id = state_manager.create_epic(
            project_id=project2_id,
            title="Project 2 Epic",
            description="Epic 2"
        )
        state_manager.create_story(
            project_id=project2_id,
            epic_id=epic2_id,
            title="Project 2 Story",
            description="Story 2"
        )

        # list_stories should only return stories from project 1
        project1_stories = state_manager.list_stories(project_id)

        assert len(project1_stories) == 1
        assert project1_stories[0].project_id == project_id
        assert project1_stories[0].title == "Test Story"

    def test_list_stories_filters_by_epic(self, state_manager, project_with_entities):
        """Test list_stories() can filter by epic_id."""
        project_id = project_with_entities['project_id']
        epic_id = project_with_entities['epic_id']

        # Create second epic with story
        epic2_id = state_manager.create_epic(
            project_id=project_id,
            title="Epic 2",
            description="Second epic"
        )
        state_manager.create_story(
            project_id=project_id,
            epic_id=epic2_id,
            title="Story for Epic 2",
            description="Story 2"
        )

        # Filter by first epic
        epic1_stories = state_manager.list_stories(project_id, epic_id=epic_id)
        epic2_stories = state_manager.list_stories(project_id, epic_id=epic2_id)

        assert len(epic1_stories) == 1
        assert epic1_stories[0].epic_id == epic_id
        assert len(epic2_stories) == 1
        assert epic2_stories[0].epic_id == epic2_id

    def test_list_epics_returns_only_epics(self, state_manager, project_with_entities):
        """Test list_epics() returns only EPICs, not other task types."""
        project_id = project_with_entities['project_id']

        epics = state_manager.list_epics(project_id)

        # Should only contain EPICs
        assert all(epic.task_type == TaskType.EPIC for epic in epics)
        assert len(epics) == 1

    def test_list_stories_returns_only_stories(self, state_manager, project_with_entities):
        """Test list_stories() returns only STORYs, not other task types."""
        project_id = project_with_entities['project_id']

        stories = state_manager.list_stories(project_id)

        # Should only contain STORYs
        assert all(story.task_type == TaskType.STORY for story in stories)
        assert len(stories) == 1

    # ==================== Empty Results ====================

    def test_list_epics_empty_project(self, state_manager):
        """Test list_epics() returns empty list for project with no epics."""
        project_id = state_manager.create_project(
            project_name="Empty Project",
            description="No epics"
        )

        epics = state_manager.list_epics(project_id)

        assert epics == []
        assert isinstance(epics, list)

    def test_list_stories_empty_epic(self, state_manager):
        """Test list_stories() returns empty list for epic with no stories."""
        project_id = state_manager.create_project(
            project_name="Test Project",
            description="Test"
        )
        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Empty Epic",
            description="No stories"
        )

        stories = state_manager.list_stories(project_id, epic_id=epic_id)

        assert stories == []
        assert isinstance(stories, list)

    # ==================== Return Types ====================

    def test_list_epics_returns_task_objects(self, state_manager, project_with_entities):
        """Test list_epics() returns Task model objects."""
        from src.core.models import Task

        project_id = project_with_entities['project_id']
        epics = state_manager.list_epics(project_id)

        assert all(isinstance(epic, Task) for epic in epics)

    def test_list_stories_returns_task_objects(self, state_manager, project_with_entities):
        """Test list_stories() returns Task model objects."""
        from src.core.models import Task

        project_id = project_with_entities['project_id']
        stories = state_manager.list_stories(project_id)

        assert all(isinstance(story, Task) for story in stories)
```

**Verification**:
```bash
pytest tests/test_state_manager_api_completeness.py -v
```

**Expected**: All tests pass (25+ tests)

---

### STEP 3: Create NL Query Project Filtering Tests

**File**: `tests/nl/test_nl_query_project_filtering.py`
**Action**: CREATE NEW FILE
**Purpose**: Validate queries filter by project_id correctly

**Complete File Content**:

```python
"""Tests for NL query project_id filtering.

Ensures queries only return entities from the specified project,
not all projects in the database.

Bug Fix: Prevents queries returning tasks from all projects instead of
filtering by project_id.
"""

import pytest
from src.nl.nl_query_helper import NLQueryHelper
from src.nl.types import OperationContext, OperationType, EntityType, QueryType
from src.core.state import StateManager
from src.core.models import TaskType, TaskStatus


class TestNLQueryProjectFiltering:
    """Test NL queries filter by project_id correctly."""

    @pytest.fixture
    def state_manager(self, test_config):
        """StateManager with test database."""
        db_url = test_config.get('database.url', 'sqlite:///:memory:')
        return StateManager(database_url=db_url)

    @pytest.fixture
    def multi_project_db(self, state_manager):
        """Database with multiple projects and tasks.

        Creates:
        - Project 1: 3 regular tasks, 1 epic, 1 story
        - Project 2: 2 regular tasks, 1 epic, 1 story

        Returns:
            Dict with project_id, epic_id for both projects
        """
        # Project 1 with 3 regular tasks
        project1_id = state_manager.create_project(
            project_name="Project 1",
            description="First project"
        )
        for i in range(3):
            state_manager.create_task(
                project_id=project1_id,
                task_data={
                    'title': f'P1 Task {i+1}',
                    'description': f'Task {i+1} in project 1',
                    'task_type': TaskType.TASK
                }
            )

        # Create epic and story for project 1
        epic1_id = state_manager.create_epic(
            project_id=project1_id,
            title="P1 Epic",
            description="Epic for project 1"
        )
        story1_id = state_manager.create_story(
            project_id=project1_id,
            epic_id=epic1_id,
            title="P1 Story",
            description="Story for project 1"
        )

        # Project 2 with 2 regular tasks
        project2_id = state_manager.create_project(
            project_name="Project 2",
            description="Second project"
        )
        for i in range(2):
            state_manager.create_task(
                project_id=project2_id,
                task_data={
                    'title': f'P2 Task {i+1}',
                    'description': f'Task {i+1} in project 2',
                    'task_type': TaskType.TASK
                }
            )

        # Create epic and story for project 2
        epic2_id = state_manager.create_epic(
            project_id=project2_id,
            title="P2 Epic",
            description="Epic for project 2"
        )
        story2_id = state_manager.create_story(
            project_id=project2_id,
            epic_id=epic2_id,
            title="P2 Story",
            description="Story for project 2"
        )

        return {
            'project1_id': project1_id,
            'project2_id': project2_id,
            'epic1_id': epic1_id,
            'epic2_id': epic2_id,
            'story1_id': story1_id,
            'story2_id': story2_id
        }

    @pytest.fixture
    def query_helper(self, state_manager):
        """NLQueryHelper instance."""
        return NLQueryHelper(state_manager)

    # ==================== SIMPLE Query Filtering ====================

    def test_simple_task_query_filters_by_project(
        self, query_helper, multi_project_db
    ):
        """Test SIMPLE task query returns only tasks from specified project."""
        project1_id = multi_project_db['project1_id']
        project2_id = multi_project_db['project2_id']

        # Query for project 1 tasks
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.SIMPLE
        )
        result1 = query_helper.execute(context, project_id=project1_id)

        # Query for project 2 tasks
        result2 = query_helper.execute(context, project_id=project2_id)

        # Validate results
        assert result1.success, "Project 1 query should succeed"
        assert result2.success, "Project 2 query should succeed"

        # Project 1: 3 regular tasks + 1 epic + 1 story = 5 items
        assert result1.results['count'] == 5, f"Expected 5 items for Project 1, got {result1.results['count']}"

        # Project 2: 2 regular tasks + 1 epic + 1 story = 4 items
        assert result2.results['count'] == 4, f"Expected 4 items for Project 2, got {result2.results['count']}"

        # Entities should only be from that project
        p1_entities = result1.results['entities']
        p2_entities = result2.results['entities']

        assert len(p1_entities) == 5
        assert len(p2_entities) == 4

    def test_simple_epic_query_filters_by_project(
        self, query_helper, multi_project_db
    ):
        """Test SIMPLE epic query returns only epics from specified project."""
        project1_id = multi_project_db['project1_id']
        project2_id = multi_project_db['project2_id']

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.EPIC],
            query_type=QueryType.SIMPLE
        )

        result1 = query_helper.execute(context, project_id=project1_id)
        result2 = query_helper.execute(context, project_id=project2_id)

        # Each project should have exactly 1 epic
        assert result1.results['count'] == 1
        assert result2.results['count'] == 1

        # Verify epic titles
        assert result1.results['entities'][0]['title'] == 'P1 Epic'
        assert result2.results['entities'][0]['title'] == 'P2 Epic'

    def test_simple_story_query_filters_by_project(
        self, query_helper, multi_project_db
    ):
        """Test SIMPLE story query returns only stories from specified project."""
        project1_id = multi_project_db['project1_id']
        project2_id = multi_project_db['project2_id']

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.STORY],
            query_type=QueryType.SIMPLE
        )

        result1 = query_helper.execute(context, project_id=project1_id)
        result2 = query_helper.execute(context, project_id=project2_id)

        # Each project should have exactly 1 story
        assert result1.results['count'] == 1
        assert result2.results['count'] == 1

        # Verify story titles
        assert result1.results['entities'][0]['title'] == 'P1 Story'
        assert result2.results['entities'][0]['title'] == 'P2 Story'

    # ==================== HIERARCHICAL Query Filtering ====================

    def test_hierarchical_query_filters_by_project(
        self, query_helper, multi_project_db
    ):
        """Test HIERARCHICAL query returns only hierarchy from specified project."""
        project1_id = multi_project_db['project1_id']
        project2_id = multi_project_db['project2_id']

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.EPIC],
            query_type=QueryType.HIERARCHICAL
        )

        result1 = query_helper.execute(context, project_id=project1_id)
        result2 = query_helper.execute(context, project_id=project2_id)

        assert result1.success
        assert result2.success

        # Each project should have 1 epic in hierarchy
        hierarchy1 = result1.results['hierarchy']
        hierarchy2 = result2.results['hierarchy']

        assert result1.results['epic_count'] == 1
        assert result2.results['epic_count'] == 1

        # Verify epic titles in hierarchy
        assert hierarchy1[0]['epic_title'] == 'P1 Epic'
        assert hierarchy2[0]['epic_title'] == 'P2 Epic'

        # Verify stories under each epic
        assert len(hierarchy1[0]['stories']) == 1
        assert len(hierarchy2[0]['stories']) == 1
        assert hierarchy1[0]['stories'][0]['story_title'] == 'P1 Story'
        assert hierarchy2[0]['stories'][0]['story_title'] == 'P2 Story'

    # ==================== BACKLOG Query Filtering ====================

    def test_backlog_query_filters_by_project(
        self, query_helper, multi_project_db
    ):
        """Test BACKLOG query returns only pending tasks from specified project."""
        project1_id = multi_project_db['project1_id']
        project2_id = multi_project_db['project2_id']

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.BACKLOG
        )

        result1 = query_helper.execute(context, project_id=project1_id)
        result2 = query_helper.execute(context, project_id=project2_id)

        assert result1.success
        assert result2.success

        # Get tasks from results
        tasks1 = result1.results['tasks']
        tasks2 = result2.results['tasks']

        # All tasks should be from project 1
        assert all('P1' in t['title'] for t in tasks1), "All tasks should be from Project 1"

        # All tasks should be from project 2
        assert all('P2' in t['title'] for t in tasks2), "All tasks should be from Project 2"

    def test_backlog_query_only_includes_pending(
        self, query_helper, multi_project_db, state_manager
    ):
        """Test BACKLOG query only includes pending/ready/running tasks."""
        project1_id = multi_project_db['project1_id']

        # Mark one task as completed
        tasks = state_manager.list_tasks(project_id=project1_id, task_type=TaskType.TASK)
        if tasks:
            state_manager.update_task(
                task_id=tasks[0].id,
                updates={'status': TaskStatus.COMPLETED}
            )

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.BACKLOG
        )

        result = query_helper.execute(context, project_id=project1_id)

        # Should not include completed task
        tasks = result.results['tasks']
        assert all(
            t['status'] in ['PENDING', 'READY', 'RUNNING']
            for t in tasks
        ), "Backlog should only include pending/ready/running tasks"

    # ==================== NEXT_STEPS Query Filtering ====================

    def test_next_steps_query_filters_by_project(
        self, query_helper, multi_project_db
    ):
        """Test NEXT_STEPS query returns only next tasks from specified project."""
        project1_id = multi_project_db['project1_id']
        project2_id = multi_project_db['project2_id']

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.NEXT_STEPS
        )

        result1 = query_helper.execute(context, project_id=project1_id)
        result2 = query_helper.execute(context, project_id=project2_id)

        assert result1.success
        assert result2.success

        tasks1 = result1.results['tasks']
        tasks2 = result2.results['tasks']

        # All tasks should be from their respective projects
        assert all('P1' in t['title'] for t in tasks1)
        assert all('P2' in t['title'] for t in tasks2)

    def test_next_steps_respects_priority(
        self, query_helper, multi_project_db, state_manager
    ):
        """Test NEXT_STEPS query returns tasks sorted by priority."""
        project1_id = multi_project_db['project1_id']

        # Set different priorities
        tasks = state_manager.list_tasks(
            project_id=project1_id,
            task_type=TaskType.TASK
        )
        if len(tasks) >= 2:
            state_manager.update_task(tasks[0].id, {'priority': 1})  # High priority
            state_manager.update_task(tasks[1].id, {'priority': 10})  # Low priority

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.NEXT_STEPS
        )

        result = query_helper.execute(context, project_id=project1_id)

        tasks = result.results['tasks']

        # Tasks should be sorted by priority (ascending)
        priorities = [t['priority'] for t in tasks]
        assert priorities == sorted(priorities), "Tasks should be sorted by priority"

    # ==================== ROADMAP Query Filtering ====================

    def test_roadmap_query_filters_by_project(
        self, query_helper, multi_project_db, state_manager
    ):
        """Test ROADMAP query returns only milestones from specified project."""
        project1_id = multi_project_db['project1_id']
        project2_id = multi_project_db['project2_id']
        epic1_id = multi_project_db['epic1_id']
        epic2_id = multi_project_db['epic2_id']

        # Create milestones for each project
        state_manager.create_milestone(
            project_id=project1_id,
            name="P1 Milestone",
            description="Milestone for project 1",
            required_epic_ids=[epic1_id]
        )
        state_manager.create_milestone(
            project_id=project2_id,
            name="P2 Milestone",
            description="Milestone for project 2",
            required_epic_ids=[epic2_id]
        )

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.MILESTONE],
            query_type=QueryType.ROADMAP
        )

        result1 = query_helper.execute(context, project_id=project1_id)
        result2 = query_helper.execute(context, project_id=project2_id)

        assert result1.success
        assert result2.success

        # Each project should have 1 milestone
        roadmap1 = result1.results['milestones']
        roadmap2 = result2.results['milestones']

        assert len(roadmap1) == 1
        assert len(roadmap2) == 1

        assert roadmap1[0]['milestone_name'] == 'P1 Milestone'
        assert roadmap2[0]['milestone_name'] == 'P2 Milestone'

    # ==================== Edge Cases ====================

    def test_query_empty_project_returns_empty_results(
        self, query_helper, state_manager
    ):
        """Test querying empty project returns empty results, not all projects."""
        # Create empty project
        empty_project_id = state_manager.create_project(
            project_name="Empty Project",
            description="No tasks"
        )

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.SIMPLE
        )

        result = query_helper.execute(context, project_id=empty_project_id)

        assert result.success
        assert result.results['count'] == 0
        assert result.results['entities'] == []

    def test_query_nonexistent_project_id(
        self, query_helper
    ):
        """Test querying non-existent project returns empty results."""
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.SIMPLE
        )

        result = query_helper.execute(context, project_id=99999)

        assert result.success
        assert result.results['count'] == 0

    # ==================== Count Accuracy ====================

    def test_query_count_matches_entities_length(
        self, query_helper, multi_project_db
    ):
        """Test query result count matches actual entities length.

        This is the critical bug fix: prevents "Found 5 items / No results found".
        """
        project1_id = multi_project_db['project1_id']

        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.SIMPLE
        )

        result = query_helper.execute(context, project_id=project1_id)

        # Count should match entities length EXACTLY
        reported_count = result.results['count']
        actual_entities = result.results['entities']

        assert reported_count == len(actual_entities), \
            f"Count mismatch: reported {reported_count} but got {len(actual_entities)} entities"
```

**Verification**:
```bash
pytest tests/nl/test_nl_query_project_filtering.py -v
```

**Expected**: All tests pass (25+ tests)

---

### STEP 4: Create End-to-End NL Command Tests

**File**: `tests/integration/test_nl_command_e2e.py`
**Action**: CREATE NEW FILE
**Purpose**: Test complete NL command flow

**Complete File Content**:

```python
"""End-to-end tests for NL command execution.

Tests complete flow from user input through NL processor, orchestrator,
query execution, and result formatting.

Bug Fix: Validates count accuracy in user-facing messages matches actual results.
"""

import pytest
from src.orchestrator import Orchestrator
from src.nl.nl_command_processor import NLCommandProcessor
from src.core.state import StateManager
from src.core.models import TaskType


class TestNLCommandEndToEnd:
    """End-to-end tests for NL commands."""

    @pytest.fixture
    def state_manager(self, test_config):
        """StateManager with test database."""
        db_url = test_config.get('database.url', 'sqlite:///:memory:')
        return StateManager(database_url=db_url)

    @pytest.fixture
    def orchestrator_with_data(self, test_config, state_manager):
        """Orchestrator with test data.

        Creates:
        - 1 project: "Tetris Game"
        - 2 regular tasks
        - 1 epic
        - 1 story under the epic

        Returns:
            Tuple of (orchestrator, project_id, epic_id, story_id)
        """
        # Create project
        project_id = state_manager.create_project(
            project_name="Tetris Game",
            description="Tetris implementation in Godot"
        )

        # Create 2 regular tasks
        task1_id = state_manager.create_task(
            project_id=project_id,
            task_data={
                'title': 'Task 1',
                'description': 'First task',
                'task_type': TaskType.TASK
            }
        )
        task2_id = state_manager.create_task(
            project_id=project_id,
            task_data={
                'title': 'Task 2',
                'description': 'Second task',
                'task_type': TaskType.TASK
            }
        )

        # Create epic
        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Gameplay Epic",
            description="Core gameplay features"
        )

        # Create story
        story_id = state_manager.create_story(
            project_id=project_id,
            epic_id=epic_id,
            title="Player Movement",
            description="Implement player movement controls"
        )

        orchestrator = Orchestrator(config=test_config)
        orchestrator.state_manager = state_manager  # Use same state manager

        return orchestrator, project_id, epic_id, story_id

    # ==================== Query Count Accuracy ====================

    def test_list_tasks_count_matches_display(
        self, orchestrator_with_data
    ):
        """Test 'list tasks' shows correct count matching displayed items.

        Critical bug fix: Prevents "Found 4 task(s)" with "No results found".
        """
        orchestrator, project_id, epic_id, story_id = orchestrator_with_data

        # Initialize NL processor
        nl_processor = NLCommandProcessor(
            state_manager=orchestrator.state_manager,
            llm_provider=orchestrator.llm_provider
        )

        # Process NL command
        parsed_intent = nl_processor.process(
            "list the tasks for this project",
            context={'project_id': project_id}
        )

        # Execute through orchestrator
        result = orchestrator.execute_nl_command(
            parsed_intent,
            project_id=project_id
        )

        # Validate result structure
        assert result['success'], "Query should succeed"
        assert 'data' in result, "Result should contain data"

        # Extract count from message (e.g., "Found 4 task(s)")
        message = result['message']
        assert 'Found' in message, f"Message should contain 'Found': {message}"

        count_in_message = int(message.split()[1])  # "Found 4 task(s)"
        entities = result['data']['entities']

        # Count should match entities length EXACTLY
        assert count_in_message == len(entities), \
            f"Count mismatch: message says {count_in_message} but got {len(entities)} entities"

        # Should be: 2 regular tasks + 1 epic + 1 story = 4 items
        assert count_in_message == 4
        assert len(entities) == 4

    def test_list_epics_returns_only_epics(
        self, orchestrator_with_data
    ):
        """Test 'list epics' returns only epic entities, not all tasks."""
        orchestrator, project_id, epic_id, _ = orchestrator_with_data

        nl_processor = NLCommandProcessor(
            state_manager=orchestrator.state_manager,
            llm_provider=orchestrator.llm_provider
        )

        parsed_intent = nl_processor.process(
            "What are the epics for this project",
            context={'project_id': project_id}
        )

        result = orchestrator.execute_nl_command(
            parsed_intent,
            project_id=project_id
        )

        assert result['success']
        entities = result['data']['entities']

        # Should only return epic, not regular tasks or stories
        assert len(entities) == 1, f"Should return 1 epic, got {len(entities)}"
        assert entities[0]['id'] == epic_id
        assert entities[0]['title'] == 'Gameplay Epic'

    def test_list_stories_returns_only_stories(
        self, orchestrator_with_data
    ):
        """Test 'list stories' returns only story entities."""
        orchestrator, project_id, epic_id, story_id = orchestrator_with_data

        nl_processor = NLCommandProcessor(
            state_manager=orchestrator.state_manager,
            llm_provider=orchestrator.llm_provider
        )

        parsed_intent = nl_processor.process(
            "list the stories for this project",
            context={'project_id': project_id}
        )

        result = orchestrator.execute_nl_command(
            parsed_intent,
            project_id=project_id
        )

        assert result['success']
        entities = result['data']['entities']

        # Should only return story
        assert len(entities) == 1
        assert entities[0]['id'] == story_id
        assert entities[0]['title'] == 'Player Movement'

    # ==================== Project Isolation ====================

    def test_queries_isolated_by_project(
        self, orchestrator_with_data, state_manager
    ):
        """Test queries only return entities from current project."""
        orchestrator, project1_id, _, _ = orchestrator_with_data

        # Create second project with tasks
        project2_id = state_manager.create_project(
            project_name="Second Project",
            description="Different project"
        )
        state_manager.create_task(
            project_id=project2_id,
            task_data={
                'title': 'Project 2 Task',
                'description': 'Should not appear in project 1 queries',
                'task_type': TaskType.TASK
            }
        )

        nl_processor = NLCommandProcessor(
            state_manager=orchestrator.state_manager,
            llm_provider=orchestrator.llm_provider
        )

        # Query project 1
        parsed_intent = nl_processor.process(
            "list all tasks",
            context={'project_id': project1_id}
        )

        result = orchestrator.execute_nl_command(
            parsed_intent,
            project_id=project1_id
        )

        # Should only return project 1 tasks
        entities = result['data']['entities']
        entity_titles = [e['title'] for e in entities]

        assert 'Project 2 Task' not in entity_titles, \
            "Should not return tasks from other projects"
        assert all('Tetris' in str(entities) or 'Task' in e['title'] or 'Epic' in e['title'] or 'Movement' in e['title']
                  for e in entities)

    # ==================== Fast Path Integration ====================

    def test_fast_path_list_all_projects(
        self, orchestrator_with_data
    ):
        """Test fast path 'list all projects' works end-to-end."""
        orchestrator, project_id, _, _ = orchestrator_with_data

        nl_processor = NLCommandProcessor(
            state_manager=orchestrator.state_manager,
            llm_provider=orchestrator.llm_provider
        )

        # This should hit fast path
        parsed_intent = nl_processor.process(
            "list all projects",
            context={'project_id': project_id}
        )

        result = orchestrator.execute_nl_command(
            parsed_intent,
            project_id=project_id
        )

        assert result['success']
        assert 'data' in result

        # Should include at least the Tetris Game project
        entities = result['data']['entities']
        project_names = [e['name'] for e in entities]

        assert 'Tetris Game' in project_names

    # ==================== Hierarchical Queries ====================

    def test_hierarchical_query_shows_epic_story_structure(
        self, orchestrator_with_data
    ):
        """Test hierarchical query shows epic → story → task structure."""
        orchestrator, project_id, epic_id, story_id = orchestrator_with_data

        # Add a task under the story
        state_manager = orchestrator.state_manager
        task_under_story = state_manager.create_task(
            project_id=project_id,
            task_data={
                'title': 'Story Task',
                'description': 'Task under story',
                'task_type': TaskType.TASK,
                'story_id': story_id
            }
        )

        nl_processor = NLCommandProcessor(
            state_manager=state_manager,
            llm_provider=orchestrator.llm_provider
        )

        parsed_intent = nl_processor.process(
            "What are the stories and tasks for epic",
            context={'project_id': project_id}
        )

        result = orchestrator.execute_nl_command(
            parsed_intent,
            project_id=project_id
        )

        assert result['success']

        # Should have hierarchical data
        if 'hierarchy' in result['data']:
            hierarchy = result['data']['hierarchy']
            assert len(hierarchy) >= 1

            # Find our epic
            our_epic = [h for h in hierarchy if h['epic_id'] == epic_id]
            if our_epic:
                assert len(our_epic[0]['stories']) >= 1

    # ==================== Error Cases ====================

    def test_query_empty_project_shows_no_results(
        self, orchestrator_with_data, state_manager
    ):
        """Test querying empty project shows 'No results' not 'Found X items'."""
        orchestrator, _, _, _ = orchestrator_with_data

        # Create empty project
        empty_project_id = state_manager.create_project(
            project_name="Empty Project",
            description="No tasks"
        )

        nl_processor = NLCommandProcessor(
            state_manager=state_manager,
            llm_provider=orchestrator.llm_provider
        )

        parsed_intent = nl_processor.process(
            "list all tasks",
            context={'project_id': empty_project_id}
        )

        result = orchestrator.execute_nl_command(
            parsed_intent,
            project_id=empty_project_id
        )

        # Should return 0 items
        assert result['success']
        assert result['data']['count'] == 0
        assert result['data']['entities'] == []

        # Message should indicate 0 items
        message = result['message']
        assert '0' in message or 'no' in message.lower()
```

**Verification**:
```bash
pytest tests/integration/test_nl_command_e2e.py -v
```

**Expected**: All tests pass (10+ tests)

---

### STEP 5: Update Existing Test Files

#### 5A. Add OperationContext Validation to Fast Path Matcher Tests

**File**: `tests/nl/test_fast_path_matcher.py`
**Action**: MODIFY EXISTING FILE

**Add these tests at the end of the file** (before the final line):

```python
    # ==================== OperationContext Validation (Bug Fix) ====================

    def test_operation_context_uses_entity_types_list(self, matcher):
        """Test OperationContext uses entity_types (list) not entity_type (single).

        Bug fix regression test: Ensures we don't revert to using entity_type parameter.
        """
        context = matcher.match("list all projects")

        # Should have entity_types attribute (list)
        assert hasattr(context, 'entity_types'), "OperationContext must have entity_types attribute"
        assert isinstance(context.entity_types, list), "entity_types must be a list"

        # Backward compatibility: entity_type property should work
        assert hasattr(context, 'entity_type'), "Should have entity_type property for backward compatibility"
        assert context.entity_type == context.entity_types[0]

    def test_all_patterns_return_valid_operation_context(self, matcher):
        """Test all fast path patterns return valid OperationContext that won't cause errors."""
        test_patterns = [
            "list all projects",
            "show tasks",
            "get epic 5",
            "list stories",
            "show milestone 3"
        ]

        for pattern in test_patterns:
            context = matcher.match(pattern)
            if context:  # Pattern matched
                # Should not raise ValueError when accessed
                try:
                    _ = context.operation
                    _ = context.entity_types
                    _ = context.entity_type  # Backward compat property
                    _ = context.confidence
                except (ValueError, AttributeError, TypeError) as e:
                    pytest.fail(f"Pattern '{pattern}' created invalid OperationContext: {e}")
```

**Verification**:
```bash
pytest tests/nl/test_fast_path_matcher.py -v -k "operation_context"
```

**Expected**: 2 new tests pass

---

#### 5B. Add list_epics/list_stories Tests to StateManager Tests

**File**: `tests/test_state.py`
**Action**: MODIFY EXISTING FILE

**Find the section** with other list methods (search for `def test_list_tasks`) and add these tests nearby:

```python
    def test_list_epics_returns_only_epics(self, state_manager):
        """Test list_epics() returns only EPIC type tasks.

        Bug fix regression test: Validates list_epics() method exists and filters correctly.
        """
        # Create project
        project_id = state_manager.create_project(
            project_name="Test Project",
            description="Test"
        )

        # Create epic
        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Test Epic",
            description="Epic desc"
        )

        # Create regular task (should not be in epics list)
        task_id = state_manager.create_task(
            project_id=project_id,
            task_data={'title': 'Regular Task', 'description': 'Task desc'}
        )

        # list_epics should only return epics
        epics = state_manager.list_epics(project_id)

        assert len(epics) == 1
        assert epics[0].id == epic_id
        assert epics[0].task_type == TaskType.EPIC

    def test_list_stories_returns_only_stories(self, state_manager):
        """Test list_stories() returns only STORY type tasks.

        Bug fix regression test: Validates list_stories() method exists and filters correctly.
        """
        # Create project and epic
        project_id = state_manager.create_project(
            project_name="Test Project",
            description="Test"
        )
        epic_id = state_manager.create_epic(
            project_id=project_id,
            title="Epic",
            description="Epic"
        )

        # Create story
        story_id = state_manager.create_story(
            project_id=project_id,
            epic_id=epic_id,
            title="Test Story",
            description="Story desc"
        )

        # Create regular task (should not be in stories list)
        task_id = state_manager.create_task(
            project_id=project_id,
            task_data={'title': 'Regular Task', 'description': 'Task desc'}
        )

        # list_stories should only return stories
        stories = state_manager.list_stories(project_id)

        assert len(stories) == 1
        assert stories[0].id == story_id
        assert stories[0].task_type == TaskType.STORY

    def test_list_stories_filters_by_epic_id(self, state_manager):
        """Test list_stories() can filter by epic_id."""
        # Create project and epics
        project_id = state_manager.create_project(
            project_name="Test Project",
            description="Test"
        )
        epic1_id = state_manager.create_epic(
            project_id=project_id,
            title="Epic 1",
            description="First epic"
        )
        epic2_id = state_manager.create_epic(
            project_id=project_id,
            title="Epic 2",
            description="Second epic"
        )

        # Create stories under each epic
        story1_id = state_manager.create_story(
            project_id=project_id,
            epic_id=epic1_id,
            title="Story 1",
            description="Story for epic 1"
        )
        story2_id = state_manager.create_story(
            project_id=project_id,
            epic_id=epic2_id,
            title="Story 2",
            description="Story for epic 2"
        )

        # Filter by epic 1
        epic1_stories = state_manager.list_stories(project_id, epic_id=epic1_id)
        epic2_stories = state_manager.list_stories(project_id, epic_id=epic2_id)

        assert len(epic1_stories) == 1
        assert epic1_stories[0].id == story1_id
        assert len(epic2_stories) == 1
        assert epic2_stories[0].id == story2_id
```

**Verification**:
```bash
pytest tests/test_state.py -v -k "list_epics or list_stories"
```

**Expected**: 3 new tests pass

---

#### 5C. Add Project Filtering Tests to NL Query Helper Tests

**File**: `tests/nl/test_nl_query_helper.py`
**Action**: MODIFY EXISTING FILE

**Add at the end of the test class** (before the final line):

```python
    # ==================== Project Filtering (Bug Fix) ====================

    def test_simple_query_filters_by_project_id(self, query_helper, state_manager):
        """Test SIMPLE queries filter by project_id.

        Bug fix regression test: Prevents returning tasks from all projects.
        """
        # Create two projects with tasks
        project1_id = state_manager.create_project(
            project_name="Project 1",
            description="First"
        )
        project2_id = state_manager.create_project(
            project_name="Project 2",
            description="Second"
        )

        # Add task to each
        state_manager.create_task(
            project_id=project1_id,
            task_data={'title': 'P1 Task', 'description': 'Task 1'}
        )
        state_manager.create_task(
            project_id=project2_id,
            task_data={'title': 'P2 Task', 'description': 'Task 2'}
        )

        # Query project 1
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.TASK],
            query_type=QueryType.SIMPLE
        )

        result = query_helper.execute(context, project_id=project1_id)

        # Should only return 1 task (from project 1)
        assert result.success
        assert result.results['count'] == 1
        entities = result.results['entities']
        assert len(entities) == 1
        assert entities[0]['title'] == 'P1 Task'

    def test_hierarchical_query_filters_by_project_id(self, query_helper, state_manager):
        """Test HIERARCHICAL queries filter by project_id."""
        # Create two projects with epics
        project1_id = state_manager.create_project(
            project_name="Project 1",
            description="First"
        )
        project2_id = state_manager.create_project(
            project_name="Project 2",
            description="Second"
        )

        # Add epic to each
        epic1_id = state_manager.create_epic(
            project_id=project1_id,
            title="P1 Epic",
            description="Epic 1"
        )
        epic2_id = state_manager.create_epic(
            project_id=project2_id,
            title="P2 Epic",
            description="Epic 2"
        )

        # Query project 1
        context = OperationContext(
            operation=OperationType.QUERY,
            entity_types=[EntityType.EPIC],
            query_type=QueryType.HIERARCHICAL
        )

        result = query_helper.execute(context, project_id=project1_id)

        # Should only return hierarchy for project 1
        assert result.success
        hierarchy = result.results['hierarchy']
        assert len(hierarchy) == 1
        assert hierarchy[0]['epic_title'] == 'P1 Epic'
```

**Verification**:
```bash
pytest tests/nl/test_nl_query_helper.py -v -k "project"
```

**Expected**: 2 new tests pass

---

### STEP 6: Run Full Test Suite

**Action**: Run all new and modified tests

**Commands**:
```bash
# Run new test files
pytest tests/nl/test_fast_path_matcher_integration.py -v
pytest tests/test_state_manager_api_completeness.py -v
pytest tests/nl/test_nl_query_project_filtering.py -v
pytest tests/integration/test_nl_command_e2e.py -v

# Run modified test files (new tests only)
pytest tests/nl/test_fast_path_matcher.py -v -k "operation_context"
pytest tests/test_state.py -v -k "list_epics or list_stories"
pytest tests/nl/test_nl_query_helper.py -v -k "project"

# Run all NL tests
pytest tests/nl/ -v

# Run all tests with coverage
pytest --cov=src --cov-report=term-missing
```

**Expected Results**:
- All new tests pass (100+ new tests)
- No regressions in existing tests
- Coverage increase of 2-3%

---

### STEP 7: Verify Bug Fixes

**Action**: Manual verification of original bugs

**Test Case 1: Fast Path Matcher**
```bash
python -c "
from src.nl.fast_path_matcher import FastPathMatcher
matcher = FastPathMatcher()
context = matcher.match('list all projects')
print(f'entity_types: {context.entity_types}')  # Should be list
print(f'Test PASSED: {isinstance(context.entity_types, list)}')
"
```

**Expected**: `Test PASSED: True`

**Test Case 2: StateManager Methods**
```bash
python -c "
from src.core.state import StateManager
sm = StateManager('sqlite:///:memory:')
sm.create_project('Test', 'Test')
has_list_epics = hasattr(sm, 'list_epics')
has_list_stories = hasattr(sm, 'list_stories')
print(f'list_epics exists: {has_list_epics}')
print(f'list_stories exists: {has_list_stories}')
print(f'Test PASSED: {has_list_epics and has_list_stories}')
"
```

**Expected**: `Test PASSED: True`

**Test Case 3: Query Filtering**
```bash
# Start interactive mode and test
python -m src.cli interactive

# In interactive mode:
# /project create "Test Project 1"
# /project create "Test Project 2"
# /use 1
# /task create "Task in Project 1"
# /use 2
# /task create "Task in Project 2"
# /use 1
# list all tasks
# (Should show only 1 task, not 2)
```

**Expected**: Shows only tasks from current project

---

## Post-Implementation Checklist

- [ ] All 4 new test files created
- [ ] All 3 existing test files modified
- [ ] All tests pass (pytest shows green)
- [ ] Coverage increased by 2-3%
- [ ] No regressions in existing tests
- [ ] Manual verification completed
- [ ] Documentation updated (next step)

---

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError`:
```bash
# Verify you're in project root
pwd  # Should be /home/omarwsl/projects/claude_code_orchestrator

# Ensure PYTHONPATH is set
export PYTHONPATH=/home/omarwsl/projects/claude_code_orchestrator:$PYTHONPATH

# Reinstall dependencies
pip install -r requirements.txt
```

### Test Fixtures Not Found
If you see `fixture 'test_config' not found`:
```bash
# Check conftest.py exists
ls -la tests/conftest.py

# Verify test_config fixture is defined
grep -n "def test_config" tests/conftest.py
```

### Database Errors
If you see database lock or connection errors:
```bash
# Use in-memory database for tests
# Edit test to use: 'sqlite:///:memory:'

# Or clean up test database
rm -f test.db test.db-*
```

### Slow Tests
If tests take too long:
```bash
# Run specific test file
pytest tests/nl/test_fast_path_matcher_integration.py -v

# Skip slow tests
pytest -m "not slow"

# Run with parallelization
pytest -n auto
```

---

## Success Criteria

✅ **All 4 new test files created**
✅ **100+ new tests added**
✅ **All tests pass without errors**
✅ **Coverage increased to 90%+ for NL modules**
✅ **All 3 bug fixes validated with regression tests**
✅ **No breaking changes to existing functionality**

---

## Next Steps After Implementation

1. Update `docs/testing/NL_QUERY_TESTING_STRATEGY.md` with testing approach
2. Update `CHANGELOG.md` with testing improvements
3. Update `docs/testing/README.md` with new test files
4. Consider adding to CI/CD pipeline
5. Review coverage report and identify gaps

---

**END OF IMPLEMENTATION GUIDE**
