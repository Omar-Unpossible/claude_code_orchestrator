"""Prompt Rule Data Class.

This module defines the PromptRule data class for representing individual
prompt engineering rules loaded from YAML configuration. Each rule defines
validation criteria, severity, examples, and enforcement strategies.

Classes:
    PromptRule: Data class representing a single prompt engineering rule
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class PromptRule:
    """Represents a single prompt engineering rule.

    A PromptRule encapsulates validation criteria, severity levels, examples,
    and enforcement strategies for prompt engineering best practices. Rules are
    loaded from YAML configuration and used by the PromptRuleEngine to validate
    and optimize LLM interactions.

    Attributes:
        id: Unique identifier (e.g., "CODE_001")
        name: Short descriptive name (e.g., "NO_STUBS")
        description: Detailed explanation of the rule
        validation_type: How to validate ("ast_check", "regex", "llm_check", etc.)
        severity: Rule severity ("critical", "high", "medium", "low")
        domain: Rule domain (e.g., "code_generation", "testing", "documentation")
        examples: Dictionary with positive/negative examples
        validation_code: Optional function name or code for validation
        enforcement: Optional description of how to enforce the rule

    Example:
        >>> rule_data = {
        ...     'id': 'CODE_001',
        ...     'name': 'NO_STUBS',
        ...     'description': 'Never generate stub functions',
        ...     'validation_type': 'ast_check',
        ...     'severity': 'critical',
        ...     'domain': 'code_generation',
        ...     'examples': {
        ...         'positive': 'def func(): return x + y',
        ...         'negative': 'def func(): pass'
        ...     },
        ...     'validation_code': 'check_for_pass_statements'
        ... }
        >>> rule = PromptRule.from_dict(rule_data)
        >>> assert rule.validate()
        >>> assert rule.id == 'CODE_001'
        >>> serialized = rule.to_dict()
        >>> assert serialized['id'] == 'CODE_001'
    """

    id: str
    name: str
    description: str
    validation_type: str
    severity: str
    domain: str
    examples: Dict[str, Any] = field(default_factory=dict)
    validation_code: Optional[str] = None
    enforcement: Optional[str] = None

    # Valid severity levels
    VALID_SEVERITIES = {'critical', 'high', 'medium', 'low'}

    # Recognized validation types (extensible)
    RECOGNIZED_VALIDATION_TYPES = {
        'ast_check',
        'regex',
        'manual_review',
        'llm_check',
        'coverage_check',
        'format_check',
        'schema_check'
    }

    def validate(self) -> bool:
        """Validate that the rule structure is complete and valid.

        Checks that all required fields are present, non-empty, and valid.
        Validates severity level and provides warnings for unrecognized
        validation types.

        Returns:
            True if rule is valid, False otherwise

        Example:
            >>> rule = PromptRule(
            ...     id='CODE_001',
            ...     name='NO_STUBS',
            ...     description='Never generate stub functions',
            ...     validation_type='ast_check',
            ...     severity='critical',
            ...     domain='code_generation'
            ... )
            >>> assert rule.validate()
        """
        # Check required fields are present and non-empty
        required_fields = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'validation_type': self.validation_type,
            'severity': self.severity,
            'domain': self.domain
        }

        for field_name, field_value in required_fields.items():
            if not field_value or not str(field_value).strip():
                return False

        # Validate severity level
        if self.severity not in self.VALID_SEVERITIES:
            return False

        # Note: validation_type validation is informational only
        # Unrecognized types are allowed but may be logged
        if self.validation_type not in self.RECOGNIZED_VALIDATION_TYPES:
            # This is a warning, not a failure
            # The rule engine may log this for awareness
            pass

        return True

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the rule to a dictionary.

        Converts the PromptRule instance to a dictionary representation
        suitable for JSON serialization or storage.

        Returns:
            Dictionary containing all rule fields

        Example:
            >>> rule = PromptRule(
            ...     id='CODE_001',
            ...     name='NO_STUBS',
            ...     description='Never generate stub functions',
            ...     validation_type='ast_check',
            ...     severity='critical',
            ...     domain='code_generation',
            ...     examples={'positive': 'code', 'negative': 'pass'},
            ...     validation_code='check_function'
            ... )
            >>> data = rule.to_dict()
            >>> assert data['id'] == 'CODE_001'
            >>> assert 'examples' in data
        """
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'validation_type': self.validation_type,
            'severity': self.severity,
            'domain': self.domain,
            'examples': self.examples,
            'validation_code': self.validation_code,
            'enforcement': self.enforcement
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptRule':
        """Deserialize a rule from a dictionary.

        Creates a PromptRule instance from a dictionary representation,
        typically loaded from YAML configuration.

        Args:
            data: Dictionary containing rule fields

        Returns:
            PromptRule instance

        Raises:
            ValueError: If required fields are missing or invalid

        Example:
            >>> data = {
            ...     'id': 'CODE_001',
            ...     'name': 'NO_STUBS',
            ...     'description': 'Never generate stub functions',
            ...     'validation_type': 'ast_check',
            ...     'severity': 'critical',
            ...     'domain': 'code_generation'
            ... }
            >>> rule = PromptRule.from_dict(data)
            >>> assert rule.id == 'CODE_001'
        """
        # Validate required fields are present
        required_fields = ['id', 'name', 'description', 'validation_type', 'severity', 'domain']
        missing_fields = [f for f in required_fields if f not in data]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Validate severity is recognized
        severity = data['severity']
        if severity not in cls.VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity '{severity}'. "
                f"Must be one of: {', '.join(cls.VALID_SEVERITIES)}"
            )

        # Create instance with required fields
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            validation_type=data['validation_type'],
            severity=severity,
            domain=data['domain'],
            examples=data.get('examples', {}),
            validation_code=data.get('validation_code'),
            enforcement=data.get('enforcement')
        )

    def __repr__(self) -> str:
        """Return string representation of the rule.

        Returns:
            String representation with key fields

        Example:
            >>> rule = PromptRule(
            ...     id='CODE_001',
            ...     name='NO_STUBS',
            ...     description='Never generate stub functions',
            ...     validation_type='ast_check',
            ...     severity='critical',
            ...     domain='code_generation'
            ... )
            >>> repr(rule)
            "PromptRule(id='CODE_001', name='NO_STUBS', severity='critical', domain='code_generation')"
        """
        return (
            f"PromptRule(id='{self.id}', name='{self.name}', "
            f"severity='{self.severity}', domain='{self.domain}')"
        )

    def __eq__(self, other: Any) -> bool:
        """Compare rules for equality.

        Two rules are equal if they have the same ID, as IDs are unique
        identifiers.

        Args:
            other: Another object to compare

        Returns:
            True if other is a PromptRule with the same ID, False otherwise

        Example:
            >>> rule1 = PromptRule(
            ...     id='CODE_001', name='NO_STUBS', description='desc',
            ...     validation_type='ast_check', severity='critical',
            ...     domain='code_generation'
            ... )
            >>> rule2 = PromptRule(
            ...     id='CODE_001', name='DIFFERENT_NAME', description='desc',
            ...     validation_type='ast_check', severity='critical',
            ...     domain='code_generation'
            ... )
            >>> assert rule1 == rule2  # Same ID
        """
        if not isinstance(other, PromptRule):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Return hash of the rule.

        Hash is based on the rule ID for use in sets and dictionaries.

        Returns:
            Hash value based on rule ID

        Example:
            >>> rule = PromptRule(
            ...     id='CODE_001', name='NO_STUBS', description='desc',
            ...     validation_type='ast_check', severity='critical',
            ...     domain='code_generation'
            ... )
            >>> assert hash(rule) == hash('CODE_001')
        """
        return hash(self.id)
