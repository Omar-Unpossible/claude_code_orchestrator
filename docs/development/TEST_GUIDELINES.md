# Test Development Guidelines

**Purpose:** Prevent resource exhaustion and WSL2 crashes in test suites.

**Last Updated:** After M2 testing crisis (WSL2 crashes from resource exhaustion)

---

## Critical Rules (WSL2 Survival)

### 🚨 Rule #1: No Blocking Operations Without Mocking

**Problem:** Cumulative `time.sleep()` calls caused **75+ seconds** of blocking in a single test file.

**Solution:**
```python
# ❌ BAD - Blocks for 2.5 seconds per test
def test_completion():
    monitor.process("Ready")
    time.sleep(2.5)  # Cumulative across 30 tests = 75s!
    assert monitor.is_complete()

# ✅ GOOD - Use fast timeouts
def test_completion():
    monitor = OutputMonitor(completion_timeout=0.2)  # Fast timeout
    monitor.process("Ready")
    time.sleep(0.25)  # Just enough to exceed timeout
    assert monitor.is_complete()

# ✅ BETTER - Mock time entirely (use conftest.py fixture)
def test_completion(fast_time):
    monitor.process("Ready")
    time.sleep(2.0)  # Instant! Mocked by fast_time fixture
    assert monitor.is_complete()
```

**Limits:**
- ⚠️ **Maximum sleep per test:** 0.5s
- ⚠️ **Maximum cumulative sleep per file:** 5s total
- ✅ **Use `fast_time` fixture** from `conftest.py` for instant time advancement

---

### 🚨 Rule #2: Thread Limits and Mandatory Timeouts

**Problem:** 25+ threads across test suite without cleanup = WSL2 resource exhaustion.

**Solution:**
```python
# ❌ BAD - Too many threads, no timeout, no error handling
def test_concurrent():
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()  # Can hang forever!

# ✅ GOOD - Fewer threads, timeout, error tracking
def test_concurrent():
    errors = []

    def safe_worker():
        try:
            worker()
        except Exception as e:
            errors.append(e)

    # Limit: max 5 threads per test
    threads = [threading.Thread(target=safe_worker) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)  # MANDATORY timeout!

    assert len(errors) == 0, f"Thread errors: {errors}"
```

**Limits:**
- ⚠️ **Maximum threads per test:** 5
- ⚠️ **Maximum iterations per thread:** 50
- ✅ **ALWAYS add `timeout=` to `thread.join()`**
- ✅ **ALWAYS track errors in threaded tests**

---

### 🚨 Rule #3: Memory Allocation Limits

**Problem:** 100KB+ string allocations in tests caused memory spikes on WSL2.

**Solution:**
```python
# ❌ BAD - Massive allocations
def test_large_response():
    huge_response = "x" * 100000  # 100KB
    validator.validate(huge_response)

# ✅ GOOD - Reasonable sizes
def test_large_response():
    large_response = "x" * 5000  # 5KB - proves the point
    validator.validate(large_response)
```

**Limits:**
- ⚠️ **Maximum string allocation:** 20KB per test
- ⚠️ **Maximum buffer size in tests:** 5,000 items
- ⚠️ **Maximum iteration count:** 1,000 per loop

---

### 🚨 Rule #4: Mark Unstable Tests

**Problem:** Tests with heavy concurrency crashed WSL2 but passed locally.

**Solution:**
```python
# Tests with known instability
@pytest.mark.slow
@pytest.mark.skipif(True, reason="Unstable on WSL2 - resource exhaustion")
def test_heavy_concurrent_operations():
    # 10+ threads, complex interactions, etc.
    pass
```

**When to mark tests:**
- Uses >5 threads concurrently
- Uses ThreadPoolExecutor or multiprocessing
- Combines threading + SSH/network connections
- Known to be flaky on WSL2

**Run with:** `pytest -m "not slow"` (default safe mode)

---

## Test Writing Checklist

Before committing tests, verify:

### Timing & Blocking
- [ ] No `time.sleep()` > 0.5s in any single test
- [ ] Total `time.sleep()` per file < 5s
- [ ] Used `fast_time` fixture for tests needing time advancement
- [ ] All completion timeouts ≤ 0.5s (use 0.1-0.2s)

### Threading
- [ ] No more than 5 threads per test
- [ ] All `thread.join()` calls have `timeout=` parameter
- [ ] Error tracking in place for threaded code
- [ ] Used `errors = []` pattern to catch exceptions

### Memory
- [ ] No string allocations > 20KB
- [ ] Buffer sizes ≤ 5,000 items
- [ ] Loop iterations ≤ 1,000 per loop
- [ ] Large allocations only when testing limits

### Cleanup
- [ ] Fixtures properly tear down resources
- [ ] Background threads explicitly stopped
- [ ] File handles closed (use context managers)
- [ ] Database connections cleaned up

### Markers
- [ ] Heavy tests marked with `@pytest.mark.slow`
- [ ] Unstable tests skipped on WSL2 with reason
- [ ] Clear docstrings explaining test purpose

---

## Fixtures to Use (conftest.py)

### 1. `fast_time` - Mock Time Operations
```python
def test_with_timing(fast_time):
    start = time.time()
    time.sleep(10.0)  # Instant!
    elapsed = time.time() - start
    assert elapsed == 10.0
```

### 2. `monitor_with_cleanup` - OutputMonitor Factory
```python
def test_monitor(monitor_with_cleanup):
    monitor = monitor_with_cleanup(completion_timeout=0.1)
    # Automatically cleaned up after test
```

### 3. Auto-Cleanup Fixtures
- `cleanup_resources` - Joins threads, closes connections (autouse)
- `reset_registries` - Clears plugin registries (autouse)

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern #1: Cumulative Sleep Buildup
```python
# DON'T: 30 tests × 2.5s = 75s total
class TestCompletion:
    def test_marker_1(self):
        time.sleep(2.5)
    def test_marker_2(self):
        time.sleep(2.5)
    # ... 28 more tests
```

**Fix:** Reduce timeout in fixture to 0.2s, reduce sleeps to 0.25s (saves 67s).

---

### ❌ Anti-Pattern #2: Thread Leak
```python
# DON'T: Thread never cleaned up
def test_monitoring():
    monitor.start_monitoring(stream)  # Starts daemon thread
    # Test ends, thread keeps running!
```

**Fix:** Ensure `monitor.stop_monitoring()` called in fixture teardown.

---

### ❌ Anti-Pattern #3: Unbounded Loops
```python
# DON'T: Testing with production-scale data
def test_performance():
    for i in range(10000):  # Too many iterations
        process(i)
```

**Fix:** Reduce to 500-1000 iterations. The test proves the concept.

---

### ❌ Anti-Pattern #4: No Thread Timeout
```python
# DON'T: Can hang indefinitely
threads = [Thread(target=work) for _ in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()  # If work() hangs, test hangs
```

**Fix:** Always add `t.join(timeout=5.0)`.

---

## WSL2-Specific Constraints

WSL2 has **tighter resource limits** than native Linux:

| Resource | Native Linux | WSL2 | Recommendation |
|----------|--------------|------|----------------|
| **Threads** | 1000s | ~100 active | Max 5 per test |
| **File Descriptors** | 65536 | ~1024 | Close promptly |
| **Memory** | Full RAM | Shared with Windows | Limit allocations |
| **Process Spawn** | Fast | Slower | Mock subprocess |

### Why Tests Pass Locally But Fail in WSL2

1. **Thread accumulation:** WSL2 doesn't GC threads as aggressively
2. **File descriptor leak:** SSH, file handles accumulate faster
3. **Memory pressure:** Shared memory pool with Windows
4. **Timing differences:** Sleeps may be less accurate

**Solution:** Design tests for **constrained environments** by default.

---

## Performance Targets

### Test Execution Speed
- **Single test file:** < 30 seconds
- **Full M2 suite:** < 2 minutes
- **Individual test:** < 1 second (excluding slow tests)

### Coverage Targets
- **Overall:** ≥85%
- **Critical modules:** ≥90% (StateManager, DecisionEngine)
- **Foundation (M0):** ≥95%

### Resource Usage (per test file)
- **Peak memory:** < 100MB
- **Peak threads:** < 10 active
- **File descriptors:** < 50 open

---

## Pytest Configuration

See `pytest.ini` for recommended settings:

```ini
[pytest]
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests requiring external services
    wsl2_unstable: marks tests known to be unstable on WSL2

# Default to safe mode (skip slow tests)
addopts = -v --tb=short -m "not slow"

# Timeout for individual tests (prevents hangs)
timeout = 30

# Show warnings
filterwarnings = error
```

---

## Code Review Checklist for Test PRs

Reviewer should verify:

### Resource Management
- [ ] Total sleep time per file < 5s
- [ ] Thread count ≤ 5 per test
- [ ] All threads have join timeouts
- [ ] Memory allocations reasonable

### Test Quality
- [ ] Tests are isolated (no shared state)
- [ ] Fixtures clean up resources
- [ ] Error messages are descriptive
- [ ] Fast timeouts used (0.1-0.5s)

### WSL2 Compatibility
- [ ] No tests spawn >5 threads
- [ ] Heavy tests marked `@pytest.mark.slow`
- [ ] No subprocess calls without mocking
- [ ] File operations use context managers

### Documentation
- [ ] Test purpose clear from name/docstring
- [ ] Complex logic has comments
- [ ] Known limitations documented

---

## Example: Good Test Structure

```python
"""Tests for MyComponent.

Follows guidelines:
- Fast timeouts (0.2s)
- Minimal threading (≤3 threads)
- Error tracking in threads
- Proper cleanup
"""

import pytest
import time
import threading
from unittest.mock import Mock

from src.my_component import MyComponent


class TestMyComponent:
    """Test suite for MyComponent."""

    @pytest.fixture
    def component(self):
        """Create component with fast settings."""
        comp = MyComponent(timeout=0.2)  # Fast timeout
        yield comp
        # Cleanup
        comp.cleanup()

    def test_basic_operation(self, component):
        """Test basic operation completes."""
        result = component.process("input")
        assert result == "expected"

    def test_completion_detection(self, component):
        """Test completion detection with fast timeout."""
        component.start()
        component.mark_complete()

        # Short sleep, just over timeout
        time.sleep(0.25)

        assert component.is_complete()

    @pytest.mark.slow
    def test_concurrent_operations(self, component):
        """Test thread safety (marked slow).

        Note: Uses 3 threads × 5 iterations = 15 operations.
        Marked slow due to threading complexity.
        """
        errors = []

        def safe_worker():
            try:
                for i in range(5):  # Limited iterations
                    component.process(f"input_{i}")
            except Exception as e:
                errors.append(e)

        # Limit: 3 threads (not 10!)
        threads = [threading.Thread(target=safe_worker) for _ in range(3)]

        for t in threads:
            t.start()

        # MANDATORY: timeout on join
        for t in threads:
            t.join(timeout=5.0)

        # Check for errors
        assert len(errors) == 0, f"Thread errors: {errors}"
```

---

## Debugging Test Failures in WSL2

If tests crash WSL2:

1. **Check for resource leaks:**
   ```bash
   # Count sleep calls
   grep -r "time.sleep" tests/ | wc -l

   # Find long sleeps
   grep -r "time.sleep([1-9]" tests/

   # Find threading without timeout
   grep -A 5 "thread.join()" tests/ | grep -v "timeout="
   ```

2. **Run tests serially:**
   ```bash
   pytest tests/test_file.py -v -x  # Stop on first failure
   ```

3. **Check system resources:**
   ```bash
   # Monitor during test run
   watch -n 1 'ps aux | grep pytest | wc -l'  # Thread count
   ```

4. **Review pytest cache:**
   ```bash
   cat .pytest_cache/v/cache/lastfailed  # Last failing test
   ```

---

## Migration Guide: Fixing Existing Tests

If you have tests that violate these guidelines:

### Step 1: Reduce Sleep Times
```bash
# Find all sleeps > 0.5s
grep -rn "time.sleep([1-9]" tests/

# Replace with shorter times or mocking
```

### Step 2: Add Thread Timeouts
```bash
# Find joins without timeout
grep -rn "\.join()" tests/ | grep -v "timeout="

# Add timeout= parameter to each
```

### Step 3: Reduce Thread Counts
```bash
# Find tests with >5 threads
grep -B 10 -A 10 "range([6-9]\\|range([0-9][0-9])" tests/ | grep Thread

# Reduce to 3-5 threads
```

### Step 4: Mark Heavy Tests
```bash
# Add to tests with heavy concurrency
@pytest.mark.slow
```

---

## Success Metrics

After following these guidelines, you should see:

- ✅ Test suite runs in < 2 minutes (was 5+ minutes)
- ✅ No WSL2 crashes during testing
- ✅ Tests pass consistently on both native Linux and WSL2
- ✅ Resource usage stays under limits
- ✅ CI/CD pipeline stability improves

---

## Natural Language Command Testing

**New in v1.3.0**: NL command system has dual testing strategy.

**See**: [NL Testing Strategy](../testing/NL_TESTING_STRATEGY.md) for complete guide.

### Quick Tips

- **Use `mock_llm_smart` fixture** for fast mock tests (15s total execution)
- **Mark real LLM tests** with `@pytest.mark.integration` and `@pytest.mark.requires_ollama`
- **Run mock tests locally** for development (instant feedback)
- **Run real LLM tests in CI** for validation (5-10min, requires Ollama)

### Mock vs Real LLM Tests

| Test Type | Use Case | Speed | Requirements |
|-----------|----------|-------|--------------|
| Mock | Code logic, error handling | 15s | None |
| Real LLM | Prompt engineering, accuracy | 5-10min | Ollama + Qwen model |

### Example Usage

**Mock test (fast)**:
```python
def test_with_mock(mock_llm_smart):
    """Fast test using smart mock fixture"""
    extractor = EntityExtractor(llm_plugin=mock_llm_smart)
    result = extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"
    # Executes in ~0.1s
```

**Real LLM test (slow, validates accuracy)**:
```python
@pytest.mark.integration
@pytest.mark.requires_ollama
def test_with_real_llm(real_entity_extractor):
    """Slow test using actual Ollama/Qwen LLM"""
    result = real_entity_extractor.extract("Create epic 'Test'", "COMMAND")
    assert result.entity_type == "epic"
    assert result.confidence >= 0.7  # Validate real LLM accuracy
    # Executes in ~0.5-2.0s
```

### Running NL Tests

```bash
# Development: Mock tests only (fast - 15s)
pytest tests/test_nl_*.py -v -m "not integration"

# Validation: Real LLM tests (slow - 5-10min, requires Ollama)
pytest tests/test_nl_real_llm_integration.py -v -m integration

# Full: Both mock + real LLM (88+ tests, ~10min)
pytest tests/test_nl_*.py -v -m ""
```

### Prerequisites for Real LLM Tests

Real LLM tests require Ollama service running:

```bash
# On host machine (Windows with RTX 5090)
ollama serve

# Pull model
ollama pull qwen2.5-coder:32b

# Verify from WSL2
curl http://172.29.144.1:11434/api/tags
```

### Best Practices

1. **Write mock tests first** - Fast feedback during development
2. **Add real LLM tests for prompt changes** - Validate production behavior
3. **Use smart fixtures** - Don't create inline mocks (broken JSON)
4. **Set confidence thresholds** - Real LLM tests should validate accuracy (≥0.7)
5. **Module-scoped fixtures** - Reuse config/state for performance

**See Also**:
- [NL Testing Strategy](../testing/NL_TESTING_STRATEGY.md) - Complete decision matrix
- [Real LLM Testing Guide](REAL_LLM_TESTING_GUIDE.md) - Detailed setup and troubleshooting
- [Testing Documentation Index](../testing/README.md) - All testing resources

---

## References

- **Root Cause Analysis:** See WSL2 crash investigation (2025-11-01)
- **Fixed Tests:** M2 test suite optimization commit
- **Fixtures:** `tests/conftest.py`
- **Configuration:** `pytest.ini`
- **NL Testing:** `docs/testing/NL_TESTING_STRATEGY.md` ⭐ NEW!

---

## Questions?

If unsure whether a test follows guidelines, ask:

1. **Does this test sleep for > 0.5s total?** → Use fast_time or reduce timeout
2. **Does this test create > 5 threads?** → Reduce thread count
3. **Does this test allocate > 20KB?** → Reduce allocation size
4. **Does this test use join() without timeout?** → Add timeout=5.0
5. **Is this test flaky on WSL2?** → Mark with @pytest.mark.slow and skip

When in doubt, **optimize for constrained environments** (WSL2, CI containers).
