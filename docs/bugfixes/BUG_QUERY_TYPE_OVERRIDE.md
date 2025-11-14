# Bug Fix: Query Type LLM Extraction Override

**Bug ID**: Query Type Keyword Override
**Date**: November 13, 2025
**Severity**: Medium
**Status**: Planning
**Component**: Natural Language Command Processor (ADR-016)

## Problem

When users query a project's hierarchical plan using natural language, the system returns a flat list of ALL projects instead of the hierarchical structure for the specified project.

**User Input**:
```
"For project #1, list the current plan (epics, stories, tasks, etc)"
```

**Expected Behavior**:
- Show hierarchical structure: Epics → Stories → Tasks
- Filter to project #1 only
- Route to `_query_hierarchical()` handler

**Actual Behavior**:
- Shows flat list of ALL 11 projects
- Routes to `_query_simple()` handler
- Ignores project identifier

**Error Output**:
```
✓ Found 11 project(s)

Projects:
--------------------------------------------------------------------------------
  #11: CLI Smoke Test 1763057518
  #10: CLI Smoke Test 1763057434
  #9: CLI Smoke Test 1763020751
  ...
```

## Root Cause

**Location**: `src/nl/nl_command_processor.py` (lines 532-545)

**Two Issues**:

### Issue 1: LLM Extraction Ignored
The ParameterExtractor (Stage 4 of NL pipeline) correctly extracts `{'query_type': 'hierarchical'}` with 0.59 confidence by understanding that "plan (epics, stories, tasks)" implies a hierarchical view.

However, lines 532-545 use **hardcoded keyword matching** that **overrides** the LLM's intelligent extraction:

```python
# Current code (WRONG)
query_type = None
if operation_result.operation_type == OperationType.QUERY:
    # Only checks hardcoded keywords
    if any(keyword in message.lower() for keyword in ['workplan', 'hierarchy', 'hierarchical']):
        query_type = QueryType.HIERARCHICAL
    elif ...
    else:
        query_type = QueryType.SIMPLE  # ❌ WRONG: Defaults to SIMPLE
```

**Problem**: The keyword list doesn't include "plan", so the LLM's correct extraction is discarded.

### Issue 2: _query_simple() Ignores Identifier
**Location**: `src/nl/nl_query_helper.py` (lines 203-223)

When `entity_type=PROJECT` and `identifier=1`, the `_query_simple()` method returns ALL projects instead of filtering to project #1:

```python
# Current code (lines 203-223)
if context.entity_type == EntityType.PROJECT:
    projects = self.state_manager.list_projects()  # ❌ No filtering
    return QueryResult(
        ...
        results={'entities': [all projects]}  # ❌ Returns all
    )
```

## Solution

### Fix 1: Prioritize LLM Extraction (Primary Fix)

**File**: `src/nl/nl_command_processor.py` (lines 532-545)

**Strategy**: Prioritize ParameterExtractor's LLM-based extraction over hardcoded keyword matching, while maintaining keyword matching as a reliable fallback.

**Implementation**:
```python
# NEW CODE (lines 532-560)
query_type = None
if operation_result.operation_type == OperationType.QUERY:
    # PRIORITY 1: Check if ParameterExtractor found query_type
    if 'query_type' in parameter_result.parameters:
        query_type_str = parameter_result.parameters['query_type']
        # Convert string to enum
        try:
            query_type = QueryType(query_type_str)
            logger.debug(f"Using LLM-extracted query_type: {query_type}")
        except ValueError:
            logger.warning(
                f"Invalid query_type '{query_type_str}' from LLM, "
                f"falling back to keyword matching"
            )

    # PRIORITY 2: Keyword fallback if LLM didn't extract or conversion failed
    if query_type is None:
        if any(keyword in message.lower() for keyword in
               ['workplan', 'hierarchy', 'hierarchical', 'plan', 'plans']):
            query_type = QueryType.HIERARCHICAL
        elif any(keyword in message.lower() for keyword in
                 ['next', 'next steps', "what's next"]):
            query_type = QueryType.NEXT_STEPS
        elif any(keyword in message.lower() for keyword in
                 ['backlog', 'pending', 'todo']):
            query_type = QueryType.BACKLOG
        elif any(keyword in message.lower() for keyword in
                 ['roadmap', 'milestone']):
            query_type = QueryType.ROADMAP
        else:
            query_type = QueryType.SIMPLE
```

**Changes**:
1. Check `parameter_result.parameters` for `'query_type'` key
2. Convert string to `QueryType` enum with error handling
3. Fall back to keyword matching if LLM didn't extract or value is invalid
4. Add `'plan'` and `'plans'` to hierarchical keyword list
5. Add debug/warning logging for troubleshooting

### Fix 2: _query_simple() Identifier Filtering (Secondary Fix)

**File**: `src/nl/nl_query_helper.py` (lines 203-223)

**Note**: This is a SEPARATE bug but impacts the same user scenario.

**Implementation**:
```python
# NEW CODE (lines 203-223)
if context.entity_type == EntityType.PROJECT:
    projects = self.state_manager.list_projects()

    # Filter by identifier if provided
    if context.identifier is not None:
        if isinstance(context.identifier, int):
            projects = [p for p in projects if p.id == context.identifier]
        elif isinstance(context.identifier, str):
            # Match by name (case-insensitive)
            projects = [p for p in projects
                       if context.identifier.lower() in p.project_name.lower()]

    return QueryResult(
        success=True,
        query_type='simple',
        entity_type='project',
        results={
            'query_type': 'simple',
            'entity_type': 'project',
            'entities': [
                {
                    'id': p.id,
                    'name': p.project_name,
                    'description': p.description,
                    'status': p.status.value
                }
                for p in projects
            ],
            'count': len(projects)
        }
    )
```

## Implementation Plan

### Step 1: ✅ Analysis (COMPLETED)
- [x] Analyzed NL pipeline logs
- [x] Identified LLM extraction vs keyword matching discrepancy
- [x] Traced execution path through `_query_simple()`
- [x] Documented root causes

### Step 2: Modify Query Type Detection Logic
**File**: `src/nl/nl_command_processor.py` (lines 532-545)
**Time**: ~10 minutes

**Tasks**:
- [ ] Add LLM extraction priority check
- [ ] Add `QueryType()` enum conversion with try/except
- [ ] Keep keyword fallback logic
- [ ] Add `'plan'` and `'plans'` to hierarchical keywords
- [ ] Add debug logging for LLM extraction path
- [ ] Add warning logging for fallback path

### Step 3: Add Identifier Filtering
**File**: `src/nl/nl_query_helper.py` (lines 203-223)
**Time**: ~10 minutes

**Tasks**:
- [ ] Add identifier filtering for PROJECT queries
- [ ] Handle both int (ID) and str (name) identifiers
- [ ] Preserve backward compatibility (if `identifier=None`, show all)
- [ ] Apply same pattern to MILESTONE queries (lines 225-245)

### Step 4: Write Unit Tests
**File**: `tests/test_nl_command_processor.py`
**Time**: ~20 minutes

**Test Cases**:
- [ ] `test_query_type_llm_extraction_priority()` - LLM extraction takes priority
- [ ] `test_query_type_keyword_fallback()` - Keyword fallback when LLM doesn't extract
- [ ] `test_query_type_invalid_enum_fallback()` - Invalid LLM value falls back to keywords
- [ ] `test_query_type_plan_keyword()` - "plan" keyword routes to HIERARCHICAL
- [ ] `test_all_query_types()` - NEXT_STEPS, BACKLOG, ROADMAP, SIMPLE coverage

### Step 5: Write Integration Test
**File**: `tests/test_integration_nl_queries.py`
**Time**: ~15 minutes

**Test Case**:
- [ ] `test_project_plan_query_e2e()` - End-to-end test with real StateManager
  - Creates project #1 with epic/stories
  - Processes: `"For project #1, list the current plan"`
  - Asserts: Routes to HIERARCHICAL query
  - Asserts: Returns epic→story→task structure

### Step 6: Manual Testing
**Time**: ~10 minutes

**Test Commands**:
1. `"For project #1, list the current plan (epics, stories, tasks, etc)"`
   - Should show hierarchical structure
   - Should filter to project #1
2. `"Show me the workplan for project #2"`
   - Should show hierarchical structure
   - Should filter to project #2
3. `"List all projects"`
   - Should show ALL projects (SIMPLE query)

**Success Criteria**:
- ✅ No "Found 11 project(s)" output for hierarchical queries
- ✅ Shows epic→story→task tree structure
- ✅ Filters to specified project only
- ✅ SIMPLE queries still work for "list all" commands

### Step 7: Update Documentation
**Time**: ~10 minutes

**Files**:
- [ ] `docs/guides/NL_COMMAND_GUIDE.md` - Add "plan" keyword examples
- [ ] `src/nl/nl_command_processor.py` - Update docstring with priority explanation
- [ ] `docs/architecture/LLM_REFERENCE_MANAGEMENT.md` - Document query_type extraction priority (if applicable)

**Updates**:
- Document LLM extraction takes priority over keywords
- Add "plan" as recognized hierarchical keyword
- Update examples: `"list project plan"` command
- Note fallback behavior in troubleshooting section

## Testing Strategy

### Unit Tests (5 tests, ~20 minutes)
- LLM extraction priority
- Keyword fallback
- Invalid enum fallback
- New "plan" keyword
- All query types coverage

### Integration Tests (1 test, ~15 minutes)
- End-to-end project plan query
- Real StateManager with test data
- Verify hierarchical routing and filtering

### Manual Tests (3 commands, ~10 minutes)
- Original failing command
- Variations with different projects
- SIMPLE query regression test

## Risk Assessment

**Risk Level**: Low

**Why Low Risk**:
- ✅ LLM extraction already exists, just currently unused
- ✅ Keyword fallback ensures backward compatibility
- ✅ Clear error handling prevents failures
- ✅ Small, focused change (20 lines)
- ✅ Comprehensive test coverage

**Backward Compatibility**:
- ✅ Keyword matching preserved as fallback
- ✅ Existing SIMPLE queries unaffected
- ✅ All current query types still work

**Rollback Plan**:
- Simple git revert if issues found
- Keyword-only mode works as fallback
- No database schema changes

## Estimated Effort

| Task | Time |
|------|------|
| Code changes (nl_command_processor.py) | 10 min |
| Code changes (nl_query_helper.py) | 10 min |
| Unit tests (5 tests) | 20 min |
| Integration test (1 test) | 15 min |
| Manual testing (3 commands) | 10 min |
| Documentation updates | 10 min |
| **TOTAL** | **75 minutes** |

## Success Metrics

**Before Fix**:
- ❌ "list project plan" → Returns all projects (SIMPLE query)
- ❌ Identifier filtering not working for PROJECT queries
- ❌ "plan" keyword not recognized

**After Fix**:
- ✅ "list project plan" → Returns hierarchical structure (HIERARCHICAL query)
- ✅ Identifier filtering works for PROJECT queries
- ✅ "plan" keyword routes to HIERARCHICAL
- ✅ LLM extraction takes priority over keywords
- ✅ Keyword fallback still works
- ✅ All existing queries unaffected

## Related Issues

**Similar Bugs**: None known

**Upstream Dependencies**: None

**Downstream Impact**:
- NL command users will get more accurate query routing
- LLM's semantic understanding leveraged (aligns with ADR-016 goals)
- Better handling of natural phrasing (e.g., "show plan" vs "show hierarchy")

## References

**Code Locations**:
- `src/nl/nl_command_processor.py` - Query type detection (lines 532-545)
- `src/nl/nl_query_helper.py` - Query execution (lines 203-223)
- `src/nl/parameter_extractor.py` - LLM parameter extraction (Stage 4)
- `src/nl/types.py` - OperationContext, QueryType enums

**Architecture Decisions**:
- **[ADR-016: Decompose NL Entity Extraction](../decisions/ADR-016-decompose-nl-entity-extraction.md)** - Five-stage NL pipeline
- **[ADR-017: Unified Execution Architecture](../decisions/ADR-017-unified-execution-architecture.md)** - NL commands through orchestrator

**Testing Guidelines**:
- **[Test Guidelines](../testing/TEST_GUIDELINES.md)** - WSL2 crash prevention

---

**Status**: Ready for implementation
**Next Steps**: Create machine-optimized plan and startup prompt for Claude
