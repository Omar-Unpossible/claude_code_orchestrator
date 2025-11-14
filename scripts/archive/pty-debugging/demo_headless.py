#!/usr/bin/env python3
"""Simple demo of headless mode ClaudeCodeLocalAgent.

This script demonstrates the headless agent working end-to-end with a real
task: creating a simple Python script.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent


def main():
    """Run a simple demo of the headless agent."""
    print("=" * 70)
    print("HEADLESS MODE DEMO - Claude Code Local Agent")
    print("=" * 70)
    print()

    # Setup
    workspace = Path('/tmp/demo-headless-workspace')
    if workspace.exists():
        import shutil
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    print(f"Workspace: {workspace}")
    print()

    # Create and initialize agent
    print("Initializing agent...")
    agent = ClaudeCodeLocalAgent()

    config = {
        'workspace_path': str(workspace),
        'claude_command': 'claude',
        'response_timeout': 60
    }

    agent.initialize(config)
    print(f"✓ Agent initialized")
    print(f"  Session ID: {agent.session_id}")
    print(f"  Mode: headless (--print)")
    print()

    # Test 1: Simple prompt
    print("-" * 70)
    print("TEST 1: Ask Claude to create a simple Python script")
    print("-" * 70)

    prompt = """Create a Python script called 'hello.py' that prints 'Hello from headless mode!'
and includes a function to greet by name. Make it executable."""

    print(f"Prompt: {prompt[:80]}...")
    print()
    print("Sending to Claude Code...")

    start = time.time()
    try:
        response = agent.send_prompt(prompt)
        elapsed = time.time() - start

        print(f"✓ Response received in {elapsed:.1f}s")
        print()
        print("Response preview:")
        print("-" * 70)
        print(response[:500] + ("..." if len(response) > 500 else ""))
        print("-" * 70)
        print()

    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

    # Check workspace files
    print("-" * 70)
    print("TEST 2: Check workspace files")
    print("-" * 70)

    files = agent.get_workspace_files()
    print(f"Files created: {len(files)}")

    for file in files:
        print(f"  - {file.relative_to(workspace)}")

    print()

    # Read the file if it exists
    if files:
        print("-" * 70)
        print("TEST 3: Read created file")
        print("-" * 70)

        for file in files:
            if file.name.endswith('.py'):
                print(f"Reading: {file.name}")
                try:
                    content = agent.read_file(file)
                    print()
                    print("Content:")
                    print("-" * 70)
                    print(content)
                    print("-" * 70)
                except Exception as e:
                    print(f"✗ Error reading file: {e}")

    # Test health check
    print()
    print("-" * 70)
    print("TEST 4: Health check")
    print("-" * 70)

    healthy = agent.is_healthy()
    print(f"Agent healthy: {healthy}")

    status = agent.get_status()
    print(f"Status: {status}")
    print()

    # Cleanup
    print("-" * 70)
    print("Cleanup")
    print("-" * 70)
    agent.cleanup()
    print("✓ Agent cleanup complete")
    print()

    # Final summary
    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  ✓ Agent initialized successfully")
    print(f"  ✓ Sent prompt and received response in {elapsed:.1f}s")
    print(f"  ✓ Created {len(files)} file(s)")
    print(f"  ✓ Health check: {'PASS' if healthy else 'FAIL'}")
    print()
    print("Headless mode is WORKING! 🎉")
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
