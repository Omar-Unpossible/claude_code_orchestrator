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
from src.orchestration.session.checkpoint_verifier import (
    CheckpointVerifier,
    CheckpointVerificationError,
    CheckpointCorruptedError
)
from src.orchestration.session.decision_record_generator import (
    DecisionRecordGenerator,
    DecisionRecord
)
from src.orchestration.session.progress_reporter import (
    ProgressReporter,
    ProgressReport
)
from src.orchestration.session.session_metrics_collector import SessionMetricsCollector

__all__ = [
    'OrchestratorSessionManager',
    'CheckpointVerifier',
    'CheckpointVerificationError',
    'CheckpointCorruptedError',
    'DecisionRecordGenerator',
    'DecisionRecord',
    'ProgressReporter',
    'ProgressReport',
    'SessionMetricsCollector',
]
