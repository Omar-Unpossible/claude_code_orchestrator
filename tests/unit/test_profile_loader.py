"""Unit tests for test profile loader.

Tests the profile loading, validation, and merging functionality
for multi-LLM testing support.
"""

import os
import pytest
import tempfile
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.testing.profile_loader import (
    load_profile,
    validate_profile,
    merge_with_config,
    check_required_env_vars,
    get_profile_path,
    list_available_profiles,
    ProfileNotFoundError,
    ProfileValidationError,
)
from src.core.config import Config


class TestGetProfilePath:
    """Tests for get_profile_path function."""

    def test_get_profile_path_ollama(self):
        """Test profile path construction for Ollama."""
        path = get_profile_path("ollama")
        assert str(path) == "config/profiles/test-ollama.yaml"
        assert isinstance(path, Path)

    def test_get_profile_path_openai(self):
        """Test profile path construction for OpenAI."""
        path = get_profile_path("openai")
        assert str(path) == "config/profiles/test-openai.yaml"

    def test_get_profile_path_custom(self):
        """Test profile path construction for custom profile."""
        path = get_profile_path("custom-profile")
        assert str(path) == "config/profiles/test-custom-profile.yaml"


class TestListAvailableProfiles:
    """Tests for list_available_profiles function."""

    def test_list_profiles_when_directory_exists(self):
        """Test listing profiles when directory exists."""
        profiles = list_available_profiles()
        # Should at least have ollama and openai profiles
        assert 'ollama' in profiles
        assert 'openai' in profiles
        assert isinstance(profiles, list)
        assert all(isinstance(p, str) for p in profiles)

    def test_list_profiles_when_directory_missing(self, monkeypatch):
        """Test listing profiles when directory doesn't exist."""
        # Mock Path.exists to return False
        def mock_exists(self):
            return False

        monkeypatch.setattr(Path, "exists", mock_exists)
        profiles = list_available_profiles()
        assert profiles == []


class TestCheckRequiredEnvVars:
    """Tests for check_required_env_vars function."""

    def test_all_env_vars_set(self, monkeypatch):
        """Test when all required env vars are set."""
        monkeypatch.setenv("TEST_VAR_1", "value1")
        monkeypatch.setenv("TEST_VAR_2", "value2")

        missing = check_required_env_vars(["TEST_VAR_1", "TEST_VAR_2"])
        assert missing == []

    def test_some_env_vars_missing(self, monkeypatch):
        """Test when some env vars are missing."""
        monkeypatch.setenv("TEST_VAR_1", "value1")
        # TEST_VAR_2 not set

        missing = check_required_env_vars(["TEST_VAR_1", "TEST_VAR_2"])
        assert missing == ["TEST_VAR_2"]

    def test_all_env_vars_missing(self):
        """Test when all env vars are missing."""
        missing = check_required_env_vars(["NONEXISTENT_VAR_1", "NONEXISTENT_VAR_2"])
        assert set(missing) == {"NONEXISTENT_VAR_1", "NONEXISTENT_VAR_2"}

    def test_empty_required_list(self):
        """Test with empty required list."""
        missing = check_required_env_vars([])
        assert missing == []


class TestValidateProfile:
    """Tests for validate_profile function."""

    def test_validate_valid_profile(self):
        """Test validation succeeds for valid profile."""
        profile_data = {
            'profile_name': 'test',
            'llm': {
                'type': 'ollama',
                'model': 'qwen2.5-coder:32b'
            },
            'env_vars': {
                'required': [],
                'optional': []
            }
        }

        # Should not raise
        validate_profile(profile_data, 'test')

    def test_validate_missing_profile_name(self):
        """Test validation fails for missing profile_name."""
        profile_data = {
            'llm': {
                'type': 'ollama',
                'model': 'qwen2.5-coder:32b'
            }
        }

        with pytest.raises(ProfileValidationError, match="Missing required field: profile_name"):
            validate_profile(profile_data)

    def test_validate_missing_llm(self):
        """Test validation fails for missing llm section."""
        profile_data = {
            'profile_name': 'test'
        }

        with pytest.raises(ProfileValidationError, match="Missing required field: llm"):
            validate_profile(profile_data)

    def test_validate_llm_not_dict(self):
        """Test validation fails when llm is not a dict."""
        profile_data = {
            'profile_name': 'test',
            'llm': "not a dict"
        }

        with pytest.raises(ProfileValidationError, match="Field 'llm' must be a dictionary"):
            validate_profile(profile_data)

    def test_validate_missing_llm_type(self):
        """Test validation fails for missing llm.type."""
        profile_data = {
            'profile_name': 'test',
            'llm': {
                'model': 'qwen2.5-coder:32b'
            }
        }

        with pytest.raises(ProfileValidationError, match="Missing required field: llm.type"):
            validate_profile(profile_data)

    def test_validate_missing_llm_model(self):
        """Test validation fails for missing llm.model."""
        profile_data = {
            'profile_name': 'test',
            'llm': {
                'type': 'ollama'
            }
        }

        with pytest.raises(ProfileValidationError, match="Missing required field: llm.model"):
            validate_profile(profile_data)

    def test_validate_invalid_llm_type(self):
        """Test validation fails for invalid llm.type."""
        profile_data = {
            'profile_name': 'test',
            'llm': {
                'type': '',  # Empty string
                'model': 'test'
            }
        }

        with pytest.raises(ProfileValidationError, match="must be a non-empty string"):
            validate_profile(profile_data)

    def test_validate_missing_required_env_vars(self, monkeypatch):
        """Test validation fails when required env vars are missing."""
        # Ensure OPENAI_API_KEY is not set
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        profile_data = {
            'profile_name': 'test',
            'llm': {
                'type': 'openai-codex',
                'model': 'gpt-5-codex'
            },
            'env_vars': {
                'required': ['OPENAI_API_KEY']
            }
        }

        with pytest.raises(ProfileValidationError, match="Required environment variables not set"):
            validate_profile(profile_data)

    def test_validate_env_vars_required_not_list(self):
        """Test validation fails when env_vars.required is not a list."""
        profile_data = {
            'profile_name': 'test',
            'llm': {
                'type': 'ollama',
                'model': 'qwen2.5-coder:32b'
            },
            'env_vars': {
                'required': "not a list"
            }
        }

        with pytest.raises(ProfileValidationError, match="must be a list"):
            validate_profile(profile_data)


class TestMergeWithConfig:
    """Tests for merge_with_config function."""

    def test_merge_overrides_base_values(self):
        """Test that profile values override base config values."""
        base_config = Config.load(defaults_only=True)
        base_config.set('llm.type', 'ollama')
        base_config.set('llm.model', 'base-model')

        profile_data = {
            'llm': {
                'type': 'openai-codex',
                'model': 'gpt-5-codex'
            }
        }

        merged = merge_with_config(profile_data, base_config)

        # Profile values should override
        assert merged.get('llm.type') == 'openai-codex'
        assert merged.get('llm.model') == 'gpt-5-codex'

    def test_merge_preserves_base_values_not_in_profile(self):
        """Test that base values are preserved when not in profile."""
        base_config = Config.load(defaults_only=True)
        # Note: default agent.type is 'mock' from default_config.yaml
        assert base_config.get('agent.type') == 'mock'  # Verify default

        profile_data = {
            'llm': {
                'type': 'openai-codex'
            }
        }

        merged = merge_with_config(profile_data, base_config)

        # Base values should be preserved when not overridden by profile
        assert merged.get('agent.type') == 'mock'  # Preserved from base
        assert merged.get('llm.type') == 'openai-codex'  # From profile

    def test_merge_deep_merges_nested_dicts(self):
        """Test deep merge of nested dictionaries."""
        base_config = Config.load(defaults_only=True)
        base_config.set('llm.type', 'ollama')
        base_config.set('llm.timeout', 120)

        profile_data = {
            'llm': {
                'model': 'gpt-5-codex',  # New field
                'timeout': 60  # Override existing
            }
        }

        merged = merge_with_config(profile_data, base_config)

        # Should have both base and profile values
        assert merged.get('llm.type') == 'ollama'  # From base
        assert merged.get('llm.model') == 'gpt-5-codex'  # From profile
        assert merged.get('llm.timeout') == 60  # Profile overrides


class TestLoadProfile:
    """Tests for load_profile function."""

    def test_load_profile_not_found(self):
        """Test error when profile file doesn't exist."""
        base_config = Config.load(defaults_only=True)

        with pytest.raises(ProfileNotFoundError, match="Profile 'nonexistent' not found"):
            load_profile("nonexistent", base_config)

    def test_load_profile_ollama_success(self):
        """Test loading valid Ollama profile."""
        base_config = Config.load(defaults_only=True)

        # Load Ollama profile (should exist)
        config = load_profile("ollama", base_config)

        # Verify profile was loaded
        assert config.get('llm.type') == 'ollama'
        assert config.get('llm.model') == 'qwen2.5-coder:32b'
        assert config.get('profile_name') == 'ollama'

    def test_load_profile_invalid_yaml(self, tmp_path, monkeypatch):
        """Test error when profile has invalid YAML."""
        # Create invalid YAML file
        profile_path = tmp_path / "test-invalid-yaml.yaml"
        profile_path.write_text("invalid: yaml: syntax: [[[")

        # Mock get_profile_path to return our temp file
        monkeypatch.setattr(
            'src.testing.profile_loader.get_profile_path',
            lambda name: profile_path
        )

        base_config = Config.load(defaults_only=True)

        with pytest.raises(ProfileValidationError, match="Invalid YAML syntax"):
            load_profile("invalid-yaml", base_config)

    def test_load_profile_empty_file(self, tmp_path, monkeypatch):
        """Test error when profile file is empty."""
        # Create empty file
        profile_path = tmp_path / "test-empty.yaml"
        profile_path.write_text("")

        # Mock get_profile_path
        monkeypatch.setattr(
            'src.testing.profile_loader.get_profile_path',
            lambda name: profile_path
        )

        base_config = Config.load(defaults_only=True)

        with pytest.raises(ProfileValidationError, match="empty or contains only comments"):
            load_profile("empty", base_config)

    def test_load_profile_missing_required_field(self, tmp_path, monkeypatch):
        """Test error when profile is missing required fields."""
        # Create profile with missing llm section
        profile_path = tmp_path / "test-missing.yaml"
        profile_path.write_text("profile_name: test-missing\n")

        # Mock get_profile_path
        monkeypatch.setattr(
            'src.testing.profile_loader.get_profile_path',
            lambda name: profile_path
        )

        base_config = Config.load(defaults_only=True)

        with pytest.raises(ProfileValidationError, match="Missing required field: llm"):
            load_profile("missing", base_config)


class TestProfileErrors:
    """Tests for custom exception classes."""

    def test_profile_not_found_error_message(self):
        """Test ProfileNotFoundError message formatting."""
        error = ProfileNotFoundError("test", ["ollama", "openai"])

        assert "test" in str(error)
        assert "ollama" in str(error)
        assert "openai" in str(error)

    def test_profile_not_found_error_without_available(self):
        """Test ProfileNotFoundError without available profiles."""
        error = ProfileNotFoundError("test")

        assert "test" in str(error)
        assert "config/profiles/test-test.yaml" in str(error)

    def test_profile_validation_error_message(self):
        """Test ProfileValidationError message formatting."""
        error = ProfileValidationError("Missing field", "test-profile")

        assert "test-profile" in str(error)
        assert "Missing field" in str(error)

    def test_profile_validation_error_without_profile_name(self):
        """Test ProfileValidationError without profile name."""
        error = ProfileValidationError("Missing field")

        assert "Missing field" in str(error)
        assert "validation failed" in str(error).lower()
