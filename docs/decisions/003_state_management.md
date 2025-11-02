# ADR-003: Centralized StateManager as Single Source of Truth

## Status
**Accepted** - 2025-11-01

## Context

The orchestrator has multiple components that need to access and modify state:
- Projects and tasks
- Agent interactions
- File changes
- Breakpoints
- Checkpoints
- Metrics

We need to decide how components access and modify this shared state.

## Decision

We will implement a **centralized StateManager** that serves as the single source of truth for all application state. All components MUST access state through StateManager - no direct database access is permitted.

## Rationale

### The Problem with Distributed State

**Without StateManager** (each component accesses database directly):

```python
# Component A
db.execute("UPDATE tasks SET status='complete' WHERE id=?", task_id)

# Component B (same time)
task = db.query("SELECT * FROM tasks WHERE id=?", task_id)
# Still sees old status! Race condition.
```

**Problems**:
- Race conditions (inconsistent views)
- No transaction support across components
- Duplicate SQL in every component
- Difficult to add caching
- Hard to debug (who changed what?)
- Can't ensure business rules are enforced

### The StateManager Solution

**With StateManager**:

```python
# Component A
state_manager.complete_task(task_id)  # Thread-safe, transactional

# Component B (same time)
task = state_manager.get_task(task_id)  # Always consistent
```

**Benefits**:
- ✅ Single source of truth
- ✅ Thread-safe operations
- ✅ Transaction support
- ✅ Consistent business logic
- ✅ Centralized logging
- ✅ Easy to add caching
- ✅ Clear ownership

## Design Principles

### 1. All State Access via StateManager

**Rule**: No component may access the database directly.

**Enforcement**:
- StateManager owns database connection
- Other components don't import SQLAlchemy models
- Code reviews check for violations

**Example**:

✅ **Correct**:
```python
task = state_manager.get_task(task_id)
state_manager.update_task(task_id, status='complete')
```

❌ **Wrong**:
```python
from src.core.models import Task
task = session.query(Task).get(task_id)  # NEVER do this!
```

### 2. Thread-Safe Operations

**Problem**: Multiple threads accessing state concurrently

**Solution**: Use locks for all state mutations

```python
class StateManager:
    def __init__(self):
        self._lock = threading.RLock()

    def update_task(self, task_id, **updates):
        with self._lock:
            # Safe to modify state here
            task = self._get_task(task_id)
            for key, value in updates.items():
                setattr(task, key, value)
            self._session.commit()
```

### 3. Transaction Support

**Atomic Operations**: Multiple changes succeed together or fail together

```python
class StateManager:
    @contextmanager
    def transaction(self):
        """Context manager for transactions."""
        with self._lock:
            try:
                yield
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise

# Usage
with state_manager.transaction():
    state_manager.create_interaction(...)
    state_manager.update_task_status(...)
    state_manager.record_file_change(...)
# All committed together, or all rolled back
```

### 4. Event Emission for Monitoring

**Pattern**: Emit events on state changes for monitoring/logging

```python
class StateManager:
    def __init__(self):
        self._event_subscribers = []

    def update_task(self, task_id, **updates):
        with self._lock:
            task = self._update_task_internal(task_id, **updates)
            self._emit_event('task_updated', {
                'task_id': task_id,
                'changes': updates
            })
```

**Benefits**:
- Centralized monitoring
- Audit trail
- Debugging support
- Metrics collection

### 5. Separation of Read and Write

**Pattern**: Separate methods for reads vs writes

```python
class StateManager:
    # Read operations (no lock needed if read-only)
    def get_task(self, task_id): ...
    def list_tasks(self, **filters): ...
    def get_interactions(self, task_id): ...

    # Write operations (always locked)
    def create_task(self, **data): ...
    def update_task(self, task_id, **updates): ...
    def delete_task(self, task_id): ...
```

**Benefits**:
- Clear intent
- Better performance (reads can be concurrent if DB supports it)
- Easier to add caching

## StateManager Responsibilities

### Project Management
- Create/read/update/delete projects
- List projects with filters
- Project metadata

### Task Management
- Create tasks with dependencies
- Update task status
- Resolve dependencies
- Track task history

### Interaction Management
- Record agent interactions
- Store prompts and responses
- Link to tasks
- Interaction history

### File Change Tracking
- Record file modifications
- Store file hashes
- Link changes to interactions
- Query changes by time range

### Checkpoint Management
- Create state snapshots
- Restore from checkpoints
- List available checkpoints
- Clean up old checkpoints

### Breakpoint Management
- Record breakpoint triggers
- Store resolution
- Link to tasks
- Breakpoint history

### Metrics and Analytics
- Record performance metrics
- Store confidence scores
- Calculate success rates
- Generate reports

## Implementation Details

### Singleton Pattern

**Why**: Only one StateManager instance should exist

```python
class StateManager:
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
```

**Usage**:
```python
state_manager = StateManager()  # Always returns same instance
```

### Connection Pooling

**Why**: Avoid connection exhaustion

```python
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True  # Verify connections
)
```

### Comprehensive Logging

**All state changes logged**:

```python
def update_task(self, task_id, **updates):
    logger.info(
        f"Updating task {task_id}",
        extra={'changes': updates}
    )
    # ... perform update
    logger.info(f"Task {task_id} updated successfully")
```

## Consequences

### Positive

✅ **No race conditions**:
- Locks prevent concurrent modification
- Transactions ensure atomicity
- Consistent view of state

✅ **Single place for business logic**:
- All validation in StateManager
- Consistent rule enforcement
- Easy to update rules

✅ **Easy debugging**:
- All state changes logged in one place
- Set breakpoint in StateManager
- Clear audit trail

✅ **Testable**:
- Mock StateManager for unit tests
- Test components in isolation
- Integration tests verify StateManager

✅ **Performance optimization centralized**:
- Add caching in one place
- Query optimization benefits all components
- Connection pooling managed centrally

✅ **Database abstraction**:
- Components don't know about database
- Can swap SQLite → PostgreSQL without changing components
- Migration path clear

### Negative

❌ **Single point of failure**:
- If StateManager has bug, affects everything
- **Mitigation**: Comprehensive test coverage (≥90%)

❌ **Performance bottleneck (potential)**:
- All state access goes through one component
- **Mitigation**: Connection pooling, caching, async operations

❌ **Larger interface**:
- StateManager has many methods
- **Mitigation**: Group related methods, clear documentation

## Alternatives Considered

### Alternative 1: Direct Database Access

**Description**: Each component imports models and queries database directly.

**Pros**:
- Simpler initially (no abstraction layer)
- Faster to write first version

**Cons**:
- Race conditions
- Duplicate SQL across components
- No transaction support across components
- Difficult to debug
- Hard to add caching
- Business logic scattered

**Why Rejected**: Leads to bugs and inconsistencies. Technical debt accumulates quickly.

### Alternative 2: Multiple Managers

**Description**: Separate managers for tasks, interactions, files, etc.

**Pros**:
- Smaller interfaces per manager
- Clear separation of concerns

**Cons**:
- Transactions across managers difficult
- Still need coordination layer
- Which manager owns what?
- More complex for users

**Why Rejected**: Coordination problem just moves up one level. Single manager is simpler.

### Alternative 3: Repository Pattern

**Description**: Separate repository classes per entity (TaskRepository, InteractionRepository).

**Pros**:
- Clean separation
- Standard pattern

**Cons**:
- More classes to maintain
- Cross-entity operations complex
- Overkill for this project size

**Why Rejected**: StateManager provides similar benefits with less overhead.

## Critical Rules

### Rule 1: NO BYPASSING StateManager

**Never**:
```python
from src.core.models import Task
task = session.query(Task).get(task_id)  # ❌ FORBIDDEN
```

**Always**:
```python
task = state_manager.get_task(task_id)  # ✅ CORRECT
```

**Enforcement**: Code reviews must check this.

### Rule 2: Use Transactions for Multi-Step Operations

**Never**:
```python
state_manager.create_interaction(...)
state_manager.update_task(...)  # If this fails, interaction orphaned
```

**Always**:
```python
with state_manager.transaction():
    state_manager.create_interaction(...)
    state_manager.update_task(...)
# Both succeed or both rollback
```

### Rule 3: Emit Events for Monitoring

**Never**: Silent state changes

**Always**: Emit event when state changes
```python
def update_task(self, task_id, **updates):
    # Update...
    self._emit_event('task_updated', {'task_id': task_id})
```

## Testing Strategy

### Unit Tests
- Mock StateManager for component tests
- Test StateManager methods in isolation
- Verify transaction behavior
- Test thread safety

### Integration Tests
- Real database (SQLite in-memory)
- Test complex workflows
- Verify transactions work end-to-end
- Test checkpoint/restore

### Coverage Target
- StateManager: ≥90% (it's critical)
- Overall: ≥85%

## Migration Path

If we need to swap databases:

1. Update StateManager implementation
2. No changes to components (they use StateManager API)
3. Run tests to verify behavior unchanged

Example: SQLite → PostgreSQL
- Change connection string in StateManager
- Add PostgreSQL-specific optimizations if needed
- Components unchanged

## Validation

This decision will be validated by:
1. ✅ Zero race conditions in concurrent tests (M1)
2. ✅ Transaction tests pass (M1)
3. ⏳ No bugs traced to inconsistent state (M1-M7)
4. ⏳ StateManager test coverage ≥90% (M1)

## References

- [M1 Implementation Plan](../../plans/01_foundation.json) - StateManager implementation
- [System Design](../architecture/system_design.md) - StateManager responsibilities
- [Martin Fowler on Patterns of Enterprise Application Architecture](https://martinfowler.com/eaaCatalog/)

---
**Decision Date**: 2025-11-01
**Decision Makers**: Project Lead
**Status**: Planned (Implementation in M1)
**Priority**: Critical - This is the spine of the system
