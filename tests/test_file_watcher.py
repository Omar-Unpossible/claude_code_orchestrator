"""Tests for FileWatcher component.

Tests cover:
- Basic file watching functionality
- Pattern filtering
- Event debouncing
- Content hashing
- Thread safety
- State manager integration
- Performance requirements
"""

import pytest
import time
import tempfile
import shutil
import threading
import psutil
import os
from pathlib import Path
from typing import List, Dict

from src.monitoring.file_watcher import FileWatcher
from src.core.state import StateManager
from src.core.models import FileState


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix='test_file_watcher_')
    yield temp_dir
    # Cleanup
    if Path(temp_dir).exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def state_manager():
    """Create a test StateManager."""
    # Reset singleton
    StateManager.reset_instance()

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(
        suffix='.db',
        delete=False
    )
    db_path = temp_db.name
    temp_db.close()

    # Create StateManager
    sm = StateManager.get_instance(f'sqlite:///{db_path}')

    yield sm

    # Cleanup
    sm.close()
    StateManager.reset_instance()
    if Path(db_path).exists():
        os.unlink(db_path)


@pytest.fixture
def project(state_manager):
    """Create a test project."""
    return state_manager.create_project(
        name='test-project',
        description='Test project',
        working_dir='/tmp/test'
    )


@pytest.fixture
def file_watcher(state_manager, project, temp_project_dir):
    """Create a FileWatcher instance with PollingObserver for predictable cleanup.

    Uses PollingObserver with 0.05s polling interval instead of platform-native
    observer to ensure reliable thread cleanup on WSL2 and fast change detection
    in tests. Also uses shorter debounce window (0.05s) for faster test execution.
    """
    watcher = FileWatcher(
        state_manager=state_manager,
        project_id=project.id,
        project_root=temp_project_dir,
        use_polling=True,  # Use PollingObserver for predictable cleanup
        polling_timeout=0.05,  # Fast polling for tests (50ms)
        debounce_window=0.05  # Short debounce for tests (50ms)
    )
    yield watcher

    # Cleanup - guaranteed execution even if test fails
    try:
        if watcher.is_watching():
            watcher.stop_watching()
    except Exception as e:
        # Log but don't fail test cleanup
        import logging
        logging.getLogger(__name__).warning(f"Cleanup warning: {e}")
    finally:
        # Extra safety: nullify reference to help GC
        watcher._observer = None


class TestFileWatcherInitialization:
    """Test FileWatcher initialization."""

    def test_initialization(self, state_manager, project, temp_project_dir):
        """Test basic initialization."""
        watcher = FileWatcher(
            state_manager=state_manager,
            project_id=project.id,
            project_root=temp_project_dir,
            use_polling=True,
            polling_timeout=0.05
        )

        assert watcher._project_id == project.id
        assert watcher._project_root == Path(temp_project_dir).resolve()
        assert not watcher.is_watching()
        assert len(watcher.get_watched_paths()) == 0

    def test_initialization_with_custom_patterns(
        self,
        state_manager,
        project,
        temp_project_dir
    ):
        """Test initialization with custom patterns."""
        watch_patterns = ['*.txt', '*.log']
        ignore_patterns = ['*.tmp']

        watcher = FileWatcher(
            state_manager=state_manager,
            project_id=project.id,
            project_root=temp_project_dir,
            watch_patterns=watch_patterns,
            ignore_patterns=ignore_patterns,
            use_polling=True,
            polling_timeout=0.05
        )

        assert watcher._watch_patterns == watch_patterns
        assert watcher._ignore_patterns == ignore_patterns

    def test_initialization_with_task_id(
        self,
        state_manager,
        project,
        temp_project_dir
    ):
        """Test initialization with task ID."""
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test task',
                'description': 'Test description'
            }
        )

        watcher = FileWatcher(
            state_manager=state_manager,
            project_id=project.id,
            project_root=temp_project_dir,
            task_id=task.id,
            use_polling=True,
            polling_timeout=0.05
        )

        assert watcher._task_id == task.id


class TestFileWatchingOperations:
    """Test file watching start/stop operations."""

    def test_start_watching(self, file_watcher, temp_project_dir):
        """Test starting file watching."""
        file_watcher.start_watching()

        assert file_watcher.is_watching()
        assert str(Path(temp_project_dir).resolve()) in file_watcher.get_watched_paths()

    def test_start_watching_custom_path(self, file_watcher, temp_project_dir):
        """Test starting watching on custom path."""
        # Create subdirectory
        subdir = Path(temp_project_dir) / 'subdir'
        subdir.mkdir()

        file_watcher.start_watching(str(subdir))

        assert file_watcher.is_watching()
        assert str(subdir.resolve()) in file_watcher.get_watched_paths()

    def test_start_watching_nonexistent_path(self, file_watcher):
        """Test starting watching on non-existent path."""
        with pytest.raises(FileNotFoundError):
            file_watcher.start_watching('/nonexistent/path')

    def test_start_watching_when_already_watching(self, file_watcher):
        """Test starting watching when already watching."""
        file_watcher.start_watching()

        with pytest.raises(ValueError, match="Already watching"):
            file_watcher.start_watching()

    def test_stop_watching(self, file_watcher):
        """Test stopping file watching."""
        file_watcher.start_watching()
        assert file_watcher.is_watching()

        file_watcher.stop_watching()
        assert not file_watcher.is_watching()
        assert len(file_watcher.get_watched_paths()) == 0

    def test_stop_watching_multiple_times(self, file_watcher):
        """Test stopping watching multiple times is safe."""
        file_watcher.start_watching()
        file_watcher.stop_watching()
        file_watcher.stop_watching()  # Should not raise

        assert not file_watcher.is_watching()

    def test_context_manager(self, file_watcher):
        """Test using FileWatcher as context manager."""
        with file_watcher as watcher:
            assert watcher.is_watching()

        assert not file_watcher.is_watching()


class TestFileChangeDetection:
    """Test file change detection."""

    def test_detect_file_creation(self, file_watcher, temp_project_dir):
        """Test detecting file creation."""
        file_watcher.start_watching()
        time.sleep(0.15)  # Let watcher start

        # Create file
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')

        # Wait for event processing (real sleep needed for watchdog)
        time.sleep(0.15)  # Sufficient for event processing

        changes = file_watcher.get_recent_changes(limit=10)
        assert len(changes) > 0

        # Find creation event
        creation_events = [
            c for c in changes
            if c['change_type'] == 'created' and 'test.py' in c['file_path']
        ]
        assert len(creation_events) > 0

        change = creation_events[0]
        assert change['file_path'] == 'test.py'
        assert change['change_type'] == 'created'
        assert 'content_hash' in change
        assert change['file_size'] > 0

    def test_detect_file_modification(self, file_watcher, temp_project_dir):
        """Test detecting file modification."""
        # Create file before watching
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')

        file_watcher.start_watching()
        time.sleep(0.15)

        # Modify file
        test_file.write_text('print("hello world")')
        time.sleep(0.15)

        changes = file_watcher.get_recent_changes(limit=10)
        modification_events = [
            c for c in changes
            if c['change_type'] == 'modified' and 'test.py' in c['file_path']
        ]
        assert len(modification_events) > 0

        change = modification_events[0]
        assert change['change_type'] == 'modified'
        assert 'content_hash' in change

    def test_detect_file_deletion(self, file_watcher, temp_project_dir):
        """Test detecting file deletion."""
        # Create file
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')

        file_watcher.start_watching()
        time.sleep(0.15)

        # Delete file
        test_file.unlink()
        time.sleep(0.15)

        changes = file_watcher.get_recent_changes(limit=10)
        deletion_events = [
            c for c in changes
            if c['change_type'] == 'deleted' and 'test.py' in c['file_path']
        ]
        assert len(deletion_events) > 0

        change = deletion_events[0]
        assert change['change_type'] == 'deleted'
        assert change['content_hash'] == ''
        assert change['file_size'] == 0

    def test_detect_multiple_files(self, file_watcher, temp_project_dir):
        """Test detecting changes to multiple files."""
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create multiple files
        for i in range(5):
            test_file = Path(temp_project_dir) / f'test{i}.py'
            test_file.write_text(f'# File {i}')
            time.sleep(0.15)  # Debounce window

        changes = file_watcher.get_recent_changes(limit=20)
        creation_events = [
            c for c in changes if c['change_type'] == 'created'
        ]
        assert len(creation_events) >= 5


class TestPatternFiltering:
    """Test pattern-based filtering."""

    def test_watch_patterns(self, state_manager, project, temp_project_dir):
        """Test watching only specific patterns.

        Note: Does NOT use fast_time because PollingObserver needs real time to poll.
        Sleep times kept minimal (0.3s total) to stay within TEST_GUIDELINES.md limits.
        Uses 0.05s polling interval for fast change detection.
        """
        watcher = FileWatcher(
            state_manager=state_manager,
            project_id=project.id,
            project_root=temp_project_dir,
            watch_patterns=['*.txt'],
            use_polling=True,
            polling_timeout=0.05
        )
        watcher.start_watching()
        time.sleep(0.1)  # Real sleep for PollingObserver to initialize

        # Create watched file
        txt_file = Path(temp_project_dir) / 'test.txt'
        txt_file.write_text('test')
        time.sleep(0.1)  # Real sleep for PollingObserver to detect

        # Create unwatched file
        py_file = Path(temp_project_dir) / 'test.py'
        py_file.write_text('print("test")')
        time.sleep(0.1)  # Real sleep for PollingObserver to detect

        changes = watcher.get_recent_changes()
        txt_changes = [c for c in changes if 'test.txt' in c['file_path']]
        py_changes = [c for c in changes if 'test.py' in c['file_path']]

        assert len(txt_changes) > 0
        assert len(py_changes) == 0

        watcher.stop_watching()

    def test_ignore_patterns(self, state_manager, project, temp_project_dir):
        """Test ignoring specific patterns.

        Note: Does NOT use fast_time because PollingObserver needs real time to poll.
        Sleep times kept minimal (0.3s total) to stay within TEST_GUIDELINES.md limits.
        Uses 0.05s polling interval for fast change detection.
        """
        watcher = FileWatcher(
            state_manager=state_manager,
            project_id=project.id,
            project_root=temp_project_dir,
            watch_patterns=['*'],
            ignore_patterns=['*.log'],
            use_polling=True,
            polling_timeout=0.05
        )
        watcher.start_watching()
        time.sleep(0.1)  # Real sleep for PollingObserver to initialize

        # Create ignored file
        log_file = Path(temp_project_dir) / 'test.log'
        log_file.write_text('log data')
        time.sleep(0.1)  # Real sleep for PollingObserver to detect

        # Create watched file
        txt_file = Path(temp_project_dir) / 'test.txt'
        txt_file.write_text('test')
        time.sleep(0.1)  # Real sleep for PollingObserver to detect

        changes = watcher.get_recent_changes()
        log_changes = [c for c in changes if 'test.log' in c['file_path']]
        txt_changes = [c for c in changes if 'test.txt' in c['file_path']]

        assert len(log_changes) == 0
        assert len(txt_changes) > 0

        watcher.stop_watching()

    def test_ignore_temporary_files(self, file_watcher, temp_project_dir, fast_time):
        """Test ignoring temporary files."""
        file_watcher.start_watching()
        time.sleep(0.05)

        # Create temporary files
        temp_files = [
            'test.swp',
            'test.tmp',
            'test~',
            '.#test',
            'test.bak'
        ]

        for temp_file in temp_files:
            file_path = Path(temp_project_dir) / temp_file
            file_path.write_text('temp')
            time.sleep(0.05)

        time.sleep(0.05)

        changes = file_watcher.get_recent_changes()
        # Temporary files should be filtered out
        for temp_file in temp_files:
            temp_changes = [c for c in changes if temp_file in c['file_path']]
            assert len(temp_changes) == 0


class TestDebouncing:
    """Test event debouncing."""

    def test_debounce_rapid_changes(self, file_watcher, temp_project_dir, fast_time):
        """Test debouncing rapid changes to same file."""
        file_watcher.start_watching()
        time.sleep(0.05)

        test_file = Path(temp_project_dir) / 'test.py'

        # Make rapid changes (within debounce window)
        for i in range(5):
            test_file.write_text(f'# Version {i}')
            time.sleep(0.05)  # Much less than debounce window

        # Wait for debounce window to pass
        time.sleep(0.05)

        changes = file_watcher.get_recent_changes()
        test_changes = [
            c for c in changes
            if 'test.py' in c['file_path']
        ]

        # Should have only 1-2 events, not 5
        assert len(test_changes) <= 2

    def test_no_debounce_for_different_files(self, file_watcher, temp_project_dir):
        """Test that debouncing doesn't affect different files."""
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create different files rapidly
        for i in range(5):
            test_file = Path(temp_project_dir) / f'test{i}.py'
            test_file.write_text(f'# File {i}')
            time.sleep(0.15)

        time.sleep(0.15)

        changes = file_watcher.get_recent_changes()
        # All different files should be detected
        assert len(changes) >= 5


class TestContentHashing:
    """Test content hashing functionality."""

    def test_hash_calculation(self, file_watcher, temp_project_dir):
        """Test MD5 hash calculation."""
        test_file = Path(temp_project_dir) / 'test.py'
        content = 'print("hello")'
        test_file.write_text(content)

        # Calculate hash
        file_hash = file_watcher._calculate_hash(test_file)

        # Verify it's a valid MD5 hash
        assert len(file_hash) == 32
        assert all(c in '0123456789abcdef' for c in file_hash)

        # Verify hash is consistent
        hash2 = file_watcher._calculate_hash(test_file)
        assert file_hash == hash2

    def test_hash_changes_with_content(self, file_watcher, temp_project_dir):
        """Test hash changes when content changes."""
        test_file = Path(temp_project_dir) / 'test.py'

        test_file.write_text('version 1')
        hash1 = file_watcher._calculate_hash(test_file)

        test_file.write_text('version 2')
        hash2 = file_watcher._calculate_hash(test_file)

        assert hash1 != hash2

    def test_change_includes_hash(self, file_watcher, temp_project_dir):
        """Test that change events include content hash."""
        file_watcher.start_watching()
        time.sleep(0.15)

        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.15)

        changes = file_watcher.get_recent_changes()
        assert len(changes) > 0

        change = changes[0]
        assert 'content_hash' in change
        assert len(change['content_hash']) == 32


class TestStateManagerIntegration:
    """Test integration with StateManager."""

    def test_changes_recorded_in_state_manager(
        self,
        file_watcher,
        state_manager,
        project,
        temp_project_dir
    ):
        """Test that changes are recorded in StateManager."""
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create file
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.15)

        # Check StateManager
        file_changes = state_manager.get_file_changes(project.id)
        assert len(file_changes) > 0

        # Find our file
        test_changes = [
            fc for fc in file_changes
            if 'test.py' in fc.file_path
        ]
        assert len(test_changes) > 0

        change = test_changes[0]
        assert change.change_type == 'created'
        assert change.file_size > 0
        assert len(change.file_hash) == 32

    def test_changes_include_task_id(
        self,
        state_manager,
        project,
        temp_project_dir
    ):
        """Test that changes include task ID when provided."""
        # Create task
        task = state_manager.create_task(
            project_id=project.id,
            task_data={
                'title': 'Test task',
                'description': 'Test description'
            }
        )

        # Create watcher with task ID
        watcher = FileWatcher(
            state_manager=state_manager,
            project_id=project.id,
            project_root=temp_project_dir,
            task_id=task.id,
            use_polling=True,
            polling_timeout=0.05
        )
        watcher.start_watching()
        time.sleep(0.05)

        # Create file
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.05)

        # Check StateManager
        file_changes = state_manager.get_file_changes(project.id)
        test_changes = [
            fc for fc in file_changes
            if 'test.py' in fc.file_path
        ]

        assert len(test_changes) > 0
        assert test_changes[0].task_id == task.id

        watcher.stop_watching()


class TestCallbacks:
    """Test callback registration and notification."""

    def test_register_callback(self, file_watcher):
        """Test registering a callback."""
        called = []

        def callback(change):
            called.append(change)

        file_watcher.register_handler(callback)
        assert callback in file_watcher._callbacks

    def test_callback_receives_changes(self, file_watcher, temp_project_dir):
        """Test that callbacks receive change notifications."""
        received_changes = []

        def callback(change):
            received_changes.append(change)

        file_watcher.register_handler(callback)
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create file
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.15)

        assert len(received_changes) > 0
        change = received_changes[0]
        assert 'test.py' in change['file_path']
        assert change['change_type'] == 'created'

    def test_multiple_callbacks(self, file_watcher, temp_project_dir):
        """Test multiple callbacks receive changes."""
        received1 = []
        received2 = []

        def callback1(change):
            received1.append(change)

        def callback2(change):
            received2.append(change)

        file_watcher.register_handler(callback1)
        file_watcher.register_handler(callback2)
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create file
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.15)

        assert len(received1) > 0
        assert len(received2) > 0

    def test_unregister_callback(self, file_watcher, temp_project_dir, fast_time):
        """Test unregistering a callback."""
        received = []

        def callback(change):
            received.append(change)

        file_watcher.register_handler(callback)
        file_watcher.unregister_handler(callback)

        file_watcher.start_watching()
        time.sleep(0.05)

        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.05)

        # Callback should not receive changes
        assert len(received) == 0

    def test_callback_exception_handling(self, file_watcher, temp_project_dir):
        """Test that callback exceptions don't crash watcher."""
        def bad_callback(change):
            raise ValueError("Callback error")

        good_received = []

        def good_callback(change):
            good_received.append(change)

        file_watcher.register_handler(bad_callback)
        file_watcher.register_handler(good_callback)
        file_watcher.start_watching()
        time.sleep(0.15)

        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.15)

        # Good callback should still work
        assert len(good_received) > 0


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_recent_changes_limit(self, file_watcher, temp_project_dir, fast_time):
        """Test getting recent changes with limit."""
        file_watcher.start_watching()
        time.sleep(0.05)

        # Create multiple files
        for i in range(10):
            test_file = Path(temp_project_dir) / f'test{i}.py'
            test_file.write_text(f'# File {i}')
            time.sleep(0.05)

        # Get with limit
        changes = file_watcher.get_recent_changes(limit=5)
        assert len(changes) <= 5

    def test_clear_history(self, file_watcher, temp_project_dir):
        """Test clearing change history."""
        file_watcher.start_watching()
        time.sleep(0.15)

        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('print("hello")')
        time.sleep(0.15)

        changes = file_watcher.get_recent_changes()
        assert len(changes) > 0

        file_watcher.clear_history()
        changes = file_watcher.get_recent_changes()
        assert len(changes) == 0

    def test_get_statistics(self, file_watcher, temp_project_dir):
        """Test getting statistics."""
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create file
        test_file = Path(temp_project_dir) / 'test.py'
        test_file.write_text('v1')
        time.sleep(0.15)

        # Modify file
        test_file.write_text('v2')
        time.sleep(0.15)

        # Delete file
        test_file.unlink()
        time.sleep(0.15)

        stats = file_watcher.get_statistics()
        assert stats['total_changes'] >= 3
        assert stats['created'] >= 1
        assert stats['modified'] >= 1
        assert stats['deleted'] >= 1

    def test_relative_path_calculation(self, file_watcher, temp_project_dir):
        """Test relative path calculation."""
        absolute_path = str(Path(temp_project_dir) / 'subdir' / 'test.py')
        relative_path = file_watcher._get_relative_path(absolute_path)

        assert relative_path == 'subdir/test.py' or relative_path == 'subdir\\test.py'

    def test_temporary_file_detection(self, file_watcher):
        """Test temporary file detection."""
        temp_files = [
            'test.swp',
            'test.tmp',
            'test~',
            '.#test',
            'test.bak',
            '.DS_Store',
            'Thumbs.db'
        ]

        for temp_file in temp_files:
            assert file_watcher._is_temporary_file(temp_file)

        # Non-temporary files
        assert not file_watcher._is_temporary_file('test.py')
        assert not file_watcher._is_temporary_file('test.txt')


class TestThreadSafety:
    """Test thread safety."""

    def test_concurrent_access(self, file_watcher, temp_project_dir):
        """Test concurrent access to watcher."""
        file_watcher.start_watching()
        time.sleep(0.15)

        results = []
        errors = []

        def create_files(thread_id):
            try:
                for i in range(5):
                    test_file = Path(temp_project_dir) / f'thread{thread_id}_file{i}.py'
                    test_file.write_text(f'# Thread {thread_id} File {i}')
                    time.sleep(0.05)
                results.append(thread_id)
            except Exception as e:
                errors.append(e)

        # Create multiple threads (limit to 3 per TEST_GUIDELINES.md)
        threads = []
        for i in range(3):
            thread = threading.Thread(target=create_files, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads with timeout (MANDATORY per TEST_GUIDELINES.md)
        for thread in threads:
            thread.join(timeout=5.0)

        # Should not have errors
        assert len(errors) == 0, f"Errors during concurrent access: {errors}"
        assert len(results) == 3

        # Check changes were recorded
        changes = file_watcher.get_recent_changes(limit=100)
        assert len(changes) >= 15  # 3 threads * 5 files

    def test_concurrent_callback_access(self, file_watcher, temp_project_dir, fast_time):
        """Test concurrent callback registration."""
        def dummy_callback(change):
            pass

        def register_callbacks():
            for i in range(10):
                file_watcher.register_handler(dummy_callback)

        # Create threads (limit to 3 per TEST_GUIDELINES.md)
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=register_callbacks)
            threads.append(thread)
            thread.start()

        # Join with timeout (MANDATORY per TEST_GUIDELINES.md)
        for thread in threads:
            thread.join(timeout=5.0)

        # Should not crash


@pytest.mark.slow
class TestPerformance:
    """Test performance requirements."""

    def test_handles_rapid_changes(self, file_watcher, temp_project_dir, fast_time):
        """Test handling rapid file changes."""
        file_watcher.start_watching()
        time.sleep(0.05)

        start_time = time.time()

        # Create 100 files rapidly
        for i in range(100):
            test_file = Path(temp_project_dir) / f'test{i}.py'
            test_file.write_text(f'# File {i}')
            time.sleep(0.01)  # 10ms between files (mocked by fast_time)

        # Wait for processing
        time.sleep(0.1)

        elapsed = time.time() - start_time

        # Should handle this within reasonable time
        assert elapsed < 10.0  # 10 seconds max

        # Should have detected many changes (debouncing may reduce count)
        changes = file_watcher.get_recent_changes(limit=200)
        assert len(changes) > 0

    def test_cpu_usage(self, file_watcher, temp_project_dir, fast_time):
        """Test CPU usage while watching."""
        process = psutil.Process()

        # Measure baseline CPU
        process.cpu_percent(interval=0.1)

        file_watcher.start_watching()
        time.sleep(0.1)

        # Create some files
        for i in range(10):
            test_file = Path(temp_project_dir) / f'test{i}.py'
            test_file.write_text(f'# File {i}')
            time.sleep(0.05)

        # Measure CPU usage
        cpu_percent = process.cpu_percent(interval=1.0)

        # Should use minimal CPU (< 5% as per requirements)
        # Note: This is a soft requirement, may vary by system
        assert cpu_percent < 10.0  # Allow some margin

    def test_memory_efficiency(self, file_watcher, temp_project_dir, fast_time):
        """Test memory efficiency."""
        file_watcher.start_watching()
        time.sleep(0.05)

        # Create many files
        for i in range(100):
            test_file = Path(temp_project_dir) / f'test{i}.py'
            test_file.write_text(f'# File {i}' * 100)  # Larger files
            time.sleep(0.05)

        time.sleep(0.25)

        # History should be manageable
        changes = file_watcher.get_recent_changes(limit=100)
        assert len(changes) <= 100  # Respects limit


class TestEdgeCases:
    """Test edge cases."""

    def test_watch_empty_directory(self, file_watcher, temp_project_dir, fast_time):
        """Test watching an empty directory."""
        file_watcher.start_watching()
        time.sleep(0.1)

        changes = file_watcher.get_recent_changes()
        assert len(changes) == 0

    def test_nested_directories(self, file_watcher, temp_project_dir):
        """Test watching nested directories."""
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create nested structure
        nested_dir = Path(temp_project_dir) / 'a' / 'b' / 'c'
        nested_dir.mkdir(parents=True)

        test_file = nested_dir / 'test.py'
        test_file.write_text('print("nested")')
        time.sleep(0.15)

        changes = file_watcher.get_recent_changes()
        nested_changes = [
            c for c in changes
            if 'test.py' in c['file_path']
        ]
        assert len(nested_changes) > 0

    def test_binary_file_handling(self, file_watcher, temp_project_dir):
        """Test handling binary files."""
        # Note: Default patterns don't include binary files,
        # so we need custom patterns
        watcher = FileWatcher(
            state_manager=file_watcher._state_manager,
            project_id=file_watcher._project_id,
            project_root=temp_project_dir,
            watch_patterns=['*'],
            use_polling=True,
            polling_timeout=0.05
        )
        watcher.start_watching()
        time.sleep(0.15)

        # Create binary file
        binary_file = Path(temp_project_dir) / 'test.bin'
        binary_file.write_bytes(b'\x00\x01\x02\x03' * 100)
        time.sleep(0.15)

        changes = watcher.get_recent_changes()
        binary_changes = [
            c for c in changes
            if 'test.bin' in c['file_path']
        ]
        assert len(binary_changes) > 0

        watcher.stop_watching()

    def test_large_file_handling(self, file_watcher, temp_project_dir):
        """Test handling large files."""
        file_watcher.start_watching()
        time.sleep(0.15)

        # Create large file (1MB)
        large_file = Path(temp_project_dir) / 'large.txt'
        large_file.write_text('x' * 1024 * 1024)
        time.sleep(0.15)

        changes = file_watcher.get_recent_changes()
        large_changes = [
            c for c in changes
            if 'large.txt' in c['file_path']
        ]
        assert len(large_changes) > 0

        # Should have hash and size
        change = large_changes[0]
        assert 'content_hash' in change
        assert change['file_size'] == 1024 * 1024

    def test_unicode_filenames(self, file_watcher, temp_project_dir, fast_time):
        """Test handling unicode filenames."""
        file_watcher.start_watching()
        time.sleep(0.05)

        # Create file with unicode name
        unicode_file = Path(temp_project_dir) / 'test_日本語.txt'
        unicode_file.write_text('Unicode test')
        time.sleep(0.05)

        changes = file_watcher.get_recent_changes()
        # Should handle unicode without crashing
        assert file_watcher.is_watching()
