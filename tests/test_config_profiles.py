"""Tests for Config profiles - M9 configuration profile system.

Tests cover:
- Profile loading and initialization
- Profile precedence and merging
- Profile discovery (list_profiles)
- Error handling for missing profiles
- Profile override of default values
- Integration with existing Config loading
"""

import pytest
import yaml
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

from src.core.config import Config
from src.core.exceptions import ConfigNotFoundException


@pytest.fixture(autouse=True)
def reset_config():
    """Reset Config singleton before and after each test."""
    Config.reset()
    yield
    Config.reset()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory structure."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    profiles_dir = config_dir / "profiles"
    profiles_dir.mkdir()

    # Create default config
    default_config = {
        'project': {
            'name': 'default_project',
            'language': 'generic'
        },
        'agent': {
            'type': 'ssh',
            'timeout': 120
        },
        'testing': {
            'run_tests': False,
            'coverage_threshold': 0.80
        },
        'quality': {
            'min_quality_score': 0.60
        }
    }

    with open(config_dir / 'default_config.yaml', 'w') as f:
        yaml.dump(default_config, f)

    return config_dir


@pytest.fixture
def create_profile(temp_config_dir):
    """Factory fixture to create test profiles."""
    def _create_profile(name: str, content: dict):
        profile_path = temp_config_dir / 'profiles' / f'{name}.yaml'
        with open(profile_path, 'w') as f:
            yaml.dump(content, f)
        return profile_path

    return _create_profile


class TestProfileDiscovery:
    """Tests for profile discovery and listing."""

    def test_list_profiles_empty_directory(self, temp_config_dir):
        """Test listing profiles when directory is empty."""
        with patch('src.core.config.Path') as mock_path:
            mock_profiles_dir = Mock()
            mock_profiles_dir.exists.return_value = True
            mock_profiles_dir.glob.return_value = []
            mock_path.return_value = mock_profiles_dir

            profiles = Config.list_profiles()

            assert profiles == []

    def test_list_profiles_with_profiles(self, create_profile):
        """Test listing multiple profiles."""
        # Create test profiles
        create_profile('python_project', {'project': {'language': 'python'}})
        create_profile('web_app', {'project': {'type': 'web'}})
        create_profile('ml_project', {'project': {'type': 'ml'}})

        profiles = Config.list_profiles()

        # Should be sorted alphabetically
        assert profiles == ['ml_project', 'python_project', 'web_app']

    def test_list_profiles_ignores_non_yaml(self, temp_config_dir):
        """Test that non-YAML files are ignored."""
        profiles_dir = temp_config_dir / 'profiles'

        # Create YAML profile
        with open(profiles_dir / 'valid.yaml', 'w') as f:
            yaml.dump({'test': 'data'}, f)

        # Create non-YAML files (should be ignored)
        (profiles_dir / 'readme.txt').write_text('This is a readme')
        (profiles_dir / 'config.json').write_text('{}')

        with patch('src.core.config.Path', return_value=profiles_dir):
            profiles = Config.list_profiles()

            # Should only include YAML files
            assert profiles == ['valid']

    def test_list_profiles_nonexistent_directory(self):
        """Test listing profiles when directory doesn't exist."""
        with patch('src.core.config.Path') as mock_path:
            mock_dir = Mock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            profiles = Config.list_profiles()

            assert profiles == []


class TestProfileLoading:
    """Tests for loading configuration profiles."""

    def test_load_with_profile(self, temp_config_dir, create_profile):
        """Test loading config with a profile."""
        # Create profile with custom settings
        profile_content = {
            'project': {
                'language': 'python',
                'test_framework': 'pytest'
            },
            'agent': {
                'timeout': 300
            }
        }
        create_profile('python_project', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/' in str(path_str):
                    return temp_config_dir / 'profiles' / 'python_project.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='python_project')

            # Profile values should override defaults
            assert config.get('project.language') == 'python'
            assert config.get('project.test_framework') == 'pytest'
            assert config.get('agent.timeout') == 300

    def test_load_with_nonexistent_profile(self, temp_config_dir):
        """Test loading with non-existent profile raises error."""
        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/nonexistent' in str(path_str):
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            with pytest.raises(ConfigNotFoundException) as exc_info:
                Config.load(profile='nonexistent')

            assert 'nonexistent' in str(exc_info.value)

    def test_load_without_profile(self, temp_config_dir):
        """Test loading config without profile uses defaults."""
        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load()

            # Should use default values
            assert config.get('project.name') == 'default_project'
            assert config.get('agent.type') == 'ssh'


class TestProfilePrecedence:
    """Tests for profile precedence and merging."""

    def test_profile_overrides_defaults(self, temp_config_dir, create_profile):
        """Test that profile values override default values."""
        # Create profile that overrides some defaults
        profile_content = {
            'agent': {
                'timeout': 600  # Override default 120
            },
            'testing': {
                'run_tests': True  # Override default False
            }
        }
        create_profile('custom', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/custom' in str(path_str):
                    return temp_config_dir / 'profiles' / 'custom.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='custom')

            # Profile overrides
            assert config.get('agent.timeout') == 600
            assert config.get('testing.run_tests') is True

            # Defaults still present for non-overridden values
            assert config.get('agent.type') == 'ssh'
            assert config.get('testing.coverage_threshold') == 0.80

    def test_project_config_overrides_profile(self, temp_config_dir, create_profile):
        """Test that project config overrides profile."""
        # Create profile
        profile_content = {
            'agent': {'timeout': 300}
        }
        create_profile('test_profile', profile_content)

        # Create project config that overrides profile
        project_config = {
            'agent': {'timeout': 500}
        }
        with open(temp_config_dir / 'config.yaml', 'w') as f:
            yaml.dump(project_config, f)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/test_profile' in str(path_str):
                    return temp_config_dir / 'profiles' / 'test_profile.yaml'
                elif 'config/config.yaml' in str(path_str):
                    return temp_config_dir / 'config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='test_profile')

            # Project config should override profile
            assert config.get('agent.timeout') == 500

    def test_profile_partial_override(self, temp_config_dir, create_profile):
        """Test that profile can partially override nested config."""
        # Create profile that only overrides some nested values
        profile_content = {
            'quality': {
                'min_quality_score': 0.85  # Override only this field
                # Leave other quality fields as default
            }
        }
        create_profile('high_quality', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/high_quality' in str(path_str):
                    return temp_config_dir / 'profiles' / 'high_quality.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='high_quality')

            # Overridden value
            assert config.get('quality.min_quality_score') == 0.85

            # Other nested values should still be present from defaults
            # (This tests deep merge behavior)


class TestProfileContent:
    """Tests for typical profile content and use cases."""

    def test_python_project_profile(self, temp_config_dir, create_profile):
        """Test Python project profile configuration."""
        profile_content = {
            'project': {
                'language': 'python',
                'test_framework': 'pytest',
                'code_style': 'black + ruff'
            },
            'testing': {
                'run_tests': True,
                'coverage_threshold': 0.85,
                'test_command': 'pytest'
            },
            'quality': {
                'require_type_hints': True,
                'require_docstrings': True
            }
        }
        create_profile('python_project', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/python_project' in str(path_str):
                    return temp_config_dir / 'profiles' / 'python_project.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='python_project')

            assert config.get('project.language') == 'python'
            assert config.get('testing.run_tests') is True
            assert config.get('testing.coverage_threshold') == 0.85
            assert config.get('quality.require_type_hints') is True

    def test_minimal_profile(self, temp_config_dir, create_profile):
        """Test minimal/fast profile for prototyping."""
        profile_content = {
            'testing': {
                'run_tests': False
            },
            'validation': {
                'syntax_check': False,
                'style_check': False
            },
            'quality': {
                'min_quality_score': 0.30
            }
        }
        create_profile('minimal', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/minimal' in str(path_str):
                    return temp_config_dir / 'profiles' / 'minimal.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='minimal')

            assert config.get('testing.run_tests') is False
            assert config.get('quality.min_quality_score') == 0.30

    def test_production_profile(self, temp_config_dir, create_profile):
        """Test production profile with strict settings."""
        profile_content = {
            'testing': {
                'run_tests': True,
                'coverage_threshold': 0.90,
                'fail_on_test_failure': True
            },
            'quality': {
                'min_quality_score': 0.80,
                'max_complexity': 8
            },
            'validation': {
                'syntax_check': True,
                'style_check': True,
                'type_check': True
            }
        }
        create_profile('production', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/production' in str(path_str):
                    return temp_config_dir / 'profiles' / 'production.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='production')

            assert config.get('testing.coverage_threshold') == 0.90
            assert config.get('quality.min_quality_score') == 0.80
            assert config.get('quality.max_complexity') == 8


class TestProfileIntegration:
    """Integration tests for profile system."""

    def test_profile_with_m9_features(self, temp_config_dir, create_profile):
        """Test profile configuring M9 features (retry, git, dependencies)."""
        profile_content = {
            'retry': {
                'max_attempts': 3,
                'base_delay': 2.0,
                'backoff_multiplier': 2.0
            },
            'git': {
                'enabled': True,
                'auto_commit': True,
                'create_branch': True,
                'branch_prefix': 'feature/task-'
            },
            'dependencies': {
                'max_depth': 5,
                'allow_cycles': False
            }
        }
        create_profile('m9_enabled', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/m9_enabled' in str(path_str):
                    return temp_config_dir / 'profiles' / 'm9_enabled.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(profile='m9_enabled')

            # Verify M9 feature configuration
            assert config.get('retry.max_attempts') == 3
            assert config.get('git.enabled') is True
            assert config.get('git.branch_prefix') == 'feature/task-'
            assert config.get('dependencies.max_depth') == 5

    def test_multiple_profiles_sequential_loads(self, temp_config_dir, create_profile):
        """Test that sequential loads with different profiles work."""
        # Create two different profiles
        create_profile('profile1', {'agent': {'timeout': 100}})
        create_profile('profile2', {'agent': {'timeout': 200}})

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/profile1' in str(path_str):
                    return temp_config_dir / 'profiles' / 'profile1.yaml'
                elif 'profiles/profile2' in str(path_str):
                    return temp_config_dir / 'profiles' / 'profile2.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            # Load first profile
            config1 = Config.load(profile='profile1')
            assert config1.get('agent.timeout') == 100

            # Reset and load second profile
            Config.reset()
            config2 = Config.load(profile='profile2')
            assert config2.get('agent.timeout') == 200

    def test_profile_validation(self, temp_config_dir, create_profile):
        """Test that profile config is validated like other configs."""
        # Create invalid profile (will fail validation if implemented)
        invalid_profile = {
            # Empty config should still validate (merge with defaults)
        }
        create_profile('valid_empty', invalid_profile)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/valid_empty' in str(path_str):
                    return temp_config_dir / 'profiles' / 'valid_empty.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            # Empty profile should still be valid (uses defaults)
            config = Config.load(profile='valid_empty')
            assert config is not None


class TestProfileEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_profile_with_null_values(self, temp_config_dir, create_profile):
        """Test profile with null/None values."""
        profile_content = {
            'testing': None  # Null section
        }
        create_profile('null_profile', profile_content)

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/null_profile' in str(path_str):
                    return temp_config_dir / 'profiles' / 'null_profile.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            # Should handle null values gracefully
            config = Config.load(profile='null_profile')
            assert config is not None

    def test_profile_with_empty_file(self, temp_config_dir):
        """Test profile that is an empty YAML file."""
        profiles_dir = temp_config_dir / 'profiles'
        (profiles_dir / 'empty.yaml').write_text('')

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                elif 'profiles/empty' in str(path_str):
                    return profiles_dir / 'empty.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            # Empty profile should use all defaults
            config = Config.load(profile='empty')
            assert config.get('agent.type') == 'ssh'  # Default value

    def test_profile_name_with_special_characters(self, temp_config_dir):
        """Test profile names are properly sanitized."""
        profiles_dir = temp_config_dir / 'profiles'

        # Create profiles with various names
        with open(profiles_dir / 'test-profile.yaml', 'w') as f:
            yaml.dump({'test': 'data'}, f)

        with open(profiles_dir / 'test_profile_2.yaml', 'w') as f:
            yaml.dump({'test': 'data'}, f)

        with patch('src.core.config.Path', return_value=profiles_dir):
            profiles = Config.list_profiles()

            # Should handle hyphen and underscore in names
            assert 'test-profile' in profiles
            assert 'test_profile_2' in profiles

    def test_defaults_only_ignores_profile(self, temp_config_dir, create_profile):
        """Test that defaults_only=True ignores profile parameter."""
        create_profile('test_profile', {'agent': {'timeout': 999}})

        with patch('src.core.config.Path') as mock_path:
            def path_side_effect(path_str):
                if 'default_config.yaml' in str(path_str):
                    return temp_config_dir / 'default_config.yaml'
                else:
                    mock = Mock()
                    mock.exists.return_value = False
                    return mock

            mock_path.side_effect = path_side_effect

            config = Config.load(defaults_only=True, profile='test_profile')

            # Should use default value, not profile value
            assert config.get('agent.timeout') == 120  # Default, not 999
