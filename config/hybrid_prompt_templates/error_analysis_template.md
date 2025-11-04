# Error Analysis Hybrid Prompt Template

This template shows the structure of a hybrid prompt for error analysis and recovery.

## Format

```
<METADATA>
{
  "prompt_type": "error_analysis",
  "task_id": <task_id>,
  "error_context": {
    "error_type": "syntax|runtime|test_failure|validation|timeout",
    "error_message": "<error_message>",
    "stack_trace": "<stack_trace>",
    "failed_file": "<file_path>",
    "failed_line": <line_number>
  },
  "context": {
    "task_title": "<task_title>",
    "attempt_number": <number>,
    "files_involved": ["<file1.py>", "<file2.py>"],
    "previous_attempts": [
      {
        "attempt": 1,
        "error": "<previous_error>",
        "fix_attempted": "<what_was_tried>"
      }
    ]
  },
  "rules": [
    {
      "id": "ERR_001",
      "name": "ROOT_CAUSE_ANALYSIS",
      "description": "Always identify root cause, not just symptoms",
      "severity": "high"
    }
  ]
}
</METADATA>

<INSTRUCTION>
You are diagnosing and fixing an error for the Obra orchestration system.

**Error Details**:
- Type: <error_type>
- Message: <error_message>
- File: <failed_file>:<failed_line>

**Stack Trace**:
<stack_trace>

**Task Context**:
- Task: <task_title>
- Attempt: #<attempt_number>
- Files Involved: <files_list>

**Previous Attempts** (if any):
<previous_attempts_with_fixes_tried>

**Your Task**:
1. Analyze the error and identify the root cause
2. Explain why the error occurred
3. Propose a fix with specific code changes
4. Assess confidence that the fix will resolve the issue
5. Identify any related issues that might surface

**Output Format**:
<METADATA>
{
  "root_cause": "<concise_root_cause>",
  "error_category": "logic|syntax|type|import|config|environment",
  "fix_approach": "code_change|config_change|dependency_update|refactor",
  "confidence": <0.0-1.0>,
  "files_to_modify": ["<file1.py>"],
  "estimated_fix_time_minutes": <number>,
  "requires_human_review": <true|false>,
  "potential_side_effects": ["<side_effect1>", "<side_effect2>"]
}
</METADATA>

<CONTENT>
**Root Cause Analysis**:
<detailed_analysis>

**Proposed Fix**:
<specific_code_changes>

**Why This Works**:
<explanation>

**Testing Strategy**:
<how_to_verify_fix>
</CONTENT>
</INSTRUCTION>
```

## Example

```
<METADATA>
{
  "prompt_type": "error_analysis",
  "task_id": 123,
  "error_context": {
    "error_type": "runtime",
    "error_message": "AttributeError: 'NoneType' object has no attribute 'id'",
    "stack_trace": "File 'src/auth/handlers.py', line 15, in login_user\n    user_id = user.id\nAttributeError: 'NoneType' object has no attribute 'id'",
    "failed_file": "src/auth/handlers.py",
    "failed_line": 15
  },
  "context": {
    "task_title": "Implement user authentication module",
    "attempt_number": 2,
    "files_involved": ["src/auth/handlers.py", "src/auth/models.py"],
    "previous_attempts": [
      {
        "attempt": 1,
        "error": "ImportError: cannot import name 'User' from 'models'",
        "fix_attempted": "Fixed import path to 'src.auth.models'"
      }
    ]
  },
  "rules": [
    {
      "id": "ERR_001",
      "name": "ROOT_CAUSE_ANALYSIS",
      "description": "Always identify root cause, not just symptoms",
      "severity": "high"
    },
    {
      "id": "ERR_002",
      "name": "COMPREHENSIVE_ERROR_HANDLING",
      "description": "Handle all edge cases including None returns",
      "severity": "high"
    }
  ]
}
</METADATA>

<INSTRUCTION>
You are diagnosing and fixing an error for the Obra orchestration system.

**Error Details**:
- Type: runtime
- Message: AttributeError: 'NoneType' object has no attribute 'id'
- File: src/auth/handlers.py:15

**Stack Trace**:
```
File 'src/auth/handlers.py', line 15, in login_user
    user_id = user.id
AttributeError: 'NoneType' object has no attribute 'id'
```

**Code Context**:
```python
def login_user(email, password):
    """Login a user with email and password."""
    user = User.query.filter_by(email=email).first()
    user_id = user.id  # Line 15 - ERROR HERE
    if bcrypt.verify(password, user.password):
        token = generate_jwt_token(user_id)
        return {'token': token, 'user_id': user_id}
    return {'error': 'Invalid credentials'}
```

**Task Context**:
- Task: Implement user authentication module
- Attempt: #2
- Files Involved: src/auth/handlers.py, src/auth/models.py

**Previous Attempts**:
1. Attempt #1: ImportError - Fixed by correcting import path to 'src.auth.models'

**Your Task**:
Analyze the error, identify root cause, and propose a fix.

**Output Format**:
<METADATA>
{
  "root_cause": "...",
  "error_category": "...",
  "fix_approach": "...",
  "confidence": 0.95,
  "files_to_modify": [...],
  "estimated_fix_time_minutes": 5,
  "requires_human_review": false,
  "potential_side_effects": [...]
}
</METADATA>

<CONTENT>
...analysis and fix...
</CONTENT>
</INSTRUCTION>
```

**Expected Response**:
```
<METADATA>
{
  "root_cause": "User.query.filter_by() returns None when no matching user found, but code assumes user always exists",
  "error_category": "logic",
  "fix_approach": "code_change",
  "confidence": 0.95,
  "files_to_modify": ["src/auth/handlers.py"],
  "estimated_fix_time_minutes": 5,
  "requires_human_review": false,
  "potential_side_effects": [
    "Changes error response format for invalid email",
    "May need to update calling code expecting AttributeError"
  ]
}
</METADATA>

<CONTENT>
**Root Cause Analysis**:

The error occurs because `User.query.filter_by(email=email).first()` returns `None` when no user with the given email exists. The code then attempts to access `user.id` on line 15 without checking if `user` is None first.

This is a classic null pointer error - the code assumes the user lookup will always succeed, but it fails when:
1. The email doesn't exist in the database
2. The email parameter is malformed
3. There's a database connection issue

**Proposed Fix**:

```python
def login_user(email, password):
    """Login a user with email and password.

    Args:
        email: User's email address
        password: User's plaintext password

    Returns:
        Dict with token and user_id if successful, error dict otherwise

    Raises:
        ValueError: If email or password is empty
    """
    if not email or not password:
        return {'error': 'Email and password required'}

    user = User.query.filter_by(email=email).first()

    # FIX: Check if user exists before accessing attributes
    if user is None:
        return {'error': 'Invalid credentials'}

    # Verify password
    if bcrypt.verify(password, user.password):
        token = generate_jwt_token(user.id)
        return {'token': token, 'user_id': user.id}

    return {'error': 'Invalid credentials'}
```

**Why This Works**:

1. **Early return on None**: Check if `user is None` before accessing `user.id`
2. **Consistent error messages**: Both "user not found" and "wrong password" return "Invalid credentials" to avoid leaking information about which emails exist
3. **Input validation**: Check for empty email/password upfront
4. **Security**: Don't reveal whether the error was "user not found" vs "wrong password"

**Testing Strategy**:

1. **Test invalid email**: Call `login_user('nonexistent@example.com', 'password')` → Should return `{'error': 'Invalid credentials'}` without AttributeError
2. **Test valid email, wrong password**: Should also return error without crash
3. **Test valid credentials**: Should return token and user_id
4. **Test empty inputs**: Should return 'Email and password required' error

**Changes Required**:
- File: `src/auth/handlers.py`, lines 10-20
- Add None check after user lookup
- Add input validation
- Update docstring

**Confidence**: 95% - This is a straightforward null check. The remaining 5% uncertainty is in case there are other places in the code that expect AttributeError to be raised.
</CONTENT>
```

## Best Practices

1. **Include full stack trace** - Don't truncate, show complete error context
2. **Show previous attempts** - Helps avoid repeating failed fixes
3. **Provide code context** - Show surrounding code, not just the error line
4. **Root cause, not symptoms** - Don't just fix the crash, fix the underlying issue
5. **Security-aware fixes** - Don't leak information in error messages
6. **Test strategy** - Explain how to verify the fix works
7. **Assess confidence** - Be honest about uncertainty
8. **Note side effects** - What else might this fix impact?
