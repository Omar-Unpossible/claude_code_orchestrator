"""Central decision making for action routing and confidence assessment.

This module implements the DecisionEngine, which analyzes context and validation
results to determine the next action in the orchestration loop.

Actions:
    - proceed: Task complete, move to next
    - clarify: Ambiguous, request clarification
    - escalate: Confidence too low, trigger breakpoint
    - retry: Transient error, retry with modifications
    - checkpoint: Create savepoint before risky operation

The DecisionEngine uses multi-criteria decision making with configurable weights
and learns from outcomes to improve future decisions.

Example:
    >>> engine = DecisionEngine(state_manager, breakpoint_manager, config)
    >>>
    >>> context = {
    ...     'task': task,
    ...     'response': response,
    ...     'validation': validation_result,
    ...     'quality_score': 0.85
    ... }
    >>>
    >>> action = engine.decide_next_action(context)
    >>> print(f"Decision: {action.type}")
    >>> print(f"Confidence: {action.confidence}")
    >>> print(f"Explanation: {action.explanation}")
"""

import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from threading import RLock
from typing import Dict, List, Optional, Any, Tuple

from src.core.exceptions import OrchestratorException
from src.core.models import Task
from src.core.state import StateManager
from src.orchestration.breakpoint_manager import BreakpointManager


logger = logging.getLogger(__name__)


@dataclass
class Action:
    """Represents a decision action.

    Attributes:
        type: Action type (proceed, clarify, escalate, retry, checkpoint)
        confidence: Confidence in this decision (0.0-1.0)
        explanation: Human-readable explanation
        metadata: Additional action-specific data
        timestamp: When decision was made
    """
    type: str
    confidence: float
    explanation: str
    metadata: Dict[str, Any]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'type': self.type,
            'confidence': self.confidence,
            'explanation': self.explanation,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }


class DecisionEngine:
    """Central decision making engine for orchestration.

    Makes intelligent routing decisions based on confidence scores, validation
    results, quality metrics, and historical patterns. Uses weighted multi-criteria
    decision making and learns from outcomes.

    Thread-safe for concurrent access.

    Example:
        >>> engine = DecisionEngine(state_manager, breakpoint_manager)
        >>>
        >>> # Make decision
        >>> context = {
        ...     'task': task,
        ...     'response': 'def add(a, b): return a + b',
        ...     'validation_result': {'complete': True, 'valid': True},
        ...     'quality_score': 0.85,
        ...     'confidence_score': 0.90
        ... }
        >>>
        >>> action = engine.decide_next_action(context)
        >>> if action.type == 'proceed':
        ...     complete_task()
        >>> elif action.type == 'escalate':
        ...     await_human_input()
        >>>
        >>> # Learn from outcome
        >>> outcome = {'success': True, 'task_completed': True}
        >>> engine.learn_from_outcome(action.type, outcome)
    """

    # Action types
    ACTION_PROCEED = 'proceed'
    ACTION_CLARIFY = 'clarify'
    ACTION_ESCALATE = 'escalate'
    ACTION_RETRY = 'retry'
    ACTION_CHECKPOINT = 'checkpoint'

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.85
    MEDIUM_CONFIDENCE = 0.50
    LOW_CONFIDENCE = 0.30
    CRITICAL_THRESHOLD = 0.30

    # Decision weights (sum to 1.0)
    WEIGHT_CONFIDENCE = 0.35
    WEIGHT_VALIDATION = 0.25
    WEIGHT_QUALITY = 0.25
    WEIGHT_COMPLEXITY = 0.10
    WEIGHT_HISTORY = 0.05

    # Learning rate for outcome-based updates
    LEARNING_RATE = 0.1

    def __init__(
        self,
        state_manager: StateManager,
        breakpoint_manager: BreakpointManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize decision engine.

        Args:
            state_manager: StateManager instance
            breakpoint_manager: BreakpointManager instance
            config: Optional configuration dictionary
        """
        self.state_manager = state_manager
        self.breakpoint_manager = breakpoint_manager
        self.config = config or {}
        self._lock = RLock()

        # Load thresholds from config
        self._high_confidence = self.config.get('high_confidence', self.HIGH_CONFIDENCE)
        self._medium_confidence = self.config.get('medium_confidence', self.MEDIUM_CONFIDENCE)
        self._critical_threshold = self.config.get('critical_threshold', self.CRITICAL_THRESHOLD)

        # Decision weights
        self._weights = {
            'confidence': self.config.get('weight_confidence', self.WEIGHT_CONFIDENCE),
            'validation': self.config.get('weight_validation', self.WEIGHT_VALIDATION),
            'quality': self.config.get('weight_quality', self.WEIGHT_QUALITY),
            'complexity': self.config.get('weight_complexity', self.WEIGHT_COMPLEXITY),
            'history': self.config.get('weight_history', self.WEIGHT_HISTORY)
        }

        # Learning: action type -> success rate
        self._action_success_rates: Dict[str, float] = {
            self.ACTION_PROCEED: 0.9,
            self.ACTION_CLARIFY: 0.7,
            self.ACTION_ESCALATE: 0.95,
            self.ACTION_RETRY: 0.6,
            self.ACTION_CHECKPOINT: 0.85
        }

        # Decision history
        self._decision_history: List[Tuple[Action, Dict[str, Any]]] = []

        logger.info("DecisionEngine initialized")

    def decide_next_action(self, context: Dict[str, Any]) -> Action:
        """Decide next action based on context.

        Analyzes all available information and selects the most appropriate
        action using multi-criteria decision making.

        Args:
            context: Context dictionary with:
                - task: Task being processed
                - response: Agent response
                - validation_result: Validation results
                - quality_score: Quality score (0.0-1.0)
                - confidence_score: Confidence score (0.0-1.0)
                - (optional) other relevant data

        Returns:
            Action to take

        Example:
            >>> action = engine.decide_next_action({
            ...     'task': task,
            ...     'response': 'implementation code',
            ...     'validation_result': {'complete': True},
            ...     'quality_score': 0.85,
            ...     'confidence_score': 0.90
            ... })
            >>> print(action.type)  # 'proceed'
        """
        with self._lock:
            # Extract context data
            task = context.get('task')
            validation_result = context.get('validation_result', {})
            quality_score = context.get('quality_score', 0.0)
            confidence_score = context.get('confidence_score', 0.0)

            # Assess overall confidence
            overall_confidence = self.assess_confidence(
                context.get('response', ''),
                validation_result
            )

            # Check if breakpoint should be triggered
            should_breakpoint, reason = self.should_trigger_breakpoint(context)
            if should_breakpoint:
                action = Action(
                    type=self.ACTION_ESCALATE,
                    confidence=overall_confidence,
                    explanation=f"Triggering breakpoint: {reason}",
                    metadata={'breakpoint_reason': reason},
                    timestamp=datetime.now(UTC)
                )
                logger.info(f"Decision: ESCALATE - {reason}")
                self._record_decision(action, context)
                return action

            # Evaluate quality
            quality_acceptable = quality_score >= 0.7
            validation_passed = validation_result.get('complete', False) and \
                              validation_result.get('valid', False)

            # Decision logic based on confidence and quality
            if overall_confidence >= self._high_confidence and \
               validation_passed and quality_acceptable:
                # High confidence, good quality -> Proceed
                action = Action(
                    type=self.ACTION_PROCEED,
                    confidence=overall_confidence,
                    explanation=(
                        f"High confidence ({overall_confidence:.2f}), "
                        f"quality score {quality_score:.2f}, validation passed"
                    ),
                    metadata={
                        'quality_score': quality_score,
                        'validation': validation_result
                    },
                    timestamp=datetime.now(UTC)
                )

            elif self._medium_confidence <= overall_confidence < self._high_confidence:
                # Medium confidence -> Clarify
                issues = self._identify_ambiguities(context)
                action = Action(
                    type=self.ACTION_CLARIFY,
                    confidence=overall_confidence,
                    explanation=(
                        f"Medium confidence ({overall_confidence:.2f}), "
                        f"requesting clarification on {len(issues)} issues"
                    ),
                    metadata={
                        'issues': issues,
                        'quality_score': quality_score
                    },
                    timestamp=datetime.now(UTC)
                )

            elif overall_confidence < self._medium_confidence:
                # Low confidence -> Escalate
                action = Action(
                    type=self.ACTION_ESCALATE,
                    confidence=overall_confidence,
                    explanation=(
                        f"Low confidence ({overall_confidence:.2f}), "
                        "human intervention required"
                    ),
                    metadata={
                        'confidence_score': confidence_score,
                        'quality_score': quality_score
                    },
                    timestamp=datetime.now(UTC)
                )

            else:
                # Default: retry
                action = Action(
                    type=self.ACTION_RETRY,
                    confidence=overall_confidence,
                    explanation="Unclear decision, retrying with modifications",
                    metadata={'retry_count': context.get('retry_count', 0) + 1},
                    timestamp=datetime.now(UTC)
                )

            logger.info(f"Decision: {action.type.upper()} (confidence: {action.confidence:.2f})")
            self._record_decision(action, context)
            return action

    def should_trigger_breakpoint(
        self,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Determine if breakpoint should be triggered.

        Args:
            context: Context dictionary

        Returns:
            Tuple of (should_trigger, reason)

        Example:
            >>> should_trigger, reason = engine.should_trigger_breakpoint(context)
            >>> if should_trigger:
            ...     print(f"Breakpoint: {reason}")
        """
        # Use BreakpointManager to evaluate conditions
        triggered_types = self.breakpoint_manager.evaluate_breakpoint_conditions(context)

        if triggered_types:
            # Return first triggered breakpoint
            reason = triggered_types[0]
            return True, reason

        return False, ""

    def evaluate_response_quality(
        self,
        response: str,
        task: Task
    ) -> float:
        """Evaluate response quality heuristically.

        This is a lightweight quality check. Full quality validation
        happens in QualityController.

        Args:
            response: Agent response text
            task: Task being processed

        Returns:
            Quality score (0.0-1.0)

        Example:
            >>> quality = engine.evaluate_response_quality(response_text, task)
            >>> print(f"Quality: {quality:.2f}")
        """
        if not response or not response.strip():
            return 0.0

        score = 0.0

        # Check length (not too short, not empty)
        if len(response) > 50:
            score += 0.2

        # Check for code blocks (if task involves code)
        if task and 'code' in task.description.lower():
            if '```' in response or 'def ' in response or 'class ' in response:
                score += 0.3

        # Check for structure (paragraphs, sections)
        if '\n\n' in response or '#' in response:
            score += 0.2

        # Check for completeness markers
        if any(marker in response.lower() for marker in ['done', 'complete', 'implemented']):
            score += 0.15

        # Check for error markers (negative score)
        if any(error in response.lower() for error in ['error', 'failed', 'cannot', 'todo', 'fixme']):
            score -= 0.2

        return max(0.0, min(1.0, score))

    def determine_follow_up(
        self,
        response: str,
        validation_result: Dict[str, Any]
    ) -> str:
        """Determine follow-up prompt based on response and validation.

        Args:
            response: Agent response
            validation_result: Validation results

        Returns:
            Follow-up prompt string

        Example:
            >>> followup = engine.determine_follow_up(response, validation)
            >>> send_to_agent(followup)
        """
        if not validation_result.get('complete', True):
            return (
                "Your previous response appears incomplete. "
                "Please complete your response, you were cut off at: "
                f"{response[-100:]}"
            )

        issues = validation_result.get('issues', [])
        if issues:
            issue_list = '\n'.join(f"- {issue}" for issue in issues[:3])
            return (
                f"Please address the following issues:\n{issue_list}\n\n"
                "Provide an updated response."
            )

        # Generic clarification
        return (
            "Please provide more details or clarify your implementation. "
            "Ensure all requirements are addressed."
        )

    def assess_confidence(
        self,
        response: str,
        validation: Dict[str, Any]
    ) -> float:
        """Assess overall confidence in response.

        Uses multi-criteria scoring with weighted factors.

        Args:
            response: Agent response
            validation: Validation results

        Returns:
            Confidence score (0.0-1.0)

        Example:
            >>> confidence = engine.assess_confidence(response, validation)
            >>> if confidence > 0.85:
            ...     proceed()
        """
        # Base confidence from validation
        validation_confidence = 1.0 if validation.get('valid', False) else 0.0

        # Response completeness
        completeness_score = 1.0 if validation.get('complete', False) else 0.5

        # Response quality heuristic
        quality_score = self.evaluate_response_quality(response, None)

        # Historical success rate for similar decisions
        historical_score = self._action_success_rates.get(self.ACTION_PROCEED, 0.8)

        # Weighted combination
        confidence = (
            self._weights['validation'] * validation_confidence +
            self._weights['quality'] * quality_score +
            self._weights['confidence'] * completeness_score +
            self._weights['history'] * historical_score
        )

        return max(0.0, min(1.0, confidence))

    def explain_decision(
        self,
        decision: str,
        context: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation for decision.

        Args:
            decision: Decision type
            context: Context used for decision

        Returns:
            Explanation string

        Example:
            >>> explanation = engine.explain_decision('proceed', context)
            >>> print(explanation)
        """
        confidence = context.get('confidence_score', 0.0)
        quality = context.get('quality_score', 0.0)
        validation = context.get('validation_result', {})

        explanations = {
            self.ACTION_PROCEED: (
                f"Decision: PROCEED\n"
                f"- Confidence score: {confidence:.2f} (>= {self._high_confidence})\n"
                f"- Quality score: {quality:.2f} (>= 0.70)\n"
                f"- Validation: {'PASSED' if validation.get('valid') else 'FAILED'}\n"
                f"- Assessment: All criteria met, safe to proceed"
            ),
            self.ACTION_CLARIFY: (
                f"Decision: CLARIFY\n"
                f"- Confidence score: {confidence:.2f} "
                f"(between {self._medium_confidence} and {self._high_confidence})\n"
                f"- Quality score: {quality:.2f}\n"
                f"- Assessment: Ambiguous response, requesting clarification"
            ),
            self.ACTION_ESCALATE: (
                f"Decision: ESCALATE\n"
                f"- Confidence score: {confidence:.2f} (< {self._medium_confidence})\n"
                f"- Quality score: {quality:.2f}\n"
                f"- Assessment: Confidence too low, human intervention required"
            ),
            self.ACTION_RETRY: (
                f"Decision: RETRY\n"
                f"- Retry count: {context.get('retry_count', 0)}\n"
                f"- Assessment: Transient issue, retrying with modifications"
            ),
            self.ACTION_CHECKPOINT: (
                f"Decision: CHECKPOINT\n"
                f"- Assessment: Creating savepoint before risky operation"
            )
        }

        return explanations.get(decision, f"Decision: {decision}")

    def learn_from_outcome(
        self,
        decision: str,
        outcome: Dict[str, Any]
    ) -> None:
        """Update decision weights based on outcome.

        Uses simple learning to adjust success rates for action types.

        Args:
            decision: Decision type that was made
            outcome: Outcome dictionary with success/failure info

        Example:
            >>> outcome = {'success': True, 'task_completed': True}
            >>> engine.learn_from_outcome('proceed', outcome)
        """
        with self._lock:
            success = outcome.get('success', False)

            # Update success rate using exponential moving average
            current_rate = self._action_success_rates.get(decision, 0.5)
            new_rate = current_rate + self.LEARNING_RATE * (1.0 if success else 0.0 - current_rate)
            self._action_success_rates[decision] = max(0.0, min(1.0, new_rate))

            logger.debug(
                f"Learning: {decision} -> "
                f"{'success' if success else 'failure'}, "
                f"rate: {current_rate:.2f} -> {new_rate:.2f}"
            )

    def get_decision_stats(self) -> Dict[str, Any]:
        """Get decision statistics.

        Returns:
            Dictionary with decision metrics

        Example:
            >>> stats = engine.get_decision_stats()
            >>> print(f"Total decisions: {stats['total_decisions']}")
        """
        with self._lock:
            action_counts = {}
            for action, _ in self._decision_history:
                action_counts[action.type] = action_counts.get(action.type, 0) + 1

            return {
                'total_decisions': len(self._decision_history),
                'action_counts': action_counts,
                'success_rates': self._action_success_rates.copy(),
                'weights': self._weights.copy(),
                'thresholds': {
                    'high_confidence': self._high_confidence,
                    'medium_confidence': self._medium_confidence,
                    'critical_threshold': self._critical_threshold
                }
            }

    # Private helper methods

    def _identify_ambiguities(self, context: Dict[str, Any]) -> List[str]:
        """Identify ambiguous aspects requiring clarification.

        Args:
            context: Decision context

        Returns:
            List of ambiguity descriptions
        """
        issues = []
        validation = context.get('validation_result', {})

        if not validation.get('complete', True):
            issues.append("Response appears incomplete")

        if context.get('quality_score', 1.0) < 0.7:
            issues.append("Quality below acceptable threshold")

        # Check for TODO/FIXME markers
        response = context.get('response', '')
        if 'todo' in response.lower() or 'fixme' in response.lower():
            issues.append("Contains unresolved TODO/FIXME markers")

        # Check validation issues
        if 'issues' in validation:
            issues.extend(validation['issues'][:3])

        return issues if issues else ["Requires clarification"]

    def _record_decision(
        self,
        action: Action,
        context: Dict[str, Any]
    ) -> None:
        """Record decision in history.

        Args:
            action: Action that was decided
            context: Context used for decision
        """
        self._decision_history.append((action, context.copy()))

        # Keep history limited to last 1000 decisions
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-1000:]
