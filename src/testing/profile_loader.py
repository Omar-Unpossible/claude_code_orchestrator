"""Profile loader for test configuration.

This module provides utilities to load test profiles for different LLM providers,
enabling easy testing with multiple LLMs without manual environment variable setup.

Example:
    >>> from src.testing.profile_loader import load_profile
    >>> from src.core.config import Config
    >>>
    >>> base_config = Config.load()
    >>> profile_config = load_profile("openai", base_config)
    >>> # profile_config now has OpenAI settings

Profile Format:
    Test profiles are YAML files located in config/profiles/test-{name}.yaml.
    They contain LLM-specific configuration including model settings, timeouts,
    and required environment variables.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from copy import deepcopy

from src.core.config import Config
from src.core.exceptions import ConfigException

logger = logging.getLogger(__name__)


class ProfileNotFoundError(Exception):
    """Profile file not found.

    Raised when a requested test profile doesn't exist in config/profiles/.
    """

    def __init__(self, profile_name: str, available_profiles: Optional[List[str]] = None):
        """Initialize error.

        Args:
            profile_name: Name of profile that wasn't found
            available_profiles: Optional list of available profile names
        """
        self.profile_name = profile_name
        self.available_profiles = available_profiles or []

        if self.available_profiles:
            message = (
                f"Profile '{profile_name}' not found in config/profiles/. "
                f"Available profiles: {', '.join(self.available_profiles)}"
            )
        else:
            message = (
                f"Profile '{profile_name}' not found in config/profiles/. "
                f"Expected file: config/profiles/test-{profile_name}.yaml"
            )

        super().__init__(message)


class ProfileValidationError(Exception):
    """Profile validation failed.

    Raised when a profile file is invalid (missing fields, wrong types, etc.).
    """

    def __init__(self, reason: str, profile_name: Optional[str] = None):
        """Initialize error.

        Args:
            reason: Reason for validation failure
            profile_name: Optional name of profile that failed validation
        """
        self.reason = reason
        self.profile_name = profile_name

        if profile_name:
            message = f"Profile '{profile_name}' validation failed: {reason}"
        else:
            message = f"Profile validation failed: {reason}"

        super().__init__(message)


def get_profile_path(profile_name: str) -> Path:
    """Get path to profile file.

    Args:
        profile_name: Profile name (e.g., 'ollama', 'openai')

    Returns:
        Path to profile file

    Example:
        >>> get_profile_path("openai")
        Path('config/profiles/test-openai.yaml')
    """
    return Path(f'config/profiles/test-{profile_name}.yaml')


def list_available_profiles() -> List[str]:
    """List available test profiles.

    Returns:
        List of profile names (without 'test-' prefix and '.yaml' suffix)

    Example:
        >>> list_available_profiles()
        ['ollama', 'openai', 'anthropic']
    """
    profiles_dir = Path('config/profiles')
    if not profiles_dir.exists():
        return []

    profiles = []
    for file_path in profiles_dir.glob('test-*.yaml'):
        # Extract name: test-{name}.yaml -> {name}
        name = file_path.stem[5:]  # Remove 'test-' prefix
        profiles.append(name)

    return sorted(profiles)


def check_required_env_vars(required: List[str]) -> List[str]:
    """Check which required environment variables are missing.

    Args:
        required: List of required environment variable names

    Returns:
        List of missing environment variable names (empty if all set)

    Example:
        >>> check_required_env_vars(['OPENAI_API_KEY', 'OPENAI_ORG_ID'])
        ['OPENAI_API_KEY']  # If only OPENAI_ORG_ID is set
    """
    missing = []
    for var in required:
        if not os.getenv(var):
            missing.append(var)
    return missing


def validate_profile(profile_data: Dict[str, Any], profile_name: Optional[str] = None) -> None:
    """Validate profile structure and required fields.

    Validates:
    - Required fields: profile_name, llm.type, llm.model
    - LLM type is supported (ollama, openai-codex)
    - Required environment variables are set

    Args:
        profile_data: Profile data dictionary loaded from YAML
        profile_name: Optional profile name for better error messages

    Raises:
        ProfileValidationError: If validation fails
    """
    # Check required top-level fields
    if 'profile_name' not in profile_data:
        raise ProfileValidationError("Missing required field: profile_name", profile_name)

    if 'llm' not in profile_data:
        raise ProfileValidationError("Missing required field: llm", profile_name)

    # Check required LLM fields
    llm = profile_data['llm']
    if not isinstance(llm, dict):
        raise ProfileValidationError("Field 'llm' must be a dictionary", profile_name)

    if 'type' not in llm:
        raise ProfileValidationError("Missing required field: llm.type", profile_name)

    if 'model' not in llm:
        raise ProfileValidationError("Missing required field: llm.model", profile_name)

    # Validate LLM type (basic check - allow any string for extensibility)
    llm_type = llm['type']
    if not isinstance(llm_type, str) or not llm_type.strip():
        raise ProfileValidationError(
            f"Field 'llm.type' must be a non-empty string, got: {llm_type}",
            profile_name
        )

    # Check required environment variables
    env_vars = profile_data.get('env_vars', {})
    required_env_vars = env_vars.get('required', [])

    if not isinstance(required_env_vars, list):
        raise ProfileValidationError(
            "Field 'env_vars.required' must be a list",
            profile_name
        )

    missing_vars = check_required_env_vars(required_env_vars)
    if missing_vars:
        # Build helpful error message
        vars_str = ', '.join(missing_vars)
        examples = '\n  '.join([f"export {var}=<value>" for var in missing_vars])

        raise ProfileValidationError(
            f"Required environment variables not set: {vars_str}\n\n"
            f"Set them with:\n  {examples}",
            profile_name
        )

    logger.debug(f"Profile '{profile_name or profile_data.get('profile_name')}' validation successful")


def merge_with_config(profile_data: Dict[str, Any], base_config: Config) -> Config:
    """Deep merge profile into config object.

    Profile values override base config values. Creates a new Config instance
    to avoid modifying the base config.

    Args:
        profile_data: Profile data dictionary
        base_config: Base configuration to merge with

    Returns:
        New Config instance with merged settings

    Example:
        >>> profile = {'llm': {'type': 'openai-codex', 'model': 'gpt-5-codex'}}
        >>> merged = merge_with_config(profile, base_config)
        >>> merged.get('llm.type')
        'openai-codex'
    """
    # Create new Config instance
    new_config = Config.load(defaults_only=True)

    # Get base config as dict
    base_dict = deepcopy(base_config._config)

    # Deep merge profile into base
    merged_dict = _deep_merge(base_dict, profile_data)

    # Set merged config
    new_config._config = merged_dict

    logger.debug(f"Profile merged with base config: {profile_data.get('profile_name', 'unknown')}")

    return new_config


def _deep_merge(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries (override takes precedence).

    Args:
        base: Base dictionary
        override: Override dictionary

    Returns:
        Merged dictionary
    """
    result = deepcopy(base)

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def load_profile(profile_name: str, base_config: Config) -> Config:
    """Load profile and merge with base config.

    Loads a test profile from config/profiles/test-{profile_name}.yaml,
    validates it, checks required environment variables, and merges it
    with the base configuration.

    Args:
        profile_name: Profile name (e.g., 'ollama', 'openai')
        base_config: Base configuration to merge with

    Returns:
        Merged Config object with profile settings applied

    Raises:
        ProfileNotFoundError: Profile file not found
        ProfileValidationError: Profile validation failed

    Example:
        >>> from src.core.config import Config
        >>> base = Config.load()
        >>> openai_config = load_profile("openai", base)
        >>> openai_config.get('llm.type')
        'openai-codex'
    """
    # Get profile path
    profile_path = get_profile_path(profile_name)

    # Check if profile exists
    if not profile_path.exists():
        available = list_available_profiles()
        raise ProfileNotFoundError(profile_name, available)

    # Load YAML file
    try:
        with open(profile_path, 'r') as f:
            profile_data = yaml.safe_load(f)
            if profile_data is None:
                raise ProfileValidationError(
                    "Profile file is empty or contains only comments",
                    profile_name
                )
    except yaml.YAMLError as e:
        raise ProfileValidationError(
            f"Invalid YAML syntax: {e}",
            profile_name
        )
    except Exception as e:
        raise ProfileValidationError(
            f"Failed to load profile file: {e}",
            profile_name
        )

    # Validate profile structure
    validate_profile(profile_data, profile_name)

    # Merge with base config
    merged_config = merge_with_config(profile_data, base_config)

    logger.info(f"Successfully loaded profile '{profile_name}' from {profile_path}")

    return merged_config
