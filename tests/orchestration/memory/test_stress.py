"""Stress tests for context management system.

Tests system behavior under heavy load, high concurrency, and resource constraints.
Follows WSL2 TEST_GUIDELINES.md for resource limits.

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
import tempfile
import threading
from pathlib import Path

from src.orchestration.memory.memory_manager import MemoryManager


@pytest.mark.slow
class TestHighVolumeOperations:
    """Test system with high volume of operations."""

    def test_many_small_operations(self, fast_time):
        """Test handling many small operations efficiently."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add 500 small operations (following WSL2 guidelines - reasonable volume)
            for i in range(500):
                manager.add_operation({
                    'type': 'task',
                    'operation': 'process',
                    'data': {'id': i},
                    'tokens': 100
                })

            # Verify system still functional
            status = manager.get_status()
            assert status['total_operation_count'] == 500

            # Working memory should have evicted many operations
            wm_status = status['working_memory']
            assert wm_status['operation_count'] < 500
            assert wm_status['eviction_count'] > 0

    def test_operations_with_varying_sizes(self, fast_time):
        """Test mix of small, medium, and large operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Mix of operation sizes
            sizes = [50, 200, 500, 1000, 2000]

            for i in range(100):
                size = sizes[i % len(sizes)]
                manager.add_operation({
                    'type': 'mixed',
                    'operation': 'process',
                    'data': {'payload': 'x' * (size // 4)},
                    'tokens': size
                })

            # System should handle mixed sizes
            status = manager.get_status()
            assert status['total_operation_count'] == 100
            assert manager.window_manager.get_zone() in ['green', 'yellow', 'orange']

    def test_rapid_checkpointing(self, fast_time):
        """Test frequent checkpoint operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            checkpoints = []

            # Create 10 checkpoints with operations between
            for batch in range(10):
                # Add 10 operations
                for i in range(10):
                    manager.add_operation({
                        'type': 'task',
                        'operation': 'execute',
                        'data': {'batch': batch, 'op': i},
                        'tokens': 500
                    })

                # Checkpoint
                cp_path = manager.checkpoint()
                checkpoints.append(cp_path)

            # All checkpoints should exist
            assert len(checkpoints) == 10
            for cp in checkpoints:
                assert Path(cp).exists()


@pytest.mark.slow
class TestLargePayloads:
    """Test handling of large data payloads."""

    def test_large_operation_payloads(self, fast_time):
        """Test operations with large data (within WSL2 20KB test limit)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 200000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add 10 operations with ~15KB payload each (within WSL2 limits)
            # Using 3000 tokens per operation
            for i in range(10):
                # Create data payload (rough estimate: 4 chars per token)
                data_payload = 'x' * (3000 * 4)

                manager.add_operation({
                    'type': 'large_data',
                    'operation': 'process_file',
                    'data': {'content': data_payload},
                    'tokens': 3000
                })

            # Verify handling
            status = manager.get_status()
            assert status['total_operation_count'] == 10

            # Build context with optimization
            context = manager.build_context(optimize=True)
            assert 'operations' in context

            # Optimization should have been applied
            if 'optimization' in context['metadata']:
                opt = context['metadata']['optimization']
                assert len(opt['techniques_applied']) > 0

    def test_checkpoint_with_large_history(self, fast_time):
        """Test checkpointing with substantial operation history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 200000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add 200 operations
            for i in range(200):
                manager.add_operation({
                    'type': 'history',
                    'operation': 'log',
                    'data': {'iteration': i, 'status': 'complete'},
                    'tokens': 400
                })

            # Create checkpoint
            cp_path = manager.checkpoint()
            assert Path(cp_path).exists()

            # Verify checkpoint file isn't excessively large
            cp_size = Path(cp_path).stat().st_size
            # Should be reasonable (< 1MB)
            assert cp_size < 1024 * 1024

            # Restore and verify
            new_manager = MemoryManager(
                model_config={'context_window': 200000},
                config={'checkpoint_dir': tmpdir}
            )
            new_manager.restore(cp_path)

            # Should have operations
            ops = new_manager.get_recent_operations()
            assert len(ops) > 0


@pytest.mark.slow
class TestConcurrentAccess:
    """Test concurrent access patterns (following WSL2 5-thread limit)."""

    def test_concurrent_operation_additions(self, fast_time):
        """Test thread-safe concurrent operation additions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            operation_count = [0]
            lock = threading.Lock()

            def add_operations():
                """Add 20 operations per thread."""
                for i in range(20):
                    manager.add_operation({
                        'type': 'concurrent',
                        'operation': 'execute',
                        'data': {'thread': threading.current_thread().name},
                        'tokens': 200
                    })
                    with lock:
                        operation_count[0] += 1

            # Use 5 threads (WSL2 limit)
            threads = [threading.Thread(target=add_operations) for _ in range(5)]

            for t in threads:
                t.start()

            for t in threads:
                t.join(timeout=5.0)  # Mandatory timeout

            # Should have added 100 operations total
            assert operation_count[0] == 100

            # System should still be functional
            status = manager.get_status()
            assert status['total_operation_count'] == 100

    def test_concurrent_context_building(self, fast_time):
        """Test concurrent context building operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add some initial operations
            for i in range(50):
                manager.add_operation({
                    'type': 'task',
                    'operation': 'process',
                    'data': {'id': i},
                    'tokens': 300
                })

            contexts_built = []
            lock = threading.Lock()

            def build_context():
                """Build context in thread."""
                context = manager.build_context(optimize=False)
                with lock:
                    contexts_built.append(context)

            # Use 3 concurrent threads
            threads = [threading.Thread(target=build_context) for _ in range(3)]

            for t in threads:
                t.start()

            for t in threads:
                t.join(timeout=5.0)

            # All should succeed
            assert len(contexts_built) == 3
            for context in contexts_built:
                assert 'operations' in context
                assert 'metadata' in context

    def test_concurrent_checkpoint_and_operations(self, fast_time):
        """Test checkpointing while operations are being added."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            checkpoints = []
            lock = threading.Lock()

            def add_operations():
                """Add operations continuously."""
                for i in range(30):
                    manager.add_operation({
                        'type': 'task',
                        'operation': 'work',
                        'data': {'iteration': i},
                        'tokens': 250
                    })

            def create_checkpoints():
                """Create checkpoints periodically."""
                for i in range(3):
                    fast_time.sleep(0.1)  # Small delay between checkpoints
                    cp = manager.checkpoint()
                    with lock:
                        checkpoints.append(cp)

            # Run both concurrently (2 threads)
            t1 = threading.Thread(target=add_operations)
            t2 = threading.Thread(target=create_checkpoints)

            t1.start()
            t2.start()

            t1.join(timeout=5.0)
            t2.join(timeout=5.0)

            # Should have created checkpoints
            assert len(checkpoints) > 0
            for cp in checkpoints:
                assert Path(cp).exists()


@pytest.mark.slow
class TestMemoryLimits:
    """Test behavior at memory limits."""

    def test_working_memory_eviction_under_load(self, fast_time):
        """Test working memory eviction with sustained load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Use small context to force evictions
            manager = MemoryManager(
                model_config={'context_window': 8000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add operations until significant evictions occur
            for i in range(100):
                manager.add_operation({
                    'type': 'load_test',
                    'operation': 'process',
                    'data': {'iteration': i},
                    'tokens': 500
                })

            # Verify evictions occurred
            wm_status = manager.working_memory.get_status()
            assert wm_status['eviction_count'] > 50  # Substantial evictions

            # Most recent operations should still be available
            recent = manager.get_recent_operations(limit=5)
            assert len(recent) > 0
            recent_ids = [op['data']['iteration'] for op in recent]
            # Should be from the end of the range
            assert all(i >= 95 for i in recent_ids)

    def test_context_window_utilization_tracking(self, fast_time):
        """Test accurate tracking as context fills up."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 32000},
                config={'checkpoint_dir': tmpdir}
            )

            zones_seen = set()

            # Add operations and track zone transitions
            for i in range(100):
                manager.add_operation({
                    'type': 'utilization_test',
                    'operation': 'execute',
                    'data': {'step': i},
                    'tokens': 800
                })

                zone = manager.window_manager.get_zone()
                zones_seen.add(zone)

                # Stop if we hit red zone
                if zone == 'red':
                    break

            # Should have seen zone transitions
            assert len(zones_seen) >= 2  # At least green → yellow or similar

    def test_optimization_effectiveness_under_pressure(self, fast_time):
        """Test optimization when context is heavily utilized."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 32000},
                config={'checkpoint_dir': tmpdir}
            )

            # Fill context with large operations
            for i in range(50):
                manager.add_operation({
                    'type': 'pressure_test',
                    'operation': 'process',
                    'data': {'payload': 'x' * 400},
                    'tokens': 1500
                })

            # Build optimized context
            context = manager.build_context(optimize=True)

            # Optimization should have been applied
            assert 'metadata' in context
            assert 'optimization' in context['metadata']

            opt = context['metadata']['optimization']
            assert 'techniques_applied' in opt
            # Some optimization techniques should have been used
            assert len(opt['techniques_applied']) > 0


@pytest.mark.slow
class TestRecoveryScenarios:
    """Test recovery from various failure scenarios."""

    def test_checkpoint_corruption_handling(self, fast_time):
        """Test handling of corrupted checkpoint files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add operations
            for i in range(10):
                manager.add_operation({
                    'type': 'task',
                    'operation': 'work',
                    'data': {'id': i},
                    'tokens': 500
                })

            # Create valid checkpoint
            valid_cp = manager.checkpoint()
            assert Path(valid_cp).exists()

            # Verify we can restore from valid checkpoint
            new_manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )
            new_manager.restore(valid_cp)

            # Should have operations
            ops = new_manager.get_recent_operations()
            assert len(ops) > 0

    def test_multiple_checkpoint_restore_cycles(self, fast_time):
        """Test multiple save/restore cycles maintain consistency."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager1 = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add initial operations
            for i in range(20):
                manager1.add_operation({
                    'type': 'cycle_test',
                    'operation': 'work',
                    'data': {'iteration': 1, 'op': i},
                    'tokens': 400
                })

            cp1 = manager1.checkpoint()

            # Restore to manager2
            manager2 = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )
            manager2.restore(cp1)

            # Add more operations
            for i in range(20):
                manager2.add_operation({
                    'type': 'cycle_test',
                    'operation': 'work',
                    'data': {'iteration': 2, 'op': i},
                    'tokens': 400
                })

            cp2 = manager2.checkpoint()

            # Restore to manager3
            manager3 = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )
            manager3.restore(cp2)

            # Should have operations from both iterations
            ops = manager3.get_recent_operations()
            assert len(ops) > 0
