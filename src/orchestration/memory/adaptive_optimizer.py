"""Adaptive Optimization Profiles for context management.

This module implements adaptive optimization that auto-selects compression
strategies based on detected context window size. Provides 5 predefined
profiles ranging from ultra-aggressive (4K contexts) to minimal (1M+ contexts).

Classes:
    AdaptiveOptimizer: Auto-selects and applies optimization profiles
    OptimizationProfile: Data class for profile configuration

Example:
    >>> optimizer = AdaptiveOptimizer(context_window_size=128000)
    >>> if optimizer.should_optimize(item_tokens=600, item_type='phase'):
    ...     # Optimize this item
    ...     pass
    >>> profile = optimizer.get_active_profile()
    >>> print(f"Using profile: {profile['name']}")

Author: Obra System
Created: 2025-01-15
Version: 1.0.0
"""

import logging
import yaml
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class AdaptiveOptimizerException(Exception):
    """Exception raised for adaptive optimizer errors."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize exception.

        Args:
            message: Error message
            context: Additional context about the error
        """
        super().__init__(message)
        self.context = context or {}
        logger.error(f"AdaptiveOptimizerException: {message}", extra=context)


@dataclass
class OptimizationProfile:
    """Optimization profile configuration.

    Attributes:
        name: Profile name (e.g., "Ultra-Aggressive")
        description: Profile description
        context_min: Minimum context window size
        context_max: Maximum context window size
        summarization_threshold: Token threshold for summarization
        externalization_threshold: Token threshold for external storage
        artifact_registry_enabled: Whether to use artifact registry
        differential_state_enabled: Whether to use differential state
        pruning_age_hours: Age threshold for pruning old data
        max_validation_results: Max validation results to keep
        max_resolved_errors: Max resolved errors to keep
        checkpoint_interval_hours: Hours between checkpoints
        checkpoint_threshold_pct: Usage % to trigger checkpoint
        checkpoint_operation_count: Operations before checkpoint
        max_operations: Max operations in working memory
        max_tokens_pct: Max % of context for working memory
    """
    name: str
    description: str
    context_min: int
    context_max: int
    summarization_threshold: int
    externalization_threshold: int
    artifact_registry_enabled: bool
    differential_state_enabled: bool
    pruning_age_hours: float
    max_validation_results: int
    max_resolved_errors: int
    checkpoint_interval_hours: float
    checkpoint_threshold_pct: int
    checkpoint_operation_count: int
    max_operations: int
    max_tokens_pct: float


class AdaptiveOptimizer:
    """Adaptive optimization profile selector and manager.

    Auto-selects optimization profile based on context window size and
    provides methods to check if specific optimizations should be applied.

    Attributes:
        context_window_size: Detected context window size in tokens
        active_profile: Currently active optimization profile
        profiles: Dictionary of all loaded profiles
        manual_override: Optional manual profile override

    Example:
        >>> optimizer = AdaptiveOptimizer(
        ...     context_window_size=128000,
        ...     config_path='config/optimization_profiles.yaml'
        ... )
        >>> optimizer.get_active_profile_name()
        'balanced_aggressive'
        >>> optimizer.should_optimize(500, 'phase')
        False  # 500 tokens < threshold for this profile
    """

    DEFAULT_CONFIG_PATH = 'config/optimization_profiles.yaml'

    def __init__(
        self,
        context_window_size: int,
        config_path: Optional[str] = None,
        manual_override: Optional[str] = None,
        custom_thresholds: Optional[Dict[str, Any]] = None
    ):
        """Initialize adaptive optimizer.

        Args:
            context_window_size: Detected context window size in tokens
            config_path: Path to optimization profiles YAML (optional)
            manual_override: Manual profile name override (optional)
            custom_thresholds: Custom threshold overrides (optional)

        Raises:
            AdaptiveOptimizerException: If configuration is invalid
        """
        if context_window_size <= 0:
            raise AdaptiveOptimizerException(
                "Context window size must be positive",
                context={'context_window_size': context_window_size}
            )

        self.context_window_size = context_window_size
        self.manual_override = manual_override
        self.custom_thresholds = custom_thresholds or {}

        # Load profiles from YAML
        config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.profiles = self._load_profiles(config_path)

        # Select active profile
        self.active_profile = self._select_profile()

        # Apply custom thresholds if provided
        if self.custom_thresholds:
            self._apply_custom_thresholds()

        logger.info(
            f"AdaptiveOptimizer initialized: context={context_window_size:,}, "
            f"profile={self.active_profile.name}, "
            f"overrides={'yes' if custom_thresholds else 'no'}"
        )

    def _load_profiles(self, config_path: str) -> Dict[str, Dict[str, Any]]:
        """Load optimization profiles from YAML file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Dictionary of profile configurations

        Raises:
            AdaptiveOptimizerException: If file not found or invalid
        """
        config_file = Path(config_path)

        if not config_file.exists():
            # Fall back to example file if main config doesn't exist
            example_file = Path(str(config_path) + '.example')
            if example_file.exists():
                config_file = example_file
                logger.warning(
                    f"Config file not found, using example: {example_file}"
                )
            else:
                raise AdaptiveOptimizerException(
                    f"Configuration file not found: {config_path}",
                    context={'config_path': config_path}
                )

        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)

            if 'profiles' not in config:
                raise AdaptiveOptimizerException(
                    "Invalid configuration: missing 'profiles' key"
                )

            logger.debug(
                f"Loaded {len(config['profiles'])} optimization profiles "
                f"from {config_file}"
            )

            return config['profiles']

        except yaml.YAMLError as e:
            raise AdaptiveOptimizerException(
                f"Failed to parse YAML configuration: {e}",
                context={'config_path': config_path, 'error': str(e)}
            )
        except Exception as e:
            raise AdaptiveOptimizerException(
                f"Failed to load configuration: {e}",
                context={'config_path': config_path, 'error': str(e)}
            )

    def _select_profile(self) -> OptimizationProfile:
        """Select appropriate profile based on context window size.

        Returns:
            Selected OptimizationProfile

        Raises:
            AdaptiveOptimizerException: If no suitable profile found
        """
        # Manual override takes precedence
        if self.manual_override:
            if self.manual_override not in self.profiles:
                raise AdaptiveOptimizerException(
                    f"Manual override profile not found: {self.manual_override}",
                    context={'available_profiles': list(self.profiles.keys())}
                )

            profile_data = self.profiles[self.manual_override]
            logger.info(
                f"Using manual profile override: {self.manual_override}"
            )
        else:
            # Auto-select based on context window size
            profile_data = None
            profile_name = None

            for name, data in self.profiles.items():
                if (data['context_min'] <= self.context_window_size <=
                    data['context_max']):
                    profile_data = data
                    profile_name = name
                    break

            if profile_data is None:
                raise AdaptiveOptimizerException(
                    f"No profile found for context window size: "
                    f"{self.context_window_size:,}",
                    context={'context_window_size': self.context_window_size}
                )

            logger.info(
                f"Auto-selected profile '{profile_name}' for context "
                f"{self.context_window_size:,}"
            )

        # Convert to OptimizationProfile dataclass
        return OptimizationProfile(
            name=profile_data['name'],
            description=profile_data['description'],
            context_min=profile_data['context_min'],
            context_max=profile_data['context_max'],
            summarization_threshold=profile_data['summarization_threshold'],
            externalization_threshold=profile_data['externalization_threshold'],
            artifact_registry_enabled=profile_data['artifact_registry_enabled'],
            differential_state_enabled=profile_data['differential_state_enabled'],
            pruning_age_hours=profile_data['pruning_age_hours'],
            max_validation_results=profile_data['max_validation_results'],
            max_resolved_errors=profile_data['max_resolved_errors'],
            checkpoint_interval_hours=profile_data['checkpoint_interval_hours'],
            checkpoint_threshold_pct=profile_data['checkpoint_threshold_pct'],
            checkpoint_operation_count=profile_data['checkpoint_operation_count'],
            max_operations=profile_data['max_operations'],
            max_tokens_pct=profile_data['max_tokens_pct']
        )

    def _apply_custom_thresholds(self) -> None:
        """Apply custom threshold overrides to active profile."""
        for key, value in self.custom_thresholds.items():
            if hasattr(self.active_profile, key):
                setattr(self.active_profile, key, value)
                logger.debug(f"Applied custom threshold: {key}={value}")
            else:
                logger.warning(
                    f"Custom threshold '{key}' not found in profile, ignoring"
                )

    def should_optimize(
        self,
        item_tokens: int,
        item_type: str
    ) -> bool:
        """Check if an item should be optimized based on profile thresholds.

        Args:
            item_tokens: Token count of the item
            item_type: Type of item ('phase', 'artifact', etc.)

        Returns:
            True if item should be optimized (summarized/externalized)
        """
        if item_type == 'phase' or item_type == 'summary':
            return item_tokens > self.active_profile.summarization_threshold

        if item_type == 'artifact' or item_type == 'file':
            return item_tokens > self.active_profile.externalization_threshold

        # Default: use summarization threshold
        return item_tokens > self.active_profile.summarization_threshold

    def get_active_profile(self) -> Dict[str, Any]:
        """Get active profile as dictionary.

        Returns:
            Dictionary with all profile settings
        """
        return {
            'name': self.active_profile.name,
            'description': self.active_profile.description,
            'context_min': self.active_profile.context_min,
            'context_max': self.active_profile.context_max,
            'summarization_threshold': self.active_profile.summarization_threshold,
            'externalization_threshold': self.active_profile.externalization_threshold,
            'artifact_registry_enabled': self.active_profile.artifact_registry_enabled,
            'differential_state_enabled': self.active_profile.differential_state_enabled,
            'pruning_age_hours': self.active_profile.pruning_age_hours,
            'max_validation_results': self.active_profile.max_validation_results,
            'max_resolved_errors': self.active_profile.max_resolved_errors,
            'checkpoint_interval_hours': self.active_profile.checkpoint_interval_hours,
            'checkpoint_threshold_pct': self.active_profile.checkpoint_threshold_pct,
            'checkpoint_operation_count': self.active_profile.checkpoint_operation_count,
            'max_operations': self.active_profile.max_operations,
            'max_tokens_pct': self.active_profile.max_tokens_pct
        }

    def get_active_profile_name(self) -> str:
        """Get name of active profile.

        Returns:
            Profile name (e.g., "Balanced-Aggressive")
        """
        return self.active_profile.name

    def should_use_artifact_registry(self) -> bool:
        """Check if artifact registry optimization should be used.

        Returns:
            True if artifact registry should be enabled
        """
        return self.active_profile.artifact_registry_enabled

    def should_use_differential_state(self) -> bool:
        """Check if differential state optimization should be used.

        Returns:
            True if differential state should be enabled
        """
        return self.active_profile.differential_state_enabled

    def get_checkpoint_config(self) -> Dict[str, Any]:
        """Get checkpoint configuration from active profile.

        Returns:
            Dictionary with checkpoint settings
        """
        return {
            'interval_hours': self.active_profile.checkpoint_interval_hours,
            'threshold_pct': self.active_profile.checkpoint_threshold_pct,
            'operation_count': self.active_profile.checkpoint_operation_count
        }

    def get_working_memory_config(self) -> Dict[str, Any]:
        """Get working memory configuration from active profile.

        Returns:
            Dictionary with working memory settings
        """
        return {
            'max_operations': self.active_profile.max_operations,
            'max_tokens_pct': self.active_profile.max_tokens_pct,
            'max_tokens': int(
                self.context_window_size * self.active_profile.max_tokens_pct
            )
        }

    def get_pruning_config(self) -> Dict[str, Any]:
        """Get pruning configuration from active profile.

        Returns:
            Dictionary with pruning settings
        """
        return {
            'age_hours': self.active_profile.pruning_age_hours,
            'max_validation_results': self.active_profile.max_validation_results,
            'max_resolved_errors': self.active_profile.max_resolved_errors
        }

    def __repr__(self) -> str:
        """String representation of optimizer."""
        return (
            f"AdaptiveOptimizer(context={self.context_window_size:,}, "
            f"profile={self.active_profile.name})"
        )
