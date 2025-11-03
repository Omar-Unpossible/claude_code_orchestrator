#!/usr/bin/env python3
"""Remove fast_time from file watcher tests that need real polling time."""

import re

# Tests that need real sleep for file detection (remove fast_time from these)
TESTS_NEEDING_REAL_SLEEP = [
    'test_detect_file_creation',
    'test_detect_file_modification',
    'test_detect_file_deletion',
    'test_detect_multiple_files',
    'test_no_debounce_for_different_files',
    'test_change_includes_hash',
    'test_callback_receives_changes',
    'test_multiple_callbacks',
    'test_callback_exception_handling',
    'test_clear_history',
    'test_get_statistics',
    'test_concurrent_access',
    'test_nested_directories',
    'test_binary_file_handling',
    'test_large_file_handling',
]

def fix_test_file(file_path):
    """Remove fast_time from specified tests and increase sleep times."""
    with open(file_path, 'r') as f:
        content = f.read()

    original_content = content

    for test_name in TESTS_NEEDING_REAL_SLEEP:
        # Pattern to match test function signature with fast_time
        pattern = rf'(def {test_name}\([^)]*), fast_time(\))'
        replacement = r'\1\2'
        content = re.sub(pattern, replacement, content)

    # Also increase 0.05 sleeps to 0.1 in these tests
    # This is trickier - we'll just do a blanket replacement for now
    # content = content.replace('time.sleep(0.05)', 'time.sleep(0.1)')

    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"Fixed {file_path}")
        return True
    else:
        print(f"No changes needed in {file_path}")
        return False

if __name__ == '__main__':
    fix_test_file('tests/test_file_watcher.py')
