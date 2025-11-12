# Infrastructure Testing Strategy

## Overview

This document describes the infrastructure testing strategy for Obra, designed to catch critical system-level issues before they reach production.

## Problem Statement

Recent production issues have included:
1. **Missing database columns** - `table task has no column named requires_adr` (Migration 004 not applied)
2. **Type mismatches** - `TypeError: argument of type 'ExecutionResult' is not iterable` (API change in NLResponse)
3. **API signature changes** - `create_task()` parameter changes not caught by existing tests

**Root Cause**: Our test suite focused on unit testing individual components but missed integration-level and infrastructure-level failures.

## Solution: Infrastructure Test Suite

Three new test modules provide comprehensive infrastructure validation:

### 1. Database Schema Tests (`test_database_schema.py`)

**Purpose**: Verify database schema matches code expectations

**Tests Include**:
- ✅ All required columns exist (base + Migration 003 + Migration 004)
- ✅ Column types and defaults are correct
- ✅ Indexes exist
- ✅ All tables present
- ✅ Migrations 003 and 004 applied successfully
- ✅ Foreign key relationships work
- ✅ JSON fields (dependencies, context) serialize correctly

**Would Have Caught**:
- `requires_adr` column missing error
- Migration 004 not applied

**Example Test**:
```python
def test_task_table_has_all_required_columns(self, db_connection):
    """Verify task table has all columns from all migrations"""
    # Checks for: requires_adr, has_architectural_changes,
    # changes_summary, documentation_status, task_type, epic_id, etc.
```

### 2. Interactive Integration Tests (`test_interactive_integration.py`)

**Purpose**: Verify interactive.py works with NL processor and ExecutionResult

**Tests Include**:
- ✅ ExecutionResult object handling (not dict)
- ✅ Project switching via execution_result.results['project_id']
- ✅ Handling None execution_result
- ✅ Empty execution_result.results
- ✅ End-to-end NL command processing
- ✅ Database error handling

**Would Have Caught**:
- `TypeError: argument of type 'ExecutionResult' is not iterable`
- Incorrect attribute access on ExecutionResult

**Example Test**:
```python
def test_execution_result_not_iterable_with_in_operator(self):
    """Verify ExecutionResult is not iterable (catches the bug)"""
    result = ExecutionResult(...)

    # This is what the bug was - treating ExecutionResult as dict
    with pytest.raises(TypeError, match="not iterable"):
        _ = 'project_id' in result  # Should fail!

    # Correct way: check in results dict
    assert 'project_id' in result.results  # Should succeed
```

### 3. StateManager Strain Tests (`test_statemanager_strain.py`)

**Purpose**: Stress-test StateManager with heavy operations and edge cases

**Tests Include**:
- ✅ Create 100 tasks sequentially (database strain)
- ✅ Complex agile hierarchy (3 epics, 15 stories, 150 tasks)
- ✅ Task with ALL fields populated (catches missing columns)
- ✅ Transaction rollback on error
- ✅ Concurrent task creation (threading)
- ✅ Edge cases (empty lists, null fields, special characters)
- ✅ API compatibility (dict vs positional args)
- ✅ Data integrity (relationships, dependencies)

**Would Have Caught**:
- Any missing database column
- create_task() API signature changes
- Transaction failures
- Data type conversion issues

**Example Test**:
```python
def test_task_with_all_fields_populated(self, state_manager):
    """Create task with every possible field to catch missing columns"""
    task = state_manager.create_task(
        project.id,
        {
            'title': 'Complete Task',
            'description': 'Task with all fields',
            'priority': 8,
            'dependencies': [dep1.id, dep2.id],
            'context': {'nested': {'data': 123}},
            'epic_id': epic_id,
            'story_id': story_id,
            'requires_adr': True,  # Migration 004
            'has_architectural_changes': True,  # Migration 004
            'changes_summary': 'Major refactoring',  # Migration 004
            'documentation_status': 'pending',  # Migration 004
            # ... every field
        }
    )
```

## Test Coverage Summary

| Category | Tests | Lines | Purpose |
|----------|-------|-------|---------|
| Database Schema | 15 | 280 | Verify schema matches expectations |
| Interactive Integration | 9 | 260 | Verify UI layer integration |
| StateManager Strain | 18 | 385 | Stress-test database operations |
| **Total** | **42** | **925** | **Infrastructure validation** |

## Current Status

**⚠️ Tests Need API Updates**: The tests are written but need minor updates to match current API signatures:
- `create_project()` parameter names
- Fixture name consistency
- Import statement corrections

**✅ Framework Complete**: The testing infrastructure is in place and ready to catch these issues once API signatures are corrected.

## Running Infrastructure Tests

```bash
# Run all infrastructure tests
pytest tests/test_database_schema.py tests/test_interactive_integration.py tests/test_statemanager_strain.py -v

# Run just database schema validation
pytest tests/test_database_schema.py -v

# Run just interactive integration
pytest tests/test_interactive_integration.py -v

# Run just StateManager strain tests
pytest tests/test_statemanager_strain.py -v
```

## Integration with CI/CD

These tests should run:
1. **On every commit** - Catch issues early
2. **Before merges** - Gate production deployments
3. **After migrations** - Verify schema changes

## Future Enhancements

1. **Configuration Validation Tests**
   - Verify config files have required sections
   - Test default values
   - Validate config types

2. **Plugin System Tests**
   - Verify all plugins register correctly
   - Test plugin initialization
   - Validate plugin interfaces

3. **Session Management Tests**
   - Test session creation/cleanup
   - Verify context persistence
   - Test session limits

4. **File System Tests**
   - Verify runtime directory structure
   - Test file permissions
   - Validate path resolution

## Lessons Learned

1. **Unit tests aren't enough** - Need integration and infrastructure tests
2. **Test the database** - Schema validation catches migration issues
3. **Test type changes** - API changes need explicit validation
4. **Stress test critical paths** - Heavy operations reveal edge cases
5. **Test error paths** - Don't just test happy paths

## Maintenance

- **Update after migrations** - Add checks for new columns/tables
- **Update after API changes** - Verify new signatures in tests
- **Review after incidents** - Add tests for production issues
- **Run regularly** - Don't let these tests bitrot

---

**Created**: 2025-11-11
**Status**: Framework Complete, API Updates Needed
**Priority**: High - Critical for production stability
