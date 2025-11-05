# Headless Mode Gap Analysis & Recommendations

**Date**: 2025-11-03
**Version**: v1.2 (Post-PHASE_6)
**Status**: CRITICAL GAPS IDENTIFIED

---

## Executive Summary

After comparing Obra's implementation with the comprehensive Claude Code headless guide, we've identified **3 CRITICAL gaps** and several important enhancements needed for production readiness.

**Most Critical Issue**: **Context window management is completely missing**. If we enable session persistence, Obra will hit the token limit and fail unexpectedly. We need immediate implementation of token tracking and session refresh logic.

---

## Gap Analysis

### ✅ What We Have (Implemented)

| Feature | Status | Implementation |
|---------|--------|----------------|
| Headless Mode | ✅ Complete | `--print` flag in ClaudeCodeLocalAgent |
| Session ID Support | ✅ Partial | `--session-id` flag, but disabled by default |
| Dangerous Mode | ✅ Complete | `--dangerously-skip-permissions` for automation |
| Retry Logic | ✅ Complete | 5 retries with exponential backoff (2s → 3s → 4.5s...) |
| Timeout Handling | ✅ Complete | Configurable `response_timeout` (default 60s) |
| Fresh Sessions | ✅ Complete | `use_session_persistence: false` by default |

### ❌ Critical Gaps (Must Fix)

#### 1. ❌ JSON Output Mode (CRITICAL)

**Current State**:
```python
# We use --print and get plain text
args = ['--print', '--session-id', session_id]
result = subprocess.run(command, capture_output=True, text=True)
return result.stdout  # Plain text, manually parsed
```

**Should Be**:
```python
# Use --output-format json for structured responses
args = ['--print', '--session-id', session_id, '--output-format', 'json']
result = subprocess.run(command, capture_output=True, text=True)
response = json.loads(result.stdout)  # Structured data
```

**What We're Missing**:
- ❌ Token usage breakdown (input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens)
- ❌ Cost tracking (`total_cost_usd`)
- ❌ Session ID in response (for verification)
- ❌ Duration metrics (`duration_ms`, `duration_api_ms`)
- ❌ Error subtypes (`error_max_turns`, `error_permission_denied`, `error_timeout`)
- ❌ Number of turns (`num_turns`)
- ❌ Structured result content

**Impact**:
- **Cannot track token usage** → Can't detect approaching context limit
- **No structured error handling** → All errors look the same
- **Manual parsing required** → Fragile, regex-based extraction
- **No cost visibility** → Can't monitor spending (even on subscription, good to know)

**Recommendation**: **IMPLEMENT IMMEDIATELY** - This is foundational for context management.

---

#### 2. ❌ Context Window Management (CRITICAL - USER'S TOP CONCERN)

**Current State**:
- ✅ We have `TokenCounter` utility (uses tiktoken)
- ✅ We can count tokens in individual prompts/responses
- ❌ We do NOT track cumulative tokens across session
- ❌ We do NOT have threshold warnings
- ❌ We do NOT have session refresh logic

**User's Specific Request**:
> "management of context is critical if we are using the sessionID to carry over context; Obra needs to be able to refresh the context window with a new sessionID before the max is hit because headless mode will fail at the limit, and we want to compact / carry over context to a fresh window before we run out of room"

**The Problem**:
```
Claude Pro has ~28M token context window limit.

Without Management:
Task 1: 5M tokens → Session total: 5M  ✅
Task 2: 8M tokens → Session total: 13M ✅
Task 3: 10M tokens → Session total: 23M ✅
Task 4: 7M tokens → Session total: 30M ❌ FAIL! (exceeds limit)
                    → Claude Code headless mode crashes
                    → Obra orchestration fails
                    → User has to manually intervene
```

**What We Need**:

**A. Token Tracking in StateManager**
```python
# Add to ComplexityEstimate or new ContextWindowUsage model
class ContextWindowUsage:
    task_id: int
    session_id: str
    cumulative_tokens: int  # Running total
    input_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    output_tokens: int
    timestamp: datetime
```

**B. Threshold Logic in Orchestrator**
```python
# Before each task execution
current_tokens = state_manager.get_session_token_usage(session_id)
limit = 28_000_000  # Claude Pro limit
threshold_warning = limit * 0.75  # 21M tokens (75%)
threshold_critical = limit * 0.90  # 25.2M tokens (90%)

if current_tokens > threshold_critical:
    # CRITICAL: Must refresh session
    logger.warning(f"Context window at {current_tokens/limit:.0%} - refreshing session")
    new_session_id = refresh_session_with_context_summary()
elif current_tokens > threshold_warning:
    # WARNING: Approaching limit
    logger.warning(f"Context window at {current_tokens/limit:.0%} - consider refresh soon")
```

**C. Session Refresh Mechanism**
```python
def refresh_session_with_context_summary(orchestrator):
    """Refresh session before hitting context limit.

    Process:
    1. Generate summary of current session context using LLM
    2. Start new Claude session with fresh context window
    3. Provide summary as initial context in new session
    4. Continue work in refreshed session
    """
    # 1. Get current session context
    current_context = orchestrator.context_manager.build_context()

    # 2. Summarize using Qwen (local LLM)
    summary_prompt = f"""
    Summarize the following task context for continuation in a new session.
    Focus on:
    - What has been accomplished so far
    - Current state of the codebase
    - Next steps and pending tasks
    - Important decisions and constraints

    Context: {current_context}
    """
    summary = orchestrator.llm.send_prompt(summary_prompt)

    # 3. Start fresh session with summary
    new_session_id = str(uuid.uuid4())
    orchestrator.agent.session_id = new_session_id

    # 4. Reset token counter for new session
    state_manager.reset_session_tokens(new_session_id)

    # 5. Return summary to prepend to next prompt
    return new_session_id, summary
```

**Recommendation**: **IMPLEMENT IMMEDIATELY** - Without this, session persistence is dangerous.

---

#### 3. ❌ Max Turns Limit

**Current State**:
- We have `timeout` to kill long-running processes
- We do NOT limit conversation turns

**Should Have**:
```python
args = ['--print', '--session-id', session_id, '--max-turns', '5']
```

**Why This Matters**:
- Prevents runaway execution (infinite tool use loops)
- Controls costs (even on subscription, good practice)
- Fail-safe mechanism for unexpected behavior
- Helps detect when Claude is stuck

**Example**:
```
Without max_turns:
Task: "Fix all linting issues"
Turn 1: Read file, find 100 issues
Turn 2: Fix 20 issues
Turn 3: Fix 20 more
Turn 4: Fix 20 more
...
Turn 10: Still fixing
Turn 20: Still fixing (stuck in loop)
→ Runs until timeout (5 minutes)
→ Wastes time and tokens

With max_turns=5:
Turn 1: Read file, find 100 issues
Turn 2: Fix 20 issues
Turn 3: Fix 20 more
Turn 4: Fix 20 more
Turn 5: Fix final batch
→ Stops at 5 turns
→ Predictable behavior
→ If incomplete, Obra can decide to retry or break
```

**Recommendation**: **IMPLEMENT SOON** - Important safety feature.

---

### ⚠️ Important Gaps (Should Fix)

#### 4. ⚠️ Allowed Tools Configuration

**Current State**:
```python
# We use --dangerously-skip-permissions
# This auto-accepts ALL tools
args.append('--dangerously-skip-permissions')
```

**Better Approach**:
```python
# Use --allowedTools for fine-grained control
allowed_tools = ['Read', 'Write', 'Edit', 'Grep', 'Glob']  # No Bash without review
args.extend(['--allowedTools', ','.join(allowed_tools)])
```

**Why**:
- More secure (don't auto-accept Bash commands)
- Fine-grained control per task type
- Validation tasks: Read/Grep only
- Code generation tasks: Read/Write/Edit
- Dangerous tasks: All tools

**Recommendation**: **IMPLEMENT LATER** - Enhancement, not critical.

---

#### 5. ⚠️ Stream JSON for Long Operations

**Current State**:
```python
# Blocking subprocess.run() - wait until complete
result = subprocess.run(command, capture_output=True, timeout=300)
```

**Better for Long Tasks**:
```python
# Stream JSON for real-time progress
args.extend(['--output-format', 'stream-json'])
process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)

for line in iter(process.stdout.readline, ''):
    event = json.loads(line)
    if event['type'] == 'assistant':
        # Show progress in real-time
        logger.info(f"Progress: {event['message']['content'][0]['text']}")
```

**Why**:
- See progress during long operations
- Can cancel early if going wrong direction
- Better user feedback (orchestrator knows Claude is working)
- Can update task status in real-time

**Recommendation**: **IMPLEMENT LATER** - Nice enhancement for UX.

---

## Detailed Recommendations

### Priority 1: CRITICAL (Implement Immediately)

#### A. JSON Output Mode

**Files to Modify**:
1. `src/agents/claude_code_local.py`:
   - Change `send_prompt()` to add `--output-format json`
   - Parse JSON response instead of plain text
   - Extract structured fields (tokens, session_id, cost, errors)
   - Update return type to include metadata

2. `src/agents/output_monitor.py`:
   - Update to handle JSON responses (or deprecate if not needed)

3. `src/core/models.py`:
   - Add `AgentResponse` fields for token breakdown:
     ```python
     @dataclass
     class AgentResponse:
         task_id: int
         content: str
         status: str = 'success'
         metadata: Optional[Dict[str, Any]] = None

         # NEW: Token usage breakdown
         input_tokens: int = 0
         cache_creation_tokens: int = 0
         cache_read_tokens: int = 0
         output_tokens: int = 0
         total_tokens: int = 0

         # NEW: Performance metrics
         duration_ms: int = 0
         duration_api_ms: int = 0
         num_turns: int = 0

         # NEW: Cost tracking (optional)
         cost_usd: float = 0.0
     ```

**Implementation Steps**:
```python
# 1. Update send_prompt() in claude_code_local.py
def send_prompt(self, prompt: str, context: Optional[Dict] = None) -> str:
    # Build args with JSON output
    args = ['--print', '--session-id', session_id, '--output-format', 'json']

    if self.bypass_permissions:
        args.append('--dangerously-skip-permissions')

    args.append(prompt)

    # Run command
    result = self._run_command(args)

    # Parse JSON response
    response = json.loads(result.stdout)

    # Check for errors
    if response.get('is_error'):
        error_msg = response.get('error_message', 'Unknown error')
        subtype = response.get('subtype', '')
        raise AgentException(
            f'Claude Code failed: {error_msg}',
            context={'subtype': subtype, 'response': response}
        )

    # Extract text content
    content = response['result']['content'][0]['text']

    # Store metadata for token tracking (return via context or store in instance)
    self._last_response_metadata = {
        'session_id': response.get('session_id'),
        'usage': response.get('usage', {}),
        'cost_usd': response.get('total_cost_usd', 0.0),
        'num_turns': response.get('num_turns', 0),
        'duration_ms': response.get('duration_ms', 0)
    }

    return content

# 2. Update execute_task() to include metadata in AgentResponse
def execute_task(self, task_id: int, task: Dict[str, Any], context: Optional[Dict] = None) -> Dict[str, Any]:
    # Send prompt
    response_text = self.send_prompt(prompt_text, context)

    # Build AgentResponse with metadata
    metadata = self._last_response_metadata or {}
    usage = metadata.get('usage', {})

    agent_response = AgentResponse(
        task_id=task_id,
        content=response_text,
        status='success',
        metadata=metadata,
        # Token breakdown
        input_tokens=usage.get('input_tokens', 0),
        cache_creation_tokens=usage.get('cache_creation_input_tokens', 0),
        cache_read_tokens=usage.get('cache_read_input_tokens', 0),
        output_tokens=usage.get('output_tokens', 0),
        total_tokens=(
            usage.get('input_tokens', 0) +
            usage.get('cache_creation_input_tokens', 0) +
            usage.get('cache_read_input_tokens', 0) +
            usage.get('output_tokens', 0)
        ),
        # Performance metrics
        duration_ms=metadata.get('duration_ms', 0),
        duration_api_ms=metadata.get('duration_api_ms', 0),
        num_turns=metadata.get('num_turns', 0),
        cost_usd=metadata.get('cost_usd', 0.0)
    )

    return agent_response
```

**Testing**:
```python
# Test JSON parsing
def test_json_output_parsing():
    agent = ClaudeCodeLocalAgent()
    agent.initialize({'workspace_path': '/tmp/test'})

    response = agent.send_prompt("List files in current directory")

    # Check metadata was captured
    assert agent._last_response_metadata is not None
    assert 'usage' in agent._last_response_metadata
    assert 'session_id' in agent._last_response_metadata
```

---

#### B. Context Window Management

**Files to Modify**:
1. `src/core/models.py`:
   - Add `ContextWindowUsage` model for tracking cumulative tokens

2. `src/core/state.py`:
   - Add methods for token tracking:
     - `add_session_tokens(session_id, tokens)`
     - `get_session_token_usage(session_id)`
     - `reset_session_tokens(session_id)`

3. `src/orchestrator.py`:
   - Add `_check_context_window()` before task execution
   - Add `_refresh_session_with_summary()` for session refresh
   - Update `execute_task()` to track tokens

**Database Schema**:
```sql
CREATE TABLE context_window_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    task_id INTEGER,
    cumulative_tokens INTEGER NOT NULL,
    input_tokens INTEGER,
    cache_creation_tokens INTEGER,
    cache_read_tokens INTEGER,
    output_tokens INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

CREATE INDEX idx_session_tokens ON context_window_usage(session_id, timestamp);
```

**Implementation**:
```python
# 1. Add model
@dataclass
class ContextWindowUsage:
    """Tracks cumulative token usage for context window management."""
    id: Optional[int] = None
    session_id: str = ''
    task_id: Optional[int] = None
    cumulative_tokens: int = 0
    input_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    output_tokens: int = 0
    timestamp: Optional[datetime] = None

# 2. Add StateManager methods
class StateManager:
    def add_session_tokens(self, session_id: str, task_id: int, tokens: Dict[str, int]) -> None:
        """Add token usage to session cumulative total."""
        with self._lock:
            # Get current cumulative total
            current = self.get_session_token_usage(session_id)

            # Calculate new cumulative
            new_cumulative = current + tokens['total_tokens']

            # Store usage record
            usage = ContextWindowUsage(
                session_id=session_id,
                task_id=task_id,
                cumulative_tokens=new_cumulative,
                input_tokens=tokens['input_tokens'],
                cache_creation_tokens=tokens['cache_creation_tokens'],
                cache_read_tokens=tokens['cache_read_tokens'],
                output_tokens=tokens['output_tokens'],
                timestamp=datetime.now()
            )

            # Save to database
            self.session.add(usage)
            self.session.commit()

    def get_session_token_usage(self, session_id: str) -> int:
        """Get cumulative token usage for session."""
        with self._lock:
            latest = self.session.query(ContextWindowUsage)\
                .filter_by(session_id=session_id)\
                .order_by(ContextWindowUsage.timestamp.desc())\
                .first()

            return latest.cumulative_tokens if latest else 0

    def reset_session_tokens(self, session_id: str) -> None:
        """Reset token tracking for new session."""
        # Don't delete history, just start fresh count
        # Future queries will start from 0 with new session_id
        pass

# 3. Update Orchestrator
class Orchestrator:
    def _check_context_window(self, session_id: str) -> Optional[str]:
        """Check context window usage and refresh if needed.

        Returns:
            Optional[str]: Summary text if session was refreshed, None otherwise
        """
        CONTEXT_LIMIT = 28_000_000  # Claude Pro limit
        WARNING_THRESHOLD = CONTEXT_LIMIT * 0.75  # 21M tokens
        CRITICAL_THRESHOLD = CONTEXT_LIMIT * 0.90  # 25.2M tokens

        current_tokens = self.state_manager.get_session_token_usage(session_id)
        usage_pct = current_tokens / CONTEXT_LIMIT

        if current_tokens > CRITICAL_THRESHOLD:
            logger.warning(
                f'Context window CRITICAL: {current_tokens:,} tokens ({usage_pct:.0%}) - REFRESHING SESSION'
            )
            # Refresh session with context summary
            new_session_id, summary = self._refresh_session_with_summary()
            return summary

        elif current_tokens > WARNING_THRESHOLD:
            logger.warning(
                f'Context window WARNING: {current_tokens:,} tokens ({usage_pct:.0%}) - approaching limit'
            )

        return None

    def _refresh_session_with_summary(self) -> Tuple[str, str]:
        """Refresh Claude session before hitting context limit.

        Returns:
            Tuple[str, str]: (new_session_id, context_summary)
        """
        # 1. Build current context
        context = self.context_manager.build_context()

        # 2. Generate summary using Qwen (local LLM)
        summary_prompt = f'''
        The current Claude Code session is approaching the context window limit.
        Summarize the following context for continuation in a fresh session.

        Focus on:
        - What has been accomplished so far
        - Current state of the codebase/files
        - Pending tasks and next steps
        - Important decisions and constraints
        - Key patterns or insights discovered

        Keep the summary concise but complete (max 1000 tokens).

        CONTEXT:
        {context}
        '''

        summary = self.llm.send_prompt(summary_prompt)

        # 3. Generate new session ID
        new_session_id = str(uuid.uuid4())

        # 4. Update agent with new session
        self.agent.session_id = new_session_id

        # 5. Reset token counter (new session starts fresh)
        self.state_manager.reset_session_tokens(new_session_id)

        logger.info(f'Session refreshed: {new_session_id[:8]}... (context summarized)')

        return new_session_id, summary

    def execute_task(self, task_id: int, max_iterations: int = 10) -> Dict[str, Any]:
        """Execute task with context window management."""
        # ... existing code ...

        # CHECK CONTEXT WINDOW BEFORE EXECUTION
        if self.agent.use_session_persistence:
            session_id = self.agent.session_id or str(uuid.uuid4())
            context_summary = self._check_context_window(session_id)

            if context_summary:
                # Prepend summary to prompt
                enhanced_prompt = f'''
                [CONTEXT FROM PREVIOUS SESSION]
                {context_summary}

                [CURRENT TASK]
                {prompt}
                '''
                prompt = enhanced_prompt

        # Execute task
        agent_response = self.agent.execute_task(task_id, task_dict, context)

        # TRACK TOKENS AFTER EXECUTION
        if hasattr(agent_response, 'total_tokens') and agent_response.total_tokens > 0:
            self.state_manager.add_session_tokens(
                session_id=self.agent.session_id,
                task_id=task_id,
                tokens={
                    'total_tokens': agent_response.total_tokens,
                    'input_tokens': agent_response.input_tokens,
                    'cache_creation_tokens': agent_response.cache_creation_tokens,
                    'cache_read_tokens': agent_response.cache_read_tokens,
                    'output_tokens': agent_response.output_tokens
                }
            )

            logger.info(
                f'Session tokens: {self.state_manager.get_session_token_usage(self.agent.session_id):,}'
            )

        # ... rest of execute_task ...
```

**Configuration**:
```yaml
# config/config.yaml
agent:
  type: claude-code-local
  config:
    use_session_persistence: true  # Enable session continuity
    context_window_limit: 28000000  # Claude Pro limit
    context_warning_threshold: 0.75  # Warn at 75%
    context_critical_threshold: 0.90  # Refresh at 90%
```

---

### Priority 2: Important (Implement Soon)

#### C. Max Turns Limit

**Implementation**:
```python
# src/agents/claude_code_local.py
def send_prompt(self, prompt: str, context: Optional[Dict] = None, max_turns: Optional[int] = None) -> str:
    """Send prompt with optional max_turns limit."""
    args = ['--print', '--session-id', session_id, '--output-format', 'json']

    # Add max_turns if specified
    if max_turns:
        args.extend(['--max-turns', str(max_turns)])

    # ... rest of implementation
```

**Configuration**:
```yaml
agent:
  config:
    default_max_turns: 5  # Default limit for most tasks
    max_turns_by_type:
      validation: 2  # Validation tasks are quick
      code_generation: 5  # Code generation may need more turns
      error_analysis: 3  # Error analysis is moderate
```

---

## Migration Plan

### Phase 1: JSON Output (Week 1)
**Effort**: 8-12 hours

1. Update `ClaudeCodeLocalAgent.send_prompt()` to use `--output-format json`
2. Add JSON parsing and error handling
3. Update `AgentResponse` model with token fields
4. Update tests to verify JSON parsing
5. Test with real Claude Code CLI

**Deliverables**:
- ✅ JSON responses parsed correctly
- ✅ Token usage tracked per task
- ✅ Error subtypes handled

---

### Phase 2: Context Window Management (Week 2)
**Effort**: 16-20 hours

1. Create `ContextWindowUsage` model and database migration
2. Add StateManager token tracking methods
3. Implement `_check_context_window()` in Orchestrator
4. Implement `_refresh_session_with_summary()` in Orchestrator
5. Add configuration for thresholds
6. Add logging and monitoring
7. Write comprehensive tests

**Deliverables**:
- ✅ Cumulative token tracking working
- ✅ Warnings at 75% threshold
- ✅ Auto-refresh at 90% threshold
- ✅ Session summary generation
- ✅ Tests for threshold logic

---

### Phase 3: Max Turns & Enhancements (Week 3)
**Effort**: 4-6 hours

1. Add `max_turns` parameter support
2. Configure defaults per task type
3. Add tests for max_turns

**Deliverables**:
- ✅ Max turns limit enforced
- ✅ Configurable per task type

---

## Testing Plan

### Unit Tests

```python
# test_json_output.py
def test_json_output_parsing():
    """Test parsing of JSON responses from Claude Code."""
    agent = ClaudeCodeLocalAgent()
    # Mock subprocess to return JSON
    # Verify parsing extracts tokens, session_id, etc.

def test_json_error_handling():
    """Test handling of error responses in JSON format."""
    # Mock error response with subtype
    # Verify AgentException raised with correct subtype

# test_context_window.py
def test_token_tracking():
    """Test cumulative token tracking across tasks."""
    # Execute multiple tasks
    # Verify cumulative tokens increase correctly

def test_threshold_warning():
    """Test warning at 75% threshold."""
    # Set tokens to 21M
    # Verify warning logged

def test_threshold_critical_refresh():
    """Test auto-refresh at 90% threshold."""
    # Set tokens to 26M
    # Verify session refreshed
    # Verify summary generated

def test_session_summary_generation():
    """Test context summary for session refresh."""
    # Build complex context
    # Generate summary
    # Verify summary concise and complete
```

### Integration Tests

```python
# test_integration_context_window.py
def test_full_session_lifecycle():
    """Test complete session with context window management."""
    # Create orchestrator with session persistence
    # Execute tasks until approaching limit
    # Verify auto-refresh happens
    # Verify work continues in new session

def test_session_refresh_continuity():
    """Test that refreshed session maintains context."""
    # Execute task A
    # Fill context to 90%
    # Execute task B (should trigger refresh)
    # Verify task B has context from task A (via summary)
```

---

## Success Criteria

### Phase 1 (JSON Output)
- ✅ All Claude Code responses parsed as JSON
- ✅ Token usage tracked in AgentResponse
- ✅ Error subtypes properly handled
- ✅ Tests pass with 90%+ coverage

### Phase 2 (Context Window Management)
- ✅ Cumulative tokens tracked in database
- ✅ Warnings triggered at 75% threshold
- ✅ Auto-refresh triggered at 90% threshold
- ✅ Session summaries generated successfully
- ✅ Work continues seamlessly after refresh
- ✅ No context window errors in production

### Phase 3 (Max Turns)
- ✅ Max turns limit enforced
- ✅ Configurable per task type
- ✅ Runaway execution prevented

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| JSON parsing failures | High | Comprehensive error handling, fallback to text mode |
| Session refresh interrupts work | Medium | Generate detailed summaries, test continuity |
| False positive threshold triggers | Low | Tune thresholds based on real usage data |
| Summary generation fails | Medium | Fallback to starting fresh session without summary |
| Database migration issues | Medium | Create migration script, test in dev first |

---

## References

- **Claude Code Headless Guide**: `docs/research/claude-code-headless-guide.md`
- **Current Implementation**: `src/agents/claude_code_local.py`
- **StateManager**: `src/core/state.py`
- **Orchestrator**: `src/orchestrator.py`
- **CLAUDE.md**: Project guidelines

---

**Status**: READY FOR IMPLEMENTATION
**Priority**: CRITICAL (Blocks session persistence feature)
**Owner**: TBD
**Target Completion**: 3 weeks (Phases 1-3)
