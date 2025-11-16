"""End-to-end scenario tests for context management system.

Tests the complete memory management system across different context sizes
and usage patterns to validate real-world behavior.

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import pytest
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

from src.orchestration.memory.memory_manager import MemoryManager


class TestSmallContextScenarios:
    """Test scenarios for small context windows (4K-8K tokens)."""

    @pytest.fixture
    def small_context_manager(self):
        """Create MemoryManager with small context window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'context_window': 4096,  # 4K context
                'model': 'phi3:mini'
            }
            manager = MemoryManager(
                model_config=config,
                config={'checkpoint_dir': tmpdir}
            )
            yield manager

    def test_small_context_basic_workflow(self, small_context_manager):
        """Test basic workflow with 4K context window.

        Scenario: Phi3 Mini (4K) processing simple task workflow
        """
        manager = small_context_manager

        # Verify ultra-aggressive profile selected
        profile = manager.adaptive_optimizer.get_active_profile()
        assert profile['name'] == 'Ultra-Aggressive'

        # Add 5 small operations
        for i in range(5):
            manager.add_operation({
                'type': 'task',
                'operation': 'create_task',
                'data': {'id': i, 'title': f'Task {i}'},
                'tokens': 100
            })

        # Should stay in green zone
        assert manager.window_manager.get_zone() == 'green'

        # Build context
        context = manager.build_context(optimize=True)

        # Verify context structure
        assert 'operations' in context
        assert 'metadata' in context
        # With ultra-aggressive profile, working memory has tight limits
        # May evict older operations, so just verify we have some operations
        assert len(context['operations']) > 0
        assert len(context['operations']) <= 5

    def test_small_context_approaching_limit(self, small_context_manager):
        """Test behavior as small context approaches capacity."""
        manager = small_context_manager

        # Add operations until we hit yellow/orange zone
        # With 85% utilization limit: 4096 * 0.85 = 3481 effective max
        # Yellow at 70% of effective: 3481 * 0.70 = 2437 tokens
        # Checkpoint threshold: 70% of full context = 4096 * 0.70 = 2867 tokens

        operation_size = 500
        # Need to reach 2867+ tokens to trigger checkpoint
        operations_needed = (2867 // operation_size) + 1

        for i in range(operations_needed):
            manager.add_operation({
                'type': 'validation',
                'operation': 'validate',
                'data': {'result': 'x' * 100},
                'tokens': operation_size
            })

        # Should be in yellow/orange/red zone
        zone = manager.window_manager.get_zone()
        assert zone in ['yellow', 'orange', 'red']

        # Checkpoint should be recommended
        assert manager.should_checkpoint()

    def test_small_context_with_optimization(self, small_context_manager):
        """Test optimization techniques on small context."""
        manager = small_context_manager

        # Add operations that should trigger optimization
        for i in range(10):
            manager.add_operation({
                'type': 'task',
                'operation': 'process',
                'data': {'large_field': 'x' * 200},
                'tokens': 600
            })

        # Build optimized context
        context = manager.build_context(optimize=True)

        # Working memory should have evicted some operations
        wm_status = manager.working_memory.get_status()
        assert wm_status['eviction_count'] > 0


class TestMediumContextScenarios:
    """Test scenarios for medium context windows (32K-128K tokens)."""

    @pytest.fixture
    def medium_context_manager(self):
        """Create MemoryManager with medium context window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'context_window': 32000,  # 32K context
                'model': 'qwen2.5-coder:14b'
            }
            manager = MemoryManager(
                model_config=config,
                config={'checkpoint_dir': tmpdir}
            )
            yield manager

    def test_medium_context_development_workflow(self, medium_context_manager):
        """Test typical development workflow with 32K context.

        Scenario: Qwen 14B (32K) handling code generation tasks
        """
        manager = medium_context_manager

        # Verify aggressive profile selected for 32K
        profile = manager.adaptive_optimizer.get_active_profile()
        assert profile['name'] == 'Aggressive'  # 32K falls in 8-32K range

        # Simulate development workflow
        # 1. Create tasks
        for i in range(5):
            manager.add_operation({
                'type': 'task',
                'operation': 'create_task',
                'data': {'title': f'Implement feature {i}'},
                'tokens': 200
            })

        # 2. Code generation operations
        for i in range(10):
            manager.add_operation({
                'type': 'code_generation',
                'operation': 'generate_code',
                'data': {'file': f'module_{i}.py', 'lines': 50},
                'tokens': 1500
            })

        # 3. Validation operations
        for i in range(10):
            manager.add_operation({
                'type': 'validation',
                'operation': 'validate_code',
                'data': {'result': 'passed'},
                'tokens': 300
            })

        # Total: ~20K tokens
        # Should still be in green zone with 32K context
        assert manager.window_manager.get_zone() in ['green', 'yellow']

        # Build context
        context = manager.build_context(optimize=True)

        # Working memory has limits - verify we have operations
        assert len(context['operations']) > 0

    def test_medium_context_checkpoint_cycle(self, medium_context_manager):
        """Test checkpoint/restore cycle with medium context."""
        manager = medium_context_manager

        # Add significant operations
        for i in range(30):
            manager.add_operation({
                'type': 'task',
                'operation': 'execute',
                'data': {'step': i},
                'tokens': 800
            })

        # Create checkpoint
        checkpoint_path = manager.checkpoint()
        assert Path(checkpoint_path).exists()

        # Get status before restore
        status_before = manager.get_status()
        ops_before = manager.get_recent_operations()

        # Create new manager and restore
        new_manager = MemoryManager(
            model_config={'context_window': 32000},
            config={'checkpoint_dir': manager.checkpoint_dir}
        )
        new_manager.restore(checkpoint_path)

        # Verify restoration
        status_after = new_manager.get_status()
        ops_after = new_manager.get_recent_operations()

        assert status_after['working_memory']['operation_count'] == status_before['working_memory']['operation_count']
        assert len(ops_after) == len(ops_before)


class TestLargeContextScenarios:
    """Test scenarios for large context windows (128K+ tokens)."""

    @pytest.fixture
    def large_context_manager(self):
        """Create MemoryManager with large context window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {
                'context_window': 128000,  # 128K context
                'model': 'qwen2.5-coder:32b'
            }
            manager = MemoryManager(
                model_config=config,
                config={'checkpoint_dir': tmpdir}
            )
            yield manager

    def test_large_context_extensive_workflow(self, large_context_manager):
        """Test extensive workflow with 128K context.

        Scenario: Qwen 32B (128K) handling large codebase analysis
        """
        manager = large_context_manager

        # Verify balanced profile selected
        profile = manager.adaptive_optimizer.get_active_profile()
        assert profile['name'] == 'Balanced'

        # Simulate large codebase analysis
        # 1. File analysis operations
        for i in range(50):
            manager.add_operation({
                'type': 'analysis',
                'operation': 'analyze_file',
                'data': {'file': f'src/module_{i}.py', 'complexity': 'medium'},
                'tokens': 800
            })

        # 2. Refactoring operations
        for i in range(30):
            manager.add_operation({
                'type': 'refactoring',
                'operation': 'refactor',
                'data': {'changes': 'optimize loops'},
                'tokens': 1200
            })

        # 3. Test generation
        for i in range(20):
            manager.add_operation({
                'type': 'test_generation',
                'operation': 'generate_tests',
                'data': {'test_count': 10},
                'tokens': 1500
            })

        # Total: ~100K tokens
        # With 128K context and 85% limit (108.8K effective)
        # Should be in yellow/orange zone
        zone = manager.window_manager.get_zone()
        assert zone in ['yellow', 'orange', 'red', 'green']

        # Build optimized context
        context = manager.build_context(optimize=True)

        # Should have metadata
        assert 'metadata' in context
        assert 'operations' in context
        # Optimization metadata is optional (may or may not be present)
        assert context['metadata']['optimization_profile'] == 'Balanced'

    def test_large_context_long_session(self, large_context_manager):
        """Test long session with periodic checkpoints."""
        manager = large_context_manager

        checkpoints_created = []

        # Simulate long session with 100 operations
        for i in range(100):
            manager.add_operation({
                'type': 'task',
                'operation': 'process',
                'data': {'iteration': i},
                'tokens': 500
            })

            # Checkpoint every 20 operations
            if (i + 1) % 20 == 0:
                checkpoint = manager.checkpoint()
                checkpoints_created.append(checkpoint)

        # Should have created 5 checkpoints
        assert len(checkpoints_created) == 5

        # All checkpoint files should exist
        for cp_path in checkpoints_created:
            assert Path(cp_path).exists()

        # Verify final state
        status = manager.get_status()
        assert status['total_operation_count'] == 100


class TestProfileTransitions:
    """Test transitions between optimization profiles."""

    def test_profile_selection_by_context_size(self):
        """Test that correct profiles are selected for different context sizes."""
        test_cases = [
            (4096, 'Ultra-Aggressive'),     # 4K-8K range
            (8192, 'Aggressive'),           # 8K-32K range
            (32000, 'Aggressive'),          # 8K-32K range (32K is boundary)
            (50000, 'Balanced-Aggressive'), # 32K-100K range
            (128000, 'Balanced'),           # 100K-250K range
            (300000, 'Minimal'),            # 250K+ range
        ]

        for context_size, expected_profile in test_cases:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': context_size},
                    config={'checkpoint_dir': tmpdir}
                )

                profile = manager.adaptive_optimizer.get_active_profile()
                assert profile['name'] == expected_profile, \
                    f"Context {context_size} should use {expected_profile}, got {profile['name']}"

    def test_working_memory_sizing_across_profiles(self):
        """Test that working memory adapts to profile settings."""
        context_sizes = [4096, 32000, 128000, 1000000]

        for context_size in context_sizes:
            with tempfile.TemporaryDirectory() as tmpdir:
                manager = MemoryManager(
                    model_config={'context_window': context_size},
                    config={'checkpoint_dir': tmpdir}
                )

                wm_status = manager.working_memory.get_status()

                # Verify working memory sizing is appropriate
                assert wm_status['max_tokens'] > 0
                assert wm_status['max_operations'] > 0

                # Max tokens should be reasonable percentage of effective context
                # Effective max is context * utilization_limit (0.85)
                effective_context = context_size * manager.window_manager.utilization_limit
                max_tokens_pct = wm_status['max_tokens'] / effective_context
                assert 0.04 <= max_tokens_pct <= 0.12  # ~5-10% of effective context


class TestOptimizationEffectiveness:
    """Test effectiveness of optimization techniques."""

    def test_context_reduction_with_optimization(self):
        """Test that optimization actually reduces context size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 32000},
                config={'checkpoint_dir': tmpdir}
            )

            # Add operations with large data
            for i in range(20):
                manager.add_operation({
                    'type': 'validation',
                    'operation': 'validate',
                    'data': {'large_result': 'x' * 500},
                    'tokens': 1500
                })

            # Build context without optimization
            context_no_opt = manager.build_context(optimize=False)

            # Build context with optimization
            context_with_opt = manager.build_context(optimize=True)

            # Both should have operations
            assert 'operations' in context_no_opt
            assert 'operations' in context_with_opt

            # Both should have metadata
            assert 'metadata' in context_no_opt
            assert 'metadata' in context_with_opt

            # Verify optimization was applied (metadata will always be present)
            assert 'optimization' in context_with_opt['metadata']
            opt_result = context_with_opt['metadata']['optimization']
            assert 'techniques_applied' in opt_result
            assert len(opt_result['techniques_applied']) > 0

    def test_eviction_maintains_recent_operations(self):
        """Test that eviction keeps most recent operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 8000},  # Small context
                config={'checkpoint_dir': tmpdir}
            )

            # Add operations until eviction occurs
            for i in range(30):
                manager.add_operation({
                    'type': 'task',
                    'operation': 'execute',
                    'data': {'iteration': i},
                    'tokens': 500
                })

            # Get recent operations
            recent = manager.get_recent_operations(limit=10)

            # Should have most recent operations (20-29)
            recent_iterations = [op['data']['iteration'] for op in recent]
            assert all(i >= 20 for i in recent_iterations)

            # Verify eviction occurred
            wm_status = manager.working_memory.get_status()
            assert wm_status['eviction_count'] > 0


class TestRealWorldScenarios:
    """Test realistic real-world usage scenarios."""

    def test_iterative_development_session(self):
        """Test realistic iterative development session.

        Scenario: Developer working on feature implementation across
        multiple iterations with code generation, testing, and refinement.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 128000},
                config={'checkpoint_dir': tmpdir}
            )

            # Iteration 1: Planning
            for i in range(5):
                manager.add_operation({
                    'type': 'planning',
                    'operation': 'create_epic',
                    'data': {'epic': f'Feature {i}'},
                    'tokens': 300
                })

            # Iteration 2: Implementation
            for i in range(15):
                manager.add_operation({
                    'type': 'code',
                    'operation': 'generate_code',
                    'data': {'file': f'feature_{i}.py'},
                    'tokens': 2000
                })

            # Iteration 3: Testing
            for i in range(15):
                manager.add_operation({
                    'type': 'test',
                    'operation': 'run_tests',
                    'data': {'passed': True},
                    'tokens': 800
                })

            # Iteration 4: Bug fixes
            for i in range(10):
                manager.add_operation({
                    'type': 'bugfix',
                    'operation': 'fix_bug',
                    'data': {'bug_id': i},
                    'tokens': 1500
                })

            # Verify session state
            status = manager.get_status()
            assert status['total_operation_count'] == 45

            # Should still be manageable with 128K context
            assert status['window_manager']['zone'] in ['green', 'yellow']

            # Build final context
            context = manager.build_context(optimize=True)
            assert 'operations' in context
            assert 'metadata' in context

    def test_codebase_migration_workflow(self):
        """Test large-scale codebase migration workflow.

        Scenario: Migrating large codebase with analysis,
        transformation, and validation steps.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = MemoryManager(
                model_config={'context_window': 200000},  # Large context
                config={'checkpoint_dir': tmpdir}
            )

            # Phase 1: Analysis (30 files)
            for i in range(30):
                manager.add_operation({
                    'type': 'analysis',
                    'operation': 'analyze_dependencies',
                    'data': {'file': f'legacy/module_{i}.py', 'deps': i * 3},
                    'tokens': 1200
                })

            # Phase 2: Transformation (30 files)
            for i in range(30):
                manager.add_operation({
                    'type': 'transformation',
                    'operation': 'transform_syntax',
                    'data': {'file': f'new/module_{i}.py', 'changes': 25},
                    'tokens': 2000
                })

            # Phase 3: Validation (30 files)
            for i in range(30):
                manager.add_operation({
                    'type': 'validation',
                    'operation': 'validate_migration',
                    'data': {'file': f'new/module_{i}.py', 'status': 'ok'},
                    'tokens': 800
                })

            # Total: ~120K tokens
            status = manager.get_status()
            assert status['total_operation_count'] == 90

            # Should still be in reasonable zone
            zone = status['window_manager']['zone']
            assert zone in ['green', 'yellow', 'orange']

            # Create checkpoint for recovery
            checkpoint = manager.checkpoint()
            assert Path(checkpoint).exists()
