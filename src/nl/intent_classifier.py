"""Intent Classification for Natural Language Commands.

This module provides intent classification to determine whether a user message
is a COMMAND (execute action), QUESTION (request information), or requires
CLARIFICATION (ambiguous/incomplete).

Classes:
    IntentResult: Dataclass holding classification results
    IntentClassifier: LLM-based intent classifier

Example:
    >>> from plugins.ollama import OllamaLLMPlugin
    >>> llm = OllamaLLMPlugin()
    >>> llm.initialize({'model': 'qwen2.5-coder:32b'})
    >>> classifier = IntentClassifier(llm, confidence_threshold=0.7)
    >>> result = classifier.classify("Create an epic called User Auth")
    >>> print(result.intent)
    'COMMAND'
    >>> print(result.confidence)
    0.95
"""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Literal
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from plugins.base import LLMPlugin
from core.exceptions import OrchestratorException
from src.core.metrics import get_metrics_collector

logger = logging.getLogger(__name__)


class IntentClassificationException(OrchestratorException):
    """Exception raised when intent classification fails."""
    pass


@dataclass
class IntentResult:
    """Result of intent classification.

    Attributes:
        intent: Classification result (COMMAND, QUESTION, or CLARIFICATION_NEEDED)
        confidence: Confidence score from 0.0 to 1.0
        reasoning: Brief explanation of why this classification was chosen
        detected_entities: Dictionary of entities detected in the message
    """
    intent: Literal['COMMAND', 'QUESTION', 'CLARIFICATION_NEEDED']
    confidence: float
    reasoning: str = ""
    detected_entities: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate confidence score."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


class IntentClassifier:
    """LLM-based intent classifier for natural language messages.

    Uses a prompt template and LLM to classify user intent as:
    - COMMAND: User wants to execute an action
    - QUESTION: User wants information or explanation
    - CLARIFICATION_NEEDED: Message is ambiguous or incomplete

    The classifier is plugin-agnostic and works with any LLM that implements
    the LLMPlugin interface (Ollama, OpenAI, Claude, etc.).

    Args:
        llm_plugin: LLM provider implementing LLMPlugin interface
        confidence_threshold: Minimum confidence for COMMAND/QUESTION (default 0.7)
            Below this threshold, returns CLARIFICATION_NEEDED
        template_path: Path to Jinja2 template directory (default: prompts/)

    Example:
        >>> classifier = IntentClassifier(llm_plugin, confidence_threshold=0.7)
        >>> result = classifier.classify(
        ...     "Create an epic for user authentication",
        ...     context={'project_id': 1}
        ... )
        >>> if result.intent == 'COMMAND':
        ...     # Execute command
        ...     pass
        >>> elif result.intent == 'QUESTION':
        ...     # Forward to Claude Code for informational response
        ...     pass
        >>> else:
        ...     # Ask user for clarification
        ...     pass
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        confidence_threshold: float = 0.7,
        template_path: Optional[Path] = None
    ):
        """Initialize intent classifier.

        Args:
            llm_plugin: LLM provider for classification
            confidence_threshold: Minimum confidence for definitive classification
            template_path: Path to prompt templates (default: prompts/)

        Raises:
            ValueError: If confidence_threshold not in [0.0, 1.0]
            IntentClassificationException: If template not found
        """
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be between 0.0 and 1.0, got {confidence_threshold}"
            )

        self.llm_plugin = llm_plugin
        self.confidence_threshold = confidence_threshold

        # Set up Jinja2 template environment
        if template_path is None:
            # Default to prompts/ directory relative to project root
            template_path = Path(__file__).parent.parent.parent / 'prompts'

        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(template_path)),
                trim_blocks=True,
                lstrip_blocks=True
            )
            # Verify template exists
            self.template = self.jinja_env.get_template('intent_classification.j2')
        except TemplateNotFound as e:
            raise IntentClassificationException(
                f"Intent classification template not found: {e}",
                context={'template_path': str(template_path)},
                recovery="Ensure prompts/intent_classification.j2 exists"
            )

        logger.info(
            f"IntentClassifier initialized with threshold={confidence_threshold}, "
            f"template_path={template_path}"
        )

    def classify(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> IntentResult:
        """Classify user message intent.

        Args:
            message: User's natural language message
            context: Optional conversation context with:
                - previous_turns: List of previous message exchanges
                - current_epic_id: Active epic ID (for pronoun resolution)
                - current_story_id: Active story ID

        Returns:
            IntentResult with classification, confidence, and detected entities

        Raises:
            IntentClassificationException: If LLM fails or returns invalid response

        Example:
            >>> result = classifier.classify("Create an epic called User Auth")
            >>> print(f"{result.intent} (confidence: {result.confidence})")
            COMMAND (confidence: 0.95)
        """
        metrics = get_metrics_collector()
        start = time.time()

        if not message or not message.strip():
            return IntentResult(
                intent='CLARIFICATION_NEEDED',
                confidence=0.0,
                reasoning="Empty message",
                detected_entities={}
            )

        # Render prompt from template
        try:
            prompt = self.template.render(
                user_message=message,
                context=context or {}
            )
        except Exception as e:
            raise IntentClassificationException(
                f"Failed to render intent classification template: {e}",
                context={'message': message},
                recovery="Check template syntax in prompts/intent_classification.j2"
            )

        # Call LLM
        try:
            logger.debug(f"Classifying intent for message: {message[:100]}...")
            response = self.llm_plugin.generate(
                prompt,
                temperature=0.1,  # Very low for classification
                max_tokens=100,  # Reduced from 500 (JSON output is small)
                stop=["\n```", "}\n", "}\r\n"]  # Stop after JSON closes
            )
        except Exception as e:
            raise IntentClassificationException(
                f"LLM generation failed during intent classification: {e}",
                context={'message': message},
                recovery="Check LLM plugin is available and healthy"
            )

        # Parse JSON response
        try:
            result_data = self._parse_llm_response(response)
        except Exception as e:
            raise IntentClassificationException(
                f"Failed to parse LLM response: {e}",
                context={'response': response[:500]},
                recovery="LLM may not be following JSON output format"
            )

        # Apply confidence threshold
        intent = result_data['intent']
        confidence = result_data['confidence']

        if confidence < self.confidence_threshold:
            logger.info(
                f"Confidence {confidence} below threshold {self.confidence_threshold}, "
                f"requesting clarification"
            )
            intent = 'CLARIFICATION_NEEDED'

        result = IntentResult(
            intent=intent,
            confidence=confidence,
            reasoning=result_data.get('reasoning', ''),
            detected_entities=result_data.get('detected_entities', {})
        )

        logger.info(
            f"Classified as {result.intent} with confidence {result.confidence:.2f}"
        )

        # Record metrics BEFORE return
        latency_ms = (time.time() - start) * 1000
        metrics.record_llm_request(
            provider='ollama',
            latency_ms=latency_ms,
            success=True,
            model=self.llm_plugin.model if hasattr(self.llm_plugin, 'model') else 'unknown'
        )

        return result

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM JSON response.

        Handles various response formats:
        - Pure JSON
        - JSON wrapped in markdown code blocks
        - JSON with surrounding text

        Args:
            response: Raw LLM response

        Returns:
            Parsed JSON data as dictionary

        Raises:
            ValueError: If response is not valid JSON or missing required fields
        """
        # Strip whitespace
        response = response.strip()

        # Remove markdown code blocks if present
        if response.startswith('```'):
            # Find JSON content between ```json and ```
            lines = response.split('\n')
            json_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if in_code_block or (not json_lines and line.strip().startswith('{')):
                    json_lines.append(line)
            response = '\n'.join(json_lines)

        # Try to find JSON object in response
        try:
            # Find first '{' and last '}'
            start = response.index('{')
            end = response.rindex('}') + 1
            json_str = response[start:end]
            data = json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        # Validate required fields
        required_fields = ['intent', 'confidence']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields in response: {missing_fields}")

        # Validate intent value
        valid_intents = ['COMMAND', 'QUESTION', 'CLARIFICATION_NEEDED']
        if data['intent'] not in valid_intents:
            raise ValueError(
                f"Invalid intent value: {data['intent']}. "
                f"Must be one of {valid_intents}"
            )

        # Validate confidence is a number
        try:
            data['confidence'] = float(data['confidence'])
        except (ValueError, TypeError):
            raise ValueError(f"Confidence must be a number, got: {data['confidence']}")

        return data
