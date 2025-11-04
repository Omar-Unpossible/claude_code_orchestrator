# Hybrid Prompt Templates

This directory contains templates and best practices for writing hybrid prompts (JSON metadata + natural language) for the Obra orchestration system.

## Overview

Hybrid prompts combine the strengths of both structured data and natural language:
- **JSON Metadata**: Machine-readable context, rules, and expectations
- **Natural Language Instructions**: Clear task descriptions and guidance for the LLM

This approach enables:
- ✅ **Consistent Structure**: All prompts follow the same format
- ✅ **Rule Enforcement**: Rules from `config/prompt_rules.yaml` are automatically injected
- ✅ **Quality Validation**: Responses can be validated against schemas
- ✅ **Machine + Human Readable**: Easy for both LLMs and developers to understand

## Template Files

### 1. [task_execution_template.md](task_execution_template.md)
Template for code generation and task execution prompts.

**Use When**:
- Implementing new features
- Fixing bugs
- Refactoring code
- Adding documentation

**Key Features**:
- Injects rules from code_generation, testing, documentation, security domains
- Includes context (files, dependencies, previous attempts)
- Specifies expected response format with status, files modified, confidence

**Example**:
```json
{
  "prompt_type": "task_execution",
  "task_id": 123,
  "task_title": "Implement user authentication",
  "rules": [...],
  "expectations": {
    "include_tests": true,
    "max_files": 5
  }
}
```

---

### 2. [validation_template.md](validation_template.md)
Template for code quality validation prompts.

**Use When**:
- Validating code against rules
- Performing code reviews
- Checking security compliance
- Assessing code quality

**Key Features**:
- Specifies rules to validate against
- Includes full file content for review
- Expects structured violations with line numbers and suggestions
- Calculates quality score (0-100)

**Example**:
```json
{
  "prompt_type": "validation",
  "validation_scope": "code_quality",
  "rules": [...],
  "context": {
    "files_to_validate": ["/path/to/file.py"]
  }
}
```

---

### 3. [error_analysis_template.md](error_analysis_template.md)
Template for error diagnosis and recovery prompts.

**Use When**:
- Diagnosing runtime errors
- Fixing test failures
- Resolving syntax errors
- Recovering from failures

**Key Features**:
- Includes full stack trace and error context
- Tracks previous fix attempts to avoid repetition
- Expects root cause analysis and specific fix proposal
- Assesses confidence in fix
- Identifies potential side effects

**Example**:
```json
{
  "prompt_type": "error_analysis",
  "error_context": {
    "error_type": "runtime",
    "error_message": "AttributeError: ...",
    "stack_trace": "...",
    "failed_file": "/path/to/file.py",
    "failed_line": 42
  },
  "context": {
    "attempt_number": 2,
    "previous_attempts": [...]
  }
}
```

---

### 4. [decision_template.md](decision_template.md)
Template for orchestration decision prompts.

**Use When**:
- Deciding next action after task completion
- Determining whether to retry, escalate, or proceed
- Assessing task quality
- Making orchestration decisions

**Key Features**:
- Includes agent response and validation results
- Considers attempt history and thresholds
- Provides structured decision with confidence score
- Recommends specific next actions
- Estimates time for next action

**Example**:
```json
{
  "prompt_type": "decision",
  "decision_context": {
    "current_state": "completed",
    "agent_response": {...},
    "validation_results": {...}
  },
  "context": {
    "attempt_number": 1,
    "max_retries": 3,
    "quality_threshold": 80
  }
}
```

---

### 5. [planning_template.md](planning_template.md)
Template for task planning and decomposition prompts.

**Use When**:
- Decomposing complex tasks
- Identifying parallel execution opportunities
- Creating execution plans
- Analyzing task dependencies

**Key Features**:
- Breaks tasks into subtasks
- Identifies parallelization opportunities
- Maps dependencies between subtasks
- Estimates time for each subtask
- Groups subtasks into parallel execution groups
- Calculates time savings from parallelization

**Example**:
```json
{
  "prompt_type": "planning",
  "planning_context": {
    "planning_type": "decomposition",
    "complexity_estimate": {
      "overall_score": 78,
      "should_decompose": true
    }
  }
}
```

---

## Best Practices

See [BEST_PRACTICES.md](BEST_PRACTICES.md) for comprehensive guidance on:
- Core principles (separation of concerns, explicitness)
- Metadata design (required fields, rule integration, context completeness)
- Instruction crafting (structure, language, specificity)
- Response format guidance
- Common pitfalls to avoid
- Testing prompts before deployment

**Key Takeaways**:
1. **Metadata = Structure, Instruction = Semantics**
2. **Be Explicit, Not Implicit**
3. **Always Show Expected Output Format**
4. **Include Full Rule Objects**
5. **Provide Complete Context**
6. **Use Specific, Action-Oriented Language**
7. **Test Before Deploying**

---

## Usage

### With StructuredPromptBuilder

```python
from src.llm.structured_prompt_builder import StructuredPromptBuilder
from src.llm.prompt_rule_engine import PromptRuleEngine

# Load rules
rule_engine = PromptRuleEngine('config/prompt_rules.yaml')
rule_engine.load_rules_from_yaml()

# Create builder
builder = StructuredPromptBuilder(rule_engine=rule_engine)

# Build task execution prompt
prompt = builder.build_task_execution_prompt(
    task_data={
        'task_id': 123,
        'title': 'Implement authentication',
        'description': 'Add JWT-based user authentication'
    },
    context={
        'project_id': 1,
        'files': ['/path/to/auth.py'],
        'dependencies': ['jwt', 'bcrypt']
    }
)

# prompt now contains hybrid format ready for LLM
```

### With StructuredResponseParser

```python
from src.llm.structured_response_parser import StructuredResponseParser

# Initialize parser
parser = StructuredResponseParser('config/response_schemas.yaml')
parser.load_schemas()

# Parse LLM response
result = parser.parse_response(
    response=llm_response,
    expected_type='task_execution'
)

if result['is_valid']:
    status = result['metadata']['status']
    files = result['metadata']['files_modified']
    explanation = result['content']
else:
    errors = result['validation_errors']
```

---

## Prompt Structure

All hybrid prompts follow this structure:

```
<METADATA>
{
  "prompt_type": "task_execution|validation|error_analysis|decision|planning",
  "task_id": <integer>,
  "context": {
    "project_id": <integer>,
    "files": ["<absolute_paths>"],
    "dependencies": ["<packages>"]
  },
  "rules": [
    {
      "id": "<rule_id>",
      "name": "<rule_name>",
      "description": "<rule_description>",
      "severity": "critical|high|medium|low",
      "validation_type": "ast_check|manual_review|llm_based"
    }
  ],
  "expectations": {
    "response_format": "structured",
    "include_tests": true,
    ...
  }
}
</METADATA>

<INSTRUCTION>
Natural language instruction for the LLM.

**Task**: <one-line summary>

**Description**: <detailed description>

**Requirements**:
1. Requirement 1
2. Requirement 2

**Output Format**:
<show expected response structure>

**Important**:
- Critical guideline 1
- Critical guideline 2
</INSTRUCTION>
```

---

## Expected Response Format

LLMs should respond in this format:

```
<METADATA>
{
  "status": "completed|failed|partial|blocked",
  "files_modified": ["<absolute_paths>"],
  "confidence": 0.85,
  "requires_review": false
}
</METADATA>

<CONTENT>
Natural language explanation of what was done and why.
</CONTENT>
```

---

## Configuration Integration

### Rules from `config/prompt_rules.yaml`

The PromptRuleEngine automatically injects rules based on prompt type:
- **task_execution** → code_generation, testing, documentation, security
- **validation** → specific rules being validated
- **error_analysis** → error_handling, performance
- **planning** → code_generation, parallel_agents

See `config/prompt_rules.yaml` for all available rules (38 rules across 7 domains).

### Schemas from `config/response_schemas.yaml`

The StructuredResponseParser validates responses against schemas:
- `task_execution` - Task completion responses
- `validation` - Quality validation responses
- `error_analysis` - Error analysis responses
- `decision` - Orchestration decisions
- `planning` - Task planning responses

See `config/response_schemas.yaml` for full schema definitions.

---

## Testing

Before using a template in production:

1. **Validate JSON syntax** - Ensure metadata parses correctly
2. **Check required fields** - Verify all required fields are present
3. **Test with real LLM** - Send prompt and verify response format
4. **Validate response** - Use StructuredResponseParser to validate
5. **Iterate** - Refine based on results

Example test:
```python
# Build prompt
prompt = builder.build_task_execution_prompt(task_data, context)

# Send to LLM
response = llm.generate(prompt)

# Parse and validate
parsed = parser.parse_response(response, 'task_execution')

# Check validity
assert parsed['is_valid'], f"Errors: {parsed['validation_errors']}"
assert 'status' in parsed['metadata']
assert parsed['metadata']['status'] in ['completed', 'failed', 'partial', 'blocked']
```

---

## Contributing

When adding new templates:

1. Follow the existing format (metadata + instruction)
2. Include examples with expected responses
3. Document use cases and key features
4. Add to this README
5. Test with real LLM before committing

---

## Related Documentation

- **Architecture**: See `docs/architecture/ARCHITECTURE.md`
- **Implementation Plan**: See `docs/development/LLM_FIRST_IMPLEMENTATION_PLAN.yaml`
- **Design Document**: See `docs/design/LLM_FIRST_PROMPT_ENGINEERING_FRAMEWORK.md`
- **Code Validators**: See `src/llm/code_validators.py`
- **Prompt Rule Engine**: See `src/llm/prompt_rule_engine.py`

---

## Summary

These templates provide a consistent, validated approach to LLM prompting that:
- ✅ Enforces quality rules automatically
- ✅ Provides clear, structured context
- ✅ Generates parseable, validated responses
- ✅ Enables machine + human readability
- ✅ Supports complex orchestration workflows

For questions or improvements, see the implementation in `src/llm/structured_prompt_builder.py` and `src/llm/structured_response_parser.py`.
