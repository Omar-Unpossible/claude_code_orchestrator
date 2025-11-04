"""Test code validators for AST-based code quality checks.

Tests for:
- CodeViolation class
- detect_stubs() - Find stub functions
- detect_hardcoded_values() - Find magic numbers and hardcoded strings
- check_docstring_coverage() - Find missing docstrings
- check_test_coverage() - Verify tests exist
- validate_code_file() - Integration test

Part of TASK_2.5: Test PromptRuleEngine and validators
"""

import pytest
import tempfile
from pathlib import Path
from src.llm.code_validators import (
    CodeViolation,
    detect_stubs,
    detect_hardcoded_values,
    check_docstring_coverage,
    check_test_coverage,
    validate_code_file
)


# ============================================================================
# Tests: CodeViolation
# ============================================================================

def test_code_violation_initialization():
    """Test CodeViolation initializes correctly."""
    violation = CodeViolation(
        file_path='/path/to/file.py',
        line=42,
        column=10,
        violation_type='stub_function',
        message='Function contains only pass',
        severity='critical',
        suggestion='Implement the function logic'
    )

    assert violation.file_path == '/path/to/file.py'
    assert violation.line == 42
    assert violation.column == 10
    assert violation.violation_type == 'stub_function'
    assert violation.message == 'Function contains only pass'
    assert violation.severity == 'critical'
    assert violation.suggestion == 'Implement the function logic'


def test_code_violation_to_dict():
    """Test CodeViolation.to_dict() serialization."""
    violation = CodeViolation(
        file_path='/path/to/file.py',
        line=42,
        column=10,
        violation_type='stub_function',
        message='Test violation'
    )

    violation_dict = violation.to_dict()

    assert violation_dict['file'] == '/path/to/file.py'
    assert violation_dict['line'] == 42
    assert violation_dict['column'] == 10
    assert violation_dict['type'] == 'stub_function'
    assert violation_dict['message'] == 'Test violation'


# ============================================================================
# Tests: detect_stubs()
# ============================================================================

def test_detect_stubs_pass_statement():
    """Test detecting functions with only pass statement."""
    code = """
def stub_function():
    pass

def real_function():
    return 42
"""

    violations = detect_stubs(code)

    assert len(violations) == 1
    assert violations[0].violation_type == 'stub_function'
    assert 'stub_function' in violations[0].message


def test_detect_stubs_not_implemented():
    """Test detecting functions raising NotImplementedError."""
    code = """
def not_implemented_function():
    raise NotImplementedError("TODO: implement this")

def real_function():
    return 42
"""

    violations = detect_stubs(code)

    assert len(violations) == 1
    assert violations[0].violation_type == 'not_implemented'
    assert 'not_implemented_function' in violations[0].message


def test_detect_stubs_todo_marker():
    """Test detecting functions with TODO markers in docstring."""
    code = '''
def todo_function():
    """TODO: implement this function later."""
    return None

def real_function():
    """This is a real function."""
    return 42
'''

    violations = detect_stubs(code)

    assert len(violations) == 1
    assert violations[0].violation_type == 'todo_marker'
    assert 'todo_function' in violations[0].message


def test_detect_stubs_skips_private():
    """Test that private functions are skipped."""
    code = """
def _private_stub():
    pass

def public_stub():
    pass
"""

    violations = detect_stubs(code)

    # Should only detect public stub
    assert len(violations) == 1
    assert 'public_stub' in violations[0].message


# ============================================================================
# Tests: detect_hardcoded_values()
# ============================================================================

def test_detect_hardcoded_values_magic_numbers():
    """Test detecting magic numbers."""
    code = """
def calculate_area(radius):
    return radius * radius * 3.14159  # Magic number!

def valid_function():
    return 0  # 0 is in ignore list
"""

    violations = detect_hardcoded_values(code)

    assert len(violations) >= 1
    assert any(v.violation_type == 'magic_number' for v in violations)


def test_detect_hardcoded_values_urls():
    """Test detecting hardcoded URLs."""
    code = '''
API_URL = "https://api.example.com/v1"  # Hardcoded URL

def fetch_data():
    return requests.get("http://localhost:8080/data")
'''

    violations = detect_hardcoded_values(code)

    url_violations = [v for v in violations if v.violation_type == 'hardcoded_url']
    assert len(url_violations) >= 1


def test_detect_hardcoded_values_paths():
    """Test detecting hardcoded file paths."""
    code = '''
DATA_PATH = "/home/user/data/file.txt"  # Hardcoded path

def load_data():
    with open("/tmp/cache/data.json") as f:
        return f.read()
'''

    violations = detect_hardcoded_values(code)

    path_violations = [v for v in violations if v.violation_type == 'hardcoded_path']
    assert len(path_violations) >= 1


def test_detect_hardcoded_values_ignore_list():
    """Test that ignore_numbers parameter works."""
    code = """
def calculate():
    return 42 * 100  # Both should be ignored
"""

    # Default ignore list includes 0, 1, 2, -1, 100, 1000
    violations = detect_hardcoded_values(code)

    # 100 is in default ignore list
    magic_violations = [v for v in violations if '100' in v.message]
    assert len(magic_violations) == 0

    # 42 is not in ignore list
    magic_42 = [v for v in violations if '42' in v.message]
    assert len(magic_42) >= 1


# ============================================================================
# Tests: check_docstring_coverage()
# ============================================================================

def test_check_docstring_coverage_missing():
    """Test detecting missing docstrings."""
    code = """
def public_function(x, y):
    return x + y

def another_function():
    pass
"""

    violations = check_docstring_coverage(code)

    assert len(violations) == 2
    assert all(v.violation_type == 'missing_docstring' for v in violations)


def test_check_docstring_coverage_present():
    """Test that functions with docstrings pass."""
    code = '''
def documented_function(x, y):
    """Add two numbers together.

    Args:
        x: First number
        y: Second number

    Returns:
        Sum of x and y
    """
    return x + y
'''

    violations = check_docstring_coverage(code)

    assert len(violations) == 0


def test_check_docstring_coverage_private_skipped():
    """Test that private functions without docstrings are skipped."""
    code = """
def _private_function():
    return 42

def public_function():
    return 42
"""

    violations = check_docstring_coverage(code)

    # Only public function should be flagged
    assert len(violations) == 1
    assert 'public_function' in violations[0].message


# ============================================================================
# Tests: check_test_coverage()
# ============================================================================

def test_check_test_coverage_missing_file():
    """Test detecting missing test file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source file without test file
        source_path = Path(tmpdir) / 'module.py'
        source_path.write_text('''
def public_function():
    """A public function."""
    return 42
''')

        test_dir = Path(tmpdir) / 'tests'
        test_dir.mkdir()

        violations = check_test_coverage(str(source_path), str(test_dir))

        assert len(violations) == 1
        assert violations[0].violation_type == 'missing_test_file'


def test_check_test_coverage_missing_tests():
    """Test detecting missing test functions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source file with public function
        source_path = Path(tmpdir) / 'module.py'
        source_path.write_text('''
def public_function():
    """A public function."""
    return 42

def another_function():
    """Another public function."""
    return 100
''')

        # Create test file with only one test
        test_dir = Path(tmpdir) / 'tests'
        test_dir.mkdir()
        test_path = test_dir / 'test_module.py'
        test_path.write_text('''
def test_public_function():
    from module import public_function
    assert public_function() == 42
''')

        violations = check_test_coverage(str(source_path), str(test_dir))

        # Should flag another_function as missing test
        assert len(violations) >= 1
        assert any('another_function' in v.message for v in violations)


def test_check_test_coverage_tests_exist():
    """Test that existing tests are recognized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create source file
        source_path = Path(tmpdir) / 'module.py'
        source_path.write_text('''
def public_function():
    """A public function."""
    return 42
''')

        # Create matching test file
        test_dir = Path(tmpdir) / 'tests'
        test_dir.mkdir()
        test_path = test_dir / 'test_module.py'
        test_path.write_text('''
def test_public_function():
    from module import public_function
    assert public_function() == 42
''')

        violations = check_test_coverage(str(source_path), str(test_dir))

        # Should have no violations
        assert len(violations) == 0


# ============================================================================
# Tests: validate_code_file() Integration
# ============================================================================

def test_validate_code_file_integration():
    """Test validate_code_file runs all validators."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a file with multiple issues
        code_path = Path(tmpdir) / 'bad_code.py'
        code_path.write_text('''
def stub_function():
    pass

def undocumented_function(x):
    return x * 3.14159

API_URL = "http://localhost:8080"
''')

        results = validate_code_file(str(code_path))

        assert 'stubs' in results
        assert 'hardcoded' in results
        assert 'docstrings' in results
        assert 'tests' in results

        # Should have violations in multiple categories
        assert len(results['stubs']) > 0  # stub_function
        assert len(results['docstrings']) > 0  # missing docstrings
        # hardcoded might have URL and/or magic number


def test_validate_code_file_nonexistent():
    """Test validate_code_file with nonexistent file."""
    results = validate_code_file('/nonexistent/file.py')

    # Should return empty results, not crash
    assert results['stubs'] == []
    assert results['hardcoded'] == []
    assert results['docstrings'] == []
    assert results['tests'] == []


def test_detect_stubs_syntax_error():
    """Test detect_stubs with invalid Python code."""
    code = """
def broken_function(
    # Missing closing parenthesis
"""

    violations = detect_stubs(code)

    # Should return empty list, not crash
    assert violations == []


def test_detect_stubs_empty_function_body():
    """Test detecting functions with empty body."""
    code = """
def empty_function():
"""

    # This will cause a syntax error, so should return empty
    violations = detect_stubs(code)
    assert isinstance(violations, list)


def test_code_violation_repr():
    """Test CodeViolation string representation."""
    violation = CodeViolation(
        file_path='/path/to/file.py',
        line=42,
        column=10,
        violation_type='stub_function',
        message='Test violation'
    )

    repr_str = repr(violation)

    assert 'CodeViolation' in repr_str
    assert '/path/to/file.py:42' in repr_str
    assert 'stub_function' in repr_str


def test_detect_hardcoded_values_syntax_error():
    """Test detect_hardcoded_values with invalid Python code."""
    code = """
def broken():
    return 42 +
"""

    violations = detect_hardcoded_values(code)

    # Should return empty list, not crash
    assert violations == []


def test_check_docstring_coverage_syntax_error():
    """Test check_docstring_coverage with invalid Python code."""
    code = """
def broken(
"""

    violations = check_docstring_coverage(code)

    # Should return empty list, not crash
    assert violations == []


def test_check_docstring_coverage_class():
    """Test checking docstrings for classes."""
    code = '''
class PublicClass:
    """This class has a docstring."""
    pass

class UndocumentedClass:
    pass
'''

    violations = check_docstring_coverage(code)

    # Should flag UndocumentedClass
    assert len(violations) >= 1
    assert any('UndocumentedClass' in v.message for v in violations)
