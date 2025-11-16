# STARTUP PROMPT: Urgent Phase 3 Fixes Implementation

**Session Goal**: Implement 3 critical fixes to raise demo pass rate from 12.5% → 75%
**Estimated Duration**: 95 minutes
**Priority**: 🔴 CRITICAL (Blocks all demos)
**Date**: 2025-11-13

---

## Context (Read This First!)

Phase 3 testing revealed **catastrophic failures** that will cause live demos to fail:

**Test Results**:
- ✅ Infrastructure complete (8 demo tests, 8 workflow tests, 950+ variations created)
- ❌ **Demo scenario pass rate: 12.5%** (7/8 tests failed)
- ❌ **Obra workflow pass rate: 0%** (14/14 tests failed)
- ❌ **Variation test pass rate: ~82%** (below 90% target)

**Root Causes Identified**:
1. Confidence threshold too aggressive (0.8 vs actual 0.45-0.79)
2. Parameter extraction returns None → validation rejects
3. Synonym operations not recognized (build, craft, assemble)

**Impact**: **CURRENT CODE WILL FAIL LIVE DEMOS** - urgent fixes required.

---

## Your Mission

Implement 3 fixes to critical NL parsing issues:

1. **Fix A** (5 min): Lower confidence threshold 0.8 → 0.7
2. **Fix B** (30 min): Fix parameter None handling
3. **Fix C** (60 min): Add synonym expansion for operations

**Expected outcome**: Demo pass rate 12.5% → 75%, Variation pass rate 82% → 90%

---

## Implementation Instructions

### Read These Documents (In Order)

1. **This file** (URGENT_FIXES_STARTUP_PROMPT.md) - Context and overview
2. **URGENT_FIXES_MACHINE_SPEC.md** - Detailed implementation specifications
3. **URGENT_FIXES_IMPLEMENTATION_PLAN.md** - Full context and rationale

### Execute This Plan

**Step 1: Verify Environment** (5 min)
```bash
# Activate virtual environment
source venv/bin/activate

# Verify you're on main branch and up to date
git status
git pull origin main

# Create feature branch
git checkout -b fix/phase3-urgent-fixes
```

**Step 2: Implement Fix A - Confidence Threshold** (5 min)
```bash
# Read current value
grep "DEFAULT_CONFIDENCE_THRESHOLD" src/nl/nl_command_processor.py

# Expected: DEFAULT_CONFIDENCE_THRESHOLD = 0.8
```

**Change to**:
```python
DEFAULT_CONFIDENCE_THRESHOLD = 0.7  # Lowered from 0.8 (Phase 3 urgent fix)
```

**Quick test**:
```bash
# This test was failing at 0.8 threshold, should pass at 0.7
pytest tests/integration/test_demo_scenarios.py::TestProductionDemoFlows::test_basic_project_setup_demo -v -m "real_llm" --timeout=0
```

**Step 3: Implement Fix B - Parameter Null Handling** (30 min)

See URGENT_FIXES_MACHINE_SPEC.md for detailed code changes:
- Add REQUIRED_PARAMETERS constant
- Modify _parse_extracted_parameters() to skip None for optional fields
- Update extract() method signature

**Quick test**:
```bash
# Should NOT see "Invalid priority 'None'" errors anymore
pytest tests/integration/test_demo_scenarios.py -v -m "real_llm" --timeout=0 2>&1 | grep "Invalid priority 'None'"
# Expected: No matches (error eliminated)
```

**Step 4: Implement Fix C - Synonym Expansion** (60 min)

See URGENT_FIXES_MACHINE_SPEC.md for detailed code changes:
- Add OPERATION_SYNONYMS constant
- Update OPERATION_CLASSIFICATION_PROMPT template
- Modify classify() method to include synonyms

**Quick test**:
```bash
# Run just the first variation test (100 variations including synonyms)
pytest tests/integration/test_nl_variations.py::TestNLCreateVariations::test_create_epic_variations -v -m "real_llm" --timeout=0

# Should see improved pass rate (~90% vs ~82%)
```

**Step 5: Commit Changes** (5 min)
```bash
git add src/nl/nl_command_processor.py
git add src/nl/parameter_extractor.py
git add src/nl/operation_classifier.py

git commit -m "fix: Phase 3 urgent fixes (confidence, parameters, synonyms)

- Lower confidence threshold 0.8 → 0.7 (emergency fix for demos)
- Fix parameter extraction None values (eliminates 30% validation errors)
- Add synonym expansion for operations (improves robustness)

Impact: Demo pass rate 12.5% → 75%, Variation pass rate 82% → 90%
Related: Phase 3 testing, ENH-101, ENH-102, ENH-103"

git push origin fix/phase3-urgent-fixes
```

---

## Testing Strategy (Post-Implementation)

### Quick Validation (15 min)

**Test demo scenarios** (should raise from 12.5% → 75%):
```bash
pytest tests/integration/test_demo_scenarios.py -v -m "real_llm and demo_scenario" --timeout=0
```

**Expected**: 6-7 tests pass (vs 1 before)

### Full Validation (120 min)

**Re-run ALL tests** for clean baseline:
```bash
# Variation tests (~60 min)
pytest tests/integration/test_nl_variations.py -v -m "real_llm and stress_test" --timeout=0

# Demo tests (~3 min)
pytest tests/integration/test_demo_scenarios.py -v -m "real_llm and demo_scenario" --timeout=0

# Workflow tests (~20 min)
pytest tests/integration/test_obra_workflows.py -v -m "real_llm and workflow" --timeout=0
```

**Expected outcomes**:
- Variation: ~90% pass rate (vs 82%)
- Demo: ~75-87.5% pass rate (vs 12.5%)
- Workflow: ~67-80% pass rate (vs 0%)

---

## Success Criteria

### Minimum Requirements (Must Pass)

- [ ] Fix A: Confidence threshold changed to 0.7
- [ ] Fix B: Parameter extraction skips None for optional fields
- [ ] Fix C: Synonym mappings added to operation classifier
- [ ] Demo test pass rate > 50% (was 12.5%)
- [ ] No regressions (existing passing tests still pass)
- [ ] Changes committed to git

### Stretch Goals (Nice to Have)

- [ ] Demo test pass rate ≥ 75%
- [ ] Variation test pass rate ≥ 90%
- [ ] All tests re-run for clean baseline
- [ ] Comparison report generated (before/after metrics)

---

## Known Issues & Workarounds

### Issue 1: LLM Call Latency

**Problem**: Real LLM tests are 2-4x slower than expected
- Expected: 60 minutes for 950 variations
- Actual: 95-105 minutes

**Workaround**: Add 50-75% time buffer for any LLM-dependent tests

### Issue 2: JSON Parsing Errors

**Problem**: Occasional "Invalid JSON" errors from LLM responses
**Frequency**: ~2% of calls
**Workaround**: Retry logic already in place (RetryManager)

### Issue 3: Test Timeout

**Problem**: Default pytest timeout is 30s, but tests take 60-120s
**Solution**: Always use `--timeout=0` for real LLM tests

---

## Rollback Plan

If fixes cause regressions:

```bash
# View what changed
git diff HEAD~1

# Rollback commit
git reset --hard HEAD~1

# Or rollback specific file
git checkout HEAD~1 src/nl/nl_command_processor.py

# Identify issue and fix incrementally
```

**Incremental approach**:
1. Apply Fix A only → test
2. Apply Fix B only → test
3. Apply Fix C only → test
4. Combine all three → test

---

## Communication Plan

**When to notify stakeholders**:

1. **After Fix A** (confidence threshold):
   - Quick win, should improve demo tests immediately
   - Message: "Emergency fix applied, demo pass rate improving"

2. **After all fixes + quick validation**:
   - Message: "Urgent fixes complete, demo pass rate 12.5% → 75%, ready for re-testing"

3. **After full validation**:
   - Message: "Clean baseline established, ready for next demo"

---

## Reference Files

**Implementation details**:
- `docs/development/URGENT_FIXES_MACHINE_SPEC.md` - Exact code changes

**Context and rationale**:
- `docs/development/URGENT_FIXES_IMPLEMENTATION_PLAN.md` - Full background

**Test results**:
- `tests/demo_scenarios_run2.log` - Demo test failures (7/8 failed)
- `tests/obra_workflows_run2.log` - Workflow test failures (14/14 failed)
- `tests/phase3_stress_test_run_final.log` - Variation test results (partial)

**Enhancement recommendations**:
- `docs/design/PHASE3_ENHANCEMENT_RECOMMENDATIONS.md` - Long-term improvements

---

## Quick Reference: File Locations

```
src/nl/nl_command_processor.py       # Fix A: Line ~30
src/nl/parameter_extractor.py         # Fix B: Lines ~20, ~180-220, ~140-170
src/nl/operation_classifier.py        # Fix C: Lines ~20, ~60-100, ~140-180

tests/integration/test_demo_scenarios.py      # 8 demo workflow tests
tests/integration/test_obra_workflows.py      # 8 typical user journey tests
tests/integration/test_nl_variations.py       # 11 variation tests (950+ variations)
```

---

## Expected Timeline

| Phase | Duration | Activity |
|-------|----------|----------|
| Setup | 5 min | Branch creation, environment check |
| Fix A | 5 min | Confidence threshold change |
| Test A | 3 min | Quick demo test |
| Fix B | 30 min | Parameter null handling |
| Test B | 5 min | Verify no validation errors |
| Fix C | 60 min | Synonym expansion |
| Test C | 10 min | Variation test sample |
| Commit | 5 min | Git commit and push |
| **Subtotal** | **123 min** | **Implementation + quick validation** |
| Full test | 120 min | Re-run all tests (optional) |
| **TOTAL** | **243 min (4h)** | **Complete cycle** |

---

## Post-Implementation Checklist

After implementing all fixes:

- [ ] All code changes committed
- [ ] Quick validation tests pass (demo scenarios)
- [ ] No obvious regressions
- [ ] Branch pushed to origin
- [ ] Stakeholders notified of progress
- [ ] (Optional) Full test suite run
- [ ] (Optional) Before/after comparison report

---

## Emergency Contacts

**If you get stuck**:
1. Read URGENT_FIXES_IMPLEMENTATION_PLAN.md for full context
2. Read PHASE3_ENHANCEMENT_RECOMMENDATIONS.md for alternatives
3. Check test logs in tests/ directory for error patterns
4. Rollback and try incremental approach (one fix at a time)

**Priority order** (if time constrained):
1. Fix A (confidence) - Highest immediate impact
2. Fix B (parameters) - Fixes real bug
3. Fix C (synonyms) - Improves robustness

---

## Key Insight

**Your concern was 100% validated**: Demo tests revealed critical issues that variation tests alone would never catch.

**The multi-layer defense worked**:
- Variation tests: Found robustness issues (~82% pass)
- Demo tests: Found workflow failures (12.5% pass) 🚨
- This proves we need BOTH layers!

**Current state**: Code will fail live demos
**After fixes**: Code should handle 75-87.5% of demo scenarios
**Target state**: 100% demo pass rate (requires additional fixes later)

---

## Final Note

**DO NOT DEMO** until these fixes are deployed and validated. Current 12.5% pass rate means **87.5% chance of demo failure**.

After fixes, we'll have ~75% success rate - much better but still not 100%. Document remaining failures for Phase 3B fixes.

---

**Status**: Ready for implementation
**Owner**: Claude Code AI Agent
**Next Action**: Execute implementation per URGENT_FIXES_MACHINE_SPEC.md
**Priority**: 🔴 CRITICAL
