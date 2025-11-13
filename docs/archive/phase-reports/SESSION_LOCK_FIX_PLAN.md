# Session Lock Error Fix Plan

**Date**: 2025-11-04
**Issue**: BUG-PHASE4-006: Claude session lock errors on rapid iteration retries
**Priority**: MEDIUM (doesn't block core functionality, but impacts reliability)

---

## Problem Statement

### The Issue

When executing tasks with multiple iterations, the orchestrator attempts to reuse the same session_id across iterations. Claude Code CLI locks sessions and doesn't release them fast enough, causing "session already in use" errors on subsequent iterations.

### Error Pattern

```
Iteration 1: session_id=abc123 → ✓ Success
Iteration 2: session_id=abc123 → ❌ Session locked (retries 5x, ~16s total)
Iteration 3: session_id=abc123 → ❌ Session locked (retries 5x, ~16s total)
→ Task fails with "max_iterations" or "session still in use"
```

### Current Retry Logic

```python
# src/agents/claude_code_local.py:66-68
max_retries: 5
retry_initial_delay: 2.0s
retry_backoff: 1.5x

# Results in delays: 2s, 3s, 4.5s, 6.75s = ~16.25s total wait
```

---

## Root Cause Analysis

### Why This Happens

1. **Temp session created** for standalone task execution
2. **Session ID shared** across all iterations within the task
3. **Claude Code locks** session during execution
4. **Lock not released** fast enough for next iteration (< 1 second)
5. **Rapid iteration** timing doesn't allow for lock release

### Architecture Conflict

**Original Design Intent**:
- Session tracking for usage metrics (tokens, turns, cost)
- Session persistence for context continuity across iterations

**Current Reality**:
- Using fresh sessions per call (`use_session_persistence: false`)
- But temp session reused within task for tracking
- Claude Code session locks prevent rapid reuse

### Key Insight

**The conflict**: We want to track at the task level (single session_id for all iterations) but Claude Code enforces isolation at the call level (locks prevent rapid reuse).

---

## Investigation Results

### Test Case Analysis

**Test**: 2 tasks, Task 1 had 3 iterations with max_iterations=3

```
Task 1, Iteration 1:
- session_id=d18e5f9b
- Status: ✓ Success (file watcher error, but agent call worked)

Task 1, Iteration 2:
- session_id=d18e5f9b (SAME as iteration 1)
- Status: ❌ Session locked (5 retries exhausted, 16.2s wait)
- Error: "already in use"

Task 1, Iteration 3:
- session_id=d18e5f9b (SAME as iteration 1)
- Status: ❌ Session locked (5 retries exhausted, 16.2s wait)
- Error: "already in use"

Task 2, Iteration 1:
- session_id=<different> (new temp session for new task)
- Status: ✓ Success (completed)
```

### Conclusion

Session locks occur **within task iterations**, not **between tasks**. BUG-PHASE4-005 fix resolved between-task session issues. This is a separate issue.

---

## Solution Options

### Option A: Fresh Session Per Iteration (Recommended)

**Approach**: Generate new session_id for each iteration, aggregate metrics at task level

**Pros**:
- ✅ No session lock errors
- ✅ Simple implementation
- ✅ Works with Claude Code's locking behavior
- ✅ Still allows usage tracking (aggregate by task_id)

**Cons**:
- ❌ Loses session context continuity across iterations (but we're using `use_session_persistence: false` anyway)
- ❌ Need to aggregate session metrics at task level

**Implementation**:
```python
# In orchestrator._execute_single_task():
for iteration in range(max_iterations):
    # Generate fresh session_id per iteration
    iteration_session_id = str(uuid.uuid4())

    # Create session record for this iteration
    self.state_manager.create_session_record(
        session_id=iteration_session_id,
        project_id=task.project_id,
        task_id=task.id,  # Link to task for aggregation
        milestone_id=None
    )

    # Assign to agent
    self.agent.session_id = iteration_session_id

    # Execute iteration...

    # Complete session record
    self.state_manager.complete_session_record(
        session_id=iteration_session_id,
        ended_at=datetime.now(UTC)
    )
```

**Effort**: ~2 hours (implementation + testing)

---

### Option B: Increase Retry Delays (Band-Aid)

**Approach**: Increase max_retries and retry delays to wait longer for lock release

**Pros**:
- ✅ Minimal code changes
- ✅ Might work for some cases

**Cons**:
- ❌ Doesn't address root cause
- ❌ Wastes time waiting (could be 30-60s per retry)
- ❌ Still might fail if Claude doesn't release fast enough
- ❌ Inefficient

**Implementation**:
```python
# src/agents/claude_code_local.py
max_retries: 10 (instead of 5)
retry_initial_delay: 3.0s (instead of 2.0s)
retry_backoff: 2.0x (instead of 1.5x)

# Results in: 3s, 6s, 12s, 24s, 48s... = very long waits
```

**Effort**: 15 minutes
**Recommendation**: ❌ **NOT RECOMMENDED** (inefficient, doesn't solve problem)

---

### Option C: Add Inter-Iteration Delay (Band-Aid)

**Approach**: Add mandatory delay between iterations to allow lock release

**Pros**:
- ✅ Simple to implement
- ✅ Might reduce lock errors

**Cons**:
- ❌ Slows down ALL executions (even when not needed)
- ❌ Arbitrary delay (how long is enough?)
- ❌ Doesn't address root cause

**Implementation**:
```python
# In orchestrator._execute_single_task():
for iteration in range(max_iterations):
    if iteration > 0:
        time.sleep(5)  # Wait 5s between iterations
    # Execute iteration...
```

**Effort**: 10 minutes
**Recommendation**: ❌ **NOT RECOMMENDED** (inefficient, arbitrary)

---

### Option D: Detect Lock Release Before Next Iteration (Complex)

**Approach**: Poll Claude session status before starting next iteration

**Pros**:
- ✅ Reuses session when possible
- ✅ Waits only as long as necessary

**Cons**:
- ❌ No known API to check Claude session lock status
- ❌ Would need to parse `claude` command output or try-catch approach
- ❌ Complex implementation
- ❌ Unreliable

**Recommendation**: ❌ **NOT FEASIBLE** (no API for session lock status)

---

### Option E: Hybrid - Fresh Sessions for Iterations, Track at Task Level

**Approach**: Use fresh session per iteration but link to task_id for aggregation

This is essentially Option A with explicit task-level aggregation queries.

**Pros**:
- ✅ All benefits of Option A
- ✅ Explicit task-level metrics via SQL aggregation
- ✅ Clean separation: session = iteration, task = aggregation unit

**Cons**:
- ❌ Need to implement aggregation queries
- ❌ Slightly more complex than Option A

**Recommendation**: ✅ **BEST SOLUTION** if we need task-level metrics

---

## Recommended Solution: Option E (Hybrid)

### Implementation Plan

#### Phase 1: Modify Session Creation (1 hour)

**File**: `src/orchestrator.py` (in `_execute_single_task()`)

**Changes**:
1. Move temp session creation **inside iteration loop**
2. Generate fresh UUID per iteration
3. Link session to task_id for aggregation
4. Complete session after each iteration

**Pseudocode**:
```python
def _execute_single_task(task, max_iterations, context):
    for iteration in range(1, max_iterations + 1):
        # Generate fresh session for this iteration
        iteration_session_id = str(uuid.uuid4())

        # Create session record (linked to task)
        self.state_manager.create_session_record(
            session_id=iteration_session_id,
            project_id=task.project_id,
            task_id=task.id,  # KEY: Link to task for aggregation
            milestone_id=None,
            metadata={'iteration': iteration}
        )

        # Assign to agent for this iteration
        old_session = self.agent.session_id
        self.agent.session_id = iteration_session_id

        try:
            # Execute iteration with fresh session
            response = self.agent.send_prompt(prompt, context)
            # ... validation, decision logic ...

            # Complete session record
            self.state_manager.complete_session_record(
                session_id=iteration_session_id,
                ended_at=datetime.now(UTC)
            )

            if decision == 'proceed':
                break  # Task complete

        finally:
            # Restore agent session (probably None)
            self.agent.session_id = old_session
```

---

#### Phase 2: Add Task-Level Aggregation Queries (30 minutes)

**File**: `src/core/state.py`

**New Method**:
```python
def get_task_session_metrics(self, task_id: int) -> Dict[str, Any]:
    """Aggregate session metrics across all iterations of a task.

    Args:
        task_id: Task ID to aggregate metrics for

    Returns:
        Dict with aggregated metrics:
        - total_tokens: Sum of all session tokens
        - total_turns: Sum of all turns
        - total_cost: Sum of all costs
        - num_iterations: Number of sessions (iterations)
        - avg_tokens_per_iteration: Average tokens per iteration
    """
    with self.transaction():
        sessions = self.db_session.query(SessionRecord).filter(
            SessionRecord.task_id == task_id
        ).all()

        return {
            'total_tokens': sum(s.total_tokens or 0 for s in sessions),
            'total_turns': sum(s.total_turns or 0 for s in sessions),
            'total_cost': sum(s.total_cost_usd or 0 for s in sessions),
            'num_iterations': len(sessions),
            'avg_tokens_per_iteration': (
                sum(s.total_tokens or 0 for s in sessions) / len(sessions)
                if sessions else 0
            ),
            'sessions': [s.to_dict() for s in sessions]
        }
```

---

#### Phase 3: Update SessionRecord Schema (Optional - 15 minutes)

**Current**: SessionRecord already has `task_id` field (nullable)

**Verify**: Check if `task_id` is indexed for efficient aggregation queries

**File**: `alembic/versions/add_session_task_id_index.py` (if needed)

---

#### Phase 4: Testing (1 hour)

**Test Cases**:

1. **Single task, multiple iterations** (3 iterations)
   - Verify: 3 different session_ids
   - Verify: All sessions linked to same task_id
   - Verify: No session lock errors
   - Verify: Aggregation query returns correct totals

2. **Multiple tasks, sequential** (2 tasks, 2 iterations each)
   - Verify: 4 total sessions (2 per task)
   - Verify: No session reuse between tasks
   - Verify: No lock errors

3. **Stress test** (10 tasks, variable iterations)
   - Verify: All tasks complete successfully
   - Verify: No lock errors
   - Verify: Session metrics accurate

---

## Validation Criteria

### Success Metrics

- [ ] No "session already in use" errors
- [ ] All iterations complete without lock errors
- [ ] Session metrics correctly aggregated at task level
- [ ] Stress test (10 tasks) completes successfully
- [ ] Task-level metrics match sum of iteration metrics

### Performance Targets

- Iteration startup time: < 2s (no artificial delays)
- Session creation overhead: < 100ms
- Aggregation query time: < 50ms

---

## Risk Assessment

### Risks

1. **Database overhead**: More session records (one per iteration vs one per task)
   - **Mitigation**: Minimal (sessions are small, indexed by task_id)
   - **Impact**: LOW

2. **Metric accuracy**: Aggregation could have bugs
   - **Mitigation**: Comprehensive testing, validation queries
   - **Impact**: MEDIUM

3. **Breaking change**: Existing code expects one session per task
   - **Mitigation**: Backward compatible (task-level aggregation maintains same interface)
   - **Impact**: LOW

### Rollback Plan

If the fix causes issues:
1. Revert changes to `_execute_single_task()`
2. Restore temp session creation at task level (current BUG-PHASE4-005 fix)
3. Accept session lock errors as known limitation
4. Document workaround: Reduce iteration count or add manual delays

---

## Alternative: Quick Fix (If Time-Constrained)

If full implementation takes too long, **temporary workaround**:

### Quick Fix: Accept Lock Errors, Improve Messaging

**Changes**:
1. Catch session lock errors gracefully
2. Log warning instead of failing task
3. Continue with next iteration using fresh session

**Code**:
```python
# In orchestrator._execute_single_task():
try:
    response = self.agent.send_prompt(prompt, context)
except AgentException as e:
    if 'session still in use' in str(e).lower():
        logger.warning(f"Session lock detected, regenerating session for next iteration")
        # Generate fresh session for next iteration
        self.agent.session_id = str(uuid.uuid4())
        # Retry this iteration
        continue
    else:
        raise
```

**Pros**:
- ✅ 30 minutes to implement
- ✅ Allows tasks to complete despite lock errors

**Cons**:
- ❌ Band-aid solution
- ❌ Still wastes time on retries
- ❌ Doesn't prevent the problem

**Recommendation**: Use only if Option E cannot be implemented in this session

---

## Estimated Effort

| Phase | Time | Complexity |
|-------|------|------------|
| Phase 1: Modify session creation | 1 hour | Medium |
| Phase 2: Aggregation queries | 30 min | Low |
| Phase 3: Schema verification | 15 min | Low |
| Phase 4: Testing | 1 hour | Medium |
| **Total** | **2h 45min** | **Medium** |

**Quick Fix Alternative**: 30 minutes (Low complexity)

---

## Decision Matrix

| Criteria | Option A | Option B | Option C | Option D | **Option E** |
|----------|----------|----------|----------|----------|------------|
| Solves root cause | ✅ | ❌ | ❌ | ❓ | ✅ |
| No performance impact | ✅ | ❌ | ❌ | ❌ | ✅ |
| Maintains tracking | ⚠️ | ✅ | ✅ | ✅ | ✅ |
| Implementation time | 2h | 15m | 10m | Unknown | 2.5h |
| Reliability | ✅ | ⚠️ | ⚠️ | ❓ | ✅ |
| **Recommendation** | Good | Bad | Bad | Infeasible | **BEST** |

---

## Recommendation

**Implement Option E (Hybrid)** - Fresh sessions per iteration with task-level aggregation

**Reasoning**:
1. Completely eliminates session lock errors
2. Maintains all tracking capabilities via aggregation
3. Clean architecture (iteration = session, task = aggregation unit)
4. Reasonable implementation time (~3 hours)
5. No performance penalties

**Alternative**: If time-constrained, implement Quick Fix and schedule Option E for later

---

## Next Steps (After Plan Approval)

1. **Get approval** on Option E approach
2. **Phase 1**: Modify `_execute_single_task()` to use fresh session per iteration
3. **Phase 2**: Add `get_task_session_metrics()` aggregation method
4. **Phase 3**: Verify schema has task_id indexed
5. **Phase 4**: Test with 3-iteration task, 2-task sequence, stress test
6. **Validate**: No lock errors, correct metrics
7. **Document**: Update architecture docs and ADR

---

**Plan Status**: ✅ **COMPLETE - AWAITING APPROVAL TO IMPLEMENT**
**Recommended**: Option E (Fresh sessions per iteration + task-level aggregation)
**Estimated Time**: 2-3 hours
**Complexity**: Medium
**Risk**: Low
