# Clarification Loop Fix Plan - CSV Regression Test Failure

**Issue ID**: BUG-PHASE4-006
**Date**: 2025-11-04
**Priority**: HIGH
**Impact**: Blocks task completion, causes max_turns exhaustion

---

## Executive Summary

The CSV regression test revealed a critical **clarification loop** issue where the orchestrator gets stuck requesting clarifications instead of proceeding to completion. The task exhausted 20 max_turns (10 initial + 10 retry) without completing, despite passing all validation and quality checks in every iteration.

**Root Cause**: Confidence thresholds are too conservative for simple tasks, causing medium-confidence responses (0.32-0.62) to trigger "clarify" instead of "proceed".

**Impact**: Simple tasks that should complete in ≤5 iterations fail after 20 turns, blocking production use.

---

## Problem Analysis

### Observed Behavior (CSV Test)

```
Iteration Pattern (Repeated 20 times):
  ✓ Prompt sent to Claude Code
  ✓ Response received
  ✓ Validation: PASSED
  ✓ Quality: 0.78 (PASS, above 0.7 threshold)
  ⚠️ Confidence: 0.32-0.62 (MEDIUM range)
  → Decision: CLARIFY (request more info)
  → Loop continues...
```

**Result**: Task never completed, exceeded max_turns limit (20/20).

### Root Cause: Decision Logic Thresholds

**Current Thresholds** (from `decision_engine.py:118-122`):
```python
HIGH_CONFIDENCE = 0.85    # Required for PROCEED
MEDIUM_CONFIDENCE = 0.50  # Triggers CLARIFY
LOW_CONFIDENCE = 0.30     
CRITICAL_THRESHOLD = 0.30 # Triggers ESCALATE
```

**Decision Logic** (from `decision_engine.py:241-289`):
```python
if confidence >= 0.85 AND validation_passed AND quality >= 0.7:
    → PROCEED  # Complete task
elif 0.50 <= confidence < 0.85:
    → CLARIFY  # Request more info (STUCK HERE!)
elif confidence < 0.50:
    → ESCALATE # Human intervention
```

**The Problem**:
- CSV test confidence scores: 0.32, 0.39, 0.62 (mostly in MEDIUM range)
- Medium range (0.50-0.85) is **TOO WIDE** (35 percentage points)
- Confidence of 0.62 should be "good enough" for simple tasks
- But current threshold requires 0.85 to proceed
- Results in endless clarification loop for simple, valid responses

### Why Confidence is Too Low

**Confidence Calculation** (from `decision_engine.py:454-459`):
```python
confidence = (
    35% * validation_confidence +  # 1.0 (passed)
    25% * quality_score +          # 0.78
    35% * completeness_score +     # 0.5-1.0
    5% * historical_score          # varies
)
```

**For CSV test**:
- Validation: 1.0 (passed)
- Quality: 0.78
- Completeness: likely 0.5-0.7 (ambiguous response format)
- Historical: ~0.7

**Calculated confidence**:
```
0.35 * 1.0 + 0.25 * 0.78 + 0.35 * 0.6 + 0.05 * 0.7
= 0.35 + 0.195 + 0.21 + 0.035
= 0.79  (below 0.85 threshold!)
```

Even with perfect validation and good quality, confidence only reaches ~0.79, which still triggers CLARIFY.

---

## Detailed Impact Analysis

### Performance Impact

**Expected vs Actual**:
| Metric | Expected (M8 Baseline) | Actual (CSV Test) | Delta |
|--------|------------------------|-------------------|-------|
| Completion | ✓ COMPLETED | ❌ FAILED (max_turns) | -100% |
| Iterations | ≤10 | 20 (exhausted) | +100% |
| Time | <300s | 546.5s | +82% |
| Result | Average age: 30.0 | No result | - |

### Affected Task Types

**High Risk** (likely to hit clarification loop):
- Simple code generation (CSV parsing, calculators)
- Data processing tasks
- Script creation
- File manipulation

**Medium Risk**:
- Medium complexity features
- Refactoring tasks
- Test creation

**Low Risk**:
- Complex multi-file features
- Architecture design
- Debugging (naturally iterative)

### Production Readiness

**Current Status**: ❌ **NOT PRODUCTION READY**

**Blockers**:
1. Simple tasks cannot complete
2. Max_turns exhaustion is common
3. Wastes API calls and time
4. Unpredictable behavior

---

## Proposed Solution

### Strategy: Multi-Pronged Approach

Fix the issue at **three levels**:

1. **Configuration Level**: Adjust thresholds in config
2. **Code Level**: Improve decision logic
3. **Documentation Level**: Add tuning guidelines

### Solution 1: Adjust Confidence Thresholds (IMMEDIATE)

**Change in `config/config.yaml`**:

```yaml
decision_engine:
  # Confidence thresholds (0.0-1.0)
  high_confidence: 0.70     # Lower from 0.85 (more lenient)
  medium_confidence: 0.40   # Lower from 0.50 (narrow CLARIFY range)
  critical_threshold: 0.25  # Lower from 0.30 (more margin)
  
  # Decision weights (must sum to 1.0)
  weight_confidence: 0.30   # Lower from 0.35 (less weight)
  weight_validation: 0.30   # Increase from 0.25 (more weight)
  weight_quality: 0.30      # Increase from 0.25 (more weight)
  weight_complexity: 0.05   # Lower from 0.10
  weight_history: 0.05      # Keep at 0.05
```

**Rationale**:
- **high_confidence: 0.70**: Allows valid, quality responses to proceed
- **medium_confidence: 0.40**: Narrows CLARIFY range (0.40-0.70 vs 0.50-0.85)
- **critical_threshold: 0.25**: More margin before escalation
- **Rebalanced weights**: Prioritize validation/quality over confidence score

**Expected Impact**:
- CSV test confidence ~0.79 now triggers PROCEED (above 0.70)
- CLARIFY range narrowed to 30 points (was 35)
- More deterministic behavior

### Solution 2: Improve Decision Logic (SHORT-TERM)

**Add "proceed on quality" path** in `decision_engine.py`:

```python
# BEFORE confidence check, add quality-based path:
if validation_passed and quality_score >= 0.75 and overall_confidence >= 0.60:
    # Quality + validation override low-medium confidence
    action = Action(
        type=self.ACTION_PROCEED,
        confidence=max(overall_confidence, quality_score),
        explanation=(
            f"High quality ({quality_score:.2f}) and validation passed, "
            f"proceeding despite medium confidence ({overall_confidence:.2f})"
        ),
        ...
    )
```

**Rationale**:
- If response passes validation AND quality is high, trust it
- Confidence score is just heuristic, not ground truth
- Quality + validation are more reliable signals

### Solution 3: Add Iteration-Based Escape Hatch (SHORT-TERM)

**Prevent infinite loops** by adding iteration awareness:

```python
# In decide_next_action(), check iteration count
iteration = context.get('iteration', 1)
max_iterations = context.get('max_iterations', 10)

if iteration >= max_iterations - 2:  # Last 2 iterations
    if validation_passed and quality_score >= 0.65:
        # Force proceed to avoid max_turns exhaustion
        action = Action(
            type=self.ACTION_PROCEED,
            confidence=max(overall_confidence, 0.70),
            explanation=(
                f"Forcing proceed at iteration {iteration}/{max_iterations} "
                f"with acceptable quality ({quality_score:.2f})"
            ),
            ...
        )
```

**Rationale**:
- Prevents max_turns exhaustion
- Still requires validation + decent quality
- Safety valve for edge cases

### Solution 4: Task-Type Specific Thresholds (MEDIUM-TERM)

**Add task-type awareness**:

```yaml
decision_engine:
  thresholds_by_task_type:
    code_generation:
      high_confidence: 0.65    # More lenient for simple code
      medium_confidence: 0.35
    
    debugging:
      high_confidence: 0.75    # More iterations expected
      medium_confidence: 0.45
    
    refactoring:
      high_confidence: 0.70
      medium_confidence: 0.40
    
    planning:
      high_confidence: 0.60    # Quick planning tasks
      medium_confidence: 0.30
```

**Rationale**:
- Different task types have different confidence patterns
- Code generation can be validated objectively (syntax, tests)
- Planning/documentation is more subjective

---

## Implementation Plan

### Phase 1: Immediate Fix (30 minutes)

**Goal**: Unblock CSV test

**Steps**:
1. Update `config/config.yaml` with new thresholds
2. Test configuration loads correctly
3. Re-run CSV regression test
4. Verify task completes in ≤10 iterations

**Success Criteria**:
- ✅ CSV test PASSES
- ✅ Task completes successfully
- ✅ Iterations ≤10
- ✅ Time <300s

### Phase 2: Code Improvements (1-2 hours)

**Goal**: Make decision logic more robust

**Steps**:
1. Implement quality-based proceed path
2. Implement iteration-based escape hatch
3. Add comprehensive logging for decision rationale
4. Update unit tests for new thresholds
5. Run full test suite

**Success Criteria**:
- ✅ All tests pass
- ✅ Decision logic handles edge cases
- ✅ Clear logging of decision reasoning

### Phase 3: Task-Type Awareness (2-3 hours)

**Goal**: Optimize thresholds per task type

**Steps**:
1. Add task-type config section
2. Update DecisionEngine to load task-type thresholds
3. Implement threshold selection based on task.task_type
4. Add tests for task-type routing
5. Document task-type tuning

**Success Criteria**:
- ✅ Task-type thresholds working
- ✅ Backwards compatible (defaults used if not configured)
- ✅ Documented tuning guidelines

### Phase 4: Validation & Tuning (2-3 hours)

**Goal**: Validate across multiple scenarios

**Steps**:
1. Re-run CSV regression test (PASS expected)
2. Run calculator test (Task 4.2)
3. Run stress test (10 tasks, Task 4.1)
4. Analyze decision patterns
5. Fine-tune thresholds based on results

**Success Criteria**:
- ✅ CSV test: PASS
- ✅ Calculator test: PASS
- ✅ Stress test: ≥80% completion rate
- ✅ Average iterations: ≤6 per task

---

## Risk Assessment

### Risks of Fix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Too lenient thresholds | Medium | Medium | Add quality-based gates |
| Tasks proceed too early | Low | Low | Keep validation + quality checks |
| Break existing behavior | Low | Medium | Comprehensive testing before deploy |
| Introduce new edge cases | Medium | Low | Iteration escape hatch prevents loops |

### Risks of NOT Fixing

| Risk | Probability | Impact | Severity |
|------|-------------|--------|----------|
| Production failures | **HIGH** | **CRITICAL** | **BLOCKER** |
| User frustration | **HIGH** | **HIGH** | **MAJOR** |
| Wasted API calls | **HIGH** | **MEDIUM** | **MODERATE** |
| Reputation damage | Medium | HIGH | MAJOR |

**Conclusion**: Risks of NOT fixing far outweigh risks of fixing.

---

## Configuration Changes Summary

### Before (Current - Too Conservative)

```yaml
decision_engine:
  high_confidence: 0.85      # Too high
  medium_confidence: 0.50    # CLARIFY range too wide
  critical_threshold: 0.30
  
  weight_confidence: 0.35    # Too much weight
  weight_validation: 0.25
  weight_quality: 0.25
  weight_complexity: 0.10
  weight_history: 0.05
```

**Result**: Simple tasks stuck in clarification loop

### After (Proposed - Balanced)

```yaml
decision_engine:
  high_confidence: 0.70      # More lenient
  medium_confidence: 0.40    # Narrower CLARIFY range
  critical_threshold: 0.25   # More margin
  
  weight_confidence: 0.30    # Less weight on heuristic
  weight_validation: 0.30    # More weight on objective check
  weight_quality: 0.30       # More weight on LLM validation
  weight_complexity: 0.05    # Minimal weight
  weight_history: 0.05       # Minimal weight
```

**Result**: Simple tasks proceed when validation + quality pass

---

## Expected Outcomes

### CSV Regression Test (Post-Fix)

**Predicted Execution**:
```
Iteration 1:
  - Prompt: "Read CSV, calculate average age"
  - Response: Python script with CSV parsing
  - Validation: ✓ PASSED
  - Quality: 0.78 (PASS)
  - Confidence: ~0.79 (calculated)
  → Decision: PROCEED (above 0.70 threshold!)
  → Status: COMPLETED

Result: Average age = 30.0
Iterations: 1-3 (vs 20 current)
Time: <60s (vs 546.5s current)
Status: PASS ✅
```

### Performance Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Completion Rate | 0% | ≥95% | +95% |
| Avg Iterations | N/A (fails) | 3-6 | -70% |
| Avg Time | N/A (fails) | <120s | -75% |
| Max Turns Exhausted | 100% | <5% | -95% |

### Behavioral Changes

**Tasks that will proceed faster**:
- Simple code generation (CSV, calculators, scripts)
- Data processing (file I/O, transformations)
- Test creation (unit tests, fixtures)
- Documentation (docstrings, README)

**Tasks unchanged** (still need iteration):
- Complex features (multi-file, architecture)
- Debugging (requires investigation)
- Ambiguous requirements (legitimately needs clarification)

---

## Testing Strategy

### Unit Tests

**New tests needed**:
1. `test_decision_thresholds_lowered()`
   - Verify 0.70 triggers PROCEED
   - Verify 0.60 triggers CLARIFY
   - Verify 0.30 triggers ESCALATE

2. `test_quality_override_path()`
   - Verify high quality + validation overrides medium confidence
   - Verify threshold: quality >= 0.75, confidence >= 0.60

3. `test_iteration_escape_hatch()`
   - Verify forced proceed at iteration N-2
   - Verify still requires validation + quality

4. `test_task_type_thresholds()`
   - Verify code_generation uses lower thresholds
   - Verify debugging uses higher thresholds
   - Verify default fallback

### Integration Tests

**Test scenarios**:
1. CSV regression test (PASS expected)
2. Calculator module test (PASS expected)
3. 10-task stress test (≥8 should complete)
4. Complex feature test (allowed to iterate)

### Regression Tests

**Verify no regressions**:
1. Existing unit tests still pass
2. Complex tasks still get proper iteration
3. Critical threshold still triggers escalation
4. Historical learning still works

---

## Rollback Plan

**If fix causes issues**:

1. **Immediate Rollback** (5 minutes):
   ```bash
   git checkout config/config.yaml
   git checkout src/orchestration/decision_engine.py
   ```

2. **Revert to conservative thresholds**:
   ```yaml
   decision_engine:
     high_confidence: 0.85  # Original
     medium_confidence: 0.50  # Original
   ```

3. **Disable new features**:
   - Remove quality-based proceed path
   - Remove iteration escape hatch
   - Revert to original decision logic

4. **Validate rollback**:
   - Run test suite
   - Verify original behavior restored

---

## Success Metrics

### Immediate (Phase 1)

- ✅ CSV regression test: PASS
- ✅ Task completes in 1-5 iterations (vs 20 exhausted)
- ✅ No validation/quality compromises

### Short-Term (Phase 2-3)

- ✅ Calculator test: PASS
- ✅ Stress test: ≥80% completion rate
- ✅ Average iterations: ≤6 (vs current failure)
- ✅ All unit tests: PASS

### Long-Term (Phase 4)

- ✅ Production deployment: Success
- ✅ User feedback: Positive
- ✅ Max_turns exhaustion rate: <5%
- ✅ Task completion rate: ≥90%

---

## Documentation Updates

**Files to update**:

1. **CLAUDE.md**:
   - Add warning about confidence thresholds
   - Document task-type specific tuning

2. **docs/architecture/decision_engine.md** (create if missing):
   - Explain decision logic in detail
   - Provide tuning guidelines
   - Include threshold recommendations

3. **config/config.example.yaml**:
   - Update with new threshold values
   - Add comments explaining each threshold
   - Include task-type examples

4. **docs/guides/TUNING_GUIDE.md** (create):
   - How to tune confidence thresholds
   - Common symptoms and fixes
   - Task-type optimization

---

## Future Enhancements

### Machine Learning-Based Thresholds

**Idea**: Learn optimal thresholds from historical data

**Approach**:
1. Log all decisions with outcomes (success/failure)
2. Analyze patterns: Which thresholds yield best results?
3. Use ML to predict optimal thresholds per task type
4. Auto-tune thresholds based on deployment environment

**Timeline**: Post-v1.2 (M10+)

### Adaptive Confidence Scoring

**Idea**: Confidence score learns from outcomes

**Approach**:
1. Track prediction accuracy: confidence vs actual success
2. Adjust confidence calculation weights dynamically
3. Personalize to specific codebase patterns
4. Improve over time with more data

**Timeline**: v1.3+

### User-Configurable Risk Tolerance

**Idea**: Let users choose conservative vs aggressive

**Approach**:
```yaml
decision_engine:
  risk_profile: balanced  # conservative | balanced | aggressive
  
  profiles:
    conservative:
      high_confidence: 0.85  # Original
    balanced:
      high_confidence: 0.70  # Proposed
    aggressive:
      high_confidence: 0.60  # Very lenient
```

**Timeline**: v1.3+

---

**Document Status**: ✅ COMPLETE
**Next Action**: Generate this documentation in /docs/development/, then implement Phase 1 fix
**Estimated Fix Time**: 30 minutes (Phase 1) + 3-4 hours (Phases 2-4)
**Priority**: HIGH (blocks production readiness)

---

**Generated**: 2025-11-04
**Author**: Obra Development Team
**Issue**: BUG-PHASE4-006 - Clarification Loop
