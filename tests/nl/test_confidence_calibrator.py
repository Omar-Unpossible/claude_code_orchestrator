"""Tests for confidence calibration system (Phase 4.1).

These tests validate the operation-specific and context-aware confidence
thresholds introduced to address Phase 3 findings.
"""

import pytest
from src.nl.confidence_calibrator import ConfidenceCalibrator, ConfidenceThreshold
from src.nl.types import OperationType


class TestConfidenceThreshold:
    """Test ConfidenceThreshold dataclass."""

    def test_default_thresholds(self):
        """Default thresholds should match Phase 3 calibration"""
        thresholds = ConfidenceThreshold()

        assert thresholds.default == 0.6
        assert thresholds.create == 0.55  # More lenient
        assert thresholds.update == 0.6   # Standard
        assert thresholds.delete == 0.6   # Standard
        assert thresholds.query == 0.58   # Slightly lower

    def test_context_penalties(self):
        """Context penalties should be configured"""
        thresholds = ConfidenceThreshold()

        assert thresholds.has_typo_penalty == 0.05
        assert thresholds.casual_language_penalty == 0.03


class TestConfidenceCalibrator:
    """Test calibrated thresholds and acceptance logic."""

    @pytest.fixture
    def calibrator(self):
        """Create calibrator with default thresholds."""
        return ConfidenceCalibrator()

    def test_create_operation_lower_threshold(self, calibrator):
        """CREATE operations should have lower threshold (0.55)

        Phase 3 showed CREATE has mean=0.57 with 100% accuracy.
        Threshold of 0.55 captures valid variations.
        """
        threshold = calibrator.get_threshold(OperationType.CREATE)
        assert threshold == 0.55

    def test_update_operation_standard_threshold(self, calibrator):
        """UPDATE operations should have standard threshold (0.6)

        Phase 3 showed UPDATE has mean=0.78, working well at 0.6.
        """
        threshold = calibrator.get_threshold(OperationType.UPDATE)
        assert threshold == 0.6

    def test_delete_operation_standard_threshold(self, calibrator):
        """DELETE operations should have standard threshold (0.6)

        Phase 3 showed DELETE has mean=0.82, working well at 0.6.
        """
        threshold = calibrator.get_threshold(OperationType.DELETE)
        assert threshold == 0.6

    def test_query_operation_lower_threshold(self, calibrator):
        """QUERY operations should have slightly lower threshold (0.58)

        Phase 3 showed QUERY has mean=0.61 with variations in COUNT queries.
        """
        threshold = calibrator.get_threshold(OperationType.QUERY)
        assert threshold == 0.58

    def test_typo_penalty_applied(self, calibrator):
        """Typos should lower threshold by 0.05

        Phase 3 showed typos result in correct parsing but lower confidence.
        Lowering threshold allows these valid parses to pass.
        """
        normal = calibrator.get_threshold(OperationType.CREATE, has_typos=False)
        with_typo = calibrator.get_threshold(OperationType.CREATE, has_typos=True)

        assert with_typo < normal
        assert with_typo == normal - 0.05  # Penalty is 0.05
        assert with_typo == 0.50  # 0.55 - 0.05

    def test_casual_language_penalty(self, calibrator):
        """Casual language should lower threshold by 0.03

        Phase 3 showed casual phrasing ("I need...", "Can you...") lowers
        confidence but parsing is still correct.
        """
        formal = calibrator.get_threshold(OperationType.CREATE, is_casual=False)
        casual = calibrator.get_threshold(OperationType.CREATE, is_casual=True)

        assert casual < formal
        assert casual == formal - 0.03  # Penalty is 0.03
        assert casual == 0.52  # 0.55 - 0.03

    def test_combined_penalties(self, calibrator):
        """Multiple context penalties should stack

        If input has typos AND casual language, both penalties apply.
        """
        base = calibrator.get_threshold(OperationType.CREATE)
        casual_only = calibrator.get_threshold(OperationType.CREATE, is_casual=True)
        both = calibrator.get_threshold(
            OperationType.CREATE,
            has_typos=True,
            is_casual=True
        )

        assert both == base - 0.05 - 0.03  # Both penalties
        assert both == 0.47  # 0.55 - 0.05 - 0.03
        assert both < casual_only

    def test_should_accept_create_with_low_confidence(self, calibrator):
        """CREATE with 0.56 confidence should ACCEPT (threshold 0.55)

        This is a Phase 3 failure case - parsing was correct but confidence
        of 0.56 failed the 0.6 threshold. With calibration, it should pass.
        """
        accept, reason = calibrator.should_accept(
            confidence=0.56,
            operation=OperationType.CREATE
        )

        assert accept is True
        assert "0.56" in reason
        assert "0.55" in reason
        assert ">=" in reason
        assert "CREATE" in reason

    def test_should_reject_update_with_low_confidence(self, calibrator):
        """UPDATE with 0.56 confidence should REJECT (threshold 0.6)

        UPDATE operations have higher mean confidence (0.78), so lower
        confidence likely indicates genuine uncertainty.
        """
        accept, reason = calibrator.should_accept(
            confidence=0.56,
            operation=OperationType.UPDATE
        )

        assert accept is False
        assert "0.56" in reason
        assert "0.60" in reason
        assert "<" in reason
        assert "UPDATE" in reason

    def test_should_accept_with_typo_penalty(self, calibrator):
        """Low confidence with typos should pass with penalty applied

        Confidence 0.52 would fail normal CREATE threshold (0.55), but
        should pass with typo penalty (threshold becomes 0.50).
        """
        accept, reason = calibrator.should_accept(
            confidence=0.52,
            operation=OperationType.CREATE,
            has_typos=True
        )

        assert accept is True
        assert "0.52" in reason
        assert "0.50" in reason
        assert ">=" in reason

    def test_should_accept_with_casual_penalty(self, calibrator):
        """Low confidence with casual language should pass with penalty

        Confidence 0.53 would fail normal CREATE threshold (0.55), but
        should pass with casual penalty (threshold becomes 0.52).
        """
        accept, reason = calibrator.should_accept(
            confidence=0.53,
            operation=OperationType.CREATE,
            is_casual=True
        )

        assert accept is True
        assert "0.53" in reason
        assert "0.52" in reason
        assert ">=" in reason

    def test_boundary_cases(self, calibrator):
        """Test exact boundary confidence values

        Equality (>=) should accept, not strict inequality (>).
        """
        # Exact match should accept
        accept, _ = calibrator.should_accept(
            confidence=0.55,
            operation=OperationType.CREATE
        )
        assert accept is True

        # Just below should reject
        accept, _ = calibrator.should_accept(
            confidence=0.5499,
            operation=OperationType.CREATE
        )
        assert accept is False

    def test_get_statistics_for_create(self, calibrator):
        """Should return Phase 3 calibration statistics for CREATE"""
        stats = calibrator.get_statistics(OperationType.CREATE)

        assert stats['mean_confidence'] == 0.57
        assert stats['std'] == 0.04
        assert stats['accuracy'] == 1.0
        assert stats['sample_size'] == 100

    def test_get_statistics_for_all_operations(self, calibrator):
        """All operations should have Phase 3 calibration data"""
        operations = [
            OperationType.CREATE,
            OperationType.UPDATE,
            OperationType.DELETE,
            OperationType.QUERY
        ]

        for operation in operations:
            stats = calibrator.get_statistics(operation)

            # All should have statistics
            assert 'mean_confidence' in stats
            assert 'std' in stats
            assert 'accuracy' in stats
            assert stats['accuracy'] == 1.0  # Phase 3 showed 100% parsing accuracy

    def test_custom_thresholds(self):
        """Should support custom threshold configuration"""
        custom_thresholds = ConfidenceThreshold(
            create=0.50,  # Even more lenient
            update=0.70,  # Stricter
        )

        calibrator = ConfidenceCalibrator(thresholds=custom_thresholds)

        assert calibrator.get_threshold(OperationType.CREATE) == 0.50
        assert calibrator.get_threshold(OperationType.UPDATE) == 0.70

    def test_phase3_failure_case_build_epic(self, calibrator):
        """Reproduce Phase 3 failure: 'build epic' with confidence 0.485

        Phase 3 showed "build epic for auth" had:
        - Parsing: 100% correct
        - Confidence: 0.485 (failed 0.6 threshold)

        This should still fail even with calibration (0.485 < 0.55).
        Task 4.2 (synonym expansion) will address this by improving
        the confidence score itself.
        """
        accept, reason = calibrator.should_accept(
            confidence=0.485,
            operation=OperationType.CREATE
        )

        # Still fails (threshold is 0.55, not low enough for 0.485)
        assert accept is False
        assert "0.48" in reason  # Rounded to 0.48
        assert "0.55" in reason
        assert "<" in reason

        # But it's CLOSER to passing (0.485 vs 0.55) than before (0.485 vs 0.6)
        # This is progress! Task 4.2 will fix the root cause.

    def test_phase3_failure_case_i_need_epic(self, calibrator):
        """Reproduce Phase 3 failure: 'I need an epic' with confidence 0.56

        Phase 3 showed casual language "I need an epic for auth" had:
        - Parsing: 100% correct
        - Confidence: 0.56 (failed 0.6 threshold)

        With calibration + casual penalty, this SHOULD PASS.
        """
        accept, reason = calibrator.should_accept(
            confidence=0.56,
            operation=OperationType.CREATE,
            is_casual=True
        )

        # Should pass! (0.56 >= 0.52 with casual penalty)
        assert accept is True
        assert "0.56" in reason
        assert "0.52" in reason
        assert ">=" in reason

        # This fixes one of the Phase 3 failure modes!

    def test_phase3_failure_case_typo(self, calibrator):
        """Reproduce Phase 3 failure: 'crete epik' with confidence 0.52

        Phase 3 showed typos "crete epik for auth" had:
        - Parsing: 100% correct (typo handling works!)
        - Confidence: 0.52 (failed 0.6 threshold)

        With calibration + typo penalty, this SHOULD PASS.
        """
        accept, reason = calibrator.should_accept(
            confidence=0.52,
            operation=OperationType.CREATE,
            has_typos=True
        )

        # Should pass! (0.52 >= 0.50 with typo penalty)
        assert accept is True
        assert "0.52" in reason
        assert "0.50" in reason
        assert ">=" in reason

        # This fixes another Phase 3 failure mode!
