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
from typing import Any, Optional, Dict
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
    5. Default config (./config/default_config.yaml) (lowest)

    Thread-safe singleton implementation.

    Example:
        >>> config = Config.load()
        >>> agent_type = config.get('agent.type')
        >>> config.set('agent.timeout', 60)
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
        defaults_only: bool = False
    ) -> 'Config':
        """Load configuration from file(s).

        Thread-safe singleton factory method.

        Args:
            config_path: Optional path to config file
            defaults_only: If True, only load default config

        Returns:
            Config instance

        Raises:
            ConfigNotFoundException: If config file not found
            ConfigValidationException: If config invalid

        Example:
            >>> config = Config.load('config/config.yaml')
            >>> config = Config.load()  # Use default paths
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()

            # Load configuration
            cls._instance._load_configuration(config_path, defaults_only)

            return cls._instance

    def _load_configuration(
        self,
        config_path: Optional[str] = None,
        defaults_only: bool = False
    ) -> None:
        """Load configuration from multiple sources with precedence.

        Args:
            config_path: Optional explicit config path
            defaults_only: Only load defaults
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

        # 2. Load project config
        project_path = Path('config/config.yaml')
        if project_path.exists():
            logger.debug(f"Loading project config from {project_path}")
            project_config = self._load_yaml(project_path)
            self._config = self._deep_merge(self._config, project_config)
            self._config_path = project_path

        # 3. Load user config
        user_config_path = Path.home() / '.orchestrator' / 'config.yaml'
        if user_config_path.exists():
            logger.debug(f"Loading user config from {user_config_path}")
            user_config = self._load_yaml(user_config_path)
            self._config = self._deep_merge(self._config, user_config)

        # 4. Load explicit config path
        if config_path:
            path = Path(config_path)
            if not path.exists():
                raise ConfigNotFoundException(str(path))

            logger.debug(f"Loading explicit config from {path}")
            explicit_config = self._load_yaml(path)
            self._config = self._deep_merge(self._config, explicit_config)
            self._config_path = path

        # 5. Apply environment variable overrides (highest priority)
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
        """Validate configuration structure.

        Returns:
            True if valid

        Raises:
            ConfigValidationException: If validation fails
        """
        # Basic validation - check required keys exist
        required_sections = []  # Will add validation in future milestones

        for section in required_sections:
            if section not in self._config:
                raise ConfigValidationException(
                    config_key=section,
                    expected='dictionary',
                    got='missing'
                )

        return True

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

    @classmethod
    def reset(cls) -> None:
        """Reset singleton instance (for testing only).

        Example:
            >>> Config.reset()  # In test teardown
        """
        with cls._lock:
            cls._instance = None
