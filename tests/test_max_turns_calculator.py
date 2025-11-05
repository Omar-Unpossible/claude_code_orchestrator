"""Tests for MaxTurnsCalculator.

Tests adaptive max_turns calculation based on task complexity,
task type overrides, and configuration.
"""

import pytest
from src.orchestration.max_turns_calculator import MaxTurnsCalculator


class TestMaxTurnsCalculator:
    """Test suite for MaxTurnsCalculator."""

    def test_init_default_config(self):
        """Test initialization with default configuration."""
        calculator = MaxTurnsCalculator()

        assert calculator.min_turns == 3
        assert calculator.max_turns == 30
        assert calculator.default_turns == 10
        assert calculator.task_type_defaults == MaxTurnsCalculator.TASK_TYPE_DEFAULTS

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        config = {
            'min': 5,
            'max': 25,
            'default': 12,
            'max_turns_by_type': {'debugging': 25}
        }
        calculator = MaxTurnsCalculator(config=config)

        assert calculator.min_turns == 5
        assert calculator.max_turns == 25
        assert calculator.default_turns == 12
        assert calculator.task_type_defaults['debugging'] == 25

    def test_task_type_override_validation(self):
        """Test task type override for validation."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 1,
            'task_type': 'validation',
            'description': 'Validate user input'
        }

        result = calculator.calculate(task)
        assert result == 5  # validation default

    def test_task_type_override_debugging(self):
        """Test task type override for debugging."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 2,
            'task_type': 'debugging',
            'description': 'Debug authentication issues'
        }

        result = calculator.calculate(task)
        assert result == 20  # debugging default

    def test_task_type_override_documentation(self):
        """Test task type override for documentation."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 3,
            'task_type': 'documentation',
            'description': 'Write API documentation'
        }

        result = calculator.calculate(task)
        assert result == 3  # documentation default

    def test_simple_task_single_file(self):
        """Test simple task detection (single file, no complexity)."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 4,
            'title': 'Fix typo',
            'description': 'Fix typo in config file',
            'estimated_files': 1,
            'estimated_loc': 5
        }

        result = calculator.calculate(task)
        assert result == 3  # simple task

    def test_medium_task_small_feature(self):
        """Test medium task detection (small feature, few files)."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 5,
            'title': 'Add validation',
            'description': 'Add email validation to user form',
            'estimated_files': 2,
            'estimated_loc': 50
        }

        result = calculator.calculate(task)
        assert result == 6  # medium task

    def test_complex_task_multiple_files(self):
        """Test complex task detection (feature, multiple files)."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 6,
            'title': 'Implement authentication',
            'description': 'Implement JWT authentication system',
            'estimated_files': 5,
            'estimated_loc': 300
        }

        result = calculator.calculate(task)
        assert result == 12  # complex task (has 'implement' keyword)

    def test_very_complex_task_large_refactor(self):
        """Test very complex task detection (large refactor, >500 LOC)."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 7,
            'title': 'Refactor entire module',
            'description': 'Refactor the entire authentication module',
            'estimated_files': 10,
            'estimated_loc': 600
        }

        result = calculator.calculate(task)
        assert result == 20  # very complex (>500 LOC)

    def test_very_complex_task_wide_scope(self):
        """Test very complex task detection (project-wide scope)."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 8,
            'title': 'Update dependencies',
            'description': 'Update dependencies across entire codebase',
            'estimated_files': 20,
            'estimated_loc': 100
        }

        result = calculator.calculate(task)
        assert result == 20  # very complex (scope >= 2: 'across', 'entire codebase')

    def test_complexity_word_detection(self):
        """Test detection of complexity words."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 9,
            'title': 'Migrate database',
            'description': 'Migrate database schema',
            'estimated_files': 3,
            'estimated_loc': 200
        }

        result = calculator.calculate(task)
        # complexity=1 (migrate), 3 files -> medium
        assert result == 6  # medium (complexity=1, 3 files)

    def test_scope_indicator_detection(self):
        """Test detection of scope indicators."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 10,
            'title': 'Update all files',
            'description': 'Update imports throughout repository',
            'estimated_files': 15,
            'estimated_loc': 300
        }

        result = calculator.calculate(task)
        assert result == 20  # very complex (scope indicators: 'all files', 'throughout', 'repository')

    def test_default_for_unknown_complexity(self):
        """Test default value for unknown complexity."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 11,
            'title': 'Task with moderate complexity',
            'description': 'Some task description',
            'estimated_files': 4,
            'estimated_loc': 150
        }

        result = calculator.calculate(task)
        assert result == 12  # complex (4 files)

    def test_bound_enforcement_below_min(self):
        """Test that bounds are enforced (below minimum)."""
        calculator = MaxTurnsCalculator()
        # Manually test _bound method
        result = calculator._bound(1)
        assert result == 3  # min_turns

    def test_bound_enforcement_above_max(self):
        """Test that bounds are enforced (above maximum)."""
        calculator = MaxTurnsCalculator()
        # Manually test _bound method
        result = calculator._bound(50)
        assert result == 30  # max_turns

    def test_bound_enforcement_within_range(self):
        """Test that bounds don't affect values within range."""
        calculator = MaxTurnsCalculator()
        result = calculator._bound(10)
        assert result == 10  # unchanged

    def test_custom_bounds_config(self):
        """Test custom bounds from configuration."""
        config = {'min': 5, 'max': 25}
        calculator = MaxTurnsCalculator(config=config)

        # Test below custom min
        result = calculator._bound(3)
        assert result == 5

        # Test above custom max
        result = calculator._bound(30)
        assert result == 25

    def test_task_type_override_precedence(self):
        """Test that task type override takes precedence over analysis."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 12,
            'task_type': 'documentation',  # Should override to 3
            'title': 'Complete refactor',
            'description': 'Refactor entire system across all files',  # Would be 20
            'estimated_files': 20,
            'estimated_loc': 1000
        }

        result = calculator.calculate(task)
        assert result == 3  # task_type override takes precedence

    def test_missing_metadata_defaults(self):
        """Test handling of missing metadata fields."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 13,
            'description': 'Some task'
            # No title, estimated_files, estimated_loc
        }

        result = calculator.calculate(task)
        # Should use defaults: estimated_files=1, estimated_loc=0
        assert result == 3  # simple task (no complexity, 1 file default)

    def test_empty_description(self):
        """Test handling of empty description."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 14,
            'title': '',
            'description': '',
            'estimated_files': 1
        }

        result = calculator.calculate(task)
        assert result == 3  # simple task (no text to analyze)

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case-insensitive."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 15,
            'title': 'REFACTOR MODULE',
            'description': 'MIGRATE DATABASE ACROSS ENTIRE CODEBASE',
            'estimated_files': 10,
            'estimated_loc': 400
        }

        result = calculator.calculate(task)
        # Should detect keywords despite uppercase
        assert result == 20  # very complex

    def test_custom_default_turns(self):
        """Test custom default_turns configuration."""
        config = {'default': 15}
        calculator = MaxTurnsCalculator(config=config)

        task = {
            'id': 16,
            'description': 'Some moderately complex task',
            'estimated_files': 4,
            'estimated_loc': 150
        }

        result = calculator.calculate(task)
        # Falls into "else" case due to estimated_files=4
        # Actually, 4 files falls into: complexity <= 2 or scope == 1 or estimated_files <= 8
        # So it should be 12, not the default
        assert result == 12  # complex (4 files <= 8)

    def test_custom_task_type_defaults(self):
        """Test custom task type defaults configuration."""
        config = {
            'max_turns_by_type': {
                'custom_type': 18,
                'validation': 8  # Override default
            }
        }
        calculator = MaxTurnsCalculator(config=config)

        task1 = {
            'id': 17,
            'task_type': 'custom_type',
            'description': 'Custom task'
        }
        result1 = calculator.calculate(task1)
        assert result1 == 18

        task2 = {
            'id': 18,
            'task_type': 'validation',
            'description': 'Validation task'
        }
        result2 = calculator.calculate(task2)
        assert result2 == 8  # Override from config

    def test_all_task_type_defaults(self):
        """Test all predefined task type defaults."""
        calculator = MaxTurnsCalculator()

        expected = {
            'validation': 5,
            'code_generation': 12,
            'refactoring': 15,
            'debugging': 20,
            'error_analysis': 8,
            'planning': 5,
            'documentation': 3,
            'testing': 8,
        }

        for task_type, expected_turns in expected.items():
            task = {
                'id': 100,
                'task_type': task_type,
                'description': f'Test {task_type}'
            }
            result = calculator.calculate(task)
            assert result == expected_turns, f"Failed for task_type={task_type}"

    def test_multiple_complexity_words(self):
        """Test task with multiple complexity words."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 19,
            'title': 'Refactor and migrate',
            'description': 'Refactor module and migrate to new framework',
            'estimated_files': 6,
            'estimated_loc': 350
        }

        result = calculator.calculate(task)
        # complexity=3 (refactor, migrate, framework), 6 files
        # Falls into: complexity <= 2 or scope == 1 or estimated_files <= 8
        # complexity > 2 but files <= 8, so 12 turns
        assert result == 12  # complex

    def test_multiple_scope_indicators(self):
        """Test task with multiple scope indicators."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 20,
            'title': 'Update project-wide',
            'description': 'Update across entire codebase in all files',
            'estimated_files': 25,
            'estimated_loc': 200
        }

        result = calculator.calculate(task)
        # scope >= 2 (project-wide, across, entire codebase, all files)
        assert result == 20  # very complex

    def test_edge_case_exactly_8_files(self):
        """Test edge case with exactly 8 files."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 21,
            'description': 'Update 8 files',
            'estimated_files': 8,
            'estimated_loc': 200
        }

        result = calculator.calculate(task)
        # estimated_files <= 8, so complex
        assert result == 12  # complex

    def test_edge_case_exactly_500_loc(self):
        """Test edge case with exactly 500 LOC."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 22,
            'description': 'Task with 500 lines',
            'estimated_files': 5,
            'estimated_loc': 500
        }

        result = calculator.calculate(task)
        # estimated_loc <= 500, so not very complex from LOC
        # But 5 files falls into complex category
        assert result == 12  # complex

    def test_edge_case_exactly_501_loc(self):
        """Test edge case with 501 LOC (triggers very complex)."""
        calculator = MaxTurnsCalculator()
        task = {
            'id': 23,
            'description': 'Task with 501 lines',
            'estimated_files': 5,
            'estimated_loc': 501
        }

        result = calculator.calculate(task)
        # estimated_loc > 500, so very complex
        assert result == 20  # very complex

    def test_no_task_id(self):
        """Test handling of task without ID (for logging)."""
        calculator = MaxTurnsCalculator()
        task = {
            'description': 'Task without ID'
        }

        result = calculator.calculate(task)
        # Should not crash, uses 'unknown' for logging
        assert result == 3  # simple task

    def test_integration_with_complexity_estimator_output(self):
        """Test integration with ComplexityEstimate output."""
        calculator = MaxTurnsCalculator()

        # Simulate task with ComplexityEstimate metadata
        task = {
            'id': 24,
            'title': 'Add feature',
            'description': 'Add new feature to module',
            'estimated_files': 7,
            'estimated_loc': 400,
            'complexity_score': 65  # Not used by calculator, but present
        }

        result = calculator.calculate(task)
        assert result == 12  # complex (7 files, 400 LOC)
