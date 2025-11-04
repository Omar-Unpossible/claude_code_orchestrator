"""Test configuration file validation for LLM-first prompt engineering framework.

Tests validate that YAML configuration files:
1. Parse correctly (valid YAML syntax)
2. Contain all required sections/domains
3. Follow expected schema structure
4. Include required fields for all entries
5. Have reasonable values for thresholds and multipliers

Part of TASK_1.4: Validate configuration files
"""

import os
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List


# Path to config directory
CONFIG_DIR = Path(__file__).parent.parent / "config"


# ============================================================================
# Helper Functions
# ============================================================================

def load_yaml(filename: str) -> Dict[str, Any]:
    """Load and parse a YAML file from config directory.

    Args:
        filename: Name of YAML file in config/ directory

    Returns:
        Parsed YAML content as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    filepath = CONFIG_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def check_required_fields(item: Dict, required_fields: List[str], item_name: str) -> List[str]:
    """Check that a dictionary contains all required fields.

    Args:
        item: Dictionary to check
        required_fields: List of required field names
        item_name: Name of item for error messages

    Returns:
        List of missing field names (empty if all present)
    """
    missing = []
    for field in required_fields:
        if field not in item or item[field] is None:
            missing.append(field)
    return missing


# ============================================================================
# Test: prompt_rules.yaml
# ============================================================================

def test_prompt_rules_yaml_valid_structure():
    """Test that prompt_rules.yaml is valid YAML and has expected top-level structure."""
    config = load_yaml("prompt_rules.yaml")

    # Should have 'rules' key
    assert 'rules' in config, "Missing 'rules' top-level key"
    assert isinstance(config['rules'], dict), "'rules' should be a dictionary"


def test_prompt_rules_yaml_all_domains_present():
    """Test that all 7 required domains are present in prompt_rules.yaml."""
    config = load_yaml("prompt_rules.yaml")
    rules = config['rules']

    required_domains = [
        'code_generation',
        'documentation',
        'testing',
        'error_handling',
        'performance',
        'security',
        'parallel_agents'
    ]

    for domain in required_domains:
        assert domain in rules, f"Missing domain: {domain}"
        assert isinstance(rules[domain], list), f"Domain '{domain}' should be a list of rules"
        assert len(rules[domain]) >= 5, f"Domain '{domain}' should have at least 5 rules, got {len(rules[domain])}"


def test_prompt_rules_yaml_rule_schema_compliance():
    """Test that all rules follow the expected schema with required fields."""
    config = load_yaml("prompt_rules.yaml")
    rules = config['rules']

    required_fields = ['id', 'name', 'description', 'validation_type', 'severity']

    for domain, rule_list in rules.items():
        for i, rule in enumerate(rule_list):
            missing = check_required_fields(rule, required_fields, f"{domain}[{i}]")
            assert not missing, f"Rule {domain}[{i}] missing required fields: {missing}"

            # Check field types
            assert isinstance(rule['id'], str), f"Rule {domain}[{i}] 'id' should be string"
            assert isinstance(rule['name'], str), f"Rule {domain}[{i}] 'name' should be string"
            assert isinstance(rule['description'], str), f"Rule {domain}[{i}] 'description' should be string"
            assert isinstance(rule['validation_type'], str), f"Rule {domain}[{i}] 'validation_type' should be string"
            assert isinstance(rule['severity'], str), f"Rule {domain}[{i}] 'severity' should be string"

            # Check severity values
            valid_severities = ['critical', 'high', 'medium', 'low']
            assert rule['severity'] in valid_severities, \
                f"Rule {domain}[{i}] has invalid severity '{rule['severity']}', must be one of {valid_severities}"


def test_prompt_rules_yaml_examples_present():
    """Test that all rules have examples (positive and/or negative)."""
    config = load_yaml("prompt_rules.yaml")
    rules = config['rules']

    for domain, rule_list in rules.items():
        for i, rule in enumerate(rule_list):
            assert 'examples' in rule, f"Rule {domain}[{i}] ({rule.get('id', 'unknown')}) missing 'examples'"
            examples = rule['examples']
            assert isinstance(examples, dict), f"Rule {domain}[{i}] 'examples' should be a dictionary"

            # At least one of 'positive' or 'negative' should be present
            has_examples = 'positive' in examples or 'negative' in examples
            assert has_examples, f"Rule {domain}[{i}] should have at least one example (positive or negative)"


# ============================================================================
# Test: response_schemas.yaml
# ============================================================================

def test_response_schemas_yaml_valid_structure():
    """Test that response_schemas.yaml is valid YAML and has expected top-level structure."""
    config = load_yaml("response_schemas.yaml")

    # Should have 'schemas' key
    assert 'schemas' in config, "Missing 'schemas' top-level key"
    assert isinstance(config['schemas'], dict), "'schemas' should be a dictionary"


def test_response_schemas_yaml_all_schemas_present():
    """Test that all 5 required response schemas are present."""
    config = load_yaml("response_schemas.yaml")
    schemas = config['schemas']

    required_schemas = [
        'task_execution',
        'validation',
        'error_analysis',
        'decision',
        'planning'
    ]

    for schema_name in required_schemas:
        assert schema_name in schemas, f"Missing schema: {schema_name}"
        assert isinstance(schemas[schema_name], dict), f"Schema '{schema_name}' should be a dictionary"


def test_response_schemas_yaml_schema_completeness():
    """Test that each schema has all required fields."""
    config = load_yaml("response_schemas.yaml")
    schemas = config['schemas']

    required_schema_fields = [
        'schema_name',
        'description',
        'required_fields',
        'validation_rules',
        'example'
    ]

    for schema_name, schema in schemas.items():
        missing = check_required_fields(schema, required_schema_fields, schema_name)
        assert not missing, f"Schema '{schema_name}' missing required fields: {missing}"

        # Check field types
        assert isinstance(schema['schema_name'], str), f"Schema '{schema_name}' 'schema_name' should be string"
        assert isinstance(schema['description'], str), f"Schema '{schema_name}' 'description' should be string"
        assert isinstance(schema['required_fields'], list), f"Schema '{schema_name}' 'required_fields' should be list"
        assert isinstance(schema['validation_rules'], list), f"Schema '{schema_name}' 'validation_rules' should be list"
        assert isinstance(schema['example'], dict), f"Schema '{schema_name}' 'example' should be dict"

        # Check that required_fields is not empty
        assert len(schema['required_fields']) > 0, f"Schema '{schema_name}' should have at least one required field"


def test_response_schemas_yaml_examples_present():
    """Test that all schemas have complete example responses."""
    config = load_yaml("response_schemas.yaml")
    schemas = config['schemas']

    for schema_name, schema in schemas.items():
        # Check example exists
        assert 'example' in schema, f"Schema '{schema_name}' missing example"
        example = schema['example']
        assert isinstance(example, dict), f"Schema '{schema_name}' example should be a dictionary"
        assert len(example) > 0, f"Schema '{schema_name}' example should not be empty"

        # Check that example contains all required fields
        required_fields = schema['required_fields']
        for field in required_fields:
            # Get field name (could be dict with 'name' key or just string)
            field_name = field['name'] if isinstance(field, dict) else field
            assert field_name in example, \
                f"Schema '{schema_name}' example missing required field '{field_name}'"


# ============================================================================
# Test: complexity_thresholds.yaml
# ============================================================================

def test_complexity_thresholds_yaml_valid_structure():
    """Test that complexity_thresholds.yaml is valid YAML and has expected top-level structure."""
    config = load_yaml("complexity_thresholds.yaml")

    # Should be a dictionary
    assert isinstance(config, dict), "Config should be a dictionary"
    assert len(config) > 0, "Config should not be empty"


def test_complexity_thresholds_yaml_all_sections_present():
    """Test that all required sections are present in complexity_thresholds.yaml."""
    config = load_yaml("complexity_thresholds.yaml")

    required_sections = [
        'complexity_heuristics',
        'decomposition_thresholds',
        'parallelization_rules',
        'task_type_multipliers'
    ]

    for section in required_sections:
        assert section in config, f"Missing section: {section}"
        assert isinstance(config[section], dict), f"Section '{section}' should be a dictionary"
        assert len(config[section]) > 0, f"Section '{section}' should not be empty"


def test_complexity_thresholds_yaml_threshold_values_reasonable():
    """Test that threshold values are reasonable (not negative, not extreme)."""
    config = load_yaml("complexity_thresholds.yaml")

    # Check decomposition thresholds
    decomp = config['decomposition_thresholds']

    required_thresholds = ['max_tokens', 'max_files', 'max_dependencies', 'max_duration_hours']
    for threshold in required_thresholds:
        assert threshold in decomp, f"Missing threshold: {threshold}"
        value = decomp[threshold]
        assert isinstance(value, (int, float)), f"Threshold '{threshold}' should be numeric"
        assert value > 0, f"Threshold '{threshold}' should be positive, got {value}"

    # Check specific reasonable ranges
    assert 1000 <= decomp['max_tokens'] <= 100000, \
        f"max_tokens should be reasonable (1k-100k), got {decomp['max_tokens']}"
    assert 1 <= decomp['max_files'] <= 100, \
        f"max_files should be reasonable (1-100), got {decomp['max_files']}"
    assert 1 <= decomp['max_dependencies'] <= 20, \
        f"max_dependencies should be reasonable (1-20), got {decomp['max_dependencies']}"
    assert 0.5 <= decomp['max_duration_hours'] <= 24, \
        f"max_duration_hours should be reasonable (0.5-24), got {decomp['max_duration_hours']}"

    # Check task type multipliers are reasonable
    multipliers = config['task_type_multipliers']
    for task_type, multiplier in multipliers.items():
        assert isinstance(multiplier, (int, float)), \
            f"Task type '{task_type}' multiplier should be numeric"
        assert 0.1 <= multiplier <= 3.0, \
            f"Task type '{task_type}' multiplier should be reasonable (0.1-3.0), got {multiplier}"

    # Check parallelization rules
    parallel = config['parallelization_rules']
    assert 'max_concurrent_agents' in parallel, "Missing max_concurrent_agents"
    max_agents = parallel['max_concurrent_agents']
    assert isinstance(max_agents, int), "max_concurrent_agents should be integer"
    assert 1 <= max_agents <= 20, f"max_concurrent_agents should be reasonable (1-20), got {max_agents}"


# ============================================================================
# Integration Test: All Config Files Load Together
# ============================================================================

def test_all_config_files_load_successfully():
    """Integration test: ensure all 3 new config files can be loaded without errors."""
    files = [
        "prompt_rules.yaml",
        "response_schemas.yaml",
        "complexity_thresholds.yaml"
    ]

    loaded = {}
    for filename in files:
        try:
            loaded[filename] = load_yaml(filename)
        except Exception as e:
            pytest.fail(f"Failed to load {filename}: {e}")

    # Verify all loaded successfully
    assert len(loaded) == 3, "Should have loaded 3 config files"

    # Verify non-empty
    for filename, content in loaded.items():
        assert content is not None, f"{filename} should not be None"
        assert len(content) > 0, f"{filename} should not be empty"
