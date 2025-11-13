# ADR-017 Story 3 Startup Prompt

**Context**: You're implementing ADR-017 (Unified Execution Architecture) for Obra. Stories 0-2 are complete. Now implement Story 3.

---

## What You're Building

**Story 3**: Refactor CommandExecutor → NLQueryHelper (10 hours)

**Purpose**: Remove write operations from CommandExecutor, keep only read-only query operations.

**Key Changes**:
- Rename `CommandExecutor` → `NLQueryHelper`
- Rename file `src/nl/command_executor.py` → `src/nl/nl_query_helper.py`
- **Remove ALL write operations** (CREATE/UPDATE/DELETE)
- **Keep ONLY query operations** (return metadata, don't execute)
- Add deprecation warnings for backward compatibility

---

## The Problem

Currently, `CommandExecutor` handles both:
1. **Write operations**: CREATE/UPDATE/DELETE (will move to orchestrator via IntentToTaskConverter)
2. **Query operations**: SIMPLE/HIERARCHICAL/NEXT_STEPS/BACKLOG/ROADMAP (stay in NL layer)

This violates the unified architecture where ALL writes go through orchestrator.

---

## The Solution

Create `NLQueryHelper` that:
- **Only** handles QUERY operations
- Returns **metadata** (query context), doesn't execute queries
- Provides read-only support for NL pipeline
- Maintains backward compatibility with deprecation warnings

---

## Implementation Plan

### Step 1: Create NLQueryHelper (New File)

**File**: `src/nl/nl_query_helper.py`
**Size**: ~280 lines (down from 1214 lines)

**Keep from CommandExecutor**:
- `_execute_query()` → Refactor to `build_query_context()`
- `_query_simple()`, `_query_hierarchical()`, `_query_next_steps()`, `_query_backlog()`, `_query_roadmap()`
- Helper: `_resolve_identifier_to_id()` (for queries)

**Remove from CommandExecutor**:
- `execute()` method (write operation routing)
- `_execute_create()`, `_execute_update()`, `_execute_delete()`
- ALL create helpers: `_create_epic()`, `_create_story()`, `_create_task()`, `_create_subtask()`, `_create_milestone()`
- ALL update/delete helpers: `_update_entity()`, `_delete_entity()`
- Reference resolution: `_resolve_references()`
- Legacy methods: `execute_legacy()`, `_execute_single_entity()`

### Step 2: Refactor Query Method Signature

**Old (CommandExecutor)**:
```python
def _execute_query(self, context: OperationContext, project_id: int) -> ExecutionResult:
    # Executes query and returns results
    return ExecutionResult(success=True, results={'entities': [...]})
```

**New (NLQueryHelper)**:
```python
def build_query_context(self, context: OperationContext, project_id: int) -> Dict[str, Any]:
    """Build query context metadata (does NOT execute query).

    Returns:
        Dict with query metadata:
        - query_type: SIMPLE | HIERARCHICAL | NEXT_STEPS | BACKLOG | ROADMAP
        - entity_type: project | epic | story | task | milestone
        - filters: Dict[str, Any]
        - project_id: int
    """
    # Return metadata ONLY, caller executes query
```

### Step 3: Add Deprecation Support

Keep a deprecated `execute()` method for backward compatibility:

```python
@deprecated(version='1.8.0', reason="Use build_query_context() instead")
def execute(self, context: OperationContext, project_id: Optional[int] = None) -> ExecutionResult:
    """DEPRECATED: Use build_query_context() instead.

    This method is deprecated and will be removed in v1.8.0.
    """
    warnings.warn(
        "NLQueryHelper.execute() is deprecated. Use build_query_context() instead.",
        DeprecationWarning,
        stacklevel=2
    )

    # Forward to query helpers for QUERY operations only
    if context.operation != OperationType.QUERY:
        raise ExecutionException(
            f"NLQueryHelper only supports QUERY operations. "
            f"Got: {context.operation}. "
            f"Use IntentToTaskConverter for {context.operation} operations."
        )

    return self._execute_query(context, project_id or self.default_project_id)
```

---

## File Structure

```python
# src/nl/nl_query_helper.py (~280 lines)

"""Read-only query helper for Natural Language Commands (ADR-017).

After ADR-017 refactor, NLQueryHelper handles ONLY query operations.
Write operations (CREATE/UPDATE/DELETE) now route through orchestrator
via IntentToTaskConverter.

Classes:
    QueryContext: Dataclass holding query metadata
    NLQueryHelper: Build query context for SIMPLE/HIERARCHICAL/etc queries
"""

import logging
import warnings
from dataclasses import dataclass
from typing import Dict, Any, Optional
from core.state import StateManager
from src.nl.types import OperationContext, OperationType, QueryType, EntityType

logger = logging.getLogger(__name__)


class QueryException(Exception):
    """Exception raised during query context building."""
    pass


@dataclass
class QueryContext:
    """Query metadata (not results).

    Attributes:
        query_type: Type of query (SIMPLE, HIERARCHICAL, etc.)
        entity_type: Entity type to query
        filters: Filter criteria
        project_id: Project ID
        sort_order: Sort order (list of tuples)
    """
    query_type: QueryType
    entity_type: EntityType
    filters: Dict[str, Any]
    project_id: int
    sort_order: List[Tuple[str, str]] = field(default_factory=list)


class NLQueryHelper:
    """Build query context for natural language queries (READ-ONLY).

    After ADR-017, this class ONLY handles queries. Write operations
    (CREATE/UPDATE/DELETE) are handled by IntentToTaskConverter + Orchestrator.

    Supported query types:
    - SIMPLE: List entities (projects, epics, stories, tasks)
    - HIERARCHICAL: Show task hierarchies (epics → stories → tasks)
    - NEXT_STEPS: Show next pending tasks
    - BACKLOG: Show all pending tasks
    - ROADMAP: Show milestones and associated epics

    Args:
        state_manager: StateManager instance for queries
        default_project_id: Default project ID (default: 1)

    Example:
        >>> helper = NLQueryHelper(state_manager)
        >>> context = OperationContext(
        ...     operation=OperationType.QUERY,
        ...     entity_type=EntityType.TASK,
        ...     query_type=QueryType.SIMPLE
        ... )
        >>> query_ctx = helper.build_query_context(context, project_id=1)
        >>> # Caller executes query using query_ctx metadata
    """

    def __init__(self, state_manager: StateManager, default_project_id: int = 1):
        self.state_manager = state_manager
        self.default_project_id = default_project_id
        logger.info("NLQueryHelper initialized (query-only mode)")

    def build_query_context(
        self,
        context: OperationContext,
        project_id: Optional[int] = None
    ) -> QueryContext:
        """Build query context metadata (does NOT execute query).

        Args:
            context: OperationContext with QUERY operation
            project_id: Project ID (uses default if not specified)

        Returns:
            QueryContext with query metadata

        Raises:
            QueryException: If context.operation is not QUERY
        """
        if context.operation != OperationType.QUERY:
            raise QueryException(
                f"NLQueryHelper only handles QUERY operations. "
                f"Got: {context.operation}. "
                f"Use IntentToTaskConverter + Orchestrator for write operations."
            )

        proj_id = project_id or self.default_project_id
        query_type = context.query_type or QueryType.SIMPLE

        # Map WORKPLAN to HIERARCHICAL
        if query_type == QueryType.WORKPLAN:
            query_type = QueryType.HIERARCHICAL

        # Build query context based on type
        filters = self._build_filters(context, proj_id)
        sort_order = self._build_sort_order(context, query_type)

        return QueryContext(
            query_type=query_type,
            entity_type=context.entity_type,
            filters=filters,
            project_id=proj_id,
            sort_order=sort_order
        )

    # ... (helper methods for building filters, executing queries, etc.)

    # DEPRECATED method for backward compatibility
    @deprecated(version='1.8.0', reason="Use build_query_context() instead")
    def execute(self, context: OperationContext, project_id: Optional[int] = None) -> ExecutionResult:
        """DEPRECATED: Use build_query_context() instead."""
        warnings.warn(...)
        # Forward to _execute_query for QUERY operations only
```

---

## Test Updates

### Remove Tests for Write Operations
**File**: `tests/nl/test_command_executor.py`
**Rename to**: `tests/nl/test_nl_query_helper.py`

**Remove**:
- All CREATE operation tests (~15 tests)
- All UPDATE operation tests (~8 tests)
- All DELETE operation tests (~6 tests)
- Legacy API tests

**Keep and Update**:
- Query context building tests (~30 tests)
- Hierarchical query support tests
- Query type detection tests
- Filter construction tests

**Add**:
- Deprecation warning tests (~5 tests)
- Query metadata structure validation (~3 tests)
- Write operation rejection tests (~2 tests)

---

## Acceptance Criteria

✅ **Refactoring**:
- [ ] `CommandExecutor` renamed to `NLQueryHelper`
- [ ] File renamed: `command_executor.py` → `nl_query_helper.py`
- [ ] All write operations removed (CREATE/UPDATE/DELETE)
- [ ] Query operations return metadata (not results)
- [ ] File size reduced: 1214 → ~280 lines

✅ **Backward Compatibility**:
- [ ] Deprecated `execute()` method for QUERY operations
- [ ] Clear error for write operations
- [ ] Deprecation warnings logged

✅ **Tests**:
- [ ] Test file renamed: `test_command_executor.py` → `test_nl_query_helper.py`
- [ ] Write operation tests removed
- [ ] Query tests updated for new API
- [ ] 30+ unit tests passing
- [ ] Code coverage ≥90%

✅ **Integration**:
- [ ] No breaking changes for query functionality
- [ ] Imports updated in `nl_command_processor.py`
- [ ] Smoke tests still passing

---

## Validation

**After Story 3 complete**:
```bash
# Run NL smoke tests (should still work with renamed component)
pytest tests/smoke/ -v -k "nl_"

# Run LLM integration tests
pytest tests/integration/test_llm_connectivity.py -v

# Verify query functionality intact
pytest tests/nl/test_nl_query_helper.py -v --cov=src/nl/nl_query_helper
```

---

## Key Reminders

1. **Do NOT execute queries** - Return metadata only
2. **Reject write operations** - Throw clear error message
3. **Add deprecation warnings** - For backward compatibility
4. **Keep query helpers** - _query_simple, _query_hierarchical, etc.
5. **Reduce file size** - 1214 → ~280 lines (remove 75% of code)

---

**Ready to start? Implement Story 3: Refactor CommandExecutor → NLQueryHelper.**
