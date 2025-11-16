"""Decision record generator for automated ADR creation.

This module implements the DecisionRecordGenerator class that automatically
generates privacy-compliant decision records in ADR format from orchestration
decisions.

Example:
    >>> from src.orchestration.session import DecisionRecordGenerator
    >>> generator = DecisionRecordGenerator(config, state_manager)
    >>> action = Action(type='proceed', confidence=0.9, ...)
    >>> if generator.is_significant(action):
    ...     dr = generator.generate_decision_record(action, context)
    ...     generator.save_decision_record(dr)

Author: Obra System
Created: 2025-11-15
Version: 1.0.0
"""

import logging
import re
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List

from src.core.config import Config
from src.core.state import StateManager
from src.core.exceptions import OrchestratorException


logger = logging.getLogger(__name__)


# Privacy: Reasoning indicators to remove
REASONING_INDICATORS = [
    r'\bI think\b',
    r'\bI believe\b',
    r'\bLet me consider\b',
    r'\bLet\'s analyze\b',
    r'\bMy reasoning is\b',
    r'\bMy thought process\b',
    r'\bIn my opinion\b',
    r'\bIt seems to me\b',
    r'\bFrom my perspective\b',
]

# Privacy: Secret patterns to redact
SECRET_PATTERNS = [
    (r'\b[A-Za-z0-9]{32,}\b', '[REDACTED_KEY]'),  # API keys
    (r'sk-[A-Za-z0-9]{48}', '[REDACTED_OPENAI_KEY]'),  # OpenAI keys
    (r'Bearer [A-Za-z0-9\-._~+/]+=*', '[REDACTED_TOKEN]'),  # Bearer tokens
    (r'password\s+is\s+"([^"]+)"', r'password is "[REDACTED]"'),  # Passwords with "is"
    (r'password\s*[:=]\s*"([^"]+)"', r'password="[REDACTED]"'),  # Passwords with : or =
]


class DecisionRecord:
    """Represents a decision record in ADR format.

    Attributes:
        dr_id: Decision record ID (DR-YYYYMMDD-NNN)
        timestamp: When decision was made
        context: Problem context (sanitized)
        decision: What was decided
        consequences: Expected outcomes
        alternatives: Alternatives considered
        confidence: Decision confidence (0.0-1.0)
        metadata: Additional metadata
    """

    def __init__(
        self,
        dr_id: str,
        timestamp: datetime,
        context: str,
        decision: str,
        consequences: List[str],
        alternatives: List[str],
        confidence: float,
        metadata: Dict[str, Any]
    ):
        """Initialize decision record."""
        self.dr_id = dr_id
        self.timestamp = timestamp
        self.context = context
        self.decision = decision
        self.consequences = consequences
        self.alternatives = alternatives
        self.confidence = confidence
        self.metadata = metadata

    def to_markdown(self) -> str:
        """Generate ADR-format markdown.

        Returns:
            Markdown string in ADR format
        """
        md = f"# {self.dr_id}: Orchestrator Decision Record\n\n"
        md += f"**Status**: Decided | **Date**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        md += f"**Confidence**: {self.confidence:.2f}\n\n"

        md += "## Context\n\n"
        md += f"{self.context}\n\n"

        md += "## Decision\n\n"
        md += f"{self.decision}\n\n"

        md += "## Consequences\n\n"
        for consequence in self.consequences:
            md += f"- {consequence}\n"
        md += "\n"

        if self.alternatives:
            md += "## Alternatives Considered\n\n"
            for alt in self.alternatives:
                md += f"- {alt}\n"
            md += "\n"

        md += "## Metadata\n\n"
        for key, value in self.metadata.items():
            md += f"- **{key}**: {value}\n"

        return md

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'dr_id': self.dr_id,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'decision': self.decision,
            'consequences': self.consequences,
            'alternatives': self.alternatives,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


class DecisionRecordGenerator:
    """Generate privacy-compliant decision records in ADR format.

    This class automatically generates decision records from orchestration
    actions, ensuring privacy compliance by sanitizing reasoning indicators
    and redacting secrets.

    Thread-safe: No (designed for single-threaded decision recording)

    Attributes:
        config: Obra configuration
        state_manager: State manager for context
        enabled: Whether DR generation is enabled
        significance_threshold: Confidence threshold for recording (0.7)
        output_dir: Directory for decision records

    Example:
        >>> generator = DecisionRecordGenerator(config, state_manager)
        >>> action = engine.decide_next_action(context)
        >>> if generator.is_significant(action):
        ...     dr = generator.generate_decision_record(action, context)
        ...     generator.save_decision_record(dr)
    """

    def __init__(self, config: Config, state_manager: StateManager):
        """Initialize decision record generator.

        Args:
            config: Obra configuration
            state_manager: State manager
        """
        self.config = config
        self.state_manager = state_manager

        # Configuration
        self.enabled = config.get(
            'orchestrator.session_continuity.decision_logging.enabled', True
        )
        self.significance_threshold = config.get(
            'orchestrator.session_continuity.decision_logging.significance_threshold', 0.7
        )
        self.output_dir = Path(config.get(
            'orchestrator.session_continuity.decision_logging.output_dir',
            'docs/decisions/session_decisions'
        ))

        # Counter for DR IDs
        self._dr_counter = 0

        # Ensure output directory exists
        if self.enabled:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "DecisionRecordGenerator initialized: enabled=%s, threshold=%.2f",
            self.enabled, self.significance_threshold
        )

    def is_significant(self, action: Any) -> bool:
        """Check if action is significant enough to record.

        Args:
            action: Action object from DecisionEngine

        Returns:
            True if action should be recorded
        """
        if not self.enabled:
            return False

        # Significant if confidence meets threshold
        return action.confidence >= self.significance_threshold

    def generate_decision_record(
        self,
        action: Any,  # Type: Action from DecisionEngine
        context: Dict[str, Any]
    ) -> DecisionRecord:
        """Generate decision record from action and context.

        Args:
            action: Action object with type, confidence, explanation
            context: Decision context (task, response, validation, etc.)

        Returns:
            DecisionRecord object

        Raises:
            OrchestratorException: If DR generation fails
        """
        try:
            # Generate DR ID
            dr_id = self._generate_dr_id()

            # Extract and sanitize components
            context_str = self._extract_context(context)
            decision_str = self._extract_decision(action)
            consequences = self._extract_consequences(action, context)
            alternatives = self._extract_alternatives(context)

            # Create decision record
            task = context.get('task')
            task_id = getattr(task, 'id', None) if task else None

            dr = DecisionRecord(
                dr_id=dr_id,
                timestamp=action.timestamp,
                context=context_str,
                decision=decision_str,
                consequences=consequences,
                alternatives=alternatives,
                confidence=action.confidence,
                metadata={
                    'action_type': action.type,
                    'task_id': task_id,
                    'session_id': context.get('session_id'),
                }
            )

            logger.info("Generated decision record: %s (confidence=%.2f)", dr_id, action.confidence)

            return dr

        except Exception as e:
            raise OrchestratorException(
                f"Failed to generate decision record: {e}",
                context={'action_type': action.type, 'error': str(e)},
                recovery="Check decision context and try again"
            ) from e

    def save_decision_record(self, dr: DecisionRecord) -> Path:
        """Save decision record to file.

        Args:
            dr: DecisionRecord to save

        Returns:
            Path where DR was saved

        Raises:
            OrchestratorException: If save fails
        """
        try:
            # Generate filename
            filename = f"{dr.dr_id}.md"
            filepath = self.output_dir / filename

            # Write markdown
            markdown = dr.to_markdown()
            filepath.write_text(markdown, encoding='utf-8')

            logger.info("Saved decision record: %s", filepath)

            return filepath

        except Exception as e:
            raise OrchestratorException(
                f"Failed to save decision record: {e}",
                context={'dr_id': dr.dr_id, 'error': str(e)},
                recovery="Check file permissions and disk space"
            ) from e

    def _generate_dr_id(self) -> str:
        """Generate unique decision record ID.

        Returns:
            DR ID in format DR-YYYYMMDD-NNN
        """
        self._dr_counter += 1
        date_str = datetime.now(UTC).strftime('%Y%m%d')
        return f"DR-{date_str}-{self._dr_counter:03d}"

    def _extract_context(self, context: Dict[str, Any]) -> str:
        """Extract and sanitize problem context.

        Args:
            context: Decision context

        Returns:
            Sanitized context string
        """
        parts = []

        # Task context
        task = context.get('task')
        if task:
            task_title = getattr(task, 'title', 'Unknown task')
            parts.append(f"Task: {task_title}")

        # Validation context
        validation = context.get('validation_result', {})
        if validation:
            is_complete = validation.get('complete', False)
            is_valid = validation.get('valid', False)
            parts.append(f"Validation: complete={is_complete}, valid={is_valid}")

        # Quality context
        quality_score = context.get('quality_score')
        if quality_score is not None:
            parts.append(f"Quality score: {quality_score:.2f}")

        context_str = "\n".join(parts) if parts else "Decision made in orchestration workflow."

        # Sanitize
        return self._sanitize_text(context_str)

    def _extract_decision(self, action: Any) -> str:
        """Extract and sanitize decision.

        Args:
            action: Action object

        Returns:
            Sanitized decision string
        """
        decision = f"Action: {action.type}\n\n{action.explanation}"

        # Sanitize
        return self._sanitize_text(decision)

    def _extract_consequences(
        self,
        action: Any,
        context: Dict[str, Any]
    ) -> List[str]:
        """Extract expected consequences.

        Args:
            action: Action object
            context: Decision context

        Returns:
            List of consequence strings
        """
        consequences = []

        # Action-specific consequences
        if action.type == 'proceed':
            consequences.append("Task marked as complete and moves to next in queue")
        elif action.type == 'escalate':
            consequences.append("Human intervention requested via breakpoint")
        elif action.type == 'retry':
            consequences.append("Task retried with modifications")
        elif action.type == 'clarify':
            consequences.append("Additional information requested from user")
        elif action.type == 'checkpoint':
            consequences.append("Checkpoint created before proceeding")

        # Confidence-based consequence
        if action.confidence < 0.6:
            consequences.append(f"Low confidence ({action.confidence:.2f}) may indicate ambiguity")
        elif action.confidence >= 0.9:
            consequences.append(f"High confidence ({action.confidence:.2f}) indicates clear path forward")

        return consequences

    def _extract_alternatives(self, context: Dict[str, Any]) -> List[str]:
        """Extract alternatives considered.

        Args:
            context: Decision context

        Returns:
            List of alternative strings
        """
        alternatives = []

        # Extract from metadata if available
        metadata = context.get('metadata', {})
        if 'alternatives' in metadata:
            alternatives = metadata['alternatives']

        return alternatives

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text for privacy compliance.

        Removes reasoning indicators and redacts secrets.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        # Remove reasoning indicators
        for pattern in REASONING_INDICATORS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Redact secrets
        for pattern, replacement in SECRET_PATTERNS:
            text = re.sub(pattern, replacement, text)

        # Clean up extra whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = text.strip()

        return text
