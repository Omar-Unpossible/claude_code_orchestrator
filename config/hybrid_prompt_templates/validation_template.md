# Validation Hybrid Prompt Template

This template shows the structure of a hybrid prompt for code validation.

## Format

```
<METADATA>
{
  "prompt_type": "validation",
  "task_id": <task_id>,
  "validation_scope": "code_quality|rule_compliance|security|performance",
  "rules": [
    {
      "id": "<rule_id>",
      "name": "<rule_name>",
      "description": "<rule_description>",
      "severity": "critical|high|medium|low",
      "validation_type": "ast_check|manual_review|llm_based"
    }
  ],
  "context": {
    "files_to_validate": ["<file1.py>", "<file2.py>"],
    "project_id": <project_id>,
    "validation_trigger": "post_execution|pre_merge|scheduled"
  }
}
</METADATA>

<INSTRUCTION>
You are performing code quality validation for the Obra orchestration system.

**Validation Scope**: <code_quality|rule_compliance|security|performance>

**Files to Validate**:
<file_list_with_content>

**Rules to Check**:
<rules_list_with_details>

**Your Task**:
1. Review the provided code against each rule
2. Identify any violations with specific line numbers
3. Assess severity of each violation
4. Provide actionable fix suggestions
5. Calculate overall quality score (0-100)

**Output Format**:
<METADATA>
{
  "is_valid": <true|false>,
  "quality_score": <0-100>,
  "violations": [
    {
      "rule_id": "<rule_id>",
      "file": "<file_path>",
      "line": <line_number>,
      "severity": "<critical|high|medium|low>",
      "message": "<violation_description>",
      "suggestion": "<fix_suggestion>"
    }
  ],
  "warnings": ["<warning1>", "<warning2>"],
  "passed_rules": ["<rule_id1>", "<rule_id2>"]
}
</METADATA>

<CONTENT>
<detailed_analysis_and_reasoning>
</CONTENT>
</INSTRUCTION>
```

## Example

```
<METADATA>
{
  "prompt_type": "validation",
  "task_id": 123,
  "validation_scope": "code_quality",
  "rules": [
    {
      "id": "CODE_001",
      "name": "NO_STUBS",
      "description": "Never generate stub functions or placeholder code",
      "severity": "critical",
      "validation_type": "ast_check"
    },
    {
      "id": "CODE_002",
      "name": "COMPREHENSIVE_DOCSTRINGS",
      "description": "All public functions must have Google-style docstrings",
      "severity": "high",
      "validation_type": "ast_check"
    },
    {
      "id": "CODE_005",
      "name": "NO_HARDCODED_VALUES",
      "description": "No magic numbers or hardcoded configuration",
      "severity": "medium",
      "validation_type": "ast_check"
    }
  ],
  "context": {
    "files_to_validate": ["src/auth/handlers.py"],
    "project_id": 5,
    "validation_trigger": "post_execution"
  }
}
</METADATA>

<INSTRUCTION>
You are performing code quality validation for the Obra orchestration system.

**Validation Scope**: code_quality

**Files to Validate**:

`src/auth/handlers.py`:
```python
def login_user(email, password):
    # TODO: implement login logic
    pass

def register_user(email, password):
    hashed = bcrypt.hash(password, rounds=12)
    user = User(email=email, password=hashed)
    return user

def validate_token(token):
    """Validate JWT token."""
    try:
        payload = jwt.decode(token, "secret_key_123", algorithms=["HS256"])
        return payload
    except:
        return None
```

**Rules to Check**:
1. **CODE_001 (CRITICAL)**: NO_STUBS - Never generate stub functions or placeholder code
2. **CODE_002 (HIGH)**: COMPREHENSIVE_DOCSTRINGS - All public functions must have Google-style docstrings
3. **CODE_005 (MEDIUM)**: NO_HARDCODED_VALUES - No magic numbers or hardcoded configuration

**Your Task**:
1. Review the code against each rule
2. Identify violations with specific line numbers
3. Provide fix suggestions
4. Calculate quality score

**Output Format**:
<METADATA>
{
  "is_valid": <true|false>,
  "quality_score": <0-100>,
  "violations": [...],
  "warnings": [...],
  "passed_rules": [...]
}
</METADATA>

<CONTENT>
<analysis>
</CONTENT>
</INSTRUCTION>
```

**Expected Response**:
```
<METADATA>
{
  "is_valid": false,
  "quality_score": 45,
  "violations": [
    {
      "rule_id": "CODE_001",
      "file": "src/auth/handlers.py",
      "line": 2,
      "severity": "critical",
      "message": "Function 'login_user' contains only TODO comment and pass statement",
      "suggestion": "Implement the complete login logic with email/password verification"
    },
    {
      "rule_id": "CODE_002",
      "file": "src/auth/handlers.py",
      "line": 1,
      "severity": "high",
      "message": "Function 'login_user' missing docstring",
      "suggestion": "Add Google-style docstring with Args, Returns, and Raises sections"
    },
    {
      "rule_id": "CODE_002",
      "file": "src/auth/handlers.py",
      "line": 5,
      "severity": "high",
      "message": "Function 'register_user' missing docstring",
      "suggestion": "Add Google-style docstring documenting the registration process"
    },
    {
      "rule_id": "CODE_005",
      "file": "src/auth/handlers.py",
      "line": 6,
      "severity": "medium",
      "message": "Hardcoded value 'rounds=12' should be configuration",
      "suggestion": "Move bcrypt rounds to config file or environment variable"
    },
    {
      "rule_id": "CODE_005",
      "file": "src/auth/handlers.py",
      "line": 12,
      "severity": "medium",
      "message": "Hardcoded secret key 'secret_key_123' is a security risk",
      "suggestion": "Load JWT secret from environment variable or secure configuration"
    }
  ],
  "warnings": [
    "Bare except clause in validate_token() hides errors - use specific exceptions",
    "Missing error handling for invalid email format in register_user()"
  ],
  "passed_rules": []
}
</METADATA>

<CONTENT>
The code has 5 critical and high severity violations:

1. **CRITICAL - Stub Function**: The `login_user()` function is a stub with only a TODO comment and pass statement. This violates the NO_STUBS rule and makes the authentication system non-functional.

2. **HIGH - Missing Docstrings**: Both `login_user()` and `register_user()` lack docstrings. Google-style docstrings should document parameters, return values, and potential exceptions.

3. **MEDIUM - Hardcoded Configuration**: The bcrypt rounds parameter (12) should be in configuration to allow tuning for different environments.

4. **MEDIUM - Hardcoded Secret**: The JWT secret key "secret_key_123" is hardcoded, which is a major security vulnerability. Secrets must be loaded from environment variables or secure vaults.

**Recommended Fixes**:
- Implement complete login logic with database lookup and password verification
- Add comprehensive docstrings to all functions
- Move bcrypt rounds to config file
- Load JWT secret from environment variable (e.g., JWT_SECRET_KEY)
- Replace bare except with specific exception handling

**Quality Score Calculation**: 45/100
- -30 points: Critical stub function
- -15 points: Missing docstrings (high severity)
- -10 points: Security issues (hardcoded secrets)
</CONTENT>
```

## Best Practices

1. **Include full file content** - Show the actual code being validated
2. **List all applicable rules** - With severity and validation type
3. **Be specific about violations** - Include line numbers and context
4. **Provide actionable suggestions** - Not just "fix this", but "do X instead of Y"
5. **Calculate quality score** - Helps track improvements over time
6. **Separate violations from warnings** - Critical issues vs. recommendations
