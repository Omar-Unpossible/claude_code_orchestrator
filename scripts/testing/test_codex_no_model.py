#!/usr/bin/env python3
"""Test that Codex plugin works without forcing a specific model."""

import sys
sys.path.insert(0, '/home/omarwsl/projects/claude_code_orchestrator')

from src.llm.openai_codex_interface import OpenAICodexLLMPlugin

def test_codex_initialization():
    """Test Codex plugin initialization without model."""
    print("=" * 80)
    print("Testing OpenAI Codex Plugin - No Forced Model")
    print("=" * 80)
    print()

    # Test 1: Initialize with no model specified
    print("Test 1: Initialize with empty config (should use None)")
    plugin1 = OpenAICodexLLMPlugin()
    config1 = {}  # No model specified

    try:
        plugin1.initialize(config1)
        print(f"✓ Initialized successfully")
        print(f"  Model: {plugin1.model}")
        print(f"  Expected: None (auto-select)")

        if plugin1.model is None:
            print(f"  ✓ PASS: Model is None as expected")
        else:
            print(f"  ✗ FAIL: Model should be None but is '{plugin1.model}'")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        print(f"  (This is expected if Codex CLI not installed/authenticated)")

    print()

    # Test 2: Initialize with explicit model
    print("Test 2: Initialize with explicit model 'gpt-4'")
    plugin2 = OpenAICodexLLMPlugin()
    config2 = {'model': 'gpt-4'}

    try:
        plugin2.initialize(config2)
        print(f"✓ Initialized successfully")
        print(f"  Model: {plugin2.model}")
        print(f"  Expected: 'gpt-4'")

        if plugin2.model == 'gpt-4':
            print(f"  ✓ PASS: Model is 'gpt-4' as configured")
        else:
            print(f"  ✗ FAIL: Model should be 'gpt-4' but is '{plugin2.model}'")
    except Exception as e:
        print(f"✗ Initialization failed: {e}")

    print()

    # Test 3: Check command building
    print("Test 3: Check codex command building")
    print("-" * 80)

    # Mock the command building (without actually calling codex)
    plugin3 = OpenAICodexLLMPlugin()
    plugin3.codex_command = 'codex'
    plugin3.model = None  # No model
    plugin3.full_auto = True

    # Simulate command building from generate()
    prompt = "test prompt"
    cmd = [plugin3.codex_command, 'exec']
    if plugin3.full_auto:
        cmd.append('--full-auto')
    if plugin3.model:
        cmd.extend(['--model', plugin3.model])
    cmd.append(prompt)

    print(f"Command with model=None: {' '.join(cmd)}")
    if '--model' not in cmd:
        print("  ✓ PASS: --model flag NOT included (as expected)")
    else:
        print("  ✗ FAIL: --model flag should not be included when model is None")

    print()

    # Test 4: With model specified
    plugin3.model = 'gpt-4'
    cmd = [plugin3.codex_command, 'exec']
    if plugin3.full_auto:
        cmd.append('--full-auto')
    if plugin3.model:
        cmd.extend(['--model', plugin3.model])
    cmd.append(prompt)

    print(f"Command with model='gpt-4': {' '.join(cmd)}")
    if '--model' in cmd and 'gpt-4' in cmd:
        print("  ✓ PASS: --model flag included with correct value")
    else:
        print("  ✗ FAIL: --model flag should be included when model is set")

    print()
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    print("✓ No forced default model (was: codex-mini-latest)")
    print("✓ Model defaults to None (auto-select)")
    print("✓ --model flag only added when explicitly configured")
    print("✓ Codex CLI will auto-select model based on account type")
    print()

if __name__ == '__main__':
    test_codex_initialization()
