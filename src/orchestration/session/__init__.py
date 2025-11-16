"""Session continuity components for Orchestrator LLM.

This package provides session management and continuity features:
- OrchestratorSessionManager: LLM lifecycle and self-handoff
- CheckpointVerifier: Pre/post checkpoint integrity validation
- DecisionRecordGenerator: Automated ADR-format decision records
- ProgressReporter: Structured JSON progress reporting
- SessionMetricsCollector: Session pattern tracking

Example:
    >>> from src.orchestration.session import OrchestratorSessionManager
    >>> session_mgr = OrchestratorSessionManager(config, llm_interface, checkpoint_manager)
    >>> session_mgr.restart_orchestrator_with_checkpoint()
"""

from src.orchestration.session.orchestrator_session_manager import OrchestratorSessionManager
from src.orchestration.session.checkpoint_verifier import CheckpointVerifier

__all__ = [
    'OrchestratorSessionManager',
    'CheckpointVerifier',
]
