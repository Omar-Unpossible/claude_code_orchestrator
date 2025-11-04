"""Complexity estimation data structures.

This module provides the ComplexityEstimate data class for representing
task complexity analysis results. Used by TaskComplexityEstimator to
return detailed complexity assessments including decomposition suggestions
and parallelization opportunities.

Example Usage:
    >>> from datetime import datetime
    >>> estimate = ComplexityEstimate(
    ...     task_id=123,
    ...     estimated_tokens=5000,
    ...     estimated_loc=250,
    ...     estimated_files=3,
    ...     complexity_score=65.0,
    ...     should_decompose=True,
    ...     decomposition_suggestions=[
    ...         "Implement data models",
    ...         "Create API endpoints",
    ...         "Add tests"
    ...     ],
    ...     parallelization_opportunities=[
    ...         {"group": 1, "tasks": ["Implement data models", "Add tests"]},
    ...     ],
    ...     estimated_duration_minutes=120,
    ...     confidence=0.75,
    ...     timestamp=datetime.now()
    ... )
    >>>
    >>> # Serialize
    >>> data = estimate.to_dict()
    >>>
    >>> # Deserialize
    >>> estimate2 = ComplexityEstimate.from_dict(data)
    >>>
    >>> # Category
    >>> category = estimate.get_complexity_category()  # "high"
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ComplexityEstimate:
    """Represents a task complexity analysis result.

    PHASE_5B UPDATE: This class now returns SUGGESTIONS for Claude to consider,
    not authoritative commands. Claude makes final decisions on decomposition
    and parallelization.

    Contains detailed information about estimated task complexity including
    token count, lines of code, file modifications, and decomposition
    suggestions. Used by orchestration engine to provide suggestions to Claude.

    Attributes:
        task_id: ID of the task being estimated
        estimated_tokens: Estimated prompt + response tokens
        estimated_loc: Estimated lines of code to write
        estimated_files: Estimated number of files to modify/create
        complexity_score: Overall complexity score (0-100)
        obra_suggests_decomposition: Whether Obra suggests task decomposition (not a command)
        obra_suggestion_confidence: Obra's confidence in suggestion (0-1)
        suggested_subtasks: Obra's suggested subtask descriptions
        suggested_parallel_groups: Obra's suggested groups of parallelizable subtasks
        estimated_duration_minutes: Estimated time to complete
        suggestion_rationale: Explanation for why Obra suggests decomposition or not
        timestamp: When estimate was created
    """

    task_id: int
    estimated_tokens: int
    estimated_loc: int
    estimated_files: int
    complexity_score: float
    obra_suggests_decomposition: bool  # Changed from should_decompose
    obra_suggestion_confidence: float  # NEW: Confidence in Obra's suggestion
    suggested_subtasks: List[str] = field(default_factory=list)  # Changed from decomposition_suggestions
    suggested_parallel_groups: List[Dict[str, Any]] = field(default_factory=list)  # Changed from parallelization_opportunities
    estimated_duration_minutes: int = 0
    suggestion_rationale: str = ""  # NEW: Why Obra suggests this
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        """Validate field values after initialization.

        Raises:
            ValueError: If any field has an invalid value
        """
        if self.task_id < 0:
            raise ValueError(f"task_id must be non-negative, got {self.task_id}")

        if self.estimated_tokens < 0:
            raise ValueError(f"estimated_tokens must be non-negative, got {self.estimated_tokens}")

        if self.estimated_loc < 0:
            raise ValueError(f"estimated_loc must be non-negative, got {self.estimated_loc}")

        if self.estimated_files < 0:
            raise ValueError(f"estimated_files must be non-negative, got {self.estimated_files}")

        if not 0 <= self.complexity_score <= 100:
            raise ValueError(f"complexity_score must be in [0, 100], got {self.complexity_score}")

        if not 0 <= self.obra_suggestion_confidence <= 1:
            raise ValueError(f"obra_suggestion_confidence must be in [0, 1], got {self.obra_suggestion_confidence}")

        if self.estimated_duration_minutes < 0:
            raise ValueError(f"estimated_duration_minutes must be non-negative, got {self.estimated_duration_minutes}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize ComplexityEstimate to a JSON-serializable dictionary.

        Converts datetime objects to ISO format strings for JSON compatibility.

        Returns:
            Dictionary representation with all fields as JSON-compatible types

        Example:
            >>> estimate = ComplexityEstimate(task_id=1, ...)
            >>> data = estimate.to_dict()
            >>> isinstance(data['timestamp'], str)
            True
        """
        return {
            'task_id': self.task_id,
            'estimated_tokens': self.estimated_tokens,
            'estimated_loc': self.estimated_loc,
            'estimated_files': self.estimated_files,
            'complexity_score': self.complexity_score,
            'obra_suggests_decomposition': self.obra_suggests_decomposition,
            'obra_suggestion_confidence': self.obra_suggestion_confidence,
            'suggested_subtasks': self.suggested_subtasks.copy(),
            'suggested_parallel_groups': [
                opp.copy() for opp in self.suggested_parallel_groups
            ],
            'estimated_duration_minutes': self.estimated_duration_minutes,
            'suggestion_rationale': self.suggestion_rationale,
            'timestamp': self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ComplexityEstimate':
        """Deserialize ComplexityEstimate from a dictionary.

        Converts ISO format timestamp strings back to datetime objects.
        Supports both old field names (for backward compatibility) and new field names.

        Args:
            data: Dictionary containing ComplexityEstimate fields

        Returns:
            New ComplexityEstimate instance with data from dictionary

        Raises:
            KeyError: If required fields are missing from data
            ValueError: If field values are invalid

        Example:
            >>> data = {
            ...     'task_id': 1,
            ...     'estimated_tokens': 1000,
            ...     'estimated_loc': 50,
            ...     'estimated_files': 2,
            ...     'complexity_score': 40.0,
            ...     'obra_suggests_decomposition': False,
            ...     'obra_suggestion_confidence': 0.8,
            ...     'suggested_subtasks': [],
            ...     'suggested_parallel_groups': [],
            ...     'estimated_duration_minutes': 30,
            ...     'suggestion_rationale': 'Low complexity task',
            ...     'timestamp': '2025-11-03T10:00:00.000000'
            ... }
            >>> estimate = ComplexityEstimate.from_dict(data)
            >>> estimate.task_id
            1
        """
        # Parse timestamp from ISO format string
        timestamp_str = data.get('timestamp')
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str)
        elif isinstance(timestamp_str, datetime):
            timestamp = timestamp_str
        else:
            timestamp = datetime.now()

        # Support old field names for backward compatibility
        suggests_decompose = data.get('obra_suggests_decomposition', data.get('should_decompose', False))
        confidence = data.get('obra_suggestion_confidence', data.get('confidence', 0.0))
        subtasks = data.get('suggested_subtasks', data.get('decomposition_suggestions', []))
        parallel_groups = data.get('suggested_parallel_groups', data.get('parallelization_opportunities', []))

        return cls(
            task_id=data['task_id'],
            estimated_tokens=data['estimated_tokens'],
            estimated_loc=data['estimated_loc'],
            estimated_files=data['estimated_files'],
            complexity_score=data['complexity_score'],
            obra_suggests_decomposition=suggests_decompose,
            obra_suggestion_confidence=confidence,
            suggested_subtasks=subtasks.copy() if isinstance(subtasks, list) else list(subtasks),
            suggested_parallel_groups=[
                opp.copy() if isinstance(opp, dict) else opp for opp in parallel_groups
            ],
            estimated_duration_minutes=data.get('estimated_duration_minutes', 0),
            suggestion_rationale=data.get('suggestion_rationale', ''),
            timestamp=timestamp,
        )

    def get_complexity_category(self) -> str:
        """Return complexity category based on complexity score.

        Categories are determined by score thresholds:
        - low: 0-30
        - medium: 31-60
        - high: 61-85
        - very_high: 86-100

        Returns:
            One of: "low", "medium", "high", "very_high"

        Example:
            >>> estimate = ComplexityEstimate(
            ...     task_id=1,
            ...     estimated_tokens=1000,
            ...     estimated_loc=50,
            ...     estimated_files=2,
            ...     complexity_score=65.0,
            ...     obra_suggests_decomposition=True,
            ...     obra_suggestion_confidence=0.8
            ... )
            >>> estimate.get_complexity_category()
            'high'
        """
        if self.complexity_score <= 30:
            return "low"
        elif self.complexity_score <= 60:
            return "medium"
        elif self.complexity_score <= 85:
            return "high"
        else:
            return "very_high"

    def to_suggestion_dict(self) -> Dict[str, Any]:
        """Convert to suggestion format for Claude's prompt.

        PHASE_5B: This method formats the complexity estimate as a suggestion
        for Claude to consider, not as an authoritative command. Claude makes
        final decisions on decomposition and parallelization.

        Returns:
            Dictionary formatted for inclusion in structured prompts with:
            - complexity_analysis: Estimated metrics
            - obra_suggestion: Decomposition and parallelization suggestions
            - guidance: Clarifies Claude's authority to accept/reject

        Example:
            >>> estimate = ComplexityEstimate(...)
            >>> suggestion = estimate.to_suggestion_dict()
            >>> suggestion['guidance']
            'Review this analysis. You may accept, modify, or reject...'
        """
        return {
            "complexity_analysis": {
                "estimated_tokens": self.estimated_tokens,
                "estimated_loc": self.estimated_loc,
                "estimated_files": self.estimated_files,
                "complexity_score": self.complexity_score,
                "complexity_category": self.get_complexity_category(),
                "estimated_duration_minutes": self.estimated_duration_minutes
            },
            "obra_suggestion": {
                "suggest_decomposition": self.obra_suggests_decomposition,
                "confidence": self.obra_suggestion_confidence,
                "rationale": self.suggestion_rationale,
                "suggested_subtasks": self.suggested_subtasks.copy(),
                "suggested_parallel_groups": [
                    group.copy() for group in self.suggested_parallel_groups
                ]
            },
            "guidance": "Review this analysis. You may accept, modify, or reject these suggestions based on your understanding of the codebase. Your judgment takes precedence."
        }

    def __repr__(self) -> str:
        """Return detailed string representation for debugging.

        Returns:
            String with all field values formatted for readability

        Example:
            >>> estimate = ComplexityEstimate(task_id=1, ...)
            >>> repr(estimate)
            'ComplexityEstimate(task_id=1, score=65.0, category=high, ...)'
        """
        return (
            f"ComplexityEstimate("
            f"task_id={self.task_id}, "
            f"score={self.complexity_score:.1f}, "
            f"category={self.get_complexity_category()}, "
            f"tokens={self.estimated_tokens}, "
            f"loc={self.estimated_loc}, "
            f"files={self.estimated_files}, "
            f"suggests_decomp={self.obra_suggests_decomposition}, "
            f"confidence={self.obra_suggestion_confidence:.2f}, "
            f"duration={self.estimated_duration_minutes}min)"
        )
