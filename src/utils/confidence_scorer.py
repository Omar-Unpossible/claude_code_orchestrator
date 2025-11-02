"""Multi-factor confidence scoring with calibration and learning.

This module implements the ConfidenceScorer class for scoring response quality
using multiple methods (heuristic, LLM-based, ensemble) with calibration.

Example:
    >>> scorer = ConfidenceScorer(llm_interface)
    >>> score = scorer.score_response(response, task, context)
    >>> print(f"Confidence: {score:.2f}")
"""

import logging
import re
from datetime import datetime, UTC
from threading import RLock
from typing import Dict, List, Any, Optional, Tuple

from src.core.models import Task

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """Multi-factor confidence scoring with calibration.

    Scores response quality using:
    - Heuristic scoring (fast, rule-based)
    - LLM-based scoring (slow, accurate)
    - Ensemble scoring (combines both)

    Learns from outcomes to improve calibration over time.

    Thread-safe for concurrent access.

    Example:
        >>> scorer = ConfidenceScorer()
        >>> score = scorer.score_response("def add(a, b): return a + b", task)
        >>> assert 0.0 <= score <= 1.0
    """

    # Scoring weights for factors
    WEIGHT_COMPLETENESS = 0.25
    WEIGHT_COHERENCE = 0.20
    WEIGHT_CORRECTNESS = 0.30
    WEIGHT_RELEVANCE = 0.15
    WEIGHT_SPECIFICITY = 0.10

    # Ensemble weights
    ENSEMBLE_WEIGHT_HEURISTIC = 0.4
    ENSEMBLE_WEIGHT_LLM = 0.6

    def __init__(
        self,
        llm_interface: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize confidence scorer.

        Args:
            llm_interface: Optional LLM interface for LLM-based scoring
            config: Optional configuration dictionary
        """
        self.llm_interface = llm_interface
        self.config = config or {}
        self._lock = RLock()

        # Calibration data (predicted_score, actual_outcome)
        self._calibration_data: List[Tuple[float, bool]] = []

        # Confidence tracking
        self._confidence_history: Dict[int, List[float]] = {}

        logger.info("ConfidenceScorer initialized")

    def score_response(
        self,
        response: str,
        task: Task,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Score response confidence using ensemble method.

        Combines heuristic and LLM-based scoring for best accuracy.

        Args:
            response: Response text to score
            task: Task being responded to
            context: Optional context dictionary

        Returns:
            Confidence score (0.0-1.0)

        Example:
            >>> score = scorer.score_response("implementation", task)
            >>> assert 0.0 <= score <= 1.0
        """
        context = context or {}

        # Get scores from both methods
        heuristic_score = self.score_heuristic(response, task)

        # Use LLM scoring if available
        if self.llm_interface:
            try:
                llm_score = self.score_with_llm(response, task)
                # Ensemble
                score = self.ensemble_score(
                    {'heuristic': heuristic_score, 'llm': llm_score},
                    {
                        'heuristic': self.ENSEMBLE_WEIGHT_HEURISTIC,
                        'llm': self.ENSEMBLE_WEIGHT_LLM
                    }
                )
            except Exception as e:
                logger.warning(f"LLM scoring failed: {e}, using heuristic only")
                score = heuristic_score
        else:
            score = heuristic_score

        # Store in history
        with self._lock:
            if task and task.project_id:
                if task.project_id not in self._confidence_history:
                    self._confidence_history[task.project_id] = []
                self._confidence_history[task.project_id].append(score)

        return score

    def score_heuristic(
        self,
        response: str,
        task: Task
    ) -> float:
        """Score response using heuristic rules.

        Fast scoring based on patterns and rules.

        Args:
            response: Response text
            task: Task

        Returns:
            Heuristic score (0.0-1.0)

        Example:
            >>> score = scorer.score_heuristic("def foo(): pass", task)
            >>> assert 0.0 <= score <= 1.0
        """
        scores = {}

        # Completeness: Check for required sections
        completeness = self._score_completeness(response, task)
        scores['completeness'] = completeness

        # Coherence: Check for logical flow
        coherence = self._score_coherence(response)
        scores['coherence'] = coherence

        # Correctness: Basic validation
        correctness = self._score_correctness(response)
        scores['correctness'] = correctness

        # Relevance: Keyword overlap with task
        relevance = self._score_relevance(response, task)
        scores['relevance'] = relevance

        # Specificity: Concrete vs vague
        specificity = self._score_specificity(response)
        scores['specificity'] = specificity

        # Weighted average
        total_score = (
            scores['completeness'] * self.WEIGHT_COMPLETENESS +
            scores['coherence'] * self.WEIGHT_COHERENCE +
            scores['correctness'] * self.WEIGHT_CORRECTNESS +
            scores['relevance'] * self.WEIGHT_RELEVANCE +
            scores['specificity'] * self.WEIGHT_SPECIFICITY
        )

        return max(0.0, min(1.0, total_score))

    def _score_completeness(self, response: str, task: Task) -> float:
        """Score completeness of response.

        Args:
            response: Response text
            task: Task

        Returns:
            Completeness score (0.0-1.0)
        """
        if not response or not response.strip():
            return 0.0

        score = 0.5  # Base score for non-empty

        # Check for common required elements
        has_code = bool(re.search(r'def |class |import |from ', response))
        has_explanation = len(response.split()) > 20
        has_examples = 'example' in response.lower() or '>>>' in response

        if has_code:
            score += 0.2
        if has_explanation:
            score += 0.2
        if has_examples:
            score += 0.1

        return min(1.0, score)

    def _score_coherence(self, response: str) -> float:
        """Score logical coherence.

        Args:
            response: Response text

        Returns:
            Coherence score (0.0-1.0)
        """
        if not response:
            return 0.0

        score = 1.0

        # Check for contradictions (simple heuristic)
        contradiction_patterns = [
            (r'\bnot\s+\w+', r'\bis\s+\w+'),
            (r'\bcan\'t\b', r'\bcan\b'),
            (r'\bdoesn\'t\b', r'\bdoes\b')
        ]

        for neg_pattern, pos_pattern in contradiction_patterns:
            if re.search(neg_pattern, response, re.IGNORECASE) and \
               re.search(pos_pattern, response, re.IGNORECASE):
                score -= 0.1

        # Check for logical flow indicators
        flow_indicators = ['therefore', 'thus', 'so', 'because', 'since', 'first', 'then', 'finally']
        has_flow = any(indicator in response.lower() for indicator in flow_indicators)
        if has_flow:
            score += 0.1

        return max(0.0, min(1.0, score))

    def _score_correctness(self, response: str) -> float:
        """Score basic correctness.

        Args:
            response: Response text

        Returns:
            Correctness score (0.0-1.0)
        """
        if not response:
            return 0.0

        score = 1.0

        # Penalize obvious errors
        error_markers = ['error', 'failed', 'exception', 'todo', 'fixme', 'xxx']
        for marker in error_markers:
            if marker in response.lower():
                score -= 0.15

        # Penalize incomplete code
        if 'pass' in response and 'def ' in response:
            score -= 0.2

        if '...' in response:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _score_relevance(self, response: str, task: Task) -> float:
        """Score relevance to task.

        Args:
            response: Response text
            task: Task

        Returns:
            Relevance score (0.0-1.0)
        """
        if not task or not task.description:
            return 0.5  # Neutral if no task context

        # Keyword overlap
        task_words = set(task.description.lower().split())
        response_words = set(response.lower().split())

        if not task_words:
            return 0.5

        overlap = len(task_words & response_words)
        relevance = overlap / len(task_words)

        return min(1.0, relevance)

    def _score_specificity(self, response: str) -> float:
        """Score specificity (concrete vs vague).

        Args:
            response: Response text

        Returns:
            Specificity score (0.0-1.0)
        """
        if not response:
            return 0.0

        score = 0.5

        # Check for specific details
        has_numbers = bool(re.search(r'\d+', response))
        has_quotes = '"' in response or "'" in response
        has_code = bool(re.search(r'[(){}\[\]]', response))
        has_specifics = any(word in response.lower() for word in ['specifically', 'particular', 'exact', 'precise'])

        if has_numbers:
            score += 0.15
        if has_quotes:
            score += 0.1
        if has_code:
            score += 0.15
        if has_specifics:
            score += 0.1

        # Penalize vague language
        vague_words = ['might', 'maybe', 'perhaps', 'possibly', 'generally', 'usually']
        vague_count = sum(1 for word in vague_words if word in response.lower())
        score -= vague_count * 0.05

        return max(0.0, min(1.0, score))

    def score_with_llm(
        self,
        response: str,
        task: Task
    ) -> float:
        """Score response using LLM assessment.

        Args:
            response: Response text
            task: Task

        Returns:
            LLM-based score (0.0-1.0)

        Example:
            >>> score = scorer.score_with_llm("implementation", task)
        """
        if not self.llm_interface:
            raise RuntimeError("LLM interface not available")

        prompt = f"""Rate the following response on a scale of 0-1 for each factor:
- Completeness (has all required information)
- Coherence (logical and consistent)
- Correctness (factually accurate)
- Relevance (addresses the task)
- Specificity (concrete vs vague)

Task: {task.description if task else 'N/A'}

Response:
{response}

Provide scores in format:
completeness: X.X
coherence: X.X
correctness: X.X
relevance: X.X
specificity: X.X
"""

        try:
            llm_response = self.llm_interface.send_prompt(prompt)
            scores = self._parse_llm_scores(llm_response)

            # Weighted average
            total_score = (
                scores.get('completeness', 0.5) * self.WEIGHT_COMPLETENESS +
                scores.get('coherence', 0.5) * self.WEIGHT_COHERENCE +
                scores.get('correctness', 0.5) * self.WEIGHT_CORRECTNESS +
                scores.get('relevance', 0.5) * self.WEIGHT_RELEVANCE +
                scores.get('specificity', 0.5) * self.WEIGHT_SPECIFICITY
            )

            return max(0.0, min(1.0, total_score))

        except Exception as e:
            logger.error(f"LLM scoring failed: {e}")
            raise

    def _parse_llm_scores(self, llm_response: str) -> Dict[str, float]:
        """Parse scores from LLM response.

        Args:
            llm_response: LLM response text

        Returns:
            Dictionary of factor scores
        """
        scores = {}
        pattern = r'(\w+):\s*([0-9.]+)'

        for match in re.finditer(pattern, llm_response.lower()):
            factor = match.group(1)
            try:
                score = float(match.group(2))
                scores[factor] = max(0.0, min(1.0, score))
            except ValueError:
                continue

        return scores

    def ensemble_score(
        self,
        scores: Dict[str, float],
        weights: Dict[str, float]
    ) -> float:
        """Combine multiple scores using weighted ensemble.

        Args:
            scores: Dictionary of method -> score
            weights: Dictionary of method -> weight

        Returns:
            Ensemble score (0.0-1.0)

        Example:
            >>> scores = {'heuristic': 0.7, 'llm': 0.9}
            >>> weights = {'heuristic': 0.4, 'llm': 0.6}
            >>> ensemble = scorer.ensemble_score(scores, weights)
        """
        if not scores or not weights:
            return 0.5

        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.5

        weighted_sum = sum(
            scores.get(method, 0.5) * weight
            for method, weight in weights.items()
        )

        return max(0.0, min(1.0, weighted_sum / total_weight))

    def calibrate(
        self,
        predicted_confidence: float,
        actual_outcome: bool
    ) -> None:
        """Update calibration with new outcome.

        Args:
            predicted_confidence: Previously predicted confidence
            actual_outcome: Actual outcome (True=success, False=failure)

        Example:
            >>> scorer.calibrate(0.85, True)  # High confidence, successful
        """
        with self._lock:
            self._calibration_data.append((predicted_confidence, actual_outcome))

            # Keep last 1000 calibration points
            if len(self._calibration_data) > 1000:
                self._calibration_data = self._calibration_data[-1000:]

            logger.debug(f"Calibration updated: {predicted_confidence:.2f} -> {actual_outcome}")

    def get_confidence_distribution(
        self,
        project_id: int
    ) -> Dict[str, Any]:
        """Get confidence score distribution for a project.

        Args:
            project_id: Project ID

        Returns:
            Dictionary with distribution statistics

        Example:
            >>> dist = scorer.get_confidence_distribution(project_id=1)
            >>> assert 'mean' in dist
        """
        with self._lock:
            scores = self._confidence_history.get(project_id, [])

            if not scores:
                return {
                    'count': 0,
                    'mean': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'std': 0.0
                }

            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            std = variance ** 0.5

            return {
                'count': len(scores),
                'mean': mean,
                'min': min(scores),
                'max': max(scores),
                'std': std
            }

    def explain_confidence(
        self,
        score: float,
        factors: Dict[str, float]
    ) -> str:
        """Generate explanation for confidence score.

        Args:
            score: Overall confidence score
            factors: Individual factor scores

        Returns:
            Explanation string

        Example:
            >>> explanation = scorer.explain_confidence(0.85, {'completeness': 0.9})
            >>> assert 'high' in explanation.lower()
        """
        if score >= 0.85:
            level = "high"
        elif score >= 0.5:
            level = "medium"
        else:
            level = "low"

        explanation = f"Confidence: {level} ({score:.2f})\n"

        # Add factor breakdowns
        if factors:
            explanation += "\nFactor scores:\n"
            for factor, factor_score in sorted(factors.items(), key=lambda x: x[1], reverse=True):
                explanation += f"  - {factor}: {factor_score:.2f}\n"

        return explanation

    def predict_confidence(
        self,
        task: Task,
        context: Dict[str, Any]
    ) -> float:
        """Predict confidence before execution.

        Args:
            task: Task to predict for
            context: Context dictionary

        Returns:
            Predicted confidence

        Example:
            >>> prediction = scorer.predict_confidence(task, {})
            >>> assert 0.0 <= prediction <= 1.0
        """
        # Simple prediction based on task complexity
        if not task or not task.description:
            return 0.5

        description = task.description.lower()

        # Heuristics for prediction
        score = 0.5

        # Simple tasks
        if any(word in description for word in ['simple', 'easy', 'basic', 'trivial']):
            score += 0.2

        # Complex tasks
        if any(word in description for word in ['complex', 'difficult', 'advanced', 'challenging']):
            score -= 0.2

        # Clear requirements
        if len(description.split()) > 20:
            score += 0.1

        # Vague requirements
        if any(word in description for word in ['might', 'maybe', 'possibly']):
            score -= 0.1

        return max(0.0, min(1.0, score))

    def get_calibration_stats(self) -> Dict[str, Any]:
        """Get calibration statistics.

        Returns:
            Calibration statistics dictionary

        Example:
            >>> stats = scorer.get_calibration_stats()
            >>> assert 'sample_count' in stats
        """
        with self._lock:
            if not self._calibration_data:
                return {
                    'sample_count': 0,
                    'accuracy': 0.0,
                    'mean_predicted_confidence': 0.0
                }

            predictions = [pred for pred, _ in self._calibration_data]
            outcomes = [out for _, out in self._calibration_data]

            mean_predicted = sum(predictions) / len(predictions)
            actual_success_rate = sum(outcomes) / len(outcomes)

            return {
                'sample_count': len(self._calibration_data),
                'accuracy': actual_success_rate,
                'mean_predicted_confidence': mean_predicted,
                'calibration_error': abs(mean_predicted - actual_success_rate)
            }
