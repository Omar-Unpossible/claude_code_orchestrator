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
from src.llm.structured_response_parser import StructuredResponseParser
from src.llm.prompt_rule_engine import PromptRuleEngine


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
        rule_violations: List of rule violation dictionaries (from structured mode)
        metadata: Additional metadata (e.g., structured_mode, schema_valid)
    """
    overall_score: float
    stage_scores: Dict[str, float]
    passes_gate: bool
    improvements: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    rule_violations: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

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
            'timestamp': self.timestamp.isoformat(),
            'rule_violations': self.rule_violations,
            'metadata': self.metadata
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
        config: Optional[Dict[str, Any]] = None,
        git_manager: Optional[Any] = None
    ):
        """Initialize quality controller.

        Args:
            state_manager: StateManager instance
            config: Optional configuration dictionary
            git_manager: Optional GitManager instance for M9 git context
        """
        self.state_manager = state_manager
        self.config = config or {}
        self.git_manager = git_manager
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

        # Structured response parsing (TASK_5.1)
        self._response_parser: Optional[StructuredResponseParser] = None
        self._rule_engine: Optional[PromptRuleEngine] = None

        # Initialize structured validation if enabled
        if self.config.get('structured_mode', False):
            self._initialize_structured_validation()

        logger.info("QualityController initialized")

    def _initialize_structured_validation(self) -> None:
        """Initialize StructuredResponseParser and PromptRuleEngine.

        This method is called during __init__ if structured_mode is enabled in config.
        It initializes the response parser and rule engine for structured validation.

        Example:
            >>> config = {'structured_mode': True}
            >>> controller = QualityController(state_manager, config)
            >>> assert controller._response_parser is not None
        """
        try:
            # Get schema file path from config
            schemas_file = self.config.get(
                'response_schemas_file',
                'config/response_schemas.yaml'
            )

            # Initialize response parser
            self._response_parser = StructuredResponseParser(schemas_file)
            self._response_parser.load_schemas()

            # Get rules file path from config
            rules_file = self.config.get(
                'prompt_rules_file',
                'config/prompt_rules.yaml'
            )

            # Initialize rule engine
            self._rule_engine = PromptRuleEngine(
                rules_file_path=rules_file,
                state_manager=self.state_manager
            )
            self._rule_engine.load_rules_from_yaml()

            logger.info(
                f"Structured validation initialized: "
                f"{len(self._response_parser.schemas)} schemas, "
                f"{len(self._rule_engine.get_all_rules())} rules"
            )

        except Exception as e:
            logger.warning(
                f"Failed to initialize structured validation: {e}. "
                f"Falling back to unstructured validation."
            )
            self._response_parser = None
            self._rule_engine = None

    def _gather_m9_context(self, task: Task, output: str) -> Dict[str, Any]:
        """Gather M9-specific context for validation (TASK_1.2.3).

        Collects context from M9 features: dependencies, git tracking, retry logic.

        Args:
            task: Task being validated
            output: Agent output

        Returns:
            Dictionary with M9 context (dependencies, git, retry)
        """
        context = {}

        if not task:
            return context

        task_id = task.id

        # Dependency context (M9)
        if hasattr(self.state_manager, 'dependency_resolver'):
            try:
                resolver = self.state_manager.dependency_resolver

                # Get detailed dependency info
                dep_ids = resolver.get_dependencies(task_id)
                if dep_ids:
                    deps_detailed = []
                    for dep_id in dep_ids:
                        dep_task = self.state_manager.get_task(dep_id)
                        if dep_task:
                            deps_detailed.append({
                                'id': dep_id,
                                'title': dep_task.title,
                                'status': dep_task.status,
                                'completion_percentage': 100 if dep_task.status == 'completed' else 0
                            })
                    context['task_dependencies_detailed'] = deps_detailed

                # Check dependency impact
                affected = resolver.get_dependents(task_id)
                if affected:
                    context['dependency_impact'] = {
                        'affected_tasks': affected,
                        'breaking_changes': []  # Could analyze for breaking changes
                    }
            except Exception as e:
                logger.warning(f"Failed to gather dependency context: {e}")

        # Git context (M9)
        if self.git_manager:
            try:
                # Get recent commits
                if hasattr(self.git_manager, 'get_recent_commits'):
                    commits = self.git_manager.get_recent_commits(limit=3)
                    if commits:
                        context['git_context'] = {
                            'recent_commits': commits,
                            'current_branch': getattr(self.git_manager, 'get_current_branch', lambda: None)()
                        }

                # Get file changes for this task
                if hasattr(self.git_manager, 'get_changes_for_task'):
                    file_changes = self.git_manager.get_changes_for_task(task_id)
                    if file_changes:
                        context['file_changes'] = file_changes

            except Exception as e:
                logger.warning(f"Failed to gather git context: {e}")

        # Retry context (M9)
        if hasattr(self.state_manager, 'retry_manager'):
            try:
                retry_manager = self.state_manager.retry_manager
                if hasattr(retry_manager, 'get_retry_info'):
                    retry_info = retry_manager.get_retry_info(task_id)
                    if retry_info and retry_info.get('attempt_number', 0) > 1:
                        context['retry_context'] = {
                            'attempt_number': retry_info['attempt_number'],
                            'max_attempts': retry_info.get('max_attempts', 3),
                            'failure_reason': retry_info.get('last_failure', 'Unknown'),
                            'improvements': retry_info.get('improvements', []),
                            'previous_errors': retry_info.get('previous_errors', [])
                        }
            except Exception as e:
                logger.warning(f"Failed to gather retry context: {e}")

        return context

    def validate_output(
        self,
        output: str,
        task: Task,
        context: Dict[str, Any]
    ) -> QualityResult:
        """Validate output through all quality stages.

        Supports both structured and unstructured validation:
        - Structured mode: Parses response with StructuredResponseParser,
          validates against schema, checks rule compliance
        - Unstructured mode: Falls back to traditional validation stages

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
            # Gather M9 context and merge with provided context (TASK_1.2.4)
            m9_context = self._gather_m9_context(task, output)
            enhanced_context = {**context, **m9_context}

            # Determine response type from context
            response_type = enhanced_context.get('response_type', 'task_execution')

            # Use structured parsing if available
            if self._response_parser:
                logger.debug(f"Using structured validation for {response_type} response")
                return self._validate_structured_response(
                    output=output,
                    task=task,
                    context=enhanced_context,
                    response_type=response_type
                )
            else:
                logger.debug("Using unstructured validation")
                return self._validate_unstructured_response(
                    output=output,
                    task=task,
                    context=enhanced_context
                )

    def _validate_structured_response(
        self,
        output: str,
        task: Task,
        context: Dict[str, Any],
        response_type: str
    ) -> QualityResult:
        """Validate output using structured response parsing.

        Process:
        1. Parse response with StructuredResponseParser
        2. Validate response against expected schema
        3. Check rule compliance
        4. Calculate quality score including rule compliance
        5. Log rule violations to StateManager

        Args:
            output: Agent output to validate
            task: Task being validated
            context: Enhanced context dictionary
            response_type: Expected response type (e.g., 'task_execution')

        Returns:
            QualityResult with structured validation results
        """
        # Parse structured response
        parsed_response = self._parse_structured_response(
            agent_response=output,
            response_type=response_type,
            context=context
        )

        # Extract metadata
        metadata = parsed_response.get('metadata', {})
        content = parsed_response.get('content', '')
        is_valid = parsed_response['is_valid']
        validation_errors = parsed_response.get('validation_errors', [])
        schema_errors = parsed_response.get('schema_errors', [])

        # Check rule violations if rule engine available
        rule_violations = []
        if self._rule_engine and is_valid:
            rule_violations = self._check_rule_violations(
                task=task,
                metadata=metadata,
                content=content,
                context=context
            )

            # Log violations to StateManager
            if rule_violations and task:
                self._log_rule_violations(task.id, rule_violations)

        # Calculate quality score
        quality_score = self._calculate_structured_quality_score(
            parsed_response=parsed_response,
            rule_violations=rule_violations,
            context=context
        )

        # Check quality gate
        passes_gate = self.enforce_quality_gate(
            quality_score,
            {'minimum_score': self._minimum_score}
        )

        # Generate improvements from validation errors and rule violations
        improvements = []
        improvements.extend(validation_errors)
        improvements.extend(schema_errors)
        for violation in rule_violations:
            improvements.append(
                f"Rule violation ({violation.get('severity', 'medium')}): "
                f"{violation.get('message', 'Unknown')}"
            )

        if not improvements:
            improvements = ["No improvements needed"]

        # Create result
        result = QualityResult(
            overall_score=quality_score,
            stage_scores={
                'schema_validation': 1.0 if is_valid else 0.0,
                'rule_compliance': self._calculate_rule_compliance_score(rule_violations)
            },
            passes_gate=passes_gate,
            improvements=improvements,
            rule_violations=rule_violations,
            metadata={
                'structured_mode': True,
                'response_metadata': metadata,
                'schema_valid': is_valid,
                'response_type': response_type
            },
            details={
                'parsed_response': parsed_response,
                'rule_violations': rule_violations
            }
        )

        # Store in history
        project_id = task.project_id if task else 0
        if project_id not in self._validation_history:
            self._validation_history[project_id] = []
        self._validation_history[project_id].append(result)

        logger.info(
            f"Structured validation: score={quality_score:.2f}, "
            f"gate={'PASS' if passes_gate else 'FAIL'}, "
            f"violations={len(rule_violations)}"
        )

        return result

    def _validate_unstructured_response(
        self,
        output: str,
        task: Task,
        context: Dict[str, Any]
    ) -> QualityResult:
        """Validate output using traditional unstructured validation.

        Falls back to the original validation logic for backward compatibility.

        Args:
            output: Agent output to validate
            task: Task being validated
            context: Enhanced context dictionary

        Returns:
            QualityResult with traditional validation results
        """
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
            },
            metadata={'structured_mode': False}
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

    # Private helper methods for structured validation (TASK_5.1)

    def _parse_structured_response(
        self,
        agent_response: str,
        response_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Parse agent response using StructuredResponseParser.

        Args:
            agent_response: Raw response from agent
            response_type: Expected type (task_execution, validation, etc.)
            context: Optional validation context

        Returns:
            Parsed response dict with:
            - is_valid: bool
            - metadata: Dict[str, Any]
            - content: str
            - validation_errors: List[str]
            - schema_errors: List[str]

        Example:
            >>> parsed = controller._parse_structured_response(
            ...     agent_response='<METADATA>{"status": "completed"}</METADATA>',
            ...     response_type='task_execution'
            ... )
            >>> assert parsed['is_valid'] == True
        """
        try:
            parsed = self._response_parser.parse_response(
                response=agent_response,
                expected_type=response_type
            )

            logger.debug(
                f"Parsed {response_type} response: "
                f"valid={parsed['is_valid']}, "
                f"errors={len(parsed.get('validation_errors', []))}"
            )

            return parsed

        except Exception as e:
            logger.error(f"Failed to parse structured response: {e}")
            return {
                'is_valid': False,
                'metadata': {},
                'content': agent_response,
                'validation_errors': [f"Parsing failed: {str(e)}"],
                'schema_errors': []
            }

    def _check_rule_violations(
        self,
        task: Task,
        metadata: Dict[str, Any],
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Check for rule violations in agent response.

        Uses PromptRuleEngine to validate response against applicable rules.

        Args:
            task: Task being validated
            metadata: Parsed metadata from response
            content: Natural language content from response
            context: Optional validation context

        Returns:
            List of violation dicts with:
            - rule_id: str
            - rule_name: str
            - severity: str
            - message: str
            - location: Dict (file, line, etc.)
            - suggestion: str

        Example:
            >>> violations = controller._check_rule_violations(
            ...     task=task,
            ...     metadata={'status': 'completed'},
            ...     content='Implementation complete'
            ... )
        """
        violations = []

        try:
            # Get applicable rules for this response type
            response_type = metadata.get('response_type', 'task_execution')

            # Get rules for relevant domains
            domains = self._get_domains_from_context(context)

            applicable_rules = []
            for domain in domains:
                domain_rules = self._rule_engine.get_rules_for_domain(domain)
                applicable_rules.extend(domain_rules)

            # Validate response against rules
            if applicable_rules:
                # Prepare response dict for validation
                response_dict = {
                    'metadata': metadata,
                    'content': content
                }

                # Validate
                validation_result = self._rule_engine.validate_response_against_rules(
                    response=response_dict,
                    applicable_rules=applicable_rules,
                    context={
                        'task_id': task.id if task else None,
                        **context
                    }
                )

                # Extract violations
                violations = validation_result.violations

            logger.debug(f"Checked {len(applicable_rules)} rules, found {len(violations)} violations")

        except Exception as e:
            logger.error(f"Failed to check rule violations: {e}")

        return violations

    def _log_rule_violations(
        self,
        task_id: int,
        violations: List[Dict[str, Any]]
    ) -> None:
        """Log rule violations to StateManager.

        Args:
            task_id: Task ID
            violations: List of violation dictionaries

        Example:
            >>> controller._log_rule_violations(
            ...     task_id=123,
            ...     violations=[{'rule_id': 'CODE_001', ...}]
            ... )
        """
        if not violations:
            return

        try:
            for violation in violations:
                # Log to StateManager
                self.state_manager.log_rule_violation(
                    task_id=task_id,
                    rule_data={
                        'rule_id': violation.get('rule_id', 'unknown'),
                        'rule_name': violation.get('rule_name', 'Unknown'),
                        'rule_domain': violation.get('domain', 'unknown'),
                        'violation_details': {
                            'message': violation.get('message', ''),
                            'location': violation.get('location', {}),
                            'suggestion': violation.get('suggestion', '')
                        },
                        'severity': violation.get('severity', 'medium')
                    }
                )

            logger.info(f"Logged {len(violations)} rule violations for task {task_id}")

        except Exception as e:
            logger.error(f"Failed to log rule violations: {e}")

    def _calculate_structured_quality_score(
        self,
        parsed_response: Dict[str, Any],
        rule_violations: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate quality score for structured response.

        Scoring factors:
        - Schema compliance: 30 points
        - Completeness: 30 points
        - Rule compliance: 40 points

        Args:
            parsed_response: Parsed response from StructuredResponseParser
            rule_violations: List of rule violation dicts
            context: Optional validation context

        Returns:
            Quality score 0.0-1.0

        Example:
            >>> score = controller._calculate_structured_quality_score(
            ...     parsed_response={'is_valid': True, ...},
            ...     rule_violations=[]
            ... )
            >>> assert 0.0 <= score <= 1.0
        """
        score = 0.0

        # Schema compliance (30 points)
        if parsed_response['is_valid']:
            score += 0.30

        # Completeness (30 points)
        metadata = parsed_response.get('metadata', {})
        if metadata:
            # Get required fields for response type
            response_type = parsed_response.get('schema_type', 'task_execution')
            required_fields = self._get_required_fields(response_type)

            if required_fields:
                present_fields = sum(1 for field in required_fields if field in metadata)
                completeness = present_fields / len(required_fields)
                score += completeness * 0.30
            else:
                # No required fields defined, assume complete
                score += 0.30
        else:
            # No metadata, cannot assess completeness
            pass

        # Rule compliance (40 points)
        if rule_violations:
            # Deduct points based on severity
            deductions = 0
            for violation in rule_violations:
                severity = violation.get('severity', 'medium')
                if severity == 'critical':
                    deductions += 0.10
                elif severity == 'high':
                    deductions += 0.05
                elif severity == 'medium':
                    deductions += 0.02
                else:  # low
                    deductions += 0.01

            rule_score = max(0.0, 0.40 - deductions)
            score += rule_score
        else:
            score += 0.40

        return min(1.0, max(0.0, score))

    def _calculate_rule_compliance_score(
        self,
        rule_violations: List[Dict[str, Any]]
    ) -> float:
        """Calculate rule compliance score from violations.

        Args:
            rule_violations: List of violation dictionaries

        Returns:
            Compliance score 0.0-1.0

        Example:
            >>> score = controller._calculate_rule_compliance_score([])
            >>> assert score == 1.0
        """
        if not rule_violations:
            return 1.0

        # Deduct based on severity
        deductions = 0.0
        for violation in rule_violations:
            severity = violation.get('severity', 'medium')
            if severity == 'critical':
                deductions += 0.25
            elif severity == 'high':
                deductions += 0.15
            elif severity == 'medium':
                deductions += 0.05
            else:  # low
                deductions += 0.025

        return max(0.0, 1.0 - deductions)

    def _get_required_fields(self, response_type: str) -> List[str]:
        """Get required fields for a response type.

        Args:
            response_type: Response type (e.g., 'task_execution')

        Returns:
            List of required field names

        Example:
            >>> fields = controller._get_required_fields('task_execution')
            >>> assert 'status' in fields
        """
        # Map response types to required fields
        # This should match the schemas in response_schemas.yaml
        required_fields_map = {
            'task_execution': ['status', 'files_modified', 'confidence'],
            'validation': ['is_valid', 'errors', 'warnings'],
            'error_analysis': ['error_type', 'root_cause', 'suggested_fix'],
            'decision': ['decision', 'reasoning', 'confidence'],
            'planning': ['tasks', 'dependencies', 'estimated_duration']
        }

        return required_fields_map.get(response_type, [])

    def _get_domains_from_context(
        self,
        context: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Get applicable rule domains from context.

        Args:
            context: Validation context

        Returns:
            List of domain names

        Example:
            >>> domains = controller._get_domains_from_context(
            ...     {'language': 'python', 'task_type': 'implementation'}
            ... )
            >>> assert 'code_generation' in domains
        """
        if not context:
            return ['code_generation']

        # Default domains
        domains = ['code_generation']

        # Add testing domain if tests are involved
        if context.get('requires_tests', False):
            domains.append('testing')

        # Add security domain if security-related
        if context.get('security_sensitive', False):
            domains.append('security')

        # Add documentation domain if docs required
        if context.get('requires_documentation', False):
            domains.append('documentation')

        return domains

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
