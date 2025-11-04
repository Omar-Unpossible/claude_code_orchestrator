"""Evaluation and analysis modules for Obra orchestration system.

This package provides tools for:
- A/B testing (structured vs unstructured prompts)
- Performance metrics collection
- Statistical analysis
- Results export and visualization

Modules:
    ab_testing: A/B testing framework for prompt comparison (PHASE_6 TASK_6.2)
"""

from src.evaluation.ab_testing import ABTestingFramework, ABTestResult, TestMetrics

__all__ = [
    'ABTestingFramework',
    'ABTestResult',
    'TestMetrics'
]
