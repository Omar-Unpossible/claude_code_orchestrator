# Task Execution Hybrid Prompt Template

This template shows the structure of a hybrid prompt for task execution.

## Format

```
<METADATA>
{
  "prompt_type": "task_execution",
  "task_id": <task_id>,
  "task_title": "<task_title>",
  "project_id": <project_id>,
  "context": {
    "files": ["<file1.py>", "<file2.py>"],
    "dependencies": ["<dep1>", "<dep2>"],
    "previous_attempts": <number>,
    "working_directory": "<path>"
  },
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
    }
  ],
  "expectations": {
    "response_format": "structured",
    "include_tests": true,
    "include_documentation": true,
    "max_files": 5,
    "preserve_existing_code": true
  }
}
</METADATA>

<INSTRUCTION>
You are implementing a software development task for the Obra orchestration system.

**Task**: <task_title>

**Description**: <detailed_task_description>

**Requirements**:
1. Implement the functionality described in the task
2. Follow all provided rules (see METADATA section)
3. Write comprehensive tests for all new code
4. Add Google-style docstrings to all public functions and classes
5. Ensure thread safety where applicable
6. Handle errors gracefully with proper exception handling

**Context**:
- Project: <project_name> (ID: <project_id>)
- Working Directory: <working_directory>
- Related Files: <files_list>
- Dependencies: <dependencies_list>

**Output Format**:
Please respond using the structured format:

<METADATA>
{
  "status": "completed|failed|partial|blocked",
  "files_modified": ["<absolute_paths>"],
  "files_created": ["<absolute_paths>"],
  "tests_added": <count>,
  "confidence": <0.0-1.0>,
  "requires_review": <true|false>,
  "blocking_issues": ["<issue1>", "<issue2>"] // if status=blocked
}
</METADATA>

<CONTENT>
<your_explanation_and_reasoning>
</CONTENT>

**Important**:
- Never use stub functions (pass, TODO, NotImplemented)
- All code must be production-ready
- Include error handling and edge cases
- Follow Python best practices and PEP 8
</INSTRUCTION>
```

## Example

```
<METADATA>
{
  "prompt_type": "task_execution",
  "task_id": 123,
  "task_title": "Implement user authentication module",
  "project_id": 5,
  "context": {
    "files": ["src/auth/models.py", "src/auth/handlers.py"],
    "dependencies": ["bcrypt", "jwt"],
    "previous_attempts": 0,
    "working_directory": "/projects/webapp"
  },
  "rules": [
    {
      "id": "CODE_001",
      "name": "NO_STUBS",
      "description": "Never generate stub functions or placeholder code",
      "severity": "critical",
      "validation_type": "ast_check"
    },
    {
      "id": "SEC_001",
      "name": "SECURE_PASSWORD_HASHING",
      "description": "Always use bcrypt or similar for password hashing, never plaintext",
      "severity": "critical",
      "validation_type": "manual_review"
    }
  ],
  "expectations": {
    "response_format": "structured",
    "include_tests": true,
    "include_documentation": true,
    "max_files": 3,
    "preserve_existing_code": true
  }
}
</METADATA>

<INSTRUCTION>
You are implementing a software development task for the Obra orchestration system.

**Task**: Implement user authentication module

**Description**: Create a complete user authentication system with JWT tokens. The module should support user registration, login, logout, and token refresh. Use bcrypt for password hashing and include comprehensive error handling.

**Requirements**:
1. Implement user registration with email/password
2. Implement login with JWT token generation
3. Implement token refresh mechanism
4. Write unit tests for all authentication flows
5. Add Google-style docstrings
6. Handle edge cases (duplicate emails, invalid credentials, expired tokens)

**Context**:
- Project: WebApp (ID: 5)
- Working Directory: /projects/webapp
- Related Files: src/auth/models.py, src/auth/handlers.py
- Dependencies: bcrypt, jwt

**Output Format**:
Please respond using the structured format:

<METADATA>
{
  "status": "completed|failed|partial|blocked",
  "files_modified": ["<absolute_paths>"],
  "files_created": ["<absolute_paths>"],
  "tests_added": <count>,
  "confidence": <0.0-1.0>,
  "requires_review": <true|false>,
  "blocking_issues": ["<issue1>"] // if status=blocked
}
</METADATA>

<CONTENT>
<your_explanation_and_reasoning>
</CONTENT>

**Important**:
- Never use stub functions (pass, TODO, NotImplemented)
- All code must be production-ready
- Security is critical - follow SEC_001 rule strictly
- Include comprehensive error handling
</INSTRUCTION>
```

## Best Practices

1. **Always include task context** - Files, dependencies, working directory
2. **Inject applicable rules** - Use PromptRuleEngine to get relevant rules
3. **Set clear expectations** - Response format, test requirements, documentation
4. **Be specific about output format** - Show the expected structured response
5. **Include previous attempt count** - Helps LLM understand if it's a retry
6. **List blocking issues** - If task failed before, explain what blocked it
