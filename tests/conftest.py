"""Pytest configuration and shared fixtures."""

import gc
import time
import threading
import pytest
from unittest.mock import Mock
from src.plugins.registry import AgentRegistry, LLMRegistry


@pytest.fixture(autouse=True)
def reset_registries():
    """Clear plugin registries before each test.

    This ensures tests don't interfere with each other through
    shared registry state.
    """
    yield
    # Teardown: clear registries after test
    AgentRegistry.clear()
    LLMRegistry.clear()


@pytest.fixture(autouse=True)
def cleanup_resources(request):
    """Clean up resources after each test to prevent leaks.

    This is critical for preventing resource accumulation that can
    crash WSL2, especially with SSH connections and file descriptors.

    OPTIMIZATION: Only performs expensive paramiko cleanup for tests
    that actually use SSH, avoiding 453 gc.get_objects() scans that
    were causing WSL2 crashes.
    """
    yield
    # Force garbage collection to clean up any lingering connections
    gc.collect()

    # Clean up watchdog observers specifically (for file_watcher tests)
    try:
        from watchdog.observers import Observer
        from watchdog.observers.polling import PollingObserver

        # Stop any lingering observers
        for obj in gc.get_objects():
            if isinstance(obj, (Observer, PollingObserver)):
                try:
                    if hasattr(obj, 'is_alive') and obj.is_alive():
                        obj.stop()
                        obj.join(timeout=1.0)
                except Exception:
                    pass
    except (ImportError, Exception):
        pass  # watchdog not available or cleanup failed

    # Clean up any active threads (except main and daemon threads we don't own)
    try:
        active_threads = threading.enumerate()
        for thread in active_threads:
            # Skip main thread and system threads
            if thread == threading.main_thread():
                continue
            # Skip threads we don't own (pytest internal, etc.)
            if not hasattr(thread, '_target'):
                continue
            # Try to join with short timeout (reduced from 0.5s to 0.1s)
            if thread.is_alive() and thread != threading.current_thread():
                thread.join(timeout=0.1)
    except Exception:
        pass

    # CRITICAL OPTIMIZATION: Only clean up paramiko for SSH tests
    # This avoids calling gc.get_objects() 453 times (was causing WSL2 crashes)
    # Only run for tests in files that actually use SSH/paramiko
    test_file = request.node.fspath.basename
    ssh_test_files = {'test_claude_code_ssh.py', 'test_core.py', 'test_plugins.py'}

    if test_file in ssh_test_files:
        try:
            import paramiko
            # Close any active transport connections
            # NOTE: gc.get_objects() is VERY expensive - only use when necessary
            for obj in gc.get_objects():
                if isinstance(obj, paramiko.Transport):
                    try:
                        obj.close()
                    except Exception:
                        pass
        except ImportError:
            pass  # paramiko not available, skip


@pytest.fixture
def fast_time(monkeypatch):
    """Mock time functions for fast test execution.

    Replaces time.sleep() with instant time advancement and time.time()
    with controlled time tracking. This eliminates blocking sleeps that
    can cause WSL2 resource exhaustion.

    Usage:
        def test_with_timing(fast_time):
            start = time.time()
            time.sleep(2.0)  # Instant, no blocking
            elapsed = time.time() - start
            assert elapsed == 2.0
    """
    current_time = [time.time()]  # Use list for mutability in closure

    def fake_sleep(duration):
        """Advance time without blocking."""
        if duration > 0:
            current_time[0] += duration

    def fake_time():
        """Return current mocked time."""
        return current_time[0]

    # Patch both time.sleep and time.time
    monkeypatch.setattr('time.sleep', fake_sleep)
    monkeypatch.setattr('time.time', fake_time)

    return Mock(advance=lambda d: fake_sleep(d), now=fake_time)


@pytest.fixture
def monitor_with_cleanup():
    """Create OutputMonitor with guaranteed cleanup.

    Ensures the monitor is properly stopped and threads are cleaned up,
    preventing resource leaks that cause WSL2 crashes.

    Usage:
        def test_monitor(monitor_with_cleanup):
            monitor = monitor_with_cleanup(completion_timeout=0.1)
            # ... use monitor ...
            # Cleanup happens automatically
    """
    monitors = []

    def create_monitor(**kwargs):
        from src.agents.output_monitor import OutputMonitor
        # Use fast timeouts by default
        if 'completion_timeout' not in kwargs:
            kwargs['completion_timeout'] = 0.1
        monitor = OutputMonitor(**kwargs)
        monitors.append(monitor)
        return monitor

    yield create_monitor

    # Cleanup all created monitors
    for monitor in monitors:
        try:
            if monitor.is_monitoring:
                monitor.stop_monitoring()
            # Give thread minimal time to exit (reduced from 0.01s)
            time.sleep(0.001)
        except Exception:
            pass
