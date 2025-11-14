#!/usr/bin/env python3
"""Test the retry logic for session-in-use errors."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent


def main():
    print("=" * 70)
    print("RETRY LOGIC TEST")
    print("=" * 70)
    print("Testing automatic retry on session-in-use errors\n")

    agent = ClaudeCodeLocalAgent()
    agent.initialize({'workspace_path': '/tmp/test-retry'})

    print(f"Session: {agent.session_id}\n")

    # Test rapid consecutive calls that should trigger retries
    prompts = [
        "What is 2 + 2?",
        "What is 3 + 3?",
        "What is 4 + 4?",
        "What is 5 + 5?",
    ]

    results = []

    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'='*70}")
        print(f"Call {i}/{len(prompts)}: {prompt}")
        print('='*70)

        start = time.time()
        try:
            response = agent.send_prompt(prompt)
            elapsed = time.time() - start

            results.append({
                'call': i,
                'success': True,
                'time': elapsed,
                'response': response
            })

            print(f"✓ Success ({elapsed:.1f}s)")
            print(f"Response: {response}")

        except Exception as e:
            elapsed = time.time() - start

            results.append({
                'call': i,
                'success': False,
                'time': elapsed,
                'error': str(e)
            })

            print(f"✗ Failed ({elapsed:.1f}s)")
            print(f"Error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for r in results if r['success'])
    total = len(results)

    print(f"Success rate: {successful}/{total} ({successful/total*100:.0f}%)")

    if successful > 0:
        avg_time = sum(r['time'] for r in results if r['success']) / successful
        print(f"Average response time: {avg_time:.1f}s")

    if successful == total:
        print("\n✅ ALL CALLS SUCCESSFUL - Retry logic working!")
    elif successful > total / 2:
        print(f"\n⚠️  Partial success - {total - successful} calls failed")
    else:
        print(f"\n❌ Poor success rate - retry logic may need tuning")

    agent.cleanup()


if __name__ == '__main__':
    main()
