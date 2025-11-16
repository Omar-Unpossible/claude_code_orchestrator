"""Orchestrator session manager for LLM lifecycle and self-handoff.

This module implements the OrchestratorSessionManager class that manages
Orchestrator LLM lifecycle, including self-handoff when context exceeds threshold.

Example:
    >>> from src.orchestration.session import OrchestratorSessionManager
    >>> session_mgr = OrchestratorSessionManager(config, llm_interface, checkpoint_manager)
    >>> session_mgr.restart_orchestrator_with_checkpoint()

Author: Obra System
Created: 2025-11-15
Version: 1.0.0
"""

import logging
import time
import uuid
from typing import Dict, Any, Optional
from threading import RLock

from src.core.config import Config
from src.core.exceptions import OrchestratorException

logger = logging.getLogger(__name__)


class OrchestratorSessionManager:
    """Manage Orchestrator LLM lifecycle and self-handoff.

    This class handles Orchestrator LLM session management including:
    - Self-handoff when context exceeds threshold (>85%)
    - LLM disconnect and reconnect with checkpoint resume
    - Session state tracking

    Thread-safe: Yes (uses RLock for concurrent access)

    Attributes:
        current_session_id: Unique identifier for current session
        handoff_count: Number of handoffs performed in current Obra session
        last_checkpoint_id: Last checkpoint used for handoff
        config: Obra configuration
        llm_interface: Interface to Orchestrator LLM
        checkpoint_manager: Manages checkpoint creation/loading
        context_manager: Manages Orchestrator context window
        checkpoint_verifier: Verifies checkpoint integrity

    Example:
        >>> config = Config.load("config.yaml")
        >>> session_mgr = OrchestratorSessionManager(
        ...     config=config,
        ...     llm_interface=llm,
        ...     checkpoint_manager=checkpoint_mgr,
        ...     context_manager=context_mgr,
        ...     checkpoint_verifier=verifier
        ... )
        >>> # Trigger handoff when context >85%
        >>> if context_mgr.get_zone() == 'red':
        ...     session_mgr.restart_orchestrator_with_checkpoint()
    """

    def __init__(
        self,
        config: Config,
        llm_interface: Any,  # Type: LocalLLMInterface (future: will have disconnect/connect)
        checkpoint_manager: Any,  # Type: CheckpointManager from ADR-018
        context_manager: Any,  # Type: OrchestratorContextManager from ADR-018
        checkpoint_verifier: Any,  # Type: CheckpointVerifier
        session_metrics_collector: Any = None  # Type: SessionMetricsCollector (ADR-019 Phase 3)
    ):
        """Initialize Orchestrator session manager.

        Args:
            config: Obra configuration
            llm_interface: Interface to Orchestrator LLM
            checkpoint_manager: Checkpoint manager from ADR-018
            context_manager: Context manager from ADR-018
            checkpoint_verifier: Checkpoint integrity verifier
            session_metrics_collector: Optional session metrics collector (ADR-019 Phase 3)

        Raises:
            ValueError: If required config missing
        """
        self.config = config
        self.llm_interface = llm_interface
        self.checkpoint_manager = checkpoint_manager
        self.context_manager = context_manager
        self.checkpoint_verifier = checkpoint_verifier
        self.session_metrics_collector = session_metrics_collector

        # Session state
        self.current_session_id = str(uuid.uuid4())
        self.handoff_count = 0
        self.last_checkpoint_id: Optional[str] = None

        # Thread safety
        self._lock = RLock()

        # Configuration
        self._enabled = config.get('orchestrator.session_continuity.self_handoff.enabled', True)
        self._trigger_zone = config.get('orchestrator.session_continuity.self_handoff.trigger_zone', 'red')
        self._require_task_boundary = config.get(
            'orchestrator.session_continuity.self_handoff.require_task_boundary', True
        )
        self._max_handoffs = config.get(
            'orchestrator.session_continuity.self_handoff.max_handoffs_per_session', 10
        )

        logger.info(
            f"OrchestratorSessionManager initialized: session_id={self.current_session_id}, "
            f"enabled={self._enabled}, trigger_zone={self._trigger_zone}"
        )

    def restart_orchestrator_with_checkpoint(
        self,
        checkpoint_id: Optional[str] = None
    ) -> Optional[str]:
        """Restart Orchestrator LLM with checkpoint context.

        Performs complete self-handoff workflow:
        1. Verify ready for checkpoint (git clean, tests pass, etc.)
        2. Create checkpoint (or use provided checkpoint_id)
        3. Disconnect current LLM
        4. Reconnect to fresh LLM instance
        5. Load checkpoint context into new instance

        Args:
            checkpoint_id: Optional checkpoint to load. If None, creates new checkpoint.

        Returns:
            Checkpoint ID used for restart

        Raises:
            OrchestratorException: If LLM restart fails after retries
            CheckpointVerificationError: If pre-handoff verification fails
                (only if checkpoint.verification.require_verification=True)

        Example:
            >>> # Automatic handoff at threshold
            >>> if context_manager.get_zone() == 'red':
            ...     checkpoint_id = session_manager.restart_orchestrator_with_checkpoint()
            ...     print(f"Handoff complete: {checkpoint_id}")
        """
        with self._lock:
            # Check if enabled
            if not self._enabled:
                logger.warning("Self-handoff disabled - skipping restart")
                return None

            # Check max handoffs limit
            if self.handoff_count >= self._max_handoffs:
                raise OrchestratorException(
                    f"Maximum handoffs reached: {self.handoff_count}/{self._max_handoffs}",
                    context={'session_id': self.current_session_id},
                    recovery="Restart Obra to reset handoff counter"
                )

            logger.info(
                f"Starting Orchestrator self-handoff (handoff {self.handoff_count + 1}/"
                f"{self._max_handoffs})"
            )

            # Step 1: Verify ready for checkpoint
            if checkpoint_id is None:
                ready, checks_failed = self.checkpoint_verifier.verify_ready()
                if not ready:
                    logger.warning(f"Pre-handoff verification failed: {checks_failed}")
                    # CheckpointVerifier will raise if require_verification=True

            # Step 2: Create checkpoint
            if checkpoint_id is None:
                checkpoint_id = self.checkpoint_manager.create_checkpoint(
                    trigger='self_handoff_threshold',
                    metadata={
                        'session_id': self.current_session_id,
                        'handoff_count': self.handoff_count,
                        'context_usage': self.context_manager.get_usage_percentage(),
                        'zone': self.context_manager.get_zone()
                    }
                )
                logger.info(f"Checkpoint created: {checkpoint_id}")

            # ADR-019 Phase 3: Generate session summary before handoff
            if self.session_metrics_collector and self.session_metrics_collector.enabled:
                try:
                    # Record handoff event
                    context_usage = self.context_manager.get_usage_percentage()
                    self.session_metrics_collector.record_handoff(checkpoint_id, context_usage)

                    # Generate and log summary
                    if self.session_metrics_collector.summary_on_handoff:
                        summary = self.session_metrics_collector.generate_session_summary()
                        logger.info(f"Session summary before handoff:\n{summary}")

                    # Reset metrics for new session
                    self.session_metrics_collector.reset_session()
                except Exception as e:
                    logger.warning(f"Failed to generate session summary: {e}")

            # Step 3: Disconnect current LLM
            self._disconnect_llm()

            # Step 4: Load checkpoint context
            checkpoint_context = self._load_checkpoint_context(checkpoint_id)

            # Step 5: Reconnect to fresh LLM
            self._reconnect_llm()

            # Step 6: Inject checkpoint context
            self.context_manager.load_from_checkpoint(checkpoint_context)

            # Update state
            self.handoff_count += 1
            self.last_checkpoint_id = checkpoint_id
            self.current_session_id = str(uuid.uuid4())

            logger.info(
                f"Orchestrator self-handoff complete: checkpoint={checkpoint_id}, "
                f"new_session={self.current_session_id}, handoff_count={self.handoff_count}"
            )

            return checkpoint_id

    def _disconnect_llm(self) -> None:
        """Disconnect current Orchestrator LLM instance.

        Cleanly disconnects from current LLM, saving any pending state.
        Retries on failure with exponential backoff.

        Raises:
            OrchestratorException: If disconnect fails after retries
        """
        max_retries = 3
        backoff_seconds = 1

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Disconnecting Orchestrator LLM (attempt {attempt}/{max_retries})")
                self.llm_interface.disconnect()
                logger.info("Orchestrator LLM disconnected successfully")
                return
            except Exception as e:
                if attempt == max_retries:
                    raise OrchestratorException(
                        f"Failed to disconnect Orchestrator LLM after {max_retries} attempts",
                        context={'error': str(e), 'session_id': self.current_session_id},
                        recovery="Check LLM interface health and retry"
                    ) from e
                logger.warning(
                    f"Disconnect attempt {attempt} failed: {e}, retrying in {backoff_seconds}s"
                )
                time.sleep(backoff_seconds)
                backoff_seconds *= 2  # Exponential backoff

    def _reconnect_llm(self) -> None:
        """Reconnect to fresh Orchestrator LLM instance.

        Connects to new LLM instance with fresh context window.
        Retries on failure with exponential backoff.

        Raises:
            OrchestratorException: If reconnect fails after retries
        """
        max_retries = 3
        backoff_seconds = 1

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Reconnecting to Orchestrator LLM (attempt {attempt}/{max_retries})")
                self.llm_interface.connect()
                # Verify connection
                if not self.llm_interface.is_connected():
                    raise ConnectionError("LLM interface reports not connected")
                logger.info("Orchestrator LLM reconnected successfully")
                return
            except Exception as e:
                if attempt == max_retries:
                    raise OrchestratorException(
                        f"Failed to reconnect to Orchestrator LLM after {max_retries} attempts",
                        context={'error': str(e), 'session_id': self.current_session_id},
                        recovery="Check LLM service availability and network connectivity"
                    ) from e
                logger.warning(
                    f"Reconnect attempt {attempt} failed: {e}, retrying in {backoff_seconds}s"
                )
                time.sleep(backoff_seconds)
                backoff_seconds *= 2  # Exponential backoff

    def _load_checkpoint_context(self, checkpoint_id: str) -> Dict[str, Any]:
        """Load checkpoint and extract context for fresh LLM.

        Args:
            checkpoint_id: Checkpoint to load

        Returns:
            Context dictionary ready for injection into fresh LLM

        Raises:
            CheckpointCorruptedError: If checkpoint data invalid or corrupted
        """
        logger.info(f"Loading checkpoint context: {checkpoint_id}")

        # Load checkpoint from CheckpointManager
        checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_id)

        # Post-resume verification (handled by CheckpointManager calling CheckpointVerifier)

        # Extract context snapshot
        context_snapshot = checkpoint.get('context_snapshot', {})

        # Build context for fresh LLM
        context = {
            'checkpoint_id': checkpoint_id,
            'timestamp': checkpoint.get('timestamp'),
            'working_memory': context_snapshot.get('working_memory'),
            'session_memory': context_snapshot.get('session_memory'),
            'episodic_memory': context_snapshot.get('episodic_memory'),
            'resume_instructions': checkpoint.get('resume_instructions', {}),
            'metadata': checkpoint.get('metadata', {})
        }

        logger.info(
            f"Checkpoint context loaded: {len(context.get('working_memory', []))} operations, "
            f"session_memory={len(str(context.get('session_memory', '')))} chars"
        )

        return context

    def get_handoff_count(self) -> int:
        """Get number of handoffs performed in current Obra session.

        Returns:
            Handoff count
        """
        with self._lock:
            return self.handoff_count

    def get_current_session_id(self) -> str:
        """Get current Orchestrator session ID.

        Returns:
            Session ID (UUID)
        """
        with self._lock:
            return self.current_session_id

    def get_last_checkpoint_id(self) -> Optional[str]:
        """Get last checkpoint ID used for handoff.

        Returns:
            Checkpoint ID or None if no handoffs yet
        """
        with self._lock:
            return self.last_checkpoint_id
