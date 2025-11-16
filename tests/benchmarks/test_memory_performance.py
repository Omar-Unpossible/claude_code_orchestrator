"""Performance benchmarks for context management system.

Measures actual performance characteristics including throughput, latency,
memory usage, and optimization effectiveness.

Note: These are marked as @pytest.mark.slow and should be run separately
from unit tests.

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
import tempfile
import time
import json
from pathlib import Path
from typing import Dict, List, Any

from src.orchestration.memory.memory_manager import MemoryManager


@pytest.mark.slow
class TestOperationPerformance:
    """Benchmark core operation performance."""

    def test_operation_add_throughput(self, fast_time):
        """Benchmark operation addition throughput."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Measure single operation time
            times = []
            for _ in range(100):
                start = time.perf_counter()
                manager.add_operation({
                    'type': 'benchmark',
                    'operation': 'test',
                    'data': {'payload': 'x' * 100},
                    'tokens': 500
                })
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            mean_time = sum(times) / len(times)

            # Should be fast (<10ms per operation)
            assert mean_time < 0.01  # 10ms
            print(f"\nMean operation time: {mean_time*1000:.3f}ms")

    def test_bulk_operation_performance(self, fast_time):
        """Measure performance of adding many operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            start_time = time.perf_counter()

            # Add 1000 operations
            for i in range(1000):
                manager.add_operation({
                    'type': 'bulk',
                    'operation': 'process',
                    'data': {'id': i},
                    'tokens': 300
                })

            elapsed = time.perf_counter() - start_time

            # Should complete in reasonable time
            # Target: <1s for 1000 operations (1ms per op)
            assert elapsed < 1.0

            # Record throughput
            throughput = 1000 / elapsed
            print(f"\nOperation throughput: {throughput:.0f} ops/sec")

    def test_eviction_performance(self, fast_time):
        """Measure performance when eviction occurs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Small context to force evictions
            manager = MemoryManager(
                model_config={'context_window': 8000},
                config={'checkpoint_dir': tmpdir}
            )

            start_time = time.perf_counter()

            # Add operations to trigger evictions
            for i in range(200):
                manager.add_operation({
                    'type': 'eviction_test',
                    'operation': 'add',
                    'data': {'iteration': i},
                    'tokens': 500
                })

            elapsed = time.perf_counter() - start_time

            # Eviction should not significantly slow operations
            # Target: <500ms for 200 operations with evictions
            assert elapsed < 0.5

            # Verify evictions occurred
            status = manager.working_memory.get_status()
            assert status['eviction_count'] > 0

            print(f"\nEvictions: {status['eviction_count']}, Time: {elapsed:.3f}s")

    def test_query_operation_performance(self, fast_time):
        """Benchmark operation query performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add operations
            for i in range(100):
                manager.add_operation({
                    'type': 'query_test',
                    'operation': 'store',
                    'data': {'id': i, 'tag': f'tag_{i % 10}'},
                    'tokens': 400
                })

            # Measure query time
            times = []
            for _ in range(100):
                start = time.perf_counter()
                result = manager.get_recent_operations(limit=10)
                elapsed = time.perf_counter() - start
                times.append(elapsed)

            mean_time = sum(times) / len(times)

            # Should be very fast (<1ms)
            assert mean_time < 0.001
            print(f"\nMean query time: {mean_time*1000:.3f}ms")

    def test_context_build_performance(self, fast_time):
        """Measure context building performance."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add operations
            for i in range(50):
                manager.add_operation({
                    'type': 'build_test',
                    'operation': 'data',
                    'data': {'content': 'x' * 200},
                    'tokens': 600
                })

            # Measure without optimization
            start_time = time.perf_counter()
            context_no_opt = manager.build_context(optimize=False)
            time_no_opt = time.perf_counter() - start_time

            # Measure with optimization
            start_time = time.perf_counter()
            context_opt = manager.build_context(optimize=True)
            time_opt = time.perf_counter() - start_time

            print(f"\nContext build (no opt): {time_no_opt*1000:.1f}ms")
            print(f"Context build (with opt): {time_opt*1000:.1f}ms")

            # Both should be reasonably fast
            assert time_no_opt < 0.1  # <100ms
            assert time_opt < 0.5     # <500ms (optimization adds overhead)


@pytest.mark.slow
class TestCheckpointPerformance:
    """Benchmark checkpoint and restore operations."""

    def test_checkpoint_creation_performance(self, fast_time):
        """Measure checkpoint creation time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add operations
            for i in range(100):
                manager.add_operation({
                    'type': 'checkpoint_test',
                    'operation': 'work',
                    'data': {'iteration': i},
                    'tokens': 500
                })

            # Measure checkpoint creation
            start_time = time.perf_counter()
            checkpoint_path = manager.checkpoint()
            elapsed = time.perf_counter() - start_time

            # Should be fast (<50ms)
            assert elapsed < 0.05

            print(f"\nCheckpoint creation: {elapsed*1000:.1f}ms")
            print(f"Checkpoint size: {Path(checkpoint_path).stat().st_size / 1024:.1f}KB")

    def test_checkpoint_restore_performance(self, fast_time):
        """Measure checkpoint restore time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create checkpoint
            manager1 = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            for i in range(100):
                manager1.add_operation({
                    'type': 'restore_test',
                    'operation': 'work',
                    'data': {'id': i},
                    'tokens': 500
                })

            checkpoint_path = manager1.checkpoint()

            # Measure restore
            start_time = time.perf_counter()
            manager2 = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )
            manager2.restore(checkpoint_path)
            elapsed = time.perf_counter() - start_time

            # Should be fast (<100ms)
            assert elapsed < 0.1

            print(f"\nCheckpoint restore: {elapsed*1000:.1f}ms")

    def test_checkpoint_with_large_history(self, fast_time):
        """Benchmark checkpoint with substantial history."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 200000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add many operations
            for i in range(500):
                manager.add_operation({
                    'type': 'large_history',
                    'operation': 'log',
                    'data': {'iteration': i, 'status': 'complete'},
                    'tokens': 400
                })

            # Measure checkpoint
            start_time = time.perf_counter()
            checkpoint_path = manager.checkpoint()
            elapsed = time.perf_counter() - start_time

            # Should still be reasonable (<200ms)
            assert elapsed < 0.2

            cp_size = Path(checkpoint_path).stat().st_size / 1024
            print(f"\nLarge checkpoint: {elapsed*1000:.1f}ms, {cp_size:.1f}KB")


@pytest.mark.slow
class TestProfileComparison:
    """Compare performance across optimization profiles."""

    def test_profile_operation_limits(self, fast_time):
        """Compare operation handling across profiles."""
        profiles_data = []

        test_cases = [
            (4096, 'Ultra-Aggressive'),
            (32000, 'Aggressive'),
            (128000, 'Balanced'),
            (1000000, 'Minimal'),
        ]

        for context_size, expected_profile in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': context_size},
                    config={'checkpoint_dir': tmpdir}
                )

                profile = manager.adaptive_optimizer.get_active_profile()
                wm_status = manager.working_memory.get_status()

                # Add operations until eviction
                evictions_start = 0
                operations_added = 0

                for i in range(100):
                    manager.add_operation({
                        'type': 'profile_test',
                        'operation': 'add',
                        'data': {'id': i},
                        'tokens': 500
                    })
                    operations_added += 1

                    current_evictions = manager.working_memory.get_status()['eviction_count']
                    if current_evictions > evictions_start:
                        evictions_start = current_evictions
                        break

                profiles_data.append({
                    'profile': profile['name'],
                    'context_size': context_size,
                    'max_operations': wm_status['max_operations'],
                    'max_tokens': wm_status['max_tokens'],
                    'operations_before_eviction': operations_added,
                })

        # Print comparison
        print("\n\nProfile Operation Limits:")
        print("=" * 80)
        for data in profiles_data:
            print(f"{data['profile']:20s} | Context: {data['context_size']:>7,} | "
                  f"Max Ops: {data['max_operations']:>3} | Max Tokens: {data['max_tokens']:>6,} | "
                  f"Before Evict: {data['operations_before_eviction']:>3}")

    def test_optimization_effectiveness_by_profile(self, fast_time):
        """Compare optimization effectiveness across profiles."""
        results = []

        test_cases = [
            (8000, 'Aggressive'),
            (32000, 'Aggressive'),
            (128000, 'Balanced'),
        ]

        for context_size, _ in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': context_size},
                    config={'checkpoint_dir': tmpdir}
                )

                # Add operations with large data
                for i in range(30):
                    manager.add_operation({
                        'type': 'optimization_test',
                        'operation': 'process',
                        'data': {'payload': 'x' * 300},
                        'tokens': 1000
                    })

                # Build optimized context
                context = manager.build_context(optimize=True)

                profile_name = manager.adaptive_optimizer.get_active_profile()['name']

                if 'optimization' in context['metadata']:
                    opt = context['metadata']['optimization']
                    results.append({
                        'profile': profile_name,
                        'context_size': context_size,
                        'tokens_before': opt['tokens_before'],
                        'tokens_after': opt['tokens_after'],
                        'compression_ratio': opt['compression_ratio'],
                        'techniques': len(opt['techniques_applied'])
                    })

        # Print results
        print("\n\nOptimization Effectiveness by Profile:")
        print("=" * 90)
        for r in results:
            reduction_pct = (1 - r['compression_ratio']) * 100
            print(f"{r['profile']:20s} | Context: {r['context_size']:>7,} | "
                  f"Before: {r['tokens_before']:>6,} | After: {r['tokens_after']:>6,} | "
                  f"Reduction: {reduction_pct:>5.1f}% | Techniques: {r['techniques']}")

    def test_checkpoint_frequency_by_profile(self, fast_time):
        """Compare checkpoint frequency across profiles."""
        checkpoint_data = []

        test_cases = [
            (4096, 'Ultra-Aggressive'),
            (32000, 'Aggressive'),
            (128000, 'Balanced'),
        ]

        for context_size, _ in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': context_size},
                    config={'checkpoint_dir': tmpdir}
                )

                profile = manager.adaptive_optimizer.get_active_profile()

                # Add operations until checkpoint recommended
                for i in range(200):
                    manager.add_operation({
                        'type': 'frequency_test',
                        'operation': 'work',
                        'data': {'id': i},
                        'tokens': 500
                    })

                    if manager.should_checkpoint():
                        checkpoint_data.append({
                            'profile': profile['name'],
                            'context_size': context_size,
                            'operations_before_checkpoint': i + 1,
                            'checkpoint_op_count': profile['checkpoint_operation_count'],
                            'checkpoint_threshold_pct': profile['checkpoint_threshold_pct'],
                        })
                        break

        # Print results
        print("\n\nCheckpoint Frequency by Profile:")
        print("=" * 90)
        for data in checkpoint_data:
            print(f"{data['profile']:20s} | Context: {data['context_size']:>7,} | "
                  f"Ops before CP: {data['operations_before_checkpoint']:>3} | "
                  f"Config Op Count: {data['checkpoint_op_count']:>3} | "
                  f"Threshold: {data['checkpoint_threshold_pct']:>3}%")


@pytest.mark.slow
class TestMemoryUsage:
    """Measure memory consumption of the system."""

    def test_working_memory_footprint(self, fast_time):
        """Measure memory footprint of working memory."""
        import sys

        memory_data = []

        for context_size in [8000, 32000, 128000, 1000000]:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': context_size},
                    config={'checkpoint_dir': tmpdir}
                )

                # Add operations to fill working memory
                wm_max = manager.working_memory.max_operations
                for i in range(wm_max):
                    manager.add_operation({
                        'type': 'memory_test',
                        'operation': 'fill',
                        'data': {'id': i, 'payload': 'x' * 100},
                        'tokens': 500
                    })

                # Estimate memory usage
                wm_status = manager.working_memory.get_status()
                operations = manager.get_recent_operations()

                # Rough estimate of memory usage
                estimated_bytes = sys.getsizeof(operations) + sum(
                    sys.getsizeof(str(op)) for op in operations
                )

                memory_data.append({
                    'context_size': context_size,
                    'operation_count': wm_status['operation_count'],
                    'current_tokens': wm_status['current_tokens'],
                    'estimated_kb': estimated_bytes / 1024,
                })

        # Print results
        print("\n\nWorking Memory Footprint:")
        print("=" * 70)
        for data in memory_data:
            print(f"Context: {data['context_size']:>7,} | Ops: {data['operation_count']:>3} | "
                  f"Tokens: {data['current_tokens']:>6,} | Memory: ~{data['estimated_kb']:.1f}KB")

    def test_checkpoint_file_sizes(self, fast_time):
        """Measure checkpoint file sizes."""
        checkpoint_sizes = []

        for op_count in [50, 100, 200, 500]:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': 200000},
                    config={'checkpoint_dir': tmpdir}
                )

                # Add operations
                for i in range(op_count):
                    manager.add_operation({
                        'type': 'size_test',
                        'operation': 'data',
                        'data': {'id': i, 'content': 'x' * 100},
                        'tokens': 500
                    })

                # Create checkpoint
                checkpoint_path = manager.checkpoint()
                size_kb = Path(checkpoint_path).stat().st_size / 1024

                checkpoint_sizes.append({
                    'operation_count': op_count,
                    'checkpoint_size_kb': size_kb,
                    'kb_per_operation': size_kb / op_count,
                })

        # Print results
        print("\n\nCheckpoint File Sizes:")
        print("=" * 60)
        for data in checkpoint_sizes:
            print(f"Operations: {data['operation_count']:>3} | "
                  f"Size: {data['checkpoint_size_kb']:>6.1f}KB | "
                  f"Per Op: {data['kb_per_operation']:>5.2f}KB/op")


@pytest.mark.slow
class TestScalability:
    """Test system scalability characteristics."""

    def test_linear_scaling_operations(self, fast_time):
        """Verify operations scale linearly."""
        timing_data = []

        for op_count in [100, 200, 500, 1000]:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': 200000},
                    config={'checkpoint_dir': tmpdir}
                )

                start_time = time.perf_counter()

                for i in range(op_count):
                    manager.add_operation({
                        'type': 'scaling_test',
                        'operation': 'add',
                        'data': {'id': i},
                        'tokens': 400
                    })

                elapsed = time.perf_counter() - start_time

                timing_data.append({
                    'operation_count': op_count,
                    'total_time_ms': elapsed * 1000,
                    'time_per_op_ms': (elapsed / op_count) * 1000,
                })

        # Print results
        print("\n\nOperation Scaling:")
        print("=" * 60)
        for data in timing_data:
            print(f"Ops: {data['operation_count']:>4} | "
                  f"Total: {data['total_time_ms']:>7.1f}ms | "
                  f"Per Op: {data['time_per_op_ms']:>6.3f}ms")

        # Verify roughly linear scaling
        # Time per operation should remain relatively constant
        times_per_op = [d['time_per_op_ms'] for d in timing_data]
        variance = max(times_per_op) / min(times_per_op)
        assert variance < 3.0  # Should not vary more than 3x
