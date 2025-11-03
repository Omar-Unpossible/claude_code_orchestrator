#!/usr/bin/env python3
"""Debug script to understand Claude failures and rate limiting."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent
from src.plugins.exceptions import AgentException


def test_rapid_fire():
    """Test rapid consecutive calls to identify rate limiting."""
    print("=" * 70)
    print("TEST: Rapid Consecutive Calls")
    print("=" * 70)

    agent = ClaudeCodeLocalAgent()
    agent.initialize({'workspace_path': '/tmp/debug-rapid'})

    print(f"Session: {agent.session_id}\n")

    results = []

    for i in range(5):
        prompt = f"What is {i} + 1? Just the number."
        print(f"\nCall {i+1}/5: {prompt}")

        start = time.time()
        try:
            response = agent.send_prompt(prompt)
            elapsed = time.time() - start

            results.append({
                'call': i+1,
                'success': True,
                'time': elapsed,
                'response': response[:50]
            })

            print(f"  ✓ Success ({elapsed:.1f}s): {response}")

        except AgentException as e:
            elapsed = time.time() - start

            results.append({
                'call': i+1,
                'success': False,
                'time': elapsed,
                'error': str(e)
            })

            print(f"  ✗ Failed ({elapsed:.1f}s)")
            print(f"  Error: {e}")
            print(f"  Context: {e.context if hasattr(e, 'context') else 'None'}")

    # Summary
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    successful = sum(1 for r in results if r['success'])
    print(f"Successful calls: {successful}/5")
    print(f"Failed calls: {5-successful}/5")

    if successful > 0:
        avg_time = sum(r['time'] for r in results if r['success']) / successful
        print(f"Average success time: {avg_time:.1f}s")

    # Failure pattern
    if successful < 5:
        print("\nFailure pattern:")
        for r in results:
            if not r['success']:
                print(f"  Call {r['call']}: {r['error'][:100]}")

    agent.cleanup()
    return results


def test_with_delays():
    """Test calls with delays between them."""
    print("\n" + "=" * 70)
    print("TEST: Calls with 2s Delay")
    print("=" * 70)

    agent = ClaudeCodeLocalAgent()
    agent.initialize({'workspace_path': '/tmp/debug-delayed'})

    print(f"Session: {agent.session_id}\n")

    results = []

    for i in range(3):
        prompt = f"What is {i * 2} + 2? Just the number."
        print(f"\nCall {i+1}/3: {prompt}")

        start = time.time()
        try:
            response = agent.send_prompt(prompt)
            elapsed = time.time() - start

            results.append({
                'call': i+1,
                'success': True,
                'time': elapsed
            })

            print(f"  ✓ Success ({elapsed:.1f}s): {response}")

            if i < 2:  # Don't wait after last call
                print("  Waiting 2s...")
                time.sleep(2)

        except AgentException as e:
            elapsed = time.time() - start

            results.append({
                'call': i+1,
                'success': False,
                'time': elapsed,
                'error': str(e)
            })

            print(f"  ✗ Failed ({elapsed:.1f}s): {e}")

    # Summary
    print("\n" + "=" * 70)
    successful = sum(1 for r in results if r['success'])
    print(f"With delays: {successful}/3 successful")
    print("=" * 70)

    agent.cleanup()
    return results


def test_different_sessions():
    """Test whether issue is session-specific."""
    print("\n" + "=" * 70)
    print("TEST: Different Sessions")
    print("=" * 70)

    results = []

    for i in range(3):
        print(f"\nSession {i+1}/3:")

        agent = ClaudeCodeLocalAgent()
        agent.initialize({'workspace_path': f'/tmp/debug-session-{i}'})

        print(f"  Session ID: {agent.session_id}")

        prompt = "What is 5 + 5? Just the number."

        try:
            start = time.time()
            response = agent.send_prompt(prompt)
            elapsed = time.time() - start

            results.append({'session': i+1, 'success': True, 'time': elapsed})
            print(f"  ✓ Success ({elapsed:.1f}s): {response}")

        except AgentException as e:
            elapsed = time.time() - start
            results.append({'session': i+1, 'success': False, 'error': str(e)})
            print(f"  ✗ Failed ({elapsed:.1f}s): {e}")

        agent.cleanup()

        if i < 2:
            print("  Waiting 1s...")
            time.sleep(1)

    # Summary
    print("\n" + "=" * 70)
    successful = sum(1 for r in results if r['success'])
    print(f"Different sessions: {successful}/3 successful")
    print("=" * 70)

    return results


def test_stderr_capture():
    """Examine stderr for clues."""
    print("\n" + "=" * 70)
    print("TEST: Stderr Analysis")
    print("=" * 70)

    agent = ClaudeCodeLocalAgent()
    agent.initialize({'workspace_path': '/tmp/debug-stderr'})

    # Force a failure by invalid prompt or rapid calls
    for i in range(2):
        try:
            print(f"\nAttempt {i+1}:")
            result = agent._run_claude(['--print', '--session-id', agent.session_id, 'Test'])

            print(f"  Exit code: {result.returncode}")
            print(f"  Stdout: {result.stdout[:200] if result.stdout else '(empty)'}")
            print(f"  Stderr: {result.stderr[:200] if result.stderr else '(empty)'}")

            time.sleep(0.5)

        except Exception as e:
            print(f"  Exception: {e}")

    agent.cleanup()


def main():
    """Run all debug tests."""
    print("\n" + "=" * 70)
    print("CLAUDE FAILURE DEBUGGING SUITE")
    print("=" * 70)
    print("Investigating rate limiting and session issues\n")

    # Test 1: Rapid fire
    rapid_results = test_rapid_fire()

    # Test 2: With delays
    delayed_results = test_with_delays()

    # Test 3: Different sessions
    session_results = test_different_sessions()

    # Test 4: Stderr analysis
    test_stderr_capture()

    # Final analysis
    print("\n" + "=" * 70)
    print("FINAL ANALYSIS")
    print("=" * 70)

    rapid_success_rate = sum(1 for r in rapid_results if r['success']) / len(rapid_results) * 100
    delayed_success_rate = sum(1 for r in delayed_results if r['success']) / len(delayed_results) * 100
    session_success_rate = sum(1 for r in session_results if r['success']) / len(session_results) * 100

    print(f"Rapid fire success rate: {rapid_success_rate:.0f}%")
    print(f"With delays success rate: {delayed_success_rate:.0f}%")
    print(f"Different sessions success rate: {session_success_rate:.0f}%")

    print("\nConclusions:")
    if rapid_success_rate < 80:
        print("  - Rapid consecutive calls likely cause failures")
    if delayed_success_rate > rapid_success_rate + 20:
        print("  - Adding delays between calls improves reliability")
    if session_success_rate < delayed_success_rate:
        print("  - Session reuse may be problematic")
    else:
        print("  - Session reuse appears acceptable")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
