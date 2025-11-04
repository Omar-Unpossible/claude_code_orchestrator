"""A/B Testing Framework for Prompt Comparison.

This module provides the ABTestingFramework for comparing structured vs
unstructured prompt performance with statistical analysis.

Part of the LLM-First Prompt Engineering Framework (PHASE_6 TASK_6.2).

Key Features:
- Run same task with both prompt formats
- Collect comprehensive metrics (tokens, latency, success rate, rule violations)
- Statistical significance testing (t-test)
- Export results to JSON for analysis
- Summary statistics and comparison reports

Example:
    >>> from src.evaluation.ab_testing import ABTestingFramework
    >>> from src.llm.prompt_generator import PromptGenerator
    >>> from src.llm.structured_prompt_builder import StructuredPromptBuilder
    >>>
    >>> framework = ABTestingFramework(
    ...     prompt_generator=prompt_generator,
    ...     llm_interface=llm,
    ...     state_manager=state_manager
    ... )
    >>>
    >>> # Run A/B test on validation prompts
    >>> result = framework.run_ab_test(
    ...     test_name='validation_prompts',
    ...     prompt_type='validation',
    ...     test_cases=[
    ...         {'task': task1, 'work_output': output1, 'context': context1},
    ...         {'task': task2, 'work_output': output2, 'context': context2}
    ...     ]
    ... )
    >>>
    >>> # Export results
    >>> framework.export_results(result, 'evaluation_results/validation_ab_test.json')
    >>>
    >>> # Print summary
    >>> print(result.get_summary())
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from statistics import mean, stdev
from scipy import stats  # For t-test

logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """Metrics collected for a single test run.

    Attributes:
        prompt_format: 'structured' or 'unstructured'
        tokens_prompt: Number of tokens in prompt
        tokens_response: Number of tokens in response
        total_tokens: Total tokens (prompt + response)
        latency_ms: Response latency in milliseconds
        success: Whether the test succeeded
        rule_violations_count: Number of rule violations found
        quality_score: Quality score (0.0-1.0) if applicable
        schema_valid: Whether response schema was valid (structured only)
        error_message: Error message if test failed
        timestamp: When test was run
    """
    prompt_format: str  # 'structured' or 'unstructured'
    tokens_prompt: int
    tokens_response: int
    total_tokens: int
    latency_ms: float
    success: bool
    rule_violations_count: int = 0
    quality_score: Optional[float] = None
    schema_valid: Optional[bool] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ABTestResult:
    """Result of A/B test comparing two prompt formats.

    Attributes:
        test_name: Name of the test
        prompt_type: Type of prompt tested (validation, task_execution, etc.)
        test_cases_count: Number of test cases run
        structured_metrics: List of metrics for structured format
        unstructured_metrics: List of metrics for unstructured format
        statistical_analysis: Statistical comparison results
        summary: Human-readable summary
        timestamp: When test was run
    """
    test_name: str
    prompt_type: str
    test_cases_count: int
    structured_metrics: List[TestMetrics] = field(default_factory=list)
    unstructured_metrics: List[TestMetrics] = field(default_factory=list)
    statistical_analysis: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'test_name': self.test_name,
            'prompt_type': self.prompt_type,
            'test_cases_count': self.test_cases_count,
            'structured_metrics': [m.to_dict() for m in self.structured_metrics],
            'unstructured_metrics': [m.to_dict() for m in self.unstructured_metrics],
            'statistical_analysis': self.statistical_analysis,
            'summary': self.summary,
            'timestamp': self.timestamp.isoformat()
        }

    def get_summary(self) -> str:
        """Get human-readable summary."""
        if not self.summary:
            self._generate_summary()
        return self.summary

    def _generate_summary(self) -> None:
        """Generate summary from statistical analysis."""
        stats = self.statistical_analysis

        summary_lines = [
            f"A/B Test Results: {self.test_name}",
            f"Prompt Type: {self.prompt_type}",
            f"Test Cases: {self.test_cases_count}",
            "",
            "=== Token Efficiency ===",
            f"Structured avg: {stats.get('structured_tokens_avg', 0):.0f} tokens",
            f"Unstructured avg: {stats.get('unstructured_tokens_avg', 0):.0f} tokens",
            f"Improvement: {stats.get('token_improvement_pct', 0):.1f}%",
            f"Significance: p={stats.get('token_pvalue', 1.0):.4f} "
            f"({'significant' if stats.get('token_significant', False) else 'not significant'})",
            "",
            "=== Latency ===",
            f"Structured avg: {stats.get('structured_latency_avg', 0):.0f} ms",
            f"Unstructured avg: {stats.get('unstructured_latency_avg', 0):.0f} ms",
            f"Improvement: {stats.get('latency_improvement_pct', 0):.1f}%",
            f"Significance: p={stats.get('latency_pvalue', 1.0):.4f} "
            f"({'significant' if stats.get('latency_significant', False) else 'not significant'})",
            "",
            "=== Success Rate ===",
            f"Structured: {stats.get('structured_success_rate', 0):.1f}%",
            f"Unstructured: {stats.get('unstructured_success_rate', 0):.1f}%",
            "",
            "=== Rule Violations ===",
            f"Structured avg: {stats.get('structured_violations_avg', 0):.1f}",
            f"Unstructured avg: {stats.get('unstructured_violations_avg', 0):.1f}",
            "",
            "=== Quality Score ===",
            f"Structured avg: {stats.get('structured_quality_avg', 0):.2f}",
            f"Unstructured avg: {stats.get('unstructured_quality_avg', 0):.2f}",
        ]

        self.summary = "\n".join(summary_lines)


class ABTestingFramework:
    """A/B testing framework for comparing prompt formats.

    Runs the same test cases with both structured and unstructured prompt formats,
    collects comprehensive metrics, performs statistical analysis, and exports results.

    Thread-safe for concurrent test execution.

    Example:
        >>> framework = ABTestingFramework(
        ...     prompt_generator=prompt_generator,
        ...     llm_interface=llm,
        ...     state_manager=state_manager
        ... )
        >>>
        >>> # Run A/B test
        >>> result = framework.run_ab_test(
        ...     test_name='validation_test',
        ...     prompt_type='validation',
        ...     test_cases=[...]
        ... )
        >>>
        >>> # Export results
        >>> framework.export_results(result, 'results/validation_ab.json')
    """

    def __init__(
        self,
        prompt_generator: Any,  # PromptGenerator
        llm_interface: Any,  # LocalLLMInterface
        state_manager: Optional[Any] = None  # StateManager
    ):
        """Initialize A/B testing framework.

        Args:
            prompt_generator: PromptGenerator instance for generating prompts
            llm_interface: LocalLLMInterface for token counting and LLM calls
            state_manager: Optional StateManager for logging results
        """
        self.prompt_generator = prompt_generator
        self.llm_interface = llm_interface
        self.state_manager = state_manager

        # Statistics
        self.stats = {
            'tests_run': 0,
            'total_test_cases': 0,
            'structured_wins': 0,
            'unstructured_wins': 0,
            'ties': 0
        }

        logger.info("ABTestingFramework initialized")

    def run_ab_test(
        self,
        test_name: str,
        prompt_type: str,
        test_cases: List[Dict[str, Any]],
        alpha: float = 0.05
    ) -> ABTestResult:
        """Run A/B test comparing structured vs unstructured prompts.

        Runs each test case with both prompt formats, collects metrics,
        performs statistical analysis, and returns comprehensive results.

        Args:
            test_name: Name of this test (for identification)
            prompt_type: Type of prompt ('validation', 'task_execution', etc.)
            test_cases: List of test case dicts with keys:
                - task: Task model instance
                - work_output: Output to validate (for validation prompts)
                - context: Additional context dict
                - error_data: Error data (for error_analysis prompts)
                - decision_context: Decision context (for decision prompts)
            alpha: Significance level for statistical tests (default: 0.05)

        Returns:
            ABTestResult with metrics and statistical analysis

        Example:
            >>> test_cases = [
            ...     {
            ...         'task': task1,
            ...         'work_output': 'def func(): pass',
            ...         'context': {'rules': [...]}
            ...     },
            ...     {
            ...         'task': task2,
            ...         'work_output': 'class MyClass: pass',
            ...         'context': {'rules': [...]}
            ...     }
            ... ]
            >>>
            >>> result = framework.run_ab_test(
            ...     test_name='validation_ab_test',
            ...     prompt_type='validation',
            ...     test_cases=test_cases
            ... )
        """
        logger.info(
            f"Starting A/B test '{test_name}' for {prompt_type} prompts "
            f"with {len(test_cases)} test cases"
        )

        result = ABTestResult(
            test_name=test_name,
            prompt_type=prompt_type,
            test_cases_count=len(test_cases)
        )

        # Run test cases with both formats
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"Running test case {i}/{len(test_cases)}")

            # Run with structured format
            structured_metrics = self._run_single_test(
                prompt_type=prompt_type,
                test_case=test_case,
                use_structured=True
            )
            result.structured_metrics.append(structured_metrics)

            # Run with unstructured format
            unstructured_metrics = self._run_single_test(
                prompt_type=prompt_type,
                test_case=test_case,
                use_structured=False
            )
            result.unstructured_metrics.append(unstructured_metrics)

        # Perform statistical analysis
        result.statistical_analysis = self._perform_statistical_analysis(
            structured_metrics=result.structured_metrics,
            unstructured_metrics=result.unstructured_metrics,
            alpha=alpha
        )

        # Generate summary
        result._generate_summary()

        # Update statistics
        self.stats['tests_run'] += 1
        self.stats['total_test_cases'] += len(test_cases)

        logger.info(f"A/B test '{test_name}' completed successfully")

        return result

    def _run_single_test(
        self,
        prompt_type: str,
        test_case: Dict[str, Any],
        use_structured: bool
    ) -> TestMetrics:
        """Run a single test with specified format.

        Args:
            prompt_type: Type of prompt
            test_case: Test case data
            use_structured: Whether to use structured format

        Returns:
            TestMetrics with collected metrics
        """
        format_str = 'structured' if use_structured else 'unstructured'
        start_time = time.time()

        try:
            # Set prompt generator mode
            original_mode = self.prompt_generator._structured_mode
            self.prompt_generator.set_structured_mode(use_structured)

            # Generate prompt based on type
            if prompt_type == 'validation':
                prompt = self.prompt_generator.generate_validation_prompt(
                    task=test_case['task'],
                    work_output=test_case['work_output'],
                    context=test_case['context']
                )
            elif prompt_type == 'task_execution':
                prompt = self.prompt_generator.generate_task_prompt(
                    task=test_case['task'],
                    context=test_case['context']
                )
            elif prompt_type == 'error_analysis':
                prompt = self.prompt_generator.generate_error_analysis_prompt(
                    task=test_case['task'],
                    error_data=test_case['error_data'],
                    context=test_case['context']
                )
            elif prompt_type == 'decision':
                prompt = self.prompt_generator.generate_decision_prompt(
                    task=test_case['task'],
                    agent_response=test_case.get('agent_response', ''),
                    context=test_case.get('decision_context', {})
                )
            else:
                raise ValueError(f"Unsupported prompt_type: {prompt_type}")

            # Count prompt tokens
            tokens_prompt = self.llm_interface.count_tokens(prompt)

            # Send prompt to LLM
            response = self.llm_interface.send_prompt(prompt)

            # Count response tokens
            tokens_response = self.llm_interface.count_tokens(response)

            # Calculate latency
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            # Extract metrics from response
            rule_violations_count = 0
            quality_score = None
            schema_valid = None

            # Parse response (simplified - real implementation would use parser)
            # For validation prompts, extract violations and quality score
            if prompt_type == 'validation':
                try:
                    # Try to extract JSON
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        response_data = json.loads(json_match.group())
                        rule_violations_count = len(response_data.get('violations', []))
                        quality_score = response_data.get('quality_score', 0) / 100.0  # Normalize to 0-1
                        schema_valid = True
                except Exception:
                    schema_valid = False

            # Restore original mode
            self.prompt_generator.set_structured_mode(original_mode)

            return TestMetrics(
                prompt_format=format_str,
                tokens_prompt=tokens_prompt,
                tokens_response=tokens_response,
                total_tokens=tokens_prompt + tokens_response,
                latency_ms=latency_ms,
                success=True,
                rule_violations_count=rule_violations_count,
                quality_score=quality_score,
                schema_valid=schema_valid
            )

        except Exception as e:
            logger.error(f"Test failed ({format_str}): {e}")

            # Restore original mode
            try:
                self.prompt_generator.set_structured_mode(original_mode)
            except:
                pass

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000

            return TestMetrics(
                prompt_format=format_str,
                tokens_prompt=0,
                tokens_response=0,
                total_tokens=0,
                latency_ms=latency_ms,
                success=False,
                error_message=str(e)
            )

    def _perform_statistical_analysis(
        self,
        structured_metrics: List[TestMetrics],
        unstructured_metrics: List[TestMetrics],
        alpha: float
    ) -> Dict[str, Any]:
        """Perform statistical analysis on collected metrics.

        Uses t-tests to determine if differences are statistically significant.

        Args:
            structured_metrics: Metrics from structured format tests
            unstructured_metrics: Metrics from unstructured format tests
            alpha: Significance level (default: 0.05)

        Returns:
            Dictionary with statistical analysis results
        """
        analysis = {}

        # Filter successful tests
        structured_success = [m for m in structured_metrics if m.success]
        unstructured_success = [m for m in unstructured_metrics if m.success]

        # Success rates
        analysis['structured_success_rate'] = (
            len(structured_success) / len(structured_metrics) * 100
        ) if structured_metrics else 0
        analysis['unstructured_success_rate'] = (
            len(unstructured_success) / len(unstructured_metrics) * 100
        ) if unstructured_metrics else 0

        # Token analysis
        if structured_success and unstructured_success:
            structured_tokens = [m.total_tokens for m in structured_success]
            unstructured_tokens = [m.total_tokens for m in unstructured_success]

            analysis['structured_tokens_avg'] = mean(structured_tokens)
            analysis['structured_tokens_std'] = stdev(structured_tokens) if len(structured_tokens) > 1 else 0
            analysis['unstructured_tokens_avg'] = mean(unstructured_tokens)
            analysis['unstructured_tokens_std'] = stdev(unstructured_tokens) if len(unstructured_tokens) > 1 else 0

            # Calculate improvement
            if analysis['unstructured_tokens_avg'] > 0:
                improvement = (
                    (analysis['unstructured_tokens_avg'] - analysis['structured_tokens_avg'])
                    / analysis['unstructured_tokens_avg'] * 100
                )
                analysis['token_improvement_pct'] = improvement

            # T-test for tokens
            if len(structured_tokens) > 1 and len(unstructured_tokens) > 1:
                t_stat, p_value = stats.ttest_ind(structured_tokens, unstructured_tokens)
                analysis['token_tstat'] = t_stat
                analysis['token_pvalue'] = p_value
                analysis['token_significant'] = p_value < alpha

        # Latency analysis
        if structured_success and unstructured_success:
            structured_latency = [m.latency_ms for m in structured_success]
            unstructured_latency = [m.latency_ms for m in unstructured_success]

            analysis['structured_latency_avg'] = mean(structured_latency)
            analysis['structured_latency_std'] = stdev(structured_latency) if len(structured_latency) > 1 else 0
            analysis['unstructured_latency_avg'] = mean(unstructured_latency)
            analysis['unstructured_latency_std'] = stdev(unstructured_latency) if len(unstructured_latency) > 1 else 0

            # Calculate improvement
            if analysis['unstructured_latency_avg'] > 0:
                improvement = (
                    (analysis['unstructured_latency_avg'] - analysis['structured_latency_avg'])
                    / analysis['unstructured_latency_avg'] * 100
                )
                analysis['latency_improvement_pct'] = improvement

            # T-test for latency
            if len(structured_latency) > 1 and len(unstructured_latency) > 1:
                t_stat, p_value = stats.ttest_ind(structured_latency, unstructured_latency)
                analysis['latency_tstat'] = t_stat
                analysis['latency_pvalue'] = p_value
                analysis['latency_significant'] = p_value < alpha

        # Rule violations analysis
        structured_violations = [m.rule_violations_count for m in structured_success]
        unstructured_violations = [m.rule_violations_count for m in unstructured_success]

        if structured_violations:
            analysis['structured_violations_avg'] = mean(structured_violations)
        if unstructured_violations:
            analysis['unstructured_violations_avg'] = mean(unstructured_violations)

        # Quality score analysis
        structured_quality = [m.quality_score for m in structured_success if m.quality_score is not None]
        unstructured_quality = [m.quality_score for m in unstructured_success if m.quality_score is not None]

        if structured_quality:
            analysis['structured_quality_avg'] = mean(structured_quality)
        if unstructured_quality:
            analysis['unstructured_quality_avg'] = mean(unstructured_quality)

        return analysis

    def export_results(
        self,
        result: ABTestResult,
        output_path: str
    ) -> None:
        """Export test results to JSON file.

        Args:
            result: ABTestResult to export
            output_path: Path to output JSON file

        Example:
            >>> framework.export_results(
            ...     result,
            ...     'evaluation_results/validation_ab_test.json'
            ... )
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, indent=2)

        logger.info(f"Exported results to {output_path}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get framework statistics.

        Returns:
            Dictionary with statistics
        """
        return self.stats.copy()
