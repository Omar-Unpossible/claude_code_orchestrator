# Fix Plan: InteractiveSession Import Error

**Document Type**: Implementation Plan (Machine-Optimized)
**Priority**: Medium-High
**Estimated Time**: 5 minutes
**Complexity**: Trivial

## Error Summary

```
ImportError: cannot import name 'InteractiveSession' from 'src.interactive'
Location: tests/test_llm_graceful_fallback.py:20
Actual Class: InteractiveMode (src/interactive.py:25)
```

## Root Cause

Test file uses incorrect class name `InteractiveSession` instead of `InteractiveMode`.

## Validation Checklist

- [ ] Read test file to identify all occurrences
- [ ] Update import statement (line 20)
- [ ] Update all class instantiations (search pattern: `InteractiveSession(`)
- [ ] Verify no other files use wrong name
- [ ] Run test collection to verify fix
- [ ] Run full test file to ensure tests pass

## Execution Steps

### Step 1: Analyze Scope
**Action**: Grep for all occurrences of `InteractiveSession` in test file
**Command**: `grep -n "InteractiveSession" tests/test_llm_graceful_fallback.py`
**Expected**: Multiple matches (import + instantiations)

### Step 2: Update Import Statement
**Action**: Fix line 20 import
**Pattern**:
```python
# OLD
from src.interactive import InteractiveSession

# NEW
from src.interactive import InteractiveMode
```

### Step 3: Update Class Instantiations
**Action**: Replace all `InteractiveSession(` with `InteractiveMode(`
**Method**: Use Edit tool with replace_all=True
**Expected Locations**:
- Line ~169: Test initialization
- Line ~200: Test initialization
- Line ~230: Test initialization
- Line ~425: Integration test

### Step 4: Verify No Other Files Affected
**Action**: Search entire codebase for `InteractiveSession`
**Command**: `grep -r "InteractiveSession" --include="*.py" .`
**Expected**: Should only find test file (after fix)

### Step 5: Validate Fix
**Action**: Run pytest collection
**Command**: `python -m pytest --collect-only tests/test_llm_graceful_fallback.py`
**Success Criteria**: No ImportError, all tests collected

### Step 6: Run Tests
**Action**: Execute test file
**Command**: `python -m pytest tests/test_llm_graceful_fallback.py -v`
**Note**: Tests may fail due to other issues, but ImportError must be resolved

## Risk Assessment

**Risk Level**: Minimal
**Reversibility**: High (simple text change)
**Side Effects**: None (isolated to test file)

## Success Criteria

1. ImportError eliminated
2. Test file collects successfully
3. No new errors introduced
4. All `InteractiveSession` references updated to `InteractiveMode`

## Rollback Plan

If issues occur:
```bash
git checkout tests/test_llm_graceful_fallback.py
```

## Post-Fix Actions

- Update test logs
- Run full test suite to verify no regression
- Document fix in CHANGELOG.md if committing
