"""Entity Extraction for Natural Language Commands.

This module provides schema-aware entity extraction from natural language,
converting user commands into structured work item data (epic, story, task, subtask).

Classes:
    ExtractedEntities: Dataclass holding extraction results
    EntityExtractor: LLM-based entity extractor with Obra schema awareness

Example:
    >>> from plugins.ollama import OllamaLLMPlugin
    >>> llm = OllamaLLMPlugin()
    >>> llm.initialize({'model': 'qwen2.5-coder:32b'})
    >>> extractor = EntityExtractor(llm, schema_path='src/nl/schemas/obra_schema.json')
    >>> result = extractor.extract(
    ...     "Create an epic called User Auth with OAuth support",
    ...     intent="COMMAND"
    ... )
    >>> print(result.entity_type)
    'epic'
    >>> print(result.entities[0]['title'])
    'User Auth'
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Literal
from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from plugins.base import LLMPlugin
from core.exceptions import OrchestratorException

logger = logging.getLogger(__name__)


class EntityExtractionException(OrchestratorException):
    """Exception raised when entity extraction fails."""
    pass


@dataclass
class ExtractedEntities:
    """Result of entity extraction.

    Attributes:
        entity_type: Type of work item (epic, story, task, subtask, milestone)
        entities: List of extracted entity dictionaries with work item properties
        confidence: Confidence score from 0.0 to 1.0
        reasoning: Brief explanation of extraction decisions
    """
    entity_type: Literal['epic', 'story', 'task', 'subtask', 'milestone']
    entities: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""

    def __post_init__(self):
        """Validate confidence score and entity type."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        valid_types = ['epic', 'story', 'task', 'subtask', 'milestone']
        if self.entity_type not in valid_types:
            raise ValueError(
                f"entity_type must be one of {valid_types}, got {self.entity_type}"
            )


class EntityExtractor:
    """LLM-based entity extractor with Obra schema awareness.

    Extracts structured work item data from natural language commands using:
    - Jinja2 prompt template
    - Obra schema JSON for context
    - LLM for intelligent extraction
    - Support for multi-item extraction ("create 3 stories...")

    The extractor is plugin-agnostic and works with any LLM implementing
    the LLMPlugin interface.

    Args:
        llm_plugin: LLM provider implementing LLMPlugin interface
        schema_path: Path to Obra schema JSON file (default: src/nl/schemas/obra_schema.json)
        template_path: Path to Jinja2 template directory (default: prompts/)

    Example:
        >>> extractor = EntityExtractor(llm_plugin)
        >>> result = extractor.extract(
        ...     "Add 3 stories to User Auth epic: login, signup, MFA",
        ...     intent="COMMAND"
        ... )
        >>> print(len(result.entities))
        3
        >>> print(result.entities[0]['title'])
        'Login'
    """

    def __init__(
        self,
        llm_plugin: LLMPlugin,
        schema_path: Optional[Path] = None,
        template_path: Optional[Path] = None
    ):
        """Initialize entity extractor.

        Args:
            llm_plugin: LLM provider for extraction
            schema_path: Path to Obra schema JSON
            template_path: Path to prompt templates

        Raises:
            EntityExtractionException: If schema or template not found
        """
        self.llm_plugin = llm_plugin

        # Load Obra schema
        if schema_path is None:
            schema_path = Path(__file__).parent / 'schemas' / 'obra_schema.json'

        try:
            with open(schema_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
        except FileNotFoundError:
            raise EntityExtractionException(
                f"Obra schema not found: {schema_path}",
                context={'schema_path': str(schema_path)},
                recovery="Ensure src/nl/schemas/obra_schema.json exists"
            )
        except json.JSONDecodeError as e:
            raise EntityExtractionException(
                f"Invalid JSON in Obra schema: {e}",
                context={'schema_path': str(schema_path)},
                recovery="Check schema JSON syntax"
            )

        # Set up Jinja2 template environment
        if template_path is None:
            template_path = Path(__file__).parent.parent.parent / 'prompts'

        try:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(template_path)),
                trim_blocks=True,
                lstrip_blocks=True
            )
            self.template = self.jinja_env.get_template('entity_extraction.j2')
        except TemplateNotFound as e:
            raise EntityExtractionException(
                f"Entity extraction template not found: {e}",
                context={'template_path': str(template_path)},
                recovery="Ensure prompts/entity_extraction.j2 exists"
            )

        logger.info(
            f"EntityExtractor initialized with schema={schema_path}, "
            f"template_path={template_path}"
        )

    def extract(
        self,
        message: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExtractedEntities:
        """Extract structured entities from natural language message.

        Args:
            message: User's natural language command
            intent: Intent type (COMMAND, QUESTION) from IntentClassifier
            context: Optional conversation context with:
                - previous_turns: List of previous message exchanges
                - current_epic_id: Active epic ID
                - current_story_id: Active story ID

        Returns:
            ExtractedEntities with entity_type, entities list, and confidence

        Raises:
            EntityExtractionException: If LLM fails or returns invalid response

        Example:
            >>> result = extractor.extract(
            ...     "Create epic for user authentication",
            ...     intent="COMMAND"
            ... )
            >>> print(result.entity_type)
            'epic'
            >>> print(result.entities[0]['title'])
            'User Authentication'
        """
        if not message or not message.strip():
            raise EntityExtractionException(
                "Cannot extract entities from empty message",
                context={'message': message},
                recovery="Provide non-empty message"
            )

        # Render prompt from template
        try:
            prompt = self.template.render(
                user_message=message,
                intent_type=intent,
                context=context or {},
                schema=self.schema
            )
        except Exception as e:
            raise EntityExtractionException(
                f"Failed to render entity extraction template: {e}",
                context={'message': message},
                recovery="Check template syntax in prompts/entity_extraction.j2"
            )

        # Call LLM
        try:
            logger.debug(f"Extracting entities from message: {message[:100]}...")
            response = self.llm_plugin.generate(
                prompt,
                temperature=0.2,  # Low temperature for consistent extraction
                max_tokens=1000   # Allow for multiple entities
            )
        except Exception as e:
            raise EntityExtractionException(
                f"LLM generation failed during entity extraction: {e}",
                context={'message': message},
                recovery="Check LLM plugin is available and healthy"
            )

        # Parse JSON response
        try:
            result_data = self._parse_llm_response(response)
        except Exception as e:
            raise EntityExtractionException(
                f"Failed to parse LLM response: {e}",
                context={'response': response[:500]},
                recovery="LLM may not be following JSON output format"
            )

        # Validate and create result
        result = ExtractedEntities(
            entity_type=result_data['entity_type'],
            entities=result_data.get('entities', []),
            confidence=result_data.get('confidence', 0.0),
            reasoning=result_data.get('reasoning', '')
        )

        logger.info(
            f"Extracted {len(result.entities)} {result.entity_type}(s) "
            f"with confidence {result.confidence:.2f}"
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
            start = response.index('{')
            end = response.rindex('}') + 1
            json_str = response[start:end]
            data = json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Invalid JSON in LLM response: {e}")

        # Validate required fields
        required_fields = ['entity_type', 'entities']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields in response: {missing_fields}")

        # Validate entity_type
        valid_types = ['epic', 'story', 'task', 'subtask', 'milestone']
        if data['entity_type'] not in valid_types:
            raise ValueError(
                f"Invalid entity_type: {data['entity_type']}. "
                f"Must be one of {valid_types}"
            )

        # Validate entities is a list
        if not isinstance(data['entities'], list):
            raise ValueError(f"entities must be a list, got: {type(data['entities'])}")

        # Validate confidence if present
        if 'confidence' in data:
            try:
                data['confidence'] = float(data['confidence'])
            except (ValueError, TypeError):
                raise ValueError(f"Confidence must be a number, got: {data['confidence']}")

        return data

    def validate_entity(self, entity: Dict[str, Any], entity_type: str) -> bool:
        """Validate entity against schema.

        Args:
            entity: Entity dictionary to validate
            entity_type: Expected entity type (epic, story, task, etc.)

        Returns:
            True if valid, False otherwise

        Note:
            This is a basic validation. Full validation (including FK checks)
            happens in CommandValidator using StateManager.
        """
        # Check required fields based on entity type
        required_fields = {
            'epic': ['title'],
            'story': ['title'],
            'task': ['title'],
            'subtask': ['title', 'parent_task_id'],
            'milestone': ['name', 'required_epic_ids']
        }

        entity_required = required_fields.get(entity_type, [])
        for field in entity_required:
            # For milestones, 'name' is the title field
            check_field = 'title' if field == 'name' and 'title' in entity else field
            if check_field not in entity or not entity[check_field]:
                logger.warning(
                    f"Entity missing required field '{field}': {entity}"
                )
                return False

        return True
