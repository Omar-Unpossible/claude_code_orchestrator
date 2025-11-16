"""Model configuration loader for LLM context management.

This module provides functionality to load and validate model configurations
from YAML files, including context window sizes, costs, and optimization profiles.

Classes:
    ModelConfigLoader: Loads and validates model configurations

Example:
    >>> loader = ModelConfigLoader()
    >>> config = loader.load_models('config/models.yaml')
    >>> qwen_config = loader.get_model('qwen_2_5_32b')
    >>> print(qwen_config['context_window'])
    128000

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml

logger = logging.getLogger(__name__)


class ModelConfigurationError(Exception):
    """Raised when model configuration is invalid or cannot be loaded."""

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        validation_errors: Optional[List[str]] = None
    ):
        """Initialize configuration error.

        Args:
            message: Error description
            config_path: Path to config file that failed
            validation_errors: List of specific validation errors
        """
        self.config_path = config_path
        self.validation_errors = validation_errors or []

        full_message = message
        if config_path:
            full_message = f"{message} (config: {config_path})"
        if validation_errors:
            full_message += f"\nValidation errors:\n  - " + "\n  - ".join(validation_errors)

        super().__init__(full_message)


class ModelConfigLoader:
    """Load and validate LLM model configurations.

    This class handles loading model configurations from YAML files,
    validating the schema, and providing access to model-specific settings.

    Thread-safe: Yes (read-only operations after initialization)

    Attributes:
        config_path: Path to models configuration file
        models: Dictionary of loaded model configurations
        active_orchestrator_model: ID of active orchestrator model
        active_implementer_model: ID of active implementer model

    Example:
        >>> loader = ModelConfigLoader('config/models.yaml')
        >>> qwen = loader.get_model('qwen_2_5_32b')
        >>> print(f"Context window: {qwen['context_window']:,} tokens")
        Context window: 128,000 tokens
    """

    # Required fields for each model configuration
    REQUIRED_MODEL_FIELDS = [
        'provider',
        'model',
        'context_window'
    ]

    # Valid providers
    VALID_PROVIDERS = ['ollama', 'anthropic', 'openai']

    # Valid optimization profiles
    VALID_OPTIMIZATION_PROFILES = [
        'ultra-aggressive',
        'aggressive',
        'balanced-aggressive',
        'balanced',
        'minimal'
    ]

    def __init__(self, config_path: Optional[str] = None):
        """Initialize model configuration loader.

        Args:
            config_path: Path to models.yaml file. If None, uses default
                location (config/models.yaml)

        Raises:
            ModelConfigurationError: If config file cannot be loaded or is invalid
        """
        if config_path is None:
            config_path = 'config/models.yaml'

        self.config_path = Path(config_path)
        self.models: Dict[str, Dict[str, Any]] = {}
        self.active_orchestrator_model: Optional[str] = None
        self.active_implementer_model: Optional[str] = None
        self.optimization_profiles: Dict[str, Dict[str, Any]] = {}

        # Load configuration on initialization
        self._load_config()

        logger.info(
            f"ModelConfigLoader initialized: {len(self.models)} models loaded from {self.config_path}"
        )

    def _load_config(self) -> None:
        """Load configuration from YAML file.

        Raises:
            ModelConfigurationError: If file doesn't exist or YAML is invalid
        """
        if not self.config_path.exists():
            raise ModelConfigurationError(
                f"Model configuration file not found: {self.config_path}",
                config_path=str(self.config_path)
            )

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ModelConfigurationError(
                f"Invalid YAML syntax in configuration file: {e}",
                config_path=str(self.config_path)
            )
        except Exception as e:
            raise ModelConfigurationError(
                f"Error reading configuration file: {e}",
                config_path=str(self.config_path)
            )

        # Validate and load configuration
        self._validate_and_load(config)

    def _validate_and_load(self, config: Dict[str, Any]) -> None:
        """Validate configuration schema and load data.

        Args:
            config: Parsed YAML configuration

        Raises:
            ModelConfigurationError: If configuration is invalid
        """
        validation_errors = []

        # Check for required top-level keys
        if 'llm_models' not in config:
            validation_errors.append("Missing required key: 'llm_models'")

        if not validation_errors and not isinstance(config['llm_models'], dict):
            validation_errors.append("'llm_models' must be a dictionary")

        if validation_errors:
            raise ModelConfigurationError(
                "Invalid configuration schema",
                config_path=str(self.config_path),
                validation_errors=validation_errors
            )

        # Validate each model configuration
        for model_id, model_config in config['llm_models'].items():
            errors = self._validate_model_config(model_id, model_config)
            validation_errors.extend(errors)

        if validation_errors:
            raise ModelConfigurationError(
                "Model configuration validation failed",
                config_path=str(self.config_path),
                validation_errors=validation_errors
            )

        # Load models
        self.models = config['llm_models']

        # Load active model selections
        self.active_orchestrator_model = config.get('active_orchestrator_model')
        self.active_implementer_model = config.get('active_implementer_model')

        # Load optimization profiles (optional)
        self.optimization_profiles = config.get('optimization_profiles', {})

        # Validate active model references
        if self.active_orchestrator_model and self.active_orchestrator_model not in self.models:
            logger.warning(
                f"Active orchestrator model '{self.active_orchestrator_model}' not found in models"
            )

        if self.active_implementer_model and self.active_implementer_model not in self.models:
            logger.warning(
                f"Active implementer model '{self.active_implementer_model}' not found in models"
            )

    def _validate_model_config(
        self,
        model_id: str,
        model_config: Dict[str, Any]
    ) -> List[str]:
        """Validate a single model configuration.

        Args:
            model_id: Model identifier
            model_config: Model configuration dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check required fields
        for field in self.REQUIRED_MODEL_FIELDS:
            if field not in model_config:
                errors.append(f"Model '{model_id}': missing required field '{field}'")

        if errors:
            return errors  # Don't continue validation if required fields missing

        # Validate provider
        provider = model_config.get('provider')
        if provider not in self.VALID_PROVIDERS:
            errors.append(
                f"Model '{model_id}': invalid provider '{provider}'. "
                f"Must be one of: {', '.join(self.VALID_PROVIDERS)}"
            )

        # Validate context_window
        context_window = model_config.get('context_window')
        if not isinstance(context_window, int) or context_window <= 0:
            errors.append(
                f"Model '{model_id}': context_window must be a positive integer "
                f"(got: {context_window})"
            )

        # Validate optimization_profile if present
        optimization_profile = model_config.get('optimization_profile')
        if optimization_profile and optimization_profile not in self.VALID_OPTIMIZATION_PROFILES:
            errors.append(
                f"Model '{model_id}': invalid optimization_profile '{optimization_profile}'. "
                f"Must be one of: {', '.join(self.VALID_OPTIMIZATION_PROFILES)}"
            )

        # Validate cost fields if present
        cost_fields = [
            'cost_per_1m_input_tokens',
            'cost_per_1m_output_tokens'
        ]
        for field in cost_fields:
            if field in model_config:
                value = model_config[field]
                if not isinstance(value, (int, float)) or value < 0:
                    errors.append(
                        f"Model '{model_id}': {field} must be a non-negative number "
                        f"(got: {value})"
                    )

        return errors

    def load_models(self, path: str) -> Dict[str, Dict[str, Any]]:
        """Load models from a different configuration file.

        This method allows loading models from a different path than the
        one specified during initialization.

        Args:
            path: Path to models.yaml file

        Returns:
            Dictionary of model configurations

        Raises:
            ModelConfigurationError: If file cannot be loaded or is invalid

        Example:
            >>> loader = ModelConfigLoader()
            >>> custom_models = loader.load_models('config/models-custom.yaml')
        """
        # Temporarily update config path
        original_path = self.config_path
        self.config_path = Path(path)

        try:
            self._load_config()
            return self.models
        except Exception:
            # Restore original path on error
            self.config_path = original_path
            raise

    def get_model(self, model_id: str) -> Dict[str, Any]:
        """Get configuration for a specific model.

        Args:
            model_id: Model identifier (e.g., 'qwen_2_5_32b')

        Returns:
            Model configuration dictionary

        Raises:
            ModelConfigurationError: If model_id not found

        Example:
            >>> loader = ModelConfigLoader()
            >>> qwen = loader.get_model('qwen_2_5_32b')
            >>> print(qwen['provider'])
            ollama
        """
        if model_id not in self.models:
            available_models = ', '.join(sorted(self.models.keys()))
            raise ModelConfigurationError(
                f"Model '{model_id}' not found in configuration. "
                f"Available models: {available_models}",
                config_path=str(self.config_path)
            )

        return self.models[model_id].copy()

    def get_active_orchestrator_config(self) -> Dict[str, Any]:
        """Get configuration for active orchestrator model.

        Returns:
            Active orchestrator model configuration

        Raises:
            ModelConfigurationError: If no active orchestrator model configured

        Example:
            >>> loader = ModelConfigLoader()
            >>> orch_config = loader.get_active_orchestrator_config()
            >>> print(orch_config['model'])
            qwen2.5-coder:32b
        """
        if not self.active_orchestrator_model:
            raise ModelConfigurationError(
                "No active orchestrator model configured. "
                "Set 'active_orchestrator_model' in configuration.",
                config_path=str(self.config_path)
            )

        return self.get_model(self.active_orchestrator_model)

    def get_active_implementer_config(self) -> Dict[str, Any]:
        """Get configuration for active implementer model.

        Returns:
            Active implementer model configuration

        Raises:
            ModelConfigurationError: If no active implementer model configured

        Example:
            >>> loader = ModelConfigLoader()
            >>> impl_config = loader.get_active_implementer_config()
            >>> print(impl_config['model'])
            claude-3-5-sonnet-20241022
        """
        if not self.active_implementer_model:
            raise ModelConfigurationError(
                "No active implementer model configured. "
                "Set 'active_implementer_model' in configuration.",
                config_path=str(self.config_path)
            )

        return self.get_model(self.active_implementer_model)

    def validate_schema(self, config: Dict[str, Any]) -> bool:
        """Validate configuration schema without loading.

        This method validates a configuration dictionary without actually
        loading it into the current instance.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid, False otherwise

        Example:
            >>> loader = ModelConfigLoader()
            >>> test_config = {'llm_models': {...}}
            >>> is_valid = loader.validate_schema(test_config)
        """
        try:
            self._validate_and_load(config)
            return True
        except ModelConfigurationError:
            return False

    def list_models(self) -> List[str]:
        """Get list of all available model IDs.

        Returns:
            List of model identifiers

        Example:
            >>> loader = ModelConfigLoader()
            >>> models = loader.list_models()
            >>> print(models)
            ['phi3_mini', 'qwen_2_5_3b', 'qwen_2_5_32b', 'claude_3_5_sonnet', ...]
        """
        return list(self.models.keys())

    def get_models_by_provider(self, provider: str) -> Dict[str, Dict[str, Any]]:
        """Get all models for a specific provider.

        Args:
            provider: Provider name (ollama, anthropic, openai)

        Returns:
            Dictionary of models for the specified provider

        Example:
            >>> loader = ModelConfigLoader()
            >>> ollama_models = loader.get_models_by_provider('ollama')
            >>> print(len(ollama_models))
            5
        """
        return {
            model_id: config
            for model_id, config in self.models.items()
            if config.get('provider') == provider
        }

    def get_models_by_context_range(
        self,
        min_context: int,
        max_context: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get models within a specific context window range.

        Args:
            min_context: Minimum context window size (inclusive)
            max_context: Maximum context window size (inclusive). If None,
                returns all models with context >= min_context

        Returns:
            Dictionary of models within the specified range

        Example:
            >>> loader = ModelConfigLoader()
            >>> # Get models with 100K-250K context windows
            >>> medium_models = loader.get_models_by_context_range(100000, 250000)
        """
        result = {}
        for model_id, config in self.models.items():
            context_window = config.get('context_window', 0)
            if context_window >= min_context:
                if max_context is None or context_window <= max_context:
                    result[model_id] = config

        return result
