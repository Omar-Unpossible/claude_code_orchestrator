"""Adaptive max_turns calculation based on task complexity.

This module provides the MaxTurnsCalculator class that analyzes task descriptions
and metadata to determine appropriate max_turns values for Claude Code CLI execution.

Based on Claude Code max-turns guide recommendations:
- Simple tasks: 3 turns (single file, specific fix)
- Medium tasks: 6 turns (small feature, module refactor)
- Complex tasks: 12 turns (complete feature, multi-file)
- Very complex: 20 turns (large refactor, migrations)
- Default: 10 turns (if unsure)

Example Usage:
    >>> from src.orchestration.max_turns_calculator import MaxTurnsCalculator
    >>> calculator = MaxTurnsCalculator()
    >>>
    >>> # Calculate max_turns for a task
    >>> task = {
    ...     'id': 123,
    ...     'title': 'Implement authentication',
    ...     'description': 'Add JWT authentication to API',
    ...     'task_type': 'code_generation',
    ...     'estimated_files': 5,
    ...     'estimated_loc': 300
    ... }
    >>> max_turns = calculator.calculate(task)
    >>> print(f"Recommended max_turns: {max_turns}")
    >>>
    >>> # With custom config
    >>> config = {
    ...     'max_turns_by_type': {'debugging': 25},
    ...     'min': 5,
    ...     'max': 25,
    ...     'default': 12
    ... }
    >>> calculator = MaxTurnsCalculator(config=config)
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MaxTurnsCalculator:
    """Calculate appropriate max_turns based on task complexity.

    Based on Claude Code max-turns guide:
    - Simple tasks: 3 turns (single file, specific fix)
    - Medium tasks: 6 turns (small feature, module refactor)
    - Complex tasks: 12 turns (complete feature, multi-file)
    - Very complex: 20 turns (large refactor, migrations)
    - Default: 10 turns (if unsure)

    Attributes:
        task_type_defaults: Dict mapping task types to default max_turns
        min_turns: Minimum allowed max_turns value
        max_turns: Maximum allowed max_turns value
        default_turns: Default max_turns when complexity is unknown
    """

    # Complexity indicators (from guide)
    COMPLEX_WORDS = [
        'migrate', 'refactor', 'implement', 'debug', 'comprehensive',
        'entire', 'all', 'complete', 'full', 'across', 'multiple',
        'system', 'architecture', 'framework'
    ]

    SCOPE_INDICATORS = [
        'all files', 'entire codebase', 'multiple', 'across',
        'throughout', 'repository', 'project-wide', 'every'
    ]

    # Task type specific defaults (from guide)
    TASK_TYPE_DEFAULTS = {
        'validation': 5,        # Focused validation checks
        'code_generation': 12,  # Code gen needs iterations
        'refactoring': 15,      # Refactoring needs test cycles
        'debugging': 20,        # Debugging can be extensive
        'error_analysis': 8,    # Analysis is bounded
        'planning': 5,          # Planning is mostly reading
        'documentation': 3,     # Docs are usually quick
        'testing': 8,           # Test creation is moderate
    }

    # Safety bounds (from guide)
    MIN_TURNS = 3   # Never less than 3
    MAX_TURNS = 30  # Never more than 30
    DEFAULT_TURNS = 10  # Fallback

    def __init__(self, config: Optional[Dict] = None):
        """Initialize calculator with optional config overrides.

        Args:
            config: Optional configuration dict with overrides:
                - max_turns_by_type: Dict mapping task types to max_turns
                - min: Minimum max_turns value (default 3)
                - max: Maximum max_turns value (default 30)
                - default: Default max_turns when unknown (default 10)

        Example:
            >>> config = {
            ...     'max_turns_by_type': {'debugging': 25},
            ...     'min': 5,
            ...     'max': 25,
            ...     'default': 12
            ... }
            >>> calculator = MaxTurnsCalculator(config=config)
        """
        self.config = config or {}

        # Allow config overrides
        self.task_type_defaults = self.config.get(
            'max_turns_by_type',
            self.TASK_TYPE_DEFAULTS
        )
        self.min_turns = self.config.get('min', self.MIN_TURNS)
        self.max_turns = self.config.get('max', self.MAX_TURNS)
        self.default_turns = self.config.get('default', self.DEFAULT_TURNS)

        logger.debug(
            f"MaxTurnsCalculator initialized: "
            f"min={self.min_turns}, max={self.max_turns}, default={self.default_turns}"
        )

    def calculate(self, task: Dict) -> int:
        """Calculate appropriate max_turns for task.

        Analyzes task description, type, and metadata to determine the
        appropriate max_turns value. Decision logic:

        1. Check for task type override (if task_type matches)
        2. Analyze text for complexity/scope indicators
        3. Check metadata (estimated_files, estimated_loc)
        4. Apply decision rules:
           - complexity=0, scope=0, files≤1 → 3 turns (simple)
           - complexity≤1, scope=0, files≤3 → 6 turns (medium)
           - complexity≤2, scope=1, files≤8 → 12 turns (complex)
           - loc>500 or scope≥2 → 20 turns (very complex)
           - else → default (10 turns)
        5. Enforce min/max bounds

        Args:
            task: Task dict with keys:
                - id: Task ID (for logging)
                - title: Task title (optional)
                - description: Task description (optional)
                - task_type: Task type string (optional)
                - estimated_files: Number of files (from ComplexityEstimate, optional)
                - estimated_loc: Lines of code (from ComplexityEstimate, optional)

        Returns:
            int: Recommended max_turns (bounded by min/max)

        Example:
            >>> task = {
            ...     'id': 123,
            ...     'title': 'Fix bug',
            ...     'description': 'Fix authentication bug in single file',
            ...     'estimated_files': 1,
            ...     'estimated_loc': 50
            ... }
            >>> calculator.calculate(task)
            3  # Simple task
        """
        task_id = task.get('id', 'unknown')

        # Check for task type override first
        task_type = task.get('task_type')
        if task_type and task_type in self.task_type_defaults:
            turns = self.task_type_defaults[task_type]
            logger.debug(
                f"Task {task_id}: Using task type default for '{task_type}': {turns} turns"
            )
            return self._bound(turns)

        # Analyze task description
        description = task.get('description', '').lower()
        title = task.get('title', '').lower()
        combined_text = f"{title} {description}"

        # Count complexity indicators
        complexity = sum(
            1 for word in self.COMPLEX_WORDS
            if word in combined_text
        )

        scope = sum(
            1 for indicator in self.SCOPE_INDICATORS
            if indicator in combined_text
        )

        # Check task metadata (from ComplexityEstimate if available)
        estimated_files = task.get('estimated_files', 1)
        estimated_loc = task.get('estimated_loc', 0)

        logger.debug(
            f"Task {task_id}: complexity={complexity}, scope={scope}, "
            f"files={estimated_files}, loc={estimated_loc}"
        )

        # Decision logic (from guide)
        # Check very complex conditions first
        if estimated_loc > 500 or scope >= 2:
            # Very Complex: Large refactor, migrations
            turns = 20
            reason = "very complex (large refactor, >500 LOC or wide scope)"

        elif complexity == 0 and scope == 0 and estimated_files <= 1:
            # Simple: Single file read, specific fix
            turns = 3
            reason = "simple (single file, no complexity indicators)"

        elif complexity <= 1 and scope == 0 and estimated_files <= 3:
            # Medium: Small feature, single module refactor
            turns = 6
            reason = "medium (small feature, ≤3 files)"

        elif complexity <= 2 or scope == 1 or estimated_files <= 8:
            # Complex: Complete feature, multi-file work
            turns = 12
            reason = "complex (feature, multiple files)"

        else:
            # Default for unknown complexity
            turns = self.default_turns
            reason = "default (complexity unknown)"

        logger.info(
            f"Task {task_id}: Calculated max_turns={turns} ({reason})"
        )

        return self._bound(turns)

    def _bound(self, turns: int) -> int:
        """Ensure turns within configured bounds.

        Args:
            turns: Unbounded max_turns value

        Returns:
            int: Bounded max_turns value (min ≤ turns ≤ max)

        Example:
            >>> calculator = MaxTurnsCalculator()
            >>> calculator._bound(2)  # Below min
            3
            >>> calculator._bound(50)  # Above max
            30
            >>> calculator._bound(10)  # Within bounds
            10
        """
        bounded = max(self.min_turns, min(turns, self.max_turns))
        if bounded != turns:
            logger.debug(
                f"Bounded max_turns from {turns} to {bounded} "
                f"(min={self.min_turns}, max={self.max_turns})"
            )
        return bounded
