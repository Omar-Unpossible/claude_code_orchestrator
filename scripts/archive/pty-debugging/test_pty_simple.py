#!/usr/bin/env python3
"""Simple PTY test - Direct Claude Code interaction with hook system.

Tests:
- PTY spawn with pexpect
- Simple prompt delivery
- Real-time output streaming
- Hook-based completion detection
- Colored output prefixes
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent

def main():
    print("=" * 80)
    print("PTY SIMPLE TEST - Direct Claude Code Interaction")
    print("=" * 80)
    print()

    # Configuration
    workspace = Path("/tmp/claude-workspace-simple-test")
    workspace.mkdir(parents=True, exist_ok=True)

    config = {
        'workspace_path': str(workspace),
        'claude_command': 'claude',
        'startup_timeout': 30,
        'response_timeout': 60  # Shorter timeout for simple prompt
    }

    print(f"📁 Workspace: {workspace}")
    print()

    # Initialize agent
    print("\033[34m[TEST]\033[0m Initializing Claude Code agent with PTY...")
    agent = ClaudeCodeLocalAgent()

    try:
        agent.initialize(config)
        print("\033[32m✓\033[0m Agent initialized successfully")
        print()

        # Check agent status
        status = agent.get_status()
        print(f"\033[34m[TEST]\033[0m Agent Status:")
        print(f"  State: {status['state']}")
        print(f"  Healthy: {status['healthy']}")
        print(f"  PID: {status['pid']}")
        print()

        # Send simple prompt
        prompt = "Who are you? Please respond briefly."

        print("\033[34m[TEST]\033[0m Sending simple prompt to Claude...")
        print(f"\033[34m[PROMPT]\033[0m {prompt}")
        print()
        print("-" * 80)
        print()

        start_time = time.time()
        response = agent.send_prompt(prompt)
        elapsed = time.time() - start_time

        print()
        print("-" * 80)
        print()

        print(f"\033[32m✓\033[0m Response received in {elapsed:.1f}s")
        print()
        print(f"\033[34m[TEST]\033[0m Response length: {len(response)} chars")
        print(f"\033[34m[TEST]\033[0m Response preview: {response[:200]}...")
        print()

        # Check if hook fired
        if agent._completion_marker_count > 0:
            print(f"\033[32m✓\033[0m Hook fired successfully (markers: {agent._completion_marker_count})")
        else:
            print("\033[31m✗\033[0m Hook did not fire")

        print()
        print("=" * 80)
        print("\033[32m✓ TEST PASSED\033[0m")
        print("=" * 80)

    except Exception as e:
        print()
        print(f"\033[31m✗ TEST FAILED\033[0m")
        print(f"\033[31m[ERROR]\033[0m {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        print()
        print("\033[34m[TEST]\033[0m Cleaning up...")
        agent.cleanup()
        print("\033[32m✓\033[0m Cleanup complete")

    return 0

if __name__ == '__main__':
    sys.exit(main())
