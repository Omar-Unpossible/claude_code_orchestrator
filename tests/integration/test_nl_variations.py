"""Variation stress tests for NL command parsing.

⭐ STRESS TESTS - 100+ VARIATIONS (QUICK MODE) ⭐

Tests NL parsing robustness with 10 variations per base command.
Validates that different phrasings, synonyms, case variations,
typos, and verbosity all parse correctly.

Quick mode (10 variations): ~20 minutes execution time.
For comprehensive testing (100 variations), see test_nl_variations_full.py

Skipped if LLM unavailable (CI-friendly).
"""

import pytest
import logging
from typing import Dict, List, Any
from src.nl.types import EntityType, OperationType

logger = logging.getLogger(__name__)


@pytest.fixture
def variation_generator(real_llm):
    """Create variation generator with real LLM."""
    from tests.fixtures.nl_variation_generator import NLVariationGenerator
    return NLVariationGenerator(real_llm)


@pytest.mark.real_llm
@pytest.mark.stress_test
@pytest.mark.slow
class TestNLCreateVariations:
    """Stress test CREATE operations with variations."""

    def test_create_epic_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'create epic' command (quick mode)."""
        base_command = "create epic for user authentication"

        # Generate variations (quick mode: 10 instead of 100)
        variations = variation_generator.generate_variations(
            base_command,
            count=10
        )

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                # Validate operation type
                assert parsed.operation_context.operation == OperationType.CREATE, \
                    f"Wrong operation: {parsed.operation_context.operation}"

                # Validate entity type
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'epic' in entity_types, \
                    f"Missing EPIC entity type, got: {entity_types}"

                # Allow lower confidence for variations (typos, etc.)
                assert parsed.confidence > 0.6, \
                    f"Low confidence: {parsed.confidence}"

                passed += 1

                if i % 10 == 0:
                    logger.info(f"Progress: {i}/{len(variations)} ({passed} passed)")

            except AssertionError as e:
                failed.append({
                    'variation': variant,
                    'error': str(e)
                })
                logger.warning(f"Variation {i} failed: {variant} - {e}")

        # Calculate pass rate
        pass_rate = (passed / len(variations)) * 100

        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        # Log failures
        if failed:
            logger.warning(f"Failed variations ({len(failed)}):")
            for f in failed[:10]:  # Show first 10
                logger.warning(f"  - '{f['variation']}': {f['error']}")

        # Require 90% pass rate
        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}% (expected ≥90%)\n" \
            f"Failures: {failed[:5]}"

    def test_create_story_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'create story' command."""
        base_command = "add a story for password reset to epic 5"

        variations = variation_generator.generate_variations(base_command, count=10)

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                # Validate operation and entity
                assert parsed.operation_context.operation == OperationType.CREATE
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'story' in entity_types
                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError as e:
                failed.append({'variation': variant, 'error': str(e)})

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}%\nFailures: {failed[:5]}"

    def test_create_task_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'create task' command."""
        base_command = "create a task for implementing the login form"

        variations = variation_generator.generate_variations(base_command, count=10)

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                assert parsed.operation_context.operation == OperationType.CREATE
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'task' in entity_types
                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError as e:
                failed.append({'variation': variant, 'error': str(e)})

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}%\nFailures: {failed[:5]}"


@pytest.mark.real_llm
@pytest.mark.stress_test
@pytest.mark.slow
class TestNLUpdateVariations:
    """Stress test UPDATE operations with variations."""

    def test_update_task_status_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'update task status' command."""
        base_command = "mark task 42 as completed"

        variations = variation_generator.generate_variations(base_command, count=10)

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                # Validate operation
                assert parsed.operation_context.operation == OperationType.UPDATE

                # Validate entity type
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'task' in entity_types

                # Validate identifier extraction (may be int or str)
                identifier = parsed.operation_context.identifier
                assert identifier == 42 or identifier == '42', \
                    f"Wrong identifier: {identifier}"

                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError as e:
                failed.append({'variation': variant, 'error': str(e)})

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}%\nFailures: {failed[:5]}"

    def test_update_task_title_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'update task title' command."""
        base_command = "update task 5 title to New Task Title"

        variations = variation_generator.generate_variations(base_command, count=10)

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                assert parsed.operation_context.operation == OperationType.UPDATE
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'task' in entity_types

                identifier = parsed.operation_context.identifier
                assert identifier == 5 or identifier == '5'
                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError as e:
                failed.append({'variation': variant, 'error': str(e)})

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}%\nFailures: {failed[:5]}"


@pytest.mark.real_llm
@pytest.mark.stress_test
@pytest.mark.slow
class TestNLQueryVariations:
    """Stress test QUERY operations with variations."""

    def test_list_tasks_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'list tasks' command."""
        base_command = "show me all tasks"

        variations = variation_generator.generate_variations(base_command, count=10)

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                # Query operations should be QUERY type
                assert parsed.operation_context.operation == OperationType.QUERY

                # Should involve tasks
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'task' in entity_types

                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError as e:
                failed.append({'variation': variant, 'error': str(e)})

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}%\nFailures: {failed[:5]}"

    def test_count_tasks_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'count tasks' command."""
        base_command = "how many tasks are there"

        variations = variation_generator.generate_variations(base_command, count=10)

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                # Could be QUERY or QUESTION intent
                assert parsed.intent_type in ['COMMAND', 'QUESTION']

                # If COMMAND, should be QUERY operation
                if parsed.intent_type == 'COMMAND':
                    assert parsed.operation_context.operation == OperationType.QUERY

                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError as e:
                failed.append({'variation': variant, 'error': str(e)})

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}%\nFailures: {failed[:5]}"


@pytest.mark.real_llm
@pytest.mark.stress_test
@pytest.mark.slow
class TestNLDeleteVariations:
    """Stress test DELETE operations with variations."""

    def test_delete_task_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test 10 variations of 'delete task' command."""
        base_command = "delete task 15"

        variations = variation_generator.generate_variations(base_command, count=10)

        logger.info(f"Testing {len(variations)} variations of: '{base_command}'")

        passed = 0
        failed = []

        for i, variant in enumerate(variations, 1):
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                assert parsed.operation_context.operation == OperationType.DELETE

                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'task' in entity_types

                identifier = parsed.operation_context.identifier
                assert identifier == 15 or identifier == '15'

                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError as e:
                failed.append({'variation': variant, 'error': str(e)})

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Results: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0, \
            f"Pass rate too low: {pass_rate:.1f}%\nFailures: {failed[:5]}"


@pytest.mark.real_llm
@pytest.mark.stress_test
@pytest.mark.slow
class TestNLCategoryValidation:
    """Test specific variation categories."""

    def test_synonym_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test synonym variations (create→add, make, build)."""
        base_command = "create epic for user authentication"

        # Generate only synonym variations
        variations = variation_generator.generate_variations(
            base_command,
            count=5,
            categories=['synonyms']
        )

        logger.info(f"Testing {len(variations)} synonym variations")

        passed = 0
        for variant in variations:
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                assert parsed.operation_context.operation == OperationType.CREATE
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'epic' in entity_types
                passed += 1

            except AssertionError:
                pass

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Synonym variations: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 85.0  # Slightly lower threshold for specific categories

    def test_typo_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test typo variations (create→crete, epic→epik)."""
        base_command = "create epic for user authentication"

        # Generate only typo variations
        variations = variation_generator.generate_variations(
            base_command,
            count=5,
            categories=['typos']
        )

        logger.info(f"Testing {len(variations)} typo variations")

        passed = 0
        for variant in variations:
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                assert parsed.operation_context.operation == OperationType.CREATE
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'epic' in entity_types
                # Lower confidence acceptable for typos
                assert parsed.confidence > 0.5

                passed += 1

            except AssertionError:
                pass

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Typo variations: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        # Lower threshold for typos (harder to handle)
        assert pass_rate >= 70.0, \
            f"Typo tolerance too low: {pass_rate:.1f}%"

    def test_verbose_variations(
        self,
        real_nl_processor_with_llm,
        variation_generator
    ):
        """Test verbose variations (please, can you, I would like)."""
        base_command = "create epic for user authentication"

        # Generate only verbose variations
        variations = variation_generator.generate_variations(
            base_command,
            count=5,
            categories=['verbose']
        )

        logger.info(f"Testing {len(variations)} verbose variations")

        passed = 0
        for variant in variations:
            try:
                parsed = real_nl_processor_with_llm.process(
                    variant,
                    context={'project_id': 1}
                )

                assert parsed.operation_context.operation == OperationType.CREATE
                entity_types = [et.value for et in parsed.operation_context.entity_types]
                assert 'epic' in entity_types
                assert parsed.confidence > 0.6

                passed += 1

            except AssertionError:
                pass

        pass_rate = (passed / len(variations)) * 100
        logger.info(f"Verbose variations: {passed}/{len(variations)} passed ({pass_rate:.1f}%)")

        assert pass_rate >= 90.0  # Should handle verbose well
