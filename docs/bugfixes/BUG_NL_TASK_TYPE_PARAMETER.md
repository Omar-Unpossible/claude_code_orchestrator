# Bug Fix: NL Query System Missing task_type Parameter

**Bug ID**: NL Query Missing task_type Parameter
**Date**: November 13, 2025
**Severity**: High
**Status**: Fixed

## Problem

Natural language hierarchical queries failed with `TypeError` when attempting to filter tasks by type (EPIC, STORY, TASK, SUBTASK):

```
Failed to execute query task: StateManager.list_tasks() got an unexpected keyword argument 'task_type'
```

**User Command**:
```
orchestrator> list the plans (epics, stories, tasks, etc) in project #1
```

**Error Traceback**:
```
File "src/nl/nl_query_helper.py", line 278, in _query_simple
    tasks = self.state_manager.list_tasks(task_type=task_type, limit=50)
TypeError: StateManager.list_tasks() got an unexpected keyword argument 'task_type'
```

## Root Cause

**API mismatch** between `NLQueryHelper` and `StateManager`:

1. **NLQueryHelper expected** `task_type` parameter in `StateManager.list_tasks()`:
   - Line 278: `_query_simple()` calls `list_tasks(task_type=task_type, limit=50)`
   - Line 315: `_query_hierarchical()` calls `list_tasks(task_type=TaskType.EPIC, limit=50)`

2. **StateManager.list_tasks() signature** (before fix):
   ```python
   def list_tasks(
       self,
       project_id: Optional[int] = None,
       status: Optional[TaskStatus] = None,
       limit: Optional[int] = None
   ) -> List[Task]:
   ```

   **Missing**: `task_type` parameter for filtering by TaskType enum

3. **Inconsistency**: Other StateManager methods (`get_epic_stories()`, `get_story_tasks()`) already filter by `task_type`, but `list_tasks()` didn't support it

## Solution

Added `task_type` parameter to `StateManager.list_tasks()` method following existing filtering pattern.

### File: `src/core/state.py` (lines 644-691)

**Before**:
```python
def list_tasks(
    self,
    project_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    limit: Optional[int] = None
) -> List[Task]:
    """Get all tasks with optional filtering."""
    with self._lock:
        session = self._get_session()
        query = session.query(Task).filter(Task.is_deleted == False)

        # Apply filters
        if project_id is not None:
            query = query.filter(Task.project_id == project_id)
        if status is not None:
            query = query.filter(Task.status == status)

        # Order by priority (desc) and created date
        query = query.order_by(desc(Task.priority), Task.created_at)

        # Apply limit
        if limit is not None:
            query = query.limit(limit)

        return query.all()
```

**After**:
```python
def list_tasks(
    self,
    project_id: Optional[int] = None,
    status: Optional[TaskStatus] = None,
    task_type: Optional[TaskType] = None,  # ✅ NEW PARAMETER
    limit: Optional[int] = None
) -> List[Task]:
    """Get all tasks with optional filtering.

    Args:
        project_id: Filter by project ID (None = all projects)
        status: Filter by status (None = all statuses)
        task_type: Filter by task type (None = all types)  # ✅ NEW
        limit: Maximum number of tasks to return (None = no limit)

    Returns:
        List of tasks matching criteria, ordered by priority and created date

    Example:
        >>> # Get all epics
        >>> epics = state_manager.list_tasks(task_type=TaskType.EPIC)  # ✅ NEW
    """
    with self._lock:
        session = self._get_session()
        query = session.query(Task).filter(Task.is_deleted == False)

        # Apply filters
        if project_id is not None:
            query = query.filter(Task.project_id == project_id)
        if status is not None:
            query = query.filter(Task.status == status)
        if task_type is not None:  # ✅ NEW FILTER
            query = query.filter(Task.task_type == task_type)

        # Order by priority (desc) and created date
        query = query.order_by(desc(Task.priority), Task.created_at)

        # Apply limit
        if limit is not None:
            query = query.limit(limit)

        return query.all()
```

**Changes**:
- ✅ Added `task_type: Optional[TaskType] = None` parameter
- ✅ Added filtering logic: `if task_type is not None: query = query.filter(Task.task_type == task_type)`
- ✅ Updated docstring with new parameter and example
- ✅ Zero breaking changes (new optional parameter)

### No Changes Required: `src/nl/nl_query_helper.py`

The existing calls in `NLQueryHelper` were already correct:
- Line 278: `self.state_manager.list_tasks(task_type=task_type, limit=50)` ✅
- Line 315: `self.state_manager.list_tasks(task_type=TaskType.EPIC, limit=50)` ✅

The bug was entirely in `StateManager`, not `NLQueryHelper`.

## Testing

### Unit Tests (7 new tests)

Added `TestTaskTypeFiltering` class to `tests/test_state_manager_task_operations.py` (154 lines):

```python
class TestTaskTypeFiltering:
    """Test StateManager.list_tasks() filtering by task_type parameter."""

    def test_filter_by_epic(self):
        """Test filtering tasks by EPIC task_type."""
        epics = state.list_tasks(task_type=TaskType.EPIC)
        assert all(t.task_type == TaskType.EPIC for t in epics)

    def test_filter_by_story(self):
        """Test filtering tasks by STORY task_type."""
        stories = state.list_tasks(task_type=TaskType.STORY)
        assert all(t.task_type == TaskType.STORY for t in stories)

    def test_filter_by_task(self):
        """Test filtering tasks by TASK task_type."""
        tasks = state.list_tasks(task_type=TaskType.TASK)
        assert all(t.task_type == TaskType.TASK for t in tasks)

    def test_filter_by_subtask(self):
        """Test filtering tasks by SUBTASK task_type."""
        subtasks = state.list_tasks(task_type=TaskType.SUBTASK)
        assert all(t.task_type == TaskType.SUBTASK for t in subtasks)

    def test_no_filter_returns_all_types(self):
        """Test that omitting task_type returns all task types."""
        all_tasks = state.list_tasks()
        task_types = {t.task_type for t in all_tasks}
        assert TaskType.EPIC in task_types
        assert TaskType.STORY in task_types
        assert TaskType.TASK in task_types
        assert TaskType.SUBTASK in task_types

    def test_filter_with_limit(self):
        """Test combining task_type filter with limit."""
        epics = state.list_tasks(task_type=TaskType.EPIC, limit=2)
        assert len(epics) == 2
        assert all(t.task_type == TaskType.EPIC for t in epics)

    def test_filter_with_status(self):
        """Test combining task_type filter with status filter."""
        completed_epics = state.list_tasks(
            task_type=TaskType.EPIC,
            status=TaskStatus.COMPLETED
        )
        assert all(t.task_type == TaskType.EPIC for t in completed_epics)
        assert all(t.status == TaskStatus.COMPLETED for t in completed_epics)
```

**Results**: All 17 tests passing (10 existing + 7 new)

### Integration Testing

Manual verification with the original failing command:

```bash
$ python -m src.cli interactive
orchestrator> list the plans (epics, stories, tasks, etc) in project #1

✓ Query succeeded
Found 3 epics:
  - Epic 1: User Authentication
  - Epic 2: Database Migration
  - Epic 3: API Refactoring
```

**Results**:
- ✅ NL hierarchical queries work correctly
- ✅ NL simple queries work correctly
- ✅ All NL query types (SIMPLE, HIERARCHICAL, NEXT_STEPS, BACKLOG, ROADMAP) work
- ✅ No regressions in existing functionality

## Impact

**Before Fix**:
- ❌ NL hierarchical queries failed with TypeError
- ❌ NL simple queries for specific task types (epics, stories) failed
- ❌ Users couldn't use natural language to query task hierarchies
- ❌ Inconsistent API: Some methods filter by task_type, but list_tasks() didn't

**After Fix**:
- ✅ All NL query types work correctly
- ✅ Task type filtering supported in StateManager.list_tasks()
- ✅ Consistent API with other StateManager methods
- ✅ Zero breaking changes (backward compatible)

## Architecture Compliance

This fix adheres to Obra's core architecture principles:

1. **StateManager is Single Source of Truth** ✅
   - All filtering logic remains in StateManager
   - No workarounds or bypasses in NLQueryHelper

2. **No API Bypasses** ✅
   - Fixed the API properly instead of working around it

3. **Consistent Patterns** ✅
   - Follows existing filter pattern (similar to `status` parameter)
   - Matches how `get_epic_stories()` already filters by task_type

## Files Modified

- `src/core/state.py` (1 method signature + 3 lines)
- `tests/test_state_manager_task_operations.py` (154 lines, 7 new tests)

## Related

- Natural Language Command Interface: `docs/guides/NL_COMMAND_GUIDE.md`
- Agile Work Hierarchy: `docs/guides/AGILE_WORKFLOW_GUIDE.md`
- StateManager Architecture: `docs/architecture/ARCHITECTURE.md`

---

**Status**: ✅ Fixed and tested
**Version**: 1.7.5 (Unreleased)
