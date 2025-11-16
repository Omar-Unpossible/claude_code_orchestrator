"""Deliverable assessment for task execution (v1.8.1).

This module provides the DeliverableAssessor class that evaluates the quality and
completeness of deliverables created during task execution, particularly when
tasks hit max_turns or other limits.

Purpose:
    Prevent false failures by assessing actual work completed when limits are hit.
    Enable partial success recognition when deliverables exist but task incomplete.

Example Usage:
    >>> from src.orchestration.deliverable_assessor import DeliverableAssessor
    >>> from src.monitoring.file_watcher import FileWatcher
    >>> from src.orchestration.quality_controller import QualityController
    >>>
    >>> assessor = DeliverableAssessor(file_watcher, quality_controller)
    >>> assessment = assessor.assess_deliverables(task)
    >>>
    >>> print(f"Outcome: {assessment.outcome}")
    >>> print(f"Files created: {len(assessment.files)}")
    >>> print(f"Quality score: {assessment.quality_score:.2f}")
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from src.core.models import Task, TaskOutcome

logger = logging.getLogger(__name__)


@dataclass
class DeliverableAssessment:
    """Assessment of deliverables created during task execution.

    Attributes:
        outcome: Task outcome based on deliverable assessment
        files: List of file paths created/modified
        quality_score: Overall quality score (0.0-1.0)
        reason: Human-readable explanation of outcome
        syntax_valid: Whether all files have valid syntax
        estimated_completeness: Estimated task completion (0.0-1.0)
        assessment_time: When assessment was performed
    """
    outcome: TaskOutcome
    files: List[str]
    quality_score: float
    reason: str
    syntax_valid: bool = True
    estimated_completeness: float = 1.0
    assessment_time: Optional[datetime] = None

    def __post_init__(self):
        """Set assessment time if not provided."""
        if self.assessment_time is None:
            self.assessment_time = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert assessment to dictionary.

        Returns:
            Dictionary representation of assessment
        """
        return {
            'outcome': self.outcome.value if isinstance(self.outcome, TaskOutcome) else str(self.outcome),
            'files': self.files,
            'quality_score': self.quality_score,
            'reason': self.reason,
            'syntax_valid': self.syntax_valid,
            'estimated_completeness': self.estimated_completeness,
            'assessment_time': self.assessment_time.isoformat() if self.assessment_time else None
        }


class DeliverableAssessor:
    """Assess quality of deliverables created during task execution.

    Evaluates files created/modified to determine if task delivered value
    despite hitting limits (max_turns, timeout, etc). Uses lightweight
    heuristics to avoid expensive LLM calls during error handling.

    Heuristics:
        - Syntax validation (Python, JSON, YAML)
        - File size checks (too small = stub, too large = bloat)
        - Content analysis (docstrings, type hints, functions)
        - File count (more files = more work completed)

    Attributes:
        file_watcher: FileWatcher instance for tracking file changes
        quality_controller: QualityController instance for advanced validation
    """

    # Quality scoring weights
    WEIGHT_SYNTAX = 0.3       # Syntax validity
    WEIGHT_SIZE = 0.2         # Appropriate file size
    WEIGHT_CONTENT = 0.3      # Code quality indicators
    WEIGHT_COUNT = 0.2        # Number of files created

    # File size thresholds (bytes)
    MIN_FILE_SIZE = 100       # Below this = likely stub
    MAX_FILE_SIZE = 50000     # Above this = possibly bloated
    GOOD_FILE_SIZE_MIN = 500  # Ideal minimum
    GOOD_FILE_SIZE_MAX = 10000  # Ideal maximum

    def __init__(self, file_watcher, quality_controller=None):
        """Initialize DeliverableAssessor.

        Args:
            file_watcher: FileWatcher instance for tracking file changes
            quality_controller: Optional QualityController for advanced validation
        """
        self.file_watcher = file_watcher
        self.quality_controller = quality_controller

        logger.debug("DeliverableAssessor initialized")

    def assess_deliverables(self, task: Task, file_watcher=None) -> DeliverableAssessment:
        """Assess deliverables created during task execution.

        Args:
            task: Task instance to assess
            file_watcher: Optional FileWatcher instance (overrides self.file_watcher)

        Returns:
            DeliverableAssessment with outcome, files, and quality score

        Example:
            >>> assessment = assessor.assess_deliverables(task)
            >>> if assessment.outcome == TaskOutcome.SUCCESS_WITH_LIMITS:
            ...     print(f"Task delivered {len(assessment.files)} files")
        """
        logger.info(f"Assessing deliverables for task {task.id}")

        # Get files created/modified since task started
        new_files = self._get_task_files(task, file_watcher=file_watcher)

        if not new_files:
            return DeliverableAssessment(
                outcome=TaskOutcome.FAILED,
                files=[],
                quality_score=0.0,
                reason="No deliverables created",
                syntax_valid=False,
                estimated_completeness=0.0
            )

        logger.debug(f"Found {len(new_files)} files for task {task.id}")

        # Validate syntax for all files
        valid_files = []
        syntax_errors = []
        for file_path in new_files:
            if self._is_valid_syntax(file_path):
                valid_files.append(file_path)
            else:
                syntax_errors.append(file_path)

        if not valid_files:
            return DeliverableAssessment(
                outcome=TaskOutcome.PARTIAL,
                files=new_files,
                quality_score=0.3,
                reason=f"Files created ({len(new_files)}) but all have syntax errors",
                syntax_valid=False,
                estimated_completeness=0.3
            )

        # Assess quality of valid files
        quality_score = self._assess_file_quality(valid_files)

        # Determine outcome based on quality
        if quality_score >= 0.7:
            outcome = TaskOutcome.SUCCESS_WITH_LIMITS
            reason = f"Created {len(valid_files)} valid files, quality score {quality_score:.2f}"
            completeness = 0.9  # High quality suggests near completion
        elif quality_score >= 0.5:
            outcome = TaskOutcome.PARTIAL
            reason = f"Created {len(valid_files)} files, quality score {quality_score:.2f}, may need refinement"
            completeness = 0.6
        else:
            outcome = TaskOutcome.FAILED
            reason = f"Created {len(valid_files)} files but quality score {quality_score:.2f} is too low"
            completeness = 0.3

        logger.info(
            f"Task {task.id} assessment: outcome={outcome.value}, "
            f"files={len(valid_files)}, quality={quality_score:.2f}"
        )

        return DeliverableAssessment(
            outcome=outcome,
            files=valid_files,
            quality_score=quality_score,
            reason=reason,
            syntax_valid=len(syntax_errors) == 0,
            estimated_completeness=completeness
        )

    def _get_task_files(self, task: Task, file_watcher=None) -> List[str]:
        """Get files created/modified during task execution.

        Args:
            task: Task instance
            file_watcher: Optional FileWatcher instance (overrides self.file_watcher)

        Returns:
            List of file paths created/modified since task started
        """
        # Use provided file_watcher or fall back to self.file_watcher
        watcher = file_watcher if file_watcher is not None else self.file_watcher

        if not watcher:
            logger.warning("FileWatcher not available, cannot detect files")
            return []

        try:
            # Get recent changes from FileWatcher
            # Note: For now, we get all recent changes since we don't have reliable session start time
            # TODO: Pass session_start_time from orchestrator for accurate filtering
            all_changes = watcher.get_recent_changes(limit=100)
            logger.info(f"Retrieved {len(all_changes)} changes from FileWatcher for task {task.id}")

            # Extract unique file paths
            files = []
            for change in all_changes:
                # Handle both 'file_path' and 'path' keys
                file_path = change.get('file_path') or change.get('path')
                if file_path and file_path not in files:
                    # Only include 'created' and 'modified' changes, skip 'deleted'
                    change_type = change.get('change_type', 'unknown')
                    if change_type in ('created', 'modified'):
                        files.append(file_path)
                        logger.debug(f"Added {change_type} file: {file_path}")

            logger.info(f"FileWatcher detected {len(files)} deliverable files for task {task.id}")
            return files
        except Exception as e:
            logger.error(f"Failed to get file changes: {e}", exc_info=True)
            return []

    def _is_valid_syntax(self, file_path: str) -> bool:
        """Check if file has valid syntax.

        Supports:
            - Python (.py): compile() check
            - JSON (.json): json.load() check
            - YAML (.yaml, .yml): basic parsing (if PyYAML available)
            - Other: basic readability check

        Args:
            file_path: Path to file to validate

        Returns:
            True if syntax is valid, False otherwise

        Example:
            >>> assessor._is_valid_syntax("example.py")
            True  # Valid Python syntax
            >>> assessor._is_valid_syntax("broken.py")
            False  # Syntax error
        """
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return False

        try:
            if file_path.endswith('.py'):
                # Python syntax check
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, file_path, 'exec')
                return True

            elif file_path.endswith('.json'):
                # JSON syntax check
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                return True

            elif file_path.endswith(('.yaml', '.yml')):
                # YAML syntax check (basic)
                try:
                    import yaml
                    with open(file_path, 'r', encoding='utf-8') as f:
                        yaml.safe_load(f)
                    return True
                except ImportError:
                    # PyYAML not available, just check readability
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read()
                    return True

            else:
                # For other file types, just check if readable
                with open(file_path, 'r', encoding='utf-8') as f:
                    f.read()
                return True

        except SyntaxError as e:
            logger.debug(f"Syntax error in {file_path}: {e}")
            return False
        except json.JSONDecodeError as e:
            logger.debug(f"JSON decode error in {file_path}: {e}")
            return False
        except Exception as e:
            logger.debug(f"Error validating {file_path}: {e}")
            return False

    def _assess_file_quality(self, files: List[str]) -> float:
        """Lightweight quality assessment of created files.

        Uses heuristics to score file quality without expensive LLM calls:
            - Syntax validity (already checked)
            - File size (appropriate range)
            - Content indicators (docstrings, type hints, functions)
            - File count (more files = more work)

        Args:
            files: List of file paths to assess

        Returns:
            Quality score (0.0-1.0)

        Example:
            >>> files = ["cli.py", "templates.py", "README.md"]
            >>> score = assessor._assess_file_quality(files)
            >>> print(f"Quality: {score:.2f}")  # e.g., 0.85
        """
        if not files:
            return 0.0

        scores = []

        for file_path in files:
            file_score = 0.0

            try:
                # Get file size
                file_size = os.path.getsize(file_path)

                # Size score (0.0-1.0)
                if file_size < self.MIN_FILE_SIZE:
                    size_score = 0.1  # Too small, likely stub
                elif file_size > self.MAX_FILE_SIZE:
                    size_score = 0.5  # Too large, possibly bloated
                elif self.GOOD_FILE_SIZE_MIN <= file_size <= self.GOOD_FILE_SIZE_MAX:
                    size_score = 1.0  # Ideal size range
                else:
                    size_score = 0.7  # Acceptable size

                # Content score (0.0-1.0) - only for code files
                content_score = 0.5  # Base score for any valid file

                if file_path.endswith('.py'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for quality indicators
                    has_docstrings = '"""' in content or "'''" in content
                    has_type_hints = ': ' in content and '->' in content
                    has_functions = 'def ' in content or 'class ' in content
                    has_imports = 'import ' in content

                    # Increment score for each indicator
                    if has_docstrings:
                        content_score += 0.15
                    if has_type_hints:
                        content_score += 0.15
                    if has_functions:
                        content_score += 0.10
                    if has_imports:
                        content_score += 0.10

                elif file_path.endswith('.md'):
                    # README/docs get bonus for having content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if len(content) > 500:
                        content_score += 0.3

                # Combine scores (weighted)
                file_score = (size_score * self.WEIGHT_SIZE) + (content_score * self.WEIGHT_CONTENT)

                # Syntax always valid (pre-filtered)
                file_score += 1.0 * self.WEIGHT_SYNTAX

                scores.append(min(file_score, 1.0))

            except Exception as e:
                logger.debug(f"Error assessing {file_path}: {e}")
                scores.append(0.3)  # Low score for files that can't be assessed

        # Average score across all files
        base_score = sum(scores) / len(scores) if scores else 0.0

        # Bonus for file count (more files = more work)
        file_count_bonus = min(len(files) * 0.05, 0.2)  # Max 0.2 bonus for 4+ files

        total_score = min(base_score + file_count_bonus, 1.0)

        logger.debug(
            f"Quality assessment: {len(files)} files, "
            f"avg_score={base_score:.2f}, bonus={file_count_bonus:.2f}, "
            f"total={total_score:.2f}"
        )

        return total_score
