# Migration Guide: v1.2 → v1.3 (Agile Hierarchy)

**Version**: 1.3.0
**Last Updated**: November 6, 2025
**Migration Time**: 15-30 minutes
**Downtime**: None (backward compatible)

This guide helps existing Obra users migrate from v1.2 to v1.3, which introduces the Agile/Scrum work hierarchy.

---

## Table of Contents

1. [What Changed](#what-changed)
2. [Breaking Changes](#breaking-changes)
3. [Migration Steps](#migration-steps)
4. [Code Updates](#code-updates)
5. [Verification](#verification)
6. [Rollback Procedure](#rollback-procedure)
7. [Troubleshooting](#troubleshooting)

---

## What Changed

### New Features

✅ **Agile/Scrum Hierarchy** (ADR-013):
- TaskType enum: EPIC, STORY, TASK, SUBTASK
- Epic methods: `create_epic()`, `get_epic_stories()`, `execute_epic()`
- Story methods: `create_story()`, `get_story_tasks()`
- Milestone model: Separate table with completion tracking
- CLI commands: `obra epic`, `obra story`, `obra milestone`

✅ **Database Schema Updates**:
- Task table: Added `task_type`, `epic_id`, `story_id` columns
- Milestone table: New table with `required_epic_ids`, `achieved`, `achieved_at`
- Migration script: `migrations/versions/003_agile_hierarchy.sql`

✅ **Comprehensive Test Suite**:
- 75+ new tests for Agile hierarchy
- Edge cases, performance, integration coverage
- 96% pass rate (72/75 tests passing)

### Terminology Changes

| Old Term | New Term | Context |
|----------|----------|---------|
| "Milestone" (as task group) | Epic | Large features spanning multiple stories |
| `execute_milestone()` | `execute_epic()` | Orchestrator method name |
| Generic "task" | Story/Task/Subtask | Depends on work item size |

**Note**: "Milestone" now means zero-duration checkpoint, not a work container.

---

## Breaking Changes

### ⚠️ NONE - Fully Backward Compatible

**Good News**: v1.3 is 100% backward compatible with v1.2!

- ✅ Existing tasks continue working (default to `TaskType.TASK`)
- ✅ Task dependencies (M9) still work
- ✅ Subtask hierarchy via `parent_task_id` preserved
- ✅ All existing CLI commands unchanged
- ✅ All StateManager methods unchanged (new methods added)

**Deprecated** (but still working):
- ⚠️ `execute_milestone()` - Use `execute_epic()` instead (will be removed in v2.0)

---

## Migration Steps

### Step 1: Backup Database

**Critical**: Always backup before applying schema changes.

```bash
# SQLite (default)
cp orchestrator.db orchestrator.db.backup.$(date +%Y%m%d)

# PostgreSQL
pg_dump -U postgres obra_db > obra_db_backup_$(date +%Y%m%d).sql
```

### Step 2: Verify Current Version

```bash
# Check current version
python -c "from src.core.models import Task; print('Schema OK' if hasattr(Task, 'id') else 'Schema Error')"

# Check test coverage
pytest --version
```

### Step 3: Apply Database Migration

**SQLite**:
```bash
# Apply migration
sqlite3 orchestrator.db < migrations/versions/003_agile_hierarchy.sql

# Verify migration succeeded
sqlite3 orchestrator.db "PRAGMA table_info(task);" | grep -E "task_type|epic_id|story_id"
sqlite3 orchestrator.db ".tables" | grep milestone
```

**PostgreSQL**:
```bash
# Apply migration
psql -U postgres -d obra_db -f migrations/versions/003_agile_hierarchy.sql

# Verify migration
psql -U postgres -d obra_db -c "\d task" | grep -E "task_type|epic_id|story_id"
psql -U postgres -d obra_db -c "\dt" | grep milestone
```

### Step 4: Verify Database Schema

```python
# Test migration programmatically
from src.core.state import StateManager
from src.core.models import TaskType, Milestone

state = StateManager('sqlite:///orchestrator.db')

# Test new enums
print("TaskType values:", [t.value for t in TaskType])
# Expected: ['epic', 'story', 'task', 'subtask']

# Test milestone table exists
try:
    milestone = state.get_milestone(1)
    print("Milestone table: OK")
except Exception as e:
    print(f"Milestone table: Error - {e}")
```

### Step 5: Update Code (Optional)

**Important**: This step is optional - existing code continues working!

```python
# OLD CODE (still works)
task_data = {'title': 'Build auth system', 'description': 'OAuth + MFA'}
task = state_manager.create_task(project_id=1, task_data=task_data)

# NEW CODE (recommended for large features)
epic_id = state_manager.create_epic(
    project_id=1,
    title="User Authentication System",
    description="OAuth + MFA"
)

story_id = state_manager.create_story(
    project_id=1,
    epic_id=epic_id,
    title="OAuth integration",
    description="As a user, I want to log in with Google/GitHub"
)

orchestrator.execute_epic(project_id=1, epic_id=epic_id)
```

### Step 6: Run Tests

```bash
# Run new Agile hierarchy tests
pytest tests/test_agile_hierarchy_basic.py -v

# Run comprehensive test suite
pytest tests/test_agile_hierarchy_comprehensive.py -v

# Run full test suite to check for regressions
pytest tests/ --cov=src --cov-report=term
```

### Step 7: Try CLI Commands

```bash
# Test epic commands
obra epic create "Test Epic" --project 1 --description "Testing v1.3"
obra epic list --project 1
obra epic show 1

# Test story commands
obra story create "Test Story" --epic 1 --project 1
obra story list --epic 1

# Test milestone commands
obra milestone create "Test Milestone" --project 1 --epics 1
obra milestone check 1
```

---

## Code Updates

### Update 1: Use Epic for Large Features

**Before (v1.2)**:
```python
# Created large features as regular tasks
task1 = state.create_task(1, {'title': 'Login', 'description': 'Email login'})
task2 = state.create_task(1, {'title': 'OAuth', 'description': 'OAuth login'})
task3 = state.create_task(1, {'title': 'MFA', 'description': '2FA'})

# No built-in way to execute as a group
for task_id in [task1.id, task2.id, task3.id]:
    orchestrator.execute_task(project_id=1, task_id=task_id)
```

**After (v1.3)**:
```python
# Create epic (large feature)
epic_id = state.create_epic(
    project_id=1,
    title="User Authentication",
    description="Complete auth system"
)

# Break down into stories
state.create_story(1, epic_id, "Email login", "As a user...")
state.create_story(1, epic_id, "OAuth login", "As a user...")
state.create_story(1, epic_id, "MFA", "As a user...")

# Execute entire epic
orchestrator.execute_epic(project_id=1, epic_id=epic_id)
```

### Update 2: Use Milestones for Checkpoints

**Before (v1.2)**:
```python
# No built-in milestone tracking
# Had to manually check task completion
auth_tasks = [1, 2, 3]
all_complete = all(state.get_task(t).status == TaskStatus.COMPLETED for t in auth_tasks)
if all_complete:
    print("Auth milestone complete!")
```

**After (v1.3)**:
```python
# Create milestone with epic requirements
milestone_id = state.create_milestone(
    project_id=1,
    name="Auth Complete",
    required_epic_ids=[auth_epic_id]
)

# Automatic completion checking
if state.check_milestone_completion(milestone_id):
    state.achieve_milestone(milestone_id)
    print("Auth milestone achieved!")
```

### Update 3: Query by Hierarchy

**Before (v1.2)**:
```python
# Manual filtering by context or naming conventions
all_tasks = state.get_project_tasks(project_id=1)
auth_tasks = [t for t in all_tasks if 'auth' in t.title.lower()]
```

**After (v1.3)**:
```python
# Built-in hierarchical queries
stories = state.get_epic_stories(epic_id)
tasks = state.get_story_tasks(story_id)
```

### Update 4: Deprecation Handling

**Deprecated Method** (still works in v1.3):
```python
# OLD: execute_milestone() (deprecated, will be removed in v2.0)
orchestrator.execute_milestone(
    project_id=1,
    task_ids=[1, 2, 3],
    milestone_id=5
)
```

**Replacement**:
```python
# NEW: execute_epic()
orchestrator.execute_epic(project_id=1, epic_id=5)
```

---

## Verification

### Database Verification

```bash
# SQLite
sqlite3 orchestrator.db "SELECT COUNT(*) FROM task WHERE task_type='task';"
# Should show count of existing tasks (all default to 'task')

sqlite3 orchestrator.db "SELECT COUNT(*) FROM milestone;"
# Should show 0 (no milestones yet)

sqlite3 orchestrator.db "PRAGMA table_info(task);" | grep -c epic_id
# Should output 1 (column exists)
```

### Code Verification

```python
from src.core.state import StateManager
from src.core.models import TaskType

state = StateManager('sqlite:///orchestrator.db')

# Verify TaskType enum
assert hasattr(TaskType, 'EPIC')
assert hasattr(TaskType, 'STORY')
assert hasattr(TaskType, 'TASK')
assert hasattr(TaskType, 'SUBTASK')
print("✓ TaskType enum OK")

# Verify StateManager methods exist
assert hasattr(state, 'create_epic')
assert hasattr(state, 'create_story')
assert hasattr(state, 'create_milestone')
assert hasattr(state, 'get_epic_stories')
assert hasattr(state, 'get_story_tasks')
assert hasattr(state, 'check_milestone_completion')
assert hasattr(state, 'achieve_milestone')
print("✓ StateManager methods OK")

# Verify backward compatibility
task_data = {'title': 'Test Task', 'description': 'Test'}
task = state.create_task(project_id=1, task_data=task_data)
assert task.task_type == TaskType.TASK
print("✓ Backward compatibility OK")

print("\n✅ Migration verification complete!")
```

### Test Verification

```bash
# Run basic tests
pytest tests/test_agile_hierarchy_basic.py -v
# Expected: 9/9 passing

# Run comprehensive tests
pytest tests/test_agile_hierarchy_comprehensive.py -v
# Expected: 72+ passing, 3 skipped

# Run regression tests
pytest tests/test_state.py tests/test_orchestrator.py -v
# Expected: All passing (no regressions)
```

---

## Rollback Procedure

If migration fails or issues occur, follow these steps to rollback.

### Rollback Step 1: Stop Obra

```bash
# Stop any running Obra processes
pkill -f "python.*obra"
```

### Rollback Step 2: Restore Database

**SQLite**:
```bash
# Restore from backup
cp orchestrator.db orchestrator.db.failed
cp orchestrator.db.backup.YYYYMMDD orchestrator.db
```

**PostgreSQL**:
```bash
# Drop and recreate database
psql -U postgres -c "DROP DATABASE obra_db;"
psql -U postgres -c "CREATE DATABASE obra_db;"
psql -U postgres obra_db < obra_db_backup_YYYYMMDD.sql
```

### Rollback Step 3: Verify Rollback

```python
from src.core.state import StateManager

state = StateManager('sqlite:///orchestrator.db')

# Check if old schema restored
tasks = state.get_project_tasks(project_id=1)
print(f"Tasks restored: {len(tasks)}")

# Verify migration columns don't exist
try:
    from src.core.models import TaskType
    print("ERROR: Migration still present")
except Exception:
    print("✓ Rollback successful")
```

### Rollback Step 4: Alternative - Manual Rollback SQL

If backup unavailable, use manual rollback script:

**File**: `migrations/versions/003_agile_hierarchy_rollback.sql`

```sql
-- WARNING: This will lose milestone data!

-- Remove new columns (SQLite requires table rebuild)
BEGIN TRANSACTION;

-- Backup existing data
CREATE TABLE task_backup AS
SELECT id, project_id, parent_task_id, title, description, status,
       assigned_to, priority, dependencies, context, result, task_metadata,
       retry_count, max_retries, started_at, completed_at, is_deleted,
       created_at, updated_at
FROM task;

-- Drop current table
DROP TABLE task;

-- Recreate with old schema (without task_type, epic_id, story_id)
CREATE TABLE task (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    parent_task_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING',
    assigned_to TEXT DEFAULT 'CLAUDE_CODE',
    priority INTEGER DEFAULT 5,
    dependencies TEXT DEFAULT '[]',
    context TEXT DEFAULT '{}',
    result TEXT DEFAULT '{}',
    task_metadata TEXT DEFAULT '{}',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    is_deleted BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES project_state(id),
    FOREIGN KEY (parent_task_id) REFERENCES task(id)
);

-- Restore data
INSERT INTO task SELECT * FROM task_backup;

-- Drop backup
DROP TABLE task_backup;

-- Drop milestone table
DROP TABLE IF EXISTS milestone;

COMMIT;
```

Apply rollback:
```bash
sqlite3 orchestrator.db < migrations/versions/003_agile_hierarchy_rollback.sql
```

---

## Troubleshooting

### Issue 1: Migration Fails with "duplicate column"

**Cause**: Migration already partially applied.

**Solution**:
```bash
# Check current schema
sqlite3 orchestrator.db "PRAGMA table_info(task);" | grep task_type

# If column exists, migration already applied
# Either:
# 1. Continue using v1.3 (no action needed)
# 2. Rollback completely (see Rollback Procedure)
```

### Issue 2: Tests Fail After Migration

**Cause**: Test fixtures may reference old schema.

**Solution**:
```bash
# Clear test database
rm -f test_orchestrator.db

# Re-run tests (will recreate with new schema)
pytest tests/ -v

# If still failing, check specific test errors
pytest tests/test_agile_hierarchy_basic.py -v --tb=short
```

### Issue 3: "TaskType object has no attribute 'EPIC'"

**Cause**: Python cache not cleared after code update.

**Solution**:
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete

# Restart Python interpreter
# Re-import
from src.core.models import TaskType
print(TaskType.EPIC)  # Should work
```

### Issue 4: Existing Code Breaks

**Unlikely** (v1.3 is backward compatible), but if it happens:

**Solution**:
```python
# Check TaskType defaults
task = state.create_task(1, {'title': 'Test', 'description': 'Test'})
print(task.task_type)  # Should be TaskType.TASK

# If epic methods don't exist
if not hasattr(state, 'create_epic'):
    print("ERROR: Migration not applied correctly")
    print("Solution: Re-apply migration or rollback")
```

### Issue 5: CLI Commands Not Found

**Cause**: CLI not reloaded after update.

**Solution**:
```bash
# Reload CLI
pip install -e .

# Verify commands available
obra epic --help
obra story --help
obra milestone --help
```

---

## Post-Migration Checklist

- [ ] Database backup created
- [ ] Migration script executed successfully
- [ ] New columns exist in task table
- [ ] Milestone table created
- [ ] TaskType enum accessible in Python
- [ ] StateManager methods available
- [ ] Basic tests pass (9/9)
- [ ] Comprehensive tests pass (72+/75)
- [ ] Existing functionality still works (regression tests)
- [ ] CLI commands accessible
- [ ] Team trained on new terminology
- [ ] Documentation reviewed

---

## Resources

- **Architecture Decision**: [ADR-013](../decisions/ADR-013-adopt-agile-work-hierarchy.md)
- **Workflow Guide**: [AGILE_WORKFLOW_GUIDE.md](AGILE_WORKFLOW_GUIDE.md)
- **System Overview**: [OBRA_SYSTEM_OVERVIEW.md](../design/OBRA_SYSTEM_OVERVIEW.md)
- **Test Guidelines**: [TEST_GUIDELINES.md](../development/TEST_GUIDELINES.md)

---

## Getting Help

- **GitHub Issues**: https://github.com/Omar-Unpossible/claude_code_orchestrator/issues
- **Documentation**: `docs/guides/` directory
- **Test Examples**: `tests/test_agile_hierarchy_*.py`

---

**Version**: 1.3.0
**Last Updated**: November 6, 2025
**Migration Time**: 15-30 minutes
**Status**: Production-Ready
