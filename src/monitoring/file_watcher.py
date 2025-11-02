"""FileWatcher - Watches project directory for file changes.

This module implements file watching using the watchdog library with:
- Recursive directory watching
- Pattern-based filtering
- Event debouncing
- Content hashing for deduplication
- Thread-safe operation
- Integration with StateManager
"""

import logging
import hashlib
import time
from pathlib import Path
from typing import Callable, List, Dict, Optional, Set
from threading import RLock

from watchdog.observers import Observer  # type: ignore
from watchdog.observers.polling import PollingObserver  # type: ignore
from watchdog.events import (
    PatternMatchingEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent
)

from src.core.state import StateManager
from src.core.exceptions import StateManagerException

logger = logging.getLogger(__name__)


class FileWatcher:  # pylint: disable=too-many-instance-attributes
    """Watches project directory for file changes.

    The FileWatcher monitors file system changes and tracks them in StateManager.
    It provides:
    - Recursive directory watching
    - Pattern-based filtering (include/exclude)
    - Event debouncing (0.5s window)
    - Content hashing for deduplication
    - Thread-safe operations
    - Observer pattern for notifications

    Example:
        >>> state_manager = StateManager.get_instance('sqlite:///test.db')
        >>> watcher = FileWatcher(
        ...     state_manager=state_manager,
        ...     project_id=1,
        ...     project_root='/path/to/project'
        ... )
        >>> watcher.register_handler(lambda change: print(change))
        >>> watcher.start_watching('/path/to/project')
        >>> # ... later ...
        >>> changes = watcher.get_recent_changes(limit=10)
        >>> watcher.stop_watching()
    """

    # Default patterns
    DEFAULT_WATCH_PATTERNS = [
        "*.py", "*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.toml"
    ]
    DEFAULT_IGNORE_PATTERNS = [
        "*/__pycache__/*", "*.pyc", "*/.git/*", "*/.venv/*", "*/venv/*",
        "*/node_modules/*", "*/.pytest_cache/*", "*.log", "*/.mypy_cache/*",
        "*/__pycache__/*", "*/*.egg-info/*", "*/.tox/*", "*/build/*",
        "*/dist/*", "*/.coverage", "*/htmlcov/*"
    ]

    # Debounce window in seconds
    DEBOUNCE_WINDOW = 0.5

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        state_manager: StateManager,
        project_id: int,
        project_root: str,
        task_id: Optional[int] = None,
        watch_patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        debounce_window: float = DEBOUNCE_WINDOW,
        use_polling: bool = False,
        polling_timeout: float = 1.0
    ):
        """Initialize FileWatcher.

        Args:
            state_manager: StateManager instance for persisting changes
            project_id: Project ID for tracking changes
            project_root: Root directory to watch
            task_id: Optional task ID to associate changes with
            watch_patterns: File patterns to watch (default: DEFAULT_WATCH_PATTERNS)
            ignore_patterns: Patterns to ignore (default: DEFAULT_IGNORE_PATTERNS)
            debounce_window: Debounce window in seconds (default: 0.5)
            use_polling: Use PollingObserver instead of platform-native observer.
                        Recommended for tests and WSL2 environments for predictable
                        cleanup behavior (default: False)
            polling_timeout: Polling interval in seconds for PollingObserver.
                            Lower values detect changes faster but use more CPU.
                            Default: 1.0s (ignored if use_polling=False)

        Example:
            >>> watcher = FileWatcher(
            ...     state_manager=state_manager,
            ...     project_id=1,
            ...     project_root='/tmp/project',
            ...     watch_patterns=['*.py', '*.txt']
            ... )
        """
        self._state_manager = state_manager
        self._project_id = project_id
        self._project_root = Path(project_root).resolve()
        self._task_id = task_id
        self._watch_patterns = watch_patterns or self.DEFAULT_WATCH_PATTERNS
        self._ignore_patterns = ignore_patterns or self.DEFAULT_IGNORE_PATTERNS
        self._debounce_window = debounce_window
        self._use_polling = use_polling
        self._polling_timeout = polling_timeout

        # Thread safety
        self._lock = RLock()

        # Observer and handler
        self._observer: Optional[Observer] = None  # type: ignore
        self._event_handler: Optional[PatternMatchingEventHandler] = None

        # Watched paths
        self._watched_paths: Set[str] = set()

        # Change tracking
        self._change_history: List[Dict] = []

        # Debouncing - track last event time per file
        self._last_event_time: Dict[str, float] = {}

        # Registered callbacks
        self._callbacks: List[Callable[[Dict], None]] = []

        logger.info(
            "FileWatcher initialized for project %s at %s",
            project_id, project_root
        )

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            MD5 hash as hex string

        Raises:
            IOError: If file cannot be read
        """
        try:
            hasher = hashlib.md5()
            with open(file_path, 'rb') as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as exc:
            logger.warning("Failed to hash %s: %s", file_path, exc)
            return ""

    def _get_relative_path(self, absolute_path: str) -> str:
        """Get path relative to project root.

        Args:
            absolute_path: Absolute file path

        Returns:
            Relative path as string
        """
        try:
            return str(Path(absolute_path).relative_to(self._project_root))
        except ValueError:
            # Path is not relative to project root
            return absolute_path

    def _should_debounce(self, file_path: str) -> bool:
        """Check if event should be debounced.

        Args:
            file_path: File path

        Returns:
            True if event should be debounced (ignored)
        """
        current_time = time.time()
        last_time = self._last_event_time.get(file_path, 0)

        if current_time - last_time < self._debounce_window:
            return True

        self._last_event_time[file_path] = current_time
        return False

    def _is_temporary_file(self, file_path: str) -> bool:
        """Check if file is temporary.

        Args:
            file_path: File path

        Returns:
            True if file is temporary (should be ignored)
        """
        # Common temporary file patterns
        temp_patterns = [
            '.swp', '.swo', '.tmp', '~', '.bak',
            '.DS_Store', 'Thumbs.db', '.#'
        ]

        file_name = Path(file_path).name
        return any(
            file_name.endswith(pattern) or file_name.startswith(pattern)
            for pattern in temp_patterns
        )

    def _process_file_event(
        self,
        event_type: str,
        file_path: str
    ) -> None:
        """Process a file system event.

        Args:
            event_type: Event type ('created', 'modified', 'deleted')
            file_path: Absolute file path
        """
        with self._lock:
            try:
                # Skip temporary files
                if self._is_temporary_file(file_path):
                    logger.debug("Skipping temporary file: %s", file_path)
                    return

                # Debounce rapid changes
                if self._should_debounce(file_path):
                    logger.debug("Debouncing %s event for: %s", event_type, file_path)
                    return

                # Get relative path
                relative_path = self._get_relative_path(file_path)

                # Prepare change data
                change_data = {
                    'file_path': relative_path,
                    'change_type': event_type,
                    'timestamp': time.time(),
                    'absolute_path': file_path
                }

                path_obj = Path(file_path)

                # Calculate hash and size for created/modified files
                if event_type in ('created', 'modified') and path_obj.exists():
                    try:
                        file_hash = self._calculate_hash(path_obj)
                        file_size = path_obj.stat().st_size

                        change_data['content_hash'] = file_hash
                        change_data['file_size'] = file_size

                        # Record in StateManager
                        self._state_manager.record_file_change(
                            project_id=self._project_id,
                            task_id=self._task_id,
                            file_path=relative_path,
                            file_hash=file_hash,
                            file_size=file_size,
                            change_type=event_type
                        )

                        logger.info(
                            "File %s: %s (size: %s, hash: %s...)",
                            event_type, relative_path, file_size, file_hash[:8]
                        )
                    except Exception as exc:
                        logger.error(
                            "Failed to process %s for %s: %s",
                            event_type, file_path, exc
                        )
                        return

                elif event_type == 'deleted':
                    # For deleted files, we don't have hash/size
                    change_data['content_hash'] = ''
                    change_data['file_size'] = 0

                    # Record in StateManager
                    self._state_manager.record_file_change(
                        project_id=self._project_id,
                        task_id=self._task_id,
                        file_path=relative_path,
                        file_hash='',
                        file_size=0,
                        change_type=event_type
                    )

                    logger.info("File deleted: %s", relative_path)

                # Add to history
                self._change_history.append(change_data)

                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(change_data)
                    except Exception as exc:
                        logger.error("Callback failed: %s", exc)

            except StateManagerException as exc:
                logger.error("Failed to record file change: %s", exc)
            except Exception as exc:
                logger.error("Unexpected error processing file event: %s", exc)

    def _on_created(self, event: FileCreatedEvent) -> None:
        """Handle file created event.

        Args:
            event: File created event
        """
        if not event.is_directory:
            self._process_file_event('created', str(event.src_path))

    def _on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modified event.

        Args:
            event: File modified event
        """
        if not event.is_directory:
            self._process_file_event('modified', str(event.src_path))

    def _on_deleted(self, event: FileDeletedEvent) -> None:
        """Handle file deleted event.

        Args:
            event: File deleted event
        """
        if not event.is_directory:
            self._process_file_event('deleted', str(event.src_path))

    def start_watching(self, path: Optional[str] = None) -> None:
        """Start watching directory for changes.

        Args:
            path: Directory path to watch (default: project_root)

        Raises:
            ValueError: If already watching
            FileNotFoundError: If path doesn't exist
        """
        with self._lock:
            if self._observer is not None and self._observer.is_alive():
                raise ValueError("Already watching. Call stop_watching() first.")

            watch_path = Path(path) if path else self._project_root
            if not watch_path.exists():
                raise FileNotFoundError(f"Path does not exist: {watch_path}")

            # Create event handler
            self._event_handler = PatternMatchingEventHandler(
                patterns=self._watch_patterns,
                ignore_patterns=self._ignore_patterns,
                ignore_directories=False,
                case_sensitive=True
            )

            # Register event handlers
            self._event_handler.on_created = self._on_created  # type: ignore
            self._event_handler.on_modified = self._on_modified  # type: ignore
            self._event_handler.on_deleted = self._on_deleted  # type: ignore

            # Create and start observer
            # Use PollingObserver for tests/WSL2 for predictable cleanup
            if self._use_polling:
                self._observer = PollingObserver(timeout=self._polling_timeout)
                logger.debug(
                    "Using PollingObserver for predictable cleanup "
                    "(polling interval: %.2fs)", self._polling_timeout
                )
            else:
                self._observer = Observer()
                logger.debug("Using platform-native Observer")

            self._observer.schedule(
                self._event_handler,
                str(watch_path),
                recursive=True
            )
            self._observer.start()

            # Track watched path
            self._watched_paths.add(str(watch_path.resolve()))

            logger.info("Started watching: %s", watch_path)

    def stop_watching(self) -> None:
        """Stop watching for file changes.

        Safe to call multiple times. Uses graceful shutdown with timeout
        and forced cleanup if observer thread doesn't terminate.
        """
        with self._lock:
            if self._observer is not None:
                logger.debug("Stopping observer...")
                self._observer.stop()

                # Wait for observer thread to terminate
                # WSL2's filesystem emulation is slow, so we use a longer timeout
                self._observer.join(timeout=2.0)

                # Check if thread actually terminated
                if self._observer.is_alive():
                    logger.warning(
                        "Observer thread did not terminate within timeout, "
                        "forcing cleanup"
                    )
                    # Thread is still alive after timeout - this is a known issue
                    # with watchdog on WSL2/slow filesystems. We null the reference
                    # to avoid blocking, but note the thread may linger briefly.
                    # The Python GC and OS will eventually clean it up.
                else:
                    logger.debug("Observer thread terminated cleanly")

                self._observer = None
                logger.info("Stopped watching")

            self._watched_paths.clear()
            self._event_handler = None

    def is_watching(self) -> bool:
        """Check if currently watching for changes.

        Returns:
            True if watching, False otherwise
        """
        with self._lock:
            return (
                self._observer is not None
                and self._observer.is_alive()
            )

    def get_watched_paths(self) -> List[str]:
        """Get list of currently watched paths.

        Returns:
            List of watched directory paths
        """
        with self._lock:
            return list(self._watched_paths)

    def get_recent_changes(self, limit: int = 100) -> List[Dict]:
        """Get recent file changes.

        Args:
            limit: Maximum number of changes to return (default: 100)

        Returns:
            List of change dictionaries (most recent first)

        Example:
            >>> changes = watcher.get_recent_changes(limit=10)
            >>> for change in changes:
            ...     print(f"{change['change_type']}: {change['file_path']}")
        """
        with self._lock:
            # Return most recent first
            return list(reversed(self._change_history[-limit:]))

    def register_handler(self, callback: Callable[[Dict], None]) -> None:
        """Register a callback for file change notifications.

        The callback will be called with a change dictionary containing:
        - file_path: Relative file path
        - change_type: 'created', 'modified', or 'deleted'
        - timestamp: Unix timestamp
        - content_hash: MD5 hash (if available)
        - file_size: Size in bytes (if available)

        Args:
            callback: Callable that takes a change dictionary

        Example:
            >>> def on_change(change):
            ...     print(f"File changed: {change['file_path']}")
            >>> watcher.register_handler(on_change)
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
                logger.debug("Registered callback: %s", callback.__name__)

    def unregister_handler(self, callback: Callable[[Dict], None]) -> None:
        """Unregister a callback.

        Args:
            callback: Callback to remove
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                logger.debug("Unregistered callback: %s", callback.__name__)

    def clear_history(self) -> None:
        """Clear change history.

        Note: This only clears the in-memory history, not the StateManager records.
        """
        with self._lock:
            self._change_history.clear()
            self._last_event_time.clear()
            logger.debug("Cleared change history")

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about file changes.

        Returns:
            Dictionary with statistics:
            - total_changes: Total number of changes
            - created: Number of files created
            - modified: Number of files modified
            - deleted: Number of files deleted

        Example:
            >>> stats = watcher.get_statistics()
            >>> print(f"Total changes: {stats['total_changes']}")
        """
        with self._lock:
            stats = {
                'total_changes': len(self._change_history),
                'created': 0,
                'modified': 0,
                'deleted': 0
            }

            for change in self._change_history:
                change_type = change.get('change_type', '')
                if change_type in stats:
                    stats[change_type] += 1

            return stats

    def __enter__(self):
        """Context manager entry."""
        self.start_watching()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_watching()
        return False
