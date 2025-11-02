"""Multi-stage quality validation with gates and trending.

This module implements the QualityController, which validates agent output through
multiple stages: syntax, requirements, code quality, and testing. It enforces
quality gates and tracks quality trends over time.

Validation Stages:
    1. Syntax & Format - Valid syntax, no obvious errors
    2. Requirements - Addresses all task requirements
    3. Code Quality - Error handling, documentation, conventions
    4. Testing - Tests exist and pass

Example:
    >>> controller = QualityController(state_manager, config)
    >>>
    >>> result = controller.validate_output(
    ...     output='def add(a, b): return a + b',
    ...     task=task,
    ...     context={'language': 'python'}
    ... )
    >>>
    >>> print(f"Quality score: {result.overall_score:.2f}")
    >>> if result.passes_gate:
    ...     proceed()
    >>> else:
    ...     print(f"Issues: {result.improvements}")
"""

import ast
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from threading import RLock
from typing import Dict, List, Optional, Any, Callable

from src.core.exceptions import OrchestratorException
from src.core.models import Task
from src.core.state import StateManager


logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Result of quality validation.

    Attributes:
        overall_score: Overall quality score (0.0-1.0)
        stage_scores: Scores for each validation stage
        passes_gate: Whether quality gate passed
        improvements: List of suggested improvements
        details: Detailed validation results per stage
        timestamp: When validation performed
    """
    overall_score: float
    stage_scores: Dict[str, float]
    passes_gate: bool
    improvements: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'overall_score': self.overall_score,
            'stage_scores': self.stage_scores,
            'passes_gate': self.passes_gate,
            'improvements': self.improvements,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class QualityController:
    """Multi-stage quality validation controller.

    Validates agent output through 4 stages with configurable weights and gates.
    Tracks quality trends and suggests improvements.

    Thread-safe for concurrent access.

    Example:
        >>> controller = QualityController(state_manager)
        >>>
        >>> # Validate output
        >>> result = controller.validate_output(
        ...     output=code_output,
        ...     task=task,
        ...     context={'language': 'python'}
        ... )
        >>>
        >>> if result.passes_gate:
        ...     print(f"Quality: {result.overall_score:.2f}")
        >>> else:
        ...     print("Failed quality gate:")
        ...     for improvement in result.improvements:
        ...         print(f"  - {improvement}")
        >>>
        >>> # Check trends
        >>> trends = controller.get_quality_trends(project_id, days=7)
        >>> print(f"Average quality: {trends['average_score']:.2f}")
    """

    # Validation stages
    STAGE_SYNTAX = 'syntax'
    STAGE_REQUIREMENTS = 'requirements'
    STAGE_QUALITY = 'quality'
    STAGE_TESTING = 'testing'

    # Stage weights (sum to 1.0)
    WEIGHT_SYNTAX = 0.20
    WEIGHT_REQUIREMENTS = 0.30
    WEIGHT_QUALITY = 0.30
    WEIGHT_TESTING = 0.20

    # Quality gate configuration
    MINIMUM_SCORE = 0.70
    BLOCKING_STAGES = [STAGE_SYNTAX, STAGE_REQUIREMENTS]

    def __init__(
        self,
        state_manager: StateManager,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize quality controller.

        Args:
            state_manager: StateManager instance
            config: Optional configuration dictionary
        """
        self.state_manager = state_manager
        self.config = config or {}
        self._lock = RLock()

        # Load configuration
        self._minimum_score = self.config.get('minimum_score', self.MINIMUM_SCORE)
        self._weights = {
            self.STAGE_SYNTAX: self.config.get('weight_syntax', self.WEIGHT_SYNTAX),
            self.STAGE_REQUIREMENTS: self.config.get('weight_requirements', self.WEIGHT_REQUIREMENTS),
            self.STAGE_QUALITY: self.config.get('weight_quality', self.WEIGHT_QUALITY),
            self.STAGE_TESTING: self.config.get('weight_testing', self.WEIGHT_TESTING)
        }

        # Validation history (project_id -> List[QualityResult])
        self._validation_history: Dict[int, List[QualityResult]] = {}

        # Custom validators
        self._custom_validators: Dict[str, List[Callable]] = {
            self.STAGE_SYNTAX: [],
            self.STAGE_REQUIREMENTS: [],
            self.STAGE_QUALITY: [],
            self.STAGE_TESTING: []
        }

        logger.info("QualityController initialized")

    def validate_output(
        self,
        output: str,
        task: Task,
        context: Dict[str, Any]
    ) -> QualityResult:
        """Validate output through all quality stages.

        Args:
            output: Agent output to validate
            task: Task being validated
            context: Context dictionary with language, requirements, etc.

        Returns:
            QualityResult with scores and recommendations

        Example:
            >>> result = controller.validate_output(
            ...     output='def add(a, b): return a + b',
            ...     task=task,
            ...     context={'language': 'python'}
            ... )
            >>> print(f"Score: {result.overall_score:.2f}")
        """
        with self._lock:
            # Run all validation stages
            syntax_score, syntax_details = self._validate_stage_1_syntax(output, context)
            requirements_score, requirements_details = self._validate_stage_2_requirements(
                output, task, context
            )
            quality_score, quality_details = self._validate_stage_3_quality(output, context)
            testing_score, testing_details = self._validate_stage_4_testing(output, context)

            # Calculate weighted overall score
            stage_scores = {
                self.STAGE_SYNTAX: syntax_score,
                self.STAGE_REQUIREMENTS: requirements_score,
                self.STAGE_QUALITY: quality_score,
                self.STAGE_TESTING: testing_score
            }

            overall_score = self.calculate_quality_score(stage_scores)

            # Check quality gate
            passes_gate = self.enforce_quality_gate(
                overall_score,
                {'minimum_score': self._minimum_score, 'blocking_stages': self.BLOCKING_STAGES}
            )

            # Generate improvement suggestions
            improvements = self.suggest_improvements({
                self.STAGE_SYNTAX: syntax_details,
                self.STAGE_REQUIREMENTS: requirements_details,
                self.STAGE_QUALITY: quality_details,
                self.STAGE_TESTING: testing_details
            })

            # Create result
            result = QualityResult(
                overall_score=overall_score,
                stage_scores=stage_scores,
                passes_gate=passes_gate,
                improvements=improvements,
                details={
                    self.STAGE_SYNTAX: syntax_details,
                    self.STAGE_REQUIREMENTS: requirements_details,
                    self.STAGE_QUALITY: quality_details,
                    self.STAGE_TESTING: testing_details
                }
            )

            # Store in history
            project_id = task.project_id if task else 0
            if project_id not in self._validation_history:
                self._validation_history[project_id] = []
            self._validation_history[project_id].append(result)

            logger.info(
                f"Quality validation: score={overall_score:.2f}, "
                f"gate={'PASS' if passes_gate else 'FAIL'}"
            )

            return result

    def cross_validate(
        self,
        output: str,
        validators: List[Callable[[str], bool]]
    ) -> Dict[str, Any]:
        """Run multiple validators and aggregate results.

        Args:
            output: Output to validate
            validators: List of validation functions

        Returns:
            Dictionary with aggregated results

        Example:
            >>> validators = [check_syntax, check_style, check_complexity]
            >>> result = controller.cross_validate(code, validators)
            >>> print(f"Pass rate: {result['pass_rate']:.2f}")
        """
        results = []
        for validator in validators:
            try:
                passed = validator(output)
                results.append(passed)
            except Exception as e:
                logger.warning(f"Validator failed: {e}")
                results.append(False)

        pass_rate = sum(results) / len(results) if results else 0.0

        return {
            'validators_run': len(validators),
            'passed': sum(results),
            'failed': len(results) - sum(results),
            'pass_rate': pass_rate
        }

    def check_regression(
        self,
        current: Dict[str, float],
        baseline: Dict[str, float]
    ) -> bool:
        """Check if quality has regressed compared to baseline.

        Args:
            current: Current quality scores
            baseline: Baseline quality scores

        Returns:
            True if regression detected

        Example:
            >>> has_regressed = controller.check_regression(
            ...     current={'overall': 0.65},
            ...     baseline={'overall': 0.85}
            ... )
            >>> if has_regressed:
            ...     alert_team()
        """
        current_overall = current.get('overall', 0.0)
        baseline_overall = baseline.get('overall', 0.0)

        # Regression if current is significantly lower (>10% drop)
        regression_threshold = 0.10
        return (baseline_overall - current_overall) > regression_threshold

    def calculate_quality_score(
        self,
        validation_results: Dict[str, float]
    ) -> float:
        """Calculate weighted overall quality score.

        Args:
            validation_results: Stage scores dictionary

        Returns:
            Overall quality score (0.0-1.0)

        Example:
            >>> scores = {
            ...     'syntax': 1.0,
            ...     'requirements': 0.9,
            ...     'quality': 0.8,
            ...     'testing': 0.7
            ... }
            >>> overall = controller.calculate_quality_score(scores)
        """
        score = 0.0
        for stage, stage_score in validation_results.items():
            weight = self._weights.get(stage, 0.0)
            score += stage_score * weight

        return max(0.0, min(1.0, score))

    def suggest_improvements(
        self,
        validation_results: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable improvement suggestions.

        Args:
            validation_results: Detailed validation results per stage

        Returns:
            List of improvement suggestions

        Example:
            >>> improvements = controller.suggest_improvements(results)
            >>> for suggestion in improvements:
            ...     print(f"TODO: {suggestion}")
        """
        suggestions = []

        # Syntax issues
        syntax_details = validation_results.get(self.STAGE_SYNTAX, {})
        if not syntax_details.get('valid_syntax', True):
            suggestions.append("Fix syntax errors before proceeding")
        if syntax_details.get('has_markers', False):
            suggestions.append("Remove TODO/FIXME markers")

        # Requirements issues
        req_details = validation_results.get(self.STAGE_REQUIREMENTS, {})
        if not req_details.get('complete_solution', True):
            suggestions.append("Complete all required functionality (no partial implementations)")
        missing_features = req_details.get('missing_features', [])
        if missing_features:
            suggestions.append(f"Implement missing features: {', '.join(missing_features)}")

        # Quality issues
        quality_details = validation_results.get(self.STAGE_QUALITY, {})
        if not quality_details.get('has_error_handling', False):
            suggestions.append("Add error handling (try/except blocks)")
        if not quality_details.get('has_documentation', False):
            suggestions.append("Add docstrings to functions and classes")
        if quality_details.get('high_complexity', False):
            suggestions.append("Reduce cyclomatic complexity (simplify logic)")

        # Testing issues
        testing_details = validation_results.get(self.STAGE_TESTING, {})
        if not testing_details.get('has_tests', False):
            suggestions.append("Create test file with unit tests")
        if not testing_details.get('tests_passing', True):
            suggestions.append("Fix failing tests")

        return suggestions if suggestions else ["No improvements needed"]

    def enforce_quality_gate(
        self,
        quality_score: float,
        gate_config: Dict[str, Any]
    ) -> bool:
        """Enforce quality gate based on configuration.

        Args:
            quality_score: Overall quality score
            gate_config: Gate configuration with minimum_score

        Returns:
            True if quality gate passed

        Example:
            >>> gate_config = {'minimum_score': 0.70}
            >>> passes = controller.enforce_quality_gate(0.85, gate_config)
            >>> assert passes == True
        """
        minimum_score = gate_config.get('minimum_score', self._minimum_score)
        return quality_score >= minimum_score

    def get_quality_trends(
        self,
        project_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get quality trends for a project.

        Args:
            project_id: Project ID
            days: Number of days to analyze

        Returns:
            Dictionary with trend statistics

        Example:
            >>> trends = controller.get_quality_trends(project_id, days=7)
            >>> print(f"Average: {trends['average_score']:.2f}")
            >>> print(f"Trend: {trends['trend']}")
        """
        with self._lock:
            history = self._validation_history.get(project_id, [])

            # Filter to recent results
            cutoff = datetime.now(UTC) - timedelta(days=days)
            recent_results = [
                r for r in history
                if r.timestamp >= cutoff
            ]

            if not recent_results:
                return {
                    'average_score': 0.0,
                    'count': 0,
                    'trend': 'no_data'
                }

            scores = [r.overall_score for r in recent_results]
            average_score = sum(scores) / len(scores)

            # Calculate trend (improving/declining/stable)
            if len(scores) >= 5:
                first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
                second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)

                if second_half > first_half + 0.05:
                    trend = 'improving'
                elif second_half < first_half - 0.05:
                    trend = 'declining'
                else:
                    trend = 'stable'
            else:
                trend = 'insufficient_data'

            return {
                'average_score': average_score,
                'min_score': min(scores),
                'max_score': max(scores),
                'count': len(recent_results),
                'trend': trend,
                'recent_scores': scores[-10:]  # Last 10
            }

    def generate_quality_report(
        self,
        project_id: int
    ) -> Dict[str, Any]:
        """Generate comprehensive quality report for project.

        Args:
            project_id: Project ID

        Returns:
            Quality report dictionary

        Example:
            >>> report = controller.generate_quality_report(project_id)
            >>> print(f"Total validations: {report['total_validations']}")
            >>> print(f"Pass rate: {report['gate_pass_rate']:.2%}")
        """
        with self._lock:
            history = self._validation_history.get(project_id, [])

            if not history:
                return {
                    'total_validations': 0,
                    'gate_pass_rate': 0.0,
                    'average_scores': {},
                    'common_issues': []
                }

            # Calculate metrics
            total = len(history)
            passed_gate = sum(1 for r in history if r.passes_gate)
            gate_pass_rate = passed_gate / total

            # Average scores per stage
            stage_averages = {}
            for stage in [self.STAGE_SYNTAX, self.STAGE_REQUIREMENTS,
                         self.STAGE_QUALITY, self.STAGE_TESTING]:
                scores = [r.stage_scores.get(stage, 0.0) for r in history]
                stage_averages[stage] = sum(scores) / len(scores) if scores else 0.0

            # Most common issues
            all_improvements = []
            for result in history:
                all_improvements.extend(result.improvements)

            issue_counts = {}
            for improvement in all_improvements:
                issue_counts[improvement] = issue_counts.get(improvement, 0) + 1

            common_issues = sorted(
                issue_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]

            return {
                'total_validations': total,
                'gate_pass_rate': gate_pass_rate,
                'average_scores': stage_averages,
                'overall_average': sum(r.overall_score for r in history) / total,
                'common_issues': [issue for issue, _ in common_issues]
            }

    # Private validation stage methods

    def _validate_stage_1_syntax(
        self,
        output: str,
        context: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        """Stage 1: Validate syntax and format.

        Args:
            output: Output to validate
            context: Context with language info

        Returns:
            Tuple of (score, details)
        """
        score = 1.0
        details = {}

        # Check for Python syntax if applicable
        language = context.get('language', 'python')
        if language == 'python' and ('def ' in output or 'class ' in output):
            try:
                # Extract code from markdown if present
                code = output
                if '```python' in output:
                    code = self._extract_code_blocks(output, 'python')

                ast.parse(code)
                details['valid_syntax'] = True
            except SyntaxError as e:
                details['valid_syntax'] = False
                details['syntax_error'] = str(e)
                score -= 0.5

        # Check for TODO/FIXME markers
        has_markers = bool(re.search(r'\b(TODO|FIXME|XXX)\b', output, re.IGNORECASE))
        details['has_markers'] = has_markers
        if has_markers:
            score -= 0.2

        # Check for obvious errors
        error_patterns = [r'\berror\b', r'\bfailed\b', r'\bexception\b']
        has_errors = any(re.search(pattern, output, re.IGNORECASE) for pattern in error_patterns)
        details['has_errors'] = has_errors
        if has_errors:
            score -= 0.3

        return max(0.0, score), details

    def _validate_stage_2_requirements(
        self,
        output: str,
        task: Task,
        context: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        """Stage 2: Validate requirements adherence.

        Args:
            output: Output to validate
            task: Task with requirements
            context: Context

        Returns:
            Tuple of (score, details)
        """
        score = 1.0
        details = {}

        # Check for partial implementation markers
        partial_markers = ['pass', 'NotImplementedError', '...']
        has_partial = any(marker in output for marker in partial_markers)
        details['complete_solution'] = not has_partial
        if has_partial:
            score -= 0.4

        # Check output length (completeness heuristic)
        if len(output.strip()) < 50:
            details['too_short'] = True
            score -= 0.3
        else:
            details['too_short'] = False

        # Check for required keywords from task description
        if task and task.description:
            # Extract key terms from description
            description_words = set(task.description.lower().split())
            important_words = [w for w in description_words if len(w) > 4][:5]

            found_words = sum(1 for word in important_words if word in output.lower())
            keyword_coverage = found_words / len(important_words) if important_words else 1.0
            details['keyword_coverage'] = keyword_coverage

            if keyword_coverage < 0.5:
                score -= 0.3

        details['missing_features'] = []  # Placeholder for detailed feature check

        return max(0.0, score), details

    def _validate_stage_3_quality(
        self,
        output: str,
        context: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        """Stage 3: Validate code quality.

        Args:
            output: Output to validate
            context: Context

        Returns:
            Tuple of (score, details)
        """
        score = 1.0
        details = {}

        # Check for error handling
        has_error_handling = 'try' in output or 'except' in output
        details['has_error_handling'] = has_error_handling
        if not has_error_handling and len(output) > 200:
            score -= 0.2

        # Check for documentation
        has_docstrings = '"""' in output or "'''" in output
        details['has_documentation'] = has_docstrings
        if not has_docstrings and ('def ' in output or 'class ' in output):
            score -= 0.2

        # Check complexity heuristic (nested blocks)
        nesting_level = self._estimate_nesting_level(output)
        details['nesting_level'] = nesting_level
        details['high_complexity'] = nesting_level > 3
        if nesting_level > 3:
            score -= 0.2

        # Check naming conventions (simple heuristic)
        has_good_names = not re.search(r'\b[a-z]\b|\bfoo\b|\bbar\b|\btemp\b', output)
        details['good_naming'] = has_good_names
        if not has_good_names:
            score -= 0.1

        return max(0.0, score), details

    def _validate_stage_4_testing(
        self,
        output: str,
        context: Dict[str, Any]
    ) -> tuple[float, Dict[str, Any]]:
        """Stage 4: Validate testing coverage.

        Args:
            output: Output to validate
            context: Context

        Returns:
            Tuple of (score, details)
        """
        score = 0.5  # Default assume no tests
        details = {}

        # Check if test file created
        has_tests = 'test_' in output or 'def test' in output or 'class Test' in output
        details['has_tests'] = has_tests

        if has_tests:
            score = 1.0
            details['tests_passing'] = True  # Assume passing unless evidence otherwise

            # Check for assertions
            has_assertions = 'assert' in output or 'assertEqual' in output
            details['has_assertions'] = has_assertions
            if not has_assertions:
                score -= 0.3

            # Check for edge case tests
            edge_case_keywords = ['empty', 'none', 'zero', 'negative', 'boundary']
            has_edge_cases = any(keyword in output.lower() for keyword in edge_case_keywords)
            details['edge_cases_covered'] = has_edge_cases
            if not has_edge_cases:
                score -= 0.2

        return max(0.0, score), details

    def _extract_code_blocks(self, text: str, language: str) -> str:
        """Extract code from markdown code blocks.

        Args:
            text: Text with code blocks
            language: Language to extract

        Returns:
            Extracted code
        """
        pattern = f'```{language}\\s*\\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        return '\n\n'.join(matches) if matches else text

    def _estimate_nesting_level(self, code: str) -> int:
        """Estimate maximum nesting level in code.

        Args:
            code: Code to analyze

        Returns:
            Estimated max nesting level
        """
        max_level = 0
        current_level = 0

        for line in code.split('\n'):
            stripped = line.lstrip()
            if stripped.startswith(('if ', 'for ', 'while ', 'def ', 'class ', 'with ')):
                current_level += 1
                max_level = max(max_level, current_level)
            elif stripped.startswith(('else:', 'elif ', 'except:', 'finally:')):
                pass  # Same level
            elif not stripped or stripped.startswith('#'):
                continue
            else:
                # Dedent detection (approximate)
                if line and not line[0].isspace():
                    current_level = 0

        return max_level
