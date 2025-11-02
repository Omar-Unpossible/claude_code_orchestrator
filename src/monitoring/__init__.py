"""Monitoring module for file watching and event detection.

This module provides:
- FileWatcher: Detects and tracks file changes in the project directory
- EventDetector: Detects significant events from file changes and patterns
"""

from src.monitoring.file_watcher import FileWatcher
from src.monitoring.event_detector import (
    EventDetector, FailurePattern, Event, ThresholdEvent
)

__all__ = [
    'FileWatcher',
    'EventDetector',
    'FailurePattern',
    'Event',
    'ThresholdEvent'
]
