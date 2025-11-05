# Session Management Guide

**User Guide for Understanding and Using Obra's Session Management Features**

This guide explains how Obra manages Claude Code sessions, handles context windows, and optimizes task execution through intelligent session management.

## Table of Contents

1. [Overview](#overview)
2. [Session Lifecycle](#session-lifecycle)
3. [Context Window Management](#context-window-management)
4. [Max Turns Management](#max-turns-management)
5. [Configuration Guide](#configuration-guide)
6. [Best Practices](#best-practices)
7. [Examples](#examples)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Session Management?

Obra uses a **milestone-based session management** system where:

- **Sessions** represent a continuous conversation with Claude Code
- **Milestones** group related tasks together in a single session
- **Context** is maintained across tasks within a milestone
- **Summaries** preserve key information when sessions end

### Why Does Session Management Matter?

Without proper session management:
- Context window overflows cause errors
- Long tasks get terminated prematurely
- Redundant information gets repeated
- Performance degrades over time

With Obra's intelligent session management:
- ✅ **Automatic context window monitoring** prevents overflows
- ✅ **Adaptive max turns** prevents premature termination
- ✅ **Session summaries** maintain continuity
- ✅ **Extended timeouts** support complex workflows

---

## Session Lifecycle

### 1. Session Start

When Obra begins a milestone, it:

```
┌─────────────────────────────────────┐
│ START MILESTONE                      │
├─────────────────────────────────────┤
│ 1. Generate session_id (UUID)       │
│ 2. Create database record            │
│ 3. Build milestone context          │
│    - Project info                    │
│    - Workplan                        │
│    - Previous milestone summary      │
│ 4. Configure agent with session_id  │
└─────────────────────────────────────┘
```

**Log Example:**
```
SESSION START: session_id=550e8400..., project_id=1, context=milestone 5
```

### 2. Task Execution Within Session

Each task in the milestone reuses the same session:

```
Task 1 → Claude Code (session_id: 550e8400...)
         ↓
         Validation + Scoring
         ↓
Task 2 → Claude Code (SAME session_id)
         ↓
         Context preserved!
```

**First Task Gets Special Treatment:**
- Workplan context injected into prompt
- Previous milestone summary included
- Sets the stage for subsequent tasks

**Subsequent Tasks:**
- Reuse established session
- Build on previous context
- Faster execution (less context needed)

### 3. Session End

When milestone completes, Obra:

1. **Generates Summary** using Qwen (local LLM)
   - What was accomplished
   - Implementation decisions made
   - Current codebase state
   - Issues encountered
   - Next steps

2. **Saves Summary** to database

3. **Marks Session Complete** with metadata:
   - Total tokens used
   - Number of turns
   - Duration
   - Status (completed/abandoned/refreshed)

**Log Example:**
```
SESSION END: session_id=550e8400..., summary_chars=2,453, milestone=5
```

---

## Context Window Management

### How Context Windows Work

Claude Code has a **context window limit** (200,000 tokens for Claude Pro). As you work:

```
┌──────────────────────────────────────────┐
│ Context Window (200,000 tokens)          │
├──────────────────────────────────────────┤
│ ████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░│ 30% (START)
│                                           │
│ After 5 tasks:                            │
│ ████████████████████████████░░░░░░░░░░░░│ 70% (WARNING)
│                                           │
│ After 8 tasks:                            │
│ ████████████████████████████████░░░░░░░░│ 80% (REFRESH)
│                                           │
│ After 12 tasks:                           │
│ ████████████████████████████████████████│ 95% (CRITICAL)
└──────────────────────────────────────────┘
```

### Automatic Threshold Detection

Obra tracks token usage manually and takes action at key thresholds:

#### 70% - Warning Threshold
```
CONTEXT_WINDOW WARNING: session_id=550e8400...,
  usage=70.5% (141,000/200,000) - approaching refresh threshold (80%)
```

**Action:** Log warning, continue normally

#### 80% - Refresh Threshold
```
CONTEXT_WINDOW REFRESH: session_id=550e8400...,
  usage=80.2% (160,400/200,000) - auto-refreshing (threshold=80%)
```

**Action:** Automatic session refresh
1. Generate summary of old session (using Qwen)
2. Create new session with fresh context
3. Prepend summary to next prompt
4. Continue seamlessly

**User Impact:** Brief pause for summary generation (~5-10 seconds)

#### 95% - Critical Threshold
```
CONTEXT_WINDOW CRITICAL: session_id=550e8400...,
  usage=95.8% (191,600/200,000) - forcing refresh
```

**Action:** Emergency session refresh (same as 80%, but logged as critical)

### Manual Token Tracking (Path B)

Since Claude Code doesn't provide context window percentage via API, Obra implements **manual tracking**:

```python
# Obra tracks tokens after each response
response = agent.send_prompt(prompt)
metadata = agent.get_last_metadata()

# Extract token breakdown
input_tokens = metadata['input_tokens']
cache_read_tokens = metadata['cache_read_tokens']
cache_creation_tokens = metadata['cache_creation_tokens']
output_tokens = metadata['output_tokens']
total_tokens = sum([input_tokens, cache_read_tokens,
                    cache_creation_tokens, output_tokens])

# Add to cumulative session total
state_manager.add_session_tokens(session_id, task_id, tokens_dict)

# Check against limit
current_usage = state_manager.get_session_token_usage(session_id)
percentage = current_usage / context_window_limit  # e.g., 0.82 (82%)
```

**Why Manual Tracking?**
- Claude Code JSON doesn't include context window percentage
- We track cumulative tokens across all interactions
- More accurate than single-prompt estimates

**Potential Drift:**
- System messages add ~200-500 tokens per turn
- Cache efficiency varies (40-90% hit rate)
- Estimate may be ±5-10% off actual usage

**Mitigation:**
- Conservative thresholds (70%, 80%, 95%)
- Generous context window limit (200K)
- Frequent summary generation

---

## Max Turns Management

### What Are "Turns"?

A **turn** is one iteration of the orchestration loop:

```
Turn 1: Prompt → Execute → Validate → Score → Decision
Turn 2: Feedback + Prompt → Execute → Validate → Score → Decision
Turn 3: Feedback + Prompt → Execute → Validate → Score → Decision
...
```

**Each turn consumes:**
- Tokens (context window)
- Time (wall-clock duration)
- API credits (if using paid tier)

### Why Limit Turns?

Without limits:
- Tasks run indefinitely (infinite loops)
- Context windows fill up
- Resources wasted on unachievable goals

With intelligent limits:
- ✅ Tasks complete faster
- ✅ Resources used efficiently
- ✅ Failures detected early

### Adaptive Max Turns Calculation

Obra calculates `max_turns` based on **task complexity**:

```
Simple Task         → 3 turns   (single file, specific fix)
Medium Task         → 6 turns   (small feature, module refactor)
Complex Task        → 12 turns  (complete feature, multi-file)
Very Complex Task   → 20 turns  (large refactor, migrations)
```

**Complexity Indicators:**
- **Keywords:** "migrate", "refactor", "implement", "debug", "comprehensive"
- **Scope:** "all files", "entire codebase", "multiple", "across"
- **Metadata:** Number of files, lines of code, task type

**Example:**
```python
# Task: "Fix authentication bug in login.py"
# Analysis:
#   - complexity_words: 0
#   - scope_words: 0
#   - estimated_files: 1
#   - estimated_loc: 50
# Result: 3 turns (simple task)

# Task: "Refactor entire authentication system across multiple modules"
# Analysis:
#   - complexity_words: 1 ("refactor")
#   - scope_words: 2 ("entire", "multiple")
#   - estimated_files: 8
#   - estimated_loc: 600
# Result: 20 turns (very complex task)
```

### Task Type Overrides

Certain task types have **fixed defaults** (from config):

```yaml
max_turns:
  by_task_type:
    validation: 5        # Quick checks
    code_generation: 12  # Code writing
    refactoring: 15      # Code improvements
    debugging: 20        # Troubleshooting
    error_analysis: 8    # Error investigation
    planning: 5          # Task planning
    documentation: 3     # Doc generation
    testing: 8           # Test writing
```

**Override takes precedence over complexity analysis.**

### Auto-Retry on error_max_turns

When a task exceeds `max_turns`:

```
┌────────────────────────────────────────────────┐
│ Turn 10/10: Task not complete                  │
│ ❌ ERROR_MAX_TURNS: Exceeded limit (10 turns)  │
├────────────────────────────────────────────────┤
│ AUTO-RETRY ENABLED                             │
│ Attempt 1 failed with max_turns=10            │
│ Retrying with max_turns=20 (2x multiplier)    │
├────────────────────────────────────────────────┤
│ Turn 1/20: Resume task...                      │
│ ...                                            │
│ Turn 15/20: ✓ Task complete!                   │
└────────────────────────────────────────────────┘
```

**Configuration:**
```yaml
max_turns:
  auto_retry: true           # Enable auto-retry
  max_retries: 1             # Retry once (2 attempts total)
  retry_multiplier: 2        # Double max_turns on retry
```

**Log Example:**
```
ERROR_MAX_TURNS: task_id=123, turns_used=10, max_turns=10, attempt=1/2
MAX_TURNS RETRY: task_id=123, attempt=2/2, max_turns=10 → 20 (multiplier=2x)
```

**When Retries Fail:**
```
MAX_TURNS EXHAUSTED: task_id=123, attempts=2, final_max_turns=20, last_turns_used=20
```

Task is marked as **failed** and may trigger a **breakpoint** for human review.

### Bounds Enforcement

Obra enforces **safety bounds** (from Claude Code guide):

- **Minimum:** 3 turns (never less)
- **Maximum:** 30 turns (never more)

Even with retry multiplier, max_turns is capped at 30.

---

## Configuration Guide

### Session Settings

```yaml
session:
  # Session persistence (NOT RECOMMENDED for production)
  # Fresh sessions are more reliable
  use_session_persistence: false

  # Context window configuration
  context_window:
    # Limit (tokens) - must match Claude tier
    # Claude Pro: 200,000 tokens
    # Claude Teams: 200,000 tokens
    limit: 200000

    # Thresholds (percentages 0.0-1.0)
    thresholds:
      warning: 0.70   # 70% = 140,000 tokens
      refresh: 0.80   # 80% = 160,000 tokens
      critical: 0.95  # 95% = 190,000 tokens
```

### Max Turns Configuration

```yaml
orchestration:
  max_turns:
    # Enable adaptive calculation
    adaptive: true

    # Fallback default
    default: 10

    # Safety bounds
    min: 3
    max: 30

    # Task type overrides
    by_task_type:
      debugging: 20
      code_generation: 12
      validation: 5

    # Retry behavior
    auto_retry: true
    max_retries: 1
    retry_multiplier: 2
```

### Extended Timeout

```yaml
agent:
  local:
    # Extended timeout (seconds)
    # Default: 7200 (2 hours) - allows complex workflows
    response_timeout: 7200
```

**Why 2 Hours?**
- Complex tasks may take 20+ turns
- Each turn: 3-5 minutes typical
- 20 turns × 5 min = 100 minutes (~2 hours)
- Provides buffer for slower operations

**Timeout vs Max Turns:**
- **Timeout:** Wall-clock limit (absolute deadline)
- **Max Turns:** Iteration limit (number of attempts)
- Both limits apply independently
- Whichever hits first ends the task

---

## Best Practices

### When to Use Milestone Sessions

✅ **Use milestone sessions for:**
- Related tasks that build on each other
- Multi-phase features (design → implement → test)
- Iterative refinement workflows
- Code reviews with multiple fixes

❌ **Don't use milestone sessions for:**
- Independent, unrelated tasks
- Quick one-off operations
- Tasks with completely different contexts
- Experimental/exploratory work

### Tuning Context Window Thresholds

**Conservative Settings** (frequent refresh):
```yaml
thresholds:
  warning: 0.60   # Early warning
  refresh: 0.70   # Refresh earlier
  critical: 0.90  # Still conservative
```

**Pros:** Fewer out-of-memory errors, more frequent summaries
**Cons:** More overhead, more interruptions

**Aggressive Settings** (maximize context):
```yaml
thresholds:
  warning: 0.80   # Late warning
  refresh: 0.85   # Refresh later
  critical: 0.98  # Maximum usage
```

**Pros:** Less overhead, fewer interruptions
**Cons:** Higher risk of overflow, less margin for error

**Recommended** (balanced):
```yaml
thresholds:
  warning: 0.70
  refresh: 0.80
  critical: 0.95
```

### Monitoring Context Window Logs

**Key logs to watch:**

```bash
# Normal operation
CONTEXT_WINDOW: session_id=550e8400..., tracked=45,234 tokens

# Warning threshold crossed
CONTEXT_WINDOW WARNING: session_id=550e8400...,
  usage=70.5% (141,000/200,000) - approaching refresh threshold (80%)

# Automatic refresh triggered
CONTEXT_WINDOW REFRESH: session_id=550e8400...,
  usage=80.2% (160,400/200,000) - auto-refreshing (threshold=80%)
SESSION REFRESH: new_session=7b3c9d12..., summary_chars=2,453

# Emergency refresh (critical threshold)
CONTEXT_WINDOW CRITICAL: session_id=550e8400...,
  usage=95.8% (191,600/200,000) - forcing refresh
```

**What to do:**
- **WARNING:** No action needed, just awareness
- **REFRESH:** Brief pause expected (~5-10s), normal behavior
- **CRITICAL:** Consider lowering refresh threshold if this happens often

### Configuring Max Turns for Different Task Types

**Quick Tasks** (validation, planning, docs):
```yaml
by_task_type:
  validation: 5
  planning: 5
  documentation: 3
```

**Medium Tasks** (testing, error analysis):
```yaml
by_task_type:
  testing: 8
  error_analysis: 8
```

**Complex Tasks** (code generation, refactoring):
```yaml
by_task_type:
  code_generation: 12
  refactoring: 15
```

**Very Complex Tasks** (debugging, migrations):
```yaml
by_task_type:
  debugging: 20
  migration: 20
```

**Custom Task Types:**
```yaml
by_task_type:
  api_integration: 15
  database_schema: 18
  ui_component: 10
```

### Interpreting MAX_TURNS Logs

**Normal completion:**
```
MAX_TURNS: task_id=123, max_turns=12, reason=calculated,
  estimated_files=5, estimated_loc=300
TASK END: task_id=123, status=completed, iterations=7, max_iterations=12
```
✓ Task completed in 7 turns (under the 12 turn limit)

**Exceeded with retry:**
```
ERROR_MAX_TURNS: task_id=123, turns_used=12, max_turns=12, attempt=1/2
MAX_TURNS RETRY: task_id=123, attempt=2/2, max_turns=12 → 24 (multiplier=2x)
TASK END: task_id=123, status=completed, iterations=18, max_iterations=24
```
✓ Task needed 18 turns total (12 + 6 more after retry)

**Exhausted retries:**
```
ERROR_MAX_TURNS: task_id=123, turns_used=24, max_turns=24, attempt=2/2
MAX_TURNS EXHAUSTED: task_id=123, attempts=2, final_max_turns=24,
  last_turns_used=24
```
❌ Task failed after 2 attempts (24 turns used)
→ Consider breaking task into smaller pieces

---

## Examples

### Example 1: Basic Milestone Execution

**Scenario:** Execute 3 related tasks in a milestone

```python
from src.orchestrator import Orchestrator
from src.core.config import Config

# Load configuration
config = Config.load('config/config.yaml')
orchestrator = Orchestrator(config=config)
orchestrator.initialize()

# Execute milestone with 3 tasks
result = orchestrator.execute_milestone(
    project_id=1,
    task_ids=[10, 11, 12],
    milestone_id=5,
    max_iterations_per_task=10
)

# Check results
print(f"Session ID: {result['session_id']}")
print(f"Tasks completed: {result['tasks_completed']}")
print(f"Tasks failed: {result['tasks_failed']}")
```

**Logs:**
```
SESSION START: session_id=550e8400..., project_id=1, context=milestone 5
Executing task 10 in session 550e8400...
TASK START: task_id=10, title='Implement authentication'
MAX_TURNS: task_id=10, max_turns=12, reason=calculated
TASK END: task_id=10, status=completed, iterations=8, max_iterations=12
Executing task 11 in session 550e8400...
...
SESSION END: session_id=550e8400..., summary_chars=2,453, milestone=5
MILESTONE END: milestone_id=5, completed=3, failed=0, session_id=550e8400...
```

### Example 2: Handling Context Window Refresh

**Scenario:** Long milestone with automatic session refresh

```python
# Execute milestone with many tasks (will hit 80% threshold)
result = orchestrator.execute_milestone(
    project_id=1,
    task_ids=range(1, 15),  # 14 tasks
    milestone_id=7
)
```

**Logs:**
```
SESSION START: session_id=550e8400..., project_id=1, context=milestone 7
Executing task 1...
CONTEXT_WINDOW: session_id=550e8400..., usage=25.3% (50,600/200,000)
Executing task 2...
CONTEXT_WINDOW: session_id=550e8400..., usage=41.8% (83,600/200,000)
...
Executing task 8...
CONTEXT_WINDOW WARNING: session_id=550e8400..., usage=70.5% (141,000/200,000)
Executing task 9...
CONTEXT_WINDOW REFRESH: session_id=550e8400..., usage=80.2% (160,400/200,000)
SESSION REFRESH: 550e8400... → 7b3c9d12..., summary_chars=2,453
Executing task 10 with new session...
CONTEXT_WINDOW: session_id=7b3c9d12..., usage=22.1% (44,200/200,000)
...
SESSION END: session_id=7b3c9d12..., summary_chars=3,102, milestone=7
```

### Example 3: Configuring Max Turns for Different Task Types

**config.yaml:**
```yaml
orchestration:
  max_turns:
    adaptive: true
    default: 10
    by_task_type:
      debugging: 25      # Very complex
      refactoring: 15
      code_generation: 12
      testing: 8
      validation: 5
    auto_retry: true
    max_retries: 1
    retry_multiplier: 2
```

**Usage:**
```python
# Task with type='debugging' will get max_turns=25
task = state_manager.create_task(
    project_id=1,
    title='Debug memory leak in worker pool',
    description='Investigate and fix memory leak...',
    task_type='debugging'  # ← Triggers max_turns=25
)

result = orchestrator.execute_task(task.id)
```

**Logs:**
```
MAX_TURNS: task_id=456, max_turns=25, reason=task_type_override (debugging)
TASK START: task_id=456, title='Debug memory leak in worker pool'
Turn 1/25: Analyzing code...
...
Turn 18/25: Found leak in ThreadPoolExecutor...
Turn 19/25: Applied fix...
TASK END: task_id=456, status=completed, iterations=19, max_iterations=25
```

---

## Troubleshooting

### Problem: "Context window exceeded" errors

**Symptoms:**
```
ERROR: Context window limit exceeded (200,000 tokens)
CONTEXT_WINDOW CRITICAL: usage=95.8% (191,600/200,000)
```

**Solution:**
1. Lower refresh threshold to refresh earlier:
   ```yaml
   context_window:
     thresholds:
       refresh: 0.70  # Refresh at 70% instead of 80%
   ```

2. Check if tasks are too large (break into smaller pieces)

3. Verify `context_window.limit` matches your Claude tier

### Problem: Tasks hitting max_turns too often

**Symptoms:**
```
ERROR_MAX_TURNS: task_id=123, turns_used=12, max_turns=12
MAX_TURNS EXHAUSTED: attempts=2, final_max_turns=24
```

**Solution:**
1. Increase default max_turns:
   ```yaml
   max_turns:
     default: 15  # Increase from 10
   ```

2. Add task-type overrides for specific types:
   ```yaml
   max_turns:
     by_task_type:
       code_generation: 18  # Increase for complex generation
   ```

3. Increase retry multiplier:
   ```yaml
   max_turns:
     retry_multiplier: 3  # Triple instead of double
   ```

4. Break task into smaller subtasks

### Problem: Session refresh too frequent (performance overhead)

**Symptoms:**
```
CONTEXT_WINDOW REFRESH: session_id=550e8400... (happens every 2-3 tasks)
```

**Solution:**
1. Raise refresh threshold to delay refresh:
   ```yaml
   context_window:
     thresholds:
       refresh: 0.85  # Refresh at 85% instead of 80%
   ```

2. Reduce verbosity in prompts (use shorter descriptions)

3. Use milestone sessions only for related tasks

### Problem: Tasks timing out (response_timeout exceeded)

**Symptoms:**
```
CLAUDE_TIMEOUT: Timeout after 7200s (2 hours)
```

**Solution:**
1. Increase timeout for complex tasks:
   ```yaml
   agent:
     local:
       response_timeout: 14400  # 4 hours
   ```

2. Check if task is stuck in infinite loop (review logs)

3. Consider breaking task into smaller pieces

4. Verify max_turns isn't too high (causing excessive iterations)

### Problem: Inaccurate token tracking (drift)

**Symptoms:**
```
# Expected: ~80% usage
CONTEXT_WINDOW REFRESH: usage=75.2% (150,400/200,000)
# Or
CONTEXT_WINDOW CRITICAL: usage=98.1% (196,200/200,000)  # Unexpected!
```

**Solution:**
1. Token tracking is approximate (±5-10% drift is normal)

2. If drift is large (>15%), check for:
   - System messages not tracked (~500 tokens/turn)
   - Cache efficiency changes (affects effective tokens)

3. Lower thresholds to be more conservative:
   ```yaml
   context_window:
     thresholds:
       warning: 0.60   # Earlier warning
       refresh: 0.70   # Earlier refresh
       critical: 0.90  # More margin
   ```

4. Consider using fresh sessions more often (disable session_persistence)

### Problem: Session summaries too short/long

**Symptoms:**
```
SESSION END: summary_chars=482  # Too short (< 500)
# Or
SESSION END: summary_chars=8,953  # Too long (> 5000)
```

**Solution:**
Summaries are generated by Qwen with these parameters:
```python
summary = llm_interface.generate(
    prompt=summary_prompt,
    temperature=0.3,     # Low for consistency
    max_tokens=1500      # Limits length
)
```

Adjust via config:
```yaml
llm:
  temperature: 0.3   # Lower = more focused
  max_tokens: 1500   # Increase for longer summaries
```

---

## Further Reading

- [HEADLESS_MODE_IMPLEMENTATION.md](../development/HEADLESS_MODE_IMPLEMENTATION.md) - Technical implementation details
- [ADR-007-headless-mode-enhancements.md](../decisions/ADR-007-headless-mode-enhancements.md) - Architecture decisions
- [config.example.yaml](../../config/config.example.yaml) - Full configuration reference
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md) - System architecture overview

---

**Last Updated:** 2025-11-04
**Version:** v1.1 (Phase 5 Complete)
