"""Monitoring module for file watching and event detection.

This module provides:
- FileWatcher: Detects and tracks file changes in the project directory
- EventDetector: Detects significant events from file changes and patterns
- ProductionLogger: Structured JSON logging for production monitoring
"""

from src.monitoring.file_watcher import FileWatcher
from src.monitoring.event_detector import (
    EventDetector, FailurePattern, Event, ThresholdEvent
)
from src.monitoring.production_logger import ProductionLogger

__all__ = [
    'FileWatcher',
    'EventDetector',
    'FailurePattern',
    'Event',
    'ThresholdEvent',
    'ProductionLogger'
]
