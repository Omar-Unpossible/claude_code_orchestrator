#!/usr/bin/env python3
"""Test PTY without hook system - to isolate the issue."""

import pexpect
import time
from pathlib import Path

def main():
    print("=" * 80)
    print("PTY TEST WITHOUT HOOKS - Isolate Hook Interference")
    print("=" * 80)
    print()

    workspace = Path("/tmp/claude-workspace-no-hook")
    workspace.mkdir(parents=True, exist_ok=True)

    print(f"📁 Workspace: {workspace}")
    print(f"🚫 No hook configuration will be created")
    print()

    try:
        # Spawn Claude WITHOUT hook configuration
        print("\033[34m[TEST]\033[0m Spawning Claude Code with PTY (NO HOOKS)...")
        process = pexpect.spawn(
            'claude',
            cwd=str(workspace),
            dimensions=(40, 120),
            echo=False,
            encoding='utf-8',
            codec_errors='replace'
        )

        # Wait for stability
        print("\033[34m[TEST]\033[0m Waiting 2s for process stability...")
        time.sleep(2)

        if not process.isalive():
            print("\033[31m✗\033[0m Process died during startup")
            return 1

        print(f"\033[32m✓\033[0m Process alive (PID: {process.pid})")
        print()

        # Send simple prompt (exactly like user's manual test)
        prompt = "who are you?"
        print(f"\033[34m[TEST]\033[0m Sending prompt: '{prompt}'")
        print("-" * 80)
        print()

        process.sendline(prompt)

        # Read output for 10 seconds (should respond immediately like manual test)
        print("\033[32m[CLAUDE OUTPUT]\033[0m")
        print()

        start_time = time.time()
        timeout = 10.0
        got_response = False

        while time.time() - start_time < timeout:
            try:
                chunk = process.read_nonblocking(1024, timeout=0.5)
                print(chunk, end='', flush=True)

                # Check if we got a response (look for bullet or "I'm Claude")
                if "I'm Claude" in chunk or "●" in chunk or "I am Claude" in chunk:
                    got_response = True
                    print()
                    print()
                    print("\033[32m✓ RESPONSE DETECTED!\033[0m")
                    time.sleep(1)  # Let it finish
                    break

            except pexpect.TIMEOUT:
                continue
            except pexpect.EOF:
                print()
                print("\033[31m✗ Process ended\033[0m")
                break

        print()
        print("-" * 80)
        print()

        elapsed = time.time() - start_time
        if got_response:
            print(f"\033[32m✓ TEST PASSED\033[0m - Got response in {elapsed:.1f}s")
            print("🎉 Claude responds without hooks!")
        else:
            print(f"\033[31m✗ TEST FAILED\033[0m - No response after {elapsed:.1f}s")
            print("⚠️ Still stuck even without hooks")

        # Cleanup
        print()
        print("\033[34m[TEST]\033[0m Cleaning up...")
        try:
            process.sendintr()
            process.expect(pexpect.EOF, timeout=3)
        except:
            process.terminate()
        print("\033[32m✓\033[0m Cleanup complete")

        return 0 if got_response else 1

    except Exception as e:
        print(f"\033[31m✗ ERROR\033[0m {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
