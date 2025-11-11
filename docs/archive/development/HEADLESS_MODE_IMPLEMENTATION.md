# Headless Mode Implementation

**Technical Documentation for Developers**

This document provides technical implementation details for Obra's headless mode, session management, context window tracking, and adaptive max turns calculation.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Phase 4: Max Turns Implementation](#phase-4-max-turns-implementation)
3. [Phase 5: Extended Timeout & Polish](#phase-5-extended-timeout--polish)
4. [Context Window Management (Path B)](#context-window-management-path-b)
5. [Session Management](#session-management)
6. [Testing Approach](#testing-approach)
7. [Code Structure](#code-structure)

---

## Architecture Overview

### Headless Mode Design

Obra uses **headless mode** for Claude Code execution:

```
┌────────────────────────────────────────────────────┐
│ Orchestrator                                        │
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │ ClaudeCodeLocalAgent (headless)             │  │
│  │                                              │  │
│  │  subprocess.run([                            │  │
│  │    'claude',                                 │  │
│  │    '--print',                    ← headless │  │
│  │    '--session-id', session_id,   ← sessions │  │
│  │    '--output-format', 'json',    ← metadata │  │
│  │    '--max-turns', max_turns,     ← adaptive │  │
│  │    '--dangerously-skip-permissions', ← auto │  │
│  │    prompt                                    │  │
│  │  ])                                          │  │
│  │                                              │  │
│  │  Returns: JSON with result + metadata       │  │
│  └─────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```

**Key Features:**
- **`--print` flag:** Non-interactive output mode (no TTY needed)
- **`--session-id`:** Session persistence across calls
- **`--output-format json`:** Structured metadata (tokens, turns, cost)
- **`--max-turns`:** Adaptive iteration limit (Phase 4)
- **`--dangerously-skip-permissions`:** Autonomous operation (dangerous mode)
- **Fresh sessions:** Each call uses subprocess.run() (no persistent process)

### Fresh Sessions vs Persistent Sessions

Obra provides **context continuity** even with fresh Claude sessions:

```
┌──────────────────────────────────────────────────────┐
│ FRESH SESSION PER CALL (Obra's Approach)             │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Call 1: subprocess.run([...], session_id=A)         │
│          ↓ Returns → Obra stores response            │
│                                                       │
│  Call 2: subprocess.run([...], session_id=A)         │
│          ↓ Receives context from Call 1              │
│          ↓ Returns → Obra stores response            │
│                                                       │
│  Call 3: subprocess.run([...], session_id=A)         │
│          ↓ Receives context from Call 1 + 2          │
│          ↓ Returns → Obra stores response            │
│                                                       │
│  Milestone End: Generate summary (via Qwen)          │
│                 Save to database                     │
│                                                       │
│  Next Milestone: Include previous summary in prompt  │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**Benefits:**
- ✅ **Reliability:** No process state bugs (each call is clean)
- ✅ **Simplicity:** No PTY emulation needed (avoids Claude Code bugs)
- ✅ **Continuity:** Obra provides context via prompts + summaries
- ✅ **Session persistence:** --session-id maintains Claude's context
- ✅ **Stateless:** No cleanup needed (no orphaned processes)

**Trade-offs:**
- ⚠️ Slightly slower startup (subprocess overhead ~100-200ms)
- ⚠️ Relies on Obra for continuity (not Claude's session state)
- ✅ More reliable than persistent sessions (no lock conflicts)

### Why PTY Was Abandoned

**PTY (Pseudo-Terminal) attempt:**
```python
# ATTEMPTED (but failed due to Claude Code bugs)
import pty
import os

master, slave = pty.openpty()
subprocess.Popen([...], stdin=slave, stdout=slave, stderr=slave)
# ❌ Claude Code has known issues with PTY
# ❌ Output parsing unreliable
# ❌ No bugfix available from Claude team
```

**Issues encountered:**
1. Claude Code sends ANSI escape codes (colors, cursor movement)
2. Progress indicators interfere with output parsing
3. Session state gets corrupted on certain prompts
4. No reliable completion detection

**Solution:** Use `--print` flag instead (clean, parseable output)

---

## Phase 4: Max Turns Implementation

### MaxTurnsCalculator Algorithm

**File:** `src/orchestration/max_turns_calculator.py`

The `MaxTurnsCalculator` analyzes task complexity to determine appropriate `max_turns`:

```python
class MaxTurnsCalculator:
    """Calculate appropriate max_turns based on task complexity.

    Decision Logic:
    1. Check task_type override (highest priority)
    2. Analyze text for complexity/scope indicators
    3. Check metadata (estimated_files, estimated_loc)
    4. Apply decision rules (simple/medium/complex/very_complex)
    5. Enforce min/max bounds (3-30)
    """

    COMPLEX_WORDS = [
        'migrate', 'refactor', 'implement', 'debug', 'comprehensive',
        'entire', 'all', 'complete', 'full', 'across', 'multiple',
        'system', 'architecture', 'framework'
    ]

    SCOPE_INDICATORS = [
        'all files', 'entire codebase', 'multiple', 'across',
        'throughout', 'repository', 'project-wide', 'every'
    ]

    TASK_TYPE_DEFAULTS = {
        'validation': 5,
        'code_generation': 12,
        'refactoring': 15,
        'debugging': 20,
        'error_analysis': 8,
        'planning': 5,
        'documentation': 3,
        'testing': 8,
    }

    def calculate(self, task: Dict) -> int:
        """Calculate max_turns for task."""
        # Priority 1: Task type override
        task_type = task.get('task_type')
        if task_type and task_type in self.TASK_TYPE_DEFAULTS:
            return self._bound(self.TASK_TYPE_DEFAULTS[task_type])

        # Priority 2: Complexity analysis
        description = task.get('description', '').lower()
        title = task.get('title', '').lower()
        combined = f"{title} {description}"

        # Count indicators
        complexity = sum(1 for word in self.COMPLEX_WORDS if word in combined)
        scope = sum(1 for ind in self.SCOPE_INDICATORS if ind in combined)

        # Get metadata
        estimated_files = task.get('estimated_files', 1)
        estimated_loc = task.get('estimated_loc', 0)

        # Decision rules (based on Claude Code max-turns guide)
        if estimated_loc > 500 or scope >= 2:
            turns = 20  # Very complex
        elif complexity == 0 and scope == 0 and estimated_files <= 1:
            turns = 3   # Simple
        elif complexity <= 1 and scope == 0 and estimated_files <= 3:
            turns = 6   # Medium
        elif complexity <= 2 or scope == 1 or estimated_files <= 8:
            turns = 12  # Complex
        else:
            turns = self.default_turns  # Fallback

        return self._bound(turns)

    def _bound(self, turns: int) -> int:
        """Enforce bounds: min <= turns <= max."""
        return max(self.min_turns, min(turns, self.max_turns))
```

**Decision Tree:**

```
Task Analysis
    │
    ├─ Has task_type override? ─YES─> Use TASK_TYPE_DEFAULTS[type]
    │                           │
    │                           NO
    ↓                           ↓
Analyze Description         Analyze Description
    │                           │
    ├─ Count complexity words   │
    ├─ Count scope indicators   │
    ├─ Get estimated_files      │
    └─ Get estimated_loc        │
                                ↓
                        Apply Decision Rules:
                        ├─ loc > 500 OR scope >= 2       → 20 turns (very complex)
                        ├─ complexity=0, scope=0, files≤1 → 3 turns (simple)
                        ├─ complexity≤1, scope=0, files≤3 → 6 turns (medium)
                        ├─ complexity≤2, scope=1, files≤8 → 12 turns (complex)
                        └─ else                           → 10 turns (default)
                                ↓
                        Enforce Bounds (3 ≤ turns ≤ 30)
                                ↓
                            Return max_turns
```

### Complexity Analysis Logic

**Input:**
```python
task = {
    'id': 123,
    'title': 'Refactor authentication system across multiple modules',
    'description': 'Implement comprehensive refactor of auth...',
    'estimated_files': 8,
    'estimated_loc': 650
}
```

**Analysis:**
```python
# Text analysis
combined = "refactor authentication system across multiple modules implement comprehensive refactor..."

# Count complexity words
complexity = sum(1 for word in COMPLEX_WORDS if word in combined)
# Found: 'refactor' (×2), 'implement', 'comprehensive', 'multiple', 'across'
# complexity = 6

# Count scope indicators
scope = sum(1 for ind in SCOPE_INDICATORS if ind in combined)
# Found: 'multiple', 'across'
# scope = 2

# Get metadata
estimated_files = 8
estimated_loc = 650

# Apply rules
if estimated_loc > 500 or scope >= 2:  # TRUE (loc=650 > 500)
    turns = 20  # Very complex
```

**Output:**
```python
max_turns = 20
logger.info(f"Task 123: Calculated max_turns=20 (very complex: large refactor, >500 LOC)")
```

### Task Type Defaults

**Rationale** (from Claude Code max-turns guide):

| Task Type | Turns | Reasoning |
|-----------|-------|-----------|
| `validation` | 5 | Quick checks, focused scope |
| `code_generation` | 12 | Iterative code writing + testing |
| `refactoring` | 15 | Code changes + test cycles |
| `debugging` | 20 | Extensive investigation needed |
| `error_analysis` | 8 | Bounded analysis, not as exploratory |
| `planning` | 5 | Mostly reading/thinking |
| `documentation` | 3 | Usually quick, minimal iteration |
| `testing` | 8 | Test creation + fixes |

**Override Example:**
```python
# Task has task_type='debugging'
task = {'id': 456, 'task_type': 'debugging', ...}

# MaxTurnsCalculator.calculate(task)
# → Returns 20 (from TASK_TYPE_DEFAULTS['debugging'])
# → Skips complexity analysis entirely
```

### Retry Mechanism on error_max_turns

**Location:** `src/orchestrator.py` (execute_task method)

```python
def execute_task(self, task_id: int, max_iterations: int = 10, context: Optional[Dict] = None):
    # Calculate adaptive max_turns
    max_turns = self.max_turns_calculator.calculate(task_dict)

    # Retry loop for error_max_turns
    retry_count = 0
    max_retries = self.config.get('orchestration.max_turns.max_retries', 1)
    retry_multiplier = self.config.get('orchestration.max_turns.retry_multiplier', 2)
    auto_retry = self.config.get('orchestration.max_turns.auto_retry', True)

    while retry_count <= max_retries:
        try:
            # Add max_turns to context for agent
            context['max_turns'] = max_turns

            # Execute task
            result = self._execute_single_task(task, max_iterations, context)

            # Success - break out
            break

        except AgentException as e:
            # Check for error_max_turns
            if e.context_data.get('subtype') == 'error_max_turns' and auto_retry:
                if retry_count < max_retries:
                    # Retry with increased limit
                    retry_count += 1
                    old_max_turns = max_turns
                    max_turns = max_turns * retry_multiplier

                    # Enforce upper bound
                    max_turns = min(max_turns, self.max_turns_calculator.max_turns)

                    logger.info(
                        f"MAX_TURNS RETRY: task_id={task_id}, "
                        f"attempt={retry_count + 1}/{max_retries + 1}, "
                        f"max_turns={old_max_turns} → {max_turns}"
                    )
                    continue  # Retry
                else:
                    # Max retries exhausted
                    logger.error(f"MAX_TURNS EXHAUSTED: task_id={task_id}")
                    raise
            else:
                # Not error_max_turns - don't retry
                raise
```

**Flow Diagram:**

```
execute_task(task_id=123)
    │
    ├─ Calculate max_turns → 12 (adaptive)
    │
    ↓
Try 1: _execute_single_task(max_turns=12)
    │
    ├─ Turn 1, 2, 3, ..., 12 → Not complete
    │
    ↓
❌ AgentException: error_max_turns (turns_used=12)
    │
    ├─ auto_retry=true? YES
    ├─ retry_count < max_retries? YES (0 < 1)
    │
    ↓
Retry: max_turns = 12 * 2 = 24
       Enforce bound: min(24, 30) = 24
    │
    ↓
Try 2: _execute_single_task(max_turns=24)
    │
    ├─ Turn 1, 2, 3, ..., 18 → ✓ Complete
    │
    ↓
Return: status='completed', iterations=18
```

### Integration with Orchestrator

**Initialization:**
```python
# src/orchestrator.py
def _initialize_complexity_estimator(self):
    # ...existing code...

    # Initialize MaxTurnsCalculator
    max_turns_config = self.config.get('orchestration.max_turns', {})
    self.max_turns_calculator = MaxTurnsCalculator(config=max_turns_config)
    logger.info("MaxTurnsCalculator initialized")
```

**Usage:**
```python
# src/orchestrator.py
def execute_task(self, task_id, ...):
    # Get task
    task = self.state_manager.get_task(task_id)

    # Convert to dict with complexity metadata
    task_dict = task.to_dict()
    if complexity_estimate:
        task_dict['estimated_files'] = len(complexity_estimate.files_to_create +
                                           complexity_estimate.files_to_modify)
        task_dict['estimated_loc'] = sum(f.get('estimated_loc', 0) for f in ...)

    # Calculate max_turns
    max_turns = 10  # Default fallback
    if self.max_turns_calculator:
        max_turns = self.max_turns_calculator.calculate(task_dict)
        logger.info(f"MAX_TURNS: task_id={task_id}, max_turns={max_turns}")

    # Execute with retry logic
    # ... (see retry mechanism above)
```

**Agent receives max_turns:**
```python
# src/agents/claude_code_local.py
def send_prompt(self, prompt, context=None):
    # Extract max_turns from context
    max_turns = context.get('max_turns') if context else None

    # Build command
    args = ['--print', '--session-id', session_id]
    if max_turns:
        args.extend(['--max-turns', str(max_turns)])
        logger.info(f"CLAUDE_ARGS: max_turns={max_turns}")

    # Execute
    result = self._run_claude(args)
```

---

## Phase 5: Extended Timeout & Polish

### Extended Timeout (7200s)

**Rationale:**

Complex tasks with high max_turns need proportionally longer wall-clock time:

```
Typical Task (10 turns):
  10 turns × 3 min/turn = 30 minutes

Complex Task (20 turns):
  20 turns × 5 min/turn = 100 minutes (~2 hours)

Very Complex Task (30 turns):
  30 turns × 6 min/turn = 180 minutes (~3 hours)
```

**Default timeout: 7200 seconds (2 hours)**

**Configuration:**
```yaml
agent:
  local:
    # Extended timeout for complex workflows
    response_timeout: 7200  # 2 hours
```

**Why 2 hours?**
- Supports up to ~24 turns at 5 min/turn
- Provides buffer for slower operations
- Prevents premature termination of valid work
- Can be overridden in config for specific needs

**Alternative configurations:**

```yaml
# Quick tasks only (1 hour)
agent:
  local:
    response_timeout: 3600

# Very complex tasks (4 hours, overnight jobs)
agent:
  local:
    response_timeout: 14400

# Production (30 minutes, aggressive)
agent:
  local:
    response_timeout: 1800
```

### Comprehensive Logging Structure

**43+ log points** across the orchestration pipeline:

#### Task Execution Logs

```python
# Task start
logger.info(f"TASK START: task_id={task_id}, title='{task.title}'")

# Complexity estimation
logger.info(
    f"COMPLEXITY: task_id={task_id}, score={complexity_estimate.complexity_score:.0f}/100, "
    f"category={complexity_estimate.get_complexity_category()}, "
    f"decompose={complexity_estimate.should_decompose}"
)

# Max turns calculation
logger.info(
    f"MAX_TURNS: task_id={task_id}, max_turns={max_turns}, reason={max_turns_reason}, "
    f"estimated_files={task_dict.get('estimated_files', 0)}"
)

# Task end
logger.info(
    f"TASK END: task_id={task_id}, status={result['status']}, "
    f"iterations={result.get('iterations', 0)}, max_iterations={max_iterations}"
)
```

#### Iteration Logs

```python
# Iteration start
logger.debug(f"ITERATION START: task_id={task.id}, iteration={iteration}/{max_iterations}")

# Context built
logger.debug(f"CONTEXT BUILT: iteration={iteration}, context_chars={len(context_text):,}")

# Agent send
logger.info(f"AGENT SEND: task_id={task.id}, iteration={iteration}, prompt_chars={len(prompt):,}")

# Response metadata
logger.info(
    f"RESPONSE METADATA: iteration={iteration}, "
    f"tokens={total_tokens:,} (input={input_tokens:,}, output={output_tokens:,}), "
    f"turns={num_turns}, duration={duration_ms}ms"
)
```

#### Session Management Logs

```python
# Session start
logger.info(f"SESSION START: session_id={session_id[:8]}..., project_id={project_id}")

# Session end
logger.info(f"SESSION END: session_id={session_id[:8]}..., summary_chars={len(summary):,}")

# Milestone execution
logger.info(f"MILESTONE START: milestone_id={milestone_id}, num_tasks={len(task_ids)}")
logger.info(f"MILESTONE END: milestone_id={milestone_id}, completed={tasks_completed}")
```

#### Context Window Logs

```python
# Token tracking
logger.debug(f"CONTEXT_WINDOW: session_id={session_id[:8]}..., tracked={tokens_dict['total_tokens']:,} tokens")

# Warning threshold
logger.warning(
    f"CONTEXT_WINDOW WARNING: session_id={session_id[:8]}..., "
    f"usage={pct:.1%} ({current_tokens:,}/{limit:,})"
)

# Refresh threshold
logger.info(
    f"CONTEXT_WINDOW REFRESH: session_id={session_id[:8]}..., "
    f"usage={pct:.1%} - auto-refreshing"
)

# Session refresh
logger.info(f"SESSION REFRESH: {old_session_id[:8]}... → {new_session_id[:8]}...")

# Critical threshold
logger.error(f"CONTEXT_WINDOW CRITICAL: session_id={session_id[:8]}..., usage={pct:.1%}")
```

#### Max Turns Logs

```python
# Calculation
logger.info(
    f"Task {task_id}: Calculated max_turns={turns} ({reason})"
)
logger.debug(
    f"Task {task_id}: complexity={complexity}, scope={scope}, "
    f"files={estimated_files}, loc={estimated_loc}"
)

# Error detection
logger.error(
    f"CLAUDE_ERROR_MAX_TURNS: session_id={session_id[:8]}..., "
    f"turns_used={num_turns}, max_turns_limit={max_turns_limit}"
)

# Retry
logger.warning(
    f"ERROR_MAX_TURNS: task_id={task_id}, turns_used={num_turns}, "
    f"max_turns={max_turns}, attempt={retry_count + 1}/{max_retries + 1}"
)
logger.info(
    f"MAX_TURNS RETRY: task_id={task_id}, max_turns={old_max_turns} → {max_turns}"
)

# Exhausted
logger.error(
    f"MAX_TURNS EXHAUSTED: task_id={task_id}, attempts={max_retries + 1}, "
    f"final_max_turns={max_turns}"
)
```

#### Agent Logs

```python
# Command execution
logger.info(
    f"CLAUDE_SEND: prompt_chars={len(prompt):,}, session={session_id[:8]}..., "
    f"max_turns={max_turns or 'default'}"
)
logger.debug(f"CLAUDE_PROMPT: {prompt[:100]}...")

# Response
logger.info(
    f"CLAUDE_RESPONSE: session_id={session_id[:8]}..., result_chars={len(result_text):,}"
)
logger.info(
    f"CLAUDE_JSON_METADATA: tokens={total_tokens:,}, turns={num_turns}, "
    f"duration={duration_ms}ms, cache_efficiency={cache_hit_rate:.1%}"
)

# Session conflicts
logger.warning(
    f"CLAUDE_SESSION_IN_USE: session_id={session_id[:8]}..., "
    f"attempt={attempt + 1}/{max_retries}, retry_delay={retry_delay:.1f}s"
)
logger.error(
    f"CLAUDE_SESSION_LOCKED: session_id={session_id[:8]}..., "
    f"max_retries={max_retries} exhausted"
)

# Command failures
logger.error(
    f"CLAUDE_COMMAND_FAILED: exit_code={result.returncode}, stderr={result.stderr[:200]}"
)
```

### Configuration Validation

**File:** `src/core/config.py`

Comprehensive validation ensures configuration correctness:

```python
class Config:
    def validate(self) -> bool:
        """Validate configuration structure and values."""
        self._validate_context_thresholds()
        self._validate_max_turns()
        self._validate_timeouts()
        self._validate_confidence_threshold()
        self._validate_quality_threshold()
        self._validate_breakpoints()
        self._validate_llm_config()
        self._validate_agent_config()
        return True
```

#### Context Window Validation

```python
def _validate_context_thresholds(self) -> None:
    """Validate context window thresholds.

    Rules:
    - Must be floats between 0.0 and 1.0
    - warning < refresh < critical
    - All three must be present
    """
    thresholds = self.get('context.thresholds', {})

    required_keys = ['warning', 'refresh', 'critical']
    for key in required_keys:
        if key not in thresholds:
            raise ConfigValidationException(
                config_key=f'context.thresholds.{key}',
                expected='float between 0.0 and 1.0',
                got='missing'
            )

    values = {k: float(thresholds[k]) for k in required_keys}

    # Validate range
    for key, value in values.items():
        if not (0.0 <= value <= 1.0):
            raise ConfigValidationException(
                config_key=f'context.thresholds.{key}',
                expected='float between 0.0 and 1.0',
                got=str(value)
            )

    # Validate ordering
    if not (values['warning'] < values['refresh'] < values['critical']):
        raise ConfigValidationException(
            config_key='context.thresholds',
            expected='warning < refresh < critical',
            got=f"warning={values['warning']}, refresh={values['refresh']}, critical={values['critical']}"
        )
```

#### Max Turns Validation

```python
def _validate_max_turns(self) -> None:
    """Validate max_turns configuration.

    Rules:
    - min >= 3
    - max <= 30
    - default between min and max
    - retry_multiplier >= 1.0
    """
    max_turns = self.get('orchestration.max_turns', {})

    # Validate min
    min_turns = max_turns.get('min')
    if min_turns is not None and min_turns < 3:
        raise ConfigValidationException(
            config_key='orchestration.max_turns.min',
            expected='integer >= 3',
            got=str(min_turns)
        )

    # Validate max
    max_value = max_turns.get('max')
    if max_value is not None and max_value > 30:
        raise ConfigValidationException(
            config_key='orchestration.max_turns.max',
            expected='integer <= 30',
            got=str(max_value)
        )

    # Validate default
    default_turns = max_turns.get('default')
    if default_turns is not None:
        min_val = min_turns or 3
        max_val = max_value or 30
        if not (min_val <= default_turns <= max_val):
            raise ConfigValidationException(
                config_key='orchestration.max_turns.default',
                expected=f'integer between {min_val} and {max_val}',
                got=str(default_turns)
            )
```

#### Timeout Validation

```python
def _validate_timeouts(self) -> None:
    """Validate timeout configurations.

    Rules:
    - All timeouts must be positive integers
    - response_timeout >= 60 (minimum 1 minute)
    """
    timeout_checks = [
        ('agent.timeout', 60),
        ('agent.local.response_timeout', 60),
        ('orchestration.iteration_timeout', 1),
        ('orchestration.task_timeout', 1),
    ]

    for timeout_path, min_value in timeout_checks:
        timeout = self.get(timeout_path)
        if timeout is None:
            continue

        if not isinstance(timeout, int):
            raise ConfigValidationException(
                config_key=timeout_path,
                expected='positive integer',
                got=type(timeout).__name__
            )

        if timeout < min_value:
            raise ConfigValidationException(
                config_key=timeout_path,
                expected=f'integer >= {min_value}',
                got=str(timeout)
            )
```

---

## Context Window Management (Path B)

### Why Path B (Manual Tracking)?

**Path A (Ideal):** Claude Code provides context window percentage via API
```json
{
  "result": "...",
  "context_window_usage": 0.82  // 82% full
}
```
❌ **Not available** - Claude Code doesn't expose this

**Path B (Implemented):** Obra tracks tokens manually
```python
# Track cumulative tokens across all interactions
session_tokens = 0
for interaction in session:
    session_tokens += interaction.total_tokens

# Calculate percentage
percentage = session_tokens / context_window_limit  # e.g., 0.82
```
✅ **Implemented** - Works but requires tracking

### ContextWindowUsage Model

**File:** `src/core/models.py`

```python
class ContextWindowUsage(Base):
    """Tracks token usage for context window management.

    Attributes:
        id: Primary key
        session_id: Session UUID
        task_id: Task being executed
        timestamp: When tokens were added
        input_tokens: New input tokens
        cache_creation_tokens: New cache creation tokens
        cache_read_tokens: Cache hits (don't count toward limit)
        output_tokens: Generated tokens
        total_tokens: Sum of all tokens
    """
    __tablename__ = 'context_window_usage'

    id = Column(Integer, primary_key=True)
    session_id = Column(String, nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.now, nullable=False)

    # Token breakdown
    input_tokens = Column(Integer, default=0)
    cache_creation_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
```

### StateManager Token Tracking Methods

**File:** `src/core/state.py`

```python
class StateManager:
    def add_session_tokens(
        self,
        session_id: str,
        task_id: int,
        tokens_dict: Dict[str, int]
    ) -> None:
        """Add tokens to session's cumulative usage.

        Args:
            session_id: Session UUID
            task_id: Task ID
            tokens_dict: Token breakdown with keys:
                - input_tokens
                - cache_creation_tokens
                - cache_read_tokens
                - output_tokens
                - total_tokens (calculated)
        """
        usage = ContextWindowUsage(
            session_id=session_id,
            task_id=task_id,
            timestamp=datetime.now(UTC),
            input_tokens=tokens_dict.get('input_tokens', 0),
            cache_creation_tokens=tokens_dict.get('cache_creation_tokens', 0),
            cache_read_tokens=tokens_dict.get('cache_read_tokens', 0),
            output_tokens=tokens_dict.get('output_tokens', 0),
            total_tokens=tokens_dict.get('total_tokens', 0)
        )

        self.session.add(usage)
        self.session.commit()

    def get_session_token_usage(self, session_id: str) -> int:
        """Get cumulative token usage for session.

        Returns total tokens used across all interactions in session.
        """
        result = (
            self.session.query(func.sum(ContextWindowUsage.total_tokens))
            .filter(ContextWindowUsage.session_id == session_id)
            .scalar()
        )
        return result or 0
```

### Threshold Checks Before Execution

**File:** `src/orchestrator.py` (`_execute_single_task` method)

```python
def _execute_single_task(self, task, max_iterations, context):
    """Execute single task with context window monitoring."""

    for iteration in range(1, max_iterations + 1):
        # Check context window BEFORE sending prompt
        if self.agent.use_session_persistence and hasattr(self.agent, 'session_id'):
            session_id = self.agent.session_id
            if session_id:
                # Check if refresh needed
                context_summary = self._check_context_window_manual(session_id)
                if context_summary:
                    # Session was refreshed, prepend summary
                    prompt = f"""[CONTEXT FROM PREVIOUS SESSION]
{context_summary}

[CURRENT TASK]
{prompt}
"""
                    logger.info(f"SESSION REFRESH: summary_chars={len(context_summary):,}")

        # Send prompt
        response = self.agent.send_prompt(prompt, context)

        # Update token tracking
        if hasattr(self.agent, 'get_last_metadata'):
            metadata = self.agent.get_last_metadata()
            if metadata and metadata.get('session_id'):
                # Add tokens to cumulative tracking
                tokens_dict = {
                    'input_tokens': metadata.get('input_tokens', 0),
                    'cache_creation_tokens': metadata.get('cache_creation_tokens', 0),
                    'cache_read_tokens': metadata.get('cache_read_tokens', 0),
                    'output_tokens': metadata.get('output_tokens', 0)
                }
                tokens_dict['total_tokens'] = sum(tokens_dict.values())

                self.state_manager.add_session_tokens(
                    session_id=metadata['session_id'],
                    task_id=task.id,
                    tokens_dict=tokens_dict
                )
```

### Session Refresh Mechanism

**File:** `src/orchestrator.py`

```python
def _refresh_session_with_summary(self) -> Tuple[str, str]:
    """Refresh session before hitting context limit.

    Returns:
        (new_session_id, context_summary)
    """
    # Get old session
    old_session_id = self.agent.session_id
    milestone_id = self._current_milestone_id

    # Generate summary using Qwen
    summary = self._generate_session_summary(old_session_id, milestone_id)

    # Create new session
    new_session_id = str(uuid.uuid4())
    self.agent.session_id = new_session_id

    # Create database record
    old_session = self.state_manager.get_session_record(old_session_id)
    project_id = old_session.project_id

    self.state_manager.create_session_record(
        session_id=new_session_id,
        project_id=project_id,
        milestone_id=milestone_id
    )

    # Mark old session as 'refreshed'
    old_session.status = 'refreshed'
    old_session.ended_at = datetime.now(UTC)
    old_session.summary = summary

    logger.info(
        f"Session refreshed: {old_session_id[:8]}... → {new_session_id[:8]}... "
        f"(summary: {len(summary)} chars)"
    )

    return (new_session_id, summary)
```

---

## Session Management

### Session Lifecycle Methods

**File:** `src/orchestrator.py`

#### Start Milestone Session

```python
def _start_milestone_session(
    self,
    project_id: int,
    milestone_id: Optional[int] = None
) -> str:
    """Start new session for milestone execution."""
    # Generate session ID
    session_id = str(uuid.uuid4())

    # Create database record
    self.state_manager.create_session_record(
        session_id=session_id,
        project_id=project_id,
        milestone_id=milestone_id
    )

    # Configure agent
    if hasattr(self.agent, 'session_id'):
        self.agent.session_id = session_id
        self.agent.use_session_persistence = True

    logger.info(f"SESSION START: session_id={session_id[:8]}...")
    return session_id
```

#### End Milestone Session

```python
def _end_milestone_session(
    self,
    session_id: str,
    milestone_id: Optional[int] = None
) -> None:
    """End session and save summary."""
    try:
        # Generate summary
        summary = self._generate_session_summary(session_id, milestone_id)

        # Save to database
        self.state_manager.save_session_summary(session_id, summary)

        # Mark complete
        self.state_manager.complete_session_record(
            session_id=session_id,
            ended_at=datetime.now(UTC)
        )

        logger.info(f"SESSION END: session_id={session_id[:8]}..., summary_chars={len(summary):,}")

    except Exception as e:
        logger.error(f"SESSION END ERROR: {e}")
        # Mark abandoned
        session = self.state_manager.get_session_record(session_id)
        if session:
            session.status = 'abandoned'
```

#### Build Milestone Context

```python
def _build_milestone_context(
    self,
    project_id: int,
    milestone_id: Optional[int] = None
) -> str:
    """Build context for milestone including workplan and previous summary."""
    context_parts = []

    # Project info
    project = self.state_manager.get_project(project_id)
    context_parts.append(f"# Project: {project.project_name}")
    context_parts.append(f"Working Directory: {project.working_directory}")
    context_parts.append("")

    # Previous milestone summary
    if milestone_id and milestone_id > 1:
        prev_session = self.state_manager.get_latest_session_for_milestone(milestone_id - 1)
        if prev_session and prev_session.summary:
            context_parts.append("## Previous Milestone Summary")
            context_parts.append(prev_session.summary)
            context_parts.append("")

    # Current milestone
    if milestone_id:
        context_parts.append(f"## Current Milestone: {milestone_id}")
        context_parts.append("")

    return "\n".join(context_parts)
```

### Session Summary Generation with Qwen

```python
def _generate_session_summary(
    self,
    session_id: str,
    milestone_id: Optional[int] = None
) -> str:
    """Generate summary using Qwen (local LLM)."""
    # Get session interactions
    session_record = self.state_manager.get_session_record(session_id)
    interactions = self.state_manager.get_interactions(
        project_id=session_record.project_id,
        limit=100
    )

    # Filter by session_id
    session_interactions = [
        i for i in interactions
        if i.metadata.get('session_id') == session_id
    ]

    # Build context for summarization
    context_parts = []
    for i, interaction in enumerate(session_interactions[:20], 1):
        context_parts.append(f"### Interaction {i}")
        context_parts.append(f"**Prompt**: {interaction.prompt[:500]}...")
        context_parts.append(f"**Response**: {interaction.response[:1000]}...")
        context_parts.append("")

    context_text = "\n".join(context_parts)

    # Generate summary
    summary_prompt = f"""Generate a concise summary focusing on:
1. What was accomplished
2. Implementation decisions
3. Current codebase state
4. Issues encountered
5. Next steps

## Session Data
{context_text}

Target 500-1000 tokens, MAX 1200 tokens.
"""

    summary = self.llm_interface.generate(
        prompt=summary_prompt,
        temperature=0.3,  # Low for consistency
        max_tokens=1500
    )

    return summary
```

### Database Schema (Sessions Table)

**File:** `src/core/models.py`

```python
class Session(Base):
    """Session record for milestone execution.

    Tracks Claude Code sessions across milestone tasks.
    """
    __tablename__ = 'sessions'

    # Primary key
    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, nullable=False, index=True)

    # Foreign keys
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    milestone_id = Column(Integer, nullable=True)  # Optional

    # Timestamps
    started_at = Column(DateTime, default=datetime.now, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    # Status
    status = Column(String, default='active')  # active, completed, abandoned, refreshed

    # Usage metrics
    total_tokens = Column(Integer, default=0)
    total_turns = Column(Integer, default=0)
    total_cost_usd = Column(Float, default=0.0)

    # Summary
    summary = Column(Text, nullable=True)

    # Relationships
    project = relationship('ProjectState', back_populates='sessions')
```

---

## Testing Approach

### Unit Tests for MaxTurnsCalculator

**File:** `tests/test_max_turns_calculator.py` (31 tests, 100% coverage)

```python
class TestMaxTurnsCalculator:
    def test_simple_task(self):
        """Test simple task gets min turns."""
        calc = MaxTurnsCalculator()
        task = {
            'id': 1,
            'title': 'Fix typo',
            'description': 'Fix typo in README',
            'estimated_files': 1,
            'estimated_loc': 10
        }
        assert calc.calculate(task) == 3  # Simple

    def test_complex_task(self):
        """Test complex task gets more turns."""
        calc = MaxTurnsCalculator()
        task = {
            'id': 2,
            'title': 'Refactor authentication',
            'description': 'Implement comprehensive refactor...',
            'estimated_files': 8,
            'estimated_loc': 600
        }
        assert calc.calculate(task) == 20  # Very complex

    def test_task_type_override(self):
        """Test task type overrides complexity."""
        calc = MaxTurnsCalculator()
        task = {
            'id': 3,
            'task_type': 'debugging',  # ← Override
            'estimated_files': 1,  # Would be simple
            'estimated_loc': 50
        }
        assert calc.calculate(task) == 20  # From task_type

    def test_bounds_enforcement(self):
        """Test bounds are enforced."""
        calc = MaxTurnsCalculator(config={'min': 5, 'max': 25})

        # Test min bound
        task_simple = {'id': 1, 'estimated_files': 1}
        assert calc.calculate(task_simple) >= 5

        # Test max bound
        task_complex = {'id': 2, 'estimated_loc': 10000}
        assert calc.calculate(task_complex) <= 25
```

### Integration Tests for Retry Logic

**File:** `tests/test_integration_e2e.py`

```python
@pytest.mark.integration
def test_max_turns_retry(orchestrator, mock_agent):
    """Test auto-retry when max_turns exceeded."""
    # Configure mock to fail first time
    mock_agent.fail_with_max_turns = True
    mock_agent.fail_count = 1

    # Execute task
    result = orchestrator.execute_task(task_id=1)

    # Verify retry happened
    assert result['status'] == 'completed'
    assert mock_agent.call_count == 2  # Initial + 1 retry
```

### Configuration Validation Tests

**File:** `tests/test_config_validation_comprehensive.py` (28 tests)

```python
class TestConfigValidation:
    def test_context_thresholds_valid(self):
        """Test valid context thresholds pass."""
        config = Config.load(defaults_only=True)
        config.set('context.thresholds.warning', 0.70)
        config.set('context.thresholds.refresh', 0.80)
        config.set('context.thresholds.critical', 0.95)
        assert config.validate()

    def test_context_thresholds_invalid_order(self):
        """Test invalid threshold order fails."""
        config = Config.load(defaults_only=True)
        config.set('context.thresholds.warning', 0.90)  # Too high
        config.set('context.thresholds.refresh', 0.80)
        config.set('context.thresholds.critical', 0.95)

        with pytest.raises(ConfigValidationException) as exc:
            config.validate()
        assert 'warning < refresh < critical' in str(exc.value)

    def test_max_turns_bounds(self):
        """Test max_turns bounds validation."""
        config = Config.load(defaults_only=True)
        config.set('orchestration.max_turns.min', 2)  # Too low

        with pytest.raises(ConfigValidationException) as exc:
            config.validate()
        assert 'min' in str(exc.value)
        assert '>= 3' in str(exc.value)
```

### Test Fixtures and Mocking Strategies

**File:** `tests/conftest.py`

```python
@pytest.fixture
def mock_max_turns_calculator():
    """Mock MaxTurnsCalculator for testing."""
    class MockCalculator:
        def __init__(self):
            self.call_count = 0
            self.last_task = None

        def calculate(self, task: Dict) -> int:
            self.call_count += 1
            self.last_task = task
            return 10  # Default

    return MockCalculator()

@pytest.fixture
def mock_agent_with_max_turns():
    """Mock agent that respects max_turns."""
    class MockAgent:
        def __init__(self):
            self.max_turns_used = None
            self.turn_count = 0

        def send_prompt(self, prompt, context=None):
            self.max_turns_used = context.get('max_turns')
            self.turn_count += 1

            # Simulate error_max_turns
            if self.turn_count >= self.max_turns_used:
                raise AgentException(
                    "Max turns exceeded",
                    context={'subtype': 'error_max_turns'}
                )

            return "Response"

    return MockAgent()
```

---

## Code Structure

### Key Files and Roles

```
src/
├── orchestrator.py                         # Main orchestration loop
│   ├── execute_milestone()                 # Milestone execution
│   ├── execute_task()                      # Task execution + retry
│   ├── _execute_single_task()              # Single task iteration
│   ├── _start_milestone_session()          # Session start
│   ├── _end_milestone_session()            # Session end
│   ├── _build_milestone_context()          # Context building
│   ├── _generate_session_summary()         # Summary generation
│   ├── _refresh_session_with_summary()     # Session refresh
│   └── _check_context_window_manual()      # Context window check
│
├── orchestration/
│   └── max_turns_calculator.py             # Adaptive max_turns
│       ├── calculate()                     # Main calculation
│       └── _bound()                        # Bounds enforcement
│
├── agents/
│   └── claude_code_local.py                # Headless agent
│       ├── send_prompt()                   # Execute Claude Code
│       ├── _run_claude()                   # Subprocess execution
│       ├── _extract_metadata()             # Parse JSON response
│       └── get_last_metadata()             # Retrieve metadata
│
├── core/
│   ├── config.py                           # Configuration management
│   │   ├── validate()                      # Main validation
│   │   ├── _validate_context_thresholds()
│   │   ├── _validate_max_turns()
│   │   └── _validate_timeouts()
│   │
│   ├── state.py                            # State management
│   │   ├── add_session_tokens()            # Token tracking
│   │   ├── get_session_token_usage()       # Usage retrieval
│   │   ├── create_session_record()
│   │   ├── get_session_record()
│   │   └── save_session_summary()
│   │
│   └── models.py                           # Database models
│       ├── Session                         # Session record
│       └── ContextWindowUsage              # Token usage tracking
│
└── llm/
    └── local_interface.py                  # Qwen interface
        └── generate()                      # Summary generation
```

### Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ USER REQUEST: Execute Milestone                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Orchestrator.execute_milestone(project_id, task_ids, milestone) │
├─────────────────────────────────────────────────────────────────┤
│ 1. _start_milestone_session() → session_id                      │
│ 2. _build_milestone_context() → context_text                    │
│ 3. Loop through tasks:                                          │
│    ├─ execute_task(task_id)                                     │
│    │   ├─ MaxTurnsCalculator.calculate() → max_turns           │
│    │   ├─ Retry loop (max_retries)                             │
│    │   │   ├─ _execute_single_task()                           │
│    │   │   │   ├─ Iteration loop (max_iterations)              │
│    │   │   │   │   ├─ _check_context_window_manual()           │
│    │   │   │   │   │   ├─ get_session_token_usage()            │
│    │   │   │   │   │   └─ [Refresh?] _refresh_session_summary()│
│    │   │   │   │   ├─ agent.send_prompt(prompt, context)       │
│    │   │   │   │   │   ├─ _run_claude() with max_turns         │
│    │   │   │   │   │   └─ _extract_metadata() → tokens, turns  │
│    │   │   │   │   ├─ add_session_tokens() → track usage       │
│    │   │   │   │   ├─ ResponseValidator.validate()             │
│    │   │   │   │   ├─ QualityController.validate_output()      │
│    │   │   │   │   ├─ ConfidenceScorer.score_response()        │
│    │   │   │   │   └─ DecisionEngine.decide_next_action()      │
│    │   │   └─ [Error?] Check subtype=error_max_turns           │
│    │   │       └─ [Retry] max_turns *= retry_multiplier        │
│    └─ Store result                                              │
│ 4. _end_milestone_session()                                     │
│    ├─ _generate_session_summary() (via Qwen)                   │
│    └─ save_session_summary()                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ RESULT: {milestone_id, session_id, tasks_completed, results}    │
└─────────────────────────────────────────────────────────────────┘
```

### Interaction Between Components

```
┌──────────────────┐
│  Orchestrator    │
└────────┬─────────┘
         │
         ├─────────────────────────────────────────────────┐
         │                                                  │
         ↓                                                  ↓
┌────────────────────┐                          ┌──────────────────────┐
│ MaxTurnsCalculator │                          │ ClaudeCodeLocalAgent │
│                    │                          │                      │
│ calculate(task)    │                          │ send_prompt(prompt)  │
│  → max_turns       │                          │  → response          │
└────────────────────┘                          │  → metadata          │
                                                 └──────────────────────┘
                                                            │
         ┌──────────────────────────────────────────────────┤
         │                                                  │
         ↓                                                  ↓
┌─────────────────┐                            ┌──────────────────────┐
│  StateManager   │                            │   LocalLLMInterface  │
│                 │                            │                      │
│ Session Methods │                            │ generate(summary)    │
│ Token Tracking  │                            │  → summary_text      │
└─────────────────┘                            └──────────────────────┘
```

---

## Further Reading

- [SESSION_MANAGEMENT_GUIDE.md](../guides/SESSION_MANAGEMENT_GUIDE.md) - User-facing guide
- [ADR-007-headless-mode-enhancements.md](../decisions/ADR-007-headless-mode-enhancements.md) - Architecture decisions
- [claude-code-headless-guide.md](../research/claude-code-headless-guide.md) - Headless mode research
- [claude-code-max-turns-guide.md](../research/claude-code-max-turns-guide.md) - Max turns guidance
- [HEADLESS_MODE_GAP_ANALYSIS.md](HEADLESS_MODE_GAP_ANALYSIS.md) - Gap analysis (Phase 1-3)

---

**Last Updated:** 2025-11-04
**Version:** v1.1 (Phase 4 + 5 Complete)
**Author:** Obra Development Team
