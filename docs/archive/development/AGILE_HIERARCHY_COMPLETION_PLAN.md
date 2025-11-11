# Agile Hierarchy Implementation - Completion Plan

**Purpose**: Complete the Agile/Scrum work hierarchy implementation to production-ready status
**Status**: Phase 1 Complete (Core Implementation) - 70% done
**Remaining Work**: Phase 2 (Production Readiness) - 30% remaining
**ADR**: ADR-013 - Adopt Agile/Scrum Work Hierarchy
**Estimated Time**: 16 hours (2 days)

---

## Executive Summary

**What's Done** (Phase 1 - 24 hours):
- ✅ Database schema: TaskType enum, Task updates, Milestone model
- ✅ StateManager: Epic/story/milestone CRUD methods
- ✅ Orchestrator: execute_epic() method
- ✅ CLI: epic, story, milestone command groups (create/execute/check/achieve)
- ✅ Migration script: 003_agile_hierarchy.sql
- ✅ Smoke tests: 9 tests covering core functionality (100% pass rate)
- ✅ Documentation: CHANGELOG.md updated

**What's Remaining** (Phase 2 - 16 hours):
- 🔲 Rename helper methods (orchestrator session management)
- 🔲 Update existing tests (remove old terminology references)
- 🔲 Add comprehensive CLI commands (list, show, update)
- 🔲 Enhance validation and error handling
- 🔲 Update documentation suite (guides, architecture, CLAUDE.md)
- 🔲 Add integration tests (real orchestration flows)
- 🔲 Add metrics/reporting for Agile hierarchy
- 🔲 Performance testing and optimization

---

## Current State Assessment

### Core Implementation Status

| Component | Status | Coverage | Notes |
|-----------|--------|----------|-------|
| Database Schema | ✅ Complete | 100% | TaskType, Milestone model |
| StateManager | ✅ Complete | 85% | Core CRUD methods working |
| Orchestrator | ⚠️ Partial | 60% | execute_epic() works, helper methods need rename |
| CLI Commands | ⚠️ Partial | 50% | Create/execute work, missing list/show/update |
| Tests | ⚠️ Partial | 15% | 9 smoke tests, need 150+ comprehensive tests |
| Documentation | ⚠️ Partial | 40% | CHANGELOG updated, guides need updates |

### Known Issues

1. **Helper Method Naming**: `_start_milestone_session()` should be `_start_epic_session()`
2. **Variable Naming**: `_current_milestone_id` should be `_current_epic_id`
3. **Test Coverage**: Only 9 smoke tests, need comprehensive coverage
4. **CLI Gaps**: No list/show/update commands for epic/story/milestone
5. **Documentation Gaps**: Guides still reference old "milestone" terminology
6. **Integration Testing**: No tests with real orchestration flows

### Production Readiness Gaps

1. **Error Handling**: Limited validation in CLI commands
2. **Metrics**: No reporting on epic/story progress
3. **Performance**: Untested with large hierarchies (100+ stories)
4. **Migration Validation**: No automated migration testing
5. **Backward Compatibility**: No tests for existing task behavior
6. **CLI Usability**: No interactive wizards or bulk operations
7. **API Consistency**: Some methods inconsistent signatures

---

## Phase 2: Production Readiness Implementation

### Overview

**Total Effort**: 16 hours (2 days)
**Test Coverage Target**: ≥85% (maintain current level)
**Files to Modify**: ~25 files
**New Code**: ~2,000 lines
**Test Code**: ~1,500 lines

### Task Breakdown

#### Epic 1: Code Quality & Consistency (6 hours)

**Story 1.1: Rename Helper Methods in Orchestrator** (2 hours)
- Task: Rename `_start_milestone_session()` → `_start_epic_session()`
- Task: Rename `_end_milestone_session()` → `_end_epic_session()`
- Task: Rename `_build_milestone_context()` → `_build_epic_context()`
- Task: Update variable names (`_current_milestone_id` → `_current_epic_id`)
- Task: Update docstrings and comments
- Acceptance: All renamed, no references to old names

**Story 1.2: Update Existing Tests** (3 hours)
- Task: Audit all test files for "milestone" references
- Task: Update test_orchestrator.py (rename execute_milestone tests)
- Task: Update test_state.py (add TaskType to task creation)
- Task: Update integration tests (use epic terminology)
- Task: Verify no test failures from changes
- Acceptance: All existing tests pass with new terminology

**Story 1.3: Code Quality Checks** (1 hour)
- Task: Run mypy type checking
- Task: Run pylint on modified files
- Task: Verify no new linting warnings
- Task: Update .gitignore if needed
- Acceptance: All quality checks pass

#### Epic 2: Enhanced CLI Commands (4 hours)

**Story 2.1: Epic Management Commands** (1.5 hours)
- Task: Add `obra epic list` command (filter by project, status)
- Task: Add `obra epic show <id>` command (detailed view with stories)
- Task: Add `obra epic update <id>` command (title, description, priority)
- Task: Add `obra epic delete <id>` command (soft delete)
- Acceptance: All commands work, proper error messages

**Story 2.2: Story Management Commands** (1.5 hours)
- Task: Add `obra story list` command (filter by epic, status)
- Task: Add `obra story show <id>` command (detailed view with tasks)
- Task: Add `obra story update <id>` command
- Task: Add `obra story move <id> --epic <new_epic>` command
- Acceptance: All commands work, validation in place

**Story 2.3: Milestone Management Commands** (1 hour)
- Task: Add `obra milestone list` command (filter by project)
- Task: Add `obra milestone show <id>` command (progress view)
- Task: Add `obra milestone update <id>` command
- Task: Add auto-achieve feature (check on epic completion)
- Acceptance: Commands work, auto-achieve tested

#### Epic 3: Comprehensive Testing (4 hours)

**Story 3.1: StateManager Tests** (1.5 hours)
- Task: Test epic creation edge cases (invalid project, validation)
- Task: Test story creation edge cases (invalid epic, non-epic parent)
- Task: Test get_epic_stories with filters and sorting
- Task: Test milestone completion complex scenarios
- Task: Test cascade delete behavior
- Acceptance: 40+ new tests, ≥90% StateManager coverage

**Story 3.2: Orchestrator Tests** (1.5 hours)
- Task: Test execute_epic with multiple stories
- Task: Test execute_epic with failed stories
- Task: Test execute_epic with no stories
- Task: Test session management for epics
- Task: Test context building for epic execution
- Acceptance: 30+ new tests, ≥85% Orchestrator coverage

**Story 3.3: Integration Tests** (1 hour)
- Task: Test full epic workflow (create → add stories → execute → complete)
- Task: Test milestone tracking across epics
- Task: Test backward compatibility (existing tasks still work)
- Task: Test migration script (apply → verify → rollback)
- Acceptance: 15+ integration tests, all workflows tested

#### Epic 4: Documentation Updates (2 hours)

**Story 4.1: Technical Documentation** (1 hour)
- Task: Update CLAUDE.md (replace milestone → epic terminology)
- Task: Update docs/architecture/ARCHITECTURE.md
- Task: Update docs/guides/GETTING_STARTED.md
- Task: Update docs/guides/CLI_REFERENCE.md
- Task: Update docs/architecture/data_flow.md
- Acceptance: All docs use correct terminology

**Story 4.2: User Guides** (1 hour)
- Task: Create docs/guides/AGILE_WORKFLOW_GUIDE.md
- Task: Add examples to CLI_REFERENCE.md
- Task: Update README.md with Agile hierarchy info
- Task: Create migration guide for existing users
- Acceptance: Complete user-facing documentation

---

## Detailed Implementation Steps

### STEP 1: Rename Helper Methods (2 hours)

**Objective**: Update orchestrator to use consistent epic terminology

**File**: `src/orchestrator.py`

**Actions**:

1.1. **Rename Session Methods**

Search and replace:
```python
# OLD → NEW
_start_milestone_session → _start_epic_session
_end_milestone_session → _end_epic_session
_build_milestone_context → _build_epic_context
```

1.2. **Update Variable Names**

In `__init__` method (around line 125):
```python
# OLD
self._current_milestone_id: Optional[int] = None
self._current_milestone_context: Optional[str] = None
self._current_milestone_first_task: Optional[int] = None

# NEW
self._current_epic_id: Optional[int] = None
self._current_epic_context: Optional[str] = None
self._current_epic_first_task: Optional[int] = None
```

1.3. **Update Method Implementations**

`_start_epic_session()` (line ~539):
```python
def _start_epic_session(self, project_id: int, epic_id: Optional[int] = None) -> str:
    """Start a new session for epic execution.

    Args:
        project_id: Project ID
        epic_id: Epic task ID

    Returns:
        Session UUID
    """
    session_id = str(uuid.uuid4())
    self.current_session_id = session_id

    session = SessionRecord(
        session_id=session_id,
        project_id=project_id,
        milestone_id=epic_id,  # Note: DB column still named milestone_id
        started_at=datetime.now(UTC),
        status='active'
    )
    # ... rest of implementation
```

1.4. **Update References in execute_epic()**

Update all variable references in execute_epic() method.

**Validation**:
```bash
# Verify no old references remain
grep -r "_.*milestone_" src/orchestrator.py
# Should return no results (except comments/docstrings mentioning old behavior)

# Run orchestrator tests
pytest tests/test_orchestrator.py -v
```

---

### STEP 2: Enhanced CLI Commands (4 hours)

**Objective**: Add list/show/update/delete commands for complete CRUD operations

**File**: `src/cli.py`

**Actions**:

2.1. **Epic List Command**

```python
@epic.command('list')
@click.option('--project', '-p', type=int, help='Filter by project ID')
@click.option('--status', '-s', help='Filter by status (pending, running, completed, failed)')
@click.pass_context
def epic_list(ctx, project: Optional[int], status: Optional[str]):
    """List all epics."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        # Get all epics
        from src.core.models import TaskType, TaskStatus
        with state_manager._session_scope() as session:
            query = session.query(Task).filter(
                Task.task_type == TaskType.EPIC,
                Task.is_deleted == False
            )

            if project:
                query = query.filter(Task.project_id == project)
            if status:
                query = query.filter(Task.status == TaskStatus[status.upper()])

            epics = query.order_by(desc(Task.created_at)).all()

        if not epics:
            click.echo("No epics found")
            return

        click.echo(f"\nFound {len(epics)} epic(s):\n")
        for epic in epics:
            stories = state_manager.get_epic_stories(epic.id)
            status_icon = "✓" if epic.status == TaskStatus.COMPLETED else "○"
            click.echo(f"{status_icon} Epic #{epic.id}: {epic.title}")
            click.echo(f"   Status: {epic.status.value} | Priority: {epic.priority}")
            click.echo(f"   Stories: {len(stories)} | Project: #{epic.project_id}")
            click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to list epics: {e}", err=True)
        sys.exit(1)
```

2.2. **Epic Show Command**

```python
@epic.command('show')
@click.argument('epic_id', type=int)
@click.pass_context
def epic_show(ctx, epic_id: int):
    """Show detailed epic information."""
    try:
        config = ctx.obj['config']
        db_url = config.get('database.url', 'sqlite:///orchestrator.db')
        state_manager = StateManager.get_instance(db_url)

        epic = state_manager.get_task(epic_id)
        if not epic or epic.task_type != TaskType.EPIC:
            click.echo(f"✗ Epic {epic_id} not found", err=True)
            sys.exit(1)

        stories = state_manager.get_epic_stories(epic_id)

        click.echo(f"\n{'='*60}")
        click.echo(f"Epic #{epic.id}: {epic.title}")
        click.echo(f"{'='*60}")
        click.echo(f"Status: {epic.status.value}")
        click.echo(f"Priority: {epic.priority}/10")
        click.echo(f"Project: #{epic.project_id}")
        click.echo(f"Created: {epic.created_at.strftime('%Y-%m-%d %H:%M')}")
        if epic.description:
            click.echo(f"\nDescription:\n{epic.description}")

        click.echo(f"\n{'─'*60}")
        click.echo(f"Stories ({len(stories)}):")
        click.echo(f"{'─'*60}")

        if stories:
            completed = sum(1 for s in stories if s.status == TaskStatus.COMPLETED)
            click.echo(f"Progress: {completed}/{len(stories)} completed\n")

            for story in stories:
                status_icon = "✓" if story.status == TaskStatus.COMPLETED else "○"
                click.echo(f"  {status_icon} Story #{story.id}: {story.title}")
                click.echo(f"     Status: {story.status.value}")
        else:
            click.echo("  No stories yet")

        click.echo()

    except Exception as e:
        click.echo(f"✗ Failed to show epic: {e}", err=True)
        sys.exit(1)
```

2.3. **Similar Patterns for Story and Milestone**

Repeat similar patterns for story list/show/update and milestone list/show/update.

**Validation**:
```bash
# Test CLI commands
obra epic list
obra epic show 1
obra story list --epic 1
obra milestone list --project 1
```

---

### STEP 3: Comprehensive Testing (4 hours)

**Objective**: Achieve ≥85% test coverage with comprehensive test suite

**Files to Create/Update**:
- `tests/test_agile_hierarchy_comprehensive.py` (NEW)
- `tests/test_orchestrator.py` (UPDATE)
- `tests/test_state.py` (UPDATE)
- `tests/test_cli.py` (UPDATE)

**Actions**:

3.1. **Create Comprehensive Test Suite**

File: `tests/test_agile_hierarchy_comprehensive.py`

```python
"""Comprehensive tests for Agile/Scrum hierarchy (ADR-013).

This extends the basic smoke tests with edge cases, error handling,
and integration scenarios.
"""

import pytest
from datetime import datetime, UTC

from src.core.models import TaskType, TaskStatus, Milestone
from src.core.state import StateManager
from src.core.exceptions import DatabaseException


class TestEpicEdgeCases:
    """Test epic edge cases and validation."""

    def test_create_epic_with_invalid_project(self, state_manager):
        """Test epic creation with non-existent project."""
        with pytest.raises(DatabaseException):
            state_manager.create_epic(
                project_id=9999,
                title="Invalid Epic",
                description="Should fail"
            )

    def test_create_epic_with_all_fields(self, state_manager, sample_project):
        """Test epic creation with all optional fields."""
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="Full Epic",
            description="Complete test",
            priority=9,
            context={'key': 'value'}
        )

        epic = state_manager.get_task(epic_id)
        assert epic.priority == 9
        assert epic.context == {'key': 'value'}

    def test_epic_with_zero_stories(self, state_manager, sample_project):
        """Test epic with no stories."""
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="Empty Epic",
            description="No stories"
        )

        stories = state_manager.get_epic_stories(epic_id)
        assert len(stories) == 0


class TestStoryEdgeCases:
    """Test story edge cases and validation."""

    def test_create_story_with_non_epic_parent(self, state_manager, sample_project):
        """Test story creation with regular task as parent fails."""
        # Create regular task
        task_data = {'title': 'Regular Task', 'description': 'Not an epic'}
        task = state_manager.create_task(sample_project.id, task_data)

        # Try to create story under regular task
        with pytest.raises(ValueError, match="is not an Epic"):
            state_manager.create_story(
                project_id=sample_project.id,
                epic_id=task.id,
                title="Invalid Story",
                description="Should fail"
            )

    def test_move_story_between_epics(self, state_manager, sample_project):
        """Test moving story from one epic to another."""
        # Create two epics
        epic1_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="Epic 1",
            description="First epic"
        )
        epic2_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="Epic 2",
            description="Second epic"
        )

        # Create story in epic1
        story_id = state_manager.create_story(
            project_id=sample_project.id,
            epic_id=epic1_id,
            title="Story",
            description="Will be moved"
        )

        # Move to epic2
        story = state_manager.get_task(story_id)
        state_manager.update_task_status(story_id, TaskStatus.PENDING, {'epic_id': epic2_id})

        # Verify move (need to add update method)
        # This test reveals we need an update_task() method


class TestMilestoneComplexScenarios:
    """Test complex milestone scenarios."""

    def test_milestone_with_multiple_epics(self, state_manager, sample_project):
        """Test milestone requiring multiple epics."""
        # Create 3 epics
        epic_ids = []
        for i in range(3):
            epic_id = state_manager.create_epic(
                project_id=sample_project.id,
                title=f"Epic {i}",
                description=f"Epic {i}"
            )
            epic_ids.append(epic_id)

        # Create milestone
        milestone_id = state_manager.create_milestone(
            project_id=sample_project.id,
            name="Three Epic Milestone",
            required_epic_ids=epic_ids
        )

        # Initially incomplete
        assert not state_manager.check_milestone_completion(milestone_id)

        # Complete epics one by one
        state_manager.update_task_status(epic_ids[0], TaskStatus.COMPLETED)
        assert not state_manager.check_milestone_completion(milestone_id)

        state_manager.update_task_status(epic_ids[1], TaskStatus.COMPLETED)
        assert not state_manager.check_milestone_completion(milestone_id)

        state_manager.update_task_status(epic_ids[2], TaskStatus.COMPLETED)
        assert state_manager.check_milestone_completion(milestone_id)

    def test_milestone_with_no_required_epics(self, state_manager, sample_project):
        """Test milestone with empty requirements."""
        milestone_id = state_manager.create_milestone(
            project_id=sample_project.id,
            name="Manual Milestone",
            required_epic_ids=[]
        )

        # Should not be auto-completable
        assert not state_manager.check_milestone_completion(milestone_id)


class TestCascadeOperations:
    """Test cascade delete and update operations."""

    def test_delete_epic_soft_deletes_stories(self, state_manager, sample_project):
        """Test soft deleting epic soft-deletes stories."""
        # Create epic with stories
        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="Epic to Delete",
            description="Will be deleted"
        )

        story_ids = []
        for i in range(3):
            story_id = state_manager.create_story(
                project_id=sample_project.id,
                epic_id=epic_id,
                title=f"Story {i}",
                description=f"Story {i}"
            )
            story_ids.append(story_id)

        # Soft delete epic
        state_manager.delete_task(epic_id, soft=True)

        # Verify epic is soft deleted
        epic = state_manager.get_task(epic_id)
        assert epic is None  # get_task filters soft-deleted

        # Verify stories are still accessible but marked for cleanup
        # (actual behavior depends on implementation)


class TestPerformance:
    """Test performance with large hierarchies."""

    def test_large_epic_with_many_stories(self, state_manager, sample_project, fast_time):
        """Test epic with 50 stories performs well."""
        import time

        epic_id = state_manager.create_epic(
            project_id=sample_project.id,
            title="Large Epic",
            description="50 stories"
        )

        start = time.time()

        # Create 50 stories
        for i in range(50):
            state_manager.create_story(
                project_id=sample_project.id,
                epic_id=epic_id,
                title=f"Story {i}",
                description=f"Description {i}"
            )

        creation_time = time.time() - start

        # Query stories
        start = time.time()
        stories = state_manager.get_epic_stories(epic_id)
        query_time = time.time() - start

        assert len(stories) == 50
        assert creation_time < 5.0  # Should create quickly
        assert query_time < 0.5  # Should query quickly


# Add 100+ more tests covering all scenarios...
```

3.2. **Update Existing Tests**

Update test_orchestrator.py, test_state.py, test_cli.py to use new terminology.

**Validation**:
```bash
# Run all tests
pytest tests/ --cov=src --cov-report=term

# Should show ≥85% coverage
```

---

### STEP 4: Documentation Updates (2 hours)

**Objective**: Update all documentation to reflect Agile hierarchy

**Files to Update**:
- `CLAUDE.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/guides/GETTING_STARTED.md`
- `docs/guides/CLI_REFERENCE.md`
- `docs/architecture/data_flow.md`

**Files to Create**:
- `docs/guides/AGILE_WORKFLOW_GUIDE.md`
- `docs/guides/MIGRATION_GUIDE_V1.3.md`

**Actions**:

4.1. **Update CLAUDE.md**

Search and replace:
```markdown
# OLD terminology
execute_milestone() → execute_epic()
"milestone" (as task group) → "epic"
create_task() for large features → create_epic()

# NEW sections to add
## Agile/Scrum Hierarchy (ADR-013)

Obra uses industry-standard Agile terminology:

- **Epic**: Large feature spanning multiple stories (3-15 sessions)
  - Created with `state.create_epic()`
  - Executed with `orchestrator.execute_epic()`

- **Story**: User-facing deliverable (1 orchestration session)
  - Created with `state.create_story()`
  - Belongs to an epic (epic_id foreign key)

- **Task**: Technical work implementing story (default type)
  - Created with `state.create_task()` (defaults to TaskType.TASK)
  - Can belong to a story (story_id foreign key)

- **Subtask**: Granular step
  - Uses parent_task_id hierarchy

- **Milestone**: Zero-duration checkpoint (not work items)
  - Created with `state.create_milestone()`
  - Achieved when required epics complete

### Example Workflow

```python
# Create epic
epic_id = state.create_epic(1, "User Auth System", "OAuth + MFA")

# Create stories
story1 = state.create_story(1, epic_id, "Email login", "As a user...")
story2 = state.create_story(1, epic_id, "OAuth", "As a user...")

# Execute epic (runs all stories)
orchestrator.execute_epic(project_id=1, epic_id=epic_id)

# Create milestone
milestone = state.create_milestone(1, "Auth Complete", required_epic_ids=[epic_id])

# Check/achieve milestone
if state.check_milestone_completion(milestone):
    state.achieve_milestone(milestone)
```
```

4.2. **Create Agile Workflow Guide**

File: `docs/guides/AGILE_WORKFLOW_GUIDE.md`

```markdown
# Agile Workflow Guide

This guide demonstrates how to use Obra's Agile/Scrum hierarchy for managing software projects.

## Overview

Obra implements industry-standard Agile terminology:

```
Product (Project)
  ↓
Epic (Large feature, 3-15 sessions)
  ↓
Story (User deliverable, 1 session)
  ↓
Task (Technical work)
  ↓
Subtask (Granular steps)

Milestone → Checkpoint (when epics complete)
```

## Basic Workflow

### 1. Create Project

```bash
obra project create "E-Commerce Platform" \
  --description "Online shopping platform" \
  --working-dir /path/to/project
```

### 2. Plan Epics

Break down your product into large features:

```bash
obra epic create "User Authentication" \
  --project 1 \
  --description "Complete auth system with OAuth, MFA, session management" \
  --priority 9

obra epic create "Product Catalog" \
  --project 1 \
  --description "Browse, search, filter products" \
  --priority 8

obra epic create "Shopping Cart" \
  --project 1 \
  --description "Add to cart, checkout flow" \
  --priority 7
```

### 3. Break Epics into Stories

Each story should be completable in one orchestration session:

```bash
# User Authentication Epic (ID: 1)
obra story create "Email/password login" \
  --epic 1 \
  --project 1 \
  --description "As a user, I want to log in with email/password"

obra story create "OAuth integration" \
  --epic 1 \
  --project 1 \
  --description "As a user, I want to log in with Google/GitHub"

obra story create "Multi-factor authentication" \
  --epic 1 \
  --project 1 \
  --description "As a user, I want 2FA for security"
```

### 4. Execute Epic

Run all stories in an epic:

```bash
obra epic execute 1

# Output:
# Executing epic #1: User Authentication
# Executing story #2 in epic 1...
# Executing story #3 in epic 1...
# Executing story #4 in epic 1...
# ✓ Epic execution complete:
#   Stories completed: 3/3
#   Stories failed: 0
```

### 5. Track Progress

```bash
# List all epics
obra epic list --project 1

# Show epic details
obra epic show 1

# List stories in epic
obra story list --epic 1
```

### 6. Define Milestones

Create checkpoints for major achievements:

```bash
obra milestone create "MVP Ready" \
  --project 1 \
  --epics 1,2,3 \
  --description "Core features complete"

# Check milestone progress
obra milestone check 1

# When ready, achieve milestone
obra milestone achieve 1
```

## Advanced Workflows

### Parallel Epic Execution

Execute multiple epics concurrently (if independent):

```bash
# Epic 2 and 3 don't depend on Epic 1
obra epic execute 2 &
obra epic execute 3 &
wait
```

### Story Dependencies

Use task dependencies for story ordering:

```bash
# Story 5 depends on Story 4
obra task create "Implement cart API" \
  --project 1 \
  --depends-on 4
```

### Monitoring Progress

```bash
# Real-time epic monitoring
watch -n 5 'obra epic show 1'

# Export progress report
obra epic list --project 1 --format json > progress.json
```

## Best Practices

### 1. Epic Sizing
- **Good**: 3-15 stories per epic
- **Too Small**: 1-2 stories (just use story directly)
- **Too Large**: 20+ stories (split into multiple epics)

### 2. Story Sizing
- **Goal**: Completable in 1 orchestration session (typically 1-2 hours)
- **If larger**: Break into multiple stories
- **Acceptance criteria**: Define clear "done" criteria

### 3. Task Breakdown
- Stories contain tasks (technical implementation)
- Tasks can have subtasks (granular steps)
- Use task dependencies for ordering

### 4. Milestone Planning
- Define milestones upfront (sprint goals, releases)
- Link epics to milestones
- Auto-achieve when all epics complete

### 5. Iterative Development
- Complete one epic at a time
- Review and adjust after each epic
- Use metrics to improve estimates

## Common Patterns

### Pattern 1: Sprint Planning

```bash
# Sprint 1: Authentication & Basic Catalog
obra milestone create "Sprint 1 Complete" \
  --project 1 \
  --epics 1,2

# Execute sprint
obra epic execute 1
obra epic execute 2

# Review
obra milestone check 1
```

### Pattern 2: Feature Flags

```bash
# Create epic with feature flag
obra epic create "New Checkout Flow" \
  --project 1 \
  --description "Redesigned checkout (behind feature flag)"

# Stories include flag integration
obra story create "Add feature flag toggle" --epic 5 --project 1
obra story create "Implement new UI" --epic 5 --project 1
obra story create "A/B testing setup" --epic 5 --project 1
```

### Pattern 3: Technical Debt

```bash
# Create epic for refactoring
obra epic create "Payment Service Refactor" \
  --project 1 \
  --priority 5 \
  --description "Break monolith into microservices"
```

## Troubleshooting

### Epic Not Executing

```bash
# Check epic exists and has stories
obra epic show <epic_id>

# Verify stories are not blocked
obra story list --epic <epic_id>
```

### Milestone Not Completing

```bash
# Check which epics are incomplete
obra milestone show <milestone_id>

# Complete missing epics
obra epic execute <epic_id>
```

### Story Creation Fails

```bash
# Verify epic exists and is correct type
obra epic show <epic_id>

# Check error message for validation issues
```

## Next Steps

- Read [CLI Reference](CLI_REFERENCE.md) for complete command list
- See [Architecture Guide](../architecture/ARCHITECTURE.md) for technical details
- Review [Test Guidelines](TEST_GUIDELINES.md) for testing Agile hierarchies
```

4.3. **Create Migration Guide**

File: `docs/guides/MIGRATION_GUIDE_V1.3.md`

```markdown
# Migration Guide: v1.2 → v1.3 (Agile Hierarchy)

This guide helps existing Obra users migrate to the new Agile/Scrum hierarchy.

## What Changed

### Terminology Updates

| Old Term | New Term | Usage |
|----------|----------|-------|
| "Milestone" (as task group) | Epic | Large features |
| execute_milestone() | execute_epic() | Orchestration |
| Any "task" | Story, Task, or Subtask | Depends on size |

### New Concepts

1. **TaskType Enum**: All tasks now have a type (EPIC, STORY, TASK, SUBTASK)
2. **True Milestones**: Zero-duration checkpoints (not work items)
3. **Epic/Story Hierarchy**: Explicit relationship via epic_id/story_id

## Migration Steps

### Step 1: Backup Database

```bash
# SQLite
cp orchestrator.db orchestrator.db.backup

# PostgreSQL
pg_dump obra_db > obra_db_backup.sql
```

### Step 2: Run Migration Script

```bash
# SQLite
sqlite3 orchestrator.db < migrations/versions/003_agile_hierarchy.sql

# PostgreSQL
psql obra_db < migrations/versions/003_agile_hierarchy.sql
```

### Step 3: Verify Migration

```bash
# Check task_type column exists
sqlite3 orchestrator.db "PRAGMA table_info(task);" | grep task_type

# Check milestone table exists
sqlite3 orchestrator.db ".tables" | grep milestone

# Verify all existing tasks have default type
sqlite3 orchestrator.db "SELECT COUNT(*) FROM task WHERE task_type='task';"
```

### Step 4: Update Code

#### Python API Changes

```python
# OLD CODE
orchestrator.execute_milestone(
    project_id=1,
    task_ids=[1, 2, 3],
    milestone_id=5
)

# NEW CODE
orchestrator.execute_epic(
    project_id=1,
    epic_id=5  # Epic contains stories
)
```

#### CLI Changes

```bash
# No breaking changes - old commands still work
# New commands available:

obra epic create/list/show/execute
obra story create/list/show
obra milestone create/check/achieve
```

### Step 5: Reorganize Existing Work

Convert existing "task groups" to epics:

```python
# Identify task groups (collections of related tasks)
# Convert to epics

from src.core.models import TaskType
from src.core.state import StateManager

state = StateManager('sqlite:///orchestrator.db')

# Example: Convert "Authentication Tasks" to Epic
epic_id = state.create_epic(
    project_id=1,
    title="User Authentication",
    description="Previously tracked as task group"
)

# Convert tasks to stories
for old_task_id in [10, 11, 12]:  # Task IDs that were part of group
    task = state.get_task(old_task_id)

    # Option 1: Update existing task
    state.update_task_status(
        old_task_id,
        task.status,
        {'task_type': TaskType.STORY, 'epic_id': epic_id}
    )

    # Option 2: Create new story (recommended)
    story_id = state.create_story(
        project_id=task.project_id,
        epic_id=epic_id,
        title=task.title,
        description=task.description
    )
```

## Backward Compatibility

### What Still Works

- ✅ Existing tasks (default to TaskType.TASK)
- ✅ Task dependencies (M9 feature)
- ✅ Task execution (execute_task)
- ✅ All existing CLI commands
- ✅ StateManager.create_task()

### What's Deprecated

- ⚠️ execute_milestone() - Still works but deprecated
  - Use execute_epic() instead
  - Will be removed in v2.0

### What's Removed

- ❌ None - Full backward compatibility

## Rollback Procedure

If migration fails:

```bash
# 1. Restore backup
cp orchestrator.db.backup orchestrator.db

# 2. Or run rollback SQL (if migration partially applied)
sqlite3 orchestrator.db < migrations/versions/003_agile_hierarchy_rollback.sql
```

Rollback script (create if needed):
```sql
-- Remove new columns (requires table rebuild in SQLite)
CREATE TABLE task_backup AS SELECT * FROM task;

DROP TABLE task;

CREATE TABLE task (
    -- Original schema without task_type, epic_id, story_id
    ...
);

INSERT INTO task SELECT ... FROM task_backup;

DROP TABLE task_backup;
DROP TABLE IF EXISTS milestone;
```

## Common Issues

### Issue 1: Migration Fails with "duplicate column"

**Cause**: Migration already partially applied

**Solution**:
```bash
# Check current schema
sqlite3 orchestrator.db "PRAGMA table_info(task);"

# If task_type exists, skip to later steps
# Or rollback and reapply
```

### Issue 2: Existing code uses execute_milestone()

**Cause**: Code not updated to new terminology

**Solution**:
```python
# Quick fix: Keep using execute_milestone (deprecated)
# Long-term: Update to execute_epic()

# Search for usage
grep -r "execute_milestone" src/
```

### Issue 3: Tests fail after migration

**Cause**: Tests reference old terminology

**Solution**:
```bash
# Update test imports
sed -i 's/execute_milestone/execute_epic/g' tests/*.py

# Re-run tests
pytest tests/
```

## Post-Migration Checklist

- [ ] Database migration successful
- [ ] All existing tasks have task_type='task'
- [ ] Milestone table created
- [ ] Existing tests pass
- [ ] Code updated to use execute_epic() (optional)
- [ ] Team trained on new terminology
- [ ] Documentation updated
- [ ] Backup restored if issues

## Getting Help

- Check [Agile Workflow Guide](AGILE_WORKFLOW_GUIDE.md)
- Review [CLI Reference](CLI_REFERENCE.md)
- Open issue: https://github.com/Omar-Unpossible/claude_code_orchestrator/issues
```

**Validation**:
```bash
# Verify all docs updated
grep -r "execute_milestone" docs/ | grep -v "OLD\|deprecated\|migration"
# Should return minimal results

# Verify guides are complete
ls -la docs/guides/
```

---

## Success Criteria

### Code Quality
- [ ] All helper methods use "epic" terminology (not "milestone")
- [ ] No linting warnings in modified files
- [ ] Type checking passes (mypy)
- [ ] Code follows existing patterns

### CLI Completeness
- [ ] Epic commands: create, list, show, execute, update, delete
- [ ] Story commands: create, list, show, update, move
- [ ] Milestone commands: create, list, show, check, achieve, update
- [ ] All commands have proper help text
- [ ] Error messages are clear and actionable

### Test Coverage
- [ ] Overall coverage ≥85% (maintain current level)
- [ ] StateManager epic/story methods ≥90% coverage
- [ ] Orchestrator execute_epic ≥85% coverage
- [ ] CLI commands tested (integration tests)
- [ ] Edge cases covered (invalid inputs, empty results)
- [ ] Performance tests pass (50+ stories in epic)

### Documentation
- [ ] CLAUDE.md updated with Agile terminology
- [ ] All guides reference correct terms
- [ ] AGILE_WORKFLOW_GUIDE.md created
- [ ] MIGRATION_GUIDE_V1.3.md created
- [ ] CLI_REFERENCE.md has all new commands
- [ ] Examples and tutorials updated

### Integration
- [ ] Existing tests pass (no regressions)
- [ ] Migration script tested (apply + rollback)
- [ ] Backward compatibility verified
- [ ] Real orchestration flows work end-to-end

---

## File Modification Summary

### Modified Files (20)

**Core**:
- `src/orchestrator.py` - Rename helper methods, update variables
- `src/cli.py` - Add list/show/update commands

**Tests**:
- `tests/test_orchestrator.py` - Update terminology
- `tests/test_state.py` - Update terminology
- `tests/test_cli.py` - Add CLI tests
- `tests/test_agile_hierarchy_comprehensive.py` - NEW (150+ tests)

**Documentation**:
- `CLAUDE.md` - Update terminology throughout
- `docs/architecture/ARCHITECTURE.md` - Update diagrams
- `docs/guides/GETTING_STARTED.md` - Update examples
- `docs/guides/CLI_REFERENCE.md` - Add new commands
- `docs/architecture/data_flow.md` - Update flow diagrams
- `docs/guides/AGILE_WORKFLOW_GUIDE.md` - NEW
- `docs/guides/MIGRATION_GUIDE_V1.3.md` - NEW

### Lines of Code

| Category | New Lines | Modified Lines | Total |
|----------|-----------|----------------|-------|
| Core Implementation | 500 | 200 | 700 |
| Tests | 1,500 | 300 | 1,800 |
| Documentation | 2,000 | 500 | 2,500 |
| **Total** | **4,000** | **1,000** | **5,000** |

---

## Risk Assessment

### Low Risk
- Helper method renaming (internal only)
- Documentation updates (no code impact)
- CLI additions (no breaking changes)

### Medium Risk
- Comprehensive test suite (time-consuming)
- Migration testing (requires database setup)
- Performance testing (need large datasets)

### High Risk
- None - backward compatible implementation

### Mitigation Strategies
- Incremental implementation (epic by epic)
- Continuous testing after each change
- Backup database before migration testing
- Code review before committing

---

## Timeline & Effort

### Day 1: Code Quality (6 hours)
- Morning (3h): Rename helper methods, update tests
- Afternoon (3h): Code quality checks, fix issues

### Day 2: Enhanced CLI & Tests (8 hours)
- Morning (4h): Add list/show/update commands
- Afternoon (4h): Begin comprehensive test suite

### Day 3: Tests & Documentation (8 hours)
- Morning (4h): Complete test suite
- Afternoon (4h): Update documentation, create guides

**Total**: 22 hours (2.75 days)

---

## Next Actions

1. **Review this plan** with stakeholders
2. **Set up test environment** for migration testing
3. **Create feature branch**: `feature/agile-hierarchy-completion`
4. **Begin with Epic 1** (code quality - lowest risk)
5. **Continuous integration** testing after each epic
6. **Code review** before merging to main

---

## References

- **ADR-013**: `docs/decisions/ADR-013-adopt-agile-work-hierarchy.md`
- **Phase 1 Work**: `docs/development/AGILE_MIGRATION_START.md`
- **Core Implementation**: Already complete (24 hours)
- **Test Guidelines**: `docs/development/TEST_GUIDELINES.md`

---

**Last Updated**: November 5, 2025
**Version**: v1.3.0-completion-plan
**Status**: Ready for Implementation
**Estimated Completion**: 2-3 days (16-22 hours)
