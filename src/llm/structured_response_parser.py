"""Structured response parser for LLM responses with hybrid format validation.

This module provides parsing and validation for LLM responses that combine:
- JSON metadata (structured data in <METADATA> tags)
- Natural language content (explanations in <CONTENT> tags)
- Schema validation against YAML-defined response schemas

The parser handles malformed responses gracefully and provides detailed
validation feedback for debugging and quality assurance.
"""

import json
import logging
import re
from typing import Dict, List, Any, Optional

try:
    import yaml
except ImportError:
    yaml = None  # Optional dependency

from src.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class StructuredResponseParser:
    """Parser for structured LLM responses with hybrid JSON + natural language format.

    The parser expects LLM responses in the following format:

    <METADATA>
    {
      "status": "completed",
      "files_modified": ["/path/to/file.py"],
      "confidence": 0.95
    }
    </METADATA>

    <CONTENT>
    Natural language explanation of the work completed...
    </CONTENT>

    Attributes:
        schemas_file_path: Path to YAML file containing response schemas
        schemas: Dictionary of loaded schemas by type
        _metadata_pattern: Compiled regex for extracting metadata
        _content_pattern: Compiled regex for extracting content

    Example:
        >>> parser = StructuredResponseParser('config/response_schemas.yaml')
        >>> parser.load_schemas()
        >>>
        >>> llm_response = '''
        ... <METADATA>
        ... {"status": "completed", "files_modified": []}
        ... </METADATA>
        ... <CONTENT>
        ... Task completed successfully.
        ... </CONTENT>
        ... '''
        >>>
        >>> parsed = parser.parse_response(
        ...     response=llm_response,
        ...     expected_type='task_execution'
        ... )
        >>>
        >>> if parsed['is_valid']:
        ...     print(f"Status: {parsed['metadata']['status']}")
        ...     print(f"Explanation: {parsed['content']}")
    """

    # Response format patterns
    METADATA_TAG_PATTERN = r'<METADATA>\s*(.*?)\s*</METADATA>'
    CONTENT_TAG_PATTERN = r'<CONTENT>\s*(.*?)\s*</CONTENT>'

    def __init__(self, schemas_file_path: str = 'config/response_schemas.yaml'):
        """Initialize structured response parser.

        Args:
            schemas_file_path: Path to YAML file with response schemas

        Example:
            >>> parser = StructuredResponseParser()
            >>> parser = StructuredResponseParser('custom_schemas.yaml')
        """
        self.schemas_file_path = schemas_file_path
        self.schemas: Dict[str, Any] = {}

        # Compile regex patterns for performance
        self._metadata_pattern = re.compile(
            self.METADATA_TAG_PATTERN,
            re.DOTALL | re.IGNORECASE
        )
        self._content_pattern = re.compile(
            self.CONTENT_TAG_PATTERN,
            re.DOTALL | re.IGNORECASE
        )

        logger.debug(
            f"StructuredResponseParser initialized with schemas: {schemas_file_path}"
        )

    def load_schemas(self) -> None:
        """Load response schemas from YAML file.

        Loads all schema definitions from the configured YAML file and
        stores them in the schemas dictionary for validation.

        Raises:
            ValidationException: If schemas file cannot be loaded or is invalid

        Example:
            >>> parser = StructuredResponseParser()
            >>> parser.load_schemas()
            >>> print(parser.schemas.keys())
            dict_keys(['task_execution', 'validation', 'error_analysis', ...])
        """
        if yaml is None:
            raise ValidationException(
                "YAML library not available",
                context={'schemas_file': self.schemas_file_path},
                recovery="Install PyYAML: pip install pyyaml"
            )

        try:
            with open(self.schemas_file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'schemas' not in data:
                raise ValidationException(
                    "Invalid schemas file format",
                    context={
                        'schemas_file': self.schemas_file_path,
                        'expected_key': 'schemas'
                    },
                    recovery="Ensure YAML file has 'schemas' top-level key"
                )

            self.schemas = data['schemas']

            logger.info(
                f"Loaded {len(self.schemas)} response schemas from {self.schemas_file_path}"
            )
            logger.debug(f"Available schema types: {list(self.schemas.keys())}")

        except FileNotFoundError as e:
            raise ValidationException(
                f"Schemas file not found: {self.schemas_file_path}",
                context={'error': str(e)},
                recovery="Create schemas file or check path configuration"
            )

        except yaml.YAMLError as e:
            raise ValidationException(
                f"Failed to parse YAML schemas: {str(e)}",
                context={
                    'schemas_file': self.schemas_file_path,
                    'error': str(e)
                },
                recovery="Validate YAML syntax and fix any errors"
            )

        except Exception as e:
            raise ValidationException(
                f"Unexpected error loading schemas: {str(e)}",
                context={
                    'schemas_file': self.schemas_file_path,
                    'error_type': type(e).__name__
                },
                recovery="Check file permissions and format"
            )

    def parse_response(
        self,
        response: str,
        expected_type: str
    ) -> Dict[str, Any]:
        """Parse and validate structured LLM response.

        Extracts metadata and content from response, validates against schema,
        and returns parsed data with validation results.

        Args:
            response: Raw LLM response string
            expected_type: Expected schema type (e.g., 'task_execution', 'validation')

        Returns:
            Dictionary with keys:
            - metadata: Parsed JSON metadata dict
            - content: Extracted natural language content string
            - is_valid: Whether response passed validation
            - validation_errors: List of validation error messages
            - schema_type: The expected schema type

        Example:
            >>> parsed = parser.parse_response(
            ...     response=llm_response,
            ...     expected_type='task_execution'
            ... )
            >>>
            >>> if parsed['is_valid']:
            ...     status = parsed['metadata']['status']
            ...     files = parsed['metadata']['files_modified']
            ...     explanation = parsed['content']
            ... else:
            ...     print(f"Validation errors: {parsed['validation_errors']}")
        """
        if not response or not isinstance(response, str):
            logger.warning("Empty or invalid response received")
            return self._handle_malformed_response(
                response,
                error="Response is empty or not a string"
            )

        if expected_type not in self.schemas:
            logger.error(
                f"Unknown schema type: {expected_type}. "
                f"Available types: {list(self.schemas.keys())}"
            )
            return self._handle_malformed_response(
                response,
                error=f"Unknown schema type: {expected_type}"
            )

        # Extract metadata and content
        try:
            metadata = self._extract_metadata(response)
            content = self._extract_content(response)
        except Exception as e:
            logger.error(f"Failed to extract response sections: {e}")
            return self._handle_malformed_response(
                response,
                error=f"Extraction failed: {str(e)}"
            )

        # Validate against schema
        is_valid, validation_errors = self._validate_against_schema(
            metadata,
            expected_type
        )

        # Log validation results
        if is_valid:
            logger.info(
                f"Successfully parsed and validated {expected_type} response "
                f"(metadata keys: {list(metadata.keys())})"
            )
        else:
            logger.warning(
                f"Validation failed for {expected_type} response: {validation_errors}"
            )

        return {
            'metadata': metadata,
            'content': content,
            'is_valid': is_valid,
            'validation_errors': validation_errors,
            'schema_type': expected_type
        }

    def _extract_metadata(self, response: str) -> Dict[str, Any]:
        """Extract JSON metadata from <METADATA> tags.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed metadata dictionary

        Raises:
            ValidationException: If metadata cannot be extracted or parsed

        Example:
            >>> metadata = parser._extract_metadata(response)
            >>> print(metadata['status'])
            'completed'
        """
        # Search for metadata tags
        match = self._metadata_pattern.search(response)

        if not match:
            # Try to find JSON without tags (fallback)
            logger.warning(
                "No <METADATA> tags found, attempting to extract raw JSON"
            )
            return self._extract_json_fallback(response)

        metadata_text = match.group(1).strip()

        # Parse JSON
        try:
            metadata = json.loads(metadata_text)

            if not isinstance(metadata, dict):
                raise ValidationException(
                    "Metadata must be a JSON object (dict)",
                    context={'metadata_type': type(metadata).__name__},
                    recovery="Ensure metadata is wrapped in curly braces {}"
                )

            logger.debug(f"Extracted metadata with keys: {list(metadata.keys())}")
            return metadata

        except json.JSONDecodeError as e:
            raise ValidationException(
                f"Invalid JSON in metadata: {str(e)}",
                context={
                    'metadata_text': metadata_text[:200],  # First 200 chars
                    'error': str(e)
                },
                recovery="Check JSON syntax (quotes, commas, brackets)"
            )

    def _extract_content(self, response: str) -> str:
        """Extract natural language content from <CONTENT> tags.

        Args:
            response: Raw LLM response string

        Returns:
            Extracted content string (or empty string if not found)

        Example:
            >>> content = parser._extract_content(response)
            >>> print(content)
            'Task completed successfully. Created authentication module...'
        """
        # Search for content tags
        match = self._content_pattern.search(response)

        if not match:
            logger.warning(
                "No <CONTENT> tags found, using entire response as content"
            )
            # Return response without metadata tags as fallback
            content = self._metadata_pattern.sub('', response).strip()
            return content

        content = match.group(1).strip()
        logger.debug(f"Extracted content ({len(content)} chars)")
        return content

    def _extract_json_fallback(self, response: str) -> Dict[str, Any]:
        """Fallback: Extract JSON from response without tags.

        Attempts to find JSON object in response when metadata tags are missing.

        Args:
            response: Raw LLM response string

        Returns:
            Parsed JSON dictionary

        Raises:
            ValidationException: If no valid JSON found
        """
        # Try to find JSON object pattern
        json_pattern = re.compile(r'\{.*\}', re.DOTALL)
        match = json_pattern.search(response)

        if not match:
            raise ValidationException(
                "No metadata tags or JSON object found in response",
                context={'response_preview': response[:200]},
                recovery="Ensure response includes <METADATA> tags with JSON"
            )

        try:
            json_text = match.group(0)
            metadata = json.loads(json_text)

            if not isinstance(metadata, dict):
                raise ValidationException(
                    "Extracted JSON is not an object",
                    context={'json_type': type(metadata).__name__},
                    recovery="Ensure JSON is a dict/object {}"
                )

            logger.info("Successfully extracted JSON from untagged response")
            return metadata

        except json.JSONDecodeError as e:
            raise ValidationException(
                f"Failed to parse JSON fallback: {str(e)}",
                context={'error': str(e)},
                recovery="Add proper <METADATA> tags around JSON"
            )

    def _validate_against_schema(
        self,
        data: Dict[str, Any],
        schema_type: str
    ) -> tuple[bool, List[str]]:
        """Validate metadata against schema definition.

        Checks that all required fields are present and have correct types.
        Validates allowed values for enum fields.

        Args:
            data: Metadata dictionary to validate
            schema_type: Schema type key (e.g., 'task_execution')

        Returns:
            Tuple of (is_valid, list_of_validation_errors)

        Example:
            >>> is_valid, errors = parser._validate_against_schema(
            ...     metadata, 'task_execution'
            ... )
            >>> if not is_valid:
            ...     print(f"Validation errors: {errors}")
        """
        schema = self.schemas.get(schema_type)
        if not schema:
            return False, [f"Schema not found: {schema_type}"]

        errors = []

        # Validate required fields
        required_fields = schema.get('required_fields', [])
        for field_spec in required_fields:
            field_name = field_spec.get('name')
            field_type = field_spec.get('type')
            allowed_values = field_spec.get('allowed_values', [])

            # Check field exists
            if field_name not in data:
                errors.append(
                    f"Missing required field: {field_name}"
                )
                continue

            value = data[field_name]

            # Check type
            type_valid, type_error = self._validate_field_type(
                value,
                field_type,
                field_name
            )
            if not type_valid:
                errors.append(type_error)

            # Check allowed values (for enums)
            if allowed_values and value not in allowed_values:
                errors.append(
                    f"Field '{field_name}' has invalid value '{value}'. "
                    f"Allowed: {allowed_values}"
                )

            # Check min/max values for numbers
            min_value = field_spec.get('min_value')
            max_value = field_spec.get('max_value')
            if isinstance(value, (int, float)):
                if min_value is not None and value < min_value:
                    errors.append(
                        f"Field '{field_name}' value {value} below minimum {min_value}"
                    )
                if max_value is not None and value > max_value:
                    errors.append(
                        f"Field '{field_name}' value {value} above maximum {max_value}"
                    )

            # Check max length for strings
            max_length = field_spec.get('max_length')
            if isinstance(value, str) and max_length:
                if len(value) > max_length:
                    errors.append(
                        f"Field '{field_name}' exceeds max length "
                        f"({len(value)} > {max_length})"
                    )

            # Validate array items if field_type is 'array'
            if field_type == 'array' and isinstance(value, list):
                item_type = field_spec.get('item_type')
                item_schema = field_spec.get('item_schema', [])

                for idx, item in enumerate(value):
                    if item_type == 'object' and item_schema:
                        # Validate object items against item schema
                        item_errors = self._validate_object_item(
                            item,
                            item_schema,
                            f"{field_name}[{idx}]"
                        )
                        errors.extend(item_errors)
                    else:
                        # Basic type validation
                        item_valid, item_error = self._validate_field_type(
                            item,
                            item_type,
                            f"{field_name}[{idx}]"
                        )
                        if not item_valid:
                            errors.append(item_error)

        # Validate optional fields if present
        optional_fields = schema.get('optional_fields', [])
        for field_spec in optional_fields:
            field_name = field_spec.get('name')

            # Skip if not present (optional)
            if field_name not in data:
                continue

            value = data[field_name]

            # Validate type
            field_type = field_spec.get('type')
            type_valid, type_error = self._validate_field_type(
                value,
                field_type,
                field_name
            )
            if not type_valid:
                errors.append(type_error)

        is_valid = len(errors) == 0

        if is_valid:
            logger.debug(f"Schema validation passed for {schema_type}")
        else:
            logger.warning(
                f"Schema validation failed for {schema_type}: {len(errors)} errors"
            )

        return is_valid, errors

    def _validate_field_type(
        self,
        value: Any,
        expected_type: str,
        field_name: str
    ) -> tuple[bool, str]:
        """Validate that a field value matches expected type.

        Args:
            value: Field value to validate
            expected_type: Expected type string ('string', 'number', 'boolean', 'array', 'object')
            field_name: Field name for error messages

        Returns:
            Tuple of (is_valid, error_message)
        """
        type_map = {
            'string': str,
            'number': (int, float),
            'integer': int,
            'boolean': bool,
            'array': list,
            'object': dict
        }

        expected_python_type = type_map.get(expected_type)

        if expected_python_type is None:
            return True, ""  # Unknown type, skip validation

        if not isinstance(value, expected_python_type):
            actual_type = type(value).__name__
            return False, (
                f"Field '{field_name}' has wrong type: "
                f"expected {expected_type}, got {actual_type}"
            )

        return True, ""

    def _validate_object_item(
        self,
        item: Dict[str, Any],
        item_schema: List[Dict[str, Any]],
        item_path: str
    ) -> List[str]:
        """Validate object item against schema.

        Args:
            item: Object item to validate
            item_schema: Schema definition for item
            item_path: Path to item for error messages

        Returns:
            List of validation errors
        """
        errors = []

        if not isinstance(item, dict):
            errors.append(f"{item_path} must be an object/dict")
            return errors

        # Validate each field in item schema
        for field_spec in item_schema:
            field_name = field_spec.get('name')
            field_type = field_spec.get('type')
            allowed_values = field_spec.get('allowed_values', [])

            if field_name not in item:
                # Check if required (all item_schema fields are considered required)
                errors.append(f"{item_path}.{field_name} is required")
                continue

            value = item[field_name]

            # Validate type
            type_valid, type_error = self._validate_field_type(
                value,
                field_type,
                f"{item_path}.{field_name}"
            )
            if not type_valid:
                errors.append(type_error)

            # Validate allowed values
            if allowed_values and value not in allowed_values:
                errors.append(
                    f"{item_path}.{field_name} has invalid value '{value}'. "
                    f"Allowed: {allowed_values}"
                )

        return errors

    def _handle_malformed_response(
        self,
        response: str,
        error: str
    ) -> Dict[str, Any]:
        """Handle malformed responses gracefully.

        Returns a standard error response structure when parsing fails.

        Args:
            response: Original response string
            error: Error message describing the issue

        Returns:
            Error response dictionary with empty metadata and error details

        Example:
            >>> result = parser._handle_malformed_response(
            ...     "Invalid response",
            ...     "Missing metadata tags"
            ... )
            >>> print(result['is_valid'])
            False
            >>> print(result['validation_errors'])
            ['Malformed response: Missing metadata tags']
        """
        logger.error(f"Malformed response: {error}")
        logger.debug(f"Response preview: {response[:500] if response else 'None'}")

        return {
            'metadata': {},
            'content': response if response else "",
            'is_valid': False,
            'validation_errors': [f"Malformed response: {error}"],
            'schema_type': None
        }
