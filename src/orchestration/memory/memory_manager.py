"""Memory Manager orchestrator for context management system.

This module provides the MemoryManager class which coordinates all memory
components including context window detection, adaptive optimization,
working memory, context optimization, and usage tracking.

Classes:
    MemoryManager: Orchestrator for all memory components
    MemoryManagerException: Exception for memory manager errors

Example:
    >>> model_config = {'context_window': 128000, 'model': 'qwen2.5-coder:32b'}
    >>> manager = MemoryManager(model_config=model_config)
    >>> manager.add_operation({'type': 'task', 'data': {...}, 'tokens': 500})
    >>> context = manager.build_context()
    >>> checkpoint_path = manager.checkpoint()

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from threading import RLock

from .context_window_detector import ContextWindowDetector
from .adaptive_optimizer import AdaptiveOptimizer
from .working_memory import WorkingMemory
from .context_optimizer import ContextOptimizer
from .context_window_manager import ContextWindowManager

logger = logging.getLogger(__name__)


class MemoryManagerException(Exception):
    """Exception raised for memory manager errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            context: Additional context about the error
        """
        super().__init__(message)
        self.context = context or {}
        logger.error(f"MemoryManagerException: {message}", extra=context)


class MemoryManager:
    """Orchestrator for all memory management components.

    Coordinates context window detection, adaptive optimization, working memory,
    context optimization, and usage tracking. Provides unified API for all
    memory operations and manages component lifecycle.

    Thread-safe: Yes (uses RLock for concurrent operations)

    Attributes:
        context_window_size: Detected or configured context window size
        model_name: Name of the LLM model
        detector: ContextWindowDetector instance
        adaptive_optimizer: AdaptiveOptimizer instance
        working_memory: WorkingMemory instance
        context_optimizer: ContextOptimizer instance
        window_manager: ContextWindowManager instance
        llm_interface: Optional LLM interface for summarization
        config: Configuration dictionary
        checkpoint_dir: Directory for checkpoint files

    Example:
        >>> config = {'context_window': 128000, 'model': 'qwen2.5-coder:32b'}
        >>> manager = MemoryManager(model_config=config)
        >>> manager.add_operation({
        ...     'type': 'task',
        ...     'operation': 'create_task',
        ...     'data': {'title': 'Example'},
        ...     'tokens': 500
        ... })
        >>> context = manager.build_context()
        >>> status = manager.get_status()
    """

    DEFAULT_CONFIG = {
        'artifact_storage_path': '.obra/memory/artifacts',
        'archive_path': '.obra/archive',
        'checkpoint_dir': '.obra/memory/checkpoints',
        'utilization_limit': 0.85,  # Use 85% of context window
        'summarization_threshold': 500,
        'externalization_threshold': 2000,
    }

    def __init__(
        self,
        model_config: Dict[str, Any],
        llm_interface: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        checkpoint_path: Optional[str] = None
    ):
        """Initialize MemoryManager and all components.

        Args:
            model_config: Model configuration dictionary
                Required: one of 'context_window' (int) or both 'provider' + 'model'
                Optional: 'provider', 'model' for auto-detection
            llm_interface: Optional LLM interface for summarization
            config: Optional configuration overrides
            checkpoint_path: Optional path to checkpoint file for restoration

        Raises:
            ValueError: If model_config missing required fields
            MemoryManagerException: If initialization fails

        Example:
            >>> # With explicit context window
            >>> config = {'context_window': 128000}
            >>> manager = MemoryManager(model_config=config)
            >>>
            >>> # With auto-detection
            >>> config = {'provider': 'ollama', 'model': 'qwen2.5-coder:32b'}
            >>> manager = MemoryManager(model_config=config)
            >>>
            >>> # With LLM interface for summarization
            >>> manager = MemoryManager(model_config=config, llm_interface=llm)
        """
        # Thread safety
        self._lock = RLock()

        # Merge configurations
        self.config = {**self.DEFAULT_CONFIG}
        if config:
            self.config.update(config)

        # Store LLM interface
        self.llm_interface = llm_interface

        # Extract model info
        self.model_name = model_config.get('model', 'unknown')
        self.provider = model_config.get('provider', 'unknown')

        # Step 1: Detect or use configured context window size
        if 'context_window' in model_config:
            self.context_window_size = model_config['context_window']
            logger.info(
                f"Using configured context window: {self.context_window_size:,} tokens"
            )
        else:
            # Auto-detect
            if 'provider' not in model_config or 'model' not in model_config:
                raise ValueError(
                    "model_config must contain either 'context_window' or "
                    "both 'provider' and 'model' for auto-detection"
                )

            self.detector = ContextWindowDetector(
                fallback_size=self.config.get('fallback_context_window', 16384)
            )
            self.context_window_size = self.detector.detect(
                self.provider,
                self.model_name
            )
            logger.info(
                f"Detected context window: {self.context_window_size:,} tokens "
                f"for {self.provider}/{self.model_name}"
            )

        if not hasattr(self, 'detector'):
            # Create detector even if not used for detection
            self.detector = ContextWindowDetector()

        # Update model_config with detected size for component initialization
        model_config_with_size = {**model_config, 'context_window': self.context_window_size}

        # Step 2: Initialize AdaptiveOptimizer (selects optimization profile)
        self.adaptive_optimizer = AdaptiveOptimizer(
            context_window_size=self.context_window_size,
            config_path=self.config.get('optimization_profiles_path'),
            manual_override=self.config.get('profile_override'),
            custom_thresholds=self.config.get('custom_thresholds')
        )

        active_profile = self.adaptive_optimizer.get_active_profile()
        logger.info(f"Selected optimization profile: {active_profile['name']}")

        # Step 3: Initialize WorkingMemory with profile configuration
        wm_config = self.adaptive_optimizer.get_working_memory_config()
        wm_config['context_window'] = self.context_window_size
        self.working_memory = WorkingMemory(wm_config)

        # Step 4: Initialize ContextOptimizer with profile configuration
        optimizer_config = {
            'artifact_storage_path': self.config['artifact_storage_path'],
            'archive_path': self.config['archive_path'],
            'summarization_threshold': active_profile.get(
                'summarization_threshold',
                self.config['summarization_threshold']
            ),
            'externalization_threshold': active_profile.get(
                'externalization_threshold',
                self.config['externalization_threshold']
            ),
        }
        # Add pruning config from profile
        pruning_config = self.adaptive_optimizer.get_pruning_config()
        optimizer_config.update(pruning_config)

        self.context_optimizer = ContextOptimizer(
            llm_interface=llm_interface,
            config=optimizer_config
        )

        # Step 5: Initialize ContextWindowManager for usage tracking
        self.window_manager = ContextWindowManager(
            model_config=model_config_with_size,
            utilization_limit=self.config['utilization_limit']
        )

        # Checkpoint management
        self.checkpoint_dir = self.config['checkpoint_dir']
        self._operation_count = 0  # Track operations for checkpoint triggers
        self._last_checkpoint_time = datetime.now(timezone.utc)

        # Create storage directories
        self._ensure_directories()

        logger.info(
            f"MemoryManager initialized: "
            f"context={self.context_window_size:,}, "
            f"profile={active_profile['name']}, "
            f"effective_max={self.window_manager.effective_max_tokens:,}"
        )

        # Restore from checkpoint if provided
        if checkpoint_path:
            self.restore(checkpoint_path)

    def _ensure_directories(self) -> None:
        """Create required storage directories if they don't exist."""
        directories = [
            self.config['artifact_storage_path'],
            self.config['archive_path'],
            self.checkpoint_dir
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {directory}")

    def add_operation(self, operation: Dict[str, Any]) -> None:
        """Add operation to working memory and update usage tracking.

        Automatically adds timestamp, operation name, and estimates tokens if missing.
        Thread-safe operation.

        Args:
            operation: Operation dictionary with keys:
                - type (str): Operation type (task, validation, etc.)
                - operation (str, optional): Operation name (defaults to 'unknown')
                - data (dict, optional): Operation data
                - tokens (int, optional): Token count (estimated if missing)
                - timestamp (str, optional): ISO timestamp (added if missing)

        Example:
            >>> manager.add_operation({
            ...     'type': 'task',
            ...     'operation': 'create_task',
            ...     'data': {'title': 'New Task'},
            ...     'tokens': 500
            ... })
        """
        with self._lock:
            # Add timestamp if missing
            if 'timestamp' not in operation:
                operation['timestamp'] = datetime.now(timezone.utc).isoformat()

            # Add operation name if missing (required by WorkingMemory)
            if 'operation' not in operation:
                operation['operation'] = 'unknown'

            # Estimate tokens if missing
            if 'tokens' not in operation:
                operation['tokens'] = self._estimate_tokens(operation)
                logger.debug(
                    f"Estimated {operation['tokens']} tokens for operation "
                    f"type={operation.get('type')}"
                )

            # Add to working memory
            self.working_memory.add_operation(operation)

            # Update usage tracking
            self.window_manager.add_usage(operation['tokens'])

            # Increment operation count
            self._operation_count += 1

            logger.debug(
                f"Added operation: type={operation.get('type')}, "
                f"operation={operation.get('operation')}, "
                f"tokens={operation['tokens']}, "
                f"total_usage={self.window_manager.used_tokens():,}, "
                f"zone={self.window_manager.get_zone()}"
            )

    def _estimate_tokens(self, operation: Dict[str, Any]) -> int:
        """Estimate token count for operation without explicit tokens.

        Uses simple heuristic: ~4 characters per token.

        Args:
            operation: Operation dictionary

        Returns:
            Estimated token count
        """
        # Serialize operation data to estimate size
        try:
            data_str = json.dumps(operation.get('data', {}))
            # Rough estimate: 4 characters per token
            estimated = max(50, len(data_str) // 4)
            return estimated
        except Exception as e:
            logger.warning(f"Token estimation failed: {e}, using default 100")
            return 100

    def get_recent_operations(
        self,
        limit: Optional[int] = None,
        operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent operations from working memory.

        Args:
            limit: Maximum number of operations to return (None = all)
            operation_type: Filter by operation type (None = all types)

        Returns:
            List of operation dictionaries, most recent first

        Example:
            >>> # Get 5 most recent operations
            >>> recent = manager.get_recent_operations(limit=5)
            >>>
            >>> # Get recent task operations
            >>> tasks = manager.get_recent_operations(operation_type='task')
        """
        with self._lock:
            if operation_type:
                return self.working_memory.get_operations(
                    operation_type=operation_type,
                    limit=limit or 100
                )
            else:
                return self.working_memory.get_recent_operations(limit=limit)

    def build_context(
        self,
        base_context: Optional[Dict[str, Any]] = None,
        optimize: bool = True
    ) -> Dict[str, Any]:
        """Build context dictionary for LLM from working memory.

        Fetches recent operations from working memory and optionally applies
        optimization techniques based on the active profile.

        Args:
            base_context: Optional base context to merge with operations
            optimize: Whether to apply optimization techniques (default: True)

        Returns:
            Context dictionary with operations and metadata

        Example:
            >>> # Build optimized context
            >>> context = manager.build_context()
            >>>
            >>> # Build with base context
            >>> context = manager.build_context(
            ...     base_context={'project': 'MyProject'},
            ...     optimize=True
            ... )
        """
        with self._lock:
            # Start with base context or empty dict
            context = base_context.copy() if base_context else {}

            # Add recent operations from working memory
            operations = self.working_memory.get_recent_operations()
            context['operations'] = operations

            # Add metadata
            context['metadata'] = {
                'context_window_size': self.context_window_size,
                'optimization_profile': self.adaptive_optimizer.get_active_profile()['name'],
                'current_usage': self.window_manager.used_tokens(),
                'zone': self.window_manager.get_zone(),
                'operation_count': len(operations),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            # Apply optimization if enabled
            if optimize and operations:
                logger.debug("Applying context optimization")
                result = self.context_optimizer.optimize_context(
                    context=context,
                    target_reduction=0.3  # Target 30% reduction
                )

                # Update metadata with optimization results
                context['metadata']['optimization'] = {
                    'tokens_before': result.tokens_before,
                    'tokens_after': result.tokens_after,
                    'compression_ratio': result.compression_ratio,
                    'techniques_applied': result.techniques_applied
                }

                logger.info(
                    f"Context optimized: {result.tokens_before:,} → "
                    f"{result.tokens_after:,} tokens "
                    f"({result.compression_ratio:.2%} compression)"
                )

            return context

    def checkpoint(self, path: Optional[str] = None) -> str:
        """Save current state to checkpoint file.

        Serializes state of all components to JSON file. Includes working memory,
        window manager usage, and metadata.

        Args:
            path: Optional custom checkpoint file path
                If None, generates timestamped filename in checkpoint_dir

        Returns:
            Path to created checkpoint file

        Raises:
            MemoryManagerException: If checkpoint creation fails

        Example:
            >>> # Auto-generated filename
            >>> path = manager.checkpoint()
            >>>
            >>> # Custom filename
            >>> path = manager.checkpoint('/custom/checkpoint.json')
        """
        with self._lock:
            try:
                # Generate checkpoint path if not provided
                if path is None:
                    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                    filename = f'checkpoint_{timestamp}.json'
                    path = str(Path(self.checkpoint_dir) / filename)

                # Ensure parent directory exists
                Path(path).parent.mkdir(parents=True, exist_ok=True)

                # Build checkpoint data
                checkpoint_data = {
                    'version': '1.0.0',
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'context_window_size': self.context_window_size,
                    'model_name': self.model_name,
                    'optimization_profile': self.adaptive_optimizer.get_active_profile()['name'],
                    'working_memory': {
                        'operations': self.working_memory.get_recent_operations(),
                        'current_tokens': self.working_memory._current_tokens,
                        'max_operations': self.working_memory.max_operations,
                        'max_tokens': self.working_memory.max_tokens
                    },
                    'window_manager': {
                        'used_tokens': self.window_manager.used_tokens(),
                        'max_tokens': self.window_manager.max_tokens,
                        'effective_max_tokens': self.window_manager.effective_max_tokens,
                        'utilization_limit': self.window_manager.utilization_limit
                    },
                    'metadata': {
                        'operation_count': self._operation_count,
                        'last_checkpoint_time': self._last_checkpoint_time.isoformat()
                    }
                }

                # Write to file
                with open(path, 'w') as f:
                    json.dump(checkpoint_data, f, indent=2)

                self._last_checkpoint_time = datetime.now(timezone.utc)

                logger.info(f"Checkpoint created: {path}")
                return path

            except Exception as e:
                raise MemoryManagerException(
                    f"Failed to create checkpoint: {e}",
                    context={'path': path}
                ) from e

    def restore(self, path: str) -> None:
        """Restore state from checkpoint file.

        Loads checkpoint data and restores state of all components.

        Args:
            path: Path to checkpoint file

        Raises:
            MemoryManagerException: If checkpoint file doesn't exist or restore fails

        Example:
            >>> manager.restore('/path/to/checkpoint.json')
        """
        with self._lock:
            checkpoint_path = Path(path)
            if not checkpoint_path.exists():
                raise MemoryManagerException(
                    f"Checkpoint file not found: {path}",
                    context={'path': path}
                )

            try:
                # Load checkpoint data
                with open(checkpoint_path) as f:
                    checkpoint_data = json.load(f)

                logger.info(
                    f"Restoring from checkpoint: {path} "
                    f"(created: {checkpoint_data.get('timestamp')})"
                )

                # Restore working memory operations
                wm_data = checkpoint_data.get('working_memory', {})
                for operation in wm_data.get('operations', []):
                    # Don't update usage again - will be done when we restore window manager
                    self.working_memory.add_operation(operation)

                # Restore window manager usage
                wm_mgr_data = checkpoint_data.get('window_manager', {})
                if 'used_tokens' in wm_mgr_data:
                    # Reset and restore usage
                    self.window_manager.reset()
                    self.window_manager.add_usage(wm_mgr_data['used_tokens'])

                # Restore metadata
                metadata = checkpoint_data.get('metadata', {})
                self._operation_count = metadata.get('operation_count', 0)

                if 'last_checkpoint_time' in metadata:
                    self._last_checkpoint_time = datetime.fromisoformat(
                        metadata['last_checkpoint_time']
                    )

                logger.info(
                    f"Checkpoint restored: {len(wm_data.get('operations', []))} operations, "
                    f"{wm_mgr_data.get('used_tokens', 0):,} tokens used"
                )

            except Exception as e:
                raise MemoryManagerException(
                    f"Failed to restore from checkpoint: {e}",
                    context={'path': path}
                ) from e

    def should_checkpoint(self) -> bool:
        """Check if checkpoint is needed based on profile configuration.

        Checks both operation count and usage percentage thresholds.

        Returns:
            True if checkpoint should be created

        Example:
            >>> if manager.should_checkpoint():
            ...     manager.checkpoint()
        """
        with self._lock:
            profile = self.adaptive_optimizer.get_active_profile()

            # Check operation count threshold
            checkpoint_op_count = profile.get('checkpoint_operation_count', float('inf'))
            if self._operation_count >= checkpoint_op_count:
                logger.debug(
                    f"Checkpoint needed: operation count {self._operation_count} "
                    f">= threshold {checkpoint_op_count}"
                )
                return True

            # Check usage percentage threshold
            checkpoint_pct = profile.get('checkpoint_threshold_pct', 100) / 100.0
            threshold_tokens = int(self.context_window_size * checkpoint_pct)
            if self.window_manager.used_tokens() >= threshold_tokens:
                logger.debug(
                    f"Checkpoint needed: usage {self.window_manager.used_tokens():,} "
                    f">= threshold {threshold_tokens:,} ({checkpoint_pct:.0%})"
                )
                return True

            return False

    def clear(self) -> None:
        """Clear working memory and reset usage tracking.

        Example:
            >>> manager.clear()
            >>> assert len(manager.get_recent_operations()) == 0
        """
        with self._lock:
            self.working_memory.clear()
            self.window_manager.reset()
            self._operation_count = 0
            logger.info("Memory cleared: working memory and usage reset")

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all components.

        Returns:
            Status dictionary with component details

        Example:
            >>> status = manager.get_status()
            >>> print(f"Zone: {status['window_manager']['zone']}")
            >>> print(f"Operations: {status['working_memory']['operation_count']}")
        """
        with self._lock:
            wm_status = self.working_memory.get_status()

            return {
                'context_window': {
                    'size': self.context_window_size,
                    'model': self.model_name,
                    'provider': self.provider
                },
                'optimization_profile': {
                    'name': self.adaptive_optimizer.get_active_profile()['name'],
                    'description': self.adaptive_optimizer.get_active_profile()['description']
                },
                'working_memory': {
                    'operation_count': wm_status['operation_count'],
                    'current_tokens': wm_status['current_tokens'],
                    'max_operations': wm_status['max_operations'],
                    'max_tokens': wm_status['max_tokens'],
                    'eviction_count': wm_status['eviction_count']
                },
                'window_manager': {
                    'used_tokens': self.window_manager.used_tokens(),
                    'effective_max_tokens': self.window_manager.effective_max_tokens,
                    'utilization_pct': self.window_manager.usage_percentage(),
                    'zone': self.window_manager.get_zone()
                },
                'checkpoint_needed': self.should_checkpoint(),
                'total_operation_count': self._operation_count
            }
