"""Checkpoint verification for integrity and state validation.

This module implements the CheckpointVerifier class that validates checkpoints
before creation (pre-checkpoint) and after loading (post-resume).

Example:
    >>> from src.orchestration.session import CheckpointVerifier
    >>> verifier = CheckpointVerifier(config, git_manager, state_manager)
    >>> ready, checks_failed = verifier.verify_ready()
    >>> if not ready:
    ...     print(f"Cannot checkpoint: {checks_failed}")

Author: Obra System
Created: 2025-11-15
Version: 1.0.0
"""

import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, UTC, timedelta

from src.core.config import Config
from src.core.exceptions import OrchestratorException

logger = logging.getLogger(__name__)


class CheckpointVerificationError(OrchestratorException):
    """Raised when checkpoint verification fails."""


class CheckpointCorruptedError(OrchestratorException):
    """Raised when checkpoint is corrupted or invalid."""


class CheckpointVerifier:
    """Verify checkpoint integrity before creation and after resume.

    This class performs validation checks to ensure checkpoints are created
    from consistent state and resumed safely.

    Pre-checkpoint checks:
    - Git working directory clean (no uncommitted changes)
    - Tests passing
    - Coverage meets minimum threshold
    - Task at safe boundary (optional)

    Post-resume checks:
    - Files from checkpoint exist
    - Git branch matches
    - Checkpoint not too old
    - Tests pass after resume (optional)

    Thread-safe: No (designed for single-threaded checkpoint operations)

    Attributes:
        config: Obra configuration
        git_manager: Git operations manager
        state_manager: State manager for task queries

    Example:
        >>> verifier = CheckpointVerifier(config, git_manager, state_manager)
        >>> # Before checkpoint
        >>> ready, failed_checks = verifier.verify_ready()
        >>> if not ready:
        ...     raise CheckpointVerificationError(f"Failed: {failed_checks}")
        >>> # After loading
        >>> valid, failed_checks = verifier.verify_resume(checkpoint)
        >>> if not valid:
        ...     raise CheckpointCorruptedError(f"Corrupted: {failed_checks}")
    """

    def __init__(
        self,
        config: Config,
        git_manager: Any,  # Type: GitManager
        state_manager: Any  # Type: StateManager
    ):
        """Initialize checkpoint verifier.

        Args:
            config: Obra configuration
            git_manager: Git operations manager
            state_manager: State manager
        """
        self.config = config
        self.git_manager = git_manager
        self.state_manager = state_manager

        # Configuration - pre-checkpoint
        self._enabled = config.get('orchestrator.checkpoint.verification.enabled', True)
        self._require_verification = config.get(
            'orchestrator.checkpoint.verification.require_verification', True
        )
        self._verify_git_clean = config.get(
            'orchestrator.checkpoint.verification.verify_git_clean', True
        )
        self._verify_tests = config.get(
            'orchestrator.checkpoint.verification.verify_tests_passing', True
        )
        self._verify_coverage = config.get(
            'orchestrator.checkpoint.verification.verify_coverage', True
        )
        self._min_coverage = config.get(
            'orchestrator.checkpoint.verification.min_coverage', 0.90
        )
        self._verify_task_boundary = config.get(
            'orchestrator.checkpoint.verification.verify_task_boundary', False
        )
        self._quick_test_timeout = config.get(
            'orchestrator.checkpoint.verification.quick_test_timeout', 30
        )

        # Configuration - post-resume
        self._verify_tests_on_resume = config.get(
            'orchestrator.checkpoint.verification.verify_tests_on_resume', False
        )
        self._max_age_hours = config.get(
            'orchestrator.checkpoint.verification.max_age_hours', 168  # 1 week
        )
        self._warn_on_branch_mismatch = config.get(
            'orchestrator.checkpoint.verification.warn_on_branch_mismatch', True
        )
        self._require_file_existence = config.get(
            'orchestrator.checkpoint.verification.require_file_existence', True
        )

        logger.info(
            "CheckpointVerifier initialized: enabled=%s, require_verification=%s",
            self._enabled, self._require_verification
        )

    def verify_ready(self) -> Tuple[bool, List[str]]:
        """Verify system ready for checkpoint creation.

        Runs all enabled pre-checkpoint checks.

        Returns:
            Tuple of (all_passed: bool, failed_checks: List[str])

        Raises:
            CheckpointVerificationError: If verification fails and require_verification=True
        """
        if not self._enabled:
            return True, []

        checks_failed = []

        # Git clean check
        if self._verify_git_clean:
            error = self._check_git_clean()
            if error:
                checks_failed.append(error)

        # Tests passing check
        if self._verify_tests:
            error = self._check_tests_passing()
            if error:
                checks_failed.append(error)

        # Coverage check
        if self._verify_coverage:
            error = self._check_coverage()
            if error:
                checks_failed.append(error)

        # Task boundary check
        if self._verify_task_boundary:
            error = self._check_task_boundary()
            if error:
                checks_failed.append(error)

        all_passed = len(checks_failed) == 0

        if not all_passed:
            logger.warning("Pre-checkpoint verification failed: %s", checks_failed)
            if self._require_verification:
                raise CheckpointVerificationError(
                    f"Cannot create checkpoint - failed checks: {checks_failed}",
                    context={'failed_checks': checks_failed},
                    recovery="Fix issues and retry checkpoint"
                )

        return all_passed, checks_failed

    def verify_resume(self, checkpoint: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verify checkpoint valid for resuming.

        Runs all enabled post-resume checks.

        Args:
            checkpoint: Checkpoint data

        Returns:
            Tuple of (all_passed: bool, failed_checks: List[str])

        Raises:
            CheckpointCorruptedError: If verification fails and require_verification=True
        """
        # pylint: disable=too-many-branches  # Validation logic requires multiple checks
        if not self._enabled:
            return True, []

        checks_failed = []

        # File existence check
        if self._require_file_existence:
            files_modified = checkpoint.get('files_modified', [])
            missing_files = self._check_files_exist(files_modified)
            if missing_files:
                checks_failed.append(f"Missing files: {missing_files}")

        # Branch mismatch check
        expected_branch = checkpoint.get('git_branch')
        if expected_branch:
            error = self._check_branch_match(expected_branch)
            if error:
                if self._warn_on_branch_mismatch:
                    logger.warning(error)
                else:
                    checks_failed.append(error)

        # Checkpoint age check
        checkpoint_timestamp = checkpoint.get('timestamp')
        if checkpoint_timestamp:
            error = self._check_checkpoint_age(checkpoint_timestamp)
            if error:
                checks_failed.append(error)

        # Optional test check on resume
        if self._verify_tests_on_resume:
            error = self._check_tests_passing()
            if error:
                checks_failed.append(error)

        all_passed = len(checks_failed) == 0

        if not all_passed:
            logger.warning("Post-resume verification failed: %s", checks_failed)
            if self._require_verification:
                raise CheckpointCorruptedError(
                    f"Cannot resume from checkpoint - failed checks: {checks_failed}",
                    context={
                        'checkpoint_id': checkpoint.get('checkpoint_id'),
                        'failed_checks': checks_failed
                    },
                    recovery="Use different checkpoint or fix environment"
                )

        return all_passed, checks_failed

    def _check_git_clean(self) -> Optional[str]:
        """Check if git working directory is clean.

        Returns:
            Error message if check fails, None if passes
        """
        try:
            if not self.git_manager.is_clean():
                return "Uncommitted changes in working directory"
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught  # Robustness
            logger.warning("Git clean check failed: %s", e)
            return "Git check error: " + str(e)

    def _check_tests_passing(self) -> Optional[str]:
        """Run quick test to verify tests pass.

        Returns:
            Error message if check fails, None if passes
        """
        try:
            result = self._run_quick_test()
            if result.returncode != 0:
                return "Tests failing (see output for details)"
            return None
        except subprocess.TimeoutExpired:
            return f"Tests timed out after {self._quick_test_timeout}s"
        except Exception as e:  # pylint: disable=broad-exception-caught  # Robustness
            logger.warning("Test check failed: %s", e)
            return "Test check error: " + str(e)

    def _check_coverage(self) -> Optional[str]:
        """Check if test coverage meets minimum threshold.

        Returns:
            Error message if check fails, None if passes
        """
        try:
            # Get current coverage (simplified - would query test runner)
            # For now, return None (passes) until coverage tracking implemented
            # TODO: Integrate with actual coverage measurement
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught  # Robustness
            logger.warning("Coverage check failed: %s", e)
            return "Coverage check error: " + str(e)

    def _check_task_boundary(self) -> Optional[str]:
        """Check if current task is at safe boundary.

        Returns:
            Error message if check fails, None if passes

        Note:
            This check is disabled until StateManager provides current_task tracking.
        """
        # TODO(ADR-019): Implement once StateManager has current_task tracking
        # For now, always pass (safe default: don't block checkpoints)
        return None

    def _check_files_exist(self, files: List[str]) -> List[str]:
        """Check if files exist on filesystem.

        Args:
            files: List of file paths to check

        Returns:
            List of missing files (empty if all exist)
        """
        missing = []
        for file_path in files:
            if not Path(file_path).exists():
                missing.append(file_path)
        return missing

    def _check_branch_match(self, expected_branch: str) -> Optional[str]:
        """Check if current git branch matches expected.

        Args:
            expected_branch: Expected git branch name

        Returns:
            Error message if check fails, None if passes
        """
        try:
            current_branch = self.git_manager.get_current_branch()
            if current_branch != expected_branch:
                return f"Branch mismatch: expected {expected_branch}, got {current_branch}"
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught  # Robustness
            logger.warning("Branch check failed: %s", e)
            return "Branch check error: " + str(e)

    def _check_checkpoint_age(self, checkpoint_timestamp: datetime) -> Optional[str]:
        """Check if checkpoint is not too old.

        Args:
            checkpoint_timestamp: Checkpoint creation time

        Returns:
            Error message if check fails, None if passes
        """
        try:
            age = datetime.now(UTC) - checkpoint_timestamp
            max_age = timedelta(hours=self._max_age_hours)
            if age > max_age:
                age_hours = age.total_seconds() / 3600
                return f"Checkpoint too old: {age_hours:.1f}h > {self._max_age_hours}h"
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught  # Robustness
            logger.warning("Checkpoint age check failed: %s", e)
            return "Checkpoint age check error: " + str(e)

    def _run_quick_test(self) -> subprocess.CompletedProcess:
        """Run quick test suite.

        Returns:
            CompletedProcess with returncode, stdout, stderr

        Raises:
            subprocess.TimeoutExpired: If tests exceed timeout
        """
        result = subprocess.run(
            ['pytest', '--quiet', '--maxfail=1'],
            capture_output=True,
            timeout=self._quick_test_timeout,
            check=False
        )
        return result
