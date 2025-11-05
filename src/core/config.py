"""Configuration management for the orchestrator.

This module provides a singleton Config class that:
- Loads configuration from YAML files
- Validates against schema
- Supports environment variable overrides
- Provides dot notation access
- Sanitizes secrets for logging
- Supports hot-reload
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Optional, Dict, List
from threading import RLock
from copy import deepcopy

from src.core.exceptions import (
    ConfigException,
    ConfigValidationException,
    ConfigNotFoundException
)

logger = logging.getLogger(__name__)


class Config:
    """Singleton configuration manager.

    Loads and validates configuration from multiple sources with precedence:
    1. Command-line arguments (highest)
    2. Environment variables (ORCHESTRATOR_* prefix)
    3. User config file (~/.orchestrator/config.yaml)
    4. Project config file (./config/config.yaml)
    5. Profile config (./config/profiles/{profile}.yaml)  [M9]
    6. Default config (./config/default_config.yaml) (lowest)

    Thread-safe singleton implementation.

    Example:
        >>> config = Config.load()
        >>> agent_type = config.get('agent.type')
        >>> config.set('agent.timeout', 60)

        >>> # M9: Load with profile
        >>> config = Config.load(profile='python_project')
    """

    _instance: Optional['Config'] = None
    _lock = RLock()

    # Keys that should be treated as secrets
    SECRET_KEYS = {'password', 'key', 'secret', 'token', 'api_key', 'ssh_key'}

    def __init__(self):
        """Initialize config (use Config.load() instead)."""
        if Config._instance is not None:
            raise RuntimeError("Use Config.load() to get instance")

        self._config: Dict[str, Any] = {}
        self._config_path: Optional[Path] = None
        self._loaded = False

    @classmethod
    def load(
        cls,
        config_path: Optional[str] = None,
        defaults_only: bool = False,
        profile: Optional[str] = None
    ) -> 'Config':
        """Load configuration from file(s).

        Thread-safe singleton factory method.

        Args:
            config_path: Optional path to config file
            defaults_only: If True, only load default config
            profile: Optional profile name to load (M9)

        Returns:
            Config instance

        Raises:
            ConfigNotFoundException: If config file or profile not found
            ConfigValidationException: If config invalid

        Example:
            >>> config = Config.load('config/config.yaml')
            >>> config = Config.load()  # Use default paths
            >>> config = Config.load(profile='python_project')  # M9: Load profile
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()

            # Load configuration
            cls._instance._load_configuration(config_path, defaults_only, profile)

            return cls._instance

    def _load_configuration(
        self,
        config_path: Optional[str] = None,
        defaults_only: bool = False,
        profile: Optional[str] = None
    ) -> None:
        """Load configuration from multiple sources with precedence.

        Args:
            config_path: Optional explicit config path
            defaults_only: Only load defaults
            profile: Optional profile name (M9)
        """
        self._config = {}

        # 1. Load default config (lowest priority)
        default_path = Path('config/default_config.yaml')
        if default_path.exists():
            logger.debug(f"Loading default config from {default_path}")
            defaults = self._load_yaml(default_path)
            self._config = self._deep_merge(self._config, defaults)
        else:
            logger.warning(f"Default config not found at {default_path}")

        if defaults_only:
            self._loaded = True
            return

        # 2. Load profile config (M9)
        if profile:
            profile_path = Path(f'config/profiles/{profile}.yaml')
            if not profile_path.exists():
                raise ConfigNotFoundException(
                    f"Profile '{profile}' not found at {profile_path}"
                )
            logger.info(f"Loading profile config from {profile_path}")
            profile_config = self._load_yaml(profile_path)
            self._config = self._deep_merge(self._config, profile_config)

        # 3. Load project config
        project_path = Path('config/config.yaml')
        if project_path.exists():
            logger.debug(f"Loading project config from {project_path}")
            project_config = self._load_yaml(project_path)
            self._config = self._deep_merge(self._config, project_config)
            self._config_path = project_path

        # 4. Load user config
        user_config_path = Path.home() / '.orchestrator' / 'config.yaml'
        if user_config_path.exists():
            logger.debug(f"Loading user config from {user_config_path}")
            user_config = self._load_yaml(user_config_path)
            self._config = self._deep_merge(self._config, user_config)

        # 5. Load explicit config path
        if config_path:
            path = Path(config_path)
            if not path.exists():
                raise ConfigNotFoundException(str(path))

            logger.debug(f"Loading explicit config from {path}")
            explicit_config = self._load_yaml(path)
            self._config = self._deep_merge(self._config, explicit_config)
            self._config_path = path

        # 6. Apply environment variable overrides (highest priority)
        self._apply_env_overrides()

        # Validate configuration
        if not self.validate():
            raise ConfigValidationException(
                config_key='<root>',
                expected='valid configuration',
                got='invalid structure'
            )

        self._loaded = True
        logger.info("Configuration loaded successfully")

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML as dictionary

        Raises:
            ConfigException: If YAML is malformed
        """
        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                return data if data is not None else {}
        except yaml.YAMLError as e:
            raise ConfigException(
                f"Invalid YAML in {path}",
                context={'path': str(path), 'error': str(e)},
                recovery="Fix YAML syntax errors in configuration file"
            )
        except Exception as e:
            raise ConfigException(
                f"Failed to load config from {path}",
                context={'path': str(path), 'error': str(e)},
                recovery="Check file exists and is readable"
            )

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
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
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides.

        Looks for variables with ORCHESTRATOR_ prefix.
        Example: ORCHESTRATOR_AGENT_TYPE=aider sets config['agent']['type'] = 'aider'
        """
        prefix = 'ORCHESTRATOR_'

        for env_key, env_value in os.environ.items():
            if not env_key.startswith(prefix):
                continue

            # Remove prefix and convert to config path
            config_key = env_key[len(prefix):].lower().replace('_', '.')

            # Convert string value to appropriate type
            value = self._parse_env_value(env_value)

            logger.debug(f"Env override: {config_key} = {value if not self._is_secret_key(config_key) else '***'}")
            self.set(config_key, value)

    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type.

        Args:
            value: String value from environment

        Returns:
            Parsed value (bool, int, float, or string)
        """
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key: Configuration key (e.g., 'agent.type')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config.get('agent.type')
            'claude-code-ssh'
            >>> config.get('missing.key', 'default')
            'default'
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation.

        Args:
            key: Configuration key (e.g., 'agent.timeout')
            value: Value to set

        Example:
            >>> config.set('agent.timeout', 60)
        """
        with self._lock:
            keys = key.split('.')
            target = self._config

            # Navigate to parent
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]

            # Set value
            target[keys[-1]] = value

            # Log (sanitize secrets)
            log_value = '***' if self._is_secret_key(key) else value
            logger.debug(f"Config set: {key} = {log_value}")

    def validate(self) -> bool:
        """Validate configuration structure and values.

        Validates:
        - Context window thresholds (0.0-1.0, ordered)
        - Max turns bounds (min <= default <= max, min >= 3, max <= 30)
        - Timeout values (positive integers)
        - Threshold ranges

        Returns:
            True if valid

        Raises:
            ConfigValidationException: If validation fails with helpful message
        """
        # Validate context window thresholds
        self._validate_context_thresholds()

        # Validate max_turns configuration
        self._validate_max_turns()

        # Validate timeout values
        self._validate_timeouts()

        # Validate confidence threshold
        self._validate_confidence_threshold()

        # Validate quality threshold
        self._validate_quality_threshold()

        # Validate breakpoint configuration
        self._validate_breakpoints()

        # Validate LLM configuration
        self._validate_llm_config()

        # Validate agent configuration
        self._validate_agent_config()

        logger.debug("Configuration validation passed")
        return True

    def _validate_context_thresholds(self) -> None:
        """Validate context window threshold configuration.

        Rules:
        - Must be floats between 0.0 and 1.0
        - warning < refresh < critical
        - All three must be present

        Raises:
            ConfigValidationException: If validation fails
        """
        thresholds_path = 'context.thresholds'
        thresholds = self.get(thresholds_path, {})

        if not thresholds:
            logger.debug("Context thresholds not configured, using defaults")
            return

        required_keys = ['warning', 'refresh', 'critical']
        for key in required_keys:
            if key not in thresholds:
                raise ConfigValidationException(
                    config_key=f'{thresholds_path}.{key}',
                    expected='float between 0.0 and 1.0',
                    got='missing'
                )

        # Validate each threshold
        values = {}
        for key in required_keys:
            value = thresholds[key]

            if not isinstance(value, (int, float)):
                raise ConfigValidationException(
                    config_key=f'{thresholds_path}.{key}',
                    expected='float',
                    got=type(value).__name__
                )

            if not (0.0 <= value <= 1.0):
                raise ConfigValidationException(
                    config_key=f'{thresholds_path}.{key}',
                    expected='float between 0.0 and 1.0',
                    got=str(value)
                )

            values[key] = float(value)

        # Validate ordering: warning < refresh < critical
        if not (values['warning'] < values['refresh'] < values['critical']):
            raise ConfigValidationException(
                config_key=thresholds_path,
                expected='warning < refresh < critical',
                got=f"warning={values['warning']}, refresh={values['refresh']}, critical={values['critical']}"
            )

        logger.debug(f"Context thresholds valid: warning={values['warning']}, refresh={values['refresh']}, critical={values['critical']}")

    def _validate_max_turns(self) -> None:
        """Validate max_turns configuration.

        Rules:
        - min >= 3 (minimum for meaningful iteration)
        - max <= 30 (prevent infinite loops)
        - default between min and max
        - retry_multiplier >= 1.0

        Raises:
            ConfigValidationException: If validation fails
        """
        max_turns_path = 'orchestration.max_turns'
        max_turns = self.get(max_turns_path, {})

        if not max_turns:
            logger.debug("Max turns not configured, using defaults")
            return

        # Validate min
        min_turns = max_turns.get('min')
        if min_turns is not None:
            if not isinstance(min_turns, int):
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.min',
                    expected='integer',
                    got=type(min_turns).__name__
                )
            if min_turns < 3:
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.min',
                    expected='integer >= 3',
                    got=str(min_turns)
                )

        # Validate max
        max_value = max_turns.get('max')
        if max_value is not None:
            if not isinstance(max_value, int):
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.max',
                    expected='integer',
                    got=type(max_value).__name__
                )
            if max_value > 30:
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.max',
                    expected='integer <= 30',
                    got=str(max_value)
                )

        # Validate default
        default_turns = max_turns.get('default')
        if default_turns is not None:
            if not isinstance(default_turns, int):
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.default',
                    expected='integer',
                    got=type(default_turns).__name__
                )

            min_val = min_turns or 3
            max_val = max_value or 30

            if not (min_val <= default_turns <= max_val):
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.default',
                    expected=f'integer between {min_val} and {max_val}',
                    got=str(default_turns)
                )

        # Validate retry_multiplier
        retry_mult = max_turns.get('retry_multiplier')
        if retry_mult is not None:
            if not isinstance(retry_mult, (int, float)):
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.retry_multiplier',
                    expected='number',
                    got=type(retry_mult).__name__
                )
            if retry_mult < 1.0:
                raise ConfigValidationException(
                    config_key=f'{max_turns_path}.retry_multiplier',
                    expected='number >= 1.0',
                    got=str(retry_mult)
                )

        logger.debug(f"Max turns configuration valid")

    def _validate_timeouts(self) -> None:
        """Validate timeout configurations.

        Rules:
        - All timeouts must be positive integers (seconds)
        - response_timeout >= 60 (minimum 1 minute)
        - iteration_timeout > 0
        - task_timeout >= iteration_timeout

        Raises:
            ConfigValidationException: If validation fails
        """
        timeout_checks = [
            ('agent.timeout', 60),
            ('orchestration.iteration_timeout', 1),
            ('orchestration.task_timeout', 1),
            ('agent.local.response_timeout', 60),
            ('llm.timeout', 1),
            ('database.connect_timeout', 1),
        ]

        for timeout_path, min_value in timeout_checks:
            timeout = self.get(timeout_path)
            if timeout is None:
                continue

            if not isinstance(timeout, int):
                raise ConfigValidationException(
                    config_key=timeout_path,
                    expected='positive integer',
                    got=type(timeout).__name__
                )

            if timeout < min_value:
                raise ConfigValidationException(
                    config_key=timeout_path,
                    expected=f'integer >= {min_value}',
                    got=str(timeout)
                )

        logger.debug("Timeout configuration valid")

    def _validate_confidence_threshold(self) -> None:
        """Validate confidence threshold.

        Rules:
        - Must be between 0 and 100
        - Should be reasonable (30-70 typical range)

        Raises:
            ConfigValidationException: If validation fails
        """
        threshold_path = 'confidence.threshold'
        threshold = self.get(threshold_path)

        if threshold is None:
            logger.debug("Confidence threshold not configured, using default")
            return

        if not isinstance(threshold, (int, float)):
            raise ConfigValidationException(
                config_key=threshold_path,
                expected='number between 0 and 100',
                got=type(threshold).__name__
            )

        if not (0 <= threshold <= 100):
            raise ConfigValidationException(
                config_key=threshold_path,
                expected='number between 0 and 100',
                got=str(threshold)
            )

        if threshold < 10 or threshold > 90:
            logger.warning(
                f"Confidence threshold {threshold} seems unusual. "
                f"Recommended range: 30-70. Check {threshold_path}"
            )

        logger.debug(f"Confidence threshold valid: {threshold}")

    def _validate_quality_threshold(self) -> None:
        """Validate quality score threshold.

        Rules:
        - Must be between 0 and 100
        - Should be reasonable (50-85 typical range)

        Raises:
            ConfigValidationException: If validation fails
        """
        threshold_path = 'validation.quality.threshold'
        threshold = self.get(threshold_path)

        if threshold is None:
            logger.debug("Quality threshold not configured, using default")
            return

        if not isinstance(threshold, (int, float)):
            raise ConfigValidationException(
                config_key=threshold_path,
                expected='number between 0 and 100',
                got=type(threshold).__name__
            )

        if not (0 <= threshold <= 100):
            raise ConfigValidationException(
                config_key=threshold_path,
                expected='number between 0 and 100',
                got=str(threshold)
            )

        logger.debug(f"Quality threshold valid: {threshold}")

    def _validate_breakpoints(self) -> None:
        """Validate breakpoint configuration.

        Rules:
        - Thresholds must be between 0 and 100
        - max_retries must be non-negative

        Raises:
            ConfigValidationException: If validation fails
        """
        breakpoints_path = 'breakpoints'
        breakpoints = self.get(breakpoints_path, {})

        if not breakpoints:
            logger.debug("Breakpoints not configured")
            return

        triggers = breakpoints.get('triggers', {})

        # Validate low_confidence threshold
        lc_config = triggers.get('low_confidence', {})
        if lc_config:
            threshold = lc_config.get('threshold')
            if threshold is not None and not (0 <= threshold <= 100):
                raise ConfigValidationException(
                    config_key=f'{breakpoints_path}.triggers.low_confidence.threshold',
                    expected='number between 0 and 100',
                    got=str(threshold)
                )

        # Validate quality_too_low threshold
        ql_config = triggers.get('quality_too_low', {})
        if ql_config:
            threshold = ql_config.get('threshold')
            if threshold is not None and not (0 <= threshold <= 100):
                raise ConfigValidationException(
                    config_key=f'{breakpoints_path}.triggers.quality_too_low.threshold',
                    expected='number between 0 and 100',
                    got=str(threshold)
                )

        # Validate validation_failed max_retries
        vf_config = triggers.get('validation_failed', {})
        if vf_config:
            max_retries = vf_config.get('max_retries')
            if max_retries is not None and max_retries < 0:
                raise ConfigValidationException(
                    config_key=f'{breakpoints_path}.triggers.validation_failed.max_retries',
                    expected='non-negative integer',
                    got=str(max_retries)
                )

        logger.debug("Breakpoint configuration valid")

    def _validate_llm_config(self) -> None:
        """Validate LLM configuration.

        Rules:
        - temperature must be between 0.0 and 2.0
        - max_tokens must be positive
        - context_length must be positive
        - api_url must be valid URL format

        Raises:
            ConfigValidationException: If validation fails
        """
        llm_path = 'llm'
        llm = self.get(llm_path, {})

        if not llm:
            logger.debug("LLM configuration not present, using defaults")
            return

        # Validate temperature
        temperature = llm.get('temperature')
        if temperature is not None:
            if not isinstance(temperature, (int, float)):
                raise ConfigValidationException(
                    config_key=f'{llm_path}.temperature',
                    expected='number between 0.0 and 2.0',
                    got=type(temperature).__name__
                )
            if not (0.0 <= temperature <= 2.0):
                raise ConfigValidationException(
                    config_key=f'{llm_path}.temperature',
                    expected='number between 0.0 and 2.0',
                    got=str(temperature)
                )

        # Validate max_tokens
        max_tokens = llm.get('max_tokens')
        if max_tokens is not None:
            if not isinstance(max_tokens, int):
                raise ConfigValidationException(
                    config_key=f'{llm_path}.max_tokens',
                    expected='positive integer',
                    got=type(max_tokens).__name__
                )
            if max_tokens <= 0:
                raise ConfigValidationException(
                    config_key=f'{llm_path}.max_tokens',
                    expected='positive integer',
                    got=str(max_tokens)
                )

        # Validate context_length
        context_length = llm.get('context_length')
        if context_length is not None:
            if not isinstance(context_length, int):
                raise ConfigValidationException(
                    config_key=f'{llm_path}.context_length',
                    expected='positive integer',
                    got=type(context_length).__name__
                )
            if context_length <= 0:
                raise ConfigValidationException(
                    config_key=f'{llm_path}.context_length',
                    expected='positive integer',
                    got=str(context_length)
                )

        logger.debug("LLM configuration valid")

    def _validate_agent_config(self) -> None:
        """Validate agent configuration.

        Rules:
        - type must be one of allowed values
        - workspace_path must be valid
        - max_retries must be non-negative

        Raises:
            ConfigValidationException: If validation fails
        """
        agent_path = 'agent'
        agent = self.get(agent_path, {})

        if not agent:
            logger.debug("Agent configuration not present, using defaults")
            return

        # Validate agent type
        agent_type = agent.get('type')
        if agent_type is not None:
            # Allow both full names and short names for backwards compatibility
            allowed_types = [
                'claude-code-local', 'local',
                'claude-code-ssh', 'ssh',
                'claude-code-docker', 'docker',
                'aider'
            ]
            if agent_type not in allowed_types:
                raise ConfigValidationException(
                    config_key=f'{agent_path}.type',
                    expected=f'one of {allowed_types}',
                    got=agent_type
                )

        # Validate max_retries
        max_retries = agent.get('max_retries')
        if max_retries is not None:
            if not isinstance(max_retries, int):
                raise ConfigValidationException(
                    config_key=f'{agent_path}.max_retries',
                    expected='non-negative integer',
                    got=type(max_retries).__name__
                )
            if max_retries < 0:
                raise ConfigValidationException(
                    config_key=f'{agent_path}.max_retries',
                    expected='non-negative integer',
                    got=str(max_retries)
                )

        logger.debug("Agent configuration valid")

    def reload(self) -> None:
        """Reload configuration from files.

        Useful for hot-reload without restart.

        Example:
            >>> config.reload()  # Re-reads config files
        """
        logger.info("Reloading configuration")
        self._load_configuration(
            config_path=str(self._config_path) if self._config_path else None
        )

    def export(self, sanitize_secrets: bool = True) -> Dict[str, Any]:
        """Export configuration as dictionary.

        Args:
            sanitize_secrets: If True, replace secret values with '***'

        Returns:
            Configuration dictionary

        Example:
            >>> config.export()
            {'agent': {'type': 'claude-code-ssh', 'key': '***'}}
        """
        if not sanitize_secrets:
            return deepcopy(self._config)

        return self._sanitize_dict(deepcopy(self._config))

    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize secrets in dictionary.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        for key, value in data.items():
            if self._is_secret_key(key):
                data[key] = '***'
            elif isinstance(value, dict):
                data[key] = self._sanitize_dict(value)

        return data

    def _is_secret_key(self, key: str) -> bool:
        """Check if key name indicates a secret.

        Args:
            key: Key name (possibly dot-notation path)

        Returns:
            True if key should be treated as secret
        """
        key_lower = key.lower()
        return any(secret in key_lower for secret in self.SECRET_KEYS)

    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration section.

        Returns:
            LLM configuration dictionary

        Example:
            >>> llm_config = config.get_llm_config()
            >>> print(llm_config['model'])
        """
        return self.get('llm', {})

    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration section.

        Returns:
            Agent configuration dictionary
        """
        return self.get('agent', {})

    def get_database_url(self) -> str:
        """Get database connection URL.

        Returns:
            Database URL

        Example:
            >>> config.get_database_url()
            'sqlite:///data/orchestrator.db'
        """
        return self.get('database.url', 'sqlite:///data/orchestrator.db')

    @staticmethod
    def list_profiles() -> List[str]:
        """List available configuration profiles (M9).

        Returns:
            List of profile names (without .yaml extension)

        Example:
            >>> Config.list_profiles()
            ['python_project', 'web_app', 'ml_project', 'microservice', 'minimal', 'production']
        """
        profiles_dir = Path('config/profiles')
        if not profiles_dir.exists():
            return []

        profiles = []
        for profile_file in profiles_dir.glob('*.yaml'):
            profiles.append(profile_file.stem)

        return sorted(profiles)

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing only).

        Example:
            >>> Config.reset()  # In test teardown
        """
        with cls._lock:
            cls._instance = None
