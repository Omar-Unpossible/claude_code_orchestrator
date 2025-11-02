"""Tests for ConfidenceScorer - multi-factor confidence scoring."""

import pytest
from unittest.mock import Mock

from src.core.models import Task
from src.utils.confidence_scorer import ConfidenceScorer


@pytest.fixture
def scorer():
    """Create ConfidenceScorer instance."""
    return ConfidenceScorer()


@pytest.fixture
def llm_interface():
    """Create mock LLM interface."""
    mock_llm = Mock()
    # Return properly formatted score response
    mock_llm.send_prompt = Mock(return_value="""
completeness: 0.8
coherence: 0.9
correctness: 0.85
relevance: 0.75
specificity: 0.7
""")
    return mock_llm


@pytest.fixture
def task():
    """Create test task."""
    task = Mock(spec=Task)
    task.id = 1
    task.project_id = 1
    task.description = "Implement a function to add two numbers"
    return task


class TestConfidenceScorerInitialization:
    """Test ConfidenceScorer initialization."""

    def test_default_initialization(self):
        """Test scorer initializes with defaults."""
        scorer = ConfidenceScorer()

        assert scorer.llm_interface is None
        assert scorer.config == {}
        assert len(scorer._calibration_data) == 0

    def test_custom_config_initialization(self, llm_interface):
        """Test scorer initializes with LLM interface."""
        scorer = ConfidenceScorer(llm_interface=llm_interface)

        assert scorer.llm_interface is llm_interface


class TestHeuristicScoring:
    """Test heuristic-based scoring."""

    def test_score_heuristic_good_response(self, scorer, task):
        """Test scoring good response."""
        response = '''def add(a, b):
            """Add two numbers."""
            return a + b

Example:
    >>> add(2, 3)
    5
'''

        score = scorer.score_heuristic(response, task)

        assert 0.5 <= score <= 1.0

    def test_score_heuristic_poor_response(self, scorer, task):
        """Test scoring poor response."""
        response = "TODO: implement this"

        score = scorer.score_heuristic(response, task)

        # Should score low due to TODO marker
        assert score < 0.8

    def test_score_heuristic_empty_response(self, scorer, task):
        """Test scoring empty response."""
        score = scorer.score_heuristic("", task)

        assert score == 0.0

    def test_score_completeness(self, scorer, task):
        """Test completeness scoring."""
        # Empty response
        score = scorer._score_completeness("", task)
        assert score == 0.0

        # Response with code
        score = scorer._score_completeness("def foo(): pass", task)
        assert score > 0.5

        # Response with code and explanation
        response = "def foo(): pass\n\nThis implements the foo function with examples."
        score = scorer._score_completeness(response, task)
        assert score > 0.7

    def test_score_coherence(self, scorer):
        """Test coherence scoring."""
        # Coherent response
        coherent = "First, we do X. Then, we do Y. Finally, Z."
        score = scorer._score_coherence(coherent)
        assert score > 0.8

        # Response with contradictions
        contradictory = "This can work. This can't work."
        score = scorer._score_coherence(contradictory)
        assert score < 1.0

    def test_score_correctness(self, scorer):
        """Test correctness scoring."""
        # Good code
        score = scorer._score_correctness("def add(a, b): return a + b")
        assert score > 0.8

        # Code with errors
        score = scorer._score_correctness("def foo(): pass  # TODO: implement")
        assert score < 1.0

        # Code with error markers
        score = scorer._score_correctness("This failed with an error")
        assert score < 1.0

    def test_score_relevance(self, scorer, task):
        """Test relevance scoring."""
        # Relevant response
        relevant = "Implement a function to add two numbers: def add(a, b): return a + b"
        score = scorer._score_relevance(relevant, task)
        assert score > 0.3

        # Irrelevant response
        irrelevant = "Something completely different xyz"
        score = scorer._score_relevance(irrelevant, task)
        assert score < 0.5

    def test_score_specificity(self, scorer):
        """Test specificity scoring."""
        # Specific response with details
        specific = 'The function returns 42 and uses specific("exact") parameters.'
        score = scorer._score_specificity(specific)
        assert score > 0.6

        # Vague response
        vague = "Maybe possibly it might generally work"
        score = scorer._score_specificity(vague)
        assert score < 0.5


class TestLLMScoring:
    """Test LLM-based scoring."""

    def test_score_with_llm(self, llm_interface, task):
        """Test scoring using LLM."""
        scorer = ConfidenceScorer(llm_interface=llm_interface)

        response = "def add(a, b): return a + b"
        score = scorer.score_with_llm(response, task)

        assert 0.0 <= score <= 1.0
        assert llm_interface.send_prompt.called

    def test_score_with_llm_unavailable(self, scorer, task):
        """Test LLM scoring when LLM unavailable."""
        with pytest.raises(RuntimeError):
            scorer.score_with_llm("response", task)

    def test_parse_llm_scores(self, scorer):
        """Test parsing scores from LLM response."""
        llm_response = """
completeness: 0.85
coherence: 0.90
correctness: 0.75
relevance: 0.80
specificity: 0.70
"""

        scores = scorer._parse_llm_scores(llm_response)

        assert scores['completeness'] == 0.85
        assert scores['coherence'] == 0.90
        assert 0.0 <= scores['correctness'] <= 1.0

    def test_parse_llm_scores_invalid(self, scorer):
        """Test parsing invalid LLM response."""
        scores = scorer._parse_llm_scores("Invalid response")

        # Should return empty dict
        assert isinstance(scores, dict)


class TestEnsembleScoring:
    """Test ensemble scoring."""

    def test_ensemble_score(self, scorer):
        """Test combining scores."""
        scores = {'heuristic': 0.7, 'llm': 0.9}
        weights = {'heuristic': 0.4, 'llm': 0.6}

        ensemble = scorer.ensemble_score(scores, weights)

        expected = (0.7 * 0.4 + 0.9 * 0.6) / (0.4 + 0.6)
        assert abs(ensemble - expected) < 0.01

    def test_ensemble_score_empty(self, scorer):
        """Test ensemble with no scores."""
        ensemble = scorer.ensemble_score({}, {})

        assert ensemble == 0.5  # Default

    def test_score_response_with_llm(self, llm_interface, task):
        """Test full response scoring with LLM."""
        scorer = ConfidenceScorer(llm_interface=llm_interface)

        response = "def add(a, b): return a + b"
        score = scorer.score_response(response, task)

        # Should use ensemble of heuristic + LLM
        assert 0.0 <= score <= 1.0

    def test_score_response_without_llm(self, scorer, task):
        """Test response scoring without LLM."""
        response = "def add(a, b): return a + b"
        score = scorer.score_response(response, task)

        # Should use heuristic only
        assert 0.0 <= score <= 1.0


class TestCalibration:
    """Test confidence calibration."""

    def test_calibrate_basic(self, scorer):
        """Test basic calibration."""
        scorer.calibrate(0.85, True)
        scorer.calibrate(0.60, False)

        assert len(scorer._calibration_data) == 2

    def test_calibrate_limits_history(self, scorer):
        """Test calibration history is limited."""
        # Add 1100 calibration points
        for i in range(1100):
            scorer.calibrate(0.5, i % 2 == 0)

        # Should keep only last 1000
        assert len(scorer._calibration_data) == 1000

    def test_get_calibration_stats_empty(self, scorer):
        """Test getting stats with no calibration data."""
        stats = scorer.get_calibration_stats()

        assert stats['sample_count'] == 0
        assert stats['accuracy'] == 0.0

    def test_get_calibration_stats_with_data(self, scorer):
        """Test getting calibration statistics."""
        # Add some calibration data
        scorer.calibrate(0.8, True)
        scorer.calibrate(0.9, True)
        scorer.calibrate(0.6, False)

        stats = scorer.get_calibration_stats()

        assert stats['sample_count'] == 3
        assert 0.0 <= stats['accuracy'] <= 1.0
        assert 'mean_predicted_confidence' in stats
        assert 'calibration_error' in stats


class TestConfidenceDistribution:
    """Test confidence distribution tracking."""

    def test_get_confidence_distribution_empty(self, scorer):
        """Test getting distribution with no data."""
        dist = scorer.get_confidence_distribution(project_id=1)

        assert dist['count'] == 0
        assert dist['mean'] == 0.0

    def test_get_confidence_distribution_with_data(self, scorer, task):
        """Test getting distribution with data."""
        # Score some responses
        for _ in range(5):
            scorer.score_response("def foo(): pass", task)

        dist = scorer.get_confidence_distribution(task.project_id)

        assert dist['count'] == 5
        assert 0.0 <= dist['mean'] <= 1.0
        assert 'min' in dist
        assert 'max' in dist
        assert 'std' in dist


class TestConfidenceExplanation:
    """Test confidence explanation."""

    def test_explain_confidence_high(self, scorer):
        """Test explaining high confidence."""
        explanation = scorer.explain_confidence(0.95, {'completeness': 0.9})

        assert 'high' in explanation.lower()
        assert '0.95' in explanation

    def test_explain_confidence_medium(self, scorer):
        """Test explaining medium confidence."""
        explanation = scorer.explain_confidence(0.65, {})

        assert 'medium' in explanation.lower()

    def test_explain_confidence_low(self, scorer):
        """Test explaining low confidence."""
        explanation = scorer.explain_confidence(0.35, {})

        assert 'low' in explanation.lower()

    def test_explain_confidence_with_factors(self, scorer):
        """Test explanation includes factor breakdown."""
        factors = {
            'completeness': 0.9,
            'coherence': 0.8,
            'correctness': 0.85
        }

        explanation = scorer.explain_confidence(0.85, factors)

        assert 'completeness' in explanation.lower()
        assert 'coherence' in explanation.lower()


class TestConfidencePrediction:
    """Test confidence prediction."""

    def test_predict_confidence_basic(self, scorer, task):
        """Test basic confidence prediction."""
        prediction = scorer.predict_confidence(task, {})

        assert 0.0 <= prediction <= 1.0

    def test_predict_confidence_simple_task(self, scorer):
        """Test prediction for simple task."""
        task = Mock(spec=Task)
        task.description = "Simple basic easy task"

        prediction = scorer.predict_confidence(task, {})

        # Simple task should have higher predicted confidence
        assert prediction >= 0.5

    def test_predict_confidence_complex_task(self, scorer):
        """Test prediction for complex task."""
        task = Mock(spec=Task)
        task.description = "Complex difficult challenging advanced task"

        prediction = scorer.predict_confidence(task, {})

        # Complex task should have lower predicted confidence
        assert prediction <= 0.7

    def test_predict_confidence_no_task(self, scorer):
        """Test prediction with no task."""
        prediction = scorer.predict_confidence(None, {})

        assert prediction == 0.5  # Default


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_score_very_long_response(self, scorer, task):
        """Test scoring very long response."""
        response = "word " * 100000
        score = scorer.score_heuristic(response, task)

        assert 0.0 <= score <= 1.0

    def test_score_special_characters(self, scorer, task):
        """Test scoring response with special characters."""
        response = "def foo(): return @#$% 你好 🎉"
        score = scorer.score_heuristic(response, task)

        assert 0.0 <= score <= 1.0

    def test_score_no_task(self, scorer):
        """Test scoring with no task."""
        score = scorer.score_heuristic("response", None)

        assert 0.0 <= score <= 1.0


class TestThreadSafety:
    """Test thread-safe operations."""

    def test_concurrent_scoring(self, scorer, task):
        """Test scoring concurrently."""
        import threading

        scores = []

        def score():
            s = scorer.score_response("def foo(): pass", task)
            scores.append(s)

        threads = [threading.Thread(target=score) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # All should complete
        assert len(scores) == 10
        assert all(0.0 <= s <= 1.0 for s in scores)

    def test_concurrent_calibration(self, scorer):
        """Test concurrent calibration updates."""
        import threading

        def calibrate():
            for i in range(10):
                scorer.calibrate(0.5 + i * 0.05, i % 2 == 0)

        threads = [threading.Thread(target=calibrate) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        # Should have calibration data
        assert len(scorer._calibration_data) > 0
