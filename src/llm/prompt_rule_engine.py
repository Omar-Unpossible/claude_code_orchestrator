"""PromptRuleEngine - Core rule loading, application, and validation system.

This module provides the PromptRuleEngine class which manages prompt engineering rules:
- Loads rules from YAML configuration
- Filters rules by prompt type and domain
- Applies rules to prompts
- Validates responses against rules
- Logs violations to StateManager

Part of the LLM-first prompt engineering framework (PHASE_2).
"""

import logging
import yaml
from pathlib import Path
from threading import RLock
from typing import Dict, Any, List, Optional

from src.llm.prompt_rule import PromptRule
from src.llm.rule_validation_result import RuleValidationResult
from src.core.exceptions import StateManagerException

logger = logging.getLogger(__name__)


class PromptRuleEngine:
    """Manages loading, filtering, and validation of prompt engineering rules.

    The PromptRuleEngine:
    - Loads rules from YAML configuration files
    - Filters rules by prompt type, domain, and severity
    - Applies rules to prompts by injecting rule metadata
    - Validates LLM responses against applicable rules
    - Logs rule violations to StateManager for learning

    Thread-safe with internal locking for concurrent access.

    Example:
        >>> engine = PromptRuleEngine(rules_file_path='config/prompt_rules.yaml')
        >>> engine.load_rules_from_yaml()
        >>>
        >>> # Get rules for code generation
        >>> rules = engine.get_rules_for_domain('code_generation')
        >>>
        >>> # Apply rules to a prompt
        >>> prompt_with_rules = engine.apply_rules_to_prompt(
        ...     prompt={'instruction': 'Implement auth module'},
        ...     prompt_type='task_execution'
        ... )
        >>>
        >>> # Validate response
        >>> result = engine.validate_response_against_rules(
        ...     response={'code': '...'},
        ...     applicable_rules=rules,
        ...     context={'task_id': 123}
        ... )
    """

    def __init__(
        self,
        rules_file_path: str = 'config/prompt_rules.yaml',
        state_manager: Optional[Any] = None
    ):
        """Initialize PromptRuleEngine.

        Args:
            rules_file_path: Path to YAML file containing rule definitions
            state_manager: Optional StateManager for logging violations

        Example:
            >>> engine = PromptRuleEngine()
            >>> engine.load_rules_from_yaml()
        """
        self.rules_file_path = Path(rules_file_path)
        self.state_manager = state_manager
        self._lock = RLock()

        # Internal storage
        self._rules: Dict[str, PromptRule] = {}  # rule_id -> PromptRule
        self._rules_by_domain: Dict[str, List[PromptRule]] = {}  # domain -> [rules]
        self._rules_loaded = False

        logger.info(f"PromptRuleEngine initialized with rules file: {rules_file_path}")

    def load_rules_from_yaml(self) -> int:
        """Load rules from YAML configuration file.

        Parses the YAML file, creates PromptRule objects, and organizes them
        by domain for efficient filtering.

        Returns:
            Number of rules loaded

        Raises:
            FileNotFoundError: If rules file doesn't exist
            yaml.YAMLError: If YAML parsing fails
            ValueError: If rule data is invalid

        Example:
            >>> engine = PromptRuleEngine()
            >>> count = engine.load_rules_from_yaml()
            >>> print(f"Loaded {count} rules")
        """
        with self._lock:
            if not self.rules_file_path.exists():
                raise FileNotFoundError(
                    f"Rules file not found: {self.rules_file_path}"
                )

            logger.info(f"Loading rules from {self.rules_file_path}")

            with open(self.rules_file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'rules' not in data:
                raise ValueError("Invalid rules file: missing 'rules' key")

            rules_data = data['rules']
            rule_count = 0

            # Clear existing rules
            self._rules.clear()
            self._rules_by_domain.clear()

            # Load rules from each domain
            for domain, rule_list in rules_data.items():
                if not isinstance(rule_list, list):
                    logger.warning(f"Skipping domain '{domain}': not a list")
                    continue

                domain_rules = []

                for rule_dict in rule_list:
                    try:
                        # Add domain to rule data
                        rule_dict['domain'] = domain

                        # Create PromptRule object
                        rule = PromptRule.from_dict(rule_dict)

                        # Validate rule
                        if not rule.validate():
                            logger.warning(
                                f"Skipping invalid rule: {rule_dict.get('id', 'unknown')}"
                            )
                            continue

                        # Store rule
                        self._rules[rule.id] = rule
                        domain_rules.append(rule)
                        rule_count += 1

                    except (ValueError, KeyError) as e:
                        logger.error(f"Failed to load rule from {domain}: {e}")
                        continue

                # Store domain rules
                if domain_rules:
                    self._rules_by_domain[domain] = domain_rules

            self._rules_loaded = True
            logger.info(
                f"Successfully loaded {rule_count} rules across "
                f"{len(self._rules_by_domain)} domains"
            )

            return rule_count

    def get_rules_for_domain(
        self,
        domain: str,
        severity_filter: Optional[List[str]] = None
    ) -> List[PromptRule]:
        """Get all rules for a specific domain.

        Args:
            domain: Domain name (e.g., 'code_generation', 'testing')
            severity_filter: Optional list of severities to include
                           (e.g., ['critical', 'high'])

        Returns:
            List of PromptRule objects for the domain

        Example:
            >>> rules = engine.get_rules_for_domain('code_generation')
            >>> critical_rules = engine.get_rules_for_domain(
            ...     'code_generation',
            ...     severity_filter=['critical']
            ... )
        """
        with self._lock:
            if not self._rules_loaded:
                logger.warning("Rules not loaded yet, call load_rules_from_yaml() first")
                return []

            domain_rules = self._rules_by_domain.get(domain, [])

            if severity_filter:
                domain_rules = [
                    rule for rule in domain_rules
                    if rule.severity in severity_filter
                ]

            return domain_rules

    def get_rule_by_id(self, rule_id: str) -> Optional[PromptRule]:
        """Get a specific rule by ID.

        Args:
            rule_id: Unique rule identifier (e.g., 'CODE_001')

        Returns:
            PromptRule object or None if not found

        Example:
            >>> rule = engine.get_rule_by_id('CODE_001')
            >>> if rule:
            ...     print(rule.name)
        """
        with self._lock:
            return self._rules.get(rule_id)

    def get_all_rules(self) -> List[PromptRule]:
        """Get all loaded rules.

        Returns:
            List of all PromptRule objects

        Example:
            >>> all_rules = engine.get_all_rules()
            >>> print(f"Total rules: {len(all_rules)}")
        """
        with self._lock:
            return list(self._rules.values())

    def apply_rules_to_prompt(
        self,
        prompt: Dict[str, Any],
        prompt_type: str,
        domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Apply applicable rules to a prompt by injecting rule metadata.

        Adds a 'rules' section to the prompt containing applicable rules for
        the given prompt type and domains.

        Args:
            prompt: Prompt dictionary (may be structured or unstructured)
            prompt_type: Type of prompt (e.g., 'task_execution', 'validation')
            domains: Optional list of domains to include rules from.
                    If None, uses common domains for the prompt type.

        Returns:
            Modified prompt with rules injected

        Example:
            >>> prompt = {
            ...     'instruction': 'Implement user authentication',
            ...     'context': {'project': 'webapp'}
            ... }
            >>> prompt_with_rules = engine.apply_rules_to_prompt(
            ...     prompt,
            ...     prompt_type='task_execution',
            ...     domains=['code_generation', 'security']
            ... )
            >>> assert 'rules' in prompt_with_rules
        """
        with self._lock:
            if not self._rules_loaded:
                logger.warning("Rules not loaded, skipping rule injection")
                return prompt

            # Determine domains if not specified
            if domains is None:
                domains = self._get_default_domains_for_prompt_type(prompt_type)

            # Collect applicable rules
            applicable_rules = []
            for domain in domains:
                domain_rules = self.get_rules_for_domain(domain)
                applicable_rules.extend(domain_rules)

            # Inject rules into prompt
            prompt_copy = prompt.copy()
            prompt_copy['rules'] = [
                {
                    'id': rule.id,
                    'name': rule.name,
                    'description': rule.description,
                    'severity': rule.severity,
                    'validation_type': rule.validation_type
                }
                for rule in applicable_rules
            ]

            logger.debug(
                f"Injected {len(applicable_rules)} rules into {prompt_type} prompt "
                f"from domains: {domains}"
            )

            return prompt_copy

    def validate_response_against_rules(
        self,
        response: Dict[str, Any],
        applicable_rules: List[PromptRule],
        context: Optional[Dict[str, Any]] = None
    ) -> RuleValidationResult:
        """Validate LLM response against applicable rules.

        Checks the response for violations of the provided rules.
        Currently performs basic validation; advanced validation (AST checks, etc.)
        requires code_validators module (TASK_2.4).

        Args:
            response: LLM response dictionary
            applicable_rules: List of rules to validate against
            context: Optional context with task_id, file_paths, etc.

        Returns:
            RuleValidationResult with violations, errors, and warnings

        Example:
            >>> rules = engine.get_rules_for_domain('code_generation')
            >>> result = engine.validate_response_against_rules(
            ...     response={'code': 'def func(): pass'},
            ...     applicable_rules=rules,
            ...     context={'task_id': 123}
            ... )
            >>> if result.has_violations():
            ...     print(result.get_summary())
        """
        with self._lock:
            result = RuleValidationResult(
                metadata=context or {}
            )

            for rule in applicable_rules:
                # Mark rule as checked
                result.mark_rule_checked(rule.id)

                # Perform validation based on type
                # Note: Advanced validation (AST, regex, etc.) will be added in TASK_2.4
                if rule.validation_type == 'basic_check':
                    # Basic validation - check if response has expected structure
                    self._basic_validation(rule, response, result)

            # Log violations to StateManager if configured
            if self.state_manager and result.has_violations() and context:
                task_id = context.get('task_id')
                if task_id:
                    self._log_violations_to_state_manager(
                        task_id=task_id,
                        violations=result.violations
                    )

            return result

    def _basic_validation(
        self,
        rule: PromptRule,
        response: Dict[str, Any],
        result: RuleValidationResult
    ) -> None:
        """Perform basic validation checks.

        This is a placeholder for simple validation. Advanced validation
        (AST checks, regex, LLM-based) will be implemented in TASK_2.4.

        Args:
            rule: Rule to validate against
            response: Response to validate
            result: RuleValidationResult to update with violations
        """
        # Placeholder - actual validation logic will be in code_validators.py (TASK_2.4)
        # For now, just log that validation was performed
        logger.debug(f"Performed basic validation for rule {rule.id}")

    def _get_default_domains_for_prompt_type(self, prompt_type: str) -> List[str]:
        """Get default domains for a prompt type.

        Args:
            prompt_type: Type of prompt

        Returns:
            List of relevant domain names

        Example:
            >>> domains = engine._get_default_domains_for_prompt_type('task_execution')
            >>> assert 'code_generation' in domains
        """
        # Map prompt types to relevant domains
        domain_map = {
            'task_execution': ['code_generation', 'testing', 'documentation', 'security'],
            'validation': ['code_generation', 'testing'],
            'error_analysis': ['error_handling', 'performance'],
            'decision': [],  # No specific rules for decision prompts
            'planning': ['code_generation', 'parallel_agents'],
            'code_review': ['code_generation', 'security', 'performance']
        }

        return domain_map.get(prompt_type, [])

    def _log_violations_to_state_manager(
        self,
        task_id: int,
        violations: List[Dict[str, Any]]
    ) -> None:
        """Log rule violations to StateManager.

        Args:
            task_id: Task ID where violations occurred
            violations: List of violation dictionaries

        Note:
            This integrates with StateManager.log_rule_violation() from TASK_1.6
        """
        if not self.state_manager:
            return

        for violation in violations:
            try:
                self.state_manager.log_rule_violation(
                    task_id=task_id,
                    rule_data={
                        'rule_id': violation['rule_id'],
                        'rule_name': violation.get('rule_name', 'Unknown'),
                        'rule_domain': violation.get('domain', 'unknown'),
                        'violation_details': {
                            'message': violation.get('message', ''),
                            'location': violation.get('location', {}),
                            'suggestion': violation.get('suggestion', '')
                        },
                        'severity': violation.get('severity', 'medium')
                    }
                )
                logger.debug(f"Logged violation {violation['rule_id']} to StateManager")
            except (StateManagerException, KeyError) as e:
                logger.error(f"Failed to log violation to StateManager: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded rules.

        Returns:
            Dictionary with rule statistics

        Example:
            >>> stats = engine.get_statistics()
            >>> print(f"Total rules: {stats['total_rules']}")
            >>> print(f"Domains: {stats['domains']}")
        """
        with self._lock:
            severity_counts = {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }

            for rule in self._rules.values():
                if rule.severity in severity_counts:
                    severity_counts[rule.severity] += 1

            return {
                'total_rules': len(self._rules),
                'domains': list(self._rules_by_domain.keys()),
                'domain_count': len(self._rules_by_domain),
                'severity_breakdown': severity_counts,
                'rules_loaded': self._rules_loaded
            }

    def reload_rules(self) -> int:
        """Reload rules from YAML file.

        Useful for picking up configuration changes without restarting.

        Returns:
            Number of rules loaded

        Example:
            >>> count = engine.reload_rules()
            >>> print(f"Reloaded {count} rules")
        """
        logger.info("Reloading rules from configuration")
        return self.load_rules_from_yaml()

    def __repr__(self) -> str:
        """String representation of engine state."""
        return (
            f"<PromptRuleEngine(rules_loaded={self._rules_loaded}, "
            f"total_rules={len(self._rules)}, "
            f"domains={len(self._rules_by_domain)})>"
        )
