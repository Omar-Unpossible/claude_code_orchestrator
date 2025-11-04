# Hybrid Prompt Best Practices Guide

This guide provides best practices for writing effective hybrid prompts (JSON metadata + natural language) for the Obra LLM-first orchestration system.

## Table of Contents

1. [Core Principles](#core-principles)
2. [Metadata Design](#metadata-design)
3. [Instruction Crafting](#instruction-crafting)
4. [Rule Integration](#rule-integration)
5. [Response Format Guidance](#response-format-guidance)
6. [Common Pitfalls](#common-pitfalls)
7. [Testing Prompts](#testing-prompts)

---

## Core Principles

### 1. **Separation of Concerns**

**DO**: Separate machine-readable metadata from human-readable instructions
```
<METADATA>
{machine-readable JSON}
</METADATA>

<INSTRUCTION>
Natural language for LLM
</INSTRUCTION>
```

**DON'T**: Mix JSON and natural language in the same section
```
{
  "task_id": 123,
  "instruction": "Now implement the authentication module..."  ❌
}
```

### 2. **Metadata is for Structure, Instructions are for Semantics**

**Metadata contains**:
- Task identifiers (task_id, project_id)
- Rules to enforce
- Expected response structure
- Context (files, dependencies)
- Thresholds and limits

**Instructions contain**:
- What to do (task description)
- Why to do it (business logic)
- How to do it (guidance, examples)
- What to avoid (anti-patterns)

### 3. **Be Explicit, Not Implicit**

**DO**: Spell out expectations clearly
```json
"expectations": {
  "response_format": "structured",
  "include_tests": true,
  "include_documentation": true,
  "max_files": 5
}
```

**DON'T**: Assume the LLM will infer requirements
```json
"expectations": {
  "quality": "good"  ❌ Too vague
}
```

---

## Metadata Design

### Required Fields

Every prompt must include:
```json
{
  "prompt_type": "task_execution|validation|error_analysis|decision|planning",
  "task_id": <integer>,
  "context": {
    "project_id": <integer>,
    "files": ["<absolute_paths>"],
    "dependencies": ["<package_names>"]
  }
}
```

### Rule Integration

**DO**: Include full rule objects, not just IDs
```json
"rules": [
  {
    "id": "CODE_001",
    "name": "NO_STUBS",
    "description": "Never generate stub functions or placeholder code",
    "severity": "critical",
    "validation_type": "ast_check"
  }
]
```

**DON'T**: Just reference rule IDs
```json
"rules": ["CODE_001", "CODE_002"]  ❌ LLM can't understand what these mean
```

### Context Completeness

**DO**: Provide complete context
```json
"context": {
  "project_id": 5,
  "files": ["/absolute/path/to/file.py"],
  "dependencies": ["requests", "jwt"],
  "previous_attempts": 1,
  "previous_error": "AttributeError at line 42",
  "working_directory": "/projects/webapp"
}
```

**DON'T**: Provide minimal context
```json
"context": {
  "files": ["file.py"]  ❌ Relative path, no other context
}
```

---

## Instruction Crafting

### Structure

Use this template structure:

```markdown
**Task**: <one-line summary>

**Description**: <detailed explanation>

**Requirements**:
1. Requirement 1
2. Requirement 2
...

**Context**:
- Project: <project_name>
- Files: <file_list>
- Dependencies: <dependency_list>

**Output Format**:
<show_expected_response_structure>

**Important**:
- Critical point 1
- Critical point 2
```

### Language Guidelines

**DO**: Use imperative, action-oriented language
```
✓ "Implement user authentication with JWT tokens"
✓ "Validate the code against rule CODE_001"
✓ "Analyze the error and propose a fix"
```

**DON'T**: Use vague or passive language
```
❌ "Authentication should be done"
❌ "Check if there are any issues"
❌ "Look at the code"
```

### Specificity

**DO**: Be specific about requirements
```
**Requirements**:
1. Implement user registration with email/password
2. Use bcrypt for password hashing (minimum 12 rounds)
3. Generate JWT tokens with 24-hour expiration
4. Add Google-style docstrings to all public functions
5. Write unit tests achieving ≥85% coverage
```

**DON'T**: Be vague
```
**Requirements**:
1. Add authentication  ❌ Too vague
2. Make it secure      ❌ What does "secure" mean?
3. Add tests           ❌ How many? What coverage?
```

---

## Rule Integration

### When to Include Rules

**Always include rules for**:
- `task_execution` prompts → code_generation, testing, documentation, security domains
- `validation` prompts → specific rules being validated
- `error_analysis` prompts → error_handling, performance domains
- `planning` prompts → code_generation, parallel_agents domains

**Example**:
```json
"rules": [
  {
    "id": "CODE_001",
    "name": "NO_STUBS",
    "severity": "critical",
    "description": "Never generate stub functions or placeholder code",
    "validation_type": "ast_check"
  },
  {
    "id": "CODE_002",
    "name": "COMPREHENSIVE_DOCSTRINGS",
    "severity": "high",
    "description": "All public functions must have Google-style docstrings",
    "validation_type": "ast_check"
  }
]
```

### Rule Emphasis in Instructions

**DO**: Reference rules in the instruction text
```
**Important**:
- Never use stub functions (see rule CODE_001)
- All code must be production-ready
- Add comprehensive docstrings (see rule CODE_002)
```

**DON'T**: Only include rules in metadata without mentioning them
```
<METADATA>
{"rules": [...]}  ✓
</METADATA>

<INSTRUCTION>
Implement the feature.  ❌ No mention of rules
</INSTRUCTION>
```

---

## Response Format Guidance

### Always Show Expected Format

**DO**: Include a template of the expected response
```
**Output Format**:
<METADATA>
{
  "status": "completed|failed|partial|blocked",
  "files_modified": ["<absolute_paths>"],
  "confidence": <0.0-1.0>,
  "requires_review": <true|false>
}
</METADATA>

<CONTENT>
<your_explanation_here>
</CONTENT>
```

**DON'T**: Just say "respond in structured format"
```
Please respond in structured format.  ❌ LLM doesn't know what that means
```

### Response Validation

Specify validation criteria in metadata:
```json
"expectations": {
  "response_format": "structured",
  "required_fields": ["status", "files_modified", "confidence"],
  "status_values": ["completed", "failed", "partial", "blocked"],
  "confidence_range": [0.0, 1.0]
}
```

---

## Common Pitfalls

### Pitfall 1: Redundancy

**BAD**:
```json
{
  "task_id": 123,
  "task_title": "Implement auth",
  "task_description": "Implement authentication"  ❌ Redundant
}
```

**GOOD**:
```json
{
  "task_id": 123,
  "task_title": "Implement authentication module"
}
```

Then provide full description in the `<INSTRUCTION>` section.

### Pitfall 2: Missing Context

**BAD**:
```json
{
  "context": {
    "files": ["auth.py"]  ❌ Which directory? Previous state?
  }
}
```

**GOOD**:
```json
{
  "context": {
    "files": ["/projects/webapp/src/auth/handlers.py"],
    "working_directory": "/projects/webapp",
    "previous_attempts": 1,
    "last_error": "ImportError: cannot import 'User'"
  }
}
```

### Pitfall 3: Unclear Expectations

**BAD**:
```
Make the code better.  ❌ What does "better" mean?
```

**GOOD**:
```
**Requirements**:
1. Reduce cyclomatic complexity from 15 to <10
2. Extract helper functions for repeated logic
3. Add type hints to all function parameters
4. Improve variable names for clarity
```

### Pitfall 4: Ignoring Previous Attempts

**BAD**:
```json
{
  "attempt_number": 2  ❌ No info about what failed in attempt 1
}
```

**GOOD**:
```json
{
  "attempt_number": 2,
  "previous_attempts": [
    {
      "attempt": 1,
      "error": "AttributeError: 'NoneType' object has no attribute 'id'",
      "fix_attempted": "Added None check before accessing user.id"
    }
  ]
}
```

### Pitfall 5: Overly Restrictive Rules

**BAD**:
```json
"rules": [
  /* 50 rules listed */  ❌ Too many rules confuse the LLM
]
```

**GOOD**:
```json
"rules": [
  /* 3-7 most relevant rules for this task */
]
```

Use PromptRuleEngine's domain filtering to get only applicable rules.

---

## Testing Prompts

### Validation Checklist

Before deploying a new prompt template:

- [ ] Metadata is valid JSON
- [ ] All required fields present
- [ ] Rules include full objects, not just IDs
- [ ] Context includes absolute paths
- [ ] Instruction is clear and specific
- [ ] Expected response format is shown
- [ ] Examples are included where helpful
- [ ] No redundancy between metadata and instruction

### Testing Process

1. **Validate JSON**: Use `json.loads()` to ensure metadata parses
2. **Schema Check**: Validate against prompt schema (if defined)
3. **Manual Review**: Read as if you were the LLM - is it clear?
4. **Test with Real LLM**: Send prompt to LLM and check response format
5. **Iterate**: Refine based on LLM responses

### Example Test

```python
from src.llm.structured_prompt_builder import StructuredPromptBuilder
from src.llm.prompt_rule_engine import PromptRuleEngine

# Load rules
rule_engine = PromptRuleEngine('config/prompt_rules.yaml')
rule_engine.load_rules_from_yaml()

# Build prompt
builder = StructuredPromptBuilder(rule_engine=rule_engine)
prompt = builder.build_task_execution_prompt(
    task_data={'task_id': 123, 'title': 'Test task'},
    context={'project_id': 1, 'files': ['/path/to/file.py']}
)

# Verify structure
assert '<METADATA>' in prompt
assert '<INSTRUCTION>' in prompt
assert 'task_id' in prompt
assert 'rules' in prompt

# Send to LLM and check response
response = llm.generate(prompt)
parsed = parser.parse_response(response, 'task_execution')
assert parsed['is_valid']
```

---

## Summary

**Golden Rules**:
1. **Metadata = Structure, Instruction = Semantics**
2. **Be Explicit, Not Implicit**
3. **Always Show Expected Output Format**
4. **Include Full Rule Objects**
5. **Provide Complete Context**
6. **Use Specific, Action-Oriented Language**
7. **Test Before Deploying**

Following these practices ensures:
- ✅ LLMs understand what to do
- ✅ Responses are consistently structured
- ✅ Rules are properly enforced
- ✅ Quality is maintained
- ✅ Debugging is easier

For specific examples, see the template files:
- `task_execution_template.md`
- `validation_template.md`
- `error_analysis_template.md`
- `decision_template.md`
- `planning_template.md`
