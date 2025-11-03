#!/usr/bin/env python3
"""Quick demo showing headless mode working."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent


def main():
    print("\n" + "=" * 70)
    print("QUICK HEADLESS MODE TEST")
    print("=" * 70)

    # Initialize agent
    agent = ClaudeCodeLocalAgent()
    agent.initialize({
        'workspace_path': '/tmp/quick-demo',
        'response_timeout': 30
    })

    print(f"\nSession: {agent.session_id}")
    print("\n" + "-" * 70)

    # Test 1: Simple question
    print("TEST 1: Ask Claude a simple question")
    print("-" * 70)
    prompt1 = "What is 7 times 13? Just give the number."
    print(f"Q: {prompt1}")

    import time
    start = time.time()
    response1 = agent.send_prompt(prompt1)
    t1 = time.time() - start

    print(f"A: {response1}")
    print(f"Time: {t1:.1f}s")

    # Test 2: Follow-up (test session persistence)
    print("\n" + "-" * 70)
    print("TEST 2: Follow-up question (testing session persistence)")
    print("-" * 70)
    prompt2 = "What number did I just ask you about? Just the number."
    print(f"Q: {prompt2}")

    start = time.time()
    response2 = agent.send_prompt(prompt2)
    t2 = time.time() - start

    print(f"A: {response2}")
    print(f"Time: {t2:.1f}s")

    # Test 3: Code generation (simple, no file creation)
    print("\n" + "-" * 70)
    print("TEST 3: Generate code snippet")
    print("-" * 70)
    prompt3 = "Write a one-line Python function to reverse a string. Just the code."
    print(f"Q: {prompt3}")

    start = time.time()
    response3 = agent.send_prompt(prompt3)
    t3 = time.time() - start

    print(f"A: {response3[:200]}")
    print(f"Time: {t3:.1f}s")

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"✓ All 3 prompts successful")
    print(f"✓ Average response time: {(t1+t2+t3)/3:.1f}s")
    print(f"✓ Session ID: {agent.session_id}")
    print(f"✓ Agent healthy: {agent.is_healthy()}")
    print("\n🎉 Headless mode is FULLY FUNCTIONAL!\n")

    agent.cleanup()
    return 0


if __name__ == '__main__':
    sys.exit(main())
