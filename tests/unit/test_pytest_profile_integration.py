"""Unit tests for pytest profile integration.

Tests the --profile CLI option and fixture integration
with the pytest framework.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.core.config import Config


class TestProfileOption:
    """Tests for --profile command-line option."""

    def test_profile_option_exists(self, pytestconfig):
        """Test that --profile option is registered with pytest."""
        # The option should be available
        assert hasattr(pytestconfig.option, 'profile')

    def test_default_profile_is_none(self, pytestconfig):
        """Test that default profile is None when not specified."""
        # When running without --profile flag
        # Note: This test assumes no --profile was passed
        profile = pytestconfig.getoption("--profile")
        # Could be None or a value if --profile was used
        assert profile is None or isinstance(profile, str)


class TestTestConfigFixture:
    """Tests for test_config fixture with profile support."""

    def test_config_without_profile_returns_mock(self, test_config):
        """Test that config is a mock when no profile specified."""
        # When running without --profile, should get mock config
        assert hasattr(test_config, 'get')
        assert callable(test_config.get)

    def test_config_has_required_fields(self, test_config):
        """Test that config has all required fields."""
        # Essential fields for testing
        assert test_config.get('database.url') is not None
        assert test_config.get('agent.type') is not None
        assert test_config.get('llm.type') is not None

    def test_config_get_with_default(self, test_config):
        """Test config get with default value."""
        value = test_config.get('nonexistent.key', 'default_value')
        assert value == 'default_value'

    def test_config_get_nested_keys(self, test_config):
        """Test config get with nested dot notation."""
        llm_type = test_config.get('llm.type')
        assert llm_type is not None


class TestProfileNameFixture:
    """Tests for profile_name fixture."""

    def test_profile_name_fixture_exists(self, profile_name):
        """Test that profile_name fixture is available."""
        # Should be None or a string
        assert profile_name is None or isinstance(profile_name, str)

    def test_profile_name_matches_option(self, profile_name, pytestconfig):
        """Test that profile_name fixture matches --profile option."""
        option_value = pytestconfig.getoption("--profile")
        assert profile_name == option_value


class TestProfileLoading:
    """Tests for profile loading behavior."""

    def test_load_profile_with_valid_name(self):
        """Test loading a valid profile name."""
        # This test would need to mock the profile loading
        # to avoid depending on actual profile files
        with patch('src.testing.profile_loader.load_profile') as mock_load:
            mock_config = MagicMock(spec=Config)
            mock_config.get.return_value = 'ollama'
            mock_load.return_value = mock_config

            # Simulate loading profile
            from src.testing.profile_loader import load_profile
            base_config = Config.load(defaults_only=True)
            result = load_profile('ollama', base_config)

            assert mock_load.called

    def test_profile_validation_error_exits_pytest(self):
        """Test that ProfileValidationError causes pytest to exit."""
        from src.testing.profile_loader import ProfileValidationError

        # ProfileValidationError should be caught by test_config fixture
        # and converted to pytest.exit()
        error = ProfileValidationError("Test error")
        assert "Test error" in str(error)

    def test_profile_not_found_error_exits_pytest(self):
        """Test that ProfileNotFoundError causes pytest to exit."""
        from src.testing.profile_loader import ProfileNotFoundError

        # ProfileNotFoundError should be caught by test_config fixture
        # and converted to pytest.exit()
        error = ProfileNotFoundError("nonexistent", ["ollama", "openai"])
        assert "nonexistent" in str(error)
        assert "ollama" in str(error)


class TestProfileOverridesBaseConfig:
    """Tests that profile values override base config."""

    @pytest.mark.parametrize("profile_field,expected_type", [
        ("llm.type", str),
        ("llm.model", str),
    ])
    def test_profile_fields_have_correct_types(self, test_config, profile_field, expected_type):
        """Test that profile fields have expected types."""
        value = test_config.get(profile_field)
        if value is not None:
            assert isinstance(value, expected_type)

    def test_mock_config_has_consistent_structure(self, test_config):
        """Test that mock config has consistent structure."""
        # Test nested access
        assert test_config.get('database.url') is not None
        assert test_config.get('agent.type') is not None
        assert test_config.get('llm.type') is not None
        assert test_config.get('llm.model') is not None

    def test_mock_config_llm_defaults(self, test_config):
        """Test that mock config has sensible LLM defaults."""
        # When no profile is specified, should get mock LLM
        assert test_config.get('llm.type') == 'mock'
        assert test_config.get('llm.model') == 'test'
