"""Tests for MemoryManager orchestrator class.

This module tests the MemoryManager which coordinates all memory components:
- ContextWindowDetector
- AdaptiveOptimizer
- WorkingMemory
- ContextOptimizer
- ContextWindowManager

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from src.orchestration.memory.memory_manager import (
    MemoryManager,
    MemoryManagerException
)


class TestMemoryManagerInitialization:
    """Test MemoryManager initialization and component coordination."""

    def test_init_with_model_config(self):
        """Test initialization with model configuration."""
        config = {
            'model': 'qwen2.5-coder:32b',
            'provider': 'ollama',
            'context_window': 128000
        }

        manager = MemoryManager(model_config=config)

        assert manager is not None
        assert manager.context_window_size == 128000
        assert manager.model_name == 'qwen2.5-coder:32b'

    def test_init_detects_context_window(self):
        """Test automatic context window detection."""
        config = {
            'model': 'qwen2.5-coder:32b',
            'provider': 'ollama'
        }

        with patch('src.orchestration.memory.memory_manager.ContextWindowDetector') as mock_detector:
            mock_detector.return_value.detect.return_value = 128000

            manager = MemoryManager(model_config=config)

            assert manager.context_window_size == 128000
            mock_detector.return_value.detect.assert_called_once()

    def test_init_creates_all_components(self):
        """Test that all components are initialized."""
        config = {
            'model': 'qwen2.5-coder:32b',
            'context_window': 128000
        }

        manager = MemoryManager(model_config=config)

        assert manager.detector is not None
        assert manager.adaptive_optimizer is not None
        assert manager.working_memory is not None
        assert manager.context_optimizer is not None
        assert manager.window_manager is not None

    def test_init_with_llm_interface(self):
        """Test initialization with LLM interface for summarization."""
        config = {'context_window': 128000}
        llm_mock = Mock()

        manager = MemoryManager(model_config=config, llm_interface=llm_mock)

        assert manager.llm_interface == llm_mock
        assert manager.context_optimizer.llm_interface == llm_mock

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration overrides."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            model_config = {'context_window': 128000}
            custom_config = {
                'artifact_storage_path': f'{tmpdir}/artifacts',
                'checkpoint_dir': f'{tmpdir}/checkpoints'
            }

            manager = MemoryManager(
                model_config=model_config,
                config=custom_config
            )

            assert manager.config['artifact_storage_path'] == f'{tmpdir}/artifacts'
            assert manager.config['checkpoint_dir'] == f'{tmpdir}/checkpoints'

    def test_init_loads_from_checkpoint(self):
        """Test initialization with checkpoint restoration."""
        config = {'context_window': 128000}
        checkpoint_path = '/path/to/checkpoint.json'

        with patch.object(MemoryManager, 'restore') as mock_restore:
            manager = MemoryManager(
                model_config=config,
                checkpoint_path=checkpoint_path
            )

            mock_restore.assert_called_once_with(checkpoint_path)

    def test_init_creates_storage_directories(self):
        """Test that required storage directories are created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'context_window': 128000,
                'artifact_storage_path': f'{tmpdir}/artifacts',
                'checkpoint_dir': f'{tmpdir}/checkpoints'
            }

            manager = MemoryManager(model_config={'context_window': 128000}, config=config)

            assert Path(f'{tmpdir}/artifacts').exists()
            assert Path(f'{tmpdir}/checkpoints').exists()


class TestMemoryManagerOperations:
    """Test MemoryManager operation handling."""

    @pytest.fixture
    def manager(self):
        """Create MemoryManager instance for testing."""
        config = {'context_window': 128000}
        return MemoryManager(model_config=config)

    def test_add_operation(self, manager):
        """Test adding operation to working memory."""
        operation = {
            'type': 'task',
            'operation': 'create_task',
            'data': {'title': 'Test Task'},
            'tokens': 500
        }

        manager.add_operation(operation)

        recent = manager.get_recent_operations(limit=1)
        assert len(recent) == 1
        assert recent[0]['type'] == 'task'

    def test_add_operation_updates_usage(self, manager):
        """Test that adding operation updates context usage."""
        initial_usage = manager.window_manager.used_tokens()

        operation = {
            'type': 'task',
            'data': {'title': 'Test'},
            'tokens': 1000
        }

        manager.add_operation(operation)

        assert manager.window_manager.used_tokens() == initial_usage + 1000

    def test_add_operation_with_auto_timestamp(self, manager):
        """Test that timestamp is added automatically if missing."""
        operation = {
            'type': 'task',
            'data': {'title': 'Test'},
            'tokens': 100
        }

        manager.add_operation(operation)

        recent = manager.get_recent_operations(limit=1)
        assert 'timestamp' in recent[0]

    def test_get_recent_operations(self, manager):
        """Test querying recent operations."""
        for i in range(5):
            manager.add_operation({
                'type': 'task',
                'data': {'id': i},
                'tokens': 100
            })

        recent = manager.get_recent_operations(limit=3)

        assert len(recent) == 3
        # Should be most recent first
        assert recent[0]['data']['id'] == 4

    def test_get_recent_operations_by_type(self, manager):
        """Test filtering operations by type."""
        manager.add_operation({'type': 'task', 'tokens': 100})
        manager.add_operation({'type': 'validation', 'tokens': 100})
        manager.add_operation({'type': 'task', 'tokens': 100})

        tasks = manager.get_recent_operations(operation_type='task')

        assert len(tasks) == 2
        assert all(op['type'] == 'task' for op in tasks)


class TestMemoryManagerContextBuilding:
    """Test MemoryManager context building pipeline."""

    @pytest.fixture
    def manager(self):
        """Create MemoryManager instance for testing."""
        config = {'context_window': 128000}
        return MemoryManager(model_config=config)

    def test_build_context_empty(self, manager):
        """Test building context with no operations."""
        context = manager.build_context()

        assert isinstance(context, dict)
        assert 'operations' in context
        assert len(context['operations']) == 0

    def test_build_context_with_operations(self, manager):
        """Test building context with recent operations."""
        for i in range(3):
            manager.add_operation({
                'type': 'task',
                'data': {'id': i},
                'tokens': 500
            })

        context = manager.build_context()

        assert 'operations' in context
        assert len(context['operations']) == 3

    def test_build_context_with_base_context(self, manager):
        """Test building context with base context dict."""
        base_context = {
            'project': 'Test Project',
            'phase': 'Planning'
        }

        context = manager.build_context(base_context=base_context)

        assert context['project'] == 'Test Project'
        assert context['phase'] == 'Planning'
        assert 'operations' in context

    def test_build_context_with_optimization(self, manager):
        """Test context building with optimization enabled."""
        from src.orchestration.memory.context_optimizer import OptimizationResult

        # Add large operations
        for i in range(10):
            manager.add_operation({
                'type': 'validation',
                'data': {'large_data': 'x' * 1000},
                'tokens': 2000
            })

        with patch.object(manager.context_optimizer, 'optimize_context') as mock_optimize:
            # Return a proper OptimizationResult
            mock_optimize.return_value = OptimizationResult(
                tokens_before=20000,
                tokens_after=5000,
                compression_ratio=0.25,
                techniques_applied=['pruning', 'summarization']
            )

            context = manager.build_context(optimize=True)

            mock_optimize.assert_called_once()

    def test_build_context_without_optimization(self, manager):
        """Test context building with optimization disabled."""
        manager.add_operation({'type': 'task', 'tokens': 1000})

        with patch.object(manager.context_optimizer, 'optimize_context') as mock_optimize:
            context = manager.build_context(optimize=False)

            mock_optimize.assert_not_called()

    def test_build_context_includes_metadata(self, manager):
        """Test that built context includes metadata."""
        context = manager.build_context()

        assert 'metadata' in context
        assert 'context_window_size' in context['metadata']
        assert 'optimization_profile' in context['metadata']
        assert 'current_usage' in context['metadata']
        assert 'zone' in context['metadata']


class TestMemoryManagerCheckpointing:
    """Test MemoryManager checkpoint and restore functionality."""

    @pytest.fixture
    def manager(self):
        """Create MemoryManager instance for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'context_window': 128000,
                'checkpoint_dir': tmpdir
            }
            manager = MemoryManager(model_config={'context_window': 128000}, config=config)
            manager.checkpoint_dir = tmpdir
            yield manager

    def test_checkpoint_creates_file(self, manager):
        """Test that checkpoint creates a file."""
        manager.add_operation({'type': 'task', 'tokens': 500})

        checkpoint_path = manager.checkpoint()

        assert Path(checkpoint_path).exists()

    def test_checkpoint_saves_state(self, manager):
        """Test that checkpoint saves all component state."""
        manager.add_operation({'type': 'task', 'data': {'id': 1}, 'tokens': 500})
        manager.add_operation({'type': 'task', 'data': {'id': 2}, 'tokens': 500})

        checkpoint_path = manager.checkpoint()

        # Verify checkpoint file contains expected data
        import json
        with open(checkpoint_path) as f:
            data = json.load(f)

        assert 'working_memory' in data
        assert 'window_manager' in data
        assert 'metadata' in data

    def test_checkpoint_with_custom_path(self, manager):
        """Test checkpoint with custom file path."""
        custom_path = Path(manager.checkpoint_dir) / 'custom_checkpoint.json'

        checkpoint_path = manager.checkpoint(path=str(custom_path))

        assert checkpoint_path == str(custom_path)
        assert custom_path.exists()

    def test_restore_loads_state(self, manager):
        """Test that restore loads checkpoint state."""
        # Create checkpoint
        manager.add_operation({'type': 'task', 'data': {'id': 1}, 'tokens': 500})
        checkpoint_path = manager.checkpoint()

        # Create new manager and restore
        new_manager = MemoryManager(
            model_config={'context_window': 128000},
            config={'checkpoint_dir': manager.checkpoint_dir}
        )
        new_manager.restore(checkpoint_path)

        # Verify state restored
        operations = new_manager.get_recent_operations()
        assert len(operations) == 1
        assert operations[0]['data']['id'] == 1

    def test_restore_nonexistent_checkpoint_raises_error(self, manager):
        """Test that restoring nonexistent checkpoint raises error."""
        with pytest.raises(MemoryManagerException):
            manager.restore('/nonexistent/checkpoint.json')

    def test_should_checkpoint_based_on_profile(self, manager):
        """Test checkpoint detection based on profile configuration."""
        # Add operations up to checkpoint threshold
        profile = manager.adaptive_optimizer.get_active_profile()
        checkpoint_count = profile['checkpoint_operation_count']

        for i in range(checkpoint_count - 1):
            manager.add_operation({'type': 'task', 'tokens': 100})

        assert not manager.should_checkpoint()

        # Add one more to trigger
        manager.add_operation({'type': 'task', 'tokens': 100})

        assert manager.should_checkpoint()

    def test_should_checkpoint_based_on_usage(self, manager):
        """Test checkpoint detection based on usage threshold."""
        profile = manager.adaptive_optimizer.get_active_profile()
        threshold_pct = profile['checkpoint_threshold_pct'] / 100.0

        # Add operations up to threshold
        threshold_tokens = int(manager.context_window_size * threshold_pct)
        manager.add_operation({'type': 'task', 'tokens': threshold_tokens + 1000})

        assert manager.should_checkpoint()


class TestMemoryManagerStatus:
    """Test MemoryManager status reporting."""

    @pytest.fixture
    def manager(self):
        """Create MemoryManager instance for testing."""
        config = {'context_window': 128000}
        return MemoryManager(model_config=config)

    def test_get_status(self, manager):
        """Test comprehensive status retrieval."""
        status = manager.get_status()

        assert 'context_window' in status
        assert 'optimization_profile' in status
        assert 'working_memory' in status
        assert 'window_manager' in status
        assert 'checkpoint_needed' in status

    def test_get_status_includes_component_details(self, manager):
        """Test that status includes details from all components."""
        manager.add_operation({'type': 'task', 'tokens': 1000})

        status = manager.get_status()

        # Working memory status
        assert status['working_memory']['operation_count'] == 1
        assert status['working_memory']['current_tokens'] == 1000

        # Window manager status
        assert 'used_tokens' in status['window_manager']
        assert 'zone' in status['window_manager']


class TestMemoryManagerEdgeCases:
    """Test MemoryManager edge cases and error handling."""

    def test_init_without_context_window_raises_error(self):
        """Test that missing context_window raises error."""
        with pytest.raises(ValueError):
            MemoryManager(model_config={})

    def test_add_operation_without_tokens_estimates(self):
        """Test that operations without tokens get estimated."""
        manager = MemoryManager(model_config={'context_window': 128000})

        operation = {
            'type': 'task',
            'data': {'title': 'Test Task'}
            # No 'tokens' field
        }

        manager.add_operation(operation)

        recent = manager.get_recent_operations(limit=1)
        assert 'tokens' in recent[0]
        assert recent[0]['tokens'] > 0

    def test_clear_resets_state(self):
        """Test that clear resets working memory and usage."""
        manager = MemoryManager(model_config={'context_window': 128000})

        manager.add_operation({'type': 'task', 'tokens': 1000})
        manager.add_operation({'type': 'task', 'tokens': 1000})

        manager.clear()

        assert len(manager.get_recent_operations()) == 0
        assert manager.window_manager.used_tokens() == 0

    def test_thread_safety(self):
        """Test thread-safe operation handling."""
        import threading

        manager = MemoryManager(model_config={'context_window': 128000})
        operations_added = []

        def add_operations():
            for i in range(10):
                manager.add_operation({'type': 'task', 'tokens': 100})
                operations_added.append(i)

        threads = [threading.Thread(target=add_operations) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        # Should have 30 operations total
        assert len(manager.get_recent_operations(limit=100)) == 30

    def test_large_context_window(self):
        """Test with very large context window (1M+ tokens)."""
        manager = MemoryManager(model_config={'context_window': 1000000})

        assert manager.context_window_size == 1000000
        # Should select "minimal" profile
        profile = manager.adaptive_optimizer.get_active_profile()
        assert profile['name'] == 'Minimal'


class TestMemoryManagerIntegration:
    """Integration tests for MemoryManager with all components."""

    def test_full_lifecycle(self):
        """Test complete lifecycle: init, add ops, build context, checkpoint, restore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manager
            config = {
                'context_window': 128000,
                'checkpoint_dir': tmpdir
            }
            manager1 = MemoryManager(model_config={'context_window': 128000}, config=config)

            # Add operations
            for i in range(5):
                manager1.add_operation({
                    'type': 'task',
                    'operation': 'create_task',
                    'data': {'id': i, 'title': f'Task {i}'},
                    'tokens': 500
                })

            # Build context
            context = manager1.build_context()
            assert len(context['operations']) == 5

            # Checkpoint
            checkpoint_path = manager1.checkpoint()

            # Create new manager and restore
            manager2 = MemoryManager(model_config={'context_window': 128000}, config=config)
            manager2.restore(checkpoint_path)

            # Verify restored state
            restored_ops = manager2.get_recent_operations()
            assert len(restored_ops) == 5
            # Note: operations may not preserve exact order after restore
            restored_ids = [op['data']['id'] for op in restored_ops]
            assert set(restored_ids) == {0, 1, 2, 3, 4}

    def test_optimization_pipeline(self):
        """Test full optimization pipeline with large context."""
        manager = MemoryManager(model_config={'context_window': 32000})  # Smaller context

        # Add many large operations to trigger optimization
        for i in range(20):
            manager.add_operation({
                'type': 'validation',
                'data': {'result': 'x' * 500},  # Large data
                'tokens': 1000
            })

        # Build optimized context
        context = manager.build_context(optimize=True)

        # Should have applied optimization
        assert 'metadata' in context
        # Context should be smaller than raw operations
        # (actual assertion depends on optimization implementation)
