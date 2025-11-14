#!/usr/bin/env python3
"""Safe M2 test runner with detailed logging and crash detection.

This script runs M2 tests with:
- Individual test timeouts
- Detailed progress logging
- Crash detection
- Resource monitoring
- Per-test logging
"""

import subprocess
import sys
import time
import signal
from pathlib import Path
from datetime import datetime
import os

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

# Test configuration
M2_TESTS = [
    'tests/test_local_interface.py',
    'tests/test_output_monitor.py',
    'tests/test_event_detector.py',
    'tests/test_claude_code_ssh.py',
    'tests/test_response_validator.py',
    'tests/test_prompt_generator.py',
    'tests/test_file_watcher.py',  # Most dangerous - runs last
]

# Timeout per test file (seconds)
TEST_TIMEOUT = 60  # 1 minute per file
TOTAL_TIMEOUT = 300  # 5 minutes total

LOG_FILE = Path('tests/test_run_safe.log')
DETAIL_LOG = Path('tests/test_run_detailed_safe.log')


class TestRunner:
    """Safe test runner with detailed logging."""

    def __init__(self):
        self.start_time = time.time()
        self.results = []
        self.current_test = None
        self.process = None

        # Open log files
        self.log_file = open(LOG_FILE, 'w')
        self.detail_log = open(DETAIL_LOG, 'w')

        # Track system resources (if psutil available)
        self.process_monitor = None
        if HAS_PSUTIL:
            try:
                self.process_monitor = psutil.Process()
            except:
                pass

    def log(self, message: str, level: str = 'INFO'):
        """Log message to both console and file."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_line = f"[{timestamp}] [{level}] {message}\n"

        # Write to log files
        self.log_file.write(log_line)
        self.log_file.flush()
        self.detail_log.write(log_line)
        self.detail_log.flush()

        # Console output with color
        color = {
            'INFO': Colors.CYAN,
            'SUCCESS': Colors.GREEN,
            'ERROR': Colors.RED,
            'WARNING': Colors.YELLOW,
            'HEADER': Colors.HEADER
        }.get(level, Colors.RESET)

        print(f"{color}{log_line.rstrip()}{Colors.RESET}")

    def log_resource_usage(self):
        """Log current resource usage."""
        if not self.process_monitor:
            return

        try:
            cpu_percent = self.process_monitor.cpu_percent(interval=0.1)
            memory_info = self.process_monitor.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # Count threads
            thread_count = len(psutil.Process().threads())

            self.detail_log.write(
                f"  RESOURCES: CPU={cpu_percent:.1f}%, "
                f"Memory={memory_mb:.1f}MB, Threads={thread_count}\n"
            )
            self.detail_log.flush()
        except Exception as e:
            self.detail_log.write(f"  Resource monitoring failed: {e}\n")
            self.detail_log.flush()

    def run_test(self, test_file: str) -> dict:
        """Run a single test file with timeout and logging."""
        self.current_test = test_file
        test_name = Path(test_file).name

        self.log(f"{'='*80}", 'HEADER')
        self.log(f"STARTING: {test_file}", 'HEADER')
        self.log(f"{'='*80}", 'HEADER')

        start_time = time.time()
        result = {
            'test': test_file,
            'status': 'UNKNOWN',
            'duration': 0,
            'output': '',
            'error': ''
        }

        try:
            # Log resource usage before test
            self.log_resource_usage()

            # Run pytest with verbose output (use venv python)
            venv_python = Path('venv/bin/python3')
            if venv_python.exists():
                cmd = [str(venv_python), '-m', 'pytest']
            else:
                cmd = ['pytest']

            cmd.extend([
                test_file,
                '-v',
                '--tb=short',
                '-x',  # Stop on first failure
                '--showlocals'
            ])

            self.detail_log.write(f"\nCOMMAND: {' '.join(cmd)}\n")
            self.detail_log.flush()

            # Start process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Read output line by line with timeout
            output_lines = []
            poll_count = 0

            while True:
                # Check if process finished
                retcode = self.process.poll()
                if retcode is not None:
                    # Process finished
                    remaining = self.process.stdout.read()
                    if remaining:
                        output_lines.append(remaining)
                        self.detail_log.write(remaining)
                        self.detail_log.flush()

                    result['returncode'] = retcode
                    break

                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > TEST_TIMEOUT:
                    self.log(f"TIMEOUT after {elapsed:.1f}s", 'ERROR')
                    self.process.kill()
                    result['status'] = 'TIMEOUT'
                    result['error'] = f'Test timed out after {elapsed:.1f}s'
                    break

                # Try to read output (non-blocking with short timeout)
                try:
                    import select
                    ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
                    if ready:
                        line = self.process.stdout.readline()
                        if line:
                            output_lines.append(line)
                            self.detail_log.write(line)
                            self.detail_log.flush()

                            # Log test progress
                            if '::test_' in line or 'PASSED' in line or 'FAILED' in line:
                                self.log(f"  {line.strip()}", 'INFO')
                except:
                    # Fallback for systems without select
                    time.sleep(0.1)

                poll_count += 1

                # Log resource usage every 5 seconds
                if poll_count % 50 == 0:
                    self.log_resource_usage()

            # Process completed
            result['output'] = ''.join(output_lines)
            result['duration'] = time.time() - start_time

            # Determine status from return code
            if result.get('returncode') == 0:
                result['status'] = 'PASSED'
                self.log(f"✅ PASSED: {test_name} ({result['duration']:.2f}s)", 'SUCCESS')
            elif result.get('returncode') == 5:
                result['status'] = 'NO_TESTS'
                self.log(f"⚠️  NO TESTS: {test_name}", 'WARNING')
            elif result.get('status') != 'TIMEOUT':
                result['status'] = 'FAILED'
                self.log(f"❌ FAILED: {test_name} ({result['duration']:.2f}s)", 'ERROR')

            # Log final resource usage
            self.log_resource_usage()

        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            result['duration'] = time.time() - start_time
            self.log(f"💥 ERROR: {test_name} - {e}", 'ERROR')

        finally:
            # Cleanup process
            if self.process and self.process.poll() is None:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=5)
                except:
                    self.process.kill()

            self.process = None

        return result

    def run_all(self):
        """Run all M2 tests."""
        self.log(f"{Colors.BOLD}🚀 Starting M2 Test Suite (Safe Mode){Colors.RESET}", 'HEADER')
        self.log(f"Log file: {LOG_FILE.absolute()}", 'INFO')
        self.log(f"Detail log: {DETAIL_LOG.absolute()}", 'INFO')
        self.log(f"Total tests: {len(M2_TESTS)}", 'INFO')
        self.log(f"Timeout per test: {TEST_TIMEOUT}s", 'INFO')
        self.log(f"Total timeout: {TOTAL_TIMEOUT}s", 'INFO')
        self.log('', 'INFO')

        # Run each test
        for i, test_file in enumerate(M2_TESTS, 1):
            # Check total timeout
            elapsed = time.time() - self.start_time
            if elapsed > TOTAL_TIMEOUT:
                self.log(f"⏱️  TOTAL TIMEOUT exceeded ({elapsed:.1f}s)", 'ERROR')
                break

            self.log(f"\n📋 Running test {i}/{len(M2_TESTS)}: {test_file}", 'HEADER')

            result = self.run_test(test_file)
            self.results.append(result)

            # Stop on critical failures
            if result['status'] in ['TIMEOUT', 'ERROR']:
                self.log(f"⛔ Stopping due to {result['status']}", 'ERROR')
                break

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        self.log('\n' + '='*80, 'HEADER')
        self.log('📊 FINAL SUMMARY', 'HEADER')
        self.log('='*80, 'HEADER')

        passed = sum(1 for r in self.results if r['status'] == 'PASSED')
        failed = sum(1 for r in self.results if r['status'] == 'FAILED')
        timeout = sum(1 for r in self.results if r['status'] == 'TIMEOUT')
        error = sum(1 for r in self.results if r['status'] == 'ERROR')
        no_tests = sum(1 for r in self.results if r['status'] == 'NO_TESTS')

        total_time = time.time() - self.start_time

        for result in self.results:
            status_icon = {
                'PASSED': '✅',
                'FAILED': '❌',
                'TIMEOUT': '⏱️ ',
                'ERROR': '💥',
                'NO_TESTS': '⚠️ '
            }.get(result['status'], '❓')

            self.log(
                f"  {status_icon} {result['test']:40} ({result['duration']:.2f}s)",
                'INFO'
            )

        self.log('', 'INFO')
        self.log(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed} | "
                f"Timeout: {timeout} | Error: {error} | No tests: {no_tests}", 'INFO')
        self.log(f"Total time: {total_time:.2f}s", 'INFO')
        self.log(f"Log saved to: {LOG_FILE.absolute()}", 'INFO')
        self.log(f"Detail log: {DETAIL_LOG.absolute()}", 'INFO')
        self.log('='*80, 'HEADER')

        # Return exit code
        if timeout > 0 or error > 0:
            return 2  # Critical failure
        elif failed > 0:
            return 1  # Test failures
        else:
            return 0  # Success

    def cleanup(self):
        """Cleanup resources."""
        if self.log_file:
            self.log_file.close()
        if self.detail_log:
            self.detail_log.close()


def main():
    """Main entry point."""
    runner = TestRunner()

    try:
        runner.run_all()
        return runner.print_summary()
    except KeyboardInterrupt:
        runner.log('\n⚠️  Interrupted by user', 'WARNING')
        return 130
    except Exception as e:
        runner.log(f'\n💥 Unexpected error: {e}', 'ERROR')
        import traceback
        runner.detail_log.write(traceback.format_exc())
        return 1
    finally:
        runner.cleanup()


if __name__ == '__main__':
    sys.exit(main())
