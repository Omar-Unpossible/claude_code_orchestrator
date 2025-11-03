#!/usr/bin/env python3
"""Fix remaining tests with 0.05s sleeps."""

# Additional tests that also need fixing
ADDITIONAL_TESTS = [
    'test_changes_recorded_in_state_manager',
    'test_callback_receives_changes',
    'test_multiple_callbacks',
    'test_callback_exception_handling',
    'test_get_statistics',
]

with open('tests/test_file_watcher.py', 'r') as f:
    content = f.read()

# Replace 0.05 with 0.15 in these specific tests
for test_name in ADDITIONAL_TESTS:
    # Find the test function and replace sleeps within it
    import re
    # Match from def test_name to next def or end
    pattern = rf'(def {test_name}\(.*?\n)(.*?)((?=\n    def )|$)'
    
    def replace_sleeps(match):
        header = match.group(1)
        body = match.group(2)
        footer = match.group(3)
        # Replace time.sleep(0.05) with time.sleep(0.15) in body
        body = body.replace('time.sleep(0.05)', 'time.sleep(0.15)')
        return header + body + footer
    
    content = re.sub(pattern, replace_sleeps, content, flags=re.DOTALL)

# Also remove fast_time from these tests if present
for test_name in ADDITIONAL_TESTS:
    pattern = rf'(def {test_name}\([^)]*), fast_time(\))'
    replacement = r'\1\2'
    content = re.sub(pattern, replacement, content)

with open('tests/test_file_watcher.py', 'w') as f:
    f.write(content)

print("Fixed remaining sleeps")
