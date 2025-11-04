"""
Rule validation result data class.

This module defines the RuleValidationResult class, a container for rule validation
outcomes including violations, errors, warnings, and metadata.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class RuleValidationResult:
    """Container for rule validation results.

    Encapsulates the outcome of validating code against a set of rules,
    including any violations found, errors encountered, warnings issued,
    and metadata about the validation process.

    Attributes:
        is_valid: Overall validation status (False if violations or errors exist)
        violations: List of rule violations found
        errors: List of validation errors encountered
        warnings: List of warnings issued
        checked_rules: List of rule IDs that were checked
        metadata: Additional context (timestamps, file paths, etc.)

    Example:
        >>> result = RuleValidationResult()
        >>> result.add_violation('CODE_001', {
        ...     'rule_name': 'NO_STUBS',
        ...     'severity': 'critical',
        ...     'message': 'Function contains only pass statement',
        ...     'location': {'file': 'app.py', 'line': 42},
        ...     'suggestion': 'Implement the function logic'
        ... })
        >>> result.is_valid
        False
        >>> result.has_violations()
        True
    """

    is_valid: bool = True
    violations: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_violation(self, rule_id: str, details: dict) -> None:
        """Add a rule violation.

        Automatically sets is_valid to False when a violation is added.

        Args:
            rule_id: Unique identifier for the rule that was violated
            details: Dictionary containing violation details with keys:
                - rule_name: str - Name of the rule
                - severity: str - Severity level (critical, high, medium, low)
                - message: str - Description of the violation
                - location: dict - Location info (file, line, column)
                - suggestion: Optional[str] - Suggested fix

        Example:
            >>> result = RuleValidationResult()
            >>> result.add_violation('CODE_001', {
            ...     'rule_name': 'NO_STUBS',
            ...     'severity': 'critical',
            ...     'message': 'Function is a stub',
            ...     'location': {'file': 'app.py', 'line': 42},
            ...     'suggestion': 'Implement the function'
            ... })
        """
        violation = {'rule_id': rule_id, **details}
        self.violations.append(violation)
        self.is_valid = False

    def add_error(self, error: str) -> None:
        """Add a validation error.

        Automatically sets is_valid to False when an error is added.
        Errors indicate problems with the validation process itself,
        not rule violations.

        Args:
            error: Error message describing what went wrong

        Example:
            >>> result = RuleValidationResult()
            >>> result.add_error('Failed to parse file: syntax error')
            >>> result.is_valid
            False
        """
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning message.

        Warnings do not affect the is_valid status. They indicate
        potential issues that don't constitute rule violations.

        Args:
            warning: Warning message

        Example:
            >>> result = RuleValidationResult()
            >>> result.add_warning('Function missing type hints')
            >>> result.is_valid
            True
        """
        self.warnings.append(warning)

    def mark_rule_checked(self, rule_id: str) -> None:
        """Mark a rule as having been checked.

        Tracks which rules were evaluated during validation,
        even if no violations were found.

        Args:
            rule_id: Unique identifier for the rule that was checked

        Example:
            >>> result = RuleValidationResult()
            >>> result.mark_rule_checked('CODE_001')
            >>> result.mark_rule_checked('CODE_002')
            >>> len(result.checked_rules)
            2
        """
        if rule_id not in self.checked_rules:
            self.checked_rules.append(rule_id)

    def has_violations(self) -> bool:
        """Check if any violations exist.

        Returns:
            True if violations list is non-empty, False otherwise

        Example:
            >>> result = RuleValidationResult()
            >>> result.has_violations()
            False
            >>> result.add_violation('CODE_001', {'rule_name': 'TEST', 'severity': 'high', 'message': 'Test'})
            >>> result.has_violations()
            True
        """
        return len(self.violations) > 0

    def has_errors(self) -> bool:
        """Check if any errors exist.

        Returns:
            True if errors list is non-empty, False otherwise

        Example:
            >>> result = RuleValidationResult()
            >>> result.has_errors()
            False
            >>> result.add_error('Parse error')
            >>> result.has_errors()
            True
        """
        return len(self.errors) > 0

    def get_summary(self) -> str:
        """Generate a human-readable summary of the validation result.

        Returns:
            Formatted multi-line string summarizing validation results,
            including status, violation counts by severity, errors, warnings,
            and number of rules checked.

        Example:
            >>> result = RuleValidationResult()
            >>> result.add_violation('CODE_001', {'severity': 'critical', 'rule_name': 'TEST', 'message': 'Test'})
            >>> result.add_warning('Missing docstring')
            >>> print(result.get_summary())
            Validation Result: FAILED
              Violations: 1 (1 critical)
              Errors: 0
              Warnings: 1
              Rules Checked: 0
        """
        status = "PASSED" if self.is_valid else "FAILED"

        # Count violations by severity
        severity_counts = {}
        for violation in self.violations:
            severity = violation.get('severity', 'unknown')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Format severity breakdown
        severity_str = ""
        if severity_counts:
            severity_parts = [f"{count} {severity}" for severity, count in sorted(severity_counts.items())]
            severity_str = f" ({', '.join(severity_parts)})"

        summary_lines = [
            f"Validation Result: {status}",
            f"  Violations: {len(self.violations)}{severity_str}",
            f"  Errors: {len(self.errors)}",
            f"  Warnings: {len(self.warnings)}",
            f"  Rules Checked: {len(self.checked_rules)}"
        ]

        return "\n".join(summary_lines)

    def to_dict(self) -> dict:
        """Serialize the result to a dictionary.

        Returns:
            Dictionary representation of the result with all fields

        Example:
            >>> result = RuleValidationResult()
            >>> result.add_violation('CODE_001', {'severity': 'high', 'rule_name': 'TEST', 'message': 'Test'})
            >>> data = result.to_dict()
            >>> 'is_valid' in data
            True
            >>> 'violations' in data
            True
        """
        return {
            'is_valid': self.is_valid,
            'violations': self.violations.copy(),
            'errors': self.errors.copy(),
            'warnings': self.warnings.copy(),
            'checked_rules': self.checked_rules.copy(),
            'metadata': self.metadata.copy()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'RuleValidationResult':
        """Deserialize a result from a dictionary.

        Args:
            data: Dictionary containing result data with keys matching
                  the class attributes

        Returns:
            New RuleValidationResult instance populated from the data

        Example:
            >>> data = {
            ...     'is_valid': False,
            ...     'violations': [{'rule_id': 'CODE_001', 'severity': 'high'}],
            ...     'errors': [],
            ...     'warnings': ['Missing docstring'],
            ...     'checked_rules': ['CODE_001', 'CODE_002'],
            ...     'metadata': {'timestamp': '2025-11-03'}
            ... }
            >>> result = RuleValidationResult.from_dict(data)
            >>> result.is_valid
            False
            >>> len(result.violations)
            1
        """
        return cls(
            is_valid=data.get('is_valid', True),
            violations=data.get('violations', []).copy(),
            errors=data.get('errors', []).copy(),
            warnings=data.get('warnings', []).copy(),
            checked_rules=data.get('checked_rules', []).copy(),
            metadata=data.get('metadata', {}).copy()
        )

    def __repr__(self) -> str:
        """String representation of the result.

        Returns:
            Detailed string showing validation status and counts

        Example:
            >>> result = RuleValidationResult()
            >>> repr(result)
            'RuleValidationResult(is_valid=True, violations=0, errors=0, warnings=0, checked_rules=0)'
        """
        return (
            f"RuleValidationResult("
            f"is_valid={self.is_valid}, "
            f"violations={len(self.violations)}, "
            f"errors={len(self.errors)}, "
            f"warnings={len(self.warnings)}, "
            f"checked_rules={len(self.checked_rules)})"
        )
