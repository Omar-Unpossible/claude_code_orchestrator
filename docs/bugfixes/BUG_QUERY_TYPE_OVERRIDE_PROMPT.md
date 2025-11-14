# Claude Startup Prompt: Query Type Bug Fix

## Context
Fix bug where LLM-extracted query_type is overridden by keyword matching in NL command processor.

## Bug Summary
- **User input**: "For project #1, list the current plan (epics, stories, tasks, etc)"
- **Current behavior**: Returns flat list of ALL projects (SIMPLE query)
- **Expected behavior**: Returns hierarchical structure for project #1 (HIERARCHICAL query)
- **Root cause**: Lines 532-545 in `src/nl/nl_command_processor.py` ignore LLM extraction from ParameterExtractor

## Implementation Plan
Read `/home/omarwsl/projects/claude_code_orchestrator/docs/bugfixes/BUG_QUERY_TYPE_OVERRIDE.json` for complete machine-readable implementation plan.

## Tasks (75 minutes total)

### 1. Code Changes (20 minutes)
**Primary Fix**: `src/nl/nl_command_processor.py` (lines 532-545)
- Priority 1: Check `parameter_result.parameters['query_type']` from LLM
- Priority 2: Convert string to `QueryType` enum with error handling
- Priority 3: Fall back to keyword matching if LLM didn't extract
- Add `'plan'` and `'plans'` to hierarchical keywords
- Add debug/warning logging

**Secondary Fix**: `src/nl/nl_query_helper.py` (lines 203-223)
- Add identifier filtering for PROJECT queries (handle int ID and str name)
- Preserve backward compatibility (identifier=None shows all)

### 2. Unit Tests (20 minutes)
**File**: `tests/test_nl_command_processor.py`
- `test_query_type_llm_extraction_priority()` - LLM takes priority
- `test_query_type_keyword_fallback()` - Keyword fallback works
- `test_query_type_invalid_enum_fallback()` - Invalid LLM value falls back
- `test_query_type_plan_keyword()` - "plan" keyword routes to HIERARCHICAL
- `test_all_query_types()` - All query types work (both paths)

### 3. Integration Test (15 minutes)
**File**: `tests/test_integration_nl_queries.py`
- `test_project_plan_query_e2e()` - End-to-end with real StateManager

### 4. Manual Testing (10 minutes)
Test commands:
1. "For project #1, list the current plan (epics, stories, tasks, etc)" → Hierarchical
2. "Show me the workplan for project #2" → Hierarchical
3. "List all projects" → SIMPLE (regression test)

### 5. Documentation (10 minutes)
- `docs/guides/NL_COMMAND_GUIDE.md` - Add "plan" keyword examples
- `src/nl/nl_command_processor.py` - Update docstring
- `docs/architecture/LLM_REFERENCE_MANAGEMENT.md` - Document priority (if applicable)

## Success Criteria
✅ "list project plan" → Returns hierarchical structure (not flat list)
✅ Identifier filtering works for PROJECT queries
✅ "plan" keyword recognized
✅ LLM extraction takes priority
✅ Keyword fallback still works
✅ All existing queries unaffected
✅ All tests passing (9 tests)

## Key Files
- `src/nl/nl_command_processor.py:532-545` - Primary fix
- `src/nl/nl_query_helper.py:203-223` - Secondary fix
- `src/nl/types.py` - QueryType enum
- `tests/test_nl_command_processor.py` - Unit tests
- `tests/test_integration_nl_queries.py` - Integration test

## Testing Requirements
⚠️ Read `docs/testing/TEST_GUIDELINES.md` FIRST to prevent WSL2 crashes
- Max sleep per test: 0.5s
- Max threads per test: 5
- Max memory: 20KB per test

## Risk Level
**LOW** - LLM extraction exists (unused), keyword fallback preserved, 20 lines changed, comprehensive tests

## References
- Human-readable plan: `docs/bugfixes/BUG_QUERY_TYPE_OVERRIDE.md`
- Machine-readable plan: `docs/bugfixes/BUG_QUERY_TYPE_OVERRIDE.json`
- ADR-016: Five-stage NL pipeline design
- ADR-017: Unified execution architecture
