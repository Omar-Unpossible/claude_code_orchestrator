#!/usr/bin/env python3
"""Run M2 tests with detailed per-test logging.

This script runs each M2 test file and logs:
- Test name BEFORE execution starts
- Test result AFTER execution completes
- Timestamp for each event
- Any errors or failures

This allows us to identify exactly which test was running if WSL2 crashes.
"""

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def log_with_timestamp(message, color=''):
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    colored_msg = f"{color}{message}{Colors.ENDC}" if color else message
    print(f"[{timestamp}] {colored_msg}", flush=True)


def run_test_file(test_file, log_file):
    """Run a single test file with verbose output and logging."""
    log_with_timestamp(f"\n{'='*80}", Colors.HEADER)
    log_with_timestamp(f"STARTING TEST FILE: {test_file}", Colors.HEADER + Colors.BOLD)
    log_with_timestamp(f"{'='*80}\n", Colors.HEADER)

    # Write to log file
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"[{datetime.now().isoformat()}] STARTING: {test_file}\n")
        f.write(f"{'='*80}\n")

    # Run pytest with verbose output and capture test names
    # Use -v for verbose, -s to show print statements, --tb=short for short tracebacks
    # Use venv's pytest to ensure all dependencies are available
    pytest_path = Path(__file__).parent.parent / 'venv' / 'bin' / 'pytest'
    cmd = [
        str(pytest_path),
        str(test_file),
        '-v',
        '-s',
        '--tb=short',
        '--capture=no',  # Don't capture output
        '-p', 'no:warnings',  # Disable warnings plugin for cleaner output
    ]

    start_time = time.time()

    try:
        # Run the test
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per file
        )

        elapsed = time.time() - start_time

        # Log output
        with open(log_file, 'a') as f:
            f.write(f"\n--- STDOUT ---\n")
            f.write(result.stdout)
            f.write(f"\n--- STDERR ---\n")
            f.write(result.stderr)
            f.write(f"\n--- RESULT ---\n")
            f.write(f"Return code: {result.returncode}\n")
            f.write(f"Elapsed time: {elapsed:.2f}s\n")
            f.write(f"[{datetime.now().isoformat()}] COMPLETED: {test_file}\n")

        # Print summary
        if result.returncode == 0:
            log_with_timestamp(
                f"✅ PASSED: {test_file} ({elapsed:.2f}s)",
                Colors.OKGREEN
            )
        else:
            log_with_timestamp(
                f"❌ FAILED: {test_file} ({elapsed:.2f}s) - Return code: {result.returncode}",
                Colors.FAIL
            )
            # Print stderr for failures
            if result.stderr:
                print(f"\n{Colors.WARNING}STDERR:{Colors.ENDC}")
                print(result.stderr)

        # Print stdout for visibility
        print(result.stdout)

        return result.returncode == 0

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        log_with_timestamp(
            f"⏱️  TIMEOUT: {test_file} (>{elapsed:.2f}s)",
            Colors.WARNING
        )
        with open(log_file, 'a') as f:
            f.write(f"\n[{datetime.now().isoformat()}] TIMEOUT: {test_file} after {elapsed:.2f}s\n")
        return False

    except Exception as e:
        elapsed = time.time() - start_time
        log_with_timestamp(
            f"💥 EXCEPTION: {test_file} - {str(e)}",
            Colors.FAIL
        )
        with open(log_file, 'a') as f:
            f.write(f"\n[{datetime.now().isoformat()}] EXCEPTION: {test_file}\n")
            f.write(f"Error: {str(e)}\n")
        return False


def main():
    """Run all M2 test files."""
    # M2 test files (from plans/02_interfaces.json)
    m2_test_files = [
        'test_local_interface.py',      # 2.1: Local LLM Interface
        'test_data_responses.py',        # 2.2: Data structures
        'test_output_monitor.py',        # 2.3: Output Monitor
        'test_response_validator.py',    # 2.4: Response Validator
        'test_event_detector.py',        # 2.5: Event Detector
        'test_claude_code_ssh.py',       # 2.6: Claude Code SSH Agent
        'test_prompt_generator.py',      # 2.7: Prompt Generator
        'test_file_watcher.py',          # 2.8: File Watcher (M3 but tested now)
    ]

    # Create log file
    log_file = Path(__file__).parent / 'test_run_detailed.log'

    # Clear previous log
    if log_file.exists():
        log_file.unlink()

    # Write header
    with open(log_file, 'w') as f:
        f.write(f"M2 Test Suite Execution Log\n")
        f.write(f"Started: {datetime.now().isoformat()}\n")
        f.write(f"{'='*80}\n\n")

    log_with_timestamp("🚀 Starting M2 Test Suite with Detailed Logging", Colors.OKBLUE + Colors.BOLD)
    log_with_timestamp(f"📝 Log file: {log_file}", Colors.OKCYAN)
    log_with_timestamp(f"📊 Total test files: {len(m2_test_files)}", Colors.OKCYAN)

    results = {}
    start_time = time.time()

    for i, test_file in enumerate(m2_test_files, 1):
        test_path = Path(__file__).parent / test_file

        if not test_path.exists():
            log_with_timestamp(
                f"⚠️  SKIPPED: {test_file} (file not found)",
                Colors.WARNING
            )
            results[test_file] = 'SKIPPED'
            continue

        log_with_timestamp(
            f"\n📋 Running test {i}/{len(m2_test_files)}: {test_file}",
            Colors.OKBLUE
        )

        success = run_test_file(test_path, log_file)
        results[test_file] = 'PASS' if success else 'FAIL'

        # Small delay between test files to allow cleanup
        time.sleep(0.5)

    # Summary
    total_time = time.time() - start_time
    passed = sum(1 for r in results.values() if r == 'PASS')
    failed = sum(1 for r in results.values() if r == 'FAIL')
    skipped = sum(1 for r in results.values() if r == 'SKIPPED')

    log_with_timestamp(f"\n{'='*80}", Colors.HEADER)
    log_with_timestamp("📊 FINAL SUMMARY", Colors.HEADER + Colors.BOLD)
    log_with_timestamp(f"{'='*80}", Colors.HEADER)

    for test_file, result in results.items():
        if result == 'PASS':
            log_with_timestamp(f"  ✅ {test_file}", Colors.OKGREEN)
        elif result == 'FAIL':
            log_with_timestamp(f"  ❌ {test_file}", Colors.FAIL)
        else:
            log_with_timestamp(f"  ⚠️  {test_file}", Colors.WARNING)

    log_with_timestamp(f"\n{'='*80}", Colors.HEADER)
    log_with_timestamp(f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}", Colors.BOLD)
    log_with_timestamp(f"Total time: {total_time:.2f}s", Colors.BOLD)
    log_with_timestamp(f"Log saved to: {log_file}", Colors.OKCYAN)
    log_with_timestamp(f"{'='*80}\n", Colors.HEADER)

    # Write summary to log
    with open(log_file, 'a') as f:
        f.write(f"\n{'='*80}\n")
        f.write(f"FINAL SUMMARY\n")
        f.write(f"{'='*80}\n")
        f.write(f"Total: {len(results)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}\n")
        f.write(f"Total time: {total_time:.2f}s\n")
        f.write(f"Completed: {datetime.now().isoformat()}\n")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
