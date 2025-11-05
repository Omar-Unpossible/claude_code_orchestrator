# ADR-007: Headless Mode Enhancements for Production Session Management

**Status:** Accepted

**Date:** 2025-11-04

**Deciders:** Obra Development Team

**Context Owner:** Omar (@Omar-Unpossible)

---

## Context

Obra's initial headless mode implementation (Phase 1-3) provided basic Claude Code execution via `subprocess.run()` with the `--print` flag. However, production usage revealed several gaps:

1. **No context window management** - Tasks would fail when context window filled up
2. **Fixed max_turns** - All tasks used same iteration limit regardless of complexity
3. **Short timeouts** - Complex tasks terminated prematurely (2-minute default)
4. **Manual session tracking** - No automatic session lifecycle management
5. **No continuity across milestones** - Lost context between related tasks

These limitations prevented Obra from handling:
- Long-running development workflows (multi-hour tasks)
- Complex refactoring requiring 15-20 iterations
- Multi-task milestones with shared context
- Production deployments with extended timelines

**Requirements:**
- ✓ Prevent context window overflows
- ✓ Intelligently determine max_turns per task
- ✓ Support extended timeouts (hours, not minutes)
- ✓ Maintain continuity across milestone tasks
- ✓ Graceful recovery from errors (auto-retry)
- ✓ Comprehensive logging for debugging

---

## Decision

We have implemented **five major enhancements** to headless mode:

### 1. Fresh Sessions with Obra Context Continuity

**Decision:** Each Claude Code call uses a fresh subprocess, but Obra maintains continuity through session IDs and summaries.

**Rationale:**
- PTY (persistent terminal) attempted but abandoned due to Claude Code bugs
- Fresh sessions are more reliable (no state corruption)
- `--session-id` flag provides context persistence in Claude's backend
- Obra tracks history and injects summaries into prompts

**Implementation:**
```python
# Each call is fresh subprocess
result = subprocess.run([
    'claude',
    '--print',
    '--session-id', session_id,  # ← Same ID across calls
    prompt
], timeout=7200)

# Obra provides continuity
if milestone_first_task:
    prompt = f"[MILESTONE CONTEXT]\n{workplan}\n\n{prompt}"
if session_refreshed:
    prompt = f"[PREVIOUS SESSION SUMMARY]\n{summary}\n\n{prompt}"
```

**Trade-offs:**
- ✅ **Pro:** Extremely reliable (no process bugs)
- ✅ **Pro:** Simple architecture (no PTY complexity)
- ✅ **Pro:** Stateless (no cleanup needed)
- ⚠️ **Con:** Slight startup overhead (~100-200ms per call)
- ⚠️ **Con:** Relies on Obra for continuity (not Claude's state)

### 2. Manual Token Tracking (Path B)

**Decision:** Implement manual token tracking since Claude Code doesn't provide context window percentage.

**Rationale:**
- **Path A** (ideal): Get percentage from Claude API → ❌ Not available
- **Path B** (implemented): Track tokens manually → ✅ Feasible

**Implementation:**
```python
# After each response, extract token breakdown
metadata = agent.get_last_metadata()
tokens_dict = {
    'input_tokens': metadata['input_tokens'],
    'cache_creation_tokens': metadata['cache_creation_tokens'],
    'cache_read_tokens': metadata['cache_read_tokens'],
    'output_tokens': metadata['output_tokens'],
    'total_tokens': sum(above)
}

# Add to cumulative session total
state_manager.add_session_tokens(session_id, task_id, tokens_dict)

# Check against limit
current_usage = state_manager.get_session_token_usage(session_id)
percentage = current_usage / context_window_limit  # e.g., 0.82 (82%)

# Take action at thresholds
if percentage >= 0.80:  # Refresh threshold
    new_session_id, summary = _refresh_session_with_summary()
```

**Thresholds chosen:**
- **70% (Warning):** Log warning, continue normally
- **80% (Refresh):** Auto-refresh session with summary
- **95% (Critical):** Emergency refresh

**Trade-offs:**
- ✅ **Pro:** Works with current Claude Code capabilities
- ✅ **Pro:** Conservative thresholds provide safety margin
- ✅ **Pro:** Comprehensive tracking (input + cache + output)
- ⚠️ **Con:** Manual tracking adds complexity
- ⚠️ **Con:** May drift ±5-10% from actual usage (system messages not tracked)
- ⚠️ **Con:** Requires database storage (ContextWindowUsage table)

### 3. Adaptive Max Turns Calculation

**Decision:** Calculate `max_turns` based on task complexity analysis rather than using a fixed value.

**Rationale:**
- Simple tasks (typo fixes) don't need 20 turns
- Complex tasks (large refactors) need more than 10 turns
- Claude Code max-turns guide provides clear guidelines
- Adaptive limits optimize resource usage

**Implementation:**
```python
class MaxTurnsCalculator:
    TASK_TYPE_DEFAULTS = {
        'validation': 5,
        'code_generation': 12,
        'refactoring': 15,
        'debugging': 20,
        'documentation': 3,
    }

    def calculate(self, task: Dict) -> int:
        # Priority 1: Task type override
        if task_type in TASK_TYPE_DEFAULTS:
            return TASK_TYPE_DEFAULTS[task_type]

        # Priority 2: Complexity analysis
        complexity = count_complexity_words(task)
        scope = count_scope_indicators(task)
        files = task.get('estimated_files', 1)
        loc = task.get('estimated_loc', 0)

        # Decision rules
        if loc > 500 or scope >= 2:
            return 20  # Very complex
        elif complexity == 0 and scope == 0 and files <= 1:
            return 3   # Simple
        elif complexity <= 1 and scope == 0 and files <= 3:
            return 6   # Medium
        else:
            return 12  # Complex

        # Enforce bounds: 3 <= turns <= 30
```

**Auto-retry on error_max_turns:**
```python
# If task exceeds max_turns, retry with higher limit
retry_count = 0
max_retries = 1

while retry_count <= max_retries:
    try:
        result = _execute_single_task(max_turns=max_turns)
        break  # Success
    except AgentException as e:
        if e.subtype == 'error_max_turns' and retry_count < max_retries:
            max_turns *= 2  # Double the limit
            retry_count += 1
            continue  # Retry
        raise  # Fail
```

**Trade-offs:**
- ✅ **Pro:** Optimizes resource usage (fewer wasted turns)
- ✅ **Pro:** Better success rate (complex tasks get adequate turns)
- ✅ **Pro:** Auto-retry recovers from underestimation
- ✅ **Pro:** Configurable per task type
- ⚠️ **Con:** Complexity analysis is heuristic (not perfect)
- ⚠️ **Con:** Retry mechanism may burn tokens (limited to 1 retry)

### 4. Extended Timeout (7200s Default)

**Decision:** Increase default timeout from 120s (2 minutes) to 7200s (2 hours).

**Rationale:**
- Complex tasks may need 20+ turns at 3-5 minutes per turn
- 20 turns × 5 min = 100 minutes (~2 hours)
- Previous 2-minute timeout caused premature terminations
- Timeout is wall-clock limit, max_turns is iteration limit

**Configuration:**
```yaml
agent:
  local:
    response_timeout: 7200  # 2 hours (default)
```

**Alternatives considered:**
- 1 hour (3600s): Too short for very complex tasks
- 4 hours (14400s): Too long, risk of runaway processes
- **2 hours (7200s): Balanced** ✓

**Trade-offs:**
- ✅ **Pro:** Supports complex workflows without interruption
- ✅ **Pro:** Prevents premature termination of valid work
- ✅ **Pro:** Configurable per deployment
- ⚠️ **Con:** Runaway tasks may consume resources longer
- ⚠️ **Con:** Requires monitoring for stuck processes
- ✅ **Mitigation:** max_turns provides iteration limit (separate from timeout)

### 5. Milestone-Based Sessions

**Decision:** Tie session lifecycle to milestone boundaries rather than individual tasks.

**Rationale:**
- Related tasks benefit from shared context
- Summaries preserve continuity across milestones
- Workplan context injected on first task
- Previous milestone summary included for continuity

**Lifecycle:**
```
START MILESTONE
    ↓
Generate session_id (UUID)
Create database record
Build context:
    - Project info
    - Workplan
    - Previous milestone summary (if available)
    ↓
EXECUTE TASKS (Task 1, 2, 3, ...)
    ↓
    Each task uses same session_id
    Context preserved across tasks
    Auto-refresh at 80% context window
    ↓
END MILESTONE
    ↓
Generate summary (via Qwen)
Save summary to database
Mark session complete
    ↓
NEXT MILESTONE
    ↓
Include previous summary in context
```

**Trade-offs:**
- ✅ **Pro:** Maintains continuity across related tasks
- ✅ **Pro:** Reduces redundant context in prompts
- ✅ **Pro:** Summaries provide compact historical context
- ✅ **Pro:** Qwen-generated summaries (fast, local)
- ⚠️ **Con:** Session refresh interrupts briefly (~5-10s)
- ⚠️ **Con:** Summary quality depends on Qwen

---

## Alternatives Considered

### Alternative 1: PTY for Persistent Sessions

**Option:** Use pseudo-terminal (PTY) to maintain persistent Claude Code process.

```python
# ATTEMPTED (but failed)
import pty
master, slave = pty.openpty()
subprocess.Popen(['claude'], stdin=slave, stdout=slave, stderr=slave)
```

**Rejected because:**
- ❌ Claude Code has known bugs with PTY
- ❌ Output parsing unreliable (ANSI codes, progress bars)
- ❌ Session state corruption on certain prompts
- ❌ No bugfix timeline from Claude team

**Outcome:** Fresh sessions with `--print` flag more reliable.

---

### Alternative 2: Session Persistence Across All Tasks

**Option:** Maintain single session ID across entire project (not just milestone).

**Rejected because:**
- ❌ Context window fills up too quickly
- ❌ Unrelated tasks don't benefit from shared context
- ❌ Session state becomes bloated over time
- ❌ Harder to recover from errors

**Outcome:** Milestone boundaries provide natural session lifecycle.

---

### Alternative 3: Path A (Claude-Provided Context Window %)

**Option:** Get context window percentage directly from Claude Code API.

```python
# IDEAL (but not available)
metadata = agent.get_last_metadata()
context_percentage = metadata['context_window_usage']  # e.g., 0.82
```

**Rejected because:**
- ❌ Claude Code doesn't expose this in JSON responses
- ❌ Would require API changes from Anthropic
- ❌ No timeline for implementation

**Outcome:** Implement Path B (manual tracking) as pragmatic solution.

---

### Alternative 4: Fixed Max Turns for All Tasks

**Option:** Use single max_turns value (e.g., 15) for all tasks.

**Rejected because:**
- ❌ Wastes resources on simple tasks (overkill)
- ❌ Insufficient for very complex tasks
- ❌ Ignores task complexity information
- ❌ No adaptation to actual needs

**Outcome:** Adaptive calculation provides better resource utilization.

---

## Consequences

### Positive Consequences

1. **Prevents Context Window Overflows**
   - ✅ Automatic detection at 70%, 80%, 95% thresholds
   - ✅ Session refresh with summary preserves continuity
   - ✅ Conservative thresholds provide safety margin

2. **Intelligent Max Turns Reduces Failed Tasks**
   - ✅ Simple tasks complete faster (3 turns vs 10)
   - ✅ Complex tasks get adequate iterations (20 turns)
   - ✅ Auto-retry recovers from underestimation
   - ✅ Task type overrides for known patterns

3. **Extended Timeout Supports Complex Work**
   - ✅ 2-hour timeout accommodates 20+ turn workflows
   - ✅ Prevents premature termination of valid work
   - ✅ Configurable per deployment needs

4. **Milestone Sessions Provide Continuity**
   - ✅ Related tasks benefit from shared context
   - ✅ Summaries preserve key decisions
   - ✅ Reduced redundancy in prompts
   - ✅ Previous milestone context included

5. **Comprehensive Logging**
   - ✅ 43+ log points across pipeline
   - ✅ Clear visibility into decisions
   - ✅ Easy debugging and troubleshooting
   - ✅ Structured log format (searchable)

### Negative Consequences

1. **Manual Token Tracking Adds Complexity**
   - ⚠️ Additional database table (ContextWindowUsage)
   - ⚠️ Cumulative tracking logic in orchestrator
   - ⚠️ May drift ±5-10% from actual usage
   - ✅ **Mitigation:** Conservative thresholds, frequent validation

2. **Token Tracking May Drift from Actual Usage**
   - ⚠️ System messages add ~200-500 tokens/turn (not tracked)
   - ⚠️ Cache efficiency varies (affects effective tokens)
   - ⚠️ Estimate may be off by 5-10%
   - ✅ **Mitigation:** 70%/80%/95% thresholds provide margin

3. **Session Refresh Interrupts Work**
   - ⚠️ Brief pause (~5-10s) for summary generation
   - ⚠️ User may notice slight delay
   - ✅ **Mitigation:** Only at 80% threshold (infrequent)
   - ✅ **Benefit:** Prevents catastrophic overflow

4. **Retry Mechanism May Burn Tokens**
   - ⚠️ Failed attempt uses tokens before retry
   - ⚠️ Retry doubles max_turns (more resources)
   - ✅ **Mitigation:** Limited to 1 retry (2 attempts total)
   - ✅ **Benefit:** Higher success rate worth the cost

5. **Complexity Analysis is Heuristic**
   - ⚠️ Keyword matching may misclassify tasks
   - ⚠️ No ML-based classification
   - ⚠️ May under/overestimate occasionally
   - ✅ **Mitigation:** Auto-retry recovers from underestimation
   - ✅ **Mitigation:** Task type overrides for known patterns

### Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Token tracking drift | Medium | Medium | Conservative thresholds (70%/80%/95%) |
| Context window overflow | Low | High | Automatic refresh at 80%, critical at 95% |
| Max turns underestimation | Medium | Medium | Auto-retry with 2x multiplier |
| Session refresh delay | Low | Low | Only at 80% threshold (infrequent) |
| Runaway timeout | Low | Medium | max_turns provides iteration limit |

---

## Implementation Details

### Phase 4: Max Turns (Week of Nov 2, 2025)

**Files Modified:**
- `src/orchestration/max_turns_calculator.py` (new, 260 lines)
- `src/orchestrator.py` (added retry logic, +150 lines)
- `src/agents/claude_code_local.py` (added max_turns handling, +50 lines)
- `config/config.yaml` (added max_turns section)
- `config/config.example.yaml` (added max_turns documentation)

**Tests Added:**
- `tests/test_max_turns_calculator.py` (31 tests, 100% coverage)
- Integration tests for retry logic (4 tests)

**Key Commits:**
- `feat: Implement adaptive max_turns calculation`
- `feat: Add auto-retry on error_max_turns`
- `test: Add comprehensive max_turns tests`

### Phase 5: Extended Timeout & Polish (Week of Nov 4, 2025)

**Files Modified:**
- `src/core/config.py` (added validation, +180 lines)
- `src/orchestrator.py` (added logging, +100 lines)
- `src/agents/claude_code_local.py` (extended timeout, +20 lines)
- `config/config.example.yaml` (documented timeout)

**Tests Added:**
- `tests/test_config_validation_comprehensive.py` (28 tests)
- Timeout validation tests (8 tests)

**Key Commits:**
- `feat: Extend default timeout to 7200s (2 hours)`
- `feat: Add comprehensive configuration validation`
- `feat: Add 43+ log points across orchestration`
- `docs: Create comprehensive Phase 5 documentation`

### Context Window Management (Path B)

**Files Modified:**
- `src/core/models.py` (added ContextWindowUsage model, +30 lines)
- `src/core/state.py` (added token tracking methods, +80 lines)
- `src/orchestrator.py` (added check + refresh logic, +200 lines)

**Database Schema:**
```sql
CREATE TABLE context_window_usage (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    task_id INTEGER REFERENCES tasks(id),
    timestamp DATETIME,
    input_tokens INTEGER,
    cache_creation_tokens INTEGER,
    cache_read_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER
);
```

**Key Commits:**
- `feat: Implement manual token tracking (Path B)`
- `feat: Add context window thresholds (70%/80%/95%)`
- `feat: Add automatic session refresh at 80%`

### Session Management

**Files Modified:**
- `src/core/models.py` (added Session model, +40 lines)
- `src/core/state.py` (added session methods, +120 lines)
- `src/orchestrator.py` (added milestone methods, +250 lines)

**Database Schema:**
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    session_id VARCHAR UNIQUE NOT NULL,
    project_id INTEGER REFERENCES projects(id),
    milestone_id INTEGER,
    started_at DATETIME,
    ended_at DATETIME,
    status VARCHAR,  -- 'active', 'completed', 'abandoned', 'refreshed'
    total_tokens INTEGER,
    total_turns INTEGER,
    total_cost_usd FLOAT,
    summary TEXT
);
```

**Key Commits:**
- `feat: Implement milestone-based sessions`
- `feat: Add Qwen-powered session summaries`
- `feat: Add previous milestone context injection`

---

## References

### Internal Documentation
- [SESSION_MANAGEMENT_GUIDE.md](../guides/SESSION_MANAGEMENT_GUIDE.md) - User guide
- [HEADLESS_MODE_IMPLEMENTATION.md](../development/HEADLESS_MODE_IMPLEMENTATION.md) - Technical docs
- [claude-code-headless-guide.md](../research/claude-code-headless-guide.md) - Headless research
- [claude-code-max-turns-guide.md](../research/claude-code-max-turns-guide.md) - Max turns guide
- [HEADLESS_MODE_GAP_ANALYSIS.md](../development/HEADLESS_MODE_GAP_ANALYSIS.md) - Gap analysis

### External References
- [Claude Code CLI Documentation](https://docs.claude.com/en/docs/claude-code)
- [Claude Code JSON Response Schema](../research/claude-code-json-response-schema.md)
- [Ollama API](https://github.com/ollama/ollama/blob/main/docs/api.md) - For Qwen summaries

### Configuration Examples
- [config.example.yaml](../../config/config.example.yaml) - Full configuration reference
- [config.yaml](../../config/config.yaml) - Production configuration

### Code Locations
- **MaxTurnsCalculator:** `src/orchestration/max_turns_calculator.py`
- **Session Management:** `src/orchestrator.py` (lines 316-552)
- **Token Tracking:** `src/orchestrator.py` (lines 1322-1396)
- **Agent Execution:** `src/agents/claude_code_local.py` (lines 209-393)
- **Config Validation:** `src/core/config.py` (lines 332-810)

---

## Related ADRs

- [ADR-004: Local Agent Architecture](ADR-004-local-agent-architecture.md) - Headless mode foundation
- [ADR-003: File Watcher Thread Cleanup](ADR-003-file-watcher-thread-cleanup.md) - Thread management patterns
- [001: Why Plugins](001_why_plugins.md) - Plugin architecture rationale
- [003: State Management](003_state_management.md) - StateManager as single source of truth

---

## Future Considerations

### Potential Improvements (v2.0+)

1. **ML-Based Complexity Estimation**
   - Train classifier on historical task data
   - More accurate max_turns prediction
   - Adaptive learning from user corrections

2. **Path A Implementation (If Available)**
   - Use Claude-provided context window percentage
   - Remove manual token tracking
   - More accurate threshold detection

3. **Distributed Session Management**
   - Share sessions across multiple Obra instances
   - Redis-backed session state
   - Multi-agent coordination

4. **Advanced Context Compression**
   - Semantic compression (keep relevant, drop redundant)
   - Vector embeddings for similarity search
   - Progressive summarization (multi-level)

5. **Predictive Timeout Adjustment**
   - Estimate timeout based on task complexity
   - Dynamic adjustment during execution
   - Learn from historical completion times

### Open Questions

1. **Is 7200s timeout too long for production?**
   - Monitor average task duration in production
   - Consider making timeout adaptive (based on max_turns)

2. **Should we add more task type overrides?**
   - Collect data on task type distribution
   - Identify patterns that need specific max_turns

3. **Can we reduce token tracking drift?**
   - Track system messages more accurately
   - Calibrate against Claude's actual usage
   - Periodic drift correction

4. **Should session refresh be configurable per milestone?**
   - Some milestones may prefer longer sessions
   - Others may want frequent refreshes
   - Add milestone-level configuration

---

**Last Updated:** 2025-11-04
**Version:** 1.0
**Status:** Accepted and Implemented
**Implementation:** Phase 4 + 5 Complete (Nov 2-4, 2025)
