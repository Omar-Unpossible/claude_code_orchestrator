"""Integration tests for test profile system.

Tests the complete end-to-end functionality of the test profile system,
including profile loading, validation, pytest integration, and LLM connection.
"""

import os
import pytest
from src.testing.profile_loader import (
    load_profile,
    ProfileNotFoundError,
    ProfileValidationError,
)
from src.core.config import Config


class TestProfileSystemE2E:
    """End-to-end tests for profile system."""

    def test_profile_ollama_loads_successfully(self):
        """Test that Ollama profile loads without errors."""
        base_config = Config.load(defaults_only=True)

        # Load Ollama profile
        config = load_profile("ollama", base_config)

        # Verify profile loaded correctly
        assert config.get('profile_name') == 'ollama'
        assert config.get('llm.type') == 'ollama'
        assert config.get('llm.model') == 'qwen2.5-coder:32b'
        assert config.get('llm.api_url') == 'http://localhost:11434'

    def test_profile_openai_requires_api_key(self):
        """Test that OpenAI profile validates required API key."""
        # Ensure API key is not set
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']

        base_config = Config.load(defaults_only=True)

        # Should raise validation error for missing API key
        with pytest.raises(ProfileValidationError, match="OPENAI_API_KEY"):
            load_profile("openai", base_config)

    @pytest.mark.skip(reason="Requires OPENAI_API_KEY - run manually with API key")
    def test_profile_openai_loads_with_api_key(self):
        """Test that OpenAI profile loads when API key is set.

        To run this test:
            export OPENAI_API_KEY=sk-...
            pytest --profile=openai tests/integration/test_profile_system_e2e.py::TestProfileSystemE2E::test_profile_openai_loads_with_api_key -v
        """
        # This test is skipped by default
        # Remove skip marker and run manually when API key is available
        base_config = Config.load(defaults_only=True)

        # Load OpenAI profile
        config = load_profile("openai", base_config)

        # Verify profile loaded
        assert config.get('profile_name') == 'openai-codex'
        assert config.get('llm.type') == 'openai-codex'
        assert config.get('llm.model') == 'gpt-5-codex'

    def test_profile_config_overrides_base(self):
        """Test that profile values override base config."""
        base_config = Config.load(defaults_only=True)

        # Set base value
        base_llm_type = base_config.get('llm.type')

        # Load Ollama profile
        config = load_profile("ollama", base_config)

        # Profile should override base
        assert config.get('llm.type') == 'ollama'
        assert config.get('llm.model') == 'qwen2.5-coder:32b'

        # But original base config should be unchanged
        assert base_config.get('llm.type') == base_llm_type


class TestPytestProfileIntegration:
    """Tests for pytest --profile integration."""

    def test_test_config_fixture_with_profile(self, test_config, profile_name):
        """Test that test_config fixture respects profile."""
        if profile_name is None:
            # No profile specified, should get mock config
            assert test_config.get('llm.type') == 'mock'
        else:
            # Profile specified, should get real config
            assert test_config.get('profile_name') is not None
            assert test_config.get('llm.type') is not None

    def test_profile_name_fixture(self, profile_name):
        """Test that profile_name fixture provides profile name."""
        # Should be None (no profile) or string (profile specified)
        assert profile_name is None or isinstance(profile_name, str)

    def test_config_has_llm_settings(self, test_config):
        """Test that config has required LLM settings."""
        # All configs should have LLM type and model
        assert test_config.get('llm.type') is not None
        assert test_config.get('llm.model') is not None


class TestProfileSwitching:
    """Tests for switching between profiles."""

    def test_can_load_different_profiles_sequentially(self):
        """Test loading multiple profiles in sequence."""
        base_config = Config.load(defaults_only=True)

        # Load Ollama profile
        ollama_config = load_profile("ollama", base_config)
        assert ollama_config.get('llm.type') == 'ollama'
        assert ollama_config.get('llm.model') == 'qwen2.5-coder:32b'

        # Load OpenAI profile (skip if no API key)
        if os.getenv('OPENAI_API_KEY'):
            openai_config = load_profile("openai", base_config)
            assert openai_config.get('llm.type') == 'openai-codex'
            assert openai_config.get('llm.model') == 'gpt-5-codex'

            # Verify they're different
            assert ollama_config.get('llm.type') != openai_config.get('llm.type')

    def test_profile_switching_no_state_pollution(self):
        """Test that switching profiles doesn't pollute state."""
        base_config = Config.load(defaults_only=True)

        # Load first profile
        config1 = load_profile("ollama", base_config)
        llm_type_1 = config1.get('llm.type')

        # Load second profile
        config2 = load_profile("ollama", base_config)
        llm_type_2 = config2.get('llm.type')

        # Should be same values (no pollution)
        assert llm_type_1 == llm_type_2


class TestErrorHandling:
    """Tests for error handling in profile system."""

    def test_nonexistent_profile_raises_error(self):
        """Test that loading nonexistent profile raises clear error."""
        base_config = Config.load(defaults_only=True)

        with pytest.raises(ProfileNotFoundError) as exc_info:
            load_profile("nonexistent-profile", base_config)

        # Error should list available profiles
        error_message = str(exc_info.value)
        assert "nonexistent-profile" in error_message
        assert "ollama" in error_message  # Should show available profiles

    def test_invalid_profile_structure_raises_error(self, tmp_path, monkeypatch):
        """Test that invalid profile structure is detected."""
        # Create invalid profile (missing llm section)
        invalid_profile = tmp_path / "test-invalid.yaml"
        invalid_profile.write_text("profile_name: invalid\n")

        # Mock get_profile_path to return our invalid profile
        monkeypatch.setattr(
            'src.testing.profile_loader.get_profile_path',
            lambda name: invalid_profile
        )

        base_config = Config.load(defaults_only=True)

        with pytest.raises(ProfileValidationError, match="Missing required field: llm"):
            load_profile("invalid", base_config)


class TestRealLLMConnection:
    """Tests for actual LLM connection (optional, requires running LLM)."""

    @pytest.mark.skip(reason="Requires Ollama running - run manually")
    def test_ollama_profile_connects_to_llm(self, test_config):
        """Test that Ollama profile can connect to real LLM.

        To run this test:
            1. Ensure Ollama is running: curl http://localhost:11434/api/tags
            2. Run: pytest --profile=ollama tests/integration/test_profile_system_e2e.py::TestRealLLMConnection::test_ollama_profile_connects_to_llm -v
        """
        from src.llm.llm_plugin_manager import LLMPluginManager

        # This test should run with --profile=ollama
        assert test_config.get('llm.type') == 'ollama'

        # Try to create LLM plugin
        llm = LLMPluginManager.create_llm_plugin(test_config)
        assert llm is not None

        # Try to send a simple prompt
        response = llm.generate("Hello, test")
        assert response is not None
        assert len(response) > 0

    @pytest.mark.skip(reason="Requires OPENAI_API_KEY and costs money - run manually")
    def test_openai_profile_connects_to_llm(self, test_config):
        """Test that OpenAI profile can connect to real LLM.

        To run this test:
            1. Set API key: export OPENAI_API_KEY=sk-...
            2. Run: pytest --profile=openai tests/integration/test_profile_system_e2e.py::TestRealLLMConnection::test_openai_profile_connects_to_llm -v
        """
        from src.llm.llm_plugin_manager import LLMPluginManager

        # This test should run with --profile=openai
        assert test_config.get('llm.type') == 'openai-codex'

        # Try to create LLM plugin
        llm = LLMPluginManager.create_llm_plugin(test_config)
        assert llm is not None

        # Try to send a simple prompt
        response = llm.generate("Hello, test")
        assert response is not None
        assert len(response) > 0
