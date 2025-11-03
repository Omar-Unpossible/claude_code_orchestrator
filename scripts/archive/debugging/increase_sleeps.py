#!/usr/bin/env python3
"""Increase sleep times in file watcher tests for PollingObserver."""

import re

def fix_sleeps(file_path):
    """Increase sleep(0.05) to sleep(0.15) for better PollingObserver detection."""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    # Track if we're inside a test that needs real sleep
    inside_test_needing_sleep = False
    test_patterns = [
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

    modified_lines = []
    for line in lines:
        # Check if we're entering a test that needs real sleep
        for pattern in test_patterns:
            if f'def {pattern}(' in line:
                inside_test_needing_sleep = True
                break
        
        # Check if we're exiting a test (next def)
        if inside_test_needing_sleep and line.strip().startswith('def ') and not any(p in line for p in test_patterns):
            inside_test_needing_sleep = False
        
        # Replace sleep(0.05) with sleep(0.15) in tests that need real sleep
        if inside_test_needing_sleep and 'time.sleep(0.05)' in line:
            line = line.replace('time.sleep(0.05)', 'time.sleep(0.15)')
        
        modified_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(modified_lines)
    
    print(f"Updated sleeps in {file_path}")

if __name__ == '__main__':
    fix_sleeps('tests/test_file_watcher.py')
