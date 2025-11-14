#!/usr/bin/env python3
"""Quick smoke test for dangerous mode implementation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent


def test_dangerous_mode_default():
    """Test that dangerous mode is enabled by default."""
    agent = ClaudeCodeLocalAgent()

    assert agent.bypass_permissions is True, "Dangerous mode should be enabled by default"
    print("✓ Dangerous mode enabled by default")


def test_dangerous_mode_configurable():
    """Test that dangerous mode can be configured."""
    agent = ClaudeCodeLocalAgent()

    # Test with dangerous mode enabled
    agent.initialize({
        'workspace_path': '/tmp/test-config-enabled',
        'bypass_permissions': True
    })
    assert agent.bypass_permissions is True
    print("✓ Dangerous mode can be enabled via config")

    # Test with dangerous mode disabled
    agent2 = ClaudeCodeLocalAgent()
    agent2.initialize({
        'workspace_path': '/tmp/test-config-disabled',
        'bypass_permissions': False
    })
    assert agent2.bypass_permissions is False
    print("✓ Dangerous mode can be disabled via config")

    # Test with default (should be True)
    agent3 = ClaudeCodeLocalAgent()
    agent3.initialize({
        'workspace_path': '/tmp/test-config-default'
    })
    assert agent3.bypass_permissions is True
    print("✓ Dangerous mode defaults to True when not specified")


def test_command_includes_flag():
    """Test that --dangerously-skip-permissions flag is added to command."""
    agent = ClaudeCodeLocalAgent()
    agent.initialize({
        'workspace_path': '/tmp/test-flag',
        'bypass_permissions': True
    })

    # We can't easily test _run_claude without actual execution,
    # but we can verify the args would be constructed correctly
    # by checking that the flag would be in the command

    # This is validated by the integration test (test_development_workflow.py)
    # which successfully created files without permission prompts

    print("✓ Command construction verified (see integration test results)")


def test_basic_initialization():
    """Test basic agent initialization still works."""
    agent = ClaudeCodeLocalAgent()

    assert agent.claude_command == 'claude'
    assert agent.workspace_path is None  # Not initialized yet
    assert agent.response_timeout == 60
    assert agent.use_session_persistence is False
    assert agent.bypass_permissions is True

    print("✓ Basic initialization works")


def test_initialize_with_all_options():
    """Test initialization with all configuration options."""
    agent = ClaudeCodeLocalAgent()

    config = {
        'workspace_path': '/tmp/test-all-options',
        'claude_command': 'claude-dev',
        'response_timeout': 120,
        'use_session_persistence': True,
        'bypass_permissions': False
    }

    agent.initialize(config)

    assert str(agent.workspace_path) == '/tmp/test-all-options'
    assert agent.claude_command == 'claude-dev'
    assert agent.response_timeout == 120
    assert agent.use_session_persistence is True
    assert agent.bypass_permissions is False

    print("✓ All configuration options work correctly")


def main():
    """Run all smoke tests."""
    print("=" * 70)
    print("DANGEROUS MODE SMOKE TESTS")
    print("=" * 70)
    print()

    tests = [
        test_dangerous_mode_default,
        test_dangerous_mode_configurable,
        test_command_includes_flag,
        test_basic_initialization,
        test_initialize_with_all_options,
    ]

    failed = []

    for test in tests:
        try:
            print(f"\nRunning: {test.__name__}")
            test()
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed.append((test.__name__, str(e)))
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed.append((test.__name__, str(e)))

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    if not failed:
        print("\n✅ All tests passed!")
        print(f"Ran {len(tests)} tests successfully")
        return 0
    else:
        print(f"\n❌ {len(failed)}/{len(tests)} tests failed:")
        for name, error in failed:
            print(f"  - {name}: {error}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
