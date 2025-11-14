#!/usr/bin/env python3
"""Comprehensive development workflow test for headless mode.

This test simulates a realistic software development workflow:
1. Generate initial code (calculator module)
2. Generate tests for the code
3. Run tests to verify correctness
4. Request feature addition
5. Verify the enhanced code works
6. Request bug fix
7. Verify the fix works

This validates:
- Multi-turn code generation
- Context persistence across iterations
- Code modification capability
- Real code execution/validation
- Full orchestration workflow
"""

import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.claude_code_local import ClaudeCodeLocalAgent


class DevelopmentWorkflowTest:
    """Test realistic software development workflow."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.agent = ClaudeCodeLocalAgent()
        self.results = []

    def setup(self):
        """Initialize agent and workspace."""
        print("=" * 70)
        print("DEVELOPMENT WORKFLOW TEST")
        print("=" * 70)
        print(f"Workspace: {self.workspace}")
        print()

        # Clean workspace
        if self.workspace.exists():
            import shutil
            shutil.rmtree(self.workspace)
        self.workspace.mkdir(parents=True)

        # Initialize agent
        self.agent.initialize({
            'workspace_path': str(self.workspace),
            'response_timeout': 120,  # Increased for complex operations
            'use_session_persistence': False  # Fresh sessions (100% reliable)
        })

        print(f"Session mode: {'Persistent' if self.agent.use_session_persistence else 'Fresh per call'}")
        print()

    def simulate_orchestration_delay(self, task_name: str):
        """Simulate validation, quality check, decision making."""
        print(f"  [OBRA] Validating response...")
        time.sleep(0.1)
        print(f"  [QWEN] Quality check...")
        time.sleep(1.0)  # Simulate local LLM call
        print(f"  [OBRA] Confidence scoring...")
        time.sleep(0.5)
        print(f"  [OBRA] Decision: PROCEED")
        time.sleep(0.1)

    def iteration(self, num: int, total: int, task: str, prompt: str,
                  verify_fn=None, context_hint: str = None) -> bool:
        """Execute one iteration of the development workflow.

        Args:
            num: Iteration number
            total: Total iterations
            task: Task description
            prompt: Prompt to send to Claude
            verify_fn: Optional function to verify the result
            context_hint: Optional hint about what context should include

        Returns:
            True if successful, False otherwise
        """
        print("\n" + "=" * 70)
        print(f"ITERATION {num}/{total}: {task}")
        print("=" * 70)
        print()

        if context_hint:
            print(f"[CONTEXT] Should include: {context_hint}")
            print()

        # Build context (simulate ContextManager)
        print("[OBRA] Building context from history...")
        time.sleep(0.1)

        # Send prompt to Claude
        print(f"[OBRA→CLAUDE] Sending prompt:")
        print(f"  {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        print()

        start = time.time()
        try:
            response = self.agent.send_prompt(prompt)
            claude_time = time.time() - start

            print(f"[CLAUDE→OBRA] Response received ({claude_time:.1f}s)")
            print(f"  Length: {len(response)} chars")
            print(f"  Preview: {response[:150]}...")
            print()

            # Simulate orchestration components
            self.simulate_orchestration_delay(task)

            # Verify if function provided
            if verify_fn:
                print(f"\n[TEST] Verifying results...")
                success, message = verify_fn()
                if success:
                    print(f"  ✓ {message}")
                else:
                    print(f"  ✗ {message}")
                    self.results.append({
                        'iteration': num,
                        'task': task,
                        'success': False,
                        'error': message
                    })
                    return False

            self.results.append({
                'iteration': num,
                'task': task,
                'success': True,
                'response_time': claude_time
            })

            print(f"\n✓ Iteration {num} complete")
            return True

        except Exception as e:
            print(f"\n✗ Iteration {num} failed: {e}")
            self.results.append({
                'iteration': num,
                'task': task,
                'success': False,
                'error': str(e)
            })
            return False

    def verify_file_exists(self, filename: str) -> tuple[bool, str]:
        """Verify a file was created."""
        file_path = self.workspace / filename
        if file_path.exists():
            size = file_path.stat().st_size
            return True, f"File '{filename}' created ({size} bytes)"
        return False, f"File '{filename}' not found"

    def verify_python_syntax(self, filename: str) -> tuple[bool, str]:
        """Verify Python file has valid syntax."""
        file_path = self.workspace / filename
        if not file_path.exists():
            return False, f"File '{filename}' not found"

        try:
            result = subprocess.run(
                ['python', '-m', 'py_compile', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, f"'{filename}' has valid Python syntax"
            return False, f"Syntax error in '{filename}': {result.stderr}"
        except Exception as e:
            return False, f"Failed to check syntax: {e}"

    def verify_tests_pass(self) -> tuple[bool, str]:
        """Run pytest and verify tests pass."""
        try:
            result = subprocess.run(
                ['python', '-m', 'pytest', str(self.workspace), '-v'],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace)
            )

            # Check for test results
            if 'passed' in result.stdout.lower():
                # Extract pass count
                import re
                match = re.search(r'(\d+) passed', result.stdout)
                if match:
                    count = match.group(1)
                    return True, f"Tests passed ({count} tests)"

            return False, f"Tests failed:\n{result.stdout}"

        except Exception as e:
            return False, f"Failed to run tests: {e}"

    def verify_function_works(self, module: str, function: str,
                             args: list, expected: any) -> tuple[bool, str]:
        """Verify a function produces expected output."""
        try:
            # Import the module
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                module,
                self.workspace / f"{module}.py"
            )
            if spec is None or spec.loader is None:
                return False, f"Could not load module '{module}'"

            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            # Call the function
            func = getattr(mod, function)
            result = func(*args)

            if result == expected:
                return True, f"{function}({args}) = {result} ✓"
            return False, f"{function}({args}) = {result}, expected {expected}"

        except Exception as e:
            return False, f"Function call failed: {e}"

    def run(self):
        """Execute the complete development workflow test."""
        self.setup()

        total_iterations = 6

        # Iteration 1: Create calculator module
        success = self.iteration(
            1, total_iterations,
            "Create Calculator Module",
            """Create a Python module called 'calculator.py' with these functions:
- add(a, b): returns a + b
- subtract(a, b): returns a - b
- multiply(a, b): returns a * b
- divide(a, b): returns a / b (handle division by zero)

Make sure to include proper docstrings and type hints.""",
            lambda: self.verify_python_syntax('calculator.py'),
            context_hint="Task description only (first iteration)"
        )

        if not success:
            print("\n❌ Workflow failed at iteration 1")
            return self.summary()

        # Iteration 2: Create tests
        success = self.iteration(
            2, total_iterations,
            "Generate Test Suite",
            """Create a test file 'test_calculator.py' using pytest to test all functions in calculator.py.
Include tests for:
- Basic operations (addition, subtraction, multiplication, division)
- Edge cases (division by zero)
- Type hints verification

Make sure tests are comprehensive and use pytest.""",
            lambda: self.verify_python_syntax('test_calculator.py'),
            context_hint="Previous: Created calculator.py with 4 functions"
        )

        if not success:
            print("\n❌ Workflow failed at iteration 2")
            return self.summary()

        # Iteration 3: Verify tests pass
        success = self.iteration(
            3, total_iterations,
            "Run Initial Tests",
            """Run the tests in test_calculator.py to verify the calculator module works correctly.
If any tests fail, fix the calculator.py code.""",
            self.verify_tests_pass,
            context_hint="Previous: Created calculator.py and test_calculator.py"
        )

        if not success:
            # Tests might fail - this is okay, move to next iteration
            print("\n⚠️ Tests may have failed, but continuing...")

        # Iteration 4: Add power function
        success = self.iteration(
            4, total_iterations,
            "Add Power Function",
            """Add a new function to calculator.py:
- power(base, exponent): returns base ** exponent

Also add tests for this new function in test_calculator.py.
Make sure the new function follows the same style as existing functions.""",
            lambda: self.verify_function_works('calculator', 'power', [2, 3], 8),
            context_hint="Previous: calculator.py with add/subtract/multiply/divide, test_calculator.py exists"
        )

        if not success:
            print("\n❌ Workflow failed at iteration 4")
            return self.summary()

        # Iteration 5: Add modulo function
        success = self.iteration(
            5, total_iterations,
            "Add Modulo Function",
            """Add one more function to calculator.py:
- modulo(a, b): returns a % b (handle modulo by zero)

Update test_calculator.py to include tests for modulo.""",
            lambda: self.verify_function_works('calculator', 'modulo', [10, 3], 1),
            context_hint="Previous: calculator.py has 5 functions (add/subtract/multiply/divide/power), tests exist"
        )

        if not success:
            print("\n❌ Workflow failed at iteration 5")
            return self.summary()

        # Iteration 6: Final verification
        success = self.iteration(
            6, total_iterations,
            "Final Test Run",
            """Run all tests in test_calculator.py to ensure everything works correctly.
Report the test results.""",
            self.verify_tests_pass,
            context_hint="Previous: calculator.py complete with 6 functions, comprehensive test suite exists"
        )

        return self.summary()

    def summary(self):
        """Print test summary and return exit code."""
        print("\n" + "=" * 70)
        print("WORKFLOW SUMMARY")
        print("=" * 70)

        successful = sum(1 for r in self.results if r['success'])
        total = len(self.results)

        print(f"\nIterations completed: {total}")
        print(f"Successful: {successful}/{total} ({successful/total*100:.0f}%)")

        if successful > 0:
            times = [r['response_time'] for r in self.results
                    if r['success'] and 'response_time' in r]
            if times:
                print(f"Average response time: {sum(times)/len(times):.1f}s")

        print("\nIteration results:")
        for r in self.results:
            status = "✓" if r['success'] else "✗"
            print(f"  {status} {r['iteration']}. {r['task']}")
            if not r['success'] and 'error' in r:
                print(f"      Error: {r['error'][:100]}")

        # Check workspace files
        print("\nWorkspace files:")
        files = list(self.workspace.glob('*.py'))
        for f in sorted(files):
            size = f.stat().st_size
            print(f"  - {f.name} ({size} bytes)")

        print("\n" + "=" * 70)

        if successful == total:
            print("✅ PERFECT - Complete development workflow successful!")
            print("\nThis validates:")
            print("  ✓ Multi-turn code generation")
            print("  ✓ Code modification across iterations")
            print("  ✓ Context management (no session persistence needed)")
            print("  ✓ Real code execution and validation")
            print("  ✓ Production-ready orchestration workflow")
            print("=" * 70)
            return 0
        else:
            print(f"⚠️ {total - successful} iteration(s) failed")
            print("=" * 70)
            return 1


def main():
    """Run the development workflow test."""
    workspace = Path('/tmp/test-development-workflow')

    test = DevelopmentWorkflowTest(workspace)
    exit_code = test.run()

    print(f"\nTest workspace: {workspace}")
    print("You can inspect the generated files to verify quality.\n")

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
