# ADR-008: Retry Logic with Exponential Backoff

**Status:** Accepted

**Date:** 2025-11-04

**Deciders:** Obra Development Team

**Context Owner:** Omar (@Omar-Unpossible)

---

## Context

Obra's current implementation (M0-M8) lacks graceful handling of transient failures when communicating with external services:

1. **No retry mechanism** - Single failure terminates entire task
2. **Transient failures treated as permanent** - Rate limits, timeouts, network glitches abort work
3. **Resource waste** - Long-running tasks fail at end due to temporary issues
4. **Poor user experience** - Users must manually retry failed tasks
5. **No backoff strategy** - Immediate retry would trigger same failure

These limitations cause:
- Task failures from temporary Claude API rate limits
- Orchestration interruptions from brief network issues
- Ollama timeouts during heavy GPU load
- Lost work from transient SSH connectivity problems
- Cascading failures in multi-task workflows

**Real-World Impact:**
- 20-turn task fails at turn 18 due to 30-second network timeout
- Overnight workflow stops due to temporary rate limit
- Multi-hour refactoring lost due to brief SSH disconnect

**Requirements:**
- ✓ Distinguish retryable vs non-retryable errors
- ✓ Exponential backoff prevents thundering herd
- ✓ Configurable retry limits and delays
- ✓ Jitter prevents synchronized retry storms
- ✓ Transparent logging of retry attempts
- ✓ Integration with agent and LLM calls
- ✓ Preserve task state across retries

---

## Decision

We will implement a **RetryManager** with exponential backoff and intelligent error classification for all external service calls.

### Core Components

#### 1. RetryManager Class

**Purpose:** Central retry logic with exponential backoff calculation.

```python
class RetryManager:
    """Manages retry logic with exponential backoff."""

    def __init__(self, config: dict):
        self.max_retries = config.get('max_retries', 3)
        self.base_delay = config.get('base_delay', 1.0)
        self.max_delay = config.get('max_delay', 60.0)
        self.backoff_factor = config.get('backoff_factor', 2.0)
        self.jitter = config.get('jitter', True)
        self.retryable_errors = config.get('retryable_errors', [])

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        error_context: Optional[Dict] = None,
        **kwargs
    ) -> Any:
        """Execute function with retry logic."""
        attempt = 0
        last_exception = None

        while attempt <= self.max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if not self.is_retryable(e):
                    raise

                if attempt >= self.max_retries:
                    raise

                delay = self._calculate_delay(attempt)
                time.sleep(delay)
                attempt += 1

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with optional jitter."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            delay *= (0.5 + random.random())

        return delay

    def is_retryable(self, error: Exception) -> bool:
        """Determine if error is retryable."""
        # Implementation details...
```

#### 2. Error Classification

**Retryable Errors:**
- Rate limits (429, "too many requests")
- Timeouts (TimeoutError, subprocess.TimeoutExpired)
- Network issues (ConnectionError, BrokenPipeError)
- Service unavailable (503)
- Temporary failures

**Non-Retryable Errors:**
- Authentication (401, AuthenticationError)
- Authorization (403, PermissionError)
- Not found (404)
- Validation (ValueError, SyntaxError)
- Configuration (TypeError, KeyError)

#### 3. Integration Points

**Agent Calls:**
```python
def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    retry_manager = RetryManager(self.config.get('retry', {}))
    
    return retry_manager.execute_with_retry(
        func=self._execute_claude_code,
        prompt=prompt,
        context=context,
        error_context={'agent': 'claude_code_local', 'task_id': context.get('task_id')}
    )
```

**LLM Calls:**
```python
def send_prompt(self, prompt: str, context: Optional[dict] = None) -> str:
    retry_manager = RetryManager(self.config.get('retry', {}))
    
    return retry_manager.execute_with_retry(
        func=self._call_ollama_api,
        prompt=prompt,
        model=self.model,
        error_context={'llm': 'ollama', 'model': self.model}
    )
```

#### 4. Configuration

```yaml
retry:
  enabled: true
  max_retries: 3  # Total attempts = 4 (initial + 3 retries)
  base_delay: 1.0  # Initial delay in seconds
  max_delay: 60.0  # Maximum delay cap
  backoff_factor: 2.0  # Exponential factor
  jitter: true  # Add randomness

  retryable_errors:
    - RateLimitError
    - TimeoutError
    - NetworkError
```

**Delay Progression:**
- Attempt 1: 1.0s ± 50% = 0.5-1.5s
- Attempt 2: 2.0s ± 50% = 1.0-3.0s
- Attempt 3: 4.0s ± 50% = 2.0-6.0s

---

## Alternatives Considered

### Alternative 1: Fixed Delay Retry
- ❌ No backoff = thundering herd problem
- ❌ Wastes time or insufficient for recovery
- **Outcome:** Exponential backoff distributes load

### Alternative 2: Infinite Retries with Circuit Breaker
- ❌ Too complex for current needs
- ❌ Can hang orchestrator indefinitely
- **Outcome:** Fixed limit (3 retries) is sufficient

### Alternative 3: Retry at Orchestrator Level Only
- ❌ Doesn't handle LLM failures
- ❌ Retries entire task (wasteful)
- **Outcome:** Retry at call level for granularity

### Alternative 4: No Jitter
- ❌ Synchronized retries overwhelm services
- ❌ Thundering herd when multiple tasks fail
- **Outcome:** Jitter prevents synchronized storms

---

## Consequences

### Positive Consequences

1. **Graceful Transient Failure Handling**
   - ✅ Rate limits: Automatic backoff
   - ✅ Network glitches: Brief retry succeeds
   - ✅ Preserves long-running work

2. **Prevents Thundering Herd**
   - ✅ Exponential backoff spreads retries
   - ✅ Jitter prevents synchronization
   - ✅ Better for Claude API rate limits

3. **Intelligent Error Classification**
   - ✅ Non-retryable errors fail fast
   - ✅ Retryable errors get attempts
   - ✅ Configurable per deployment

4. **Transparent and Debuggable**
   - ✅ All retries logged
   - ✅ Retry history in database
   - ✅ Clear error messages

### Negative Consequences

1. **Increased Task Duration**
   - ⚠️ Retries add delay (max 7s for 3 retries)
   - ✅ **Mitigation:** Limited to 3 retries

2. **Token Usage Increase**
   - ⚠️ Retried calls consume tokens
   - ✅ **Mitigation:** Retry only failed calls, not full tasks

3. **Complexity in Error Handling**
   - ⚠️ Need to classify errors
   - ✅ **Mitigation:** Sensible defaults

4. **Potential for Masking Issues**
   - ⚠️ Intermittent errors hidden
   - ✅ **Mitigation:** Log all retries with warnings

---

## Implementation Details

### Phase 3: Retry Logic (Day 3 of M9)

**Files to Create:**
- `src/utils/retry_manager.py` (150 lines)
- `tests/test_retry_manager.py` (90 tests)

**Files to Modify:**
- `src/agents/claude_code_local.py` (+30 lines)
- `src/agents/claude_code_ssh.py` (+30 lines)
- `src/llm/ollama_interface.py` (+20 lines)
- `src/core/exceptions.py` (+40 lines)
- `config/default_config.yaml` (+15 lines)

**Test Coverage:** ≥90%

---

## References

### Internal Documentation
- [M9_IMPLEMENTATION_PLAN.md](../development/M9_IMPLEMENTATION_PLAN.md)
- [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)
- [ADR-007: Headless Mode Enhancements](ADR-007-headless-mode-enhancements.md)

### External References
- [AWS: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Anthropic API: Rate Limits](https://docs.anthropic.com/en/api/rate-limits)

---

## Related ADRs

- [ADR-007: Headless Mode Enhancements](ADR-007-headless-mode-enhancements.md)
- [ADR-004: Local Agent Architecture](ADR-004-local-agent-architecture.md)
- [003: State Management](003_state_management.md)

---

**Last Updated:** 2025-11-04
**Version:** 1.0
**Status:** Accepted
**Implementation:** Planned for M9 Phase 3 (Day 3)
