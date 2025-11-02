# ADR-003: File Watcher Thread Cleanup Strategy

**Date**: 2025-11-01
**Status**: Implemented
**Deciders**: Development Team
**Tags**: testing, threading, watchdog, WSL2

## Context

`test_file_watcher.py` was causing test hangs and WSL2 crashes due to improper cleanup of watchdog Observer threads. The platform-native `InotifyObserver` (used on Linux/WSL2) was not terminating cleanly after `stop()` and `join()` calls, leading to:

- Test subprocess hanging for 4.5+ minutes
- Accumulated background threads
- WSL2 instability

## Decision

Implemented a **multi-layered defense-in-depth approach** for robust thread cleanup:

### Layer 1: FileWatcher Implementation (`src/monitoring/file_watcher.py`)

1. **PollingObserver Option**: Added `use_polling` parameter to use `PollingObserver` instead of platform-native observer
   - PollingObserver is more predictable and doesn't use native filesystem events
   - Recommended for tests and WSL2 environments

2. **Configurable Polling Interval**: Added `polling_timeout` parameter (default: 1.0s)
   - Tests can use shorter intervals (0.05s) for fast change detection
   - Balances responsiveness vs CPU usage

3. **Shorter Debounce Window for Tests**: Tests use `debounce_window=0.05`
   - Default is 0.5s, too long for tests with rapid operations
   - Shorter window allows multiple operations per test without debouncing

4. **Extended Shutdown Timeout**: Increased `join()` timeout from 1.0s to 2.0s
   - WSL2's filesystem emulation layer is slow
   - Gives observer more time to shut down cleanly

5. **Thread Verification**: Check `is_alive()` after `join()`
   - Log warning if thread didn't terminate
   - Null the reference anyway to allow GC to clean up eventually

```python
# __init__ parameters
def __init__(..., use_polling=False, polling_timeout=1.0, debounce_window=0.5):
    self._use_polling = use_polling
    self._polling_timeout = polling_timeout
    self._debounce_window = debounce_window

# Observer creation
if self._use_polling:
    self._observer = PollingObserver(timeout=self._polling_timeout)
else:
    self._observer = Observer()

# Shutdown
def stop_watching(self) -> None:
    if self._observer is not None:
        self._observer.stop()
        self._observer.join(timeout=2.0)

        if self._observer.is_alive():
            logger.warning("Observer thread did not terminate, forcing cleanup")

        self._observer = None
```

### Layer 2: Test Fixture (`tests/test_file_watcher.py`)

1. **Force PollingObserver**: Set `use_polling=True` in fixture
2. **Fast Polling**: Use `polling_timeout=0.05` (50ms) for quick detection
3. **Short Debounce**: Use `debounce_window=0.05` (50ms) for test speed
4. **Try/Finally Cleanup**: Guarantee cleanup even if test fails
5. **Extra Safety**: Null observer reference in finally block

```python
@pytest.fixture
def file_watcher(...):
    watcher = FileWatcher(
        ...,
        use_polling=True,
        polling_timeout=0.05,  # Fast polling for tests
        debounce_window=0.05   # Short debounce for tests
    )
    yield watcher
    try:
        if watcher.is_watching():
            watcher.stop_watching()
    finally:
        watcher._observer = None
```

### Layer 3: Global Cleanup Hook (`tests/conftest.py`)

Added watchdog-specific cleanup to `cleanup_resources` fixture:

```python
# Stop any lingering observers
for obj in gc.get_objects():
    if isinstance(obj, (Observer, PollingObserver)):
        if obj.is_alive():
            obj.stop()
            obj.join(timeout=1.0)
```

### Layer 4: Pytest Timeout (`pytest.ini`)

```ini
timeout = 30
timeout_method = thread
```

Prevents any single test from hanging forever, with automatic termination and clear error reporting.

## Consequences

### Positive

- ✅ **No more hangs**: Tests complete within expected time (38s for 41 tests)
- ✅ **Predictable cleanup**: PollingObserver has deterministic shutdown
- ✅ **Fast change detection**: 50ms polling interval detects changes quickly
- ✅ **Fail-safe**: Multiple layers catch different failure modes
- ✅ **WSL2 stable**: No more filesystem-layer issues
- ✅ **Debuggable**: Clear logging when cleanup takes longer than expected
- ✅ **High pass rate**: 40/41 tests pass consistently (1 flaky test due to test isolation)

### Negative

- ⚠️ **Slightly slower tests**: PollingObserver polls filesystem vs. native events
  - Acceptable tradeoff for stability in test environment
  - Production code still uses platform-native observer by default

- ⚠️ **More complex**: Multiple cleanup layers
  - Well-documented and following industry best practices
  - Each layer serves a specific purpose

### Neutral

- Production code unaffected (`use_polling=False` by default)
- Test behavior more consistent across platforms

## Alternatives Considered

### 1. Skip/Mock File Watching Tests
**Rejected**: Doesn't test actual behavior; file watching is core functionality

### 2. Mock Entire Watchdog Library
**Rejected**: Loses integration testing; wouldn't catch real threading issues

### 3. Increase Timeout Only
**Rejected**: Doesn't address root cause; unreliable on slow systems

### 4. Force-Kill Threads
**Rejected**: Python doesn't support safe thread termination; can leave resources leaked

## Best Practices Applied

1. **Graceful Shutdown Pattern**:
   - Signal stop (`stop()`)
   - Wait for completion (`join(timeout)`)
   - Verify termination (`is_alive()`)
   - Force cleanup if necessary

2. **Defense in Depth**: Multiple independent layers of protection

3. **Fail-Safe Defaults**: Try/except/finally around all cleanup

4. **Explicit Resource Management**: Clear ownership and lifecycle

5. **Logging**: Visibility into cleanup behavior for debugging

## References

- [Watchdog Documentation](https://python-watchdog.readthedocs.io/)
- [Python Threading Best Practices](https://docs.python.org/3/library/threading.html)
- TEST_GUIDELINES.md - Thread cleanup requirements
- [pytest-timeout Plugin](https://pypi.org/project/pytest-timeout/)

## Validation

Run file watcher tests:
```bash
pytest tests/test_file_watcher.py -v --timeout=30
```

Expected results:
- ✅ Completes in ~38s (41 tests, 3 deselected)
- ✅ 40/41 tests pass consistently
- ✅ No timeouts or hangs
- ⚠️ 1 flaky test (test_changes_include_task_id) - passes individually, sometimes fails in suite due to test isolation

## Implementation Notes

### Test Sleep Requirements

Tests using PollingObserver need **real** sleeps, not mocked sleeps (fast_time fixture):
- PollingObserver polls at intervals (50ms in tests)
- Sleeps must be >= polling interval for changes to be detected
- Tests use 0.15s sleeps (3x polling interval) for reliability

Tests that were updated:
- Removed `fast_time` fixture from 15 tests that wait for file detection
- Increased sleeps from 0.05s to 0.15s in these tests
- Kept fast_time in tests that don't wait for detection (e.g., test initialization)

### Debounce Configuration

Default debounce window (0.5s) is too long for tests:
- Tests with create → modify → delete within 0.5s would have changes debounced
- Tests now use `debounce_window=0.05` (same as polling interval)
- This allows rapid operations without losing events

### Direct FileWatcher Instantiations

All direct `FileWatcher()` instantiations in tests must include:
```python
FileWatcher(..., use_polling=True, polling_timeout=0.05)
```

Found and fixed 7 direct instantiations that bypassed the fixture.
