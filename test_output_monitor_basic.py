#!/usr/bin/env python3
"""Basic test script for OutputMonitor to verify implementation."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.output_monitor import OutputMonitor


class MockStream:
    """Simple mock stream for testing."""

    def __init__(self, chunks):
        self.chunks = chunks
        self.index = 0

    def recv_ready(self):
        return self.index < len(self.chunks)

    def recv(self, size):
        if self.index >= len(self.chunks):
            return b''
        data = self.chunks[self.index]
        self.index += 1
        return data.encode('utf-8')


def test_basic_functionality():
    """Test basic OutputMonitor functionality."""
    print("Testing OutputMonitor basic functionality...")

    # Test 1: Initialization
    print("\n1. Testing initialization...")
    monitor = OutputMonitor()
    assert not monitor.is_monitoring
    assert len(monitor._buffer) == 0
    print("✓ Initialization successful")

    # Test 2: Completion marker detection
    print("\n2. Testing completion marker detection...")
    monitor = OutputMonitor(completion_timeout=0.5)

    stream = MockStream([
        "Starting task...\n",
        "Processing...\n",
        "Command completed\n"
    ])

    monitor.start_monitoring(stream)
    time.sleep(1.0)  # Wait for completion timeout

    is_complete = monitor.is_complete()
    print(f"   Completion detected: {is_complete}")

    response = monitor.get_response()
    print(f"   Response length: {len(response)} chars")
    assert "Command completed" in response

    monitor.stop_monitoring()
    print("✓ Completion detection works")

    # Test 3: Error detection
    print("\n3. Testing error detection...")
    monitor = OutputMonitor()

    stream = MockStream([
        "Running task...\n",
        "Error: File not found\n"
    ])

    monitor.start_monitoring(stream)
    time.sleep(0.3)

    error = monitor.detect_error()
    print(f"   Error detected: {error}")
    assert error is not None
    assert "Error" in error

    monitor.stop_monitoring()
    print("✓ Error detection works")

    # Test 4: Rate limit detection
    print("\n4. Testing rate limit detection...")
    monitor = OutputMonitor()

    stream = MockStream([
        "Making request...\n",
        "rate limit exceeded\n"
    ])

    monitor.start_monitoring(stream)
    time.sleep(0.3)

    is_rate_limited = monitor.detect_rate_limit()
    print(f"   Rate limit detected: {is_rate_limited}")
    assert is_rate_limited

    monitor.stop_monitoring()
    print("✓ Rate limit detection works")

    # Test 5: Buffer management
    print("\n5. Testing buffer management...")
    monitor = OutputMonitor(buffer_size=10)

    # Add more lines than buffer size
    for i in range(20):
        monitor._buffer.append(f"Line {i}")

    assert len(monitor._buffer) == 10
    print(f"   Buffer size: {len(monitor._buffer)} (max: 10)")

    # Check FIFO behavior
    buffer_list = list(monitor._buffer)
    assert "Line 10" in buffer_list[0]  # First line in buffer
    assert "Line 19" in buffer_list[-1]  # Last line in buffer
    print("✓ Buffer management (FIFO) works")

    # Test 6: Observer pattern
    print("\n6. Testing observer pattern...")
    monitor = OutputMonitor()

    events = []
    def observer(event):
        events.append(event)

    monitor.register_observer(observer)

    stream = MockStream([
        "Test output\n"
    ])

    monitor.start_monitoring(stream)
    time.sleep(0.3)

    print(f"   Events received: {len(events)}")
    assert len(events) > 0

    monitor.stop_monitoring()
    print("✓ Observer pattern works")

    # Test 7: Statistics
    print("\n7. Testing statistics...")
    monitor = OutputMonitor()

    stats = monitor.get_stats()
    print(f"   Stats keys: {list(stats.keys())}")
    assert 'is_monitoring' in stats
    assert 'buffer_lines' in stats
    assert 'completion_detected' in stats
    print("✓ Statistics work")

    # Test 8: Context manager
    print("\n8. Testing context manager...")
    stream = MockStream(["Test\n"])

    with OutputMonitor() as monitor:
        monitor.start_monitoring(stream)
        assert monitor.is_monitoring

    # Should be stopped after context exit
    assert not monitor.is_monitoring
    print("✓ Context manager works")

    print("\n" + "="*50)
    print("All basic tests passed! ✓")
    print("="*50)


def test_multiple_patterns():
    """Test various completion, error, and rate limit patterns."""
    print("\n\nTesting pattern variations...")

    # Test completion markers
    print("\n1. Testing completion markers...")
    markers = ["Ready for", ">>>", "Command completed", "Finished"]

    for marker in markers:
        monitor = OutputMonitor(completion_timeout=0.3)
        stream = MockStream([
            "Working...\n",
            f"{marker}\n"
        ])

        monitor.start_monitoring(stream)
        time.sleep(0.5)

        assert monitor.is_complete(), f"Failed to detect: {marker}"
        monitor.stop_monitoring()
        print(f"   ✓ Detected: {marker}")

    # Test error markers
    print("\n2. Testing error markers...")
    error_markers = ["Error:", "Exception:", "Traceback:", "FAILED"]

    for marker in error_markers:
        monitor = OutputMonitor()
        stream = MockStream([
            f"{marker} Something went wrong\n"
        ])

        monitor.start_monitoring(stream)
        time.sleep(0.2)

        error = monitor.detect_error()
        assert error is not None, f"Failed to detect: {marker}"
        monitor.stop_monitoring()
        print(f"   ✓ Detected: {marker}")

    # Test rate limit markers
    print("\n3. Testing rate limit markers...")
    rate_markers = ["rate limit", "too many requests", "quota exceeded"]

    for marker in rate_markers:
        monitor = OutputMonitor()
        stream = MockStream([
            f"Error: {marker}\n"
        ])

        monitor.start_monitoring(stream)
        time.sleep(0.2)

        assert monitor.detect_rate_limit(), f"Failed to detect: {marker}"
        monitor.stop_monitoring()
        print(f"   ✓ Detected: {marker}")

    print("\nAll pattern tests passed! ✓")


if __name__ == '__main__':
    try:
        test_basic_functionality()
        test_multiple_patterns()
        print("\n" + "="*50)
        print("SUCCESS: All tests passed!")
        print("="*50)
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
